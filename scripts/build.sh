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
make android || echo "[!] Android build needs NDK, skipping"
cd "$ROOT_DIR"

echo ""
echo "[✓] Build complete"
ls -lh src/core/exploit/ghostlock_y22* || true
