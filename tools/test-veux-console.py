#!/usr/bin/env python3
"""Execute the actual console writer with guarded RAM instead of a framebuffer.
Checks line clearing at wrap, CR repaint, and that diagnostics remain untouched.
Does not exercise device memory ordering, cacheability, or real scanout.
"""
from pathlib import Path
import subprocess
import sys
root,out=map(Path,sys.argv[1:]);out.mkdir(parents=True,exist_ok=True)
src=(root/'pexpert/arm/pe_serial.c').read_text()
tail=src.split('#define VEUX_PANIC_TAIL_LINES',1)[1].split('static volatile uint32_t *veux_fb_console_base;',1)[0]
tail='#define VEUX_PANIC_TAIL_LINES'+tail
code=src.split('void\nveux_fb_console_putc(char c)',1)[1].split('#endif /* ARM64_BOARD_CONFIG_VEUX */',1)[0]
code=tail+'\nvoid\nveux_fb_console_putc(char c)'+code
code=code.replace('__asm__ volatile("dsb sy" ::: "memory");','')
pre=r'''
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <assert.h>
#include <stdio.h>
#define VEUX_FB_WIDTH 1080u
#define VEUX_FB_CONSOLE_SCALE 2u
#define VEUX_FB_CONSOLE_TOP 64u
#define VEUX_FB_CONSOLE_FG 0xffffffffu
static uint32_t memory[1080*850];
static volatile uint32_t *veux_fb_console_base=memory;
static unsigned veux_fb_console_stride=4320,veux_fb_console_col,veux_fb_console_row;
static bool veux_fb_console_ready=true;
static unsigned char iso_font[128*16];
static int veux_gui_console_muted;
static bool panic_active(void) { return false; }
'''
post=r'''
int main(void) {
 for (unsigned i=0;i<1080*850;i++) memory[i]=0x12345678;
 unsigned rows=(800-64)/32;
 for(unsigned i=0;i<rows;i++) veux_fb_console_putc('\n');
 assert(veux_fb_console_row==0);
 for(unsigned y=64;y<64+rows*32;y++)
  for(unsigned x=0;x<1080;x++) assert(memory[y*1080+x]==0xff000000);
 for(unsigned y=800;y<850;y++) assert(memory[y*1080]==0x12345678);
 for(unsigned y=0;y<64;y++) assert(memory[y*1080]==0x12345678);
 veux_fb_console_col=67;veux_fb_console_putc('A');assert(veux_fb_console_col==1&&veux_fb_console_row==1);
 veux_fb_console_putc('\r');assert(veux_fb_console_col==0);
 puts("PASS: actual console wraps with cleared lines, CR resets column, writes stay in console region. RAM only, no hardware ordering/scanout coverage.");
}
'''
(out/'console.c').write_text(pre+code+post)
subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror',str(out/'console.c'),'-o',str(out/'console')],check=True)
subprocess.run([str(out/'console')],check=True)
