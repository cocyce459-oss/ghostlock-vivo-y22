#!/usr/bin/env python3
"""
Minimal AArch64 (ARM64) instruction decoder - pure stdlib, no capstone needed.

Scope: enough of the A64 load/store + add/sub + branch-immediate encoding space
to recover struct field offsets from kernel disassembly, which is what the
offset-extraction tooling actually needs.

  python3 tools/a64dec.py Kernel.elf --sym commit_creds --span 0x80
  python3 tools/a64dec.py Kernel.elf --sym remove_waiter --span 0x100
  python3 tools/a64dec.py Kernel.elf --addr 0xffffff800812ed10 --span 0x40
"""

import argparse
import struct
import sys

# ---------------------------------------------------------------- ELF loading


class Elf:
    def __init__(self, path):
        self.data = open(path, "rb").read()
        if self.data[:4] != b"\x7fELF":
            raise ValueError("not an ELF")
        if self.data[4] != 2:
            raise ValueError("not ELF64")
        if self.data[5] != 1:
            raise ValueError("not little-endian")
        (self.e_type, self.e_machine, _ver, self.e_entry, self.e_phoff,
         self.e_shoff, _flags, _ehsize, self.phentsize, self.phnum,
         self.shentsize, self.shnum, self.shstrndx) = struct.unpack_from(
            "<HHIQQQIHHHHHH", self.data, 16)
        if self.e_machine != 183:
            raise ValueError(f"not AArch64 (e_machine={self.e_machine})")
        self.sections = self._read_sections()
        self.symbols = self._read_symbols()

    def _read_sections(self):
        out = []
        for i in range(self.shnum):
            off = self.e_shoff + i * self.shentsize
            (name, stype, flags, addr, offset, size, link, info,
             align, entsize) = struct.unpack_from("<IIQQQQIIQQ", self.data, off)
            out.append(dict(name=name, type=stype, flags=flags, addr=addr,
                            offset=offset, size=size, link=link,
                            entsize=entsize))
        return out

    def _read_symbols(self):
        syms = {}
        for sec in self.sections:
            if sec["type"] != 2:  # SHT_SYMTAB
                continue
            strtab = self.sections[sec["link"]]
            n = sec["size"] // 24
            for i in range(n):
                off = sec["offset"] + i * 24
                st_name, st_info, st_other, st_shndx, st_value, st_size = \
                    struct.unpack_from("<IBBHQQ", self.data, off)
                if st_name == 0 or st_value == 0:
                    continue
                end = self.data.find(b"\x00", strtab["offset"] + st_name)
                name = self.data[strtab["offset"] + st_name:end].decode(
                    "ascii", "replace")
                syms.setdefault(name, st_value)
        return syms

    def text_ranges(self):
        r = [(s["addr"], s["size"], s["name"]) for s in self.sections
             if s["type"] == 1 and s["size"] and s["addr"]]
        if r:
            return r
        # vmlinux-style: one giant PROGBITS named .kernel
        for s in self.sections:
            if s["type"] == 1 and s["size"]:
                return [(s["addr"], s["size"], s["name"] or ".text")]
        raise ValueError("no PROGBITS section")

    def va_to_file(self, va):
        for addr, size, _n in self.text_ranges():
            if addr <= va < addr + size:
                return va - addr
        return None

    def read_va(self, va, n):
        off = self.va_to_file(va)
        if off is None:
            return None
        return self.data[off:off + n]


# ------------------------------------------------------------------ decoding

REGS = ["x%d" % i for i in range(31)] + ["sp", "xzr"]


def sx(val, bits):
    """sign-extend"""
    sign = 1 << (bits - 1)
    return (val & (sign - 1)) - (val & sign)


def ldst(insn):
    """Decode load/store (32/64) - unsigned imm12 and unscaled imm9 forms.

    A64 load/store immediate:
        31-30 size | 29-27 111 | 26 V | 25-24 01=unsigned-imm12 00=unscaled
    """
    if ((insn >> 27) & 0x7) != 0x7:          # bits 29..27 == 111
        return None
    if (insn >> 26) & 1:                     # V=1 -> SIMD/FP, not needed
        return None
    size = (insn >> 30) & 0x3
    opc = (insn >> 22) & 0x3
    rt = insn & 0x1F
    rn = (insn >> 5) & 0x1F
    kind = {0: "b", 1: "h", 2: "w", 3: "x"}[size]
    mode = (insn >> 24) & 0x3

    if mode == 0x1:                          # unsigned imm12
        if rn == 31:
            return None                      # SP-relative / literal form
        off = ((insn >> 10) & 0xFFF) << size
        if opc == 0:
            return f"str{kind}\t{REGS[rt]}, [{REGS[rn]}, #0x{off:x}]", off, rt, rn, True
        if opc == 1:
            return f"ldr{kind}\t{REGS[rt]}, [{REGS[rn]}, #0x{off:x}]", off, rt, rn, False
        if opc == 2:
            sfx = "ldrsw" if size == 3 else f"ldr{kind}"
            return f"{sfx}\t{REGS[rt]}, [{REGS[rn]}, #0x{off:x}]", off, rt, rn, False
        return None                          # prfm

    if mode == 0x0 and ((insn >> 21) & 1) == 0 and opc in (0, 1, 2):
        off = sx((insn >> 12) & 0x1FF, 9)     # unscaled / LDUR
        u = off & 0xFFFFFFFFFFFFFFFF
        if opc == 0:
            return f"str{kind}\t{REGS[rt]}, [{REGS[rn]}, #0x{u:x}]", off, rt, rn, True
        sfx = "ldrsw" if (opc == 2 and size == 3) else f"ldr{kind}"
        return f"{sfx}\t{REGS[rt]}, [{REGS[rn]}, #0x{u:x}]", off, rt, rn, False
    return None


def addsub_imm(insn):
    """ADD/SUB (immediate) - covers the shifted form used for large offsets"""
    if (insn >> 24) & 0x3F != 0x11:
        return None
    op = (insn >> 30) & 1
    sh = (insn >> 22) & 1
    imm = ((insn >> 10) & 0xFFF) << (12 if sh else 0)
    rn = (insn >> 5) & 0x1F
    rd = insn & 0x1F
    name = "sub" if op else "add"
    if rn == 31:
        return f"{name}\t{REGS[rd]}, #0x{imm:x}", imm, rd, rn, None
    return f"{name}\t{REGS[rd]}, {REGS[rn]}, #0x{imm:x}", imm, rd, rn, None



def adrp(insn):
    if (insn >> 24) & 0x3F != 0x10:
        return None
    immlo = (insn >> 29) & 0x3
    immhi = (insn >> 5) & 0x7FFFF
    imm = sx((immhi << 2) | immlo, 21) << 12
    rd = insn & 0x1F
    return f"adrp\t{REGS[rd]}, #0x{imm:x}", imm, rd, rd, None


def decode(word):
    """Best-effort decode. Returns (mnemonic_text, kind, off, rt, rn)"""
    for fn in (adrp, addsub_imm, ldst):
        try:
            r = fn(word)
        except Exception:
            r = None
        if r:
            return r
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("elf")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--sym", help="symbol name to disassemble")
    g.add_argument("--addr", help="hex address to disassemble")
    ap.add_argument("--span", default="0x100", help="bytes to decode")
    ap.add_argument("--offsets-only", action="store_true",
                    help="print only recovered struct offsets")
    a = ap.parse_args()

    e = Elf(a.elf)
    span = int(a.span, 0)

    if a.sym:
        if a.sym not in e.symbols:
            print(f"[!] symbol not found: {a.sym}", file=sys.stderr)
            return 1
        va = e.symbols[a.sym]
    else:
        va = int(a.addr, 0)

    raw = e.read_va(va, span)
    if raw is None:
        print(f"[!] VA 0x{va:x} not inside a PROGBITS section", file=sys.stderr)
        return 1

    label = a.sym or f"0x{va:x}"
    if not a.offsets_only:
        print(f"; {label} @ 0x{va:x}  ({len(raw)} bytes)\n")

    seen = []
    for i in range(0, len(raw) - 3, 4):
        word = struct.unpack_from("<I", raw, i)[0]
        d = decode(word)
        if not d:
            continue
        txt, off, rt, rn, is_store = d
        cur = va + i
        if not a.offsets_only:
            print(f"  0x{cur:x}:  {word:08x}    {txt}")
        if off and (off & 0xFFF) in (0, 4, 8, 0xC, 0x10) or (off and off > 0x10):
            seen.append((cur, txt, off))

    if a.offsets_only:
        print(f"; offsets referenced in {label}:")
        for cur, txt, off in seen:
            print(f"  0x{cur:x}  off=0x{off & 0xffffffffffffffff:x}  {txt}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
