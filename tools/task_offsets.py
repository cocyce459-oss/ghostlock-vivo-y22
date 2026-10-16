#!/usr/bin/env python3
"""
Cross-function task_struct offset recovery for the rt_mutex/futex PI path.

Technique: the same task_struct field is touched by several unrelated kernel
functions, so an offset that shows up repeatedly across independent functions
is far more likely to be a real field than a coincidence inside one routine.

For every symbol in --syms, decode a window and histogram the
`[Xn, #imm]` displacements grouped by base register.

  python3 tools/task_offsets.py /tmp/K.elf \
      --syms task_blocks_on_rt_mutex rt_mutex_adjust_prio_chain remove_waiter \
      --span 0x300
"""

import argparse
import struct
import sys
from collections import defaultdict

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from a64dec import Elf, ldst, REGS  # noqa: E402


def scan(elf, va, span):
    """yield (base_reg, offset) for every [Xn,#imm] in the window"""
    raw = elf.read_va(va, span)
    if not raw:
        return
    for i in range(0, len(raw) - 3, 4):
        word = struct.unpack_from("<I", raw, i)[0]
        d = ldst(word)
        if d:
            _txt, off, rt, rn, _st = d
            yield (va + i, rn, off, _txt)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("elf")
    ap.add_argument("--syms", nargs="+", required=True)
    ap.add_argument("--span", type=lambda s: int(s, 0), default=0x300)
    ap.add_argument("--top", type=int, default=40)
    ap.add_argument("--detail", metavar="SYM", help="show all hits for one symbol")
    a = ap.parse_args()

    e = Elf(a.elf)
    missing = [s for s in a.syms if s not in e.symbols]
    if missing:
        print(f"[!] not in symtab: {', '.join(missing)}\n")

    per_sym = {}
    freq = defaultdict(set)          # (reg, off) -> {syms}
    counts = defaultdict(int)

    for s in a.syms:
        if s not in e.symbols:
            continue
        hits = list(scan(e, e.symbols[s], a.span))
        per_sym[s] = hits
        for _va, rn, off, _t in hits:
            if off == 0:
                continue
            key = (REGS[rn], off & 0xFFFFFFFFFFFFFFFF)
            freq[key].add(s)
            counts[key] += 1

    if a.detail:
        s = a.detail
        print(f"; {s} @ 0x{e.symbols[s]:x}\n")
        for va, rn, off, t in per_sym.get(s, []):
            print(f"  0x{va:x}  [{REGS[rn]}, #0x{off & 0xFFFFFFFFFFFFFFFF:x}]   {t}")
        return 0

    print(f"{'base':>6}  {'off':>8}  {'hits':>5}  {'#funcs':>6}  seen in")
    print("-" * 78)
    for (reg, off), syms in sorted(
            freq.items(), key=lambda kv: (-len(kv[1]), -counts[kv[0]], kv[0][1])):
        if len(syms) < 2 and off > 0x40:
            continue
        print(f"{reg:>6}  0x{off:>6x}  {counts[(reg, off)]:>5}  {len(syms):>6}  "
              f"{', '.join(sorted(s[:22] for s in syms))[:44]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
