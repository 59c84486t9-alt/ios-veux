#!/usr/bin/env python3
"""Host-test the actual recovery state machine with mocked architectural effects.
Does NOT validate real barriers, cacheability, AT, dc civac or TLBI behavior.
Usage: test-veux-recovery.py APPLIED_XNU_TREE OUT_DIR
"""
from pathlib import Path
import subprocess
import sys
root,out=map(Path,sys.argv[1:]);out.mkdir(parents=True,exist_ok=True)
src=(root/'osfmk/arm64/veux_early.c').read_text()
code=src[src.index('static void\nvd_recovery('):src.index('static void\nvd_publish(')]
assert all(x not in code for x in ('vd_cell(', 'vd_row(', 'veux_stage_flush(', 'veux_stage_mark('))
code=code.replace('__asm__ volatile("dsb ish\\n\\tisb" ::: "memory");','effect(1);')
code=code.replace('__asm__ volatile("dc civac, %0\\n\\tdsb ish" :: "r"(vd_exp_line) : "memory");','effect(2);')
code=code.replace('__asm__ volatile("tlbi vaae1is, %0\\n\\tdsb ish\\n\\tisb" :: "r"(operand) : "memory");','effect(3); (void)operand;')
assert '__asm__' not in code
pre=r'''
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <assert.h>
struct vd_walk { uint64_t pa[3],desc[3],par[3],flags; };
struct vd_report { struct vd_walk before,after; uint64_t pc,far,occurrence,call,par,result,tcr,sctlr,ttbr,mair,changed,esr; };
static bool vd_exp_once, safe_descriptor;
static uint64_t vd_exp_occurrence, vd_exp_pc, vd_exp_far, vd_exp_par[4],vd_exp_step,vd_exp_mask;
static uint64_t vd_exp_attrs,vd_exp_mismatch,vd_exp_entry_pa,vd_exp_line,vd_exp_cacheline;
static unsigned effects[8],n_effects,n_at;
static uint64_t pars[3];
static void effect(unsigned step){effects[n_effects++]=step;}
static uint64_t vd_at(uint64_t va,bool write){(void)va;assert(write);assert(n_at<3);return pars[n_at++];}
static bool vd_descriptor_line(const struct vd_walk*w,uint64_t far,unsigned level,uint64_t*va,uint64_t*pa){
 (void)w;(void)far;assert(level==2);*va=0xfffffe0010001238ULL;*pa=0x110001238;return safe_descriptor;
}
static uint64_t vd_page_attributes(uint64_t va){(void)va;return (1ULL<<32)|(255<<16)|(2<<8);}
#define __builtin_arm_rsr64(reg) (4ULL<<16)
static void reset(uint64_t a,uint64_t b,uint64_t c){
 vd_exp_once=false;vd_exp_step=vd_exp_mask=vd_exp_attrs=vd_exp_mismatch=0;
 safe_descriptor=true;n_effects=n_at=0;pars[0]=a;pars[1]=b;pars[2]=c;
}
'''
post=r'''
int main(void){
 struct vd_report r={0};r.far=0xfffffe1000b78000ULL;r.par=13;r.tcr=(1ULL<<24)|(1ULL<<26)|(2ULL<<28);
 reset(0,0,0);r.occurrence=1;vd_recovery(&r);assert(!vd_exp_once&&!n_at&&!n_effects);
 r.occurrence=2;r.par=0;vd_recovery(&r);assert(!vd_exp_once&&!n_at&&!n_effects);r.par=13;
 reset(0,13,13);vd_recovery(&r);assert(vd_exp_once&&vd_exp_occurrence==2&&vd_exp_step==1&&vd_exp_mask==1&&n_at==1&&n_effects==1);
 assert(vd_exp_par[0]==13&&vd_exp_par[1]==0&&vd_exp_par[2]==UINT64_MAX&&vd_exp_par[3]==UINT64_MAX);
 vd_recovery(&r);assert(n_at==1&&n_effects==1);
 reset(13,0,13);vd_recovery(&r);assert(vd_exp_step==2&&vd_exp_mask==3&&n_at==2&&n_effects==2&&effects[0]==1&&effects[1]==2);
 assert(!vd_exp_mismatch&&vd_exp_line==0xfffffe0010001200ULL&&vd_exp_cacheline==64);
 reset(13,13,0);vd_recovery(&r);assert(vd_exp_step==3&&vd_exp_mask==7&&n_at==3&&n_effects==3&&effects[2]==3);
 reset(13,13,13);vd_recovery(&r);assert(vd_exp_step==4&&vd_exp_mask==7&&n_at==3);
 reset(13,0,13);safe_descriptor=false;vd_recovery(&r);assert(vd_exp_step==3&&vd_exp_mask==(1|4|256)&&n_at==2&&n_effects==2&&effects[1]==3);
 reset(0,0,0);r.occurrence=3;vd_recovery(&r);assert(!vd_exp_once&&!n_at);
 reset(0,0,0);r.occurrence=2;r.result=5;vd_recovery(&r);assert(!vd_exp_once&&!n_at);
 puts("PASS: actual recovery gating (second only, F=1, success only, once), cumulative A/B/C order, early stop, saved PARs and unsafe-descriptor skip. Architectural effects are MOCKED, not hardware-validated.");
}
'''
(out/'recovery-test.c').write_text(pre+code+post)
subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror',str(out/'recovery-test.c'),'-o',str(out/'recovery-test')],check=True)
subprocess.run([str(out/'recovery-test')],check=True)
