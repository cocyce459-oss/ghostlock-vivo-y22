#!/usr/bin/env python3
"""
vmlinux disassembly for offset recovery, on top of the self-tested
a64dec2 decoder. Pure stdlib - no capstone, no binutils cross packages.

  python3 tools/dis.py Kernel.elf --sym get_task_cred
  python3 tools/dis.py Kernel.elf --sym task_blocks_on_rt_mutex --span 0x200
  python3 tools/dis.py Kernel.elf --addr 0xffffff80080b50c0 --span 0x40
"""

import argparse
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a64dec import Elf          # noqa: E402  (symtab + section reader)
from a64dec2 import decode      # noqa: E402  (self-tested instruction decoder)


def owner_map(e):
    import bisect
    funcs = sorted((v, k) for k, v in e.symbols.items() if v)
    return funcs, [a for a, _ in funcs]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("elf")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--sym")
    g.add_argument("--addr")
    ap.add_argument("--span", default="0x80")
    ap.add_argument("--func-size", action="store_true",
                    help="disassemble exactly one symbol (to next symbol)")
    a = ap.parse_args()

    e = Elf(a.elf)
    funcs, addrs = owner_map(e)
    import bisect

    if a.sym:
        if a.sym not in e.symbols:
            print(f"symbol not found: {a.sym}", file=sys.stderr)
            return 1
        start = e.symbols[a.sym]
        span = int(a.span, 0)
        if a.func_size:
            i = bisect.bisect_right(addrs, start)
            nxt = addrs[i] if i < len(addrs) else start + int(a.span, 0)
            span = min(nxt - start, int(a.span, 0))
        label = a.sym
    else:
        start = int(a.addr, 16)
        span = int(a.span, 0)
        label = f"0x{start:x}"

    raw = e.read_va(start, span)
    if not raw:
        print(f"cannot read VA 0x{start:x}", file=sys.stderr)
        return 1

    print(f"; {label} @ 0x{start:x}   ({len(raw)} bytes)\n")
    for i in range(0, len(raw) - 3, 4):
        w = struct.unpack_from("<I", raw, i)[0]
        pc = start + i
        d = decode(w)
        i2 = bisect.bisect_right(addrs, pc) - 1
        fn = funcs[i2][1] if i2 >= 0 and pc - addrs[i2] < 0x4000 else ""
        txt = d if d else ".word 0x%08x" % w
        print(f"  0x{pc:x}:  {w:08x}    {txt:<46} ; {fn}" if fn
              else f"  0x{pc:x}:  {w:08x}    {txt}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
