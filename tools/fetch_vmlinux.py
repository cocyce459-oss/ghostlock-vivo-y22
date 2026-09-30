#!/usr/bin/env python3
"""
Ghostlock - Fetch vmlinux from Google Drive
Uses same method as Arena fetch_page tool but via Python for local use

The vmlinux for Vivo Y22 is at:
https://drive.google.com/file/d/1yX1l9SKl-oFFru-prRG-UmCiLfC-Y8MN/view?usp=drivesdk

Direct download link (via drive.usercontent):
https://drive.usercontent.google.com/download?id=1yX1l9SKl-oFFru-prRG-UmCiLfC-Y8MN&export=download

This script attempts to download via requests, with fallback to gdown
"""

import sys
from pathlib import Path
import argparse

def fetch_via_requests(file_id: str, output: Path):
    try:
        import requests
    except ImportError:
        print("[!] requests not installed, pip install requests")
        return False
    
    url = f"https://drive.usercontent.google.com/download?id={file_id}&export=download"
    print(f"[+] Fetching {url}")
    print(f"[+] Output: {output}")
    
    # For large files, Drive needs confirmation token
    session = requests.Session()
    response = session.get(url, stream=True)
    
    # Check for virus scan warning page
    if "Virus scan warning" in response.text or "Google Drive - Virus scan warning" in response.text:
        print("[!] Virus scan warning page, need to parse confirm token")
        # Try to extract confirm token
        import re
        m = re.search(r'confirm=([0-9A-Za-z-_]+)', response.text)
        if m:
            token = m.group(1)
            url = f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm={token}"
            print(f"[+] Retrying with token: {token}")
            response = session.get(url, stream=True)
    
    # Save
    total = 0
    with open(output, 'wb') as f:
        for chunk in response.iter_content(chunk_size=32768):
            if chunk:
                f.write(chunk)
                total += len(chunk)
                if total % (10*1024*1024) == 0:
                    print(f"  Downloaded {total / 1024 / 1024:.1f} MB")
    
    print(f"[✓] Downloaded {total} bytes to {output}")
    # Check ELF magic
    with open(output, 'rb') as f:
        magic = f.read(4)
        if magic == b'\x7fELF':
            print(f"[✓] Valid ELF file")
            return True
        else:
            print(f"[!] Not ELF, magic: {magic.hex()}, maybe HTML error page")
            print(f"First 500 bytes:")
            with open(output, 'rb') as f:
                print(f.read(500)[:500])
            return False

def fetch_via_gdown(file_id: str, output: Path):
    try:
        import gdown
    except ImportError:
        print("[!] gdown not installed, pip install gdown")
        return False
    
    url = f"https://drive.google.com/uc?id={file_id}"
    print(f"[+] Fetching via gdown: {url}")
    gdown.download(url, str(output), quiet=False)
    
    # Check
    if output.exists():
        with open(output, 'rb') as f:
            magic = f.read(4)
            if magic == b'\x7fELF':
                print(f"[✓] Valid ELF via gdown")
                return True
    return False

def main():
    parser = argparse.ArgumentParser(description="Fetch Vivo Y22 vmlinux from Google Drive")
    parser.add_argument("--file-id", default="1yX1l9SKl-oFFru-prRG-UmCiLfC-Y8MN", help="Google Drive file ID")
    parser.add_argument("--output", "-o", type=Path, default=Path("Kernel.elf"), help="Output path")
    args = parser.parse_args()
    
    print(f"Ghostlock Vivo Y22 vmlinux fetcher")
    print(f"File ID: {args.file_id}")
    print(f"Expected: ELF 64-bit ARM64, ~32MB, Kernel 4.14.186+")
    print()
    
    # Try requests first
    success = fetch_via_requests(args.file_id, args.output)
    if not success:
        print("[!] Requests method failed, trying gdown...")
        success = fetch_via_gdown(args.file_id, args.output)
    
    if success:
        print(f"\n[✓] Success! vmlinux at {args.output}")
        print(f"Next: python3 tools/analyze_vmlinux.py --vmlinux {args.output} --device vivo-y22 -v")
    else:
        print(f"\n[✗] Failed to fetch")
        print(f"Manual download: https://drive.google.com/file/d/{args.file_id}/view")
        print(f"Then place as {args.output}")
        sys.exit(1)

if __name__ == "__main__":
    main()
