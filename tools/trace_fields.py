#!/usr/bin/env python3
"""
AArch64 dataflow tracer for kernel struct-offset recovery.

Decodes a function and tracks, where it is unambiguous, which register holds
which base pointer (the task_struct, the rt_mutex, the waiter), then reports
every field displacement reached through a known base.

This is stronger evidence than raw frequency counting, because it ties an
offset to a specific pointer the function actually operates on.

  python3 tools/trace_fields.py Kernel.elf --sym get_task_cred
  python3 tools/trace_fields.py Kernel.elf --sym task_blocks_on_rt_mutex --guess x19=task
"""

import argparse
import struct
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from a64dec import Elf, sx  # noqa: E402

R = [f"x{i}" for i in range(31)] + ["sp", "xzr"]


def rn(x):
    return R[x] if x < 32 else f"x{x}"


def decode(w):
    """Return (mnemonic, rd, rn, rm, imm) for the subset we track, else None."""
    # MOV (register) = ORR Rd, XZR, Rm
    #   sf=1 opc=01 01010 N=0 shift=00 Rm imm6=000000 Rn=11111 Rd
    if ((w >> 31) & 1) == 1 and ((w >> 29) & 3) == 1 \
            and ((w >> 24) & 0x1F) == 0x0A and ((w >> 22) & 1) == 0 \
            and ((w >> 21) & 3) == 0 and ((w >> 5) & 0x1F) == 31 \
            and ((w >> 10) & 0x3F) == 0:
        rm = (w >> 16) & 0x1F
        rd = w & 0x1F
        return ("mov", rd, None, rm, 0)
    # ADD/SUB (immediate)
    if (w >> 24) & 0x3F == 0x11:
        op = (w >> 30) & 1
        sh = (w >> 22) & 1
        imm = ((w >> 10) & 0xFFF) << (12 if sh else 0)
        return ("add" if op == 0 else "sub", w & 0x1F, (w >> 5) & 0x1F, None, imm)
    # LDR/STR immediate
    if ((w >> 27) & 7) == 7 and ((w >> 26) & 1) == 0:
        size = (w >> 30) & 3
        opc = (w >> 22) & 3
        rd = w & 0x1F
        base = (w >> 5) & 0x1F
        mode = (w >> 24) & 3
        if mode == 1 and base != 31:
            off = ((w >> 10) & 0xFFF) << size
            kind = {0: "b", 1: "h", 2: "w", 3: "x"}[size]
            if opc == 0:
                return (f"str{kind}", rd, base, None, off)
            if opc in (1, 2):
                return (f"ldr{kind}", rd, base, None, off)
        if mode == 0 and ((w >> 21) & 1) == 0 and opc in (0, 1, 2):
            off = sx((w >> 12) & 0x1FF, 9) & 0xFFFFFFFFFFFFFFFF
            kind = {0: "b", 1: "h", 2: "w", 3: "x"}[size]
            if opc == 0:
                return (f"str{kind}", rd, base, None, off)
            return (f"ldr{kind}", rd, base, None, off)
    return None


def trace(e, start, span, seeds):
    """seeds: {reg_index: label}. Returns list of (pc, base_label, off, text)."""
    raw = e.read_va(start, span)
    if not raw:
        return []
    # taint: reg -> label, meaning "this reg holds a pointer of that type"
    taint = dict(seeds)
    out = []
    for i in range(0, len(raw) - 3, 4):
        w = struct.unpack_from("<I", raw, i)[0]
        d = decode(w)
        if not d:
            continue
        mn, rd, base, rm, off = d
        pc = start + i
        kind = {0: "b", 1: "h", 2: "w", 3: "x"}[0]
        if mn == "mov":
            if rm in taint and rd not in taint:
                taint[rd] = taint[rm]
        elif mn == "add":
            # add rd, base, #imm  (LEA of a subfield -> record, don't retaint)
            if base in taint and off and rd not in taint:
                out.append((pc, taint[base], off, f"{mn} {rn(rd)}, {rn(base)}, #0x{off:x}"))
        elif mn.startswith("str") or mn.startswith("ldr"):
            if base in taint and off:
                out.append((pc, taint[base], off, f"{mn} {rn(rd)}, [{rn(base)}, #0x{off:x}]"))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("elf")
    ap.add_argument("--sym", required=True)
    ap.add_argument("--guess", action="append", default=[],
                    help="xN=label seed, e.g. x19=task")
    ap.add_argument("--span", default="0x100")
    a = ap.parse_args()

    e = Elf(a.elf)
    if a.sym not in e.symbols:
        print(f"symbol not found: {a.sym}", file=sys.stderr)
        return 1
    seeds = {}
    for g in a.guess:
        r, lbl = g.split("=", 1)
        seeds[int(r.lstrip("x"))] = lbl

    res = trace(e, e.symbols[a.sym], int(a.span, 0), seeds)
    print(f"; {a.sym} @ 0x{e.symbols[a.sym]:x}   seeds={a.guess or 'none'}\n")
    grouped = {}
    for pc, base, off, txt in res:
        grouped.setdefault((base, off), []).append((pc, txt))
    for (base, off), hits in sorted(grouped.items(), key=lambda kv: kv[0][1]):
        print(f"  {base}+0x{off:04x}   ({len(hits)}x)")
        for pc, txt in hits[:3]:
            print(f"      0x{pc:x}  {txt}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
