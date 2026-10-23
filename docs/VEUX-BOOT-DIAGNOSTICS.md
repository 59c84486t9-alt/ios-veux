# VEUX boot diagnostics: marker/reset control first

CI run 39805058203 passed. Its freshly flashed XNU image still showed the
Xiaomi logo; recovery yielded no pstore and an unchanged userdata-tail log.
That result does not identify the XNU stopping point.

## Regression candidate

Commit c27fda0 removed VEUX_NO_FB from shim/build.sh. shim_main() now runs
con_clear() before loader_boot() writes the pmsg handoff marker. The previous
screen-disabled shim could reach that marker without accessing scanout RAM.
A fault during the new screen clear could suppress all later markers. This
is a source-supported hypothesis, not proof of the current fault. Patch 0103
also changed XNU display mapping, and 0104/toolchain migration changed the
build; the comparison cannot isolate a single cause without runtime evidence.

## Local builds

```sh
PATH=/usr/local/opt/aarch64-elf-binutils/bin:$PATH python3 tools/build-veux-fb-probe.py \
  --template shim/out/shim-boot-veux-directfb-probe-oldxnu-20261022.img \
  --dtb dtb/vendor_boot_b_unpacked/dtb_1.dtb \
  --out-dir shim/out/veux-marker-reset-v3
# Same command with --screen and a distinct output directory builds RGB mode.
python3 tests/test_veux_fb_probe.py
```

Default output: shim-boot-veux-marker-reset.img. It checks EL1/MMU-off/cache-off,
writes `VEUX POSCTRL v3 stage=0 entered C; pmsg marker before FDT` to the
previously verified pmsg ring, prints the counter frequency, spins for ten
seconds using CNTVCT_EL0/CNTFRQ_EL0, logs elapsed ticks, then invokes PSCI
SYSTEM_RESET (SMC 0x84000009). Marker-only links no FDT parser or renderer.
If SYSTEM_RESET returns it logs x0 and halts. Invalid entry state halts before
C; invalid counter frequency logs an error and halts without a timed reset.
A counter-access exception or protected pmsg write could still halt early.

The pmsg ring is the same observed Linux persistent-RAM mechanism at
0xd0100000 (1 MiB, no ECC, 12-byte DBGC header). The positive marker deliberately
uses the independently verified runtime layout before FDT validation. It
is VEUX-specific, not a portable probe. This tests retained-RAM logging and
reset retention, not the separate UFS userdata logger. Missing marker remains
ambiguous if execution or reset cannot be established independently.

A standard PSCI reset does not select recovery or change slots. With B active,
it may repeatedly boot the probe. During the device test, observe elapsed time
from probe entry approximately (bootloader time adds delay from the host reboot
command), then return with Power + Volume Down and select slot-A recovery.
Do not invent Qualcomm-specific SYSTEM_RESET2 reason values. Collect pstore
before another reboot. This sequence still includes firmware transitions;
if the marker is absent, investigate execution and retention separately.

## Screen mode and selection

`--screen` produces shim-boot-veux-rgb-reset.img. It writes the same marker
first, then parses the live FDT supplied by ABL. Source priority:

1. One valid enabled live simple-framebuffer descriptor.
2. If none exists, one identity-mapped named splash region under
   reserved-memory, using the requested **assumption** of 1080x2400,
   four-byte pixels, stride 4320, a8r8g8b8.
3. Log the missing/invalid/ambiguous selection and proceed to timed reset.

An explicit but invalid/ambiguous live framebuffer is not overridden by the
fallback. Both paths require bounded aligned writes within the independently
verified VEUX splash reservation. The fallback base/size comes from the live
reg property; SWEET's 0x9c000000 is rejected. Logs name the chosen source and
record geometry before drawing. RGB bars, corner mark and border are held
for ten seconds after the fill, then reset is requested. No SDE/DSI MMIO or
UFS access is linked; padding bytes are untouched.

## Live recovery evidence, 2026-10-22

This is current slot-A recovery, not stock Android. `find -L` is required
because /proc/device-tree is a symlink. It reports:

```
/proc/device-tree/reserved-memory/splash_region@0x85200000
reg = <0x0 0x85200000 0x0 0x00c00000>
```

`grep -i splash /proc/iomem` gives no lines; the corresponding named range is:

```
85200000-85efffff : reserved
```

That iomem range also includes the adjacent DFPS reservation. The splash node
itself is 12 MiB. Current live FDT has no simple-framebuffer node; host-testing
it selects source 2, base 0x85200000, size 0xc00000. Neither reservation nor
video-mode panel source establishes live scanout layout or continued scanning.
The board-matched K6S panel declares dsi_video_mode, making command-mode refresh
a weaker hypothesis, not an eliminated possibility for all display failures.

## Validation and status

Seven host tests cover malformed/truncated FDT, geometry bounds, display
selection priority, fallback refusal, RGB/BGR layout and untouched row padding.
Both freestanding AArch64 builds and boot-v2 payload/DTB/image-ID verification
pass. C objects contain no ABS64 pointers; marker binary symbol/disassembly
inspection confirms no parser/renderer and the counter/SMC sequence.
Both v3 probes were tested; see measured outcomes below. Phone is back in slot-A recovery, with the RGB probe still on boot_b.

## Ordered device tests and interpretation

| Order | Image / action | Evidence sought |
| --- | --- | --- |
| 1 | Marker-only + 10-second counter + PSCI reset, boot_b | Recover exact `VEUX POSCTRL v3` marker in slot-A recovery after observing reset. No display dependency. |
| 2 | RGB screen probe, boot_b, only after control is understood | Log selected address/geometry; compare bars and corner with recorded fill-complete stage. |
| 3 | XNU with cpus=1 and incremental stage breadcrumbs | First failing boundary using a display/log channel already exercised independently. |

| Result | What it supports / does not prove |
| --- | --- |
| Exact marker + elapsed-ticks + reset-request records recovered | Probe C entry, pmsg writes, counter wait and reset request executed; recovery preserved those records. Does not validate XNU mapping or UFS logger. |
| Marker recovered but no reset-request record | Probe reached logging but may have stopped earlier; inspect last complete stage. Truncation or reset loss is also possible. |
| Reboots near expected interval, marker absent | Some reset path is active, but PSCI vs watchdog still needs evidence; log transport is unvalidated, so an empty XNU log cannot locate a stop. |
| Neither marker nor reset observed | Still ambiguous: image entry, entry-state guard, pmsg access, counter access, or retention. Do not call this proof of XNU failure. |
| Pattern visible and fill-complete record recovered | The selected buffer/layout can produce a visible image; inspect RGB order, border and row pitch. |
| Fill-complete recorded but no visible pattern | CPU stores completed; active plane, format, compression, display state or refresh still needs investigation. |
| Source/starting-fill logged but no completion | Suspect framebuffer access or interruption during fill; compare reset interval and preserved records. |
| SKIP plus later counter/reset records | Probe works but rejects its descriptors; inspect logged source/count/geometry before changing validation. |

### XNU breadcrumb patch 0105 (implemented after visible RGB result)

Keep cpus=1 and avoid userspace/UFS dependencies for the first stage test.
Retains existing early-text milestones and adds six 32x32 color cells at
y=2304, x=32+64*cell (zero-based), using the now-tested buffer:

| Cell | Boundary | Color |
| --- | --- | --- |
| 1 | earliest `_start` entry | red |
| 2 | MMU enabled, verified mapping usable | orange |
| 3 | `arm_init` entry | yellow |
| 4 | DT parsing completed | green |
| 5 | GIC/timer initialization completed | cyan |
| 6 | console ready | magenta |

Use the verified physical address before the MMU and an explicitly valid mapping
after it; a generic physmap need not include low reserved splash RAM when XNU
manages only the high DDR bank. Log matching stage IDs through the proven channel.
Do not overwrite Linux persistent-RAM header words with an arbitrary counter.
Move the shim's own marker ahead of any optional screen clear when returning to
XNU. Compile changed C files with tools/xnu-cc.py, check assembly separately,
then perform one full kernel build for the tested candidate.

## Device results from this session

1. Marker-only image flashed to boot_b and booted successfully by fastboot.
   User observed repeated Xiaomi-logo/black-screen/restart cycles. Exact interval
   was not measured, so watchdog vs requested PSCI reset is not independently
   proven. After manual fastboot and slot-A recovery, pstore was empty.
2. Wrote `VEUX_LINUX_PMSG_CONTROL_20261022_V3` through Linux /dev/pmsg0 and
   used `adb reboot recovery`. The exact marker survived in pmsg-ramoops-0.
3. Wrote `VEUX_LINUX_FASTBOOT_CONTROL_20261022_V3`, then used adb reboot
   bootloader and fastboot reboot recovery, keeping A selected. Pstore was
   empty. This establishes loss across the fastboot recovery route even with
   Linux's own writer. It does not prove the bare-metal writer executed.
4. RGB probe flashed next. User explicitly observed the RGB pattern followed
   by restart. The live-DT splash fallback can drive a visible pattern on this
   phone. Returned to slot-A recovery; no XNU breadcrumb image flashed yet.

The current recovery device-node properties independently confirm record-size
0x100000, pmsg-size 0x100000, reg=<0 0xd0000000 0 0x200000>. The console file
seen after a Linux reboot is not evidence for a different pmsg offset; this
Qualcomm source names the record zone "console". The actual recovery kernel
source is not fully matched, so retain the live DT and successful control as
stronger evidence than the filename.

Patch 0105 uses a dedicated L3 table with exactly 768 16KiB framebuffer pages,
leaving the rest of the containing 32MiB block unmapped. It walks the existing
bootstrap L1 table, then shares that L3 table via a reserved kernel alias before
TTBR0 teardown. No reliance on low splash RAM being in the high-bank physmap.
Console rows stop above the marker footer. The ADT/shim/late-console geometry
is corrected from the earlier 2520 assumption to the tested 2400 lines.
Cells show named boundaries, not necessarily chronological numeric order:
console routing and GIC initialization may occur in a different order. Cyan
means GIC/timer-PPI configuration completed, not proven timer IRQ delivery.

The unchanged diagnostic ADT was also checked: /chosen DRAM base 0x100000000,
size 0xf8600000; /cpus MPIDRs 0x0..0x700; /arm-io translation base 0x01000000;
GICD 0x0f200000/0x10000; GICR 0x0f240000/0x100000; virtual timer INTID 19.
These agree with recorded board data but do not validate XNU's runtime use.

Local validation: six changed XNU translation units emitted arm64 objects
(including start.s), three changed shim translation units compiled freestanding,
patch 0105 applies with standard git apply, all CI source assertions pass, and
seven probe tests pass. The exported sweet_early.h in the downloaded build tree
was refreshed for the two pexpert compile checks; full CI handles header export.
The helper xnu-cc.py now detects the fork's CI root, finds installed clang when
~/swift is absent, and creates the requested object directory. Full XNU link
and device breadcrumb results remain separate pending checks.


## Stage 0106: retained-alias fault and IRQ diagnostics

Keep the 0105 alias and L3 mapping until real console output is demonstrated.
The first strip stays at y=2304. The second strip is at y=2352, 32x32 cells,
x=32+64*i. User-facing cells 7–15 correspond to function indices 6–14:

| Cell | Color | Boundary |
| --- | --- | --- |
| 7 | white | machine_startup entry, before kernel_bootstrap |
| 8 | lime | vm_mem_bootstrap returned |
| 9 | blue | kernel_bootstrap clock_init returned |
| 10 | pink | immediately before diagnostic IRQ/FIQ unmask |
| 11 | cyan | first IRQ/FIQ first-level assembly handler, after context save |
| 12 | orange | first synchronous first-level assembly handler |
| 13 | red | sweet_early_panic entry |
| 14 | green | diagnostic handler acknowledged the virtual timer INTID |
| 15 | purple | timer probe timed out (or prerequisites unavailable) |

These are boundaries, not chronological numbers. The probe runs at cell 7,
after the original six sites but before allocator/clock/scheduler startup.
The first-level markers precede handler bookkeeping/C dispatch; they preserve
live context registers and have no extra stack/log dependencies. A failure
before context save can still prevent a first-level marker. IRQ/FIQ share cell
11; the handler only lights cell 14 for the configured virtual timer INTID.

The renderer itself is stackless AArch64 assembly. Sync C handlers pass saved
ESR/PC/FAR/SP before thread/context validation; panic passes current ESR_EL1,
ELR_EL1, FAR_EL1 and handler SP. The first dump is retained so a later panic
cannot overwrite a synchronous fault. A panic without a preceding synchronous
exception may show stale ESR/ELR/FAR; those are not automatically its caller PC.
Rows y=2120/2144/2168/2192 contain ESR, ELR, FAR, SP respectively. Each is 64
16x16 squares at x=28 with 16px pitch, MSB left, white=1, dark gray=0. Text wraps
above y=1760, preserving all diagnostic rows.

The one-shot probe saves DAIF/CNTV_CTL/CNTV_CVAL, sets about 1ms TVAL, enables
an unmasked virtual timer and clears PSTATE IRQ/FIQ masks. It spins using CNTVCT
for up to 50ms. The diagnostic handler acknowledges/EOIs the appropriate GIC
group and disables the timer; it bypasses rtclock/scheduler C handlers while
retaining balanced assembly interrupt bookkeeping. Timer and DAIF state are
restored before normal startup continues. It does not add a forced reset.

On timeout, rows starting y=1800, spaced 24px, are:
CNTV_CTL, GICR_ISPENDR0, GICR_ISENABLER0, GICR_IGROUPR0, priority byte for INTID19,
GICR_WAKER, GICD_CTLR, ICC_SRE, ICC_PMR, ICC_IGRPEN0, ICC_IGRPEN1.
These use the redistributor selected by the existing initialization, not a
hardcoded CPU frame. If prerequisites are absent, only the first row (frequency)
and purple cell are written; lack of cell 10 distinguishes this case.

ISTATUS=0 suggests timer programming/counter trouble. ISTATUS=1 with INTID19
not pending points toward delivery to the redistributor. Pending without a
vector points toward group/priority/interface or exception routing. Group
register views can be constrained by non-secure access; zero alone is not proof
of Group 0 configuration. A cyan vector without green delivery requires checking
which exception/INTID arrived. Fault rows take priority if system-register/MMIO
access itself traps. Absence of a cell does not rule out a fault before that
marker can execute.

Before flashing: local object compiles, patch application, actual assembly
renderer emulation with an unmapped stack, then full CI. Keep cpus=1 and the
shim marker before con_clear. Flash boot_b only after CI success. Start filming
while still in fastboot, then reboot; capture both strips, all dump rows and
elapsed time to any reset. Do not infer PSCI versus watchdog from reboot alone.


## 0106 photo and video result

The photo shows original six cells plus second-strip white/lime/blue/pink/cyan/
orange and diagnostic green. Red panic and purple timeout are unlit. Thus the
one-shot virtual-timer interrupt reached its diagnostic handler, allocator and
clock initialization returned, and a synchronous exception was observed later.
This validates that test delivery; it does not prove every scheduler timer works.

The attached MOV is 3.418 seconds long. It starts at the Xiaomi logo, shows the
stage strips by sampled frame 2.002s, and ends on the same stage display at
3.378s. There is no reset in this clip, so no reset interval can be measured.
The video has no visible fault rows; those are present in the separate photo.

Perspective/bit-grid fitting of the photo, without assuming register values,
gives best decode ESR 0x96000046, ELR 0xfffffe000764b18c,
FAR 0xfffffe1000b78000. The SP is less certain: candidates
0xfffffe301f7277e0 and 0xfffffe301f727fe0 differ at a blurred bit. Some pixel
thresholds also flip ELR bit14; the alternative 0xfffffe000764f18c is a BL
instruction in fq_getq_flow_internal, inconsistent with this precise write data
abort. At the best ELR, the exact run-39887758455 kernel instead contains
`str w8, [x0]`, matching the syndrome. Symbolication resolves it to
skmem_sysctl_init + 24; preceding code fetches skmem_get_sysctls_obj and loads
w8=3. The object is a newly allocated 16KiB Skywalk sysctl region. The best FAR
is 16KiB-aligned; a low-confidence threshold alternative flips bit13.

ESR EC=0x25, WnR=1, DFSC=0x06: same-EL data write, level-2 translation fault.
This is consistent with first-touch demand paging; it is not proof of a fatal
fault or the last executed PC. The first-fault renderer deliberately retains
handled exceptions too, and the panic cell is absent. Raw fitting scripts,
annotated crops and exact-kernel disassembly are kept in ignored
research/veux-logs/0106-video-analysis/.

Source review found a separate console routing defect: PE_init_veux_pmsg sets
the VEUX sink during VM initialization, then STARTUP(KPRINTF) PE_init_kprintf
replaces it with UART output or a discard function. Patch 0107 preserves the
already initialized, opted-in VEUX sink and prints a direct `VEUX kprintf route
active` banner independent of kprintf gating. It retains the early alias and
all 0106 diagnostics. Local object compilation passes; a new full CI build is
required before the next flash. Device output from 0107 remains untested.
