# VEUX software display bring-up

## Current status — lock-screen handoff

On 2026-10-27, the user supplied a photo showing the iOS lock screen after
booting the 40413116842 kernel with `veuxsandbox=1` and
`veuxiolog=backboardd,SpringBoard`. This is the first confirmed GUI handoff
for this VEUX test: SpringBoard rendered the lock screen. The user reported
that the Apple logo first appeared, faded to black, and a small asterisk
appeared before the lock screen came up; that intermediate mark was not a
terminal boot failure.

The sandbox-enabled wrapper was flashed only to `boot_b`; `boot_a` remains
untouched. The host does not enumerate ADB or Fastboot after iOS reaches the
lock screen, so use the on-device UI to confirm swipe/unlock behavior. Preserve
this booted state; no further flash or reboot is needed to establish GUI
success.

## Historical blocker — build 402315 / IMG_0724

IMG_0724.mov follows slot-B reboot with kernel 40231594906 and the entitlement-
repaired root (`d7777c229e7dc012a3e86a5d9f54ab4fc4bf74e443526fe2f11562f0d2b2d691`).
Services now execute; the spawn-setup EPERM loop is past.

Shared-cache slide: `0x53594000`. The exact cache was extracted read-only from
the saved 20H392 root, resolving HFS hard links through their private inode
records. Main-cache SHA-256:
`76874e8375252ee643011ff8063f0cce12355f05cf5f9897a34e5679667a65aa`.
Symbols-cache SHA-256:
`e763b0eadab7aaa283e3075fc4ebcd9e824d35c834101e4dd99554265126b308`.

Using installed `ipsw dyld a2s`:

| Runtime address | Unslid address | Symbol |
|---|---|---|
| SpringBoard PC `0x1eeefcca8` | `0x19b968ca8` | `-[FBSDisplayMonitor _initWithBookendObserver:transformer:]+1160` |
| `0x1f5c24438` | `0x1a2690438` | `+[FBDisplayManager sharedInstance]` block +256 |
| `0x1f5bd5a30` | `0x1a2641a30` | `+[FBDisplayManager sharedInstance]+112` |
| `0x218df95c8` | `0x1c58655c8` | `SBSystemAppMain+4976` |
| backboardd PC `0x215bab198` | `0x1c2617198` | `__pthread_kill+8` |
| `0x1e11f04b8` | `0x18dc5c4b8` | `abort+124` |
| `0x1d3666afc` | `0x1800d2afc` | `_objc_terminate+124` |
| `0x2250723d4` | `0x1d1ade3d4` | `std::terminate+52` |

The SpringBoard instruction is `brk #0`, immediately after a call to
`__bs_set_crash_log_message`. Existing SWEET notes identify the identical
FBSDisplayMonitor+1160 failure before its display service was implemented.
VEUX currently omits the service; this is the concrete first target.
Backboardd's stack confirms the abort/termination path; its exception message
is unknown. Watchdogd explicitly reports the missing watchdog KEXT service.

REA opened the extracted FrontBoardServices framework, but Ghidra import failed
while resolving its CoreFoundation dependency. No successful REA decompilation
or runtime evidence is claimed. Symbolication and instruction observations above
are from ordinary local ipsw tools. Raw transcription, symbol output and assembly
remain in ignored `research/veux-logs/entitlements-fixed-boot-0724/`.

## Change in patch 0123

Enable the existing software IOSurface, IOMobileFramebuffer/AppleCLCD and
IOWatchdog compatibility implementations for VEUX only with `veux_gui=1`.
Publish only the existing disp0 child nub. No SWEET HID, SEP, display-controller,
clock, touch, or panel power code is enabled.

Before mapping scanout, require the existing ADT node to match the validated
VEUX probe layout exactly: base `0x85200000`, reserved span `0xc00000`,
1080x2400, stride 4320, a8r8g8b8. Present a 1125x2436 iPhone X canvas with the
same centered crop already used on SWEET. The path copies BGRA surfaces with
the existing CPU presenter; it does not program display controller registers.

`veux_gui_noconsole=1` hands over the screen only after a valid enabled BGRA
layer has been copied. Normal console/diagnostic drawing then pauses; the
25-line tail continues capturing text. Panic entry reclaims the screen, and
software presentation/vsync stop while panic is active. Without this second
argument the diagnostic console remains enabled.

This is a first software display-service experiment, not a complete graphics
or input port. Touch/navigation is not implemented, and backboardd may expose
further service dependencies. Watchdog is a check-in compatibility service;
it never arms a hardware timer.

## Touch bring-up target — 2026-10-27

The phone-specific DTB carried by the successful wrapper identifies the touch
device as `goodix,gt9896` at I2C address `0x5d`, on GENI SE8 at physical
`0x04c88000` (window `0x4000`). Its reset/IRQ/AVDD/DVDD GPIOs are 21/22/51/44;
IRQ is falling-edge. The DT advertises sensor coordinates 8640x19200 and does
not set `goodix,swap-axis`, `goodix,x2x`, or `goodix,y2y`. The display canvas
used by the VEUX GUI is 1080x2400.

The existing tested SWEET path supplies reusable GT9896 event parsing and HID
event generation, but it assumes SWEET's GENI SE7 address and GPIO/rail
configuration. Its HID adapter clamps coordinates to 1080x2400 before
normalizing them, so VEUX sensor coordinates need an explicit 8:1 conversion
before calling it. That scale follows the VEUX DT maxima and display dimensions;
confirm observed touch reports at corners before treating the mapping as
validated.

The local pinned Linux reference (`../research/kernel_xiaomi_sm6375`, commit
`f4b8a13a43a130a9ab83cc985ce4d4421291ae6`) describes the same VEUX GT9896 node
and powers AVDD then DVDD through those GPIOs before reset. It is reference
behavior, not proof of ABL handoff or of the exact recovery kernel. In
particular, XNU still needs SE8 clock integration and evidence that GENI I2C
firmware is loaded. Do not enable the SWEET driver on VEUX or issue guessed
clock/PMIC/register writes.

Next implementation should be a separate VEUX-only touch path, gated by an
explicit boot argument. First stage should log read-only SE8, pin and GPIO
state; then validate a bounded Goodix identity read; only then add the reviewed
GPIO power/reset sequence and event polling/HID delivery. Keep the default
image unchanged and test only from `boot_b`, preserving the lock-screen boot
and `boot_a`.

## Read-only SE8 probe — patch 0131

Patch 0131 adds a first diagnostic behind `veuxtouchprobe=1`. It snapshots the
SE8 firmware/status/clock/IRQ/FIFO registers, the Blair GCC SE8 source and
branch state, and TLMM config/input-output registers for GPIOs 19, 20, 21, 22,
44 and 51. It does not write controller, clock, GPIO, or PMIC registers and
does not issue I2C. The normal boot path is unchanged when the argument is
absent. Build and on-device results are pending; this is not touch support.

## Validation and pending hardware test

Local syntax checks: all seven changed translation units passed; after the
panic-tail/panic-present review fixes the two affected units passed again.
Patch applicability against exact CI-40231594906 sources passes at zero fuzz.
Repository validation and Python syntax checks pass. CI must prove linking,
patch status, retained binary markers and source policy checks before wrapping.

The boot recipe keeps the verified RW pair, cpus=1, framebuffer console and
spawn diagnostics, adding `veux_gui=1 veux_gui_noconsole=1`. The persistent
userdata-tail logger stays disabled. Use the entitlement-repaired root for a
fresh RW test; never restore the older stripped-entitlement image.

## First on-device result — IMG_0729.mov

The 8.2-second user video remains on the kernel diagnostic framebuffer; the
colored bottom strip and diagnostic text remain visible, so the requested
`veux_gui_noconsole=1` handoff is not demonstrated. It shows SpringBoard
SIGTRAP (signal 5, namespace 2/code 5), mediaserverd SIGSEGV (signal 11),
identityservices aborting, and backboardd SIGABRT (signal 6, namespace 2/code
6), followed by repeated crash/corpse-limit output. The visible SpringBoard PC
is `0x1de83cca8`; the visible mediaserverd PC is `0x1c9d320cc`. The video does
not visibly include the CI build ID, so attribution to wrapper 40252779285 is
based on the immediately preceding verified slot-B flash/reboot sequence,
not an on-screen build marker. This is a successful build and partition-write
sequence but an unsuccessful GUI runtime test. This result prompted the
symbolication and trace-patch work recorded below; it is not a test of the
later 40258406080 wrapper.

## Runtime root cause and trace follow-up

The repaired 20H392 root was expanded to a temporary raw image and mounted
read-only. Its iOS 16.7 dyld cache symbolicates the new video's SpringBoard PC
`0x1de83cca8` with slide `0x42ed4000` to `0x19b968ca8`, the same
`-[FBSDisplayMonitor _initWithBookendObserver:transformer:]+1160` trap as the
earlier video. Disassembly places the trap at the nil result of
`CADisplay.displays.firstObject`; the `FrontBoardServices` error string is
`failed to find the main CADisplay`. The direct failure is therefore display
enumeration, before an IOSurface layer can be copied and handed off.

The shim ADT describes `/arm-io/disp0` as `device_type=display-subsystem` and
`compatible=sweet,display`, which matches the iOS 16 IOMobileFramebuffer
enumerator's device-tree scan. This proves the expected metadata is present in
the generated ADT, not that IOKit created the nub, matched `AppleCLCD`, or
registered a usable IOMobileFramebuffer service at runtime. Patch 0124 adds
bounded logs for those steps and for the first framebuffer user-client opens
and swaps. A green CI build and another video are required to tell which link
is missing. The trace follow-up was later built and flashed as documented
below; its on-device GUI result remains unverified because no post-reboot
screen capture or device enumeration is available.

## Trace build and reboot — 2026-10-26

CI run `40257589855` exposed that the original `0124` framebuffer hunks were
based on the pre-`0123` source layout. Commit `cddfa2a` rebuilt those hunks
against the exact post-`0123` source from green run `40252779285`. Strict CI
run `40258406080` then passed patch application, XNU compilation, the host
bounds checks, the feature manifest and artifact packaging. Patch status
records `0124-veux-display-enumeration-trace.patch APPLIED`.

The CI kernel SHA-256 is
`d9df6c247e6da4f7b39840c273a1a4edd19b277d86e1d62729e42ea4c88b739a`.
The wrapper at
`shim/out/veux-xnu-40258406080-rw-gui/shim-boot-veux-xnu-40258406080-rw-gui.img`
was reconstructed from the previously verified boot-v2 shim/header, the CI
kernel and the shim ADT, with the known phone `dtb_1.dtb`. The independent
wrapper verifier passed; wrapper SHA-256 is
`bc3e23941a64cf27ea2aefd6820730503b692a1eb2fa5c462b5bbcf55d6bf25f` and the
DTB SHA-256 remains
`08284b0f3b0d3810abda6d617598370099f36f0f54110668bfe89f6ee35b4e2e`.

The user requested flashing this wrapper. Fastboot identified serial
`4078cac030c8`, product `veux`, unlocked state, active slot B and `boot_b`
size `0x8000000`. It wrote only `boot_b` successfully and accepted reboot;
no userdata or other partition was written, and the entitlement-repaired root
was preserved. After reboot neither ADB nor Fastboot enumerated. This confirms
the wrapper write/reboot sequence only; it does not confirm the new build ID,
display-service trace output or GUI handoff on-screen. Obtain a new screen/video
capture before claiming on-device GUI validation.

## Follow-up screen evidence — IMG_0735.mov and IMG_0736.mov

Both clips remain on the kernel diagnostic framebuffer with no GUI handoff.
IMG_0735.mov (6.0 s) shows SpringBoard SIGTRAP and no visible build ID or
`VEUX GUI` marker. IMG_0736.mov (8.1 s) shows the new trace line
`VEUX GUI: IOMFB user client provider=AppleCLCD framebuffer=1`. This reaches
the IOMobileFramebuffer user-client start hook and confirms the provider casts
to `AppleCLCD`; the line is emitted before `IOUserClient::start` returns, so it
does not by itself prove client initialization completed.

IMG_0736 still shows SpringBoard SIGTRAP at PC `0x1b0814ca8` with slide
`0x146ac000`. The unslid PC is `0x19b968ca8`, the same
`-[FBSDisplayMonitor _initWithBookendObserver:transformer:]+1160` nil-main-
`CADisplay` trap established above. No first-valid-present marker or GUI
handoff is visible. The screen does not show the CI build ID, so the trace line
is evidence that patch 0124 code ran, but the exact run attribution is not
visibly confirmed. The next investigation should follow how the started
IOMobileFramebuffer client becomes a `CADisplay` entry and inspect the adjacent
`IOMFB_FDR_Loader` exit (status 1) visible in the same clip. Its root launchd
plist runs it for the `com.apple.fdr.load` matching event when a service has
`IOMFBLaunchFDR=true`; the nonzero exit is worth investigating but does not by
itself explain the missing `CADisplay`. No new phone write was made for these
clips.

## Earlier boot-state clips — IMG_0731.mov through IMG_0733.mov

The user identified these three clips as earlier boot-state footage than
IMG_0735/0736. They show the early kernel sequence: `AppleCLCD` starts from
`disp0`, the ADT framebuffer passes validation, the physical surface and
mapping/workloop/lock/client array are created, the service registers at
1080x2400, and `/arm-io` contains `disp0`. Nub publication and AppleCLCD startup
are therefore not the remaining gap.

The exact payload embedded in wrapper 40258406080 was checked directly. Its
ADT contains `/arm-io/disp0` with `device_type=display-subsystem`,
`compatible=sweet,display`, canvas 1125x2436, plus the validated
`/chosen/framebuffer@85200000` region 1080x2400, stride 4320, format
`a8r8g8b8`. This rules out a stale local `shim/out/veux.adt` as evidence about
the flashed wrapper; the local generated file was from an older build and
lacks `disp0`, while the actual embedded ADT is correct.

Patch 0125 makes the display geometry explicit on the live IOKit provider,
disables panel-FDR loading for the software-only provider, and logs user-client
initialization and successful start with the process name. The FDR loader's
status-1 exit is adjacent evidence, not yet established as the cause of
SpringBoard's nil display. The next CI build and boot test must check which
process opens the client, whether selectors are called, and whether a first
valid software present occurs. No GUI fix or successful hardware result is
claimed from these clips.

### Registry-property experiment 40262764380

The earlier IMG_0731–IMG_0733 clips show AppleCLCD starts from `/arm-io/disp0`, validates and registers the 1080x2400 framebuffer, and finds the display nub. The later IMG_0736 clip reaches the IOMobileFramebuffer user-client hook with AppleCLCD as provider, then SpringBoard traps at the known nil-main-CADisplay branch. This narrows the remaining gap to display enumeration/registration after service startup but does not identify its exact cause.

Patch 0125 explicitly republishes display-subsystem type and canvas geometry on the live AppleCLCD provider, suppresses panel FDR launch for the software-only framebuffer, and emits user-client init/ready process markers. Disabling FDR is an experiment; the observed loader exit was not proven causal.

CI [40262764380](https://github.com/59c84486t9-alt/ios-veux/actions/runs/40262764380) passed strict patch application, XNU compilation, bounds checks, manifest, packaging, and artifact upload. Kernel SHA-256 is `2149765497827cc6ed2cd516a0e369d85062037dd5b0aada76382a9cfab60167`. Wrapper SHA-256 is `d1589c81376e77dc9640b0c5d53c499d5915b6f08feea0c18fc5cc8bf844b2a5`; its adjacent manifest records exact payload/ADT/DTB/boot-argument checks. The wrapper reused the exact shim kernel and header from the previously verified 40258406080 wrapper because local `shim/out/Image` did not match those embedded shim bytes; host console test passed.

The verified wrapper was flashed only to `boot_b` on serial `4078cac030c8` (product `veux`, slot B; partition size 128 MiB); transfer and write returned OKAY, as did reboot. No userdata was written. Immediately after reboot ADB and Fastboot were both absent. There is no visible 40262764380 build ID or GUI handoff evidence yet, so the experiment is flashed but its runtime outcome is unresolved.

### IMG_0738–IMG_0740 and IOMFB client fallback 40265617103

The three clips show SpringBoard launching, then `IOMFB_FDR_Loader` initializing an IOMFB user client with AppleCLCD as provider, followed by loader SIGABRT, driverkitd termination, and backboardd SIGABRT. IMG_0740 continues the SpringBoard crash loop at the same nil-main-CADisplay trap (`0x1b75c8ca8`). No client-ready marker or GUI handoff is visible. The logs confirm user-client initialization/provider discovery, but do not establish whether `start` completed before the loader abort.

Patch 0126 sets the FDR suppression property on both the framebuffer nub and AppleCLCD service, initializes user-client state explicitly, and allows the VEUX software client to finish registration if its superclass start rejects it. This tests the observed client/FDR path; the clips do not prove FDR is causal.

## Early boot evidence — IMG_0742.mov through IMG_0744.mov

All three clips show the 0126 FDR marker with `provider=1 service=1`, and
AppleCLCD reaches its validated 1080x2400 framebuffer registration. The clips
end before any `IOMFB client initialized/ready`, SpringBoard launch, or
CADisplay result, so they do not establish whether the client fallback fixes
the earlier display failure. No CI run ID is visible; the FDR marker confirms
that the corresponding patch code is present but does not uniquely identify
the flashed build.

IMG_0744 shows `FIPSPOST_USER` passing, then the keybag boot task attempts
`/usr/bin/true` and gets `errno=2` with `path_errno=0`; launchd immediately
reports the optional boot task is not present and starts the usermanagerd boot
task. A separate diagnostic line reports PID 11 named `launchd` exiting with
SIGHUP. This is not PID 1 and the clip contains no evidence that the main
launchd exits. These records do not explain the absent `CADisplay`.

After reviewing the clips, a read-only reboot of the already-flashed slot-B
wrapper returned OKAY; after 20 seconds neither ADB nor Fastboot enumerated.
No partition was written during this check. The next useful runtime evidence
must extend beyond the early usermanagerd boot task and show the client-ready
marker or the subsequent SpringBoard/backboardd result. The 0126 CI and
verified `boot_b` flash remain successful build/write milestones, not GUI
validation.

CI [40265617103](https://github.com/59c84486t9-alt/ios-veux/actions/runs/40265617103) passed the strict build and all feature checks. Kernel SHA-256: `9402dc7e1033db8e72d5be67e03e93644f0609a37af9f141e8dd5f68b70af7b1`. Verified wrapper SHA-256: `7c33d9018630e6d0cc3c56136c58fd1136f05052b10272a68bbea6b1ab0a5b3a`. The wrapper was flashed only to slot-B `boot_b`; transfer, write, and reboot returned OKAY. No userdata was written. ADB and Fastboot are absent immediately after reboot, so this build's on-device runtime outcome remains unverified.

## Same-boot failure evidence — IMG_0747.mov

The user identifies IMG_0747 as later footage from the same boot sequence as
IMG_0742–IMG_0744. It shows backboardd aborting and SpringBoard repeatedly
trapping. The SpringBoard PC is `0x1c9e84ca8` with slide `0x2e51c000`, giving
unslid `0x19b968ca8`, the known
`-[FBSDisplayMonitor _initWithBookendObserver:transformer:]+1160` nil-main-
`CADisplay` branch. No IOMFB client-ready or first-present line is visible in
this clip, and there is no build ID. This confirms that the observed boot did
not reach the GUI, but it does not identify which display-list step failed.

The iOS 16 IOMobileFramebuffer discovery path reads `dfr`, `AppleTV`, and
`external` from each matching framebuffer service. AppleCLCD already publishes
`external=false`; patch 0127 explicitly sets the three flags to false on the
software framebuffer service and logs setter results. This is a targeted
metadata hypothesis. Strict CI and a verified slot-B wrapper are required
before the experiment is flashed; on-device success still requires a later
client-ready/first-present marker and no SpringBoard trap.

### Patch 0127 build and wrapper — CI 40268776775

Patch 0127 applied with zero fuzz and the strict CI run passed XNU compilation,
synthetic framebuffer bounds checks, source/binary feature-manifest checks,
build-tree packaging, and artifact upload. Kernel SHA-256 is
`e5e5715c365cc0390b59bc0fa6510e2fae94d862e2a4b4e0c982a53a86b7c062`.

The boot-v2 wrapper was assembled from that exact CI kernel, the previously
verified shim kernel, the same embedded ADT as the prior wrapper, and phone
DTB SHA-256 `08284b0f3b0d3810abda6d617598370099f36f0f54110668bfe89f6ee35b4e2e`.
The independent verifier passed CI-kernel reconstruction, payload, DTB,
build/run ID, boot-args, and patch-status checks. Wrapper SHA-256 is
`21d6bb6a2bf80d84d6ef11a7bcd76924664e5083d46f7f0f8851faa47e32b7e7`.
The image is ready at
`shim/out/veux-xnu-40268776775-rw-gui/shim-boot-veux-xnu-40268776775-rw-gui.img`.

The first flash attempt was deferred because the phone was absent from
Fastboot, ADB, and USB enumeration. After the user reconnected it in Fastboot,
the device reported product `veux`, unlocked, slot B, and `boot_b` capacity
`0x8000000`. The wrapper hash matched its manifest. Fastboot `Sending` and
`Writing` for only `boot_b` returned OKAY, followed by reboot OKAY. No userdata
or other partition was written; the entitlement-repaired root remains in
place. ADB and Fastboot were absent 15 seconds after reboot. The GUI result
still requires later on-device evidence for client-ready/first-present and
SpringBoard outcome.

## IMG_0757 follow-up — patch 0127 boot evidence

The attached photo shows the VEUX boot log through AppleCLCD registration:
validated 1080x2400 software framebuffer, surface/mapping/workloop/lock setup,
and `IOMFB list properties dfr=1 AppleTV=1 external=1`. These are the
`setProperty` success results, not the stored boolean values; patch 0127 sets
each property to false. The photo does not show an IOMFB client initialized or
ready marker, a first-present marker, or the GUI handoff. Its patch-specific
property log confirms patch 0127 code ran, but the crash clips do not display a
build ID.

Both attached 8.05-second clips show the same crash-report screen. SpringBoard
exits with signal 5 / `EXC_BREAKPOINT`; backboardd later aborts, and watchdogd
reports its software service check-in as OK. The OCR-transcribed SpringBoard
PC is `0x1cd158cab` with slide `0x24af0000`, giving an unslid address near
`0x1a8628cab`. The repaired iOS 16.7 shared cache maps that address to
`GameCenterUI.AchievementHighlightLayout.init(metrics:decorationView:titleText:subtitleText:orientation:)`
around offset +0x47. The stack includes `FBDisplayManager.sharedInstance`
and `FBSystemShellInitialize`, so this is during early SpringBoard display
setup, but it is a different reported PC from the previously symbolicated
FBSDisplayMonitor+1160 trap. The OCR PC ends unaligned for arm64; treat the
nearest-symbol result as a lead until a sharper crash frame or a captured crash
report verifies the exact register value.

The same frame reports FAR `0x2068e5b28`. The nearest aligned instruction in
the recovered cache is the `stp q0, q1, [x21, #0xa0]` inside that Swift
initializer. This is consistent with the fault occurring while the layout
initializer writes its result, rather than at the earlier explicit
FBSDisplayMonitor breakpoint. It does not identify why the destination is
invalid, and the phone-provided register transcription still needs confirmation.

The new evidence verifies AppleCLCD setup and successful property writes, but
does not establish that IOMFB created a `CADisplay` or completed a client open.
Patch 0127 therefore has not demonstrated a GUI fix. Preserve that distinction
when selecting the next display-enumeration experiment.

## Recovery-side crash-report search — 2026-10-26

At the user's request, selected slot A and rebooted into recovery. Fastboot
reported serial `4078cac030c8`, product `veux`, unlocked, current slot B before
selection; `fastboot set_active a` and `fastboot reboot recovery` both returned
OKAY. Recovery ADB connected as root using the host's libusb backend. No phone
partition was written.

Recovery does not mount the iOS `userdata` HFSX volume and its kernel has no
HFS+ driver. Read-only inspection of `/dev/block/sda22` showed a 16-GiB HFSX
volume. A temporary local copy of exactly that 16-GiB volume was mounted
read-only after running `fsck_hfs -fy` on a copy-on-write clone only; the
original capture and phone partition were not repaired or modified.

No SpringBoard `.ips`/`.crash` files were found in the standard CrashReporter
locations (`/private/var/mobile/Library/Logs/CrashReporter` and
`/private/var/logs/CrashReporter`); the CrashReporter directory contained only
`Assistant` and an empty `DiagnosticLogs` directory, and the Panics directory
was empty. The captured raw images were deleted after the search. This means no
saved SpringBoard report is available from this recovery snapshot; it does not
prove that no report was ever created before the crash/reboot.

## Next diagnostic candidate — patch 0128

Since the app-level report was not persisted and recovery pstore is empty, the
next run needs to report the display path at the moment SpringBoard or
backboardd exits. Patch 0128 adds a compact kernel snapshot of AppleCLCD
registration, FDR/display-list property setter results, IOMFB client init/ready
counts and callers, selectors seen, last selector caller, swap calls, and the
first successful software present. It emits only on SpringBoard/backboardd
exit and does not alter display behavior. The candidate compiled against the
402687 build tree. Strict CI and a verified boot wrapper have now passed; the
remaining gate is on-device evidence from the boot below. This is intended to
make the next failure actionable, not to claim a GUI fix.

### Patch 0128 diagnostic build and boot_b flash — CI 40329697379

Strict CI [40329697379](https://github.com/59c84486t9-alt/ios-veux/actions/runs/40329697379)
passed on commit `e899b868b4ef8d9ee64a6f499aeef67dade56361`. XNU compilation,
host framebuffer bounds checks, the kernel feature manifest, build-tree
packaging, and artifact upload all succeeded; `0128-veux-gui-exit-summary.patch`
is marked APPLIED. Kernel SHA-256 is
`29337e2eb8323317f0275597b49335d1540cd5c613b802fb662d6e898a5ce984`.

The boot-v2 wrapper uses that exact CI kernel, the previously verified shim
kernel/header and embedded ADT, and phone DTB SHA-256
`08284b0f3b0d3810abda6d617598370099f36f0f54110668bfe89f6ee35b4e2e`. The
independent wrapper verifier confirmed payload reconstruction, build/run ID,
boot arguments, DTB, and patch status. Wrapper SHA-256 is
`e35b50e5920c2bb3575a8f30f6f51fcb52f9412239e7608ebf5cb2413d9488b2`; image:
`shim/out/veux-xnu-40329697379-rw-gui/shim-boot-veux-xnu-40329697379-rw-gui.img`.

Fastboot identified serial `4078cac030c8`, product `veux`, unlocked `yes`,
and `boot_b` capacity `0x8000000`. Flashing only `boot_b`, selecting slot B,
and rebooting returned OKAY. No userdata or other partition was written; the
entitlement-repaired root was preserved. After reboot, neither ADB nor Fastboot
enumerated on the host at the 10-second check. This confirms the flash/reboot
sequence, not that the kernel reached the GUI. The next evidence needed is a
screen capture showing build ID `40329697379` and the exit summary, especially
IOMFB client/selector/present counts and SpringBoard/backboardd exit status.

## IMG_0763 boot evidence — patch 0128 diagnostics

Both clips show the new exit-summary code, confirming the patch-0128 boot.
The initial frame repeats AppleCLCD registration at 1080x2400 and successful
property setter calls (`FDR policy provider=1 service=1`; `dfr`, `AppleTV`,
and `external` each report setter success). These are write-success flags, not
the stored values.

The summary reads `registered=1 fdr=0x3 list=0x7 init=1/0:IOMFB_FDR_Loader
ready=1:IOMFB_FDR_Loader last=4294967295/none selectors=0x0 swaps=0 present=0`.
So the AppleCLCD service registered, and the only user-client init/ready
recorded before SpringBoard's exit belongs to `IOMFB_FDR_Loader` (type 0).
No selector reached the kernel framebuffer client, and no swap or software
present occurred. The evidence places the gap before a window-server display
client reaches the service; it does not show whether IOMobileFramebuffer's
matching callback rejected the service or whether SpringBoard failed earlier
while obtaining a display list.

The SpringBoard report shows PC `0x1dbcf4ca8`, slide `0x4038c000`, yielding
unslid PC `0x19b968ca8`. The local 20H392 shared cache resolves this exactly to
`-[FBSDisplayMonitor _initWithBookendObserver:transformer:]+1160`, the same
nil-main-CADisplay trap as earlier boots. SpringBoard exits with signal 5;
backboardd later exits with signal 6, and lockdownd reaches the “Too many
corpses being created” limit. The clips do not show a successful GUI handoff.

The next code investigation should focus on the IOMobileFramebuffer display
list matching path and its main-display selection. The summary narrows the
failure to enumeration/connection before any selector or present; changing
framebuffer rectangle handling or surface copy code cannot address this
failure point.

## Recovery Unified Log findings and sandbox policy candidate

The user authorized recovery ADB, which connected as root. A read-only copy of
the previous boot's HFSX root contains no saved SpringBoard `.ips` or `.crash`
report. It does contain about 92 MiB of persisted tracev3 logs. The UUID text
directory is empty, so parsing recovers launchd lifecycle records but not
framework format strings. These files span eight boot UUIDs; their totals are
not evidence for any single build.

Across those boots, launchd records repeated `error = 159: Sandbox restriction`
lookups from SpringBoard, including `com.apple.backboard.system-app-server`,
`com.apple.CARenderServer`, and `com.apple.chronoservices`. Backboardd lookup
denials include `com.apple.iohideventsystem`, `com.apple.mobilegestalt.xpc`,
and `com.apple.containermanagerd`. The same persisted boots show SpringBoard
SIGTRAPs and backboardd SIGABRTs. This reproduces a known gap in the boot
configuration: patch 0099's VEUX Sandbox compatibility policy is opt-in via
`veuxsandbox=1`, but the flashed wrapper omitted that argument. The kernel
build's patch-status file confirms 0099 is applied. The missing policy is the
strongest current explanation for backboardd failing before display discovery;
it is not yet proven to resolve `CADisplay` enumeration.

The next wrapper reuses green CI 40329697379's exact kernel and phone DTB and
adds `veuxsandbox=1` plus `veuxiolog=backboardd,SpringBoard`. The exact kernel
SHA-256 remains
`29337e2eb8323317f0275597b49335d1540cd5c613b802fb662d6e898a5ce984`, and the
locally reverified wrapper SHA-256 is
`6f4ff70eb38990a9cc454b21d917d23655d92e56188056ebf1109ccd563b6786`.
No XNU source changed, so this reuses the successful CI result. It is ready to
flash only to `boot_b` after Fastboot reconnects. Fastboot later reported
serial `4078cac030c8`, product `veux`, unlocked state, current slot B, and
`boot_b` size `0x8000000`. Only `boot_b` was written; selecting B and rebooting
returned OKAY. No userdata write occurred. ADB and Fastboot did not enumerate
at the 10-second check, so the sandbox-enabled runtime effect is still
unobserved. The next evidence should show `VEUX Sandbox: permissive policy
registered`, whether backboardd reaches IOMobileFramebuffer matching/open, and
whether SpringBoard gets a main `CADisplay`. CI/build success and flash success
do not establish GUI success.

## IMG_0777–IMG_0778 sandbox-enabled boot evidence

The still repeats patch-0127's successful AppleCLCD registration at 1080x2400
and successful FDR/display-list property setter calls. These values confirm
provider setup only; they do not show framework display enumeration or GUI
handoff.

Both clips show `SWEET Sandbox: ... op ...` callbacks for `containermanager`,
`distnoted`, and `cfprefsd`. The sandbox syscall hook is therefore active in
these boots, although the explicit policy-registration result line is not
visible. IMG_0777 shows launchd starting SpringBoard, then `driverkitd` SIGKILL
and `logd privilege 1002 denied`. IMG_0778 shows backboardd SIGABRT (Mach
exception namespace 2/code 6), followed by `IOMFB_FDR_Loader` SIGABRT. Neither
clip exposes the patch-0128 exit summary, build ID, or a readable SpringBoard
main-display result. The register dump is not a SpringBoard crash report.

This evidence means the previous sandbox-omission hypothesis is insufficient:
the sandbox syscall callback is running, but privilege checks are a separate
MAC hook. Current code grants only `PRIV_WORK_INTERVAL` and returns `EPERM` for
other privilege requests. The `logd` denial is visible, but does not establish
that it caused the display failure. Next correlate per-process privilege
denials with the `IOMFB_FDR_Loader` and backboardd stack traces, then use the
0128 exit summary to check whether any IOMFB client issued selectors or
presented a frame.

The host detected the phone in Fastboot on slot B. `fastboot reboot recovery`
returned OKAY, but neither ADB nor Fastboot enumerated afterward. No new
recovery log read or partition write occurred during this check. The
entitlement-repaired root remains preserved.

## Recovery crash reports: `canvas-width` and `canvas-height` must be CFData

After selecting slot A and rebooting to recovery, the user approved ADB; the
host connected as root. Recovery pstore and `/proc/last_kmsg` are empty. A
read-only capture of the first 16 GiB HFSX volume was made on the host. The
volume was repaired and mounted only through an APFS copy-on-write clone; the
phone's userdata was never modified.

The captured CrashReporter directory contains two
`IOMFB_FDR_Loader` `.ips` files at 60 and 82 seconds uptime, plus repeated
backboardd reports through 640 seconds uptime (50 consecutive backboardd
crashes). It has no `SpringBoard*.ips` report. The IOMFB loader's main-thread
exception backtrace is:

`-[NSObject doesNotRecognizeSelector:]` → `getEDTProperty+104` →
`IOMobileFramebufferOpen+160` → `iomfb_get_display`.

The iOS 16.7.16 `IOMobileFramebuffer` implementation disassembly shows
`getEDTProperty` looks up `canvas-width` and `canvas-height`, then calls
`CFDataGetLength` on the property value. VEUX's patch 0125 had published those
values with `setProperty(key, uint64, 32)`, which constructs an `OSNumber`.
That object is not the `OSData`/`CFData` expected by this framework path, so
the unchecked call throws `doesNotRecognizeSelector`. The latest backboardd
report confirms the same failure reaches display discovery:
`IOMobileFramebufferCreateDisplayList+252` →
`CA::WindowServer::display_count_of_type` →
`-[CAWindowServer _detectDisplays]`.

Patch 0125 now uses `IORegistryEntry::setProperty(key, bytes, length)`, which
stores the 32-bit framebuffer geometry as `OSData`. The changed patch applies
with zero fuzz after patches 0123 and 0124. `tools/xnu-cc.py` compiled the
changed `SweetFramebuffer.cpp` against successful CI 40329697379's build tree
with 0/1 failures. This is a source-supported root-cause fix for the observed
display-list crash. CI 40356435384 subsequently passed, and its wrapper was
independently verified and flashed to `boot_b` as documented below. On-device
IOMFB client selectors/presents and GUI handoff are still unconfirmed.

The first CI attempt for this fix (40355196690) stopped during patching:
0126 still expected the previous numeric canvas setters. Its context now
follows 0125's byte-data properties; the next CI run confirmed the full ordered
patch stack and kernel build.

CI 40356435384 completed green with patches 0123–0128 applied. The verified
wrapper built from its kernel and patch-status artifact was flashed only to
`boot_b`; Fastboot confirmed the write, slot B selection and reboot. The
immediate post-reboot USB check found neither ADB nor Fastboot. This confirms
the flash sequence only; GUI success still requires on-device boot evidence.

## Follow-up: display-list `device_type` type mismatch

The recovery-captured backboardd report at 640 seconds provides a second,
independent property-type failure. Its terminating exception is thrown from
`__IOMobileFramebufferCreateDisplayList_block_invoke+316`; the caller is
`IOMobileFramebufferCreateDisplayList+252`, then
`CA::WindowServer::display_count_of_type` and
`-[CAWindowServer _detectDisplays]`. Disassembly of the exact iOS 16.7.16
shared-cache image shows this display-list block enumerates children of
`IODeviceTree:/arm-io`, reads each child's `device_type`, and calls
`CFDataGetLength`/`CFDataGetBytes` before comparing it with
`display-subsystem` and `ext-display-subsystem`.

The report's `imageOffset=31420` maps to the instruction immediately after
`CFDataGetBytes` in the iOS 16.7.16 display-list block, but it does not identify
which `/arm-io` child supplied the bad object. The captured report has no unique
build ID, so its presence on the userdata volume does not prove it came from
CI 40369369423.

### Follow-up: normalize all `/arm-io` display types

The earlier theory that `device_type` on `disp0` was an OSString was incorrect.
XNU has a two-argument string setter and a three-argument `void *` byte-data
setter; patch 0125 calls the latter because it supplies a length. Its original
`char *` buffer already becomes OSData. The explicit cast in commit `bed5c50`
does not change runtime behavior. Apple's implementation is visible in
[IORegistryEntry.cpp](https://github.com/apple-oss-distributions/xnu/blob/main/iokit/Kernel/IORegistryEntry.cpp).

Patch 0129 now works on the actual `IODeviceTree` `/arm-io` node before the
display nub is published. It canonicalizes `disp0` to NUL-terminated
`display-subsystem` OSData, converts any string-valued sibling `device_type` to
OSData, and replaces missing or unexpected values with empty OSData. It logs
each child's type and data length. This covers a wrong property on any child,
which the framework's display-list loop reads with `CFDataGetBytes`; whether
that is the captured failure remains a hypothesis until the next crash report
or successful display enumeration confirms it.

The first CI run for the redundant cast, 40380782893, was canceled after
correcting the overload analysis. Patch 0129 compiled locally against the
40369369423 packaged build tree (0/1 failures), and its patch applied exactly
to that tree.

CI **40369369423** then passed on commit `1f46527d7c86d956da5c2ee27fc379f8ee099e72`:
the ordered patches, XNU build, synthetic framebuffer bounds checks, feature
manifest and artifact packaging succeeded. Patches 0123–0128 are APPLIED; the
CI kernel SHA-256 is
`09be0aeefe7d435a5895f7cf886cfc795fe216e91633caf7ab86afc014dea663`.
The new payload and wrapper were independently verified against that exact
kernel, the retained verified shim/header, embedded ADT and phone DTB. The
wrapper SHA-256 is
`2a7badfbd2139f9ff472754f33f48d138b7ca42da84f8304e437afa92652d628`.

Fastboot identified serial `4078cac030c8`, product `veux`, unlocked state,
slot A active, and `boot_b` capacity `0x8000000`. The wrapper was written only
to `boot_b`; transfer and write returned OKAY, slot B selection returned OKAY,
and reboot returned OKAY. The entitlement-repaired root image was preserved.
Neither ADB nor Fastboot enumerated at the 15- and 45-second checks after
reboot. This is a green build and successful flash, but the display-list fix
and SpringBoard GUI are not yet confirmed on-device. The next runtime capture
should show build ID 40369369423, no backboardd display-list exception, and an
IOMFB client/selector/first-present followed by SpringBoard handoff.

### CI 40384236283 and the latest runtime clip

CI [40384236283](https://github.com/59c84486t9-alt/ios-veux/actions/runs/40384236283)
passed with patch 0129 applied. The independently verified wrapper is
`shim/out/veux-xnu-40384236283-iomfb-type-normalization/shim-boot-veux-xnu-40384236283-iomfb-type-normalization.img`,
SHA-256 `7024eba36ca05c9c17cee70bb342b1890b40d64eeffc5751da64e3445e711d76`.
Its manifest checks the CI kernel payload, embedded ADT, phone DTB and boot
arguments. This verification is separate from proof that the wrapper is
currently installed; Fastboot's `fetch` command is unsupported on this device.

The user's latest 90.69-second clip shows the kernel diagnostic display, then
repeated backboardd IOKit matching requests for `IOAcceleratorES` returning
`0 found`, then the Apple logo at approximately 80 seconds. These are zero
accelerator matches, not evidence that IOMFB matching itself returned zero.
The clip ends without showing a GUI, panic reason, or ten-minute wait. The
attached still shows the Apple logo only. Neither confirms a SpringBoard
handoff or explains the later report of an asterisk.

Current host-side Fastboot checks found `veux`, unlocked, slot B active, and a
128 MiB `boot_b`; ADB was absent. The user-authorized read-only recovery route
selected slot A and rebooted to recovery. ADB now sees the phone as
`unauthorized`, despite loading the existing host key; no recovery data has
been read. The next step is to accept the USB debugging prompt on the phone,
then read pstore/last-kmsg and the current boot logs before changing the
kernel again. No partition or userdata was written in this handoff.

### Recovery follow-up: 403842 readback and the persisted ring

The user enabled ADB; recovery ADB is root on serial `4078cac030c8`, slot
`_a`. `/sys/fs/pstore` is empty and `/proc/last_kmsg` is absent. A read-only
readback of the first 17,203,200 bytes of `boot_b` matches the verified 403842
wrapper exactly (SHA-256
`7024eba36ca05c9c17cee70bb342b1890b40d64eeffc5751da64e3445e711d76`). This
confirms the currently installed B image; the clip itself has no readable
build ID, so it cannot independently identify the image used while filming.

The bounded ring pull returned 16,990 bytes, flush sequence 16,990, SHA-256
`3267a899aa0978bd583a7d4e3de0a8714c72c5ccff6c9de8f724936d9eb89dbd`. Its
boot-args record has `veuxlog=1` but lacks 403842's `rootrw=1 ufsrw=1`,
`veuxsandbox=1`, `veux_gui=1`, and `veuxiolog=backboardd,SpringBoard`, so it is
from an older boot and cannot explain the latest 0129 result. That earlier
read-only boot failed launchd `mount-phase-1`: `mount_hfs` received
`Read-only file system`, then BindFS could not find
`/private/preboot/<boot-manifest-hash>/usr/standalone/firmware` (`ENOENT`).
Launchd requested a panic and reboot. The sequence is a useful explanation for
the earlier reboot loop only.

The 403842 boot arguments omit `veuxlog=1`, so no boot-specific ring was
written for that test. To identify why the latest run stayed at the Apple logo,
a diagnostic wrapper with the existing logger was prepared. The user has since
authorized repeated writes to `boot_b` and explicitly prohibited writes to
`boot_a`.

A temporary 403842 diagnostic wrapper is prepared at
`shim/out/veux-xnu-40384236283-iomfb-type-normalization-veuxlog/shim-boot-veux-xnu-40384236283-iomfb-type-normalization-veuxlog.img`
(SHA-256 `a793e3e8c8bf5580c2e4ab8cd99974fb82158acdc94ee4fdea2db4f690e7a742`).
The only binary change from the currently installed image is the added
`veuxlog=1` payload boot argument; image size and outer kernel/header/DTB are
unchanged. It retains `rootrw=1 ufsrw=1`, so booting it leaves the HFS root
writable and writes the bounded logger ring. A temporary `fastboot boot`
attempt returned `remote: 'unknown command'`; it did not boot or write the
image. The user then authorized flashing this candidate to `boot_b`, while
explicitly prohibiting writes to `boot_a`. Fastboot send/write, slot-B
activation, and reboot returned OKAY. No other partition was written. After
reboot, ADB
and Fastboot did not enumerate at the immediate check or repeated checks over
30 seconds; `lsusb` also showed no phone USB device. This is only a host-side
USB observation: display state, boot stage, reset, and power state are unknown.
The log ring has not yet been pulled. Next, the user must force Fastboot with
Power + Volume Down; then verify the phone before selecting slot A and rebooting
to recovery for `tools/veux-log-pull.sh`. Keep `boot_a` untouched.

### The 403842 ring identifies the current blocker

After the user returned the phone to Fastboot and enabled ADB, Fastboot
confirmed serial `4078cac030c8`, product `veux`, slot B. Selected slot A and
rebooted to recovery; no write to `boot_a` occurred. Recovery ADB connected as
root. The recovered ring is 1,010,909 bytes (flush sequence 1056; SHA-256
`684a7a74845e02f187c5fd89a405b9a534f81a327835f4affa45e0b1965e72dc`) and
identifies build `40384236283` with `rootrw=1 ufsrw=1 veuxlog=1`.

The HFS `iOSRoot` mount and journal replay succeed, launchd continues, and
backboardd opens AppleCLCD. IOMFB client initialization/readiness succeeds; the
GUI summary records the display service and list, two surface swaps, and a
first valid software present. SpringBoard then repeatedly exits via SIGTRAP
(signal 5, code `0x600000001`) at PC/LR `0x1badc28c0`, with a stable backtrace.
The “Too many corpses” records are downstream of that restart loop. The boot is
therefore past root mounting and first display presentation; the log does not
capture the reason for SpringBoard's failure.

To capture it, a wrapper from the same verified build added only
`veuxscan=SpringBoard` while retaining the bounded logger. The kernel, DTB, and
all other payload bytes match the prior verified wrapper; image size remains
17,203,200 bytes. The user authorized repeated writes to `boot_b` and forbade
`boot_a`; only `boot_b` was flashed, slot B selected, and reboot returned
OKAY. The user reported the small mark under the Apple logo appeared almost
immediately, then returned the phone to Fastboot. Recovery ADB on slot A
returned a scan ring of 224,297 decoded bytes (raw ring 224,537 bytes, flush
sequence 157; decoded SHA-256
`6233238d5f4ed895ba36d21fdbb8a6198d3eb1b4ff6107679ca024b9c1522905`). The
confirmed boot args include `veuxlog=1 veuxscan=SpringBoard` for build
`40384236283`.

The heap scan ran on the first SpringBoard SIGTRAP but captured only FrontBoard
listener strings and `Version 16.7.16 (Build 20H392)`, not the assertion reason.
The trap PC/LR is `0x1b76968c0`, slide `0x9290000`, unslid `0x1ae4068c0`, FAR
`0x1e6ea4f40`. Several unrelated daemons trap at the same PC, so the address
alone does not prove an FBSDisplayMode failure. The embedded ADT already has
`/chosen/display-scale=3`.

The logger changed its bounded final 4 MiB + 4 KiB userdata region. After
preserving the decoded scan log, restored that exact 1,025-block range from
`backup/veux-device/userdata-tail-pre-veuxlog.bin`; readback matches its
pre-logger SHA-256 `06955cde7f98b9503653b906e9634732d59a17a6dc2cb1a0e453fbdd4adaab86`.
No other userdata range or `boot_a` was written. The phone remains in slot-A
recovery; `boot_b` retains the scan wrapper.

### SpringBoard crash report identifies missing AppleKeyStore — 2026-10-26

The read-only HFS+ image of the 16 GiB iOS root volume contains four
SpringBoard `.ips` reports for build `20H392`. The latest report,
`SpringBoard-1969-12-31-173201.00016.ips`, records uptime 5,500 seconds and
111 consecutive SpringBoard crashes. Its main-thread stack is
`MKBEventsRegister.cold.2` → `MKBEventsRegister` → `-[SBFMobileKeyBag init]` →
`SBUIBiometricResource` → `SBBiometricsService` →
`SpringBoard initializeSystemServicesBeforeApplicationDidFinishLaunching`.
The `MKBEventsRegister.cold.2` string is “failed to find %s service”, with the
argument `AppleKeyStore`; the breakpoint is the intentional `brk #1` in that
fatal error helper. This is the immediate SpringBoard failure after the first
display present, and explains why waiting longer cannot complete this boot.

The 403842 kernel ring independently logs
`IOService:/IOResources/AppleKeyStore -> none` and a matching query for
`AppleKeyStore` returning `none`; `init_data_protection` also reports “No SEP
present on this device.” The existing software AppleKeyStore implementation is
guarded by `#if defined(SWEET)`, and its match record is inside the SWEET board
configuration block, so neither is enabled for the VEUX build. The specific
next fix is to register that existing no-passcode software service for
`ARM64_BOARD_CONFIG_VEUX`. Patch 0130 adds the service to the VEUX match table
and compiles its existing implementation for VEUX. This may expose a later
missing-keybag or event-notification incompatibility, which should be diagnosed
from the next boot log rather than guessed at now.

The exact shared cache confirms `MKBEventsRegister.cold.2` at unslid address
`0x1ae406894`, with its `brk #1` at `0x1ae4068c0`. The report's matching
`MobileKeyBag` image UUID is `18e44f74-0a9a-3b74-b9e3-0c48f331cc03`.
