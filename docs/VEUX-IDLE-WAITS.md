# 0109: idle-thread / BSD-root diagnostics

The 0108 photo shows one handled write translation fault, vm_fault=0,
first PAR.F=0, no repeat, and a timer sample at machine_idle+256. It does
not establish what the bootstrap thread waits for. No pmap barrier fix is
justified by that observation; 0109 leaves pmap and the early alias unchanged.
The original four first-fault bit rows remain sticky at y2120/2144/2168/2192.

## Screen layout

- Console: x0..1079, y64..799 (23 lines at 32px). Initialization clears this
  box; each advance clears its destination line, including wrap. Glyphs have
  opaque black backgrounds. The shim title above y64 may remain.
- Compact handled-fault status at y820/840, two hex columns:
  row00 = abort count / first post-VM PAR.F (all-ones means not captured);
  row01 = repeat flag / first vm_fault result. Expected here: 1/0 and 0/0.
- Full fault panel retains its 0108 legend for unresolved faults/repeats/panic.
  Completion row07 is repaired. Per-VM cells remain stores only; immediate
  PAR and cumulative once-only A/B/C recovery sequencing are unchanged.
- Wait pages occupy y872..2046. They never overlap the console, first-fault
  bits, or stage strips. The full unresolved-fault panel takes priority.
- BSD cells at y2080, x32+64*i, 32x32: 0 white after Skywalk+net_init_run;
  1 yellow before IOKitBSDInit; 2 green after; 3 orange before IOFindBSDRoot;
  4 cyan after; 5 magenta entry to bsd_utaskbootstrap. The existing strips at
  y2240/2304/2352 remain unchanged.

## One immutable wait snapshot

After scheduler, callout, IOKit and early-boot startup have completed and
interrupts are enabled, record current_thread as the bootstrap-thread identity.
A 100ms diagnostic timer observes whether the interrupted thread is the idle
thread on the sole online processor. Capture after five seconds of consecutive
idle observations; a non-idle sample restarts the interval. Work between samples
can be missed: this is sampled idle, not proof of uninterrupted idleness.
The timer deliberately adds periodic wakeups to a normally tickless system.

Capture the global thread list once, capped at 128 entries. In interrupt context,
with cpus=1 and the interrupted thread idle, no other CPU/thread can mutate it;
no sleeping thread-list lock is acquired. Validate mappings before dereferencing,
restore PAR_EL1 after diagnostic reads, and bound the traversal. This snapshot is
not suitable for SMP. With more than one processor it does not capture.

The frozen snapshot rotates six threads per page every two seconds and loops
for filming. Data is captured once; each page is drawn using NB stores and one
final flush. It is not a live thread dump. Full fault/panic reporting overrides
wait pages. Header IDs are F0..F4; all numbers are hexadecimal:

| Header | Left | Right |
|---|---|---|
| F0 | zero-based page | page count |
| F1 | captured threads | truncation: 0 complete, 1 cap, 2 unreadable, 3 self-link |
| F2 | sched_tick at idle interval start | sched_tick at capture |
| F3 | selected scheduler root runqueue count | realtime runqueue count |
| F4 | idle samples in interval | native timer-handler samples at capture |

F2 differences show scheduler-tick progress; equal values do not by themselves
mean the diagnostic timer stopped (it has its own cadence). With clutch, F3 left
is pset_clutch_root.scr_thr_count; with traditional/multiq it is pset_runq.count.
These are selected pset queue counts, not a sum over all queue implementations.

Each six-thread page uses nine rows per thread; IDs00..08,09..11,12..1A,
1B..23,24..2C,2D..35. Add 9*j to the following row offsets:

| Offset | Left | Right |
|---|---|---|
| 0 | thread pointer | state low32, options high32 (TH_OPT_INTMASK in options bits0..1) |
| 1 | wait_event | wait_result, raw uint32 |
| 2 | block_hint low32 + pending_block_hint high32 | dump flags |
| 3 | continuation address | saved FP |
| 4 | kernel_stack base | global snapshot thread index |
| 5..8 | return addresses 0,2,4,6 | return addresses 1,3,5,7 |

Dump flags: bit0 bootstrap thread; bit1 idle thread; bit2 currently executing
(no saved trace); bit3 continuation dispatch (old frame context not trusted);
bit4 invalid/unaligned/unmapped/out-of-stack frame; bit5 non-increasing/cyclic FP;
bit6 missing or invalid saved context. Continuations are evidence, not a fabricated
backtrace. Valid inactive contexts provide saved LR then up to seven saved FP-chain
return addresses. Frames must be aligned, readable, inside the kernel stack and
strictly increasing. No raw arbitrary stack scan is performed.

## Offline symbolization

Use the exact CI kernel artifact corresponding to the flashed image. Kernel is
unslid, base FFFFFE0006000000; do not apply a guessed slide. Transcribe only RA
columns into a text file and run:

```
python3 tools/symbolize-veux-waits.py /absolute/path/kernel.development.veux /absolute/path/ras.txt --return-address
```

This uses nm -n text symbols, subtracting 4 bytes from return addresses to identify
the call instruction. For continuation addresses omit --return-address. It reports
symbol+offset, not source lines; DWARF line lookup requires matching debug info.
Wait events are opaque identities and should not be symbolized as PCs. Photos
from 0109 are needed before actual waits/addresses can be classified.

## Actual boot configuration and root wait

Current image manifest 39896881721 and its packaging script use:

```
debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam -noprogress rd=ufsroot0 veuxlog=1 veuxfb=1 veuxfbconsole=1
```

The shim's Android INITRD is the roughly16MB XNU payload. mkpayload is invoked
without --ramdisk, so there is no XNU RAMDisk memory-map registration. A real
ramdisk root would require --ramdisk plus rd=md0. Current root is the built-in
ufsroot0 BSD disk, default GPT partition name userdata on internal UFS LUN0.
No ufsroot override, ufscache, ufswait, or ufsrw option is supplied. This diagnostic
candidate keeps these boot arguments; packaging must verify them in its manifest.

IOFindBSDRoot first waits up to30 seconds for IOResources/IOBSD matching to
finish (filesystems); timeout logs !BSD. Its custom rd=ufsroot0 branch then calls
sweet_ufs_rootdev: initialize/take over the UFS host if not ready, test readiness,
find the GPT partition, and expose the block device. Driver commands have a
5-second timeout each (and readiness retries), not one fixed boot timeout.
Failure here panics with SWEET UFS root unavailable; success skips the generic
IOService root-device matching loop and proceeds to filesystem mounting.
Filesystem/mount waits are a later stage, not proof of missing UFS hardware.

A generic Still waiting for root device message is therefore NOT expected for
this rd=ufsroot0 branch. In the alternative generic path DEVELOPMENT uses a
60-second service wait (DEBUG120), measured from that wait, potentially after
the initial IOBSD resource wait; it is not a guaranteed boot-relative deadline.
BSD cell3 without4 could be the resource/UFS lookup. Neither lit means inspect
an earlier boot wait. Cell4 lit shifts attention to subsequent mount/bootstrap.

## Validation limits

Local object compiles check types/code generation. Host console test executes
the writer with guarded RAM; frame test executes the actual walker against
synthetic stacks, including rejection paths. Existing synthetic TTBR/recovery
tests remain green. None validates hardware cacheability, barriers, timer delivery,
real saved-stack lifetime, or screen scanout. Only a boot with the CI-passing
exact kernel and recorded pages can identify the waiting thread(s).
