# Compatibility

## Vivo Y22 Variants

| Model | SoC | Kernel | Android | Status |
|-------|-----|--------|---------|--------|
| V2127 (Y22) | MT6769Z Helio G85 | 4.14.186+ | 12/13 | ✅ Supported (primary) |
| V2127 (Y22s) | Snapdragon 680 | 4.19+ | 12/13 | ⚠️ Likely, needs offset update |
| V2111 (Y21) | MT6765 Helio G70 | 4.14.186+ | 11/12 | ⚠️ Likely |

## Firmware

- PD2226F_EX_A_12.0.8.0 - ✅ Vulnerable, tested
- PD2226F_EX_A_13.0.12.0 - ⚠️ Likely vulnerable, needs verification
- Any 4.14.186 with CONFIG_FUTEX_PI=y - Likely vulnerable

## Requirements

- Kernel <5.15 (Vivo Y22 4.14 is vulnerable)
- CONFIG_FUTEX_PI=y (Vivo stock: yes)
- Ability to run native binary via adb or app (adb shell)

## Not Compatible

- Kernel 5.15+ with fix
- Devices with kallsyms fully disabled AND no /proc/self/maps leak AND no timing side-channel (rare)
- iOS, non-Android
- Snapdragon Y22s may need different offsets (task_struct differs)

## Testing Matrix

We test on:

- Host: Linux x86_64, gcc, make
- Device: Vivo Y22 V2127 via adb (when available) or offline demo

If you test on other firmware, please report offsets via PR.
