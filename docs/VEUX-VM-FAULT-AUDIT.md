# VEUX VM-fault diagnostic candidate (0108)

This candidate retains cpus=1, the early framebuffer alias, first-fault bit
rows, console-route fix and normal pmap behavior. No pmap barrier is changed.

## Measurement phases

The existing first-fault bit dump runs before vm_fault and may flush. The new
veux_stage_mark_nb writes cells without barriers/logging; veux_stage_flush is
one dsb sy. Existing non-diagnostic callers retain the barriered wrapper.

Per-call snapshots live on the caller's stack, so nested faults cannot replace
an outer call's before-walk. Entry/pre-call markers and timer samples use NB
writes. Immediately after vm_fault, the helper saves PAR/DAIF, masks IRQ/FIQ
without a barrier, then executes AT S1E1W; ISB; MRS PAR_EL1 before drawing. This
first result is saved even on occurrence one, even with no subsequent repeat,
and regardless of the VM return code. The original PAR and DAIF are restored.

The first post-VM PAR/result/PC/FAR/call remain sticky separately from latest
results. Normal sleh return, or a timer tick after experiments have completed,
publishes the fixed panel using NB drawing and one final flush. While VM is
pending, the timer may update its own NB sample rows but cannot flush/publish.
Terminal panic ends the measurement and publishes its marker/status.

A publication flush can itself complete pending stores. Therefore first-PAR F=1
followed by no repeat is still evidence of a pre-publication problem; do not
interpret the absence of a repeat as disproving it. First-PAR F=0, VM result=0,
a return marker and first-pair occurrence count=1 show no observed unresolved
translation/retry for that saved fault. They do not rule out a later hang.

## One cumulative experiment

The experiment is gated by: successful vm_fault, immediate PAR F=1, second
consecutive occurrence of the same PC+FAR, and no previous experiment this boot.
The eighth occurrence only lights the repeat cell; it is not the experiment
trigger. The actual experiment's PC/FAR and occurrence are retained.

1. A: dsb ish; isb; AT S1E1W; isb; save PAR. Stop if F=0.
2. B: locate the descriptor at the level reported by PAR FST. Clean/invalidate
   its cache line using a validated direct-map VA: dc civac; dsb ish; AT; isb.
   Save PAR; stop if F=0. An unsafe/unmapped descriptor skips B with a flag.
3. C: tlbi vaae1is, (FAR>>12)&44-bit-mask; dsb ish; isb; AT; isb. Save PAR.

All steps are cumulative. Unexecuted PAR slots are ffffffffffffffff. No panel
render or diagnostic flush occurs between the immediate AT and completion of
the experiment. The after-call NB completion cell distinguishes a VM block from
an experiment block. The software after-walk is captured before recovery; its
loads/AT reads are observer effects but contain no full barrier. Instruction
inspection confirms emitted AT/ISB/MRS, DSB/ISB, DC/DSB, TLBI/DSB/ISB sequences;
explicit newline separators are required by this assembler.

| First step with F=0 | Interpretation to investigate |
| --- | --- |
| A | Ordering/completion, consistent with a missing dsb ishst after fresh PTE publication (FLUSH_PTE is only dmb ish). |
| B | Cache visibility/cacheability mismatch; compare live TCR and descriptor-page MAIR/SH. |
| C | Stale cached translation/walk state. |
| None | Inspect wrong/invalid descriptors, permissions, selected table and fault status. |

These are diagnostic pointers, not unique proofs: elapsed time and cumulative
operations can affect the result. A skipped B cannot rule out cacheability.
The instruction is allowed to retry; PC is never advanced to hide a fault.

## Pmap barrier audit: unchanged

In osfmk/arm/pmap/pmap.c:

- FLUSH_PTE = dmb ish. write_pte invokes it.
- FLUSH_PTE_STRONG = dsb ishst. write_pte_strong invokes it.
- pmap_enter_pte: an atomic successful change from an already valid PTE uses
  FLUSH_PTE_STRONG then PMAP_UPDATE_TLBS; a newly valid entry uses FLUSH_PTE
  then ISB, without that valid-entry TLBI path.
- pmap_expand publishes a new table descriptor with a direct store, then
  unlocks. There is no explicit dsb in that publication block. This observation
  is not a claim that caller/lock ordering provides no synchronization.
- osfmk/arm64/tlb.h sync_tlb_flush = dsb ish; isb. PMAP_UPDATE_TLBS dispatches
  the VA/ASID invalidation and calls arm64_sync_tlb, which invokes that helper.
  Leaf-only/all-level and global/ASID-specific invalidations differ by call.

Thus a blanket claim that every newly valid PTE has dsb ishst is false in this
fork. This build measures that behavior; a change belongs in a subsequent build.

Live TCR/SCTLR/TTBR1/MAIR are printed. TCR decoded fields show IRGN1, ORGN1,
SH1, T1SZ and TG1. Descriptor-page AttrIndx, SH, resolved MAIR byte and mapping
leaf level are captured from a software walk of its actual direct-map VA.
The mismatch mask compares WB/WB cacheability and shareability with the walker.
Unsupported policies are flagged for inspection, not silently called correct.
The software walker validates 16KiB granules, canonical TTBR1 addresses and
root alignment, stops on invalid/block descriptors and rejects table PAs outside
managed RAM. It checks a table alias with AT before dereferencing it. Invalid
geometry, unsafe backing and EPD1 are visible flags, not silent failures.

## Screen layout

The top console stops above y=800. Fixed hex rows have two-digit hex IDs at
x=16, two 16-digit values at x=96 and x=512, y=820+20*ID. Last row ends at
1774, below the console and above the older timer-timeout bits at y=1800.
First-fault bits at 2120/2144/2168/2192 and old strips at 2304/2352 are retained.

New y=2240 strip, 32x32 at x=32+64*i: white kernel-abort entry, yellow before
VM, green VM returned, cyan normal sleh return, red panic-with-state entry,
magenta eight consecutive same-PC/FAR data aborts. Green is cleared before the
next VM call. Counters/call tokens distinguish old completion from current work.

| Row ID | Left / right values |
| --- | --- |
| 00–01 | Latest ESR / PC; latest FAR / SP |
| 02–04 | 64-bit abort count / consecutive count; last PC / FAR; repeat count / total |
| 05–09 | Kernel entry count / PC; VM call / FAR; returned call / result; normal return count / PC; panic count / PC |
| 0A | **First post-VM PAR / first VM result**, retained without a repeat |
| 0B–0D | TCR / SCTLR; TTBR1 / MAIR; change mask / after-walk flags |
| 0E–10 | Before L1/L2/L3 table PA / descriptor |
| 11–13 | After L1/L2/L3 table PA / descriptor |
| 14 | Before / after walk flags |
| 15 | FAR classification bitmask / FAR |
| 16–1B | Alias slot, physmap, image, kmem min/max; DRAM PA/size; linear VA/size |
| 1C–1F | Before/after table-alias PARs and WB/SH consistency masks |
| 20,23 | Normal timer tick count / interrupted PC; same-PC streak / changed-PC count |
| 21 | Latest post-VM PAR / result |
| 22 | Fix step (0 none run, 1 A, 2 B, 3 C, 4 none fixed) / experiment occurrence |
| 24 | VM calls started / completed |
| 25–26 | A PAR / B PAR; C PAR / executed-step mask |
| 27–28 | Descriptor cache-line VA / descriptor PA; descriptor-page attributes / mismatch mask |
| 29 | Decoded TCR / descriptor cache-line bytes |
| 2A–2B | First post-VM PC / FAR; observed first-pair occurrence count / first call |
| 2C | Experiment's initial PAR / publication phase |
| 2D–2E | Latest descriptor PA / attributes; latest mismatch mask / descriptor-alias PAR |
| 2F | Experiment PC / FAR (sticky) |

Change mask: bits0..2 descriptors changed, bits8..10 table bases changed.
Walk flags: bits0..2 levels read; bit8 unsupported geometry/range; bit9 invalid;
bit10 block leaf; bit11 unsafe table backing; bit12 EPD1; bit31 skipped capture.
FAR class bits: alias slot, mapped splash alias, physmap, image, kernel_map,
linear kernel-managed RAM view, general kernel-VA range (bits0..6 respectively).
Executed-step mask: A/B/C in bits0..2; bit8 B skipped (unsafe descriptor), bit9
unsupported line size. Descriptor attributes: AttrIndx bits2:0, SH bits9:8,
MAIR byte bits23:16, leaf level bits31:24, valid bit32. Mismatch: bit0 no valid
page mapping, bit1 SH differs, bit2 not matched WB/WB, bit3 no safe descriptor.
TCR pack: IRGN1 bits1:0, ORGN1 bits5:4, SH1 bits9:8, T1SZ bits21:16, TG1 bits25:24.
A skipped B is not a completed cache-clean test. FST is (PAR>>1)&0x3f when F=1.

Timer samples print on tick one, then about every 100 normal timer interrupts.
A stable interrupted PC can be a spin, an idle instruction or a sampling bias;
symbolicate it. Changed-PC count is the number of changes from the preceding
tick, not a count of unique PCs. No ticks could mean masked IRQs, not necessarily
that the CPU stopped. The one-shot delivery probe is excluded from this sampler.

## Validation limits

Host tests execute the actual walker and hex renderer using synthetic tables,
and the recovery state machine with mocked AT/cache/TLB effects. They validate
bounds, gating, once-only behavior, saved slots, order and early termination.
**They cannot validate cacheability, hardware barrier behavior, real AT results,
cache maintenance or TLB invalidation. A green host test is not evidence on
those hardware questions.** Local arm64 object compilation and disassembly
check instruction emission. CI must link successfully before one image is made
and flashed. No source-level pmap fix is mixed into this measurement build.
