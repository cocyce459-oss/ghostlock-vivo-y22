#!/bin/bash
# Ghostlock Vivo Y22 - Build Script
set -e

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "[*] Building Ghostlock Vivo Y22..."

echo "[1/2] Building exploit (host)..."
cd src/core/exploit
make host
echo "[✓] Host binary built"

echo "[2/2] Building exploit (android)..."
# 'make android' now hard-fails when the NDK is missing instead of quietly
# producing an x86 binary under the android name. Surface that honestly
# rather than letting `||` turn a refusal into a cheerful "[!] skipping".
if make android; then
    echo "[✓] Android binary built"
else
    echo ""
    echo "[!] Android build was REFUSED (no NDK). That is expected on a host"
    echo "    without the Android NDK, and is not an error in the host build."
    echo "    You now have a host binary only - it CANNOT run on the device."
    echo "    See docs/COLAB_BUILD.md to build the arm64 binary."
    echo ""
fi
cd "$ROOT_DIR"

echo ""
echo "[✓] Build complete"
ls -lh src/core/exploit/ghostlock_y22* || true
