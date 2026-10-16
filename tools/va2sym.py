#!/usr/bin/env python3
"""Map a virtual address to the containing kernel symbol (from .symtab)."""
import sys, bisect
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from a64dec import Elf

e = Elf(sys.argv[1] if len(sys.argv) > 1 else "/tmp/K.elf")
funcs = sorted((v, k) for k, v in e.symbols.items() if v)
addrs = [a for a, _ in funcs]

if len(sys.argv) > 2:
    for tok in sys.argv[2:]:
        q = int(tok, 16) if tok.startswith("0x") else None
        if q is None:
            print(f"sym {tok} = 0x{e.symbols.get(tok, 0):x}" if tok in e.symbols else f"{tok}: not found")
            continue
        i = bisect.bisect_right(addrs, q) - 1
        if i >= 0:
            a, n = funcs[i]
            print(f"0x{q:x} -> {n} (+0x{q - a:x})")
        else:
            print(f"0x{q:x} -> ?")
else:
    for a, n in funcs[:20]:
        print(f"0x{a:x}  {n}")
    print(f"... {len(funcs)} symbols")
