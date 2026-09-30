# Safety Guide - Vivo Y22

## ⚠️ WARNING

This tool modifies kernel memory. Incorrect offsets or KASLR slide can cause:

- Kernel panic (recoverable via reboot)
- Bootloop (recoverable via SP Flash Tool + stock firmware)
- In worst case, hard brick (very rare, but possible)

**Use at your own risk. Authors not responsible for damage.**

## Prerequisites

### Before Running Exploit

1. **Backup**:
   ```bash
   adb shell su -c 'dd if=/dev/block/by-name/boot of=/sdcard/boot_backup.img'
   adb pull /sdcard/boot_backup.img
   ```

2. **Charge**: Battery > 60%

3. **Know Recovery**:
   - SP Flash Tool installed
   - Stock firmware downloaded from vivo.com
   - Know how to enter EDL mode (Vol Down + Power)

4. **Verify Device**:
   - Confirm you have Vivo Y22 V2127, not Y22s Snapdragon variant
   - Check kernel: `adb shell cat /proc/version` should show 4.14.186+
   - Check Android: 12 or 13

## What Exploit Does

- Exploits futex UAF to get kernel R/W
- Overwrites current->cred to init_cred (root)
- Does NOT modify system partition (safe for dm-verity)
- Does NOT unlock bootloader by itself (needs extra step)

## What It Does NOT Do

- Does NOT wipe data
- Does NOT modify boot.img (in-memory only, root lost on reboot unless you install su daemon)
- Does NOT bypass FRP
- Does NOT work on patched kernels (5.15+)

## If Something Goes Wrong

### Kernel Panic During Exploit

- Device will reboot automatically
- Or hold Power 10s to force reboot
- Try again with correct offsets

### Bootloop After Installing su

- Boot to recovery: Power + Vol Up when off
- Wipe cache
- If still bootloop, flash stock boot.img via fastboot or SP Flash Tool:
  ```bash
  fastboot flash boot boot_backup.img
  ```

### Hard Brick (No Boot, No Recovery)

- Use SP Flash Tool + stock firmware
- Enter EDL: Power off, hold Vol Down, connect USB
- Flash full firmware

## Legal

- This is for educational and security research only
- Unlocking bootloader may void warranty
- Check local laws before rooting

## Best Practices

- Run `ghostlock status` first to check device
- Run `ghostlock analyze --vmlinux Kernel.elf` to verify offsets for your firmware
- Use `--offline` demo mode first to understand flow
- Only run on device you own
- Do not distribute rooted firmware without permission

## Support

- XDA: Vivo Y22 forum
- Issues: GitHub issues (provide kernel version, firmware, logs)
- No support for bricked devices due to user error
