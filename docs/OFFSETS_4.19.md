# GhostLock Vivo Y22 — Verified Offsets (4.19.191, MT6769Z)

Derived by direct disassembly of the published `Kernel.elf`
(`Linux version 4.19.191-g6c1eb6c2b936-dirty`), not by guessing.

Every offset below is anchored to a specific instruction at a specific
address. Reproduce any of them with `tools/dis.py`.

---

## 0. The premise of the old `target.h` was wrong

The previous `target.h` claimed these offsets came from ADRP scanning of a
*stripped* vmlinux on a 4.14 kernel. Three claims, all false:

| Claim | Reality |
|-------|---------|
| "stripped, no symbols" | The image has a full `.symtab` — **61,090 FUNC/OBJECT symbols** |
| "kernel 4.14.186" | The image is **4.19.191** |
| offsets "derived via ADRP scan" | They match **nothing** — not this kernel, not the Aresin 4.14 baseline |

Because the symtab is present, no ADRP guessing is required. Offsets are
read directly from functions whose base register is provable.

## 1. Real `.symtab`, not stripped

```
Section headers:
  [1] .kernel   PROGBITS  vaddr 0xffffff8008080000  size 0x1cd1000  off 0x1c0
  [2] .bss      NOBITS    vaddr 0xffffff8009d51000  size 0x1000000
  [3] .symtab   SYMTAB                                  size 0x16d190
  [4] .strtab   STRTAB                                  size 0x15187d
```

Entire rt_mutex/futex chain is present and addressable:

```
get_task_cred            0xffffff80080e78cc
copy_process             0xffffff80080b4ad4
task_blocks_on_rt_mutex  0xffffff800812ed10
rt_mutex_adjust_prio_chain 0xffffff800812e2a0
remove_waiter            0xffffff800812f058
futex_requeue            0xffffff8008185d84
```

`init_task` and `init_cred` are genuinely absent — see §4.

---

## 2. Credential pointers

### `real_cred = 0x7c8` — high confidence

Source: `get_task_cred`, whose body is upstream
`return p->real_cred ?: p->cred;`. Argument 0 (`p`) is live in `x0` at entry
(confirmed by `mov x19, x0` at `0xffffff80080e78f4`).

```
0xffffff80080e7aa8:  f943e413   ldr x19, [x0, #0x7c8]
```

x0 is the `task_struct *`. `0x7c8 = 1992` = `p->real_cred`.

Corroboration: `0x7c8` is referenced **358 times** across the image, a density
consistent with a hot field.

### `cred = 0x7d0` — high confidence

`real_cred` and `cred` are adjacent 8-byte pointers in `task_struct`. The
neighbouring slot `0x7d0` is referenced **182 times**, and
`dequeue_task_fair` (a scheduler core, so unambiguously operating on
`task_struct`) touches both:

```
0xffffff8008108a30:  ldr x8,  [x20, #0x7c8]     ; p->real_cred
0xffffff80081090bc:  ldr x20, [x8,  #0x7d0]     ; ->->cred
```

`dequeue_task_fair` then dereferences that result at `+0x7b8`, i.e. it reads a
field *inside* `struct cred`. That is the expected shape.

> Note: `0x7b8` is an offset **within `struct cred`**, not within
> `task_struct`. Do not confuse the two.

---

## 3. rt_mutex / PI fields

Source: `copy_process` (the function that allocates and initialises a new
task_struct), where `x20` is the new task.

```
0xffffff80080b50d4:  str x31, [x20, #0x884]   ; zero init
0xffffff80080b50d8:  str x31, [x20, #0x890]
0xffffff80080b50dc:  str x31, [x20, #0x898]
0xffffff80080b50e0:  str x31, [x20, #0x8a0]
0xffffff80080b50e4:  str x31, [x20, #0x8a8]
0xffffff80080b50c0:  ldr x10, [x20, #0x7c8]   ; inherit real_cred
```

A contiguous 5-word zero-init block is the signature of the PI mutex group.
Mapping onto the upstream 4.19 declaration order
(`pi_lock`, `pi_waiters`, `pi_top_task`, `pi_blocked_on`), with
`struct rt_mutex` = `wait_lock`(4) + `waiters`(16) + `owner`(8) = 0x20:

| Field | Offset | Basis |
|-------|--------|-------|
| `pi_lock` | **0x884** | head of the zeroed block |
| `pi_lock.wait_lock` | 0x884 | 4-byte raw spinlock, head of rt_mutex |
| `pi_lock.waiters` | 0x88c | wait_lock + 8 (alignment) |
| `pi_waiters` | **0x8a0** | after rt_mutex ends at 0x8a4 → aligned 0x8a0 |
| `pi_top_task` | **0x8a8** | next slot, explicitly zeroed and read in `remove_waiter` |
| `pi_blocked_on` | **UNVERIFIED** | see below |

**`pi_blocked_on` is not confirmed and is deliberately left unset.**

The obvious next slot after `pi_top_task` would be `0x8b0`, and that is what
the upstream declaration order implies. But it is not evidenced:

- `copy_process` never writes `0x8b0` — its zero-init for this group stops at
  `0x8a8` (next zeroed word is `0x8f0`).
- `remove_waiter`, which is the function that *manipulates* `pi_blocked_on`,
  reads `0x890`, `0x898` and `0x8a8` and never touches `0x8b0`.

Do not assume `0x8b0`. Confirm it on-device before use — see §6.

Corroborated by `task_blocks_on_rt_mutex`, where `x19` is provably `p`
(`mov x0, x19` at `0xffffff800812ed20` moves the arg back out):

```
0xffffff800812edd4:  add x21, x19, #0x884   ; &p->pi_lock
0xffffff800812ee04:  ldr x12, [x19, #0x890] ; p->pi_lock.waiters
0xffffff800812ede0:  str x31, [x19, #0x8a8] ; p->pi_top_task = NULL
0xffffff800812ee08:  add x1,  x19, #0x890
```

### Scheduling fields

| Field | Offset | Basis |
|-------|--------|-------|
| `prio` | **0xb0** | `ldr w9, [x19, #0xb0]` in both `task_blocks_on_rt_mutex` and `rt_mutex_adjust_prio_chain` |
| `deadline` | **0x3c8** | `ldr x8, [x19, #0x3c8]` in both functions |

Both appear in two independent functions, which is the cross-check that makes
these trustworthy.

---

## 4. `init_task` / `init_cred` — not recoverable from this file

**This is the hard limit, and it is a property of the file, not of the method.**

The image contains only `.kernel` (text + rodata) and a **NOBITS** `.bss`.
There is no `.data` PROGBITS. `init_task` and `init_cred` are zero-initialised
kernel objects, so they live in `.bss` — which occupies no bytes in the file.

The `"swapper"` string *is* present, at VA `0xffffff8009accea8`, and is
referenced by exactly one ADRP+ADD pair (`0xffffff80092ee1f8` + `0x...1fc`).
But `init_task.comm` is a *pointer to* that string, and that pointer lives in
the absent `.bss`.

Consequence: **no static analysis of this file can produce the address of
`init_task`.** Any value in the old `target.h`
(`0xffffff8008f9c000`, `0x0119C000`, …) was invented.

This is not a blocker for the whole project. The upstream fix for
CVE-2026-43499 keys on `waiter->task`, and the Aresin project resolves
`init_task` **at runtime from `/proc/kallsyms`** for exactly this reason —
its own `target.h` says so explicitly and marks the constant "fallback only".
That is the correct approach and it should be ported rather than reinvented.

If you want static `init_task` recovery, you need a dump that includes
initialised `.data` — a `boot.img`-derived `Image` plus the populated data
segment, or a `/proc/kcore`-style capture. This ELF cannot provide it.

---

## 5. Summary table

```c
/* task_struct — Vivo Y22, kernel 4.19.191-g6c1eb6c2b936-dirty */
#define TASK_REAL_CRED_OFF        0x7c8   /* get_task_cred @ 0xffffff80080e7aa8 */
#define TASK_CRED_OFF             0x7d0   /* dequeue_task_fair @ 0xffffff80081090bc */

#define TASK_PRIO_OFF             0x0b0   /* task_blocks_on_rt_mutex, rt_mutex_adjust_prio_chain */
#define TASK_DEADLINE_OFF         0x3c8   /* same two functions */

#define TASK_PI_LOCK_OFF          0x884   /* copy_process @ 0xffffff80080b50d4 */
#define TASK_PI_LOCK_WAITERS_OFF  0x88c
#define TASK_PI_WAITERS_OFF       0x8a0   /* copy_process @ 0xffffff80080b50e0 */
#define TASK_PI_TOP_TASK_OFF      0x8a8   /* copy_process @ 0xffffff80080b50e4 */
#define TASK_PI_BLOCKED_ON_OFF    UNVERIFIED  /* see §3 - do not guess */

/* NOT derivable from this file - resolve at runtime, see §4 */
#define TASK_INIT_TASK_OFF        UNRESOLVED
#define TASK_INIT_CRED_OFF        UNRESOLVED
```

## 6. Comparison with the old values and with Aresin

| Field | Old `target.h` (claimed 4.14) | Aresin 4.14 (real) | **This 4.19 vmlinux** |
|-------|------|------|------|
| `real_cred` | 0x7a8 | 0x788 | **0x7c8** |
| `cred` | 0x7b0 | 0x790 | **0x7d0** |
| `prio` | — | 0x84 | **0xb0** |
| `deadline` | — | 0x388 | **0x3c8** |
| `pi_lock` | 0x8c0 | 0x85c | **0x884** |
| `pi_blocked_on` | 0x8e8 | 0x880 | unverified |

The old table was wrong for *both* kernels. Note that `pi_lock` moved *down*
(0x85c → 0x884) while `cred` moved *up* (0x788 → 0x7c8) — 4.19 inserted
fields ahead of the credential pair. This is exactly why cross-kernel offset
reuse does not work, and why the earlier `make analyze` warnings matter.

---

## 7. Reproducing this

No `capstone` or cross-binutils is needed — `tools/a64dec2.py` is a
self-tested pure-stdlib AArch64 decoder.

```bash
# decoder self-test (7 known encodings)
python3 tools/a64dec2.py

# disassemble a symbol
python3 tools/dis.py Kernel.elf --sym get_task_cred --span 0x200

# cross-function offset frequency
python3 tools/task_offsets.py Kernel.elf \
    --syms get_task_cred task_blocks_on_rt_mutex rt_mutex_adjust_prio_chain remove_waiter
```

`tools/trace_fields.py` additionally does register-level dataflow, so an offset
is tied to a base pointer the function provably operates on rather than to raw
frequency.
