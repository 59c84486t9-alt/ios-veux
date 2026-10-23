#!/usr/bin/env python3
"""Symbolize transcribed hex wait-panel addresses using the exact unslid CI kernel.
Example: tools/symbolize-veux-waits.py kernel.development.veux addresses.txt
Use --return-address for RA-only input (subtracts one 4-byte AArch64 instruction).
No slide inferred. nm provides symbol+offset; this is not DWARF line attribution.
"""
import argparse
import bisect
from pathlib import Path
import re
import subprocess
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('kernel', type=Path)
p.add_argument('addresses', type=Path)
p.add_argument('--nm', default='nm')
p.add_argument('--return-address', action='store_true')
a = p.parse_args()
raw = subprocess.check_output([a.nm, '-n', '-m', str(a.kernel)], text=True)
symbols = []
for line in raw.splitlines():
    m = re.match(r'^([0-9a-fA-F]{16})\s+\([^,]+,__text\)\s+.*?([^\s]+)$', line)
    if m:
        symbols.append((int(m[1], 16), m[2]))
symbols.sort()
if not symbols:
    p.error('nm returned no text symbols; use the unstripped exact CI kernel')
keys = [v[0] for v in symbols]
for m in re.finditer(r'(?i)\b(?:0x)?(fffffe[0-9a-f]{10})\b', a.addresses.read_text()):
    original = int(m[1], 16)
    pc = original - (4 if a.return_address else 0)
    i = bisect.bisect_right(keys, pc) - 1
    name = f'{symbols[i][1]}+0x{pc-keys[i]:x}' if i >= 0 else 'below text symbols'
    print(f'{original:016x}  {name}')
