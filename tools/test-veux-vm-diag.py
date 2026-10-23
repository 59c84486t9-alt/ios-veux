#!/usr/bin/env python3
"""Host-execute the actual applied VEUX 16KiB walk core and fixed hex renderer.
Usage: test-veux-vm-diag.py APPLIED_XNU_TREE OUT_DIR
The production reader validates RAM bounds and live PAR; these tests inject
readable tables, blocks and unsafe backing without requiring a physical phone.
They do NOT test real cacheability, barriers, AT, cache maintenance or TLBs.
"""
import subprocess
import sys
from pathlib import Path
root, out = map(Path, sys.argv[1:])
out.mkdir(parents=True, exist_ok=True)
src = (root/'osfmk/arm64/veux_early.c').read_text()
core = src.split('/* BEGIN VEUX WALK CORE', 1)[1].split('*/', 1)[1].split('/* END VEUX WALK CORE */', 1)[0]
render = src[src.index('void\nveux_stage_mark_nb('):src.index('void\nveux_stage_flush(')] + src[src.index('static void\nvd_cell('):src.index('static uint64_t\nvd_at(')]
pre = r'''
#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#include <stdio.h>
#include <assert.h>
#include <string.h>
static uintptr_t veux_stage_fb;
'''
harness = r'''
static uint64_t tables[3][2048];
static unsigned reads;
static bool reader(uint64_t pa, uint64_t index, uint64_t *d, uint64_t *par) {
 reads++;
 if (pa < 0x1000000 || pa >= 0x100c000 || (pa & 0x3fff) || index >= 2048) return false;
 *d=tables[(pa-0x1000000)/0x4000][index]; *par=0xff00000001000080ULL; return true;
}
static void setup(uint64_t va, unsigned bits) {
 memset(tables,0,sizeof tables); reads=0;
 unsigned first=bits>36?0:1, shift=36-first*11;
 unsigned rootidx=(va>>shift)&((1ULL<<(bits-shift))-1);
 if (!first) {
  tables[0][rootidx]=0x1004003;
  tables[1][(va>>25)&2047]=0x1008003;
 } else tables[0][rootidx]=0x1008003;
 tables[2][(va>>14)&2047]=0x1800403;
}
int main(void) {
 uint64_t va=0xfffffe1000b78000ULL,tcr=(1ULL<<30)|(17ULL<<16);
 setup(va,47);
 unsigned l1=(va>>36)&2047,l2=(va>>25)&2047,l3=(va>>14)&2047;
 uint64_t valid=tables[1][l2];tables[1][l2]=0;
 struct vd_walk before=vd_walk_core(va,tcr,0x1000000,reader);
 assert(before.flags==(3|(1<<9)) && reads==2 && before.pa[2]==0);
 tables[1][l2]=valid;reads=0;
 struct vd_walk after=vd_walk_core(va,tcr,0x1000000,reader);
 assert(after.flags==7 && reads==3 && after.desc[2]==0x1800403);
 assert(before.desc[1]!=after.desc[1] && before.pa[2]!=after.pa[2]);
 tables[0][l1]=0x1800001;reads=0;
 after=vd_walk_core(va,tcr,0x1000000,reader);
 assert(after.flags==(1|(1<<10)) && reads==1);
 setup(va,47);tables[1][l2]=0x1800001;reads=0;
 after=vd_walk_core(va,tcr,0x1000000,reader);
 assert(after.flags==(3|(1<<10)) && reads==2);
 setup(va,47);tables[2][l3]=0x1800001;
 after=vd_walk_core(va,tcr,0x1000000,reader);assert(after.flags==(7|(1<<9)));
 setup(va,47);tables[0][l1]=0xdead0003;reads=0;
 after=vd_walk_core(va,tcr,0x1000000,reader);assert((after.flags&(1<<11)) && reads==2);
 reads=0;after=vd_walk_core(1,tcr,0x1000000,reader);assert(after.flags==(1<<8)&&!reads);
 after=vd_walk_core(va,2ULL<<30,0x1000000,reader);assert(after.flags==(1<<8)&&!reads);
 after=vd_walk_core(va,tcr,0x1000040,reader);assert(after.flags==(1<<8)&&!reads);
 va=0xffffff8000b78000ULL;setup(va,39);
 after=vd_walk_core(va,(1ULL<<30)|(25ULL<<16),0x1000000,reader);assert(after.flags==7);
 va=0xfffffff000b78000ULL;setup(va,36);
 after=vd_walk_core(va,(1ULL<<30)|(28ULL<<16),0x1000000,reader);
 assert(after.flags==6 && after.pa[0]==0 && reads==2);
 size_t n=1080*2400;uint32_t *fb=malloc(n*4);assert(fb);
 veux_stage_fb=(uintptr_t)fb;for(size_t i=0;i<n;i++)fb[i]=0x5a5a5a5a;
 vd_row(0x23,0x0123456789abcdefULL,UINT64_MAX);vd_cell(5);
 for(unsigned y=0;y<2400;y++)for(unsigned x=0;x<1080;x++) {
  bool row=(y>=1520&&y<1534&&((x>=16&&x<34)||(x>=96&&x<254)||(x>=512&&x<670)));
  bool cell=y>=2240&&y<2272&&x>=352&&x<384;
  if(!row&&!cell)assert(fb[y*1080+x]==0x5a5a5a5a);
  if(cell)assert(fb[y*1080+x]==0xffff00ff);
 }
 assert(fb[1520*1080+96]==0xff101010); /* leading zero's top-left pixel */
 assert(fb[1520*1080+98]==0xffffffff);
 assert(fb[1520*1080+512]==0xffffffff); /* F's top-left pixel */
 free(fb);
 puts("PASS: actual walk core (fault before/after, blocks, bad descriptors, safe-reader rejection, canonical/range/granule/root checks, short roots) and fixed hex/cell write bounds");
}
'''
(out/'host-test.c').write_text(pre+core+render+harness)
subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror',str(out/'host-test.c'),'-o',str(out/'host-test')],check=True)
subprocess.run([str(out/'host-test')],check=True)
