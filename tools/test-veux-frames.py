#!/usr/bin/env python3
"""Actual FP walker on synthetic saved stacks; no live-thread or AT coverage."""
from pathlib import Path
import subprocess
import sys
root,out=map(Path,sys.argv[1:]);out.mkdir(parents=True,exist_ok=True)
s=(root/'osfmk/arm64/veux_early.c').read_text()
code=s.split('/* BEGIN VEUX FRAME CORE',1)[1].split('*/',1)[1].split('/* END VEUX FRAME CORE */',1)[0]
pre=r'''
#include <stdint.h>
#include <stdbool.h>
#include <assert.h>
#include <stdio.h>
struct vw_thread { uint64_t fp,flags,ra[8]; };
static bool readable=true;
static bool vw_readable(uint64_t a,uint64_t size){(void)a;assert(size==16);return readable;}
'''
post=r'''
int main(void){
 _Alignas(16) uint64_t frame[20]={0};
 uint64_t low=(uintptr_t)frame,high=low+sizeof(frame);
 for(unsigned i=0;i<9;i++){frame[2*i]=low+16*(i+1);frame[2*i+1]=0x100+i;}
 struct vw_thread t={0};vw_unwind(&t,low,0x999,low,high);
 assert(t.ra[0]==0x999&&t.ra[7]==0x106&&!t.flags);
 t=(struct vw_thread){0};vw_unwind(&t,low+1,0,low,high);assert(t.flags==16&&!t.ra[1]);
 t=(struct vw_thread){0};vw_unwind(&t,high,0,low,high);assert(t.flags==16);
 readable=false;t=(struct vw_thread){0};vw_unwind(&t,low,0,low,high);assert(t.flags==16);readable=true;
 frame[0]=low;t=(struct vw_thread){0};vw_unwind(&t,low,0,low,high);assert(t.flags==32);
 frame[0]=0;t=(struct vw_thread){0};vw_unwind(&t,low,0,low,high);assert(!t.flags&&t.ra[1]==0x100&&!t.ra[2]);
 puts("PASS: actual saved-FP walker caps at 8 RAs, rejects unaligned/out-of-stack/unreadable frames and cycles; accepts a terminated chain. Synthetic stacks only.");
}
'''
(out/'frames.c').write_text(pre+code+post)
subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror',str(out/'frames.c'),'-o',str(out/'frames')],check=True)
subprocess.run([str(out/'frames')],check=True)
