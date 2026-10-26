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
