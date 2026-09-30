# Troubleshooting

## Common Issues

### 1. "No device connected"

- Ensure adb installed: `adb --version`
- Enable USB Debugging in Developer Options
- Allow USB debugging on phone popup
- Try `adb kill-server && adb start-server`

### 2. "KASLR leak failed"

- Vivo Y22 strips kallsyms, so leak may fail
- Exploit will use fallback slide 0 and try to verify via comm
- If still fails, manually find slide:
  - On device: `adb shell cat /proc/self/maps | grep vsyscall`
  - Use that to calculate slide
  - Or brute-force: try slide values 0x0, 0x200000, 0x400000, etc (2MB aligned)

### 3. "Failed to find current task"

- task_struct offsets mismatch
- Try alternative offsets:
  - tasks: 0x448, 0x4c0, 0x4e8, 0x5a0
  - cred: 0x6b0, 0x788, 0x7a8, 0x7b0
- Run `python3 tools/analyze_vmlinux.py --vmlinux Kernel.elf -v` to get exact

### 4. "Exploit returns but no root"

- Check if SELinux blocking: `adb shell getenforce` -> Enforcing
- After cred overwrite, you may need to setenforce 0 via kernel write
- Or use su daemon that bypasses SELinux

### 5. Build fails

- Install deps: `sudo apt install gcc make`
- For Android: Install NDK, set `aarch64-linux-android33-clang` in PATH
- Host build should work without NDK: `make host`

### 6. "vmlinux analysis shows no init_task"

- Ensure file is actual vmlinux, not gzipped
- Try: `file Kernel.elf` should show ELF 64-bit
- If gzipped, gunzip first
- Use `tools/fetch_vmlinux.py` to download correctly

### 7. Bootloop after root

- See docs/safety-guide.md recovery
- Flash stock boot.img

## Debug Mode

```bash
# Verbose analyze
python3 tools/analyze_vmlinux.py --vmlinux Kernel.elf --device vivo-y22 -v

# Host exploit with strace
strace ./src/core/exploit/ghostlock_y22_host

# ADB logcat during exploit
adb logcat -c && adb shell /data/local/tmp/ghostlock_y22 & adb logcat | grep -i "ghost\|futex\|panic"
```

## Getting Help

Provide:

- Device model: `adb shell getprop ro.product.model`
- Android version: `adb shell getprop ro.build.version.release`
- Kernel version: `adb shell cat /proc/version`
- Firmware: `adb shell getprop ro.build.version.incremental`
- Exploit output
- vmlinux analysis output

Open issue on GitHub with these details.

## Known Working Setup

- Host: Ubuntu 22.04, Python 3.10+, gcc 11+
- Device: Vivo Y22 V2127, PD2226F_EX_A_12.0.8.0, Android 12, Kernel 4.14.186+
- ADB: Platform-tools 33+
- vmlinux: From Google Drive link, ~32MB ELF
