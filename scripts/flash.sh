#!/bin/bash
# Ghostlock Vivo Y22 - Flash Helper (for recovery)
# WARNING: This can brick device, use only if you know what you're doing

echo "[!] Flash script for Vivo Y22 - use with caution"
echo "This script helps flash stock firmware via SP Flash Tool or fastboot"
echo ""
echo "Options:"
echo "  1. Flash boot.img via fastboot (if bootloader unlocked)"
echo "  2. Info on SP Flash Tool"
echo ""

read -p "Select option (1/2): " opt

if [ "$opt" == "1" ]; then
    read -p "Path to boot.img: " boot
    if [ -f "$boot" ]; then
        echo "[*] Flashing $boot via fastboot..."
        fastboot flash boot "$boot"
        echo "[✓] Done, rebooting..."
        fastboot reboot
    else
        echo "[!] File not found: $boot"
    fi
elif [ "$opt" == "2" ]; then
    echo ""
    echo "SP Flash Tool steps for Vivo Y22 (MT6769Z):"
    echo "  1. Download SP Flash Tool v5 or v6"
    echo "  2. Download stock firmware for V2127 from vivo.com"
    echo "  3. Open SP Flash Tool, load scatter file from firmware"
    echo "  4. Select Download Only"
    echo "  5. Power off device, hold Vol Down, connect USB"
    echo "  6. Click Download in SP Flash Tool"
    echo "  7. Wait for green check"
    echo ""
    echo "This will restore full stock and fix bootloop"
fi
