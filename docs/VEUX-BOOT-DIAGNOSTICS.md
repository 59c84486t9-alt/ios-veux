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
Both v3 probes are prepared but unflashed. Phone remains in slot-A recovery.
