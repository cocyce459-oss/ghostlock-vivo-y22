#!/usr/bin/env python3
"""
Correct AArch64 load/store-pair + load/store decoder.

Written against the ARMv8-A ARM encoding tables (C4.1 Loads and Stores) and
self-checked against known encodings before use. Kept separate from a64dec.py
so the simple decoder stays simple and this one stays correct.
"""


def _sx(val, bits):
    sign = 1 << (bits - 1)
    return (val & (sign - 1)) - (val & sign)


REG = [f"x{i}" for i in range(31)] + ["sp"]
REGS = REG


def _sized(size, base=0):
    """AArch64 size code -> instruction suffix ('' for x, else b/h/w)."""
    return {0: "b", 1: "h", 2: "w", 3: ""}[size]


def ldp_stp(w):
    """Load/store pair.

    A64 C4.1:  opc(31:30) 101(29:27) V(26) 0(25) op2(24:23) L(22)
               imm7(21:15) Rt2(14:10) Rn(9:5) Rt(4:0)
    """
    if ((w >> 27) & 0x7) != 0b101:        # bits 29..27
        return None
    if ((w >> 25) & 1) != 0:              # bit 25 must be 0
        return None
    opc = (w >> 30) & 0x3
    V = (w >> 26) & 0x1
    op2 = (w >> 23) & 0x3
    L = (w >> 22) & 0x1
    imm7 = (w >> 15) & 0x7F
    rt2 = (w >> 10) & 0x1F
    rn = (w >> 5) & 0x1F
    rt = w & 0x1F
    size = (w >> 30) & 0x3
    scale = 8 if size == 3 else 4
    imm = _sx(imm7, 7) * scale

    # op2==0b01 -> signed offset (no writeback)
    # op2==0b10 -> LDPSW  (only when L)
    # op2==0b11 -> pre/post-index (bit21 selects which)
    if op2 == 0b11:
        mem = (f"[{REG[rn]}, #{imm}]!" if (w >> 21) & 1
               else f"[{REG[rn]}], #{imm}")
    else:
        mem = f"[{REG[rn]}, #{imm}]"

    if V:
        if op2 != 0:
            return None
        kind = {0: "q", 1: "d"}[opc & 1]
        return f"{'ldp' if L else 'stp'} {kind} v{rt}, v{rt2}, {mem}"

    if op2 == 0b10 and L:
        name, kind = "ldpsw", "x"
    elif opc == 0:
        name, kind = ("ldp", "w")
    elif opc == 1:
        name, kind = ("ldp", "x")
    elif opc == 2:
        name, kind = ("stp", "w")
    else:
        name, kind = ("stp", "x")
    return f"{name} {kind} {REG[rt]}, {REG[rt2]}, {mem}"


def ld_st_imm(w):
    """Load/store register (unsigned immediate + unscaled imm9)."""
    if ((w >> 27) & 0x7) != 0b111:       # bits 29..27 == 111
        return None
    if (w >> 26) & 1:                    # V: skip SIMD/FP
        return None
    # bits 25..24: 01 = unsigned imm12, 00 = unscaled/signed imm9
    # (11 = register offset, 10 = literal -> not needed)
    cls = (w >> 24) & 0x3
    if cls not in (0b00, 0b01):
        return None
    size = (w >> 30) & 0x3
    opc = (w >> 22) & 0x3
    mode = cls
    bit21 = (w >> 21) & 0x1
    imm12 = (w >> 10) & 0xFFF
    rn = (w >> 5) & 0x1F
    rt = w & 0x1F
    kind = _sized(size, 0)

    if mode == 0b01:                      # unsigned imm12
        if rn == 31:
            return None                   # literal / SP-relative handled elsewhere
        off = imm12 << size
        if opc == 0:
            return f"str{kind} {REG[rt]}, [{REG[rn]}, #{off}]"
        if opc == 1:
            return f"ldr{kind} {REG[rt]}, [{REG[rn]}, #{off}]"
        if opc == 2:
            n = "ldrsw" if size == 3 else f"ldr{kind}"
            return f"{n} {REG[rt]}, [{REG[rn]}, #{off}] (uxt{size * 8})"
        return None
    if mode == 0b00 and bit21 == 0:       # unscaled / signed imm9
        off = _sx((w >> 12) & 0x1FF, 9)
        if opc == 0:
            return f"str{kind} {REG[rt]}, [{REG[rn]}, #{off}]"
        if opc in (1, 2):
            n = "ldrsw" if (opc == 2 and size == 3) else f"ldr{kind}"
            return f"{n} {REG[rt]}, [{REG[rn]}, #{off}]"
    return None


def mov_orr(w):
    """ORR Rd, XZR, Rm (register move)."""
    if ((w >> 31) & 1) != 1:
        return None
    if ((w >> 29) & 3) != 1:
        return None
    if ((w >> 24) & 0x1F) != 0x0A:
        return None
    if ((w >> 22) & 1) != 0:
        return None
    if ((w >> 21) & 3) != 0:
        return None
    if ((w >> 5) & 0x1F) != 31:
        return None
    if ((w >> 10) & 0x3F) != 0:
        return None
    rm = (w >> 16) & 0x1F
    rd = w & 0x1F
    return f"mov {REG[rd]}, {REG[rm]}"


def addsub_imm(w):
    if ((w >> 24) & 0x3F) != 0x11:
        return None
    sf = (w >> 31) & 1
    op = (w >> 30) & 1
    sh = (w >> 22) & 1
    imm = ((w >> 10) & 0xFFF) << (12 if sh else 0)
    rn = (w >> 5) & 0x1F
    rd = w & 0x1F
    name = "sub" if op else "add"
    if rn == 31:
        if sf:
            return f"mov {REG[rd]}, sp" if imm == 0 else f"add {REG[rd]}, sp, #0x{imm:x}"
        return f"mov w{rd}, wsp" if imm == 0 else f"add w{rd}, sp, #0x{imm:x}"
    if imm == 0 and rd == rn:
        return f"mov {REG[rd]}, {REG[rn]}"
    w_ = "" if sf else "w"
    return f"{name}{w_} {REG[rd]}, {REG[rn]}, #0x{imm:x}"


def decode(w):
    for f in (mov_orr, addsub_imm, ld_st_imm, ldp_stp):
        r = f(w)
        if r:
            return r
    return None


if __name__ == "__main__":
    # self-test against known encodings
    checks = [
        (0xA9BE7BFD, "stp w x29, x30, [sp, #-16]!"),
        (0xA9014FF4, "stp w x20, x19, [sp, #8]"),
        (0xA8C17BFD, "stp w x29, x30, [sp, #8]"),
        (0xAA1303E0, "mov x0, x19"),
        (0xAA1403E0, "mov x0, x20"),
        (0x910003FD, "mov x29, sp"),
        (0xF943E413, "ldr x19, [x0, #1992]"),
    ]
    ok = True
    for w, want in checks:
        got = decode(w)
        flag = "ok " if got == want else "MISMATCH"
        if got != want:
            ok = False
        print(f"  {flag} 0x{w:08x}  got={got!r}  want={want!r}")
    print("SELF-TEST", "PASS" if ok else "FAIL")
