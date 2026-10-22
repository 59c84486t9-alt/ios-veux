/* ABL supplies its live FDT in x0. No XNU or hardware drivers are linked. */
    .section .text.head, "ax"
    .global _head
_head:
    b probe
    .long 0
    .quad 0
    .quad _end
    .quad 0xa
    .quad 0, 0, 0
    .ascii "ARM\x64"
    .long 0
probe:
    msr daifset, #0xf
    mrs x4, CurrentEL
    cmp x4, #4
    b.ne halt
    mrs x4, sctlr_el1
    tbnz x4, #0, halt
    tbnz x4, #2, halt
    msr spsel, #1
    adr x1, _stack_top
    mov sp, x1
    bl probe_main
halt:
    wfe
    b halt
