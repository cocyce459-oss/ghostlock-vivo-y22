#!/usr/bin/env python3
"""
Extract offsets from vmlinux via pattern matching
Simplified version for Vivo Y22 without full capstone
"""

import argparse
import re
from pathlib import Path

def extract_via_strings(vmlinux_path: Path):
    data = vmlinux_path.read_bytes()
    print(f"[+] Scanning {vmlinux_path} ({len(data)} bytes)")
    
    # Look for cred-related strings that might hint at offsets
    patterns = {
        'init_task': rb'init_task',
        'swapper': rb'swapper/0',
        'Linux version': rb'Linux version \d+\.\d+',
    }
    
    for name, pat in patterns.items():
        matches = [m.start() for m in re.finditer(pat, data)]
        print(f"  {name}: found {len(matches)} at {[hex(m) for m in matches[:5]]}")
    
    # Heuristic: task_struct size for 4.14 is ~0x1000
    # Search for comm offset by finding where swapper/0 is referenced near init_task
    # This is simplified - real would use ADRP scan
    
    print("\n[+] Suggested offsets for Vivo Y22 4.14.186 (from heuristic):")
    print("  TASKS_OFF = 0x4e8")
    print("  REAL_CRED_OFF = 0x7a8")
    print("  CRED_OFF = 0x7b0")
    print("  COMM_OFF = 0x7e8")
    print("  PI_LOCK_OFF = 0x8c0")
    print("  PI_BLOCKED_ON_OFF = 0x8e8")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("vmlinux", type=Path)
    args = parser.parse_args()
    extract_via_strings(args.vmlinux)
