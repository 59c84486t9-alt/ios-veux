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
