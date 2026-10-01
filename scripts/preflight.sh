#!/usr/bin/env bash
# Ghostlock Vivo Y22 - Preflight Check
#
# Read-only. Touches no device, changes no files, runs no exploit.
# Exits non-zero if it is NOT safe to proceed to a real device run.
#
# The point of this script: every check here is one a human would
# otherwise skip by pasting the whole README into a terminal.

set -uo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

fail=0
warn=0

ok()   { printf '\033[92m[✓]\033[0m %s\n' "$*"; }
bad()  { printf '\033[91m[✗]\033[0m %s\n' "$*"; fail=$((fail+1)); }
warn() { printf '\033[93m[⚠]\033[0m %s\n' "$*"; warn=$((warn+1)); }

printf '\033[96m'
printf '╔════════════════════════════════════════════════════════════╗\n'
printf '║            GHOSTLOCK VIVO Y22 - PREFLIGHT                  ║\n'
printf '╚════════════════════════════════════════════════════════════╝\033[0m\n\n'

# ---------------------------------------------------------------- 1. tooling
printf '\033[96m[1/4] Toolchain\033[0m\n'
if command -v python3 >/dev/null 2>&1; then
    ok "python3: $(python3 --version 2>&1 | awk '{print $2}')"
else
    bad "python3 not found"
fi

if command -v gcc >/dev/null 2>&1; then
    ok "gcc: $(gcc -dumpversion 2>/dev/null)"
else
    bad "gcc not found (needed for the host build)"
fi

NDK_CC="$(command -v aarch64-linux-android33-clang 2>/dev/null || true)"
if [ -n "$NDK_CC" ]; then
    ok "Android NDK clang: $NDK_CC"
else
    warn "Android NDK clang not on PATH."
    warn "  'make android' will REFUSE to build rather than emit an x86 binary."
    warn "  See docs/COLAB_BUILD.md - Colab sets the NDK up automatically."
fi

# ---------------------------------------------------------- 2. vmlinux check
printf '\n\033[96m[2/4] vmlinux\033[0m\n'
VMLINUX="${VMLINUX:-}"
if [ -z "$VMLINUX" ]; then
    for cand in Kernel.elf vmlinux; do
        [ -f "$cand" ] && { VMLINUX="$cand"; break; }
    done
fi

if [ -z "$VMLINUX" ] || [ ! -f "$VMLINUX" ]; then
    warn "No vmlinux found (looked for ./Kernel.elf and ./vmlinux)."
    warn "  Fetch it with:  python3 tools/fetch_vmlinux.py"
    warn "  Offsets below are UNVERIFIED for whatever kernel your device runs."
    fail=$((fail+1))
else
    ok "Found vmlinux: $VMLINUX"

    magic="$(head -c 4 "$VMLINUX" 2>/dev/null | od -An -tx1 | tr -d ' \n')"
    if [ "$magic" = "7f454c46" ]; then
        ok "ELF magic OK"
    else
        bad "$VMLINUX is not an ELF (magic=$magic) - probably an HTML error page."
        warn "  Re-download with: python3 tools/fetch_vmlinux.py"
    fi

    # Kernel series vs. the series target.h was reconstructed for.
    ver="$(strings -n 10 "$VMLINUX" 2>/dev/null \
            | grep -m1 -oE 'Linux version [0-9]+\.[0-9]+\.[0-9]+' \
            | awk '{print $3}')"
    if [ -n "$ver" ]; then
        series="${ver%%.*}"
        minor="${ver#*.}"; minor="${minor%%.*}"
        key="$series.$minor"
        ok "vmlinux kernel: $ver"
        if [ "$key" = "4.14" ]; then
            ok "Kernel series matches the 4.14 profile in src/core/exploit/target.h"
        else
            bad "KERNEL SERIES MISMATCH: vmlinux is $ver, target.h offsets are for 4.14.x"
            bad "  task_struct layout differs between series. Using these offsets on"
            bad "  this kernel will very likely panic the device."
            warn "  Re-derive offsets for $ver before running on hardware."
        fi
    else
        warn "Could not read a kernel version string out of $VMLINUX"
    fi
fi

# ------------------------------------------------- 3. built binary sanity
printf '\n\033[96m[3/4] Built binaries\033[0m\n'
EXPLOIT=src/core/exploit/ghostlock_y22
if [ -f "$EXPLOIT" ]; then
    ok "Android binary present: $EXPLOIT"
    if command -v file >/dev/null 2>&1; then
        arch="$(file -b "$EXPLOIT" 2>/dev/null)"
        ok "  file: $arch"
        case "$arch" in
            *aarch64*|*ARM\ aarch64*)
                ok "  Architecture is arm64 - correct for the Vivo Y22"
                ;;
            *x86-64*|*x86_64*)
                bad "  Architecture is x86-64. This binary CANNOT run on the device."
                bad "  Rebuild with the NDK: make android"
                ;;
            *)
                warn "  Unrecognised architecture string - verify before pushing."
                ;;
        esac
    fi
else
    warn "No Android binary at $EXPLOIT - run 'make android' (needs the NDK)"
fi

# ------------------------------------------------------------- 4. device
printf '\n\033[96m[4/4] Device\033[0m\n'
if command -v adb >/dev/null 2>&1; then
    devs="$(adb devices 2>/dev/null | awk 'NR>1 && $2=="device" {print $1}')"
    if [ -n "$devs" ]; then
        warn "Device(s) connected:"
        for d in $devs; do
            warn "  $d"
            kver="$(adb -s "$d" shell uname -r 2>/dev/null | tr -d '\r')"
            if [ -n "$kver" ]; then
                kseries="$(echo "$kver" | cut -d. -f1,2)"
                if [ "$kseries" = "4.14" ]; then
                    ok "  $d running $kver (matches 4.14 profile)"
                else
                    bad "  $d running $kver - does NOT match the 4.14 profile offsets"
                fi
            else
                warn "  $d - could not read uname -r"
            fi
        done
    else
        ok "No device connected. Good - nothing device-touching will run."
    fi
else
    ok "adb not installed. Nothing device-touching will run."
fi

# ------------------------------------------------------------- verdict
printf '\n'
if [ "$fail" -gt 0 ]; then
    printf '\033[91m╔════════════════════════════════════════════════════════════╗\033[0m\n'
    printf '\033[91m║  PREFLIGHT FAILED - %d blocking issue(s). DO NOT PROCEED.  ║\033[0m\n' "$fail"
    printf '\033[91m╚════════════════════════════════════════════════════════════╝\033[0m\n\n'
    exit 1
fi

if [ "$warn" -gt 0 ]; then
    printf '\033[93m[⚠] Preflight passed with %d warning(s). Review them above.\033[0m\n\n' "$warn"
    exit 0
fi

printf '\033[92m[✓] Preflight clean.\033[0m\n\n'
exit 0
