#!/usr/bin/env python3
"""
Ghostlock - Disassembly Helper for stripped vmlinux
Capstone-based ADRP decoder for Vivo Y22
"""

import sys
from pathlib import Path

try:
    from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
except ImportError:
    print("Install capstone: pip install capstone")
    sys.exit(1)

def decode_adrp(data: bytes, base_addr: int):
    md = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
    md.detail = True
    for insn in md.disasm(data, base_addr):
        if insn.mnemonic == 'adrp':
            print(f"{hex(insn.address)}: {insn.mnemonic} {insn.op_str} | bytes: {insn.bytes.hex()}")
            # Decode imm
            # ADRP encoding: check ARM manual
            # For quick: capstone already gives target in op_str
            # But we can also manually decode
            # Instruction: 1 00 1 immlo(2) 00000 immhi(19) Rd(5)
            # imm = SignExtend(immhi:immlo, 21) << 12
            # page = PC_page + imm
            pass

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <binary> [offset] [size]")
        sys.exit(1)
    
    path = Path(sys.argv[1])
    offset = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0
    size = int(sys.argv[3], 0) if len(sys.argv) > 3 else 0x1000
    
    data = path.read_bytes()[offset:offset+size]
    print(f"Decoding {len(data)} bytes from {path} offset {hex(offset)} as ARM64, base 0xffffff8008080000")
    decode_adrp(data, 0xffffff8008080000 + offset)
