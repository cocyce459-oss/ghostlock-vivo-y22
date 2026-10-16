#!/usr/bin/env python3
"""
Re-derive the Ghostlock Vivo Y22 task_struct offsets from a vmlinux and check
them against docs/OFFSETS_4.19.md.

This is a regression test for the offset table. If it ever fails, the table no
longer matches the kernel image and must not be used on a device.

  python3 tools/verify_offsets.py Kernel.elf
"""

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a64dec import Elf  # noqa: E402

# The table from docs/OFFSETS_4.19.md, with the evidence that produced it.
EXPECTED = {
    "real_cred": 0x7c8,
    "cred": 0x7d0,
    "prio": 0xb0,
    "deadline": 0x3c8,
    "pi_lock": 0x884,
    "pi_waiters": 0x8a0,
    "pi_top_task": 0x8a8,
}

# Deliberately NOT asserted: pi_blocked_on.
# The upstream declaration order implies 0x8b0, but that value is not
# evidenced in the image - copy_process never zero-inits it and
# remove_waiter never reads it. See docs/OFFSETS_4.19.md section 3.
# Asserting it here would launder a guess into a "verified" table.

# (function, expected VA) pairs the table is anchored to.
ANCHORS = {
    "get_task_cred": 0xffffff80080e78cc,
    "copy_process": 0xffffff80080b4ad4,
    "task_blocks_on_rt_mutex": 0xffffff800812ed10,
    "rt_mutex_adjust_prio_chain": 0xffffff800812e2a0,
    "remove_waiter": 0xffffff800812f058,
}


def u32_imm12(w):
    """Return (offset, rt, rn) for unsigned-imm12 ldr/str, else None."""
    if ((w >> 27) & 7) != 7 or (w >> 26) & 1:
        return None
    if ((w >> 24) & 3) != 1 or ((w >> 5) & 0x1F) == 31:
        return None
    size = (w >> 30) & 3
    return (((w >> 10) & 0xFFF) << size, w & 0x1F, (w >> 5) & 0x1F)


def scan_offsets(e, sym, want_off, want_reg=None, min_span=0x400):
    """Find `[reg, #want_off]` loads/stores near one symbol; return hit addresses.

    NOTE: symbol sizes are 0 in this vmlinux, and the symtab is *heavily*
    overlapping (get_task_cred's "next" symbol starts only 0x7c bytes later,
    yet the function body runs for 0x200+). So the distance to the next symbol
    is NOT a reliable upper bound. Use a fixed window and never truncate
    below min_span, otherwise real accesses get missed.
    """
    if sym not in e.symbols:
        return None
    start = e.symbols[sym]
    span = 0x2000
    raw = e.read_va(start, span)
    if not raw:
        return []
    hits = []
    for i in range(0, len(raw) - 3, 4):
        d = u32_imm12(struct.unpack_from("<I", raw, i)[0])
        if d and d[0] == want_off:
            if want_reg is None or d[2] == want_reg:
                hits.append(start + i)
    return hits


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "Kernel.elf"
    if not Path(path).exists():
        print(f"[!] not found: {path}")
        return 2
    e = Elf(path)
    print(f"; verifying offset table against {path}\n")

    fails = 0

    print("== anchors ==")
    for sym, va in ANCHORS.items():
        got = e.symbols.get(sym)
        if got is None:
            print(f"  MISSING  {sym}")
            fails += 1
        elif got != va:
            print(f"  MOVED    {sym}: table says 0x{va:x}, image has 0x{got:x}")
            fails += 1
        else:
            print(f"  ok       {sym} @ 0x{va:x}")

    print("\n== field evidence ==")
    # real_cred: get_task_cred loads it via x0 (the task arg)
    h = scan_offsets(e, "get_task_cred", EXPECTED["real_cred"], want_reg=0)
    ok = bool(h)
    print(f"  {'ok  ' if ok else 'FAIL'} real_cred 0x{EXPECTED['real_cred']:x} "
          f"in get_task_cred via x0: {', '.join(hex(a) for a in h[:2]) if h else 'not found'}")
    fails += 0 if ok else 1

    # the rest: copy_process writes the whole PI block
    for fld in ("pi_lock", "pi_waiters", "pi_top_task"):
        off = EXPECTED[fld]
        h = scan_offsets(e, "copy_process", off)
        ok = bool(h)
        print(f"  {'ok  ' if ok else 'FAIL'} {fld:<13} 0x{off:x} zeroed in copy_process"
              f": {', '.join(hex(a) for a in h[:1]) if h else 'not found'}")
        fails += 0 if ok else 1

    # remove_waiter must read pi_top_task too (independent cross-check)
    h = scan_offsets(e, "remove_waiter", EXPECTED["pi_top_task"])
    ok = bool(h)
    print(f"  {'ok  ' if ok else 'FAIL'} pi_top_task 0x{EXPECTED['pi_top_task']:x} "
          f"read in remove_waiter: {', '.join(hex(a) for a in h[:1]) if h else 'not found'}")
    fails += 0 if ok else 1

    # prio / deadline must appear in two independent rt_mutex functions
    for fld, syms in (("prio", ["task_blocks_on_rt_mutex", "rt_mutex_adjust_prio_chain"]),
                      ("deadline", ["task_blocks_on_rt_mutex", "rt_mutex_adjust_prio_chain"])):
        off = EXPECTED[fld]
        found = [s for s in syms if scan_offsets(e, s, off)]
        ok = len(found) >= 2
        print(f"  {'ok  ' if ok else 'FAIL'} {fld:<13} 0x{off:x} present in "
              f"{len(found)}/2 functions: {', '.join(found) or 'none'}")
        fails += 0 if ok else 1

    # cred: adjacent to real_cred, touched by the scheduler
    h = scan_offsets(e, "dequeue_task_fair", EXPECTED["cred"])
    ok = bool(h)
    print(f"  {'ok  ' if ok else 'FAIL'} cred       0x{EXPECTED['cred']:x} "
          f"in dequeue_task_fair: {', '.join(hex(a) for a in h[:1]) if h else 'not found'}")
    fails += 0 if ok else 1

    print("\n== unresolved (by design) ==")
    for s in ("init_task", "init_cred"):
        if s in e.symbols:
            print(f"  {s} IS in symtab @ 0x{e.symbols[s]:x} - table should be updated")
        else:
            print(f"  {s}: absent from symtab, lives in .bss (NOBITS) - resolve at runtime")

    print()
    if fails:
        print(f"FAILED: {fails} check(s) did not match. Do not run on a device.")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
