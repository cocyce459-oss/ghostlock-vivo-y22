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

echo "[1/4] Checking Python..."
python3 --version || { echo "Python3 required"; exit 1; }

echo "[2/4] Creating venv..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "[✓] venv created"
else
    echo "[✓] venv exists"
fi

echo "[3/4] Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "[✓] Dependencies installed"

echo "[4/4] Building exploit..."
cd src/core/exploit
make host || echo "[!] Host build failed, but continuing"
cd "$ROOT_DIR"

echo ""
echo -e "\033[92m[✓] Setup complete!\033[0m"
echo ""
echo "Next steps:"
echo "  source venv/bin/activate"
echo "  python src/app/main.py --help"
echo "  python src/app/main.py status"
echo "  python src/app/main.py exploit --offline  # demo mode"
echo ""
echo "For real device:"
echo "  1. Download vmlinux: python tools/fetch_vmlinux.py"
echo "  2. Analyze: python tools/analyze_vmlinux.py --vmlinux Kernel.elf -v"
echo "  3. Connect Vivo Y22 via adb"
echo "  4. Run: python src/app/main.py exploit"
echo ""
