#!/bin/bash
# Ghostlock Vivo Y22 - Setup Script
set -e

echo -e "\033[96m"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║              GHOSTLOCK VIVO Y22 SETUP                      ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "\033[0m"

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "[*] Root dir: $ROOT_DIR"

echo "[1/3] Checking Python..."
python3 --version || { echo "Python3 required"; exit 1; }

echo "[2/3] Creating venv..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "[✓] venv created"
else
    echo "[✓] venv exists"
fi

echo "[3/3] Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "[✓] Dependencies installed"

# NOTE: Building is intentionally NOT done here.
# Previously setup.sh ran `make host`, and `make all` then ran build.sh
# which built the same target again. Build is now a separate explicit step:
#     make build
cd "$ROOT_DIR"

echo ""
echo -e "\033[92m[✓] Setup complete (deps only - nothing was built)\033[0m"
echo ""
echo "Next steps:"
echo "  make build                      # build host (+ android if NDK present)"
echo "  source venv/bin/activate"
echo "  python src/app/main.py --help"
echo "  python src/app/main.py status"
echo "  python src/app/main.py exploit --offline  # demo mode, no device"
echo ""
echo "Building on Google Colab (CPU-only) instead? See docs/COLAB_BUILD.md"
echo ""
echo "Before touching a real device:"
echo "  1. Fetch vmlinux:   python tools/fetch_vmlinux.py"
echo "  2. Analyze it:      make analyze VMLINUX=Kernel.elf"
echo "  3. Run preflight:   make preflight"
echo "  4. Then, and only then, connect the device."
echo ""
