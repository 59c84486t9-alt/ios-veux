/* Standalone EL1/MMU-off screen probe. No stack, FDT parser, XNU or MMIO.
 * Geometry is passed by build-veux-fb-probe.py from console.h's VEUX profile.
 * White is invariant under ARGB/ABGR byte ordering (linear 32-bit pixels).
 */
	.section .text, "ax"
	.global _head
_head:
	b probe
	.long 0
	.quad 0
	.quad 4096
	.quad 0xa
	.quad 0, 0, 0
	.ascii "ARM\x64"
	.long 0
probe:
	msr daifset, #0xf
	/* Refuse unexpected entry state rather than use a firmware VA mapping. */
	mrs x4, CurrentEL
	cmp x4, #4
	b.ne halt
	mrs x4, sctlr_el1
	tbnz x4, #0, halt
	tbnz x4, #2, halt
	ldr x0, =PROBE_FB_BASE
	ldr x1, =PROBE_FB_HEIGHT
	ldr x2, =PROBE_FB_WIDTH
	ldr x3, =PROBE_FB_STRIDE
	mov w4, #-1
row:
	mov x5, x0
	mov x6, x2
pixel:
	str w4, [x5], #4
	subs x6, x6, #1
	b.ne pixel
	add x0, x0, x3
	subs x1, x1, #1
	b.ne row
	dsb sy
halt:
	wfe
	b halt
	.ltorg
	.balign 4096, 0
