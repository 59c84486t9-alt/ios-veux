#!/usr/bin/env python3
"""Execute the actual stage-0106 stackless AArch64 renderer under Unicorn.
Usage: python test-veux-bitdump.py APPLIED_XNU_TREE OUT_DIR
Requires unicorn, pyelftools, clang and aarch64-elf binutils in PATH.
"""
import re
import struct
import subprocess
import sys
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM64, UC_MODE_ARM
from unicorn.arm64_const import UC_ARM64_REG_X0, UC_ARM64_REG_X1, UC_ARM64_REG_X2, UC_ARM64_REG_X3, UC_ARM64_REG_X30, UC_ARM64_REG_SP
root, out = map(Path, sys.argv[1:])
out.mkdir(parents=True, exist_ok=True)
src = (root / 'osfmk/arm64/start.s').read_text()
src = src[src.index('/* Leaf renderers:'):].rsplit('#endif', 1)[0]
src = re.sub(r'LEXT\((\w+)\)', r'\1:', src)
src = re.sub(r'EXT\((\w+)\)', r'\1', src)
src = re.sub(r'adrp (x\d+), (\w+)@page', r'adrp \1, \2', src)
src = re.sub(r'(\w+)@pageoff', r':lo12:\1', src)
src += '\n.align 3\nveux_stage_fb: .quad 0x2000000\n'
(out/'renderer.S').write_text(src)
subprocess.run(['clang','--target=aarch64-none-elf','-c',str(out/'renderer.S'),'-o',str(out/'renderer.o')],check=True)
subprocess.run(['aarch64-elf-ld','-Ttext=0x100000','-Tdata=0x110000',str(out/'renderer.o'),'-o',str(out/'renderer.elf')],check=True)
u=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
u.mem_map(0x100000,0x20000)
with (out/'renderer.elf').open('rb') as f:
 elf=ELFFile(f)
 for seg in elf.iter_segments():
  if seg['p_type']=='PT_LOAD': u.mem_write(seg['p_vaddr'],seg.data())
 symbols={s.name:s['st_value'] for s in elf.get_section_by_name('.symtab').iter_symbols()}
base=0x2000000; size=0xc00000
u.mem_map(base,size)
u.mem_write(base,b'\x55'*size)
def run(name,values):
 for reg,v in zip([UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X2,UC_ARM64_REG_X3],values):u.reg_write(reg,v)
 u.reg_write(UC_ARM64_REG_X30,0x11f000)
 u.reg_write(UC_ARM64_REG_SP,0) # Any stack access faults: no stack mapped.
 u.emu_start(symbols[name],0x11f000,count=1000000)
 assert u.reg_read(UC_ARM64_REG_SP)==0
values=[0x8000000000000001,0xfffffe000748c488,0,0xffffffffffffffff]
run('veux_fault_dump',values)
expected=bytearray(b'\x55'*size)
for y,value in zip([2120,2144,2168,2192],values):
 for bit in range(64):
  pixel=struct.pack('<I',0xffffffff if value & (1<<(63-bit)) else 0xff202020)
  for yy in range(y,y+16):
   at=yy*4320+(28+16*bit)*4
   expected[at:at+64]=pixel*16
assert bytes(u.mem_read(base,size))==expected, 'render, MSB order, geometry or bounds mismatch'
run('veux_fault_dump',[1,2,3,4])
assert bytes(u.mem_read(base,size))==expected, 'later panic overwrote first fault'
run('veux_bit_row',[0x5,1800])
for bit in range(64):
 want=0xffffffff if 0x5 & (1<<(63-bit)) else 0xff202020
 assert struct.unpack('<I',u.mem_read(base+1800*4320+(28+bit*16)*4,4))[0]==want
print('PASS: actual AArch64 renderer, unmapped stack, 64-bit MSB order, all four rows, exact write bounds, first-fault retention and timer row')
