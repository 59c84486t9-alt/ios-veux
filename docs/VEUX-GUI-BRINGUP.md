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
