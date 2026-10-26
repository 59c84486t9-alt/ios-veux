# VEUX software display bring-up

## Observed blocker

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
display-list crash. It still needs a new green CI build, an independently
verified wrapper from that artifact, and on-device evidence of IOMFB client
selectors/presents and GUI handoff.

The first CI attempt for this fix (40355196690) stopped during patching:
0126 still expected the previous numeric canvas setters. Its context now
follows 0125's byte-data properties; a rerun is required to validate the full
ordered patch stack before creating or flashing a wrapper.
