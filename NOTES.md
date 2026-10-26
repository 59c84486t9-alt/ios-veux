## >>> UPDATE 2026-10-25 (launchd main-thread diagnostics and offline job cache audit) <<<

- Added `xnu/patches/0121-veux-launchd-main-stack-exec-trace.patch`. It samples
  launchd pid 1's first task thread on every 10-second liveness pass, prints
  that main thread's wait kind/event/user PC, and attempts up to 12 kernel
  frames each pass. An unattempted capture prints `skipped: no-main-thread` or
  `skipped: no-kernel-stack`; an attempted capture says `skipped: none` and
  reports result/frame count. These are kernel frames, not EL0 user frames.
  The existing per-thread wait inventory remains signature-gated.
- Patch 0121 adds pid-1 `posix_spawn` and `execve` result/path records, process
  exit status/signal records, and exec authorization denial messages for the
  `mac_vnode_check_exec` and `vnode_authorize` sites. This is targeted exec-path
  logging, not a complete audit of every MACF policy hook.
- Updated the workflow and `tools/kernel-manifest.py` to require patch 0121 and
  assert its main-thread repeated-stack, wait, spawn/exec, exit, and MAC-denial
  markers. Python syntax compilation and reverse applicability against the
  currently staged XNU source pass. `git diff --check` passes for the source,
  workflow, manifest, and notes changes; it reports whitespace warnings when
  run over the added unified-diff patch file itself because patch context lines
  carry the XNU source indentation. No XNU compile, CI run, wrapper build, or
  device flash was performed; the patch remains unverified on-device.
- Audited `/Volumes/iOSRoot/System/Library/xpc/launchd.plist` offline
  (SHA-256 `7b41fa308304021a90fb8dfc4ac6224e6c1841fb73e47b7f09efbdd7167c91d1`):
  530 cached daemon records; 49 enabled `RunAtLoad` entries and 3 additional
  enabled `MinimalBootProfile` entries (52 unique immediate/profile candidates).
  All 530 cached plist paths exist in the mounted root. One enabled RunAtLoad
  binary is absent: `com.apple.factory.NFQRCoded` at
  `/Developer/usr/local/libexec/NFQRCoded`; the other 51 candidates' Program
  paths exist. `configd`, `securityd`, and `trustd` are profile-only entries;
  `lockdownd` is both RunAtLoad and MinimalBootProfile. The cache does not
  encode launchd boot-task phases or a serialized startup order: RunAtLoad
  identifies eligible jobs, not proof they ran immediately after early boot.
- Wrote the complete cache-derived inventory to
  `docs/launchd-cache-inventory-2026-10-25.tsv` (530 data rows), including
  RunAtLoad, KeepAlive, profile/mode flags, Disabled, plist existence and
  Program existence. Alphabetical TSV order is not launch order.
- SWEET's local notes document boot-task completion and daemon startup: boot
  0039 reports LaunchDaemons starting (lockdownd pid 106 and identityservicesd
  pid 114 both crash); boot 0041 reports backboardd, bluetoothd, fairplayd.H2,
  SpringBoard and xpcproxy running; later v14 notes confirm SpringBoard,
  backboardd and Setup remain on screen. The raw logs referenced by those notes
  are not present in this checkout, so an exact SWEET job-by-job exec order
  cannot be recovered here. The evidence does show SWEET progressed past the
  phase where this VEUX run appears idle.

## >>> UPDATE 2026-10-24 (401511 display regression and RO baseline) <<<

- Confirmed the comparison point is run 40092567840, the last image documented
  as reaching launchd's “Early boot complete” line. Run 40151171910 removed
  `unentitled_ios_sim_launch=1`, `veuxlog=1`, `veuxfb=1`,
  `veuxfbconsole=1`, `ignition_level=1`, `launchd_unsecure_cache=1`,
  `wdt=-1`, and `wdt_test=no_user_checkin`, while adding launchd verbose log
  options. It retained `debug=0xc`, `serial=3`, `cpus=1`, `keepsyms=1`,
  `-enable_kprintf_spam`, `-noprogress`, and `rd=ufsroot0`. The read-only
  diagnostic wrapper restores the old arguments except `rootrw=1 ufsrw=1`,
  and keeps the new launchd verbose options.
- The read-only diagnostic wrapper is
  `shim/out/veux-xnu-40092567840/shim-boot-ro-diagnostic.img`, SHA-256
  `43709dc15a9bf0afe3d05abe6d56885e9124940564fd1c752895b06b542308ec`.
  It preserves the exact run-400925 kernel payload and phone DTB, changes only
  the XNU boot arguments, was flashed to `boot_b`, selected slot B, and reboot
  returned OKAY. ADB and fastboot enumeration are currently empty; visual
  confirmation of the read-only screen result is still pending. This is not a
  “good” result until a photo shows the expected build identity and cells.
- New applied patches in 401511 versus 400925 are 0117 (post-early-boot
  process liveness sampler), 0118 (stop mountroot retries), and 0119 (require
  both explicit rootrw/ufsrw flags). 0065 and 0078 were already in the
  baseline patch list; 0004/0010/0047 and the AppleKeyStore/crypto changes
  were also not new in that comparison. With `cpus=1`, the single-core setting
  remains explicit. 401511's shim addresses remain inside the same managed
  RAM interval: the image end moves by `0x4000`, ADT and boot args follow with
  no overlap, and the framebuffer alias and below-4-GiB initrd are disjoint.
- Added patch 0120 from the exact post-patch source artifact for 401511. It
  removes the `veuxfb`/`veuxfbconsole` early return, unconditionally enables
  the framebuffer marker/console, and draws the build ID directly through the
  framebuffer. Its hunk was regenerated with exact line/count context and
  applied using zero fuzz to the 401511 XNU build-tree artifact. Early stage
  cells remain boot-argument independent; source assertions now check the
  stage-cell writer and the early ARM/platform cell calls.
- The workflow default now restores the run-400925 diagnostics and boot
  settings while omitting only rootrw/ufsrw; it also retains the new launchd
  verbose flags. The strict kernel manifest requires patch 0120 and asserts
  unconditional framebuffer setup, direct on-screen build-ID output, and
  early cells. Local `validate-repo.py`, Python compilation, patch application
  to the exact 401511 source tree, workflow source assertions, and
  `git diff --check` pass. Changes are uncommitted and no new CI run has been
  dispatched yet. The 401511 wait/stall is not attributed to any one patch;
  if the read-only baseline is confirmed healthy, the next CI adds the new
  patches in groups and is not flashed until all strict checks pass.

## >>> UPDATE 2026-10-24 (strict patch audit, build identity, wrapper verification) <<<

- Kept macOS 13.5 / XNU 8796. The SWEET/VEUX staging scripts 0019, 0020,
  and 0026 explicitly pin to XNU 8796.141.3; moving to an older XNU would
  require a separate source/patch port and would not improve this audited base.
- GitHub logs were checked for runs 39805058203, 39940219041, 39942134414,
  39945294859, 39952064511, 39973136957, 40051486458, 40092567840,
  40103755855, and 40129031828. The only recurring non-VEUX skips are
  `iobuffermemd_monterey.patch` (context mismatch at
  `iokit/Kernel/IOBufferMemoryDescriptor.cpp:332`), `skywalk_sonoma.patch`
  (`bsd/skywalk/packet/os_packet.h:883`), `syntax_checker_sonoma.patch`
  (`tools/lldbmacros/core/syntax_checker.py:1`), and `TrustCache.patch`
  (its TrustCache headers already exist in XNU 8796). These have no VEUX
  behavior/build/symbol effect; they are version-specific upstream patches or
  duplicate upstream headers. All four are now explicit, signature-checked
  entries in `xnu/patches/SKIP_ALLOWLIST.txt`; if any starts applying, ceases
  to be skipped, changes failure signature, or disappears, the build fails.
- The same logs show accidental VEUX skips: 0113 and 0114 in run 39952064511,
  and 0117 in 40103755855. Those runs still passed upstream patch handling.
  Run 39952064511 had no documented packaged/flashed image; any package from
  it lacked 0113/0114. The later flashed images from 39973136957,
  40051486458, and 40092567840 show 0113/0114 applied; run 40103755855
  lacked 0117 because its first hunk did not apply. The associated observations
  (old panic photos without the dedicated 0113 console tail, and mount/UFS
  photos without 0114 helper and write status) cannot be used to infer those
  missing diagnostics. Historical 0111 read-only journal guard was present in
  39942134414 and later; the newer no-retry change 0118 was absent from all
  those images because it was added later. No historical log found a skipped
  flush/rw safeguard patch.
- `tools/strictify-dxb.py` now replaces the upstream permissive patch loop with
  zero-fuzz `git apply --check` + apply, fails on all unallowlisted failures,
  validates allowlist reason/signatures and freshness, records each patch
  outcome, and rejects any `.rej` / `.orig` file. Bash syntax was checked with
  the host `/bin/bash`; the transformed pinned builder also passes `bash -n`.
- Fixed the 0111 workflow assertion to match its new VEUX journal-guard log.
  Regenerated/updated 0117 against the current patched source shape, including
  the ring-first and screen build ID; applied/reversed it cleanly against the
  40103755855 buildtree files. It starts the process sampler after launchd's
  early-boot completion, so the build ID is visible on the framebuffer during
  early userland startup and is prepended as the persistent ring's first line.
  This is kernel text evidence only until a new photo/ring confirms hardware
  output.
- `tools/kernel-manifest.py` requires 0111/0113/0114/0117/0118 and verifies
  their final-kernel strings, build ID, panic console tail, mount diagnostics,
  no-retry message, journal guard, and synchronous ring flush. The workflow
  uploads this manifest with patch status and the kernel SHA-256.
  `tools/verify-veux-wrapper.py` rebuilds the SWEETXNU payload from the exact
  CI kernel and the ADT carried in the payload, then compares that payload and
  the outer DTB byte-for-byte with the wrapper. It records CI run/build IDs,
  kernel/payload/wrapper/DTB hashes, boot args, and patch statuses next to the
  wrapper image. Because `mkpayload.py` resolves chained Mach-O fixups, the
  payload bytes are not a raw Mach-O hash; provenance is proven by exact
  deterministic reconstruction from the CI kernel, and both hashes are
  recorded.
- Local Python compilation, shell syntax checks, strictifier transformation,
  and 0117 apply/reverse validation pass. Commit `357a59a` and run
  `40129031828` were canceled before the wrapper/allowlist follow-ups landed;
  that run is not validation. Current follow-up changes are uncommitted. No new
  strict CI has been dispatched, no wrapper manifest exists, and no image has
  been flashed. Next: finish diff review, commit/push, dispatch macOS 13.5 VEUX
  CI, wait for strict checks, assemble/verify the host wrapper with the phone
  DTB, then flash only if both records match. Expected display build ID is the
  new successful workflow run ID.

## >>> UPDATE 2026-10-23 (mount/UFS diagnostics and image geometry) <<<

- User confirms the old userdata contents need not be preserved; the iOS sparse
  root image can be reflashed if a writable-root experiment damages it. The
  pre-flash raw copy is `/Volumes/savedrive/veux_userdata.img`, 109,156,577,280
  bytes. I did not spend time hashing the full old copy.
- Decoded `/Users/vivien/Downloads/ios16-root-20H392.simg`: logical raw image
  17,179,869,184 bytes / 33,554,432 512-byte sectors; HFSX header says
  blockSize 4096, totalBlocks 4,194,304, 16 GiB total. Expanded raw SHA-256 is
  `7ed18fac9b9ecdab38ca3c3adc8a6abac3086e41235ba91d2d82788587bb760d`.
- The pre-flash userdata partition is 213,196,440 512-byte sectors. The tail
  ring is relative to partition end: 4 KiB LBAs `0x1969fd2..0x196a3d2`
  (header then 1024 data blocks), or 512-byte sectors `0xcb4fe90..0xcb51e97`.
  The alternate HFS volume header begins at relative byte `0x3fffffc00`,
  sector `0x1fffffe`. The intended 4 MiB tail ring is in slack after the 16
  GiB HFSX volume and does not overlap its alternate header or allocation file.
- Geometry discrepancy to verify against current GPT when recovery is available:
  Android's saved sysfs start is 23,961,920 512-byte sectors, but an older XNU
  line reports start block `0x2b8c00` and `109643 MiB`. Since the ring writer
  derives its absolute LUN address from its parsed GPT, only partition-relative
  tail placement is certain. No recovery readback of the first 16 GiB is saved;
  `adb devices` and `fastboot devices` currently show no phone.
- Added uncommitted patches 0113/0114: preserve the last 20 console lines in
  the panic region; report rootrw/ufsrw mode and vfs_mountroot errno; add mount
  helper exec/exit status cells; add first UFS write success/error cells.
  Read-only remains the default. A writable-root test requires both
  `rootrw=1 ufsrw=1`; use `veuxlog=0` to disable the separate tail write so the
  first-write cells isolate filesystem writes. CI run `39959731804` passed on
  commit `c3ec01fd9ad06c30d062ffd95e56bfa70c328f7a`; the kernel SHA-256 is
  `e80f43181543ab7ba018b9f147365c55362a402958aef58c35838cbfdddc0f2c`.
  Packaged `shim/out/veux-xnu-39959731804/shim-boot-veux-xnu-39959731804.img`
  (17,121,280 bytes, SHA-256
  `256a97332c5ae7f7235f01f8410572e6aa618aa82042a6a37fc05904924ecc27`). Its
  extracted payload and outer shim kernel/DTB compare byte-for-byte. It boots
  `rd=ufsroot0`, `cpus=1`, `veuxlog=0`, and opt-in `rootrw=1 ufsrw=1`.
  Fastboot verified product `veux`, unlocked, slot B; flashing `boot_b` and
  reboot both returned OKAY. The phone has not enumerated through ADB or
  fastboot 10 seconds after reboot; later photos show the known launchd
  wrong-platform panic (`namespace 9, code 0xe`). The first RW image omitted
  `unentitled_ios_sim_launch=1`, so it did not reach mountroot. Repacked the
  same CI kernel with that argument added:
  `shim/out/veux-xnu-39959731804/shim-boot-veux-xnu-39959731804-rw-platform.img`
  (17,121,280 bytes, SHA-256
  `702225fbe827448ac5d6cae990b4d5037df64902968dc3c5be404c28fae20388`). The
  payload, shim kernel and DTB compare byte-for-byte. The corrected image was
  then flashed to `boot_b` and booted. It used `rootrw=1 ufsrw=1` (RW root).
  Photos show `IOPlatformExpert.cpp:884 Halt/Restart Timed Out` after the
  bsd_autoconf/Skywalk output. The logged timeout caller is the 30-second
  `IOShutdownNotificationsTimedOut` fallback, so its printed frames do not
  identify the original requester. The latest console tail has no mount-helper
  result. Patch 0115 now records the originating `reboot_kernel` howto,
  requestor, and stack, snapshots the actual `haltRestart` entry frames, and
  reads the VEUX `/psci` SMC/HVC method before reset.

- The live VEUX DTB has `/soc/psci { compatible = "arm,psci-1.0"; method =
  "smc"; }` and `/soc/qcom,wdt@f410000` reports `qcom,bark-time = 11000` ms.
  `tools/mkadt.py` now emits normalized `/psci { method = "smc"; }` only for
  VEUX. A standalone RGB/countdown probe was rebuilt against the known VEUX
  template: `shim/out/veux-psci-probe-20261023/shim-boot-veux-rgb-reset.img`,
  446,464 bytes, SHA-256
  `67382ebf4227f82328af1e14ed623eed8a997927fa77389bffe78678ef47189f`. It
  marks five seconds on-screen, then issues PSCI SYSTEM_RESET; a reset near the
  five-second mark (well before the 11-second watchdog bark) is the test
  criterion. This probe has not been flashed: `fastboot devices` currently
  returns no device. Do not flash the kernel reset implementation until the
  standalone timing test confirms PSCI reset on this phone.

## >>> UPDATE 2026-10-23 (VEUX launchd wrong-platform diagnosis and test image) <<<

- The 0112 phone photos show HFS mounted and launchd exec reached. UFS success cell 16 is green; adjacent UFS read-failure cell 17 is dark, with no UFS error line. Far-right red BSD cell 15 means `execve("/sbin/launchd")` returned an error.
- Panic `unexpected SIGKILL of launchd (CS_KILLED)` with namespace 9 / code `0xe`; caller `0xfffffe0007af1af8` symbolizes as `psignal_internal.cold.3` using the CI kernel at `__TEXT=0xfffffe0007004000`. This is `OS_REASON_EXEC / EXEC_EXIT_REASON_WRONG_PLATFORM`.
- `mach_loader.c` reads the iOS device platform from `LC_BUILD_VERSION` (or arm64 `LC_VERSION_MIN_IPHONEOS`) and marks `PLATFORM_IOS` maps alien under `XNU_TARGET_OS_OSX`. The exec rejection is in `kern_exec.c`: for a `PLATFORM_IOS` process with no spawn platform, the no-sandbox entitlement is required; in DEVELOPMENT/DEBUG the `unentitled_ios_sim_launch=1` tunable satisfies that check. With a spawn platform present, the code requires `psa->psa_platform == PLATFORM_IOS`. This check is for device iOS, not `PLATFORM_IOSSIMULATOR`.
- SWEET did not use `XNU_TARGET_OS_IOS`; historical SWEET boot used the macOS target plus the same development boot-arg. SWEET and VEUX differ in machine/board config and platform drivers, while the current build target OS remains macOS. The VEUX test image below applies that boot-arg only; it bypasses this exec gate but does not grant entitlements, disable sandboxing, or remove alien-map VM behavior.
- Test image uses the passing CI kernel from run `39945294859` (SUCCESS, commit `7359133bbf46343c86fb82785155d62368ffd127`) and adds `unentitled_ios_sim_launch=1` to the payload command line. `shim/out/veux-xnu-39945294859/platform-test/shim-boot-veux-xnu-39945294859-platform-test.img`, 17,100,800 bytes, SHA-256 `ac867cc2fbc63d020f448e4514ba28f6a1806856cc7f021cc4c59bf9e8eb5df9`. Unpack/cmp verified the payload, original shim kernel, and selected DTB. Root remains read-only; diagnostics and early alias are retained.
- Expected later differences: OSX alien-map/protected-pager handling, shared-region/cache layout, missing runtime Image4 trust-cache service, remaining MACF/entitlement checks, and OSX memory/task-policy defaults. Patch 0110 enables VEUX `pid_hibernate`; `config/MASTER` enables `CONFIG_FREEZE`, so the actual freeze implementation is compiled, but its device behavior remains untested. The prior SWEET launch reached libignition but failed its separate Preboot-volume lookup; watch dyld cache path/map/slide next.

## >>> UPDATE 2026-10-23 (VEUX portable MD5 fix CI and flash) <<<

- CI run `39945294859` passed on commit `7359133bbf46343c86fb82785155d62368ffd127` (DEVELOPMENT / VEUX); build, workflow source assertions, and synthetic framebuffer/frame diagnostic tests all passed. Run URL: https://github.com/59c84486t9-alt/ios-veux/actions/runs/39945294859
- Kernel SHA-256: `8597f37ba80ad9ae36f59350869960195d045f0adec2e690027178e3ec97602d`. Disassembly at `MD5Init` now calls `_br_md5_init` on a local context and does not load `_g_crypto_funcs`.
- Packaged `shim/out/veux-xnu-39945294859/shim-boot-veux-xnu-39945294859.img` (17,100,800 bytes; SHA-256 `d225d3310f41be987ca508fca5b734b07b5179e6c9b1f7618ba14dc36f42380d`). Android boot-v2 unpack verification matched the kernel payload, verified shim and `vendor_boot_b` `dtb_1.dtb`; command line remains single-core `rd=ufsroot0`, with `veuxlog=1`, and omits both `rootrw=1` and `ufsrw=1`.
- Fastboot confirmed product `veux`, current slot B, and `boot_b` size `0x8000000`. Flash to `boot_b`, set active B, and reboot all returned OKAY. No other partition was written. ADB/fastboot had not re-enumerated 15 seconds after reboot; visual boot result is pending the next phone capture.

## >>> UPDATE 2026-10-23 (0111 CI passed, packaged, flashed to boot_b) <<<

- Earlier run `39940219041` completed SUCCESS on source
  `1a4c49db408763557127ba295a07b0cc87043631` (VEUX DEVELOPMENT). It tested
  patch 0110 plus the 0021/0022 VEUX-only gates. Its kernel artifact is not the
  flash candidate because it lacks the read-only HFS journal guard.
- The 0110 candidate has BSD cells 6-15 for mountroot/vfs/bootstrap/launchd,
  panic text at y1816-2071 with caller/eight bounded frames, and the prior dump
  and alias. Its root defaults MNT_RDONLY, but review found XNU can still open
  and replay a journaled HFS root. I am holding that safety gap for follow-up
  patch 0111 rather than treating read-only mount flags as journal protection.
- Added follow-up 0111: VEUX read-only HFS root
  disables early and legacy late journal initialization/replay; read-write
  requires both rootrw=1 and ufsrw=1. It adds y2208 first-success/read-error
  cells; errors print errno in hex. All changes remain VEUX-gated.
- Updated docs/VEUX-ROOT-BOOT-AUDIT.md with the gate table, UFS flow/error
  semantics, root-image provenance and backup state. Historical phone state
  records the 16 GiB HFSX iOS root image v15 on userdata and prior successful
  HFS mount/launchd; it was flashed from a sparse image. The full pre-flash
  userdata copy is at `/Volumes/savedrive/veux_userdata.img` (109,156,577,280
  bytes, matching 213,196,440 512-byte sectors). User confirms the old contents
  need not be preserved because the iOS image can be reflashed.
- Run `39942134414` completed SUCCESS on source
  `6c8760871b89b9bb64f28d9b987c000cd1af0730` (VEUX DEVELOPMENT), including
  synthetic host diagnostic checks. Run URL:
  https://github.com/59c84486t9-alt/ios-veux/actions/runs/39942134414
- Local 0111 patch application, repository validation, four changed-unit
  xnu-cc syntax checks, and console/frame/recovery/VM host tests pass. These
  host tests use RAM/synthetic data and do not validate actual UFS, HFS journal
  replay behavior, hardware cacheability, or phone scanout.
- The CI kernel checksum is `8a05cf4be250b71915f702d87c9e6f8f933ae91a4dad48b69ef29f1c68d2574f`.
  Post-VM disassembly confirms `vm_fault` returns to the immediate AT/ISB/PAR
  capture without DSB/DMB/TLBI; Step A, B and the conditional cumulative C
  sequence are present. The boot-v2 payload/kernel/selected outer DTB were
  unpacked and byte-compared.
- Image `shim/out/veux-xnu-39942134414/shim-boot-veux-xnu-39942134414.img`,
  17,100,800 bytes, SHA256
  `660d1990a74c559c73de1c1a91a00623079e8cbee1cbb9c0f813c51b3a8e602f`.
  It uses the verified shim and `vendor_boot_b` `dtb_1.dtb`, with
  `rd=ufsroot0`, `cpus=1`, `veuxlog=1`, and no `rootrw`/`ufsrw` options.
- Fastboot identified product `veux`, slot B, and `boot_b` size 0x8000000.
  Flashing `boot_b`, selecting B and rebooting all returned OKAY. Slot A and
  userdata were not flashed. ADB/fastboot had not re-enumerated 60 seconds
  after reboot; awaiting the screen capture to classify boot outcome.

## >>> UPDATE 2026-10-23 (0109 CI passed, flashed to boot_b) <<<

- CI39929665498 SUCCESS for source c2619e4673d87dc483875008673f095b54de5e43.
  Kernel SHA256 efe5512b757bff7a9c6ac2faa009b45c3b8bbe50bf4e9b1d70093d3cd95ab912.
  CI host console/frame bounds checks passed.
- Packaged shim/out/veux-xnu-39929665498/shim-boot-veux-xnu-39929665498.img,
  17,100,800 bytes, SHA256 fc5c9fb1adb7e85b793224a83e8ca3e8e04ea1538bf65ba70a1d1c5f897ba8a4.
  Package unpack compare passed for kernel payload, reused verified shim and
  vendor_boot_b DTB. `rd=ufsroot0`, same cpus=1 arguments. Under128MiB boot_b.
- Fastboot reported product veux, current slot B, boot_b 0x8000000. Flash to
  boot_b, set_active b, and reboot all returned OKAY. Only boot_b was written;
  boot_a and userdata untouched.
- At 37 seconds after reboot, neither fastboot nor ADB enumerated; this alone is
  not boot-screen evidence. Await photo/video of frozen rotating wait snapshot.
  Use exact kernel above with symbolize-veux-waits.py; pages rotate every2 sec.

## >>> UPDATE 2026-10-23 (0109 CI dispatched) <<<

- Source commit c2619e4673d87dc483875008673f095b54de5e43 pushed.
  Manual VEUX DEVELOPMENT CI39929665498 queued/running:
  https://github.com/59c84486t9-alt/ios-veux/actions/runs/39929665498
- All local object/host/source/patch checks pass. Symbolizer reproduces known
  skmem_sysctl_init+18hex and machine_idle+100hex from exact0108 CI kernel.
- No0109 image or flash yet. Device remains0108. CI must pass first. After
  success download exactkernel, verify source and artifacts, package sameargs,
  then collect video covering all frozen wait pages; symbolize against0109.

## >>> UPDATE 2026-10-23 (0109 idle wait candidate prepared) <<<

- User requests wait-state diagnosis after handled first fault and idle samples.
  Added 0109: console y64..799 clears on init/advance/wrap and opaque glyphs;
  handled faults get two compact status rows, full panel only unresolved/panic.
- Bootstrap identity + 100ms timer, five seconds consecutive single-core idle
  samples -> one immutable validated global-thread snapshot capped128. Captures
  state/options, wait_event/result, block hints, continuation, bounded saved FP
  trace up to8 RAs; flags unavailable traces. Six threads/page frozen rotating
  every2sec for filming. Pset runqueue/realtime counts, sched_tick start/end and
  native timer count. No IRQ sleeping locks; cpus=1 only. Adds periodic wakeups.
- BSD strip y2080 cells0..5: postnet, IOKit entry/exit, rootlookup entry/exit,
  bsd_utaskbootstrap. Existing first-fault bit rows/alias/stage strips unchanged.
- Local all4 object compiles pass, actual console and frame core host tests pass,
  VM walk/recovery tests pass, workflow source checks and109-patch checks pass.
  Synthetic tests do NOT prove cache/barrier/live stack behavior. Pmap unchanged.
- Added exact CI-kernel nm helper and docs/VEUX-IDLE-WAITS.md with screen legend,
  capture limitations and root analysis. Bootargs rd=ufsroot0, not ramdisk; outer
  INITRD is XNU payload. Root bypasses generic Stillwaiting loop, initial IOBSD
  resource wait up to30sec; UFS commands5sec each. Need0109 photos to classify waits.
- Not yet dispatched/booted at this milestone. Preserve0108 phone observation
  state. CI success required before new image/flash. Next: finalpatchreview,
  commit/push, dispatch and await exact success.

## >>> UPDATE 2026-10-22 (0108 photos: resolved first fault, idle sample) <<<

- Photo 1 is early: abort/VM counters zero, first PAR/result all-ones means
  uncaptured, timer count1. Photo 2 shows abortcount1, repeatcount1, VM1/1,
  normal sleh return1, first-pair count1. No experiment ran (step/mask0).
- ESR96000047 (L3 write translation), ELRfffffe000764e18c = exact CI
  skmem_sysctl_init+24, FARfffffe53b176c000. First/latest PARff00000104300b00
  has F=0, PA104300000; vm_fault result0. L3 descriptor0 ->0060000104300603,
  flags207->7, change mask4. Descriptor entry PA103bf2ed8 matches FAR index1499
  in L3 table103bf0000. FARclass50 = kernel_map/general kernel VA.
- TCR226511a511 = WB/WB, outer-shareable, T1SZ17/TG1=16K. Descriptor-page
  attrs103ff0200 = AttrIndx0, SH2, MAIRff, valid L3; mismatch0. Table consistency
  masks307. No cache/barrier recovery needed for this measured first fault.
- Timer count2, sampled PCfffffe00074932e0 = machine_idle+256, exact instruction
  is epilogue load after DAIFClr. Previous sample was ml_set_interrupts_enabled
  with debug. CPU has reached idle; this snapshot is not an abort retry loop.
  It does not identify a blocked thread/root-device wait. Inspect later boot
  progress/wait states next if stationary. No pmap barrier fix justified here.
- Found row07 publisher omission. Completion/result are proven via 0A/21/24
  and green cell; repair row07 during the next instrumentation change, not
  another image solely for display. Full results appended to audit doc.
- Raw crop/decoded.json/idle disassembly in ignored 0108-photo-analysis.
  No source patch/build/flash or device-state change for this analysis.

## >>> UPDATE 2026-10-22 (0108 CI passed, one image flashed) <<<

- CI 39896881721 SUCCESS for 2c3f478de5b4f1f3f61e3c1af741a3436e65106e.
  Downloaded xnu-kernel to xnu/out-39896881721; SHA256SUMS passed.
  Kernel SHA256 6c7af2598b4b850d65c29929de5d700b6664dae0a8ca798c762029f77427a8ae.
- Packaged one image: shim/out/veux-xnu-39896881721/shim-boot-veux-xnu-39896881721.img
  size 17100800, SHA256 e3c25c54967a5fe1a96b61bec6f991ff08c3cea6b763a75efd60eb27cd8343c5.
  Fresh highmem VEUX ADT/cpus=1 payload, unchanged tested shim and selected DTB.
  Unpacked shim/payload/DTB byte-compare passes. Manifest/package.py beside image.
- Verified exact CI binary diagnostic symbols. Disassembly confirms immediate
  post-VM AT/ISB/PAR has no preceding full barrier, and real DC/DSB plus
  TLBI/DSB/ISB instructions are present. instruction-check.txt/disassembly and
  symbol map are saved beside ignored image. No pmap changes in this build.
- User confirmed built, fastboot, ready to flash. Product veux, B and boot_b
  0x8000000 verified. Flash boot_b, select/verify B, reboot all OKAY. Recording
  cue followed by 20-second delay before reboot. Slot A/userdata image untouched.
- CURRENT: 0108 on boot_b, B active. Await panel/recording result. Priority rows:
  0A first PAR/result, 22 fix step/occurrence, 2B first-pair count/call; also
  latest 21, walks 0E-14, experiment 25-2F and timer 20/23. Full legend is
  docs/VEUX-VM-FAULT-AUDIT.md. Do not reboot before observation. Hardware
  cache/barrier behavior remains unproven until these results are read.

## >>> UPDATE 2026-10-22 (0108 phase-safe VM diagnostics prepared) <<<

- User requested counters/latest hex, fixed status cells, pre/post TTBR1 walks,
  hardware PAR, pmap audit and interrupted-PC samples in one measurement build.
  Subsequent steering: no new diagnostic full barrier between VM return and
  experiment end; sticky first dump before VM may flush. One A/B/C experiment
  only on occurrence two with successful VM + immediate PAR F=1; N=8 is only
  repeat warning. First post-VM PAR/result/pair saved and published without
  requiring a repeat. Pmap source unchanged.
- Added 0108, test-veux-vm-diag.py and test-veux-recovery.py. Host tests pass
  using synthetic tables/mocked architectural effects: not hardware/cache/
  barrier validation. Exact limitations and row legend in VEUX-VM-FAULT-AUDIT.
- New stage_mark_nb is stores only, flush is one dsb sy. New panel publishes
  at normal sleh return or a safe timer tick after recovery, NB draws+one flush.
  Normal sampler writes NB without flushing while VM is pending. Original
  first-fault dump, early alias and slot-A recovery preserved.
- Local object compiles passed. Disassembly caught semicolons treating trailing
  inline-asm instructions as comments; changed new asm to explicit newlines.
  Verified emitted AT/ISB/MRS, DSB/ISB, DC/DSB and TLBI/DSB/ISB sequences.
- No 0108 build dispatched or device change yet. Final validation and CI next;
  current device image remains 0107. Require CI success before one image/flash.

## >>> UPDATE 2026-10-22 (0107 console proven; data-abort return audit) <<<

- Latest user photo proves XNU text now displays, with Skywalk self-tests
  through "memcmp mask ... PASSED". Original/second strips and first-fault
  rows remain visible. No panic text observed. Device unchanged in this audit.
- Inspected exact sleh path shared by 0106/0107: exception paint/dump does
  not return out of handling. DABORT_EL1 calls handle_abort ->
  handle_kernel_abort. Translation faults skip arm_fast_fault, call vm_fault;
  KERN_SUCCESS returns with saved PC unchanged, retrying the instruction.
  Failed resolution without copyio recovery reaches panic_with_thread_kernel_state.
- Thus repeated successful vm_fault returns with an ineffective mapping could
  retrap forever, but absence of panic does not establish that. Could also be
  blocked inside vm_fault or have moved beyond the retained first exception.
  The first-fault dump is sticky and is not necessarily the current PC.
- Next discriminating instrumentation: count repeated PC/FAR entries and mark
  before/after vm_fault plus its return code, and the normal sleh-return point.
  No source patch/build/flash performed for this question.

## >>> UPDATE 2026-10-22 (0107 console route fix flashed) <<<

- CI 39891452278 SUCCESS at 729dc6f16b07605707a7856bdb8ce684ebaee1b4.
  Downloaded kernel checksum passed. Exact binary contains the direct VEUX
  kprintf route banner plus fault-dump/timer-probe/alias symbols.
- Image shim/out/veux-xnu-39891452278/shim-boot-veux-xnu-39891452278.img,
  17084416 bytes, SHA256 4e6f336997425b185e0a840a7b39ea74abf68ff2674c06bd1b48ff0dcfc4c26c.
  Kernel SHA256 7f65074b61801c13d4eaf7953cf574949bfe79a2b1938539df8605461523549a.
  Fresh --veux --highmem ADT and cpus=1 payload; preserved tested unchanged
  shim (entry marker before clear) and selected DTB. Unpacked components match.
  Manifest, package.py, reboot timestamp and flash log beside ignored image.
- User explicitly reported built/fastboot/ready to flash. Verified product
  veux, slot B, boot_b size 0x8000000. Flash boot_b, select B, verify slot,
  reboot all returned OKAY. Recording cue and 20-second delay before reboot.
  Slot A and userdata image not flashed.
- CURRENT: 0107 console-fix candidate on boot_b, B active. Await observation
  of direct banner, later XNU text, markers and any reset. Do not reboot before
  observation. Device output success remains unconfirmed.

## >>> UPDATE 2026-10-22 (0106 video/photo decoded; console fix prepared) <<<

- Photo confirms original six cells and second-strip 7/8/9/10/11/12/14;
  13 panic and 15 timeout unlit. Virtual-timer test interrupt delivered;
  allocator and clock returned. A first synchronous fault occurred later.
- MOV duration 3.418s: initial logo, strips at 2.002s, same stage screen at
  3.378s, no reset. Cannot give a reset interval. Photo shows dump rows absent
  from this short video. No device-state changes performed during analysis.
- Perspective grid fit best ESR96000046, ELRfffffe000764b18c,
  FARfffffe1000b78000; SP ambiguous 0xfffffe301f7277e0/0xfffffe301f727fe0.
  Raw data/scripts/annotated crops ignored under 0106-video-analysis.
  Threshold sensitivity is documented in the diagnostics doc; exact-kernel
  disassembly supports ELR: skmem_sysctl_init+24, str w8,[x0], w8=3, after
  skmem_get_sysctls_obj. Alternative ELR bit14 is BL, inconsistent with ESR.
- ESR says same-EL write L2 translation fault. This may be first-touch demand
  paging of the new 16KiB Skywalk sysctl object. First-fault capture includes
  handled exceptions; do not present it as a proven fatal stop or last PC.
- Found later PE_init_kprintf overwrites the VEUX sink with UART/discard.
  Added 0107 preserving VEUX sink plus direct routing banner; local arm64
  object and 107-patch validation pass. Early alias and diagnostics retained.
  CI 39891452278 started for 729dc6f:
  https://github.com/59c84486t9-alt/ios-veux/actions/runs/39891452278
  No 0107 image flashed yet. Current B still 0106.

## >>> UPDATE 2026-10-22 (0106 CI passed, packaged and booted) <<<

- CI 39887758455 SUCCESS for 9d73fc612d8345c1c4a11dae8b4b25b370cd0972.
  Downloaded xnu-kernel to xnu/out-39887758455; SHA256SUMS passed.
  nm confirms veux_bit_row/fault_dump/irq_probe/probe_interrupt and alias state.
- Packaged shim/out/veux-xnu-39887758455/shim-boot-veux-xnu-39887758455.img,
  17084416 bytes, SHA256 8614d39f2058bd76e99cfdc8b3080801b39f6e4d7418ac1089fd2096aa0b3873.
  XNU SHA256 29cb187ad02a5cd542ea01dedd68655e1099a94dd8e94c73939e505357e70ef0.
  manifest.json and reproducible package.py beside image, ignored as artifacts.
- Reused exactly the previously tested 0105 shim: git diff confirms shim and
  ADT generator unchanged since 541cad4. Entry marker before con_clear remains.
  Fresh --veux --highmem ADT and cpus=1 payload, same opted-in log/FB args.
  Boot-v2 unpack confirms shim, payload and selected dtb_1 byte-for-byte.
- User confirmed fastboot and recording readiness. Product veux, B active,
  boot_b 0x8000000 verified. Flashed boot_b, selected/verified B: all OKAY.
  Gave recording cue, waited 20 seconds, then fastboot reboot returned OKAY.
  Exact host UTC reboot timestamp is in ignored reboot-time.txt/flash-log.txt.
  Slot A and userdata image not flashed.
- CURRENT: 0106 diagnostics on boot_b and B active. Await recording/screen
  result: second strip, fault/timeout bit rows, reset interval. Do not reboot
  before observation. No inference yet about where this candidate stops.

## >>> UPDATE 2026-10-22 (0106 diagnostic candidate) <<<

- User requested second strip, stackless fault bits, bounded IRQ probe and
  retained alias. Added 0106; no device write yet. See diagnostics doc for
  exact rows/colors and interpretation, including FLEH-after-context-save limit.
- All eight changed translation units compiled as arm64 objects. Fixed local
  macro syntax and used GICR SGI-frame ISPENDR0 offset 0x10200 (not in header).
- Actual assembly renderer executed in Unicorn with SP=0/unmapped stack:
  all four rows, MSB order, exact buffer bounds and first-fault retention pass.
  Reusable test: tools/test-veux-bitdump.py; deps in ignored diag-test-venv.
- Probe intercepts before normal timer/scheduler C handler, restores original
  timer and DAIF state, uses mapped selected GICR. No forced reset introduced.
- CI 39887758455 started for 9d73fc612d8345c1c4a11dae8b4b25b370cd0972:
  https://github.com/59c84486t9-alt/ios-veux/actions/runs/39887758455
- Next: full CI success, package/verify image, user starts filming in fastboot,
  then authorized boot_b flash/reboot. Current device still previous XNU on B.

## >>> UPDATE 2026-10-22 (photo confirms all six XNU cells) <<<

- User photo after run-39884652829 boot shows red, orange, yellow, green,
  cyan and magenta footer cells. This confirms execution of all six 0105
  paint sites: _start, MMU-on, arm_init, PE_init_platform(FALSE) return,
  GIC/timer-PPI configuration, and PE_init_veux_pmsg console-route setup.
- Top text is still shim loader/handoff text; no readable XNU panic or
  later XNU progress line is established by this photo. Magenta means the
  routing function returned from veux_fb_init, not proof text rendering
  succeeded (that routine can return early). Cyan does not prove IRQ delivery.
- No reboot, flash or device-state change performed for this observation.
  B remains the diagnostic XNU candidate. Next diagnostic boundaries are
  VM/bootstrap return, serial/kprintf readiness, machine_startup and actual
  timer/SGI delivery; use the proven footer mapping to expose progress.
  Review why text output is absent as a separate observability issue.

## >>> UPDATE 2026-10-22 (stage-marker XNU built and flashed) <<<

- CI 39884652829 SUCCESS for 541cad4a058b56d91259827875f83d9e0e8464d1.
  Downloaded xnu-kernel to xnu/out-39884652829; SHA256SUMS passed.
- Built fresh VEUX shim using local clang --target=aarch64-none-elf and
  aarch64-elf binutils. Clang O2 produced absolute string-table pointers for
  shim.c exception switch; -fno-jump-tables removed them. Verified zero
  ABS64 relocations in all C objects; start.S image-size relocation is expected.
- Generated fresh --veux --highmem ADT (2400 height), payload with cpus=1,
  debug=0xc serial=3 keepsyms=1 -enable_kprintf_spam -noprogress rd=ufsroot0
  veuxlog=1 veuxfb=1 veuxfbconsole=1. No general writable-root options.
- Image: shim/out/veux-xnu-39884652829/shim-boot-veux-xnu-39884652829.img
  size 17084416, SHA256 5847c89c99882d6df22f0ba185760f19c7e25eb7a7fcfd9fdd550282782d5fb1.
  Preserved verified boot-v2 header and dtb_1.dtb. Unpacked shim, payload,
  and DTB all match byte-for-byte. Local flash-log.txt is beside the image.
- Recovery reported slot A. Rebooted bootloader; product veux and boot_b
  capacity 0x8000000 verified. Flashed boot_b, selected/verified B, rebooted:
  every operation OKAY. Slot A and userdata image untouched.
- CURRENT: stage-marker XNU on boot_b and B active. Await user observation
  of bottom red/orange/yellow/green/cyan/magenta cells and any text/restart.
  Do not reboot before observation. Bootloader acceptance is not XNU success.

## >>> UPDATE 2026-10-22 (probe tests, fastboot log loss, XNU stage patch) <<<

- Executed requested marker-only control: flashed only boot_b with the verified
  edd94c... v3 marker image, selected B, rebooted; all fastboot operations OKAY.
  User observed repeating Xiaomi logo / black / restart cycles, interval not
  measured. Returned through physical fastboot to slot A recovery: pstore empty.
- Linux /dev/pmsg0 direct-recovery control PASSED: exact marker
  VEUX_LINUX_PMSG_CONTROL_20261022_V3 recovered in pmsg-ramoops-0 (1206 bytes,
  SHA256 a0894894df57d7d4defe06349cdfc132bb86455a76a9df707d5b1bfe9d012d77).
  Repeated with marker VEUX_LINUX_FASTBOOT_CONTROL_20261022_V3 and a warm
  recovery -> fastboot -> recovery transition on A: pstore EMPTY. Thus that
  recovery route loses even a Linux-written marker; empty XNU logs through
  it cannot localize failure. Bare-metal pmsg execution remains unproven.
- Actual recovery device-node properties agree with the 1 MiB record/pmsg
  split at d0000000/d0100000. A console-ramoops filename is not evidence of
  a different split: inspected Qualcomm source calls its record zone console.
- Flashed the verified be0134... RGB-reset image to boot_b next. User reports
  "RGB pattern visible, then restart". This validates visible output from the
  fallback using live splash reservation / assumed 1080x2400 stride4320.
  Returned via fastboot to slot-A recovery; RGB probe remains on boot_b.
  No userdata image or slot-A partition was flashed during either test.
- Raw control captures and flash logs are in ignored research/veux-logs/
  marker-reset-v3-test/ and rgb-reset-v3-test/. Preserve Linux successful pmsg
  dump as the comparison; no fabricated last XNU line is available.
- Added 0105-veux-early-stage-cells.patch after the successful pattern test:
  six cells for _start, MMU on, arm_init, platform/DT, GIC/timer config and
  console. Exact 12 MiB L3 mapping (16K pages) has a persistent kernel alias
  across TTBR0 teardown. The ordinary high-bank physmap excludes splash RAM.
  Text console leaves the footer untouched; GIC color is not proof of IRQ
  delivery. Use cpus=1 for the candidate.
- Corrected shim/ADT/late-console height to the tested 2400; shim now emits
  an entry pmsg marker before clearing the screen black. Earlier c27fda0
  enabled clearing before the handoff marker: plausible regression candidate,
  not established cause. No new XNU image has been flashed in this update.
- Six changed XNU files emitted local arm64 objects, including assembly;
  three changed shim files cross-compiled. Refreshed downloaded exported
  sweet_early.h before pexpert checks. Standard git apply and all CI source
  assertions pass; 105-patch validation and seven probe tests pass. Updated
  xnu-cc.py to detect fork CI paths/use installed clang/create object dir.
  Full CI run 39884652829 is in progress for commit 541cad4a058b56d91259827875f83d9e0e8464d1:
  https://github.com/59c84486t9-alt/ios-veux/actions/runs/39884652829
  Next: inspect the first error if it fails; on success package the XNU
  candidate with cpus=1 and test stage cells. Full link and device stage
  results are pending; current boot_b is still the RGB probe.
- Flash sequence and outcome matrix: docs/VEUX-BOOT-DIAGNOSTICS.md.

## >>> UPDATE 2026-10-22 (positive-control marker/reset probes prepared) <<<

- Current root slot-A recovery live tree contains splash_region@0x85200000,
  reg `<0 0x85200000 0 0xc00000>`, but no simple-framebuffer. `find -L` is
  needed for /proc/device-tree's symlink. `/proc/iomem` has no splash-named
  line; it reports `85200000-85efffff : reserved` (includes adjacent DFPS).
  Fresh live FDT and iomem saved under ignored recovery-after-39805058203.
  This is recovery evidence, not a new stock-Android observation.
- Regression hypothesis: c27fda0 enabled shim con_clear before loader_boot's
  handoff marker, whereas earlier recovered handoff logs used display-disabled
  shim builds. A screen-clear fault could explain missing later markers; not
  established. XNU 0103 and the Xcode16/0104 change are additional differences.
- Added default marker-only positive control before any FDT dereference or
  framebuffer access. It uses the confirmed pmsg layout, logs frequency,
  waits ten seconds on CNTVCT_EL0/CNTFRQ_EL0 without IRQs, then requests
  standard PSCI SYSTEM_RESET via SMC. No invented recovery/reset2 reason.
  The marker-only linked image excludes parser and pattern code. Counter or
  pmsg faults remain possible; a reset timing observation is not itself proof
  of marker retention. This does not test the separate UFS log writer.
- Optional --screen logs source priority: valid live simplefb, otherwise live
  named splash reservation with explicit assumed 1080x2400/4320/a8r8g8b8.
  Invalid/ambiguous explicit descriptors do not trigger a fallback. Both
  address paths are bounded to VEUX splash RAM and reject 0x9c000000. Current
  recovery FDT passes host selection as source 2 at 0x85200000 size 0xc00000.
- Seven host tests pass. Initial screen build exposed compiler-generated
  memset for larger zero-initialized state; replaced it with a freestanding
  volatile byte-clear. Both final AArch64 builds pass, as do relocation,
  symbol/disassembly and boot-v2 checksum/segment comparisons.
- Marker candidate: shim/out/veux-marker-reset-v3/shim-boot-veux-marker-reset.img,
  438272 bytes, SHA-256
  edd94c34522aef58c6747e31d22a91fefd437dbd3f55fcd4422f4446def80a97.
- Screen candidate: shim/out/veux-rgb-reset-v3/shim-boot-veux-rgb-reset.img,
  446464 bytes, SHA-256
  be013405f3e86d6ade48c8f6f072548a4a8980d2a2b134e5829b95c9b2b48cc9.
- No v3 image flashed; phone remains slot-A recovery, fresh XNU on boot_b.
  Standard reset keeps B active and may repeat the probe. First hardware test
  should use marker-only and then return via fastboot to A recovery for pstore.
  Exact procedure and limitations: docs/VEUX-BOOT-DIAGNOSTICS.md.

## >>> UPDATE 2026-10-22 (fresh-kernel recovery log result) <<<

- User returned the phone to fastboot and enabled ADB for recovery log
  collection. Verified product veux and slot B, selected slot A and issued
  `fastboot reboot recovery`; both succeeded. ADB is authorized and root;
  recovery reports `_a`. No partition was flashed during this collection.
- `/sys/fs/pstore` is empty. Recovery dmesg registers ramoops at
  `0xd0000000`, size `0x200000`, ECC 0, without an invalid-buffer warning.
  Runtime parameters confirm 1 MiB record + 1 MiB pmsg, zero console/ftrace,
  mem_type 0. No last XNU line can be recovered from this attempt.
- Read the final 1025 4096-byte blocks of userdata (`sda22`, 213196440
  512-byte sectors). No VEUXLOG1 header. Tail SHA-256:
  `06955cde7f98b9503653b906e9634732d59a17a6dc2cb1a0e453fbdd4adaab86`;
  byte-for-byte identical to the pre-logger tail backup. Thus no successful
  diagnostic tail flush is evident; the failure point remains unknown.
- Independently read back the first 4162 blocks of boot_b. SHA-256 matches
  the exact fresh image `279e7808f7d65a8d50004818325e8e76ad61e21d2bb4ad2c77eb1303f9095f95`.
  This rules out accidentally testing a stale boot_b package in this attempt.
- Raw tail, recovery dmesg, pstore listing and runtime parameters saved under
  ignored `research/veux-logs/recovery-after-39805058203/`. The dmesg belongs
  to Linux recovery, not XNU. Missing pstore does not distinguish early failure
  from loss of retained RAM during the forced reset/boot transition.
- Current state: slot-A root recovery, fresh XNU image still on boot_b. The
  live-FDT RGB/pmsg v2 probe remains unflashed. No new flashing authorization
  requested or inferred from this read-only log-collection step.

## >>> UPDATE 2026-10-22 (logo persists; live-FDT standalone probe v2) <<<

- User reports the fresh run-39805058203 image still shows the Xiaomi logo.
  That CI run passed; there is no failed compile to repair for this candidate.
  Neither fastboot nor ADB enumerates after the report. No log from this exact
  boot can yet be read; older corrupted pmsg is not a reliable current last line.
- Replaced the standalone fixed-address white fill with a live-FDT parser,
  RGB bars, white corner marker and black border, plus staged pmsg records.
  Framebuffer address/allocation/geometry/format must come from one complete,
  enabled simple-framebuffer node supplied by ABL. No guessed fallback mode.
  The probe holds indefinitely and does not start XNU or access storage/MMIO.
- Pmsg is enabled only after confirming the known ramoops reservation; its
  1 MiB runtime split at 0xd0100000 remains based on prior recovery evidence,
  since the DT pmsg-size differs. Stages and decoded parameters are appended
  with ordered stores. Log retention/corruption is still a runtime uncertainty.
- Host tests cover truncation, malformed offsets, absent/disabled/incomplete/
  ambiguous/unsupported framebuffer nodes, address/size bounds, translated
  buses, RGB/BGR rendering, corner/border and untouched stride padding.
  Six tests passed; strict freestanding AArch64 compile/link passed with no
  absolute pointers in the C object. Both saved stock dtb_1.dtb and recovery
  FDT parse with ramoops present but zero simple-framebuffer nodes: ABL must
  supply one at handoff or the new probe will log SKIP and avoid drawing.
- Board-matched `dsi-panel-k6s-38-0c-0a-fhdp-dsc-video.dtsi` specifies
  `dsi_video_mode`. This makes command-mode refresh a weaker hypothesis;
  it does not establish current controller state or active scanout.
- Prepared `shim/out/veux-fdt-probe-v2/shim-boot-veux-fb-only.img`, 442,368
  bytes; SHA-256 `3c9945ef6a9c2868b3e6eaf947ebe625def3ea5aad59f9d1bb1e6dcd9a3252a9`.
  No new image flashed and no slot change in this update. First collect the
  current boot's pstore/userdata-tail log through recovery when fastboot is
  available, then decide whether to run this probe. See updated diagnostics doc.

## >>> UPDATE 2026-10-22 (corrected CI kernel packaged and flashed) <<<

- User explicitly requested packaging the successful GitHub build, flashing
  via fastboot and rebooting into it. Run `39805058203` succeeded at head
  `818ea2b813990805260495d28d3056539772c011`. Downloaded kernel SHA-256:
  `8daeea32d216658245365d7dc1f4ec3affa0e9033c36556ef793cd6ea1ab5861`.
  Artifact checksum and direct-simplefb implementation strings verified.
- Generated fresh `mkadt.py --veux --highmem` ADT and XNU payload, retaining
  RAM base `0x100000000`, size `0xf8600000`, single-core boot, `rd=ufsroot0`,
  `veuxlog=1`, `veuxfb=1`, `veuxfbconsole=1`, and verbose output. No general
  UFS/root write options enabled. The existing opted-in logger can write its
  bounded userdata-tail diagnostic area if XNU reaches UFS initialization.
- Packaged with the verified existing direct-framebuffer VEUX shim and exact
  selected vendor_boot_b `dtb_1.dtb`, preserving known boot-v2 header values.
  Every embedded XNU segment matches the fresh kernel; embedded ADT matches
  the generated tree. Unpacked shim, payload and DTB match inputs byte-for-byte.
- Image: `shim/out/veux-xnu-39805058203/shim-boot-veux-xnu-39805058203.img`,
  17,047,552 bytes; SHA-256:
  `279e7808f7d65a8d50004818325e8e76ad61e21d2bb4ad2c77eb1303f9095f95`.
- Fastboot identified product `veux`, slot B, and 128 MiB `boot_b`. Sending
  16,648 KiB and writing `boot_b` both returned OKAY. `set_active b`, verified
  `current-slot: b`, and `reboot` all succeeded. Only boot_b was flashed;
  no userdata image or slot-A partition was written.
- Screen result and XNU startup remain unobserved. Leave slot B selected for
  this test; obtain the user's screen observation before interpreting success.
  This is the fresh XNU image, not the standalone white-screen-only probe.

## >>> UPDATE 2026-10-22 (fresh-chat audit, CI repair and standalone probe) <<<

- Checked run `39796431519`: it acquired the Intel runner and compiled XNU,
  but patch 0103 was skipped by `git apply` because its hunks had no context.
  The post-build source checks rejected the resulting stale framebuffer code.
  Patch 0104 applied successfully; this was not another runner queue failure.
- Regenerated patch 0103 with three context lines against that run's actual
  saved source. Standard `git apply --check` and application pass. Fixed the
  workflow's IORPC checks to accept the field's actual whitespace. Executed
  the complete workflow post-build check block against the repaired CI source:
  all checks pass. Full recompilation is still pending.
- Added `shim/veux-fb-probe.S` and `tools/build-veux-fb-probe.py`: a standalone
  4 KiB Linux Image-header probe that checks EL1/MMU-off/cache-off, fills the
  configured linear framebuffer white, executes DSB, and waits indefinitely.
  It has no XNU, loader, stack, FDT parser, UFS, timer, GIC or pmsg dependency.
  Geometry comes from the existing VEUX console profile: 0x85200000,
  1080x2520, stride 4320, within the 12 MiB reservation. This profile is still
  an unconfirmed scanout assumption; a blank result cannot alone prove that
  the bootloader failed to enter the probe.
- Built `shim/out/veux-fb-only-20261022/shim-boot-veux-fb-only.img`, 405,504
  bytes; SHA-256 `e062a30f9d75a37d1335844a253d720385d37f34845b1575f0e22b409acc038b`.
  Preserves the known shim boot-v2 metadata and exact selected vendor_boot_b
  DTB. Unpack comparisons of kernel/ramdisk/DTB, independent Android image-ID
  calculation, compressed cpio check, and assembly disassembly all pass.
  Repository validation passes (104 patches). Diff whitespace warnings in
  0103 are unified-diff context prefixes, not added source whitespace.
- No phone access, slot change or flash in this session. The known earlier
  shim/XNU pmsg handoff already proves some prior XNU entry; the standalone
  probe isolates visibility from XNU startup. Next device action requires the
  user's approval of this exact boot_b candidate, per AGENTS.md. Temporary
  `fastboot boot` was previously rejected as unsupported on this phone.
- Concise procedure/evidence: `docs/VEUX-BOOT-DIAGNOSTICS.md`.
- Committed and pushed as `818ea2b`. Dispatched fresh XNU CI run
  `39805058203` on that exact commit (macOS 13.5 / DEVELOPMENT / VEUX,
  Intel macOS 15 runner). Build result is pending; no fresh kernel is yet
  validated or packaged.

## >>> UPDATE 2026-10-22 (direct-framebuffer shim boot probe) <<<

- Built `shim/out/shim-boot-veux-directfb-probe-oldxnu-20261022.img` with the
  new VEUX direct-framebuffer shim, the selected `vendor_boot_b` `dtb_1.dtb`,
  and the previously built XNU payload from CI run 39706120497. The payload
  still contains the earlier XNU framebuffer guards; this image tests the
  shim's pre-XNU screen writes and is not the patch-0103 kernel build. Image
  size: 17,068,032 bytes; SHA-256:
  `004c022496598c991fe82c9660b06d8f5feb39e732fa118a357d78f5829b54f6`.
  Header-v2 unpacking matched the shim kernel, payload, and outer DTB exactly.
- Verified fastboot product `veux`, active slot A before the write, and
  `boot_b` size `0x8000000`. Flashed only `boot_b`, selected B, and rebooted.
  Slot A was not written. The payload includes the previously authorized
  `veuxlog=1` option, which can write only the bounded diagnostic log tail if
  XNU UFS logging starts; no userdata image was flashed.
- After about three minutes, neither ADB nor fastboot enumerated. Host-side
  tools cannot observe the physical panel, so whether the new shim screen was
  visible is unknown. The fresh patch-0103 XNU CI run 39786091688 remains
  queued. Keep B active until the user directs otherwise.

## >>> UPDATE 2026-10-22 (local VEUX shim packaging check) <<<

- Replaced the shim's `__builtin_strcmp` uses with a freestanding `name_equal`
  helper. A local Clang/AArch64 compile exposed an unresolved libc `strcmp`
  reference at link time; the shim has no libc. The source now stays self-
  contained for freestanding toolchains.
- Local shim build check passed with the VEUX target, zero `ABS64` relocations,
  the host console renderer, and AArch64 ELF output (184,320-byte image).
  Packaged a smoke image with AOSP's `mkbootimg.py` and the selected VEUX DTB;
  unpacking verified the kernel and DTB byte-for-byte. That smoke image used
  the previously built kernel only to verify packaging and is not a new boot
  candidate.
- GitHub XNU run `39781378209` was cancelled before any steps ran; a rerun of
  the same dispatch is queued. The phone remains in slot-A recovery. No image
  has been flashed during this check.

## >>> UPDATE 2026-10-22 (CoreAnimation surface pitch audit) <<<

- SWEET's IOSurface provider advertises 64-byte row alignment. When
  `IOSurfaceBytesPerRow` is omitted, it rounds `width * bytesPerElement` up to
  that alignment; width 1125 with four-byte pixels therefore defaults to 4544
  bytes. An explicit row-byte value is retained if it is at least the packed
  row size. Its IOMobileFramebuffer blitter copies `width * 4` bytes per row,
  using the surface's recorded source pitch and the framebuffer's destination
  pitch, so either 4500-byte or 4544-byte source rows are supported.
- A SWEET boot log recorded 1080x2400 IOSurfaces with 4352-byte pitch, matching
  64-byte alignment. This is evidence for the SWEET implementation. VEUX has
  not reached CoreAnimation/backboardd, so its runtime surface pitch is still
  unknown; inspect the actual `IOSurfaceBytesPerRow`/bytes-per-row logs when it
  does.
- Keep the iPhone X 1125x2436 canvas separate from the VEUX physical scanout.
  Existing Android evidence reports a 1080x2400 panel and 4352-byte DRM pitch;
  that does not establish the bootloader scanout buffer's layout. Do not change
  the `simple-framebuffer` scanout node to 1125x2436/4544 solely from the
  CoreAnimation alignment calculation.

## >>> UPDATE 2026-10-22 (direct VEUX simple-framebuffer path) <<<

- Used the framebuffer description supplied by the user: physical base
  `0x85200000`, allocation `0x00c00000` (12 MiB), 1080x2520, 4320-byte
  stride, `a8r8g8b8`. The visible image needs 10,886,400 bytes (about 10.38
  MiB), within the declared allocation. A 12 MiB allocation also fits
  1200x2520 at 4800-byte stride (12,096,000 bytes); the table's 13 MiB value
  leaves extra headroom. Kept the explicit node's 1080x2520 mode.
- Replaced the live SDE register/geometry checks in patch 0103 with a direct
  mapping of the declared simple framebuffer. The white marker and transparent
  text console are still requested by `veuxfb=1` and `veuxfbconsole=1`; the
  active XNU diagnostic cmdline must include those options. There are no SDE
  register gates. A mapping failure still returns without a write.
- The VEUX shim now uses the same framebuffer base, geometry and stride,
  supplies those values in `Boot_Video`, and maps the containing physical block
  as non-cacheable write-combining memory. Added the matching
  `simple-framebuffer` node to the VEUX ADT. The separate logical canvas stays
  at the iPhone X size, 1125x2436 at 3x (375x812 points).
- Updated the XNU workflow's post-patch checks for the direct framebuffer and
  repaired the inline Python check indentation. Validation: 103-patch repository
  check passed; generated ADT decoded to base `0x85200000`, size `0xc00000`,
  width 1080, height 2520, stride 4320, format `a8r8g8b8`; patch 0103 applies to
  a clean run-397061 build tree. No phone boot or flash was performed. XNU CI
  run `39781378209` was dispatched for commit `c27fda0` (macOS 13.5,
  DEVELOPMENT/VEUX) and remains queued with no runner assigned. A boot-image
  rebuild remains pending.

## >>> UPDATE 2026-10-22 (slot-A recovery log inspection) <<<

- After the user's instruction, set the active slot to A and booted recovery.
  Recovery ADB is authorized, runs as root, and reports `ro.boot.slot_suffix`
  `_a`. No device partitions were written during inspection.
- Pulled `/sys/fs/pstore/pmsg-ramoops-0` to
  `/tmp/veux-recovery-pmsg-20261022.bin` (3,808 bytes; SHA-256
  `aff8c9bd99803b2dcd177a95f34f49ece24ffb180eadc3e85d83c49e49059b24`). It
  contains the exact `SHIM VEUX ramoops: XNU handoff` marker and corrupted
  printable fragments consistent with the early XNU milestones and the VEUX
  SDE probe. The remainder is too damaged to recover the final framebuffer
  marker result or a panic cause. This confirms the tested image handed off
  from the shim and entered early XNU code, but does not prove a successful
  framebuffer write or explain why the display stayed at the Xiaomi logo.
- Read the last 4 MiB + 4 KiB of `/dev/block/by-name/userdata` through recovery
  ADB. The decoder found no `VEUXLOG1` header. The raw tail SHA-256
  (`06955cde7f98b9503653b906e9634732d59a17a6dc2cb1a0e453fbdd4adaab86`)
  matches `backup/veux-device/userdata-tail-pre-veuxlog.bin` exactly, so this
  boot did not alter the reserved userdata tail. The tested RAM-disk image did
  not request the userdata logger, so this is expected.
- Current device state: slot-A recovery with authorized root ADB; the XNU test
  image remains on `boot_b`. Next useful step is to fix pmsg reliability or
  build a uniquely marked logger candidate before another boot test.

## >>> UPDATE 2026-10-22 (VEUX framebuffer screen-marker boot result) <<<

- The user authorized flashing the screen-marker diagnostic image to `boot_b`.
  Immediately before the write, fastboot identified product `veux`, current slot
  `b`, and `boot_b` size `0x8000000` (128 MiB). The source image SHA-256 was
  `64e021774ef9cb228a9ecbbdfc039252704aeb8901dfe9d06b90aa6087280125`.
- `fastboot flash boot_b` and `fastboot reboot` both returned `OKAY`; B remained
  active. No other partition was written. The user reports the display still
  shows only the Xiaomi logo. After reboot, neither ADB nor fastboot enumerated
  on the host.
- Unpacked image verification confirms XNU boot-args include `-v`,
  `veuxsde=1`, `veuxfbconsole=1`, and `veuxfb=1`; the embedded XNU payload
  includes the marker implementation. Thus the absent visible change does not
  show whether XNU failed before the probe, the live SDE guards rejected the
  marker, or the 32x32 mark was simply too small to notice.
- Next useful evidence is the persistent pmsg capture from this boot, especially
  the SDE probe's final `marker wrote/skipped` message and the early-kernel
  milestones. No such capture is currently available because USB has no ADB or
  fastboot transport. Preserve slot B and do not infer a successful XNU boot
  from the still-visible bootloader logo alone.

## >>> UPDATE 2026-10-21 (Evolution-X display source check and screen-marker candidate) <<<

- Inspected Evolution-X-Devices `device_xiaomi_veux` (`bka`, `7172cb5`),
  `vendor_xiaomi_veux` (`bka`, `0323407`), and `kernel_xiaomi_veux` (`bka`,
  `1add311`). The kernel DTS reserves `0x85200000..0x85e00000` as the 12 MiB
  continuous-splash region, matching the existing XNU guard's base and size.
- The VEUX panel DTS specifies 1080x2400, 24-bit DSI output, and
  `rgb_swap_rgb`; those describe the panel link, not CPU framebuffer byte order.
  The SDE catalog identifies Blair as SDE 6.9.0, matching revision guard
  `0x60090000`. These sources strengthen the reservation/controller match but
  do not prove the live scanout address or CPU pixel layout at XNU handoff.
- Prepared
  `shim/out/veux-diagnostic-39706120497/shim-boot-veux-screen-marker-39706120497.img`
  by adding `-v veuxfb=1` to the existing RAM-only diagnostic payload. The
  built kernel already contains the guarded 32x32 white marker and transparent
  text console; the command-line now requests both. Kernel, outer DTB, and all
  other payload bytes were verified unchanged; the Android boot-v2 ID was
  recomputed. Image size is 17,080,320 bytes; SHA-256 is
  `64e021774ef9cb228a9ecbbdfc039252704aeb8901dfe9d06b90aa6087280125`.
- This image was later flashed to `boot_b` on 2026-10-22 with user
  authorization; see the newer boot-result entry above. Do not switch from B.

## >>> UPDATE 2026-10-21 (ios-spes RAM-only XNU diagnostic) <<<

- Reviewed `AdyaGMD/ios-spes`. Its portable diagnostic idea is a tiny static
  init as PID 1 on an injected RAM disk (`rd=md0`), printing a heartbeat to
  `/dev/console`; its README reports this reached PID 1 on spes. Its FDT,
  memory map, framebuffer address, and SM6225 drivers are device-specific and
  are not evidence for VEUX/SM6375.
- Prepared `shim/out/veux-diagnostic-39706120497/shim-boot-veux-ramdiag-39706120497.img`
  (17,080,320 bytes; SHA-256
  `9c035b6e4d7b59bc2939d4f2aaf74cae19dfe4d1154367cc8244f4d3a4d4db33`). It
  reuses the VEUX XNU payload from CI run 39706120497, adds the existing static
  `tools/sweet-init.S` as a 32 KiB RAMDisk at `0x10289c000`, and regenerates
  the VEUX ADT with the iPhone X logical canvas (1125x2436 at 3x). Its
  boot-args use `rd=md0`, `ufsrw=0`, `rootrw=0`, and `sweetlog=0`; `veuxlog=1`
  is absent, so this diagnostic does not request the userdata log writer.
- The opt-in XNU console is enabled with `veuxfbconsole=1`; `veuxsde=1` records
  the guarded SDE state. `veuxfb=1` is omitted, so the separate white marker
  is disabled. Text and the PID-1 heartbeat should appear only if XNU's live
  SDE/address/geometry/format/stride checks accept the existing scanout. The
  prior boot reached kprintf startup but did not establish that the display
  guard passed, so visibility is still uncertain.
- The boot-v2 image was unpacked after packaging: kernel, ramdisk, and outer
  DTB match their inputs, and the Android image ID validates. No phone boot or
  flash occurred. Because `fastboot boot` is unsupported on this device, using
  this candidate requires a separate explicit approval to write `boot_b`.
- The new local `tools/mkadt.py` display-node edit and untracked XNU patch 0103
  remain outside this candidate's kernel build; patch 0103 has not been built.

## >>> UPDATE 2026-10-21 (VEUX display, userdata logging, and SWEET ports) <<<

- Added patches 0097–0102. Patch 0097 connects the VEUX pmsg printk path to the
  existing 4 MiB UFS ring, publishes ring bytes after storing them, bounds
  writes to the final 4 MiB + 4 KiB of the exact `userdata` partition on LUN 0,
  and requires `veuxlog=1`. Normal UFS/root writes remain read-only. Recovery
  reads the raw tail with `tools/veux-log-pull.sh`; it is not a file in the HFS+
  root. The image written earlier occupies 16 GiB of a much larger userdata
  partition, so this log window is outside that HFS+ image but overlaps the
  remaining old Android F2FS area. The old tail backup remains the restore
  point if needed.
- Patch 0098 adds an opt-in transparent framebuffer text overlay. It shares
  the marker's live SDE revision, DSI route, buffer address, geometry, linear
  8888 format, stride, and 12 MiB reservation checks. It draws white glyph
  foreground pixels only after all checks and mapping succeed; it does not
  clear rows or paint a background. `veuxfb=1` requests the guarded marker and
  SDE probe; `veuxfbconsole=1` separately requests the console.
- Patch 0099 enables the SWEET AMFI/entitlements provider on VEUX. Its
  permissive `Sandbox` stand-in remains off unless `veuxsandbox=1` is present.
  Patch 0100 ports `/dev/null` tee and bounded IOKit matching traces behind
  `veuxnull=` and `veuxiolog=`; patch 0101 enables the HFS rename-swap fallback;
  patch 0102 routes user-process crash details and optional heap strings into
  the console log (`veuxscan=`).
- Hardware-specific SWEET framebuffer bootstrap/IOMFB, touch, keys, power,
  USB, Goodix protocol, panel refresh, and secondary-CPU PSCI paths remain
  unported because their VEUX addresses or handoff behavior are not established.
  The VEUX console uses the existing guarded SDE handoff instead of SWEET's
  fixed scanout mapping. The existing VEUX patches already cover the board
  expert, single-core CPU/timer bring-up, PRNG/crypto compatibility, pthread,
  read-only UFS root, and DMA mapping. The original patch 0035 now enables its
  XML entitlements provider for VEUX as well as SWEET.
- All 102 patches pass `tools/validate-repo.py`. Patches 0097–0102 apply
  cleanly in order to the saved XNU tree from build 39699826454, and the new
  workflow checks the provider guard. The original CI attempts 39704310477 and
  39705176541 exposed a skipped entitlement patch; moving the VEUX guard into
  patch 0035 fixed it. CI run 39706120497 passed for macOS 13.5,
  DEVELOPMENT/VEUX. Kernel SHA-256:
  `a74be70aa3b8fe0cb81af24b8d0c9e7e09d4960ea7118b7665853aab9bec0049`.
- Packaged an unflashed Android boot v2 candidate at
  `shim/out/shim-boot-veux-xnu-39706120497.img` (17,063,936 bytes; SHA-256
  `d96d3a06355d487b0337f81e9a6226e8139be14fdb004a7ef945fde030ce7b7d`). Its
  embedded XNU payload SHA-256 is
  `b39e0517a0845b5817d7a59265e1344a830c3a321a5a50279af2956411a465a9`; the
  bootargs enable `veuxlog=1`, the SDE dump, guarded framebuffer marker, and
  text console. Offline unpacking verified the outer shim, payload, and
  selected `dtb_1.dtb` byte-for-byte. The image fits the 128 MiB boot_b
  partition. No phone partition was changed; the logger's actual UFS writes
  and framebuffer display still need runtime confirmation. Its reserved log
  window is in the tail of userdata and can overwrite residual Android F2FS
  data there; the saved tail backup is the recovery copy.

## >>> UPDATE 2026-10-21 (VEUX QEMU follow-up: board guards) <<<

- Re-ran the 0090 kernel on the VPS with QEMU 8.2.2, a QEMU-specific ADT, one Cortex-A76 CPU and no root device. XNU entered the kernel, then took a data abort at `_crypto_random_kmem_ctx_size+0xc` (`FAR=0x150`) and hit the debugger trap. QEMU serial output was empty. Captured artifacts are in `shim/out/qemu-veux-0090/`; the Android boot image was not run in QEMU.
- The QEMU log and kernel disassembly show `_kmem_crypto_init` still calling `crypto_random_kmem_ctx_size()`. The first attempted fix (CI run `39638151491`) reported success, but the builder log warned that patches 0085 and 0090 were skipped; its build tree confirmed the VEUX CPU and kmem fallback edits were absent. The original cause was a missing blank context line in patch 0085's `iokit/conf/files.arm64` hunk, which prevented 0085 and then 0090 from applying. Separately, the affected guards tested `VEUX`, although the compiler defines `ARM64_BOARD_CONFIG_VEUX`. Updated patches 0008, 0085 and 0090 to use the build-defined macro and repaired the 0085 hunk. A dry-run applying 0085 followed by 0090 to the saved build tree now succeeds.
- Added a VEUX post-build assertion to `.github/workflows/xnu.yml`, since the upstream builder can skip patches and still exit successfully. It requires the VeuxCPU registration, source entry and kmem fallback in the actual XNU tree. Corrected CI rebuild and QEMU rerun are pending.
- No phone boot or flash was performed. Generic QEMU does not test VEUX UFS, display, UART or other Qualcomm hardware.

## >>> UPDATE 2026-10-21 (VEUX phone bring-up patch 0090) <<<

- Added xnu/patches/0090-veux-phone-bringup.patch, derived from the saved VEUX XNU buildtree and the existing SWEET single-core driver/IRQ implementation. It registers a VEUX IOCPU for qcom,kryo, limited to cpus=1, with secondary CPU start and suspend still unsupported. The CPU-node reg width and MPIDRs match tools/mkadt.py and the selected board DTB.
- Extends the Qualcomm Group-1 timer/IRQ path to VEUX, using virtual timer INTID 19 from both the board-matched DTB and Android's active GICv3 IRQ counters. This supports the hypothesis that VEUX routes non-secure timer/IPI interrupts through Group 1; XNU delivery is not yet demonstrated on the phone.
- Adds buffered early boot milestones and panic text, flushed to the verified 1 MiB pmsg region inside the 2 MiB ramoops reservation after pmap_bootstrap makes ml_io_map_wcomb() usable. Failures before that mapping succeeds remain unpersisted. VEUX kprintf falls back to a discard sink if neither pmsg nor a serial device is available, so it does not draw on the unverified display.
- Enables the null-corecrypto startup fallbacks already used by SWEET for VEUX, including kmem RNG, the built-in PRNG and SHA-256. Also enables the already-staged libpthread provider and its required 56-byte ksyn_waitq_element storage for VEUX. These cover observed/identified shared bring-up gaps, not board-specific hardware support.
- Existing patches 0085-0088 already provide the VEUX device-tree expert, read-only UFS probe, pmsg log mapping, and UFS persistent-log work. The UFS path remains unvalidated on XNU and has no write enablement in this change. No framebuffer, touch, power, USB, or PSCI SMP code was enabled.
- GitHub Actions run 39634503409 succeeded on macOS 13.5 / DEVELOPMENT / VEUX, including patch application and compilation. Kernel artifact: xnu/out-39634503409/kernel.development.veux, SHA-256 7c8ddc5656a0d292da9b46be13de6914b846754dd221d60737457337b5ff549c.
- Built shim/out/payload-veux-0090-probe.bin and shim/out/shim-boot-veux-0090-probe.img. The payload uses the pmsg ramoops ADT and cpus=1 with rd=ufsroot0; it omits ufsrw/rootrw. Unpacking verified the outer shim kernel, ramdisk payload, and vendor_boot_b dtb_1.dtb byte-for-byte; the embedded VEUX ADT also matches. Boot image size 16,957,440 bytes, SHA-256 233bb1ddca493eff00657e5a649e9025cb2945451ffdafee19fa7d8d27d0d08c.
- No phone boot or flash was performed. fastboot devices returned no device; adb devices listed 4078cac030c8 as unauthorized. The bootloader previously rejected fastboot boot with unknown command, so an on-device test would require writing a boot partition. The user said not to flash; stop here unless they explicitly authorize a boot_b write. Keep userdata and slot A untouched.

# iOS 16 on sweet (Redmi Note 10 Pro, SM7150) - working notes

## >>> UPDATE 2026-10-21 (framebuffer-marker boot pstore read) <<<

- After the user reported fastboot, selected slot A and used `fastboot reboot
  recovery`; both commands succeeded. Recovery ADB became authorized and ran as
  root. No partition writes were made during log collection.
- Recovery exposed `/sys/fs/pstore/pmsg-ramoops-0` (2,984 bytes; SHA-256
  `305e50c7a4beedd622b63f6437c63e2403687b1c5260ce9027062c9ec2f438d7`). It
  contains the prior shim/XNU handoff text and output from the opt-in VEUX SDE
  probe, so the boot-B image reached the probe code. The dump is heavily
  corrupted. It appears to include SDE revision `0x60090000`, LM0 output size
  `0x09600438`, and a plane address containing `0x85200000`, but register values
  and the final marker-written/skipped message cannot be read reliably. Marker
  visibility and successful framebuffer writes therefore remain unconfirmed.
- Recovery's current `dmesg` is Linux recovery output, not the XNU boot log; its
  tail includes repeated missing `ipa_fws.mdt` firmware warnings, which do not
  explain the XNU stop. The raw pmsg capture is kept in `/tmp`, not the repo.

## >>> UPDATE 2026-10-21 (iOS userspace image flash) <<<

- From recovery, rebooted to fastboot and selected slot B; `fastboot getvar
  current-slot` reported `b` before the write. The userdata partition reports
  `0x196A3D3000` bytes.
- Flashed `/Users/vivien/Downloads/ios16-root-20H392.simg` to `userdata` only.
  It is a valid Android sparse image (4,194,304 blocks of 4,096 bytes; 16 GiB
  expanded), SHA-256 `9d20904cf584270fbb47ca968141cc33508e10ac7f649c03b0dd3581020cbf77`.
  Fastboot sent and wrote all 16 chunks successfully and exited 0. It warned
  that it skipped copying an AVB footer because the input is sparse; the flash
  still completed successfully.
- No reboot command was issued after the flash. On the final check the device
  no longer enumerated in fastboot or ADB, so its current USB/boot state is
  unknown. Slot B was selected; no boot partition was written in this step.

## >>> UPDATE 2026-10-21 (VEUX XNU QEMU probe) <<<

- Installed QEMU 8.2.2 (`qemu-system-arm`) on the VPS and ran the VEUX kernel payload on generic AArch64 `virt` with a QEMU-specific ADT (`mkadt.py --qemu --veux`), one `cortex-a76` CPU, and no UFS-root arguments. This was a kernel payload test; the Android `shim-boot-veux-ufs-log.img` itself is not a QEMU boot image.
- The guest entered XNU and executed far enough to hit a data abort at `_SHA1Init+0x34` (`FAR=0x28`), followed by an undefined instruction in `_DebuggerTrapWithState+0x84`; QEMU's final PC was in `_handle_debugger_trap`. Disassembly shows `_SHA1Init` dereferencing the crypto function table at offset `0x28`; this is consistent with `g_crypto_funcs == NULL`. SWEET patch `0032` installs the BearSSL SHA-1 provider only under `ARM64_BOARD_CONFIG_SWEET`, so the VEUX build does not take that workaround. The next kernel change is to enable the SHA-1 provider for VEUX and rebuild. The VPS run artifacts are `/root/veux-log-build/qemu-veux-run/{qemu.log,regs.txt,serial.txt,fb.png,result.json}`. `serial.txt` was empty, consistent with `virt` not emulating VEUX's UART. The framebuffer snapshot is not evidence of VEUX scanout or phone display behavior.
- This confirms CPU entry and execution in QEMU, not VEUX hardware startup. The `virt` machine does not emulate VEUX UFS, Qualcomm display, or the board UART. No phone was accessed or flashed.

## >>> UPDATE 2026-10-21 (VEUX BearSSL SHA-1 provider) <<<

- Added `xnu/patches/0089-veux-bearssl-sha1.patch`. It enables the existing BearSSL SHA-1 implementation under `ARM64_BOARD_CONFIG_VEUX`, adds the VEUX BearSSL include/compile flags, and enables the SHA-1 source/codecs for VEUX. The pinned staging script already fetched BearSSL for VEUX; the missing pieces were the SWEET-only source guards and include flags.
- Verified patch application against the VEUX XNU source in buildtree artifact `39589988254`; `tools/validate-repo.py` passed. GitHub XNU run `39628010706` succeeded with kernel SHA-256 `2031876e233799ab83c2c59d7449e9827d8b05a80089e0574d68e439d5fcf00f8` (`xnu/out-39628010706/kernel.development.veux`).
- Re-ran QEMU using the new kernel and the same `virt` setup. The prior `_SHA1Init` fault is gone. The next fault is now a null crypto-table dereference in `_crypto_random_kmem_ctx_size+0xc` (`FAR=0x150`), followed by the debugger trap; `serial.txt` remains empty. VPS artifacts are `/root/veux-log-build/qemu-veux-sha1/{qemu.log,regs.txt,serial.txt,fb.png,result.json}`. No phone boot or flash was performed.

## >>> UPDATE 2026-10-21 (SWEET-to-VEUX patch audit) <<<

- For the physical phone, the higher priority SWEET ports are the single-core `IOCPU` bootstrap in `0018` and Qualcomm GIC Group-1 timer/IRQ path in `0004`/`0017`. VEUX's generated ADT already gives the CPU nubs the compatible `qcom,kryo`, MPIDRs `0x0`..`0x700`, and `/arm-io/gic/virtual-timer-intid = 19`; the recovered DTB independently declares PSCI via SMC, timer PPI 3 (INTID 19), and eight CPUs. `VeuxPlatformExpert` publishes the CPU nodes but does not register an `IOCPU` or complete `ml_cpu_init_completed()`. The current non-SWEET XNU GIC setup still assumes Group 0 and PPI 27. Adapt the SWEET Group-1 route and timer lookup for VEUX, then use the single-core CPU driver with `cpus=1`; validate the self-IPI/timer before adding secondary cores. Match the CPU driver against `qcom,kryo` rather than `qcom,kryo470`.
- Do not port SWEET's complete PSCI/SMP patch `0065` into the first phone image. VEUX's DTB says PSCI 1.0 via SMC, and `mkadt.py --veux` starts with `cpus=1`, so CPU_ON is unnecessary for the first life signal. Port the CPU_ON path after single-core IRQ/timer behavior is observed; then cap topology against the VEUX MPIDR/cluster layout.
- The SWEET `start.s` change in `0004` also removes an exact `SCTLR_EL1` readback spin for Qualcomm. VEUX currently retains the spin. It is a plausible early-entry port because the shim hands XNU EL1 with the MMU off and XNU sets the control register itself; skip only the equality loop while retaining XNU's SCTLR writes, and record the VEUX register values if they become available.
- The phone's early-log gap is separate from display. Patch `0087` initializes pmsg at `STARTUP(KPRINTF)`, after `arm_init` and `arm_vm_init`, so it cannot log the earliest XNU stages or a failure during physical-map setup. Patch `0088` only flushes after UFS initializes. Port SWEET's staged early markers to a VEUX-safe pmsg/serial sink before any further phone boot. The known `qcom,msm-geni-console` at `0x04c8c000` is a serial candidate, but its clocks/pins/mode are not yet ported and no external UART capture is available. Keep the framebuffer path disabled: `0x85200000` is a reserved splash region, not a verified active scanout with known format.
- SWEET's physmap padding fix `0011` is already in the ordered VEUX patch series and is directly relevant to the phone's `--highmem` boot range. The recovered contiguous high-bank candidate is `0x100000000` + `0xf8600000`, stopping before the reserved carveout; this still needs XNU runtime validation. Do not reintroduce SWEET's older `0xfcc00000` size.
- The exact QEMU allocator fault is still a generic phone blocker too: patch `0013`'s private per-CPU RNG bypasses the null `g_crypto_funcs` call, but is guarded by `defined(SWEET)` while VEUX defines `VEUX`. Port it after the board-specific single-core path is addressed. SWEET's known subsequent `read_random` failure was fixed by PRNG patch `0014` plus direct SHA-256 handling in `0023`; keep those as the next generic startup fixes if they reproduce on the phone.
- Found a VEUX integration gap in patch `0019`: `0019-stage-libpthread.sh` and Makefile flags stage the provider for both SWEET and VEUX, but the provider C files, `ksyn_waitq_element` layout, and size assertion are guarded only for `ARM64_BOARD_CONFIG_SWEET`. As written, VEUX compiles empty provider translation units and retains 48-byte opaque storage, while the pinned libpthread-514.100.2 provider expects 56 bytes. Extend the VEUX guards and ABI storage/assertion before relying on BSD threads or attempting launchd; this is not the current early-QEMU blocker.
- The built-in HFS port is already configured for VEUX: `0026-stage-hfs.sh` accepts `MACHINE_CONFIG=VEUX`, and `MASTER.arm64.veux` includes `sweet_hfs`. The BearSSL AES-CBC, MD5, and SHA-384/512 patches (`0020`, `0027`, `0033`) are plausible later ports because they bypass missing corecrypto providers, but are not needed to fix the observed kmem call; port them in response to a concrete crypto fault or userland requirement.
- Port SWEET driver logic, not SWEET's hardware addresses: touch/power, USB, watchdog, and raw UFS setup use different VEUX devices. VEUX already has its own platform/UFS/logging patches (`0085`–`0088`); UFS remains read-only and unvalidated on XNU. The Sweet crash-log patches also need a working VEUX console or persistence path.
- This was a source/config audit only. No XNU source patch, build, device boot, or flash was performed. Phone-first next build candidate: VEUX Group-1 timer/GIC path + the single-core CPU registration + an early non-display log sink, retaining `cpus=1` and the existing high-memory carveout. Add PSCI SMP only after that single-core path is observable.

## >>> UPDATE 2026-10-21 (offline VEUX framebuffer source analysis) <<<

- Compared the saved VEUX live device tree, board-matched panel DTS and the reference Qualcomm SDE source. The live tree's `/reserved-memory/splash_region@0x85200000/reg` is `<0x85200000 0x00c00000>` (12 MiB); adjacent DFPS memory is `<0x85e00000 0x00100000>`. This confirms the reserved region, not the bootloader's currently active scanout pointer.
- In the reference `techpack/display/msm/sde/sde_kms.c`, `_sde_kms_get_splash_data()` reads `splash_region.reg` as `splash_buf_base/size`; `_sde_kms_splash_mem_get()` maps that same physical address as the SDE IOVA. `sde_rm_cont_splash_res_init()` detects the active CTL/LM/SSPP routing to preserve continuous splash. The handoff structure carries address/size and topology, but this code does not recover a framebuffer memory FourCC, byte stride, or pixel channel layout from the bootloader. It establishes intended use of this reservation for splash handoff, not that it is active on a particular boot.
- The VEUX panel DTS specifies 1080x2400, 120/60 Hz, 24-bit DSI input, DSI `rgb_swap_rgb`, and DSC at 8 bits-per-pixel. These are panel/link properties; they do not define the CPU-visible framebuffer memory format. Do not translate `rgb_swap_rgb` into XRGB/ARGB channel order.
- The saved live DT has MDSS base `0x05e00000`; `qcom,sde-sspp-off` lists VIG0 at `0x5000` and DMA0 at `0x25000`. In the reference SSPP implementation, source addresses, Y-strides, pixel format, op mode and UBWC control are at offsets `0x14–0x20`, `0x24/0x28`, `0x30`, `0x38`, and `0x44/0x48`. Candidate VIG0 registers are at `0x05e05000 + offset`; DMA0 at `0x05e25000 + offset`. The SDE resource-manager code reads CTL layer registers and determines which SSPP is staged; reading those selected pipe registers at the ABL handoff could provide base/stride/hardware-format/compression evidence. These are source-derived candidate addresses, not live register values. Read-only access still depends on the display block being mapped/powered, and a current Android capture would show Android's reprogrammed plane rather than the earlier splash state.
- Android's captured DRM primary plane is `XB24` / `DRM_FORMAT_XBGR8888`, but uses Qualcomm modifier `0x500000000000001`, a 1088x2400 allocation and 4352-byte pitch. It is an imported compressed Android scanout object (`start=0`), not proof of the ABL splash layout. A 4352-byte linear stride would consume 10,444,800 bytes for 2400 rows and fit in the 12 MiB reservation, but this is only a plausible calculation from Android's later state, not a verified ABL stride.
- Offline ABL artifact check: `abl_a.img` and `abl_b.img` are byte-identical (SHA-256 `3f51a65f47dabf9f87e700361e218c8ebde1f7c405e24a49e85e8c40189cd35d`); `imagefv_a.img` and `imagefv_b.img` are also byte-identical. They are executable firmware artifacts, not RAM/framebuffer dumps. Ghidra identified an ARM ELF entry at `0x9fa00000`, but only a small mapped segment and one invalidly decoded entry routine; no usable splash-format or runtime scanout evidence was recovered. Firmware signature scanning was unavailable on this macOS host because the REA Binwalk integration requires Linux. No phone access, boot, flash, or partition write was performed.
- Offline conclusion: retain the candidate address `0x85200000` and the confirmed Android mode/pitch as separate evidence. The ABL scanout base/stride/channel layout at XNU handoff remain unverified. The source work has now identified the SDE SSPP registers to capture; obtaining actual values still needs a pre-Android runtime register/memory capture. Keep XNU framebuffer writes disabled.

## >>> UPDATE 2026-10-21 (SWEET early-console comparison for VEUX) <<<

- Read SWEET patches `0003`, `0010`, and `0012`. SWEET's first visible life marker is a direct framebuffer band in `start.s`, before page tables, followed by `sweet_early_mark()` milestones during `arm_init`/`arm_vm_init`. Its early console stays mapped across TTBR0 teardown, then the later ADT-driven framebuffer serial console takes over. These writes depend on SWEET's verified scanout at `0x9c000000`, 1080x2400, stride 4320, and matching bootstrap page-table mappings; they cannot be copied to VEUX's unverified scanout.
- The existing VEUX handoff image already writes `SHIM VEUX ramoops: XNU handoff` into Android's pmsg ring immediately before the XNU jump. Its payload uses the `--highmem` range beginning at `0x100000000`, so the pmsg reservation at `0xd0000000` is outside XNU's managed RAM range. This is the safest current pre-kernel signal, but it has not been recovered after the prior forced return to fastboot/recovery. Because ramoops is RAM-backed and the reset method may clear it, that missing marker does not prove the shim failed to run.
- Recovery ADB is currently connected as root on slot A. `/sys/fs/pstore` is empty in this recovery session. No userdata or other phone partition was touched in this investigation. A SIMG root image is not required for XNU's early startup; userdata matters only when XNU reaches UFS/root mounting, well after the early-console milestones.
- Read-only recovery DRM/sysfs confirms DSI-1 is connected/enabled but does not expose a scanout address. Recovery dmesg reports `ramoops: found existing invalid buffer, size 1048028, start 1048540` and then registers/zaps the 2 MiB region. This shows the retained pmsg header was invalid before recovery initialized it, but does not identify which prior boot wrote it or prove how far XNU ran. The ADB recovery log cannot recover the old ring after the ramoops driver zaps it.
- Wrote `VEUX_WARM_RESET_TEST_20261021` to `/dev/pmsg0` in root recovery, then rebooted through fastboot back to recovery (no partition writes). After that transition ADB enumerates as `unauthorized`, so the marker could not yet be checked. Current phone state is recovery with ADB unauthorized; do not assume it is still rooted/authorized until ADB reconnects.
- Next useful signal requires either (a) a repeatable warm-reset path that preserves ramoops so the pre-XNU marker can be read, or (b) a verified VEUX display scanout/UART path. Do not write a guessed framebuffer address or treat the old black-screen result as evidence that a SIMG is required.

## >>> UPDATE 2026-10-21 (userdata logger result and recovery return) <<<

- The phone returned to USB fastboot. Set slot A active and `fastboot reboot recovery` succeeded. Recovery ADB is root again when using `/Users/vivien/Library/Android/sdk/platform-tools/adb`; `/usr/local/bin/adb` 37.0.1 did not start its daemon reliably in this state.
- Ran `tools/veux-log-pull.sh`; it found no `VEUXLOG1` header. Independently read the expected final 4 MiB + 4 KiB of `userdata` and compared it with `userdata-tail-pre-veuxlog.bin`: both SHA-256 values are `06955cde7f98b9503653b906e9634732d59a17a6dc2cb1a0e453fbdd4adaab86`, with 0 changed bytes. The logger did not write to userdata, so no restoration was needed and the saved backup is retained.
- The built XNU Mach-O contains `veux_log_append`, `veux_log_thread`, the logger messages, and UFS error strings. This confirms the code was linked; the missing disk marker only tells us that the logger never completed a flush. Whether XNU stopped before UFS initialization, the UFS setup failed, or the logger thread did not run is still unknown. Do not retry this same image: the current log path cannot capture the early failure.
- Current state: slot A recovery with root ADB; `boot_b` still contains the VEUX UFS logger test image; userdata matches its pre-boot tail backup. Next work needs an earlier capture path that can report UFS initialization failures before any more B boot attempt.

## >>> UPDATE 2026-10-21 (VEUX userdata logger build and B boot attempt) <<<

- Full XNU CI run `39618385680` succeeded for macOS 13.5 / DEVELOPMENT / VEUX after adding patch `0088`. Kernel SHA-256: `9f517d8984fbf86d6bf4ff5a5adcf3fca4bf673fab4d49e1cc72e45e0df63ff8`. Local syntax-only compile of the two changed XNU sources also passed.
- Packaged `shim/out/shim-boot-veux-ufs-log.img` (16,957,440 bytes; SHA-256 `9032e05292ecbb498c6e92b931630198ab8e5118d397f1b2e6185a763a6f3a13`). Offline unpack verified Android boot header v2, byte-identical shim kernel, payload, and `dtb/vendor_boot_b_unpacked/dtb_1.dtb`. Payload cmdline is `debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam -noprogress rd=ufsroot0 veuxlog=1`.
- Before booting, recovery ADB saved the raw 4 MiB + 4 KiB userdata tail to `/Users/vivien/Documents/ChatGPT/iosxia/backup/veux-device/userdata-tail-pre-veuxlog.bin` (SHA-256 `06955cde7f98b9503653b906e9634732d59a17a6dc2cb1a0e453fbdd4adaab86`). The user requested the bounded userdata log write; this region may overwrite encrypted F2FS data. No userdata write has been read back yet.
- Recovery was on slot A. `fastboot flash boot_b shim/out/shim-boot-veux-ufs-log.img` succeeded (`Sending` and `Writing` OKAY; `boot_b` is 128 MiB). Then selected slot B and rebooted. After 45 seconds, neither ADB nor fastboot enumerated the phone; XNU boot result and whether it flushed the logger are unknown. Phone currently needs to be manually returned to fastboot (Power + Volume Down). Once visible, select A and `fastboot reboot recovery`, read/decode the userdata tail with `tools/veux-log-pull.sh`, then restore the saved tail bytes so the Android F2FS area is returned to its original contents. Do not alter any partition besides the already-authorized `boot_b` and this bounded userdata tail.

## >>> UPDATE 2026-10-21 (VEUX bounded userdata log writer) <<<

- Recovery ADB confirms `userdata` is `/dev/block/sda22` (UFS LUN 0), 4096-byte blocks; it is Android encrypted F2FS. A separate 64 MiB OEM `logdump` partition is `/dev/block/sde41` on LUN 4. The chosen implementation follows the user's explicit userdata request: it stores a 4 MiB ring plus one 4 KiB header in the final 4 MiB + 4 KiB of userdata. This is a raw reserved log window, not a normal Android directory; writing there can corrupt Android F2FS data in that tail. Recovery ADB reads only that window and decodes it into `research/veux-logs/*.txt` on the Mac.
- Added `xnu/patches/0088-veux-ufs-persistent-log.patch`. It buffers early console output in RAM, starts flushing after VEUX UFS identifies `userdata`, and permits WRITE(10) only inside that exact tail window. VEUX's regular UFS block device remains read-only and `ufsrw=1` remains ignored. The log can only capture messages after a successful UFS initialization flush; no file or raw userdata write has yet been attempted.
- Added `tools/veux-log-pull.sh` and `tools/veux-log.py` to read/decode the log through recovery ADB into a host-side text file. Patch dry-run against the staged XNU source succeeded, and local Xcode clang syntax-only compiles of `sweet_ufs.c` and `serial_console.c` both passed. Full CI build, boot-image packaging, flashing, and runtime logging remain pending. The phone is still in slot A recovery; do not change the slot until the new image is built and checked.

## >>> UPDATE 2026-10-21 (VEUX read-only UFS port review) <<<

- The XNU source already contains the initial SWEET-derived VEUX port in `xnu/patches/0086-veux-readonly-ufs.patch`: it uses the `/veux-ufs` ADT node (`0x04804000`), polled UFSHCI/SCSI READ(10), LUN 0, and read-only root access. CI run `39581112792` previously compiled that port. VEUX DMA/UTRL takeover and XNU GPT parsing remain untested on hardware.
- Recovery ADB confirmed host0 at `0x04804000`; UFS LUN 0 is `sda` with 4096-byte logical blocks; `userdata` is `sda22`. `boot_a` is `sde9` on LUN 4. Read-only reads show LUN0 LBA0 is zeroed and LBA1 begins `EFI PART`; the GPT header specifies 128 entries of 128 bytes beginning at LBA2. This matches the SWEET parser's LBA1 GPT lookup. Earlier note claiming the entire first 8 KiB was zero was incorrect.
- Fixed the shim's UFS base selection: `shim/ufs.c` now uses `shim/target.h`, and `shim/build.sh --veux` defines `DEVICE_VEUX`, selecting `0x04804000` rather than SWEET's `0x01d84000`. Both VEUX and SWEET UFS translation units compile with local arm64 Clang. This affects the diagnostic shim only; the VEUX no-payload fail-stop still prevents its UFS probe from running without a deliberate diagnostic-mode change.
- No image was built, flashed, or booted in this follow-up. The phone remains in slot A recovery; `boot_b` still contains the previously authorized pmsg handoff probe. No UFS writes were issued.

## >>> UPDATE 2026-10-21 (VEUX persistent pmsg logging path) <<<

- Android slot A exposes an active `d0000000.ramoops`: runtime parameters read as base `0xd0000000`, size `0x200000`, record-size `0x100000`, console-size `0`, pmsg-size `0x100000`, ECC `0`. `/dev/pmsg0` is available. The live/reference Blair DT declares the same 2 MiB region with a 2 MiB pmsg allocation; runtime overrides it to split 1 MiB record + 1 MiB pmsg, which is the layout used below.
- Tested the host-readable retention path without touching partitions: wrote marker `XNU_RAMOOPS_COMPAT_TEST_20261021` to `/dev/pmsg0`, rebooted normally, returned to Android slot A, and found the marker in `/sys/fs/pstore/pmsg-ramoops-0` (also readable through `logcat -L`). This confirms pmsg survives a normal warm reboot and Android exposes it after reboot. The marker is an Android pmsg entry; it is not an XNU boot result.
- Added source patch `xnu/patches/0087-veux-pstore-pmsg-log.patch` plus a `veux-ramoops` node in `tools/mkadt.py --veux`. The XNU logger validates the exact observed region, appends chars using Linux persistent_ram's no-ECC PMSG header/ring layout, and routes kprintf output to that region even when no serial console exists. It leaves the first 1 MiB panic-record area alone. Patch dry-run against the staged XNU source succeeds; generated VEUX ADT shows `reg=<0xd0000000 0x200000>` and `pmsg-size=0x100000`.
- First CI run `39589017531` reached the compiler but failed because `pe_serial.c` lacked the private `<arm/caches_internal.h>` declaration for `CleanPoC_DcacheRegion_Force`. Added the include to patch 0087. CI run `39589988254` then succeeded for macOS 13.5 / DEVELOPMENT / VEUX; kernel SHA-256 is `2784b777ca2815d1ba366c47971d047aa682cf123f70f34068a8bbb41b6cb94f`.
- Packaged `shim/out/shim-boot-veux-pmsg-probe.img` (16,953,344 bytes; SHA-256 `e356345bf9aaaf330edf5c5f6094473583579126a9edab1b02d6e77c279eaaee`). Android v2 boot metadata, shim kernel, and external DTB are preserved; unpack-and-byte-compare checks passed. Payload uses single-core and read-only UFS args. It has not been flashed or booted, so XNU log capture is not yet confirmed.
- ADB confirmed healthy Android slot A (`_a`, `sys.boot_completed=1`) before flashing. The user authorized writing the new image to `boot_b`; fastboot reported `Sending` and `Writing` both `OKAY`, partition size `0x8000000` (128 MiB), and current slot remained A. The user then authorized selecting B and rebooting. `fastboot set_active b` and `fastboot reboot` returned `OKAY`. ADB is not expected while XNU runs because this image does not start Android or `adbd`; lack of ADB alone does not establish a freeze. The user returned to fastboot, we set slot A active, and `fastboot reboot recovery` returned `OKAY`. Recovery ADB later became authorized/root. Recovery reported the ramoops device at `0xd0000000` and `/dev/pmsg0`, but `/sys/fs/pstore` had no entries. Rebooted to healthy Android slot A (`sys.boot_completed=1`); `pmsg-ramoops-0` was readable but contained only recovery/Android ADB strings, with no `XNU VEUX ramoops log start` marker or XNU text. `adb logcat -L` also had no XNU entries. Therefore this attempt yielded no XNU stop-point log; whether logger init ran is unconfirmed. Userdata was not written.

## >>> UPDATE 2026-10-21 (GENI console capture path investigation) <<<

- Read-only ADB on healthy Android slot A confirms `ro.boot.console=ttyMSM0`, but `/sys/class/tty/ttyMSM0` and `/sys/bus/platform/drivers/qcom_geni_serial` are absent. This means Android does not expose a usable serial TTY to ADB; it does not establish whether ABL or the kernel used the UART earlier in boot.
- Reference Xiaomi `holi-qupv3.dtsi` defines debug GENI UART SE9 at `0x04c8c000` (0x4000), IRQ SPI 510, with `se-clk`, `m-ahb`, `s-ahb`, wrapper `qupv3_1`; `blair.dtsi` enables `qupv3_se9_2uart`. `blair-pinctrl.dtsi` routes it through GPIO25/GPIO26 with `qup13_f2`, active 2 mA and bias disabled, sleep pull-down. This is source-tree evidence; it does not identify those GPIO pads' physical board locations or confirm the installed firmware's exact state.
- Android common's Qualcomm GENI console driver confirms a complete console path depends on resource/clock/console setup. Current XNU has no GENI backend. Public device-specific “test point” results found in this pass describe EDL entry only, not UART breakout; do not treat those as UART pins. No verified host capture route is available, so do not add speculative MMIO initialization or boot another image yet.
- Next useful prerequisite for a GENI log attempt is a confirmed physical TX/GND location and 1.8 V-compatible USB-TTL capture, or another documented host-visible early-console route. Once that exists, implement/compile a polled GENI TX backend with bounded waits, first test from a controlled image, and keep slot A/userdata untouched. `boot_b` remains the previous probe image; no partition writes were made during this investigation.

## >>> UPDATE 2026-10-21 (post-probe diagnostics checked) <<<

- Android is healthy on slot A (`ro.boot.slot_suffix=_a`, `sys.boot_completed=1`); connected ADB device is `veux` (`2201116SG`). No partition operation was performed during this check.
- Checked Android's post-probe logging surfaces read-only. `/sys/fs/pstore` is empty when accessible as root, `/proc/last_kmsg` is absent, `/sys/kernel/debug/pstore` is absent, and `dmesg` is denied (`klogctl: Permission denied`). Android properties report `bootloader` for both boot-reason keys, which does not identify the preceding XNU failure. The failed XNU attempt therefore left no recoverable stop-point log in the available Android environment.
- Re-verified local stock `boot_b` backups: `/Users/vivien/Documents/ChatGPT/iosxia/backup/veux-device/boot_b.img` and `../veux-debugfs-kernel/repack-work/boot_b.stock.img` are each 128 MiB and share SHA-256 `71425c2c3bfb124b40d62bb66bf18ea25a4f52879aa9784b3c56e2c18d36f2db`. The 16 MiB probe image matches SHA-256 `32358acc81b5799281a2d3e00289f3fbe63d0cf5d3aaaa34acd16d63e4e0cb91`. No restore has been performed; `boot_b` remains the probe image and slot A remains active.
- Next blocker remains a capture path before another XNU boot. Candidate GENI console at `0x04c8c000` is DT-identified, but no live serial node, verified pad mapping/capture, or XNU GENI implementation is available. Avoid speculative UART writes, framebuffer writes, or reuse of Android's ramoops reservation. Restore `boot_b` from the verified backup only with the user's explicit confirmation because it writes a partition.

## >>> UPDATE 2026-10-21 (returned to Android slot A after VEUX probe) <<<

- After the probe froze on a black screen, the user re-entered fastboot. It reported current slot B. Switched active slot to A and rebooted; ADB is back, `ro.boot.slot_suffix=_a`, `sys.boot_completed=1`, Android 16. Slot A and userdata were not written during the probe. `boot_b` still contains `shim-boot-veux-ufs-probe.img`; the byte-matched stock backup remains available but has not been restored.
- Probe result is limited to a black-screen freeze with no ADB/fastboot enumeration while B was selected. Without a log path, the XNU stop point and UFS progress remain unknown. Do not retry on B or write userdata until logging is added and the user authorizes any partition writes.

## >>> UPDATE 2026-10-21 (VEUX read-only UFS probe boot attempt) <<<

- User explicitly authorized flashing the prepared diagnostic to `boot_b` after `fastboot boot` was rejected by ABL. `fastboot flash boot_b shim/out/shim-boot-veux-ufs-probe.img` succeeded (`Sending` and `Writing` both `OKAY`). The written image SHA-256 was `32358acc81b5799281a2d3e00289f3fbe63d0cf5d3aaaa34acd16d63e4e0cb91`, 16,556 KiB; only `boot_b` was written. The phone was on slot A before the operation; `fastboot set_active b` and `fastboot reboot` both returned `OKAY`.
- After reboot, neither `adb devices` nor `fastboot devices` lists the phone. With no verified UART or framebuffer logging, this does not establish whether XNU started, where it stopped, or whether the phone reset. Screen state is unknown. No userdata writes were issued; the payload enforces read-only UFS and has no `ufsrw`/`rootrw` arguments.
- Next: ask the user what the screen shows and, once fastboot is reachable, restore slot A as active before any further experiment. Preserve the probe image and the matching 128 MiB stock `boot_b` backup (SHA-256 `71425c2c3bfb124b40d62bb66bf18ea25a4f52879aa9784b3c56e2c18d36f2db`). Do not flash userdata until the UFS probe has a usable observation path and the user confirms that destructive write.

## >>> UPDATE 2026-10-21 (VEUX read-only UFS kernel and probe image) <<<

- Pushed commits through `d864eb8` to `59c84486t9-alt/ios-veux:veux-xnu-build` and ran GitHub Actions build `39581112792` with macOS 13.5 / DEVELOPMENT / VEUX. The workflow completed successfully. Downloaded `kernel.development.veux` is arm64 Mach-O, 16,989,624 bytes, SHA-256 `3541114f0b871eed6bdd531d4fa819e10e94d4909f015d06b836149c2e3a6245`; it includes patch 0086's read-only VEUX UFS root path.
- Built `shim/out/veux-ufs-probe.adt`, `shim/out/payload-veux-ufs-probe.bin`, and `shim/out/shim-boot-veux-ufs-probe.img`. Probe args are single-core and read-only (`rd=ufsroot0`, no `ufsrw`/`rootrw`); the payload keeps display writes disabled and uses the previously selected `dtb_1.dtb`. Unpacking the Android v2 boot image and comparing its kernel, payload ramdisk, and DTB to their sources succeeded byte-for-byte. Boot image SHA-256 `32358acc81b5799281a2d3e00289f3fbe63d0cf5d3aaaa34acd16d63e4e0cb91`.
- Phone is in fastboot with slot A active and bootloader unlocked. `fastboot boot shim/out/shim-boot-veux-ufs-probe.img` returned `FAILED (remote: 'unknown command')`; no boot or flash occurred. `boot_b` is a 128 MiB partition. The local original `boot_b` backups `/Users/vivien/Documents/ChatGPT/iosxia/backup/veux-device/boot_b.img` and `../veux-debugfs-kernel/repack-work/boot_b.stock.img` are both 128 MiB with matching SHA-256 `71425c2c3bfb124b40d62bb66bf18ea25a4f52879aa9784b3c56e2c18d36f2db`.
- Early UART logging remains unresolved: the candidate GENI console has no XNU driver or verified clock/pinctrl handoff, and VEUX display writes remain disabled. Thus this boot image has no usable host-side kernel log capture yet. Do not repurpose Android ramoops. Next possible probe is to write this exact 16 MiB image to inactive `boot_b` and select B temporarily; this is a partition write, so obtain the user's confirmation first. Keep userdata untouched until the probe is understood and a separate confirmation is given.

## >>> UPDATE 2026-10-21 (local HFSX root image check) <<<

- Found `/Users/vivien/Downloads/ios16-root-20H392.simg` (Android sparse, 16 GiB logical). Its HFS volume header identifies case-sensitive HFSX (`HX`), block size 4096, total 4,194,304 blocks, volume `iOSRoot`.
- macOS `fsck_hfs -fn` found two catalog folder-count metadata errors. I made a temporary expanded clone, repaired that clone, and verified it with a second `fsck_hfs -fn`; the original sparse image was left untouched. macOS recognizes the clone as case-sensitive Journaled HFS+ but still refuses to mount it (`no mountable file systems` / `mount_hfs: Invalid argument`), so launchd paths have not yet been inspected. Temporary expanded files were removed.
- The previous successful VEUX XNU build includes the built-in HFS sources, but it predates patch 0086 and has not been booted. The phone still runs Android from encrypted F2FS userdata. No phone data was written.

## >>> UPDATE 2026-10-21 (VEUX UFS read-only port) <<<

- Read-only Android ADB on slot A: Linux reports `/dev/block/sda` with 4096-byte logical blocks and maps `userdata` to `sda22` (sysfs start `23961920`, size `213196440`, in 512-byte sectors). Android currently mounts `/data` as F2FS from `/dev/block/dm-40`; raw `sda22` begins with non-plaintext bytes, so this is still Android’s encrypted userdata, not the iOS HFS+ image.
- Raw reads of the first 8 KiB and last 512-byte sector of `sda` returned zeroes. No GPT signature/CRC was recoverable from those locations. Preserve this as an unresolved mismatch: sysfs has the Linux partition map, but the underlying GPT bytes were not visible through the same block node. Temporary read dumps are under `/tmp/veux-*` and are not in git.
- Added `xnu/patches/0086-veux-readonly-ufs.patch`. VEUX `rd=ufsroot0` now selects the `/veux-ufs` ADT node and reuses the existing UFSHCI polled READ(10) block path. VEUX forcibly sets the device read-only, ignores `ufsrw=1`, and skips SWEET-only persistent log, sampler, keys, touch, and USB startup. No partition or phone data was written.
- `patch --dry-run` against the locally staged XNU buildtree accepts 0086. This is patch-application validation only; VEUX UFS host state after ABL, READ CAPACITY, GPT access, DMA/cache behavior, and any XNU root mount remain untested. The raw zero GPT sectors are a blocker for claiming the partition parser works. No boot or flash occurred.
- Next: investigate why Android’s sysfs partition map disagrees with raw LUN0 reads, then run the macOS XNU build workflow. Only after successful compile and a separate explicit boot decision should an XNU read-only UFS probe be attempted.

## >>> UPDATE 2026-10-21 (VEUX CPU / PSCI / timer research) <<<

- Read-only Android ADB on slot A: online CPUs `0-7`; `/proc/interrupts` shows active `GICv3 19 Level arch_timer` counts on all eight cores. The selected `dtb_1.dtb` declares PSCI 1.0 via SMC, `enable-method = "psci"` on all CPU nodes, and a 19.2 MHz architected timer whose virtual timer is GIC INTID 19. These facts validate the Android/Linux path only; XNU has not yet exercised SMC, GIC delivery, or the timer.
- The same DTB identifies the Android console as `ttyMSM0` (`qcom,msm-geni-console` at `0x04c8c000`, 0x4000 window, SPI 510). This is a candidate log path, but XNU has no VEUX GENI UART setup yet. The DTB's 2 MiB ramoops reservation at `0xd0000000` belongs to Android pstore and must not be repurposed. The SWEET screen console remains disabled for VEUX.
- No XNU boot was attempted. Before runtime validation, add VEUX CPU/GIC/timer startup and a GENI console path, compile through CI, and then prepare a controlled boot test. Details and source evidence are in `VEUX-HW-RESEARCH.md`.

## >>> UPDATE 2026-10-21 (VEUX platform expert source patch) <<<

- Added `xnu/patches/0085-veux-device-tree-platform-expert.patch`. It adds a `VeuxPlatformExpert` config match for root compatible `xiaomi,veux`, compiles the class in the ARM64 source list, and publishes `/cpus` plus the real top-level device-tree nodes while excluding `chosen`, `defaults`, `cpus`, and the absent Apple `/options` NVRAM node.
- The VEUX ADT keeps `D22AP` first in the root compatible list and `iPhone10,3` as `model`, preserving the iOS userland identity. XNU `IODTCompareNubName` checks the full compatible string list, so the VEUX expert can match the later `xiaomi,veux` compatible without changing those identity properties. Target/product name overrides are intentionally omitted so XNU keeps deriving the iPhone identity from the ADT.
- The patch parses as a unified diff. It has not yet been applied in a full XNU CI build or booted; this is source work only. No device boot or flash occurred. Next: run the ordered patch series through the macOS XNU workflow and resolve any compile diagnostics before any boot attempt.

## >>> UPDATE 2026-10-20 (VEUX boot-image packaging probe) <<<

- Built an unbooted, non-flashed Android header-v2 package at `shim/out/shim-boot-veux-probe.img` (current SHA-256 `e27689fec855aeb261cf2775f00be3d904fa46d912b5ee24851f71787e5d5c51`). Its ramdisk contains `payload-veux-probe.bin` (current SHA-256 `b0d4f860d57a8973595ab68caa896bc28d078994d25c68d0e0549a90a4fdc2ed`) and its appended DTB exactly matches `dtb_1.dtb` selected by board ID `0x1000b, 0`.
- Added a `--veux` ADT mode with VEUX-compatible identity, verified GIC/UFS bases, and no framebuffer node; CPU starts with `cpus=1`. The shim `--veux` build disables framebuffer writes, leaves boot video fields zero, and halts if payload loading fails instead of running SWEET-specific UFS/GIC probes. The boot arguments omit `rd=ufsroot0`, writable-root and SWEET framebuffer settings because VEUX XNU UFS/display support is not ported.
- **This is a packaging probe, not a boot-ready image.** An earlier package used SWEET's `dram-size=0xfcc00000`; read-only recovery capture found a reserved high-bank carveout at `0x1f8600000`, so that earlier artifact overlaps reserved memory. `VEUX-HW-RESEARCH.md` records the observed candidate `dram-base=0x100000000`, `dram-size=0xf8600000`; the current generator and probe payload use it. The VEUX XNU profile still lacks a VEUX IODT platform expert, validated CPU/PSCI/timer startup, and UFS/root support. No phone boot or flash occurred.
- Cross-compiled on the Ubuntu VPS with `gcc-aarch64-linux-gnu`; the AOSP/Ubuntu `mkbootimg` v2 output was unpacked locally and byte-compared against both the payload and selected DTB. `mkbootimg`'s optional GKI v4 helper was unavailable in Ubuntu's package, so this v2-only build used a local stub that errors if v4 signature code is called; v2 did not call it.

## >>> UPDATE 2026-10-20 (VEUX Android DRM + XNU build retry) <<<

- Rooted Android on slot B with Magisk and the temporary `CONFIG_DEBUG_FS=y` kernel exposed `/sys/kernel/debug/dri/0/state`. Active DSI-1 is 1080x2400@120; primary plane is `XB24` / `DRM_FORMAT_XBGR8888`, allocated 1088x2400 with 4352-byte pitch, modifier `0x500000000000001`, imported GEM object, and driver-reported `start=0`. Two active overlays use `AB24`. See `docs/VEUX-ANDROID-DRM-FINDINGS.md` and raw capture outside git at `../veux-debugfs-kernel/magisk-patch/android-drm-state.txt`.
- This identifies Android's active DRM format and geometry, but no physical address; its modifier is nonzero, and this does not prove `0x85200000` is scanout. Keep framebuffer writes disabled. The DRM state was captured before `sys.boot_completed` became true, so it is not evidence of a fully completed Android boot.
- Current `0082-veux-machine-config.patch` includes the VEUX processor cache-line case and GICv3 macros missing from earlier CI attempt `39518824437`; those compile errors are gone. Run `39531341699` reached link and failed with 264 unresolved generic arm64 pmap/assembly symbols because VEUX lacked `MASTER.arm64.veux` enabling `nos_arm_pmap` and `nos_arm_asm`. Added `0083-veux-open-source-arm64-config.patch`; retry `39532087795` cleared the linker errors, then stopped at missing `hfs.h` because HFS/libpthread/BearSSL staging scripts were SWEET-only. Retry `39532741922` staged those sources and compiled HFS after the compatibility include guard was extended; final link in `39533529250` had two missing SWEET-only-guarded symbols (`ml_enable_monitor`, `sweet_sample_task`). The stub fix cleared the first in `39534235727`; patch `0084` was skipped due an under-contextualized hunk. Added include context and validated it against the downloaded XNU source. Run `39535011663` then completed successfully and produced `kernel.development.veux` (arm64 Mach-O, SHA-256 `533b24000da94d343b3a876508625a43e529cca59eb748d1ceeaabe9e5c8fcd7`). See `docs/VEUX-XNU-BUILD-39531341699.md`. The image is an XNU kernel build artifact, not an Android boot image and has not been booted or flashed.

## Agent handoff / active work (2026-10-15, latest)

### >>> UPDATE 2026-10-20 (VEUX ROM/kernel debugfs research) <<<

- Research report: `VEUX-DISPLAY-DEBUG-OPTIONS.md`. Best device-specific source candidate is Nebula Kernel r07 (VEUX/PEUX, 5.4.300, Android 11+, claims AOSP/MIUI/HyperOS compatibility), but the published VEUX QGKI defconfig has DRM and IKCONFIG_PROC without `CONFIG_DEBUG_FS`; no ready-made debug-enabled candidate was verified.
- Current Paimon 5.4.292 kernel is confirmed debugfs-off on slot A; its build repo is archived and no source revision is verified against build hash `1438fcba`. Evolution-X VEUX device tree sets `PRODUCT_SET_DEBUGFS_RESTRICTIONS := true`; switching ROMs is not a reliable fix.
- Next safe route is source/config matching then a temporary `fastboot boot` debug image with `CONFIG_DEBUG_FS=y`; no ROM or partition flash needed. This may show Android composition but may not expose early bootloader splash scanout. Keep framebuffer writes disabled.

### >>> UPDATE 2026-10-20 (Magisk A-slot root / debugfs check) <<<

- Confirmed Android initially ran from slot B (`ro.boot.slot_suffix=_b`) and had no `su` command. Rebooted to fastboot, set active slot A (`fastboot set_active a`), rebooted; verified slot A and Magisk root (`uid=0(root)`). No image was flashed or erased.
- In rooted slot A, `/proc/filesystems` does not list `debugfs`; `/proc/config.gz` has `CONFIG_DRM=y` but no `CONFIG_DEBUG_FS`. `/sys/kernel/debug` is absent. Therefore this Android kernel cannot expose DRM debugfs state; Magisk root alone cannot enable a filesystem omitted from the kernel build.
- Remaining display path: use an early SDE handoff trace or boot a purpose-built debug-enabled kernel temporarily if that is later available. Keep XNU framebuffer writes disabled.

### >>> UPDATE 2026-10-20 (Android SurfaceFlinger display dump) <<<

- User-provided Android `dumpsys SurfaceFlinger` shows panel 1080x2400 at 120 Hz. HWC/SDM reports active planes and framebuffer/client-target buffers as `RGBA_8888_UBWC`; imported 1080x2400 buffers show 4352-byte stride (1088 pixels x 4 bytes). This confirms Android currently uses UBWC-compressed buffers for display composition, not a simple linear buffer that XNU may safely write with CPU stores.
- Android has no `/sys/kernel/debug/dri` exposed, and `su` is unavailable, so no DRM atomic plane state or framebuffer physical address was obtained. SurfaceFlinger HWC/SDM output describes Android's current rendering state; it does not prove the bootloader splash buffer at `0x85200000` is the active scanout. The dump's `fourcc/mod: 875708993/0` conflicts with its `compressed: true` and UBWC labels; do not treat that field alone as a verified linear channel order.
- Next: retain display writes disabled. Need an early SDE handoff/active-register trace or a debug-enabled kernel that exposes the real active plane and address; Android `dumpsys` alone cannot establish physical base or the bootloader's splash layout.

### >>> UPDATE 2026-10-20 (VEUX live recovery + hardware source) <<<

- Read-only ADB recovery collection: live DT root identifies `Qualcomm Technologies, Inc. VEUX QRD NOPMI`, board ID `0x1000b, 0`, matching selected `dtb_1.dtb`. No reboot, flash, or partition write.
- Live display DT reserves splash memory at physical `0x85200000`, size 12 MiB, plus 1 MiB DFPS data. DRM reports 1080x2400, pitch 4352, 32 bpp/depth 24. The recovery cannot expose DRM plane FourCC (`GETFB2` EINVAL; debugfs disabled/tools absent). Panel DSI `rgb_swap_rgb` is not framebuffer memory channel order. Reference SDE source maps the reserved splash address one-to-one for handoff, but we have not proven active scanout uses it or learned its format. **Keep framebuffer writes disabled.**
- Collected hardware map: UFS `0x04804000`, ICE `0x04808000`, ICE-HWKM `0x04810000`, PHY `0x04807000`, 1 lane/SPI356; Goodix GT9896 at I2C `0x5d` / QUP SE8 with IRQ/reset/power GPIOs 22/21/51/44; DWC3 wrapper `0x04e00000` / SPI255, QUSB2 PHY `0x0162b000`, QMP combo PHY `0x01630000`; PM6125/PMK8350/PMR735A platform bindings. See `VEUX-HW-RESEARCH.md` for details and limitations.
- Read-only source checkout outside repo: `../research/kernel_xiaomi_sm6375`, community ref commit `f4b8a13a43a130a9ab83cc985ce4d4421291ae6`. DTS matches the live board, but is **not proven** to match installed Paimon recovery kernel build `1438fcba`; exact framebuffer FourCC and active scanout remain unknown. Raw DT archive is outside git and contains device identifiers.
- Next: keep display writes disabled; obtain active plane/scanout details with DRM debug or a purpose-built diagnostic, locate exact recovery source if available, then prioritize headless boot/CPU/GIC/timer/interrupt/UFS bring-up. No XNU driver port or boot attempt was made in this collection step.

### >>> UPDATE 2026-10-20 (VEUX XNU build) <<<

- First `veux-xnu-build` Actions run used macOS 14 / Xcode 15.0.1 and successfully built its staged libraries, then failed before compiling XNU: `MakeInc.kernel:22: Unsupported CURRENT_MACHINE_CONFIG VEUX`.
- Root cause: `darwin-xnu-build` skipped `0082-veux-machine-config.patch` because its `pexpert/pexpert/arm64/Makefile` hunk did not match. The patch runner warns and continues on unapplied patches, so the failure surfaced later as an unsupported config.
- Fixed the patch hunk in local commit `9bb485f` and pushed it to `59c84486t9-alt/ios-veux:veux-xnu-build`. Replaying the patch queue against xnu-8796.141.3 passes `git apply --check` for 0082 and adds `VEUX` to `SUPPORTED_ARM64_MACHINE_CONFIGS` and the VEUX machine flags. This is patch-application validation only; the kernel has not yet been compiled, booted, or flashed.
- Second Actions run `39509961630` applied the VEUX config and entered XNU compilation, then failed: `osfmk/arm64/proc_reg.h` had no VEUX cache-line case (`processor not supported`), and `pexpert/arm/pe_fiq.c` found GICv3 register macros missing from VEUX.h. The uploaded buildtree confirms the VEUX config patch was applied.
- Added a VEUX `proc_reg.h` cache-line case and the GICv3 register constants used by XNU's generic FIQ code to 0082. Replaying the patch queue against xnu-8796.141.3 applies 0082. This validates patch application only; the VEUX GIC interrupt group/timer routing remains unvalidated, and no kernel has been booted or flashed.
- Compile-profile update committed as `e2b1465` and pushed to `veux-xnu-build`. **Next:** rerun the `xnu` workflow with `macos_version=13.5`, `kernel_config=DEVELOPMENT`, `machine_config=VEUX`, and inspect the next compiler result.
- SWEET patch audit (2026-10-20): compared `ios-sweet/xnu/patches/0001`–`0081` with this fork; contents are identical after normalizing CRLF/LF. The only VEUX patch is `0082`. The bundled `job-logs.txt` is from run `39509961630`, before `e2b1465`; its XNU errors are the missing VEUX cache-line case and generic GIC register definitions that `0082` now adds. That log gives no evidence for another compile fix, so rerun CI before changing the compile profile again.
- These shared patches do not make VEUX bootable: SWEET-only guards leave VEUX without its own IODT platform expert, CPU/PSCI path, timer/GIC group and interrupt setup, and storage/display drivers. SWEET’s framebuffer path assumes its own physical buffer/layout; VEUX recovery only established DRM metadata (1080x2400, pitch 4352, 32 bpp), not physical base or pixel channel order. Keep display writes disabled until those are proven. No device partition was written.

### >>> UPDATE 2026-10-18 (read first, then the 10-17 handoff below) <<<

**STATE at end of 2026-10-18 (evening):**
- On the phone: userdata = **image v15** (`/run/media/dipa/android/ios-sweet-ipsw/ios16-root-20H392-v15.img/.simg`; = v14 + `/private/var/preferences/SystemConfiguration/preferences.plist` with one network service "USB Ethernet": Interface DeviceName ue0 Type Ethernet, IPv4 Manual 192.168.7.2/24 router 192.168.7.1, DNS 1.1.1.1 8.8.8.8, set "Automatic" as CurrentSet). Fallback image v14 (v12/v13 deleted).
- Kernels: **0078** = all 8 cores (`cpus=8`, cpu6/7 = A76, homogeneous SMP; mkadt now emits 8 CPU nodes; ADT `shim/out/sweet-0078hi.adt`); **0079** = display off/on via IOMFB selector 12 kern_RequestPowerChange(state) (fade over 6 vsyncs, then black; verified: power button gives "SWEET FB: display off/on"); **0080** = `SWEET NET: <proc> route add/delete/change ...` and `... add/delete address ...` trace (built, `shim/out/shim-boot-0080s.img`, NOT booted yet).
- **Internet over USB: not working yet.** Host side is ready (temporary iptables: FORWARD accept for 192.168.7.0/24 + MASQUERADE, comment "ios-sweet"; lost on host reboot). With v15 the phone sent no DNS and no outbound traffic (only mDNS/ARP) -> configd probably did not apply the service (or did, without default route/DNS). Next: boot 0080s on v15, watch `SWEET NET` lines (does configd add 192.168.7.2 / default route on ue0?). If configd ignores ue0 (not an IOKit IONetworkInterface; configd 1241.140.6 source in `research/configd-1241`, SCNetworkInterface createInterface needs IONetworkInterface -> controller (IOMACAddress, SelfNamed) -> bus), add IOKit stand-ins and/or rename the ifnet to en*.
- Live log listener (`nc -ukl 5140`) may still be running, writing `logs/live-0078s.txt`.

**LIVE LOG over USB (0077, boot 0077s): no more recovery round-trips.** Boot an image with `sweetusb=2`, run `tools/sweet-usbnet.sh logs/live-NAME.txt` on the PC: it waits for the phone's CDC-ECM interface, sets 192.168.7.1/24 (sudo) and prints/saves the kernel console the phone streams every 100 ms as UDP to 192.168.7.1:5140 (starts with the last 64 KiB). `ping 192.168.7.2` checks the link. Current image: `shim/out/shim-boot-0077s.img` (kernel 0077, ADT sweet-0069hi, cpus=6, sweetfb_noconsole=1, sweetfb_hz=30, sweetusb=2). The recovery pull (`tools/sweet-log-pull.sh`) is still the way after a panic/hang before USB comes up.

**🎉 USB networking works (boot 0076s, 18:24 local): `ping 192.168.7.2` from the PC answers in ~1 ms, 0 % loss (200-packet burst, 1500-byte frames, 512/1024-byte frames).** 0075: CDC-ECM function (bulk 0x81/0x01, interrupt 0x82 NETWORK_CONNECTION; host MAC 02:00:5e:77:ee:01) + kernel ethernet ifnet `ue0` (legacy output, header strip like if_fake) with 192.168.7.2/24 set from the kernel (proto_plumb + SIOCAIFADDR on an in-kernel socket). 0076: received frames into one cluster mbuf (mbuf_allocpacket gave a first mbuf of length 0 -> panic "Failed mbuf validity check: len -14"). Host side (Linux cdc_ether, interface `enp0s20f0u3u1`): `nmcli dev set IF managed no; sudo ip addr add 192.168.7.1/24 dev IF; sudo ip link set IF up`. Boot image `shim/out/shim-boot-0076s.img` (`sweetusb=2`). iOS itself does not see ue0 yet (configd needs an IONetworkInterface in IOKit).

**USB device mode works (boot 0074s, 17:45 local): the host enumerates the phone at high speed as `1209:0001 ios-sweet "Sweet iOS (USB bring-up)"`.** 0072 read-only probe: ABL leaves the USB30_PRIM GDSC and all 7 USB clocks on, DWC3 v3.20a (GSNPSID 0x5533320a) in device mode (GCTL 0x00112000), halted (DCTL RUN_STOP 0, DSTS 0x00d3de04), event buffer still at ABL's 0xfdfc8000, QUSB2 PHY alive. 0073 (`sweetusb=2`): DCTL soft reset, own event buffer (polled, interrupt masked), ep0 DEPSTARTCFG/SETEPCONFIG/SETTRANSFRESOURCE, setup TRB, RUN_STOP; control-transfer state machine as Linux ep0.c; descriptors: vendor class, no data endpoints. It ran but no event came: **0074** forces the VBUS session in the Qualcomm wrapper (QSCRATCH 0xa6f8800: HS_PHY_CTRL |= UTMI_OTG_VBUS_VALID(20)|SW_SESSVLD_SEL(28), SS_PHY_CTRL |= LANE0_PWR_PRESENT(24), as Linux dwc3_qcom_vbus_override_enable) -> connect + enumeration. Image `shim/out/shim-boot-0074s.img`. Black Phone app: main thread waits in -[VMVoicemailManager fetchAccounts] (sync XPC; voicemail needs the modem).

**Navigation works (boot 0071s on v14, log `logs/boot-0071s.txt`):** swipe up from the bottom edge returns to the home screen; app switcher works. Two fixes: **0070** pid_hibernate (syscall 435 was nosys on the macOS config -> SIGSYS killed SpringBoard in -[SBToAppsWorkspaceTransaction _didComplete] when an app left the foreground; the only CONFIG_EMBEDDED-only entry in syscalls.master); **0071** touches starting within 48 px of an edge carry kIOHIDDigitizerEventFromEdgeTip (UIKit `_UIEventHIDTouchEdgeTypeForHIDEvent` reads the digitizer EventMask 0xb0007 bits 0x800/0x1000/0x2000/0x40000). Diagnosed, not fixed: Settings (Preferences) SIGTRAP in PodcastsUI func_1cdc47c58: force-unwrap of `URL.volumeTotalCapacity` (nil on our HFS+ root). Phone/Photos/Messages show black (MobilePhone launches, no crash) - next: stack samples via boot-arg `sweetsample=MobilePhone,MobileSlideShow,MobileSMS,SpringBoard` (image `shim/out/shim-boot-0071s.img`).

**🎉🎉 MILESTONE 2026-10-18 ~15:30 local: iOS 16.7 SPRINGBOARD HOME SCREEN ON THE PHONE** (boot `shim/out/shim-boot-0069s.img` = kernel 0069 + ADT `shim/out/sweet-0069hi.adt`, image **v14**; log `logs/boot-0069s-v14-HOMESCREEN.txt`). Home screen with a few apps, Settings opens, Control Center / lock screen / notification center work, touch + buttons work, 6 A55 cores (`cpus=6`), `sweetfb_noconsole=1 sweetfb_hz=30`. Known issue: cannot leave Settings (home gesture / AssistiveTouch home do nothing) - to investigate.
What it took today (in order): 0058 HID services (Apple IOHIDFamily-1915 user client), 0059 iPhone X identity (hw.product etc.), 0060 SPMI keys + GENI touch, 0061 1125x2436 presented display, 0062 RPMh L11C touch power + IOPMPowerSource battery, 0063 GENI FIFO packing (Goodix GT9896), 0064 PRIV_WORK_INTERVAL grant (SpringBoard "Failed to create work interval"), 0065 SMP via PSCI (6 A55), 0066 crash map regions, 0067 console mute without cons_ops write, 0068 IOSurface lookup of an already-mapped surface returns base -1 (backboardd snapshot crash), 0069 UFS log flush 10 s. Image v13: CommCenter removed from launchd.plist, BKNoWatchdogs. **Image v14** = v13 + Setup skipped (`/var/mobile/Library/Preferences/com.apple.purplebuddy.plist` SetupDone/SetupFinishedAllSteps true, SetupVersion 11, daemonizeNeedsToRun false; purplebuddy.notbackedup mini-buddy flags false; managedconfiguration.notbackedup LockdownActivationIndicatesCloudConfigurationAvailable false; springboard MCForceShowCloudConfigurationUI false) + mobileactivationd data ark seeded (`/private/var/containers/Data/System/D90C94C4-F94E-4FCF-8A28-A93BE3846D8E/Library/internal/data_ark.plist`, -ActivationState Activated etc.) + MediaToolbox D22/D221/Default SubServerConfiguration StartRecorderServer=false (mediaserverd crash loop: portrait-filter prewarm called NULL GL). **Activation:** ADT /chosen certificate-production-status 0, effective-production-status-ap 0, certificate-security-mode 1, effective-security-mode-sep 1 -> mobileactivationd's native Hactivation branch (Codex `codex/activation/report.md`; alternative 4-byte daemon patch documented there). Fallback image v13; v12 deleted.

**🎉 TOUCH WORKS (boot 0063u on image v13, 2026-10-18 ~13:15 local):** tapping (i) on Setup's Hello opens the device-info sheet; swipe-up is recognised (spinner, then back to Hello - under investigation). Chain: RPMh L11C vote (0062, `bsd/dev/sweet_rpmh.c`) -> GT9896 @0x5d on GENI SE7 (0063 fixed FIFO packing: register address went out byte-swapped) -> sweet_hid_touch -> SweetHIDTouch -> backboardd. Battery icon OK (0062 SweetBattery IOPMPowerSource, static 100 %). **Image v13** (= v12 + CommCenter jobs removed from launchd.plist + `BKNoWatchdogs`=true and `FBLaunchWatchdogExceptions{com.apple.purplebuddy:100}` in /var/mobile/Library/Preferences/com.apple.springboard.plist): Setup no longer killed by the scene-create watchdog (it blocked in CoreTelephony getSubscriptionInfo -> CommCenter, Codex `codex/setup/report.md`; that report also lists how to skip Setup: SetupDone/SetupFinishedAllSteps/SetupVersion=11 in com.apple.purplebuddy.plist + activation check). v9 deleted, fallback = v12. Input latency ~1 min with 1 CPU -> Codex task 11 = SMP via PSCI (`codex/smp/`).

**INPUT WORKS (boot 0060u on a freshly flashed v12, log `logs/boot-0060u.txt`):** power, volume up, volume down reach iOS (PMIC -> sweet_keys.c -> SweetHIDButtons -> backboardd). Power locks/unlocks (screen "off" shows the kernel console because the panel never really turns off). **Device identity fixed: iPhone X** (home indicator, Face-ID-style Setup). Earlier test (0059u, `sweethidtest=15` fake Home presses) advanced Setup from Hello to the language list.
- **0058** HID: `iokit/Kernel/arm/hid/`: IOHIDEventServiceUserClient + IOHIDEventServiceQueue + IOHIDEvent compiled UNCHANGED from Apple IOHIDFamily-1915.140.3 (= exact version of the iOS 16.7 IOHIDLib, clone in `research/iohid-1915`) over our minimal IOHIDEventService (SweetHID.cpp: SweetHIDButtons consumer page 0x0C power 0x30 / vol 0xE9/0xEA / menu 0x40; SweetHIDTouch digitizer collections). C hooks `sweet_hid_key(key, down)` (0 power, 1 vol+, 2 vol-, 3 home) and `sweet_hid_touch(finger, down, x, y)`. HID logs go to IOLog. Boot-arg `sweethidtest=N` = fake Home press every N s.
- **0059** identity: hw.machine/hw.model/hw.target/hw.product from the ADT (macOS-config kernel used to answer "iPad8,6"/"Redmi Note 10 Pro"). mkadt: root compatible `D22AP|iPhone10,3|xiaomi,sweet|...`, model iPhone10,3, target-type D22, `/product` copied from the real D22AP device tree (`research/ipsw-x/d22ap.adt`, extracted from the IPSW, NOT in git), `/buttons home-button-type 2`. Codex report `codex/mg/report.md`: MG ProductType = sysctl **hw.product** (unrecognized -> iPod), HWModelStr = hw.target, HomeButtonType = `/buttons/home-button-type`; disk cache `/private/var/containers/Shared/SystemGroup/systemgroup.com.apple.mobilegestaltcache/Library/Caches/com.apple.MobileGestalt.plist` (keyed by build + UUID only -> stale iPod answers survived; reflashed clean v12 to clear it).
- **0060** drivers by Codex (`codex/input/hw-report.md`): `bsd/dev/sweet_keys.c` (SPMI arbiter v5 observer reads, PON 0x810 bits KPDPWR/RESIN SID0, PM6150L GPIO2 SID4 0xc110; works), `bsd/dev/sweet_touch.c` (GENI SE7 I2C @0xa84000, starts 45 s after boot). Touch result: SE7 fw ok (proto 3) but **0x5d and 0x38 both time out -> touch IC unpowered** (L11C LDO needs an RPMh vote). Codex task 8 = RPMh client (`codex/rpmh/`), task 7 = battery (`codex/battery/`).
- **0061** (CI 39117078444): red status bar "rdar:45025538" = UIKit "No status bar visual provider for screen" (360x800 pt is no real iPhone). AppleCLCD now presents **1125x2436** (iPhone X) and shows the centered 1080x2400; touch mapped the same; ADT canvas 1125x2436. `sweetfb_native=1` reverts.
- Images: `shim/out/shim-boot-0060b.img` (0060 + /buttons ADT `sweet-0060hi.adt`). Next: 0061 image with ADT from current mkadt.

### >>> HANDOFF 2026-10-17 late (read this first) <<<

**STATE: iOS 16.7 Setup.app "Hello" screen is ON THE PHONE** (boot `shim/out/shim-boot-0057u.img` on image v12). Photo `/run/media/dipa/android/ios-sweet-work/MILESTONE-setup-hello-2026-10-17.jpg`. SpringBoard + backboardd + Setup run; nothing crashes in the GUI path. Remaining crash/relaunch loops: installcoordinationd (should be fixed by 0057, unverified), mediaserverd (VirtualAudio removed in v12, unverified), mobileactivationd (~100/boot, not analysed), bluetoothd + fairplayd.H2 relaunch constantly (no hardware).

**What is on the phone now:** userdata = image **v12** (`/run/media/dipa/android/ios-sweet-ipsw/ios16-root-20H392-v12.img` + `.simg` + `.sha256`; v9 kept as fallback, v8/v10/v11 deleted or superseded). Kernel **0057** (`xnu/out-0057`, CI `39067532732`). ADT **`shim/out/sweet-0057hi.adt`** (QEMU twin `research/q0057-hi.adt`). Boot image **`shim/out/shim-boot-0057u.img`**. Boot args: `debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam -noprogress rd=ufsroot0 unentitled_ios_sim_launch=1 ignition_level=1 wdt_test=no_user_checkin ufsrw=1 rootrw=1 launchd_unsecure_cache=1 wdt=-1`.

**Build a phone image** (kernel K, ADT A): `python3 tools/mkpayload.py $K $A shim/out/payload-X.bin --cmdline "$B" && (cd shim && ./build.sh ../shim/out/payload-X.bin && cp out/shim-boot.img out/shim-boot-X.img)` then check `python3 tools/unpack_bootv2.py shim/out/shim-boot-X.img shim/out/check-X && cmp shim/out/check-X/ramdisk shim/out/payload-X.bin`. QEMU smoke test: `python3 tools/mkpayload.py $K research/q0057-hi.adt $S/csq/payloadX.bin --ramdisk $S/csq/root-fork.img --cmdline "debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam -noprogress rd=md0"` + `PATH=~/swift/usr/bin:$PATH python3 tools/qemu-sweet.py ... --secs 40 --kernel $K --fail-on-panic` (S = scratchpad; root-fork.img lives in the session scratchpad csq/ dir and may be gone in a new session).

**Kernel workflow:** edit `research/bt28/xnu/...` (keep the pre-edit copy in `research/preNNNN/`), syntax check `python3 tools/xnu-cc.py research/run28.log research/bt28 <file>`, make `xnu/patches/NNNN-*.patch` with `diff -u pre bt28 | sed` path rewrite, add new/changed files to `research/check-patch-order.py` list, run it (must say applied + MATCH), commit + push -> GitHub Actions `xnu` builds (~8 min) -> `gh run download <id> -R dipa-studio/ios-sweet -n xnu-kernel -D xnu/out-NNNN`. **Repo is PUBLIC since 2026-10-17** (private macOS runner minutes ran out: "recent account payments have failed"); public = free runners. Commit trailer: only `Co-Authored-By: dipa-studio <183933817+dipa-studio@users.noreply.github.com>`.

**Phone workflow (user does buttons, Claude runs commands):**
- Boot test kernel: phone in fastboot -> `fastboot boot shim/out/shim-boot-X.img`. NEVER `fastboot getvar`.
- **Read logs WITHOUT filming:** after a test the user holds Power+VolDown -> fastboot -> `fastboot boot recovery/recovery.img` (OrangeFox, temp) -> wait for `adb shell true` -> `tools/sweet-log-pull.sh /run/media/dipa/android/ios-sweet-work/logs/<name>.txt` (reads the 4 MiB console ring the kernel keeps in the last 1025 blocks of userdata; patch 0047). Then `adb reboot bootloader` brings the phone back to fastboot without the user.
- **Flash a root image:** `fastboot flash -S 512M userdata <img>.simg` (7 min, 25 chunks). After a big flash the Xiaomi ABL fastboot hangs: next `fastboot boot` stalls at "Sending" -> the USER must re-enter fastboot by hand (Power+VolDown). Do not retry commands against the hung ABL. A flash right after `adb reboot bootloader` once failed on chunk 1 (USB protocol error): just retry. User must NOT unplug during flash (once interrupted at 25/25 -> reflash).
- **Edit the phone root without reflashing (same-length only):** find the file's raw offset in the local image (it is one extent; search the image for its first 4 KiB), compare with `adb exec-out dd if=/dev/block/sda34 ...`, then `adb push` changed 4 KiB blocks and `dd of=/dev/block/sda34 seek=... conv=notrunc,fsync`, read back. Recovery kernel has no hfsplus.
- **Pull the whole phone root** (12 min): `adb exec-out "dd if=/dev/block/sda34 bs=1048576 count=16384" > img`; mount ro with udisksctl or `sudo mount -t hfsplus -o loop,ro`. To write into a pulled image: `sudo fsck.hfsplus -fy` first (volume is never cleanly unmounted -> Linux mounts ro even with -o force), then `sudo mount -t hfsplus -o loop,force`.
- Making images: copy latest img with `cp --sparse=always`, mount rw with force, change, `sync; umount`, `sha256sum`, `img2simg`. Keep only the latest image + one fallback on the SSD (/home is ~98% full; big work files live in `/run/media/dipa/android/ios-sweet-work/`, old kernels/images archived in `.../ios-sweet-work/archive/`).

**Diagnostics built into the kernel (all SWEET-only):** persistent console log (0047, boot-arg sweetlog=0 off; flush every ~1 s); `|name| text` copies of /dev/null writes for processes in `sweetnull` (default backboardd,SpringBoard; 0048); `IOK name:` IOKit lookup/open trace for `sweetiolog` (default backboardd,SpringBoard; 0049/0054, 400 lines max); `SWEET Sandbox: proc op N` (0050); `STR ...` heap text dump on SIGABRT/SIGTRAP for `sweetscan` (default backboardd,SpringBoard; 0051/0053) - this is how NSException/BSAssert reasons were found; `SMP name tN pc .. bt ..` user stack sampler for `sweetsample` (default SpringBoard,backboardd; first at 90 s then every 120 s, 40 samples, 16 frames; 0054/0055); `SWEET FB: N swaps` every 1000 swaps; `CRASH name ...` crash reports (0043/0044). Symbolicate cache addresses with `ipsw dyld a2s research/dsc/dyld_shared_cache_arm64 <addr - slide>`; main-binary addresses: addr - mh + 0x100000000.

**Patches added today (0046-0057, all CI-built):** 0046 IOSurface (IOCoreSurfaceRoot) + IOMobileFramebuffer (AppleCLCD on /arm-io/disp0) + arm-io nubs; 0047 persistent log; 0048 /dev/null tee; 0049 IOKit trace; 0050 permissive "Sandbox" MAC policy; 0051/0053 heap text on crash; 0052 RENAME_SWAP via exchangedata on HFS; 0054/0055 sampler, swap counter, AKS selectors 35 (extended device state = 17) and 101; 0056 panel copy from the vsync timer at 10 Hz (sweetfb_hz) instead of every swap; 0057 no config_ext_resolver (ACL group entries resolve without memberd). ADT (tools/mkadt.py): /arm-io/disp0, /chosen/display-scale 3, /chosen/unique-chip-id (synthetic 0x5357454554000001) + chip-id 0x8015 -> IOPlatformUUID A9683613-3704-53F2-95D0-98A8FB574E78. Image v9-v12: /private/var/containers/{Bundle,Data/System,Shared/SystemGroup,Temp}; launchd.plist StandardOut/ErrorPath renamed to ...PatX (pointing jobs at /dev/console stops them launching: EACCES); v12: LastSystemVersion=20H392 in plain /var/mobile/Library/Preferences/com.apple.migration.plist (stops the 1-hour data migration that ran every boot), VirtualAudio.plugin moved to /Library/Audio/Plug-Ins/HAL.disabled/.

**Codex helper** (`codex exec --skip-git-repo-check -m gpt-6.1-sol -c model_reasoning_effort=high -s workspace-write -C /run/media/dipa/android/ios-sweet-work/codex -o OUT "$(cat task.md)" < /dev/null`, run detached with setsid nohup; config already defaults to gpt-6.1-sol high). Reports in `/run/media/dipa/android/ios-sweet-work/codex/`: mediaserverd-report.md, installcoordinationd-report.md (-> 0057), ufs-performance.md (ranked UFS speed plan), **ufs/0058-sweet-ufs-faster.patch** (READY, not yet applied: ufslogsecs default 10 s log flush batching, optional ufscache=1 directional cache ops, optional ufswait=1 spin-then-sleep; syntax-checked, host-stub verified; see ufs/README.md). Apply it as patch 0058 after review.

**Claude safety-classifier note:** several messages about QuartzCore renderer selection / writing an HFS reader tool were cut off by an automatic classifier (false positives, user agrees). Keep those topics short or let them be; they are not blockers now (rendering already works).

**NEXT STEPS (in order):**
1. **Input** (Setup stuck on Hello): touch + power + volume as IOHIDEventService/IOHIDDevice services backboardd matches (log shows backboardd matching IOHIDDevice with DeviceUsagePairs and IOService with HIDServiceSupport=true). Phone hardware: Goodix/Focaltech touch over I2C/SPI (check live DT `dtb/`), buttons via PMIC (pon) and GPIO keys. Start with a fake HID service (e.g. power button via a timer or boot-arg) to learn the ABI, then real drivers.
2. **Device identity**: MobileGestalt reports iPod + Home button. Add /product node / product-type (iPhone10,3, D22AP), device class iPhone, home-button-less (Face ID) properties in mkadt; find exact MG keys (MGIOMFBSupport.c, `IODeviceTree:/product` lookups seen in backboardd trace).
3. **Battery**: AppleSmartBattery/IOPMPowerSource style service (status bar shows empty red battery).
4. Apply Codex 0058 (UFS speed), consider cpus>1, check whether installcoordinationd/mediaserverd loops are gone, analyse mobileactivationd.
5. Hide kernel console over the GUI when not debugging: boot-arg sweetfb_noconsole=1 (but then panics are not on screen).

- **🎉 MILESTONE: iOS GUI ON THE PHONE - Setup.app "Hello" screen (2026-10-17 ~21:30 UTC, boot 0057u on image v12).** Photo: `/run/media/dipa/android/ios-sweet-work/MILESTONE-setup-hello-2026-10-17.jpg` (animated "dobar d(an)" hello lettering, status bar "iPod" + battery icon, bottom "Pritisnite Home za otvaranje" = "Press Home to open" (locale hr), (i) button). Rendered by iOS 16.7 SpringBoard/Setup through CoreAnimation -> backboardd -> kernel IOSurface (IOCoreSurfaceRoot) -> kernel AppleCLCD swaps -> ABL panel memory. What made it: data migration finally skipped (v12: `LastSystemVersion` 20H392 in the plain `/var/mobile/Library/Preferences/com.apple.migration.plist`; ADT `/chosen/unique-chip-id` + `chip-id` for IOPlatformUUID), 0057 (no ext resolver -> ACL containers work), plus everything before (0046 display/IOSurface, 0050 Sandbox policy, display-scale 3, containers dirs, RENAME_SWAP, AKS 35/101, 10 Hz present).
  **Missing (next work, in rough order):**
  - **Input: no touch, no power button, no volume buttons** (no HID drivers; backboardd looks for IOHIDDevice / HIDServiceSupport services). Setup is stuck on "Hello".
  - **Device identity: it thinks it is an iPod with a Home button** (status bar "iPod", "Press Home to open"): MobileGestalt has no product/model identity (no /product node, product-type, etc.) - give it iPhone10,3 / home-button-less (Face ID class) identity.
  - **No battery detection** (no battery/charger/PMIC service; status bar battery shows empty/red).
  - Locale came up Croatian (hr) - harmless.
  - Performance: cpus=1, polled UFS (Codex UFS patch in progress: `codex/ufs/`), backboardd presents at 60 Hz.
- **README refreshed (2026-10-17):** read the full notes and updated the public overview through patch 0045, v7 hardware observations and prepared v8 diagnostics. Documents real Apple userspace, the missing display/IOSurface GUI work, limited security services, highmem, persistent userdata root, current tooling and build examples. Documentation only; no kernel build, tests, flashing or phone boot performed.

- **v11 still migrated (boot 0056u, 20:32 UTC, `logs/boot-0056u-v11.txt`).** On iOS kCFPreferencesCurrentHost lands in the plain plist: all DMEnvironment setters (setLastBuildVersionPref, setUserDataDispositionPref, ...) use CurrentHost and the phone's `/var/mobile/Library/Preferences/com.apple.migration.plist` holds DMUserDataDisposition; datamigrator's XPC service runs with `_RoleAccount: mobile`. **Image v12** = v11 + `LastSystemVersion` = 20H392 added to that plain `com.apple.migration.plist` (keeps DMUserDataDisposition, 501:501 0600) + `/Library/Audio/Plug-Ins/HAL/VirtualAudio.plugin` moved to `/Library/Audio/Plug-Ins/HAL.disabled/` (Codex: stops the mediaserverd SIGSEGV loop; untested). **installcoordinationd loop explained (Codex `codex/installcoordinationd-report.md`):** os_crash "Failed to create data directory" EACCES for `/private/var/containers/Shared/SystemGroup/systemgroup.com.apple.installcoordinationd/Library/InstallCoordination`: `Library`/`Library/Caches` in the container are ACL-only (uid/gid 0xfffffffe, mode 0000, ACE for group GUID ...012B = gid 299 systemusers); with `config_ext_resolver` the kernel asks an identity resolver (memberd/opendirectoryd) that iOS does not run -> EWOULDBLOCK -> ACE skipped -> EACCES. **Patch 0057**: drop config_ext_resolver from FILESYS_BASE (compatibility UID/GID<->GUID mapping is used instead), likely fixes other ACL-protected containers too. Codex task 3: UFS driver performance design (`codex/ufs-performance.md`).
- **mediaserverd SIGSEGV loop explained (Codex report `/run/media/dipa/android/ios-sweet-work/codex/mediaserverd-report.md`):** the fault (FAR 0x390) is in the HAL plug-in `/Library/Audio/Plug-Ins/HAL/VirtualAudio.plugin/VirtualAudio` (ApplyBeamFormerPreference <- VirtualAudio_PlugIn::SetPropertyData <- HALS_AHPPlugIn::ObjectSetPropertyData <- AudioObjectSetPropertyData <- MediaExperience vaemVADSerializationListener): the default virtual audio device ('vdef', VirtualAudioDevice_Default) does not exist (no audio hardware/driver, no /product/audio). Proposed workaround for GUI bring-up: move VirtualAudio.plugin out of /Library/Audio/Plug-Ins/HAL/ in the next root image (untested). v11 reflashed OK after an interrupted flash (USB unplugged at chunk 25/25). Codex task 2: installcoordinationd crash loop.
- **ROOT CAUSE of the endless migration: no IOPlatformUUID (2026-10-17).** datamigrator's `-[DMMigrator isMigrationNeededWithBuildVersion:lastBuildVersion:clientPID:]` gets lastBuildVersion from `-[DMEnvironment lastBuildVersionPref]` = `CFPreferencesCopyValue("LastSystemVersion", "com.apple.migration", kCFPreferencesCurrentUser, kCFPreferencesCurrentHost)` -> a ByHost file. The phone had `/var/mobile/Library/Preferences/com.apple.migration.plist` (only DMUserDataDisposition) and NO `Preferences/ByHost` directory at all. On arm XNU publishes IOPlatformUUID (gethostuuid) only from `/chosen/unique-chip-id` (8 bytes) + `/chosen/chip-id` (4 bytes) (IOPlatformExpertDevice::generatePlatformUUID, called from IOPlatformExpert::start); the SWEET ADT had neither, so every CurrentHost preference write failed. Fix: mkadt adds `unique-chip-id` = 0x5357454554000001 (synthetic) and `chip-id` = 0x8015 -> UUID `A9683613-3704-53F2-95D0-98A8FB574E78` (same SHA1 namespace computation as the kernel). ADT `shim/out/sweet-0057hi.adt`, boot image `shim/out/shim-boot-0056u.img` (0056 kernel + 0057hi ADT, QEMU OK). **Image v11** = v10 + `Preferences/ByHost/com.apple.migration.<UUID upper and lower>.plist` {LastSystemVersion: 20H392} (501:501, dir 0755 files 0600). Flashing v11 2026-10-17 ~20:10 UTC. Codex (gpt-6.1-sol high) analysing the mediaserverd SIGSEGV loop in `/run/media/dipa/android/ios-sweet-work/codex/` (report `mediaserverd-report.md`).
- **v10 did NOT stop the migration (boot 0056n on v10, 19:18 UTC, `logs/boot-0056n-v10.txt`):** datamigrator + migrationpluginwrapper ran again, backboardd drew the progress UI (13000+ swaps in ~5 min). So `com.apple.DataMigration.plist`/LastSystemVersion is not the deciding input. What is known about the decision (datamigrator XPC service `DataMigration.framework/XPCServices/com.apple.datamigrator.xpc/com.apple.datamigrator`, strings): `Migration sentinel present. Migration necessary.` (sentinel `/private/var/datamigrator/migrate`, created and removed by datamigrator itself; absent in v10), `System build version changed from %@ to %@. Migration necessary.` / `...unchanged... not necessary`, `Disposition dictionary with build version %@ is out of date relative to current build version %@`, `SyntheticDidUpgrade`, DMUserDataDispositionManager; previous build source not found yet (not in the binary's plain strings; likely in DataMigration.framework's DMUserDataDispositionManager / preferences domain `com.apple.migration`). backboardd calls `DMPerformMigrationIfNeeded` and holds SpringBoard in `checkInAndWaitForDataMigration` until it returns. NEXT: find where the previous build version / disposition dictionary is stored (disassemble DataMigration.framework DMUserDataDispositionManager + datamigrator's isMigrationNeeded path), write it into the image; or get datamigrator's os_log out (OS_ACTIVITY_DT_MODE needs a launchd env change).
- **Data migration never records completion -> skip it (image v10, 2026-10-17).** Boot 0056n (18:16 UTC, `logs/boot-0056n.txt`, 30 min): 10 Hz panel copies, backboardd still presents at ~60 Hz (107k swaps), SpringBoard still in `BKSSystemShellService _checkIn` at sample 14. Every migration run takes 1+ hour on cpus=1 and repeats each boot. DataMigration decides from `/var/mobile/Library/Preferences/com.apple.DataMigration.plist` key `LastSystemVersion` (vs ProductBuildVersion 20H392); the pulled phone root (21:01 local) had NO such file. **v10** = that pulled phone state + fsck.hfsplus -fy (volume was marked not cleanly unmounted -> Linux mounts it read-only even with -o force; fsck found only hard-link counts + minor volume header, repaired) + `com.apple.DataMigration.plist` {LastSystemVersion: 20H392} (501:501 0600). `/run/media/dipa/android/ios-sweet-ipsw/ios16-root-20H392-v10.img` (+ .sha256, .simg); v8 files deleted, v9 kept as fallback.
- **Repo made PUBLIC (2026-10-17, user request) so GitHub-hosted macOS runners are free:** the 0056 CI run was refused ("recent account payments have failed or your spending limit needs to be increased"). Checked before: no device dumps, serials, IMEI or Apple binaries in the history (.gitignore keeps backup/, dtb/, recovery/, research/ out); commit author emails are public now. 0056 rerun `39056660104` passed -> `xnu/out-0056`, QEMU OK, image `shim/out/shim-boot-0056n.img` booted 18:16 UTC.
- **Boot 0055n (17:16 UTC, ~65 min, `logs/boot-0055n.txt`): migration bar reached 99% in ~30 min (was ~60), then crawled.** Root cause of the slowness: backboardd presents the progress UI at ~58 Hz (**167,000 swaps in ~48 min**) and AppleCLCD copied the full 10 MB frame into the panel on every swap -> ~600 MB/s memcpy on the single CPU (cpus=1), starving everything (polled UFS I/O too). Sampler (16 frames): **SpringBoard waits in `-[BKSSystemShellService _checkIn]`** (synchronous BSXPC call to backboardd, from FBSystemShellInitialize <- SBSystemAppMain) - backboardd holds the system shell check-in until the data migration ends, so the migration is the gate to SpringBoard UI. **Patch 0056**: swap only records the latest swap record; the vsync timer copies it to the panel every 60/sweetfb_hz ticks (default 10 Hz); `SWEET FB: N swaps` every 1000.
- **Boot 0054n (16:53 UTC, ~12 min, `logs/boot-0054n.txt`, patch 0054 sampler):** the data migration runs AGAIN on every boot (it completed once in the 0053s run) - completion is not being recorded. backboardd keeps swapping the progress UI (3700+ swaps in ~10 min, `SWEET FB: N swaps`). Sample during migration: SpringBoard main thread blocked in a synchronous XPC call (`mach_msg2_trap <- dispatch_mach_send_and_wait_for_reply <- xpc_connection_send_message_with_reply_sync <- -[BSXPCServiceConnectionMessage _sendSynchronously:] <- BSXPCServiceConnectionProxy ...`). Unsupported AKS selectors seen: 101 `aks_assert_consume`, 93 `aks_get_internal_info`, 34 `_aks_stash_load` (datamigrator), **35 `aks_get_extended_device_state`** (SpringBoard, chronod, remindd, searchd, symptomsd...). **Patch 0055**: AKS 35 answered like 17 (same DER device state), 101 succeeds; sampler backtraces 16 frames, 40 samples (~80 min).
- **MILESTONE: FIRST iOS PIXELS ON THE PANEL (boot 0053s long run, 15:33 UTC, ~60 min; photos IMG_20261017_183029/183222/183419; log `/run/media/dipa/android/ios-sweet-work/logs/boot-0053s-long.txt`, 407 KB, 1428 flushes).** The iOS data-migration boot screen (Apple logo + progress bar) was shown and the bar advanced to full in ~60 minutes. It is drawn by **backboardd through our kernel display path**: `SWEET SURF: backboardd create id 2/3 1080x2400 fmt 0x42475241 (BGRA) bpe 4 bpr 4352 size 10452992 keys 11`, IOSurface sels 9, 27, 5, 34 and traps 2/3 (lock/unlock), IOMFB SwapBegin (4) / SwapEnd (5, 1132-byte struct) / GetLayerDefaultSurface (3) / 68 / 55, then `SWEET FB: swap N layer 0 surface 2|3 1080x2400 ... a 0,0 1080x2400 b 0,0 1080x2400` alternating (double buffering; only the first 16 swaps are logged). Triggered by `com.apple.datamigrator` (AKS sels 101/93/34 return unsupported) and `com.apple.migrationpluginwrapper`. Probably ProgressUI-style CoreGraphics drawing into IOSurfaces (no GPU used). After the migration: SpringBoard and backboardd stay up (exec once each, no crash), nothing new drawn; crash loops only for mediaserverd, installcoordinationd, mobileactivationd (~108 each in the hour); bluetoothd and fairplayd.H2 relaunch constantly (no hardware). Kernel console text overlays the image (sweetfb_noconsole=1 would hide it).
- **MILESTONE: SpringBoard and backboardd both stay up (boot 0053s on v9, 15:29 UTC, `logs/boot-0053s.txt`).** With /chosen/display-scale = 3: `exec SpringBoard` once, `exec backboardd` once, no CRASH for either; MobileGestaltHelper reads IOMFB size/dot pitch; backboardd opens AppleCLCD (sels 57,15,22,29,33,79,74 as before). No IOSurface creates and no swaps: backboardd keeps polling `IOProviderClass IOAcceleratorES` (-> 0 found) and AGXAccelerator/IOAcceleratorESLegacy - no GPU, so no CoreAnimation renderer yet. Log goes quiet after ~47 s (only 47 flushes): the system idles. NEXT WALL: CoreAnimation rendering without a GPU (CPU path) so the window server produces frames.
- **SpringBoard's invalid mode = scale 0 (boot 0053n, 15:19 UTC, `logs/boot-0053n.txt`, heap scan):** `FBSDisplayMode cannot be configured as requested : <FBSDisplayMode: ...; infxinf@0x (1080x2400/0) 60Hz sRGB SDR>` - pixel size and 60 Hz are fine, scale is 0. libMobileGestalt (MGIOMFBSupport.c, sub_19c560a54) reads `display-scale` (u32, default 0) and `display-rotation` from **IODeviceTree:/chosen**, pixel size via IOMobileFramebufferGetDisplaySize (MobileGestaltHelper sel 8/28 in the log). mkadt now adds `/chosen/display-scale` = 3 (1080x2400 @3x = 360x800 pt). ADT `shim/out/sweet-0054hi.adt` (QEMU `research/q0054-hi.adt`), image `shim/out/shim-boot-0053s.img` = 0053 kernel + 0054hi ADT. Possible catch: MobileGestalt may have cached scale 0 in `/private/var/containers/Shared/SystemGroup/systemgroup.com.apple.mobilegestaltcache/...`.
- **MILESTONE: backboardd survives and opens the display (boot 0052n on v9, 15:07 UTC, `logs/boot-0052n.txt`).** No `CRASH backboardd`. It walks `IODeviceTree:/arm-io` children, matches IOMobileFramebuffer, `open AppleCLCD type 0 -> 0x0`, calls IOMFB selectors 57, 15, 22, 29, 33, 79 (GetBlock, out 1580/40), 74 (SupportedFrameInfo), 12, 6, 27, 17, 84, 50; opens IOCoreSurfaceRoot (sel 13); looks for AGXAccelerator / IOAcceleratorES / IOAcceleratorESLegacy (none, repeatedly), `IODeviceTree:/product` (none, repeatedly), `/buttons`, aop-smart-cover, IOPMrootDomain. No swaps yet. **SpringBoard now gets past display discovery** and dies (sig 5) in `-[FBSDisplayMode _initWithWidth:height:preferredScale:scaleOverride:refreshRate:gamut:hdr:rotation:virtual:validityCheck:]+580` <- `_initWithCADisplayMode:scale:rotation:` <- `FBSDisplayConfiguration _initWithImmutableDisplay:` <- `FBSDisplaySource initWithDisplay:` <- `FBSDisplayMonitor` (slide 0x14504000): "FBSDisplayMode cannot be configured as requested". Checks: width/height >= 2, preferredScale > 0, scaleOverride >= 0, refreshRate non-zero, valid gamut/HDR/rotation. Suspects: refresh rate 0 (IOMFB timing blocks answered with zeros) and/or scale 0 (MobileGestalt main-screen-scale; no /product node in the ADT). **Patch 0053**: heap text scan also on SIGTRAP and for SpringBoard (default sweetscan list backboardd,SpringBoard) to read the exact mode description.
- **Image v9 (2026-10-17) = v8 + `/private/var/containers/{Bundle,Data/System,Shared/SystemGroup,Temp}` (root:wheel 0755; on iOS these live on the data volume, absent from the rootfs) + launchd.plist with StandardOutPath/StandardErrorPath renamed to ...PatX (the in-place phone fix; daemons' stdout reaches the log via the 0048 /dev/null tee).** `/run/media/dipa/android/ios-sweet-ipsw/ios16-root-20H392-v9.img` SHA256 aa9f9139...6e67, `.simg` 12,145,303,864 bytes; written through `sudo mount -t hfsplus -o loop,force`. **Patch 0052** (`xnu/patches/0052-sweet-hfs-rename-swap.patch`, CI `39042761826` -> `xnu/out-0052`, QEMU OK, image `shim/out/shim-boot-0052n.img`): vn_rename falls back to VNOP_EXCHANGE when VNOP_RENAMEX(RENAME_SWAP) returns ENOTSUP for two regular files on one volume (HFS exchange swaps data and cnode descriptors = swap semantics). Flashing v9 started 2026-10-17 ~15:00 UTC.
- **backboardd EXCEPTION FOUND (boot 0051n, 14:41 UTC, `logs/boot-0051n.txt`, patch 0051 heap scan):** `*** Terminating app due to uncaught exception 'NSInvalidArgumentException', reason: '*** -[NSURL initFileURLWithPath:]: nil string parameter'`. First-throw stack (slide 0x337f0000): `+[NSURL fileURLWithPath:]` <- `-[BSSystemContainerForCurrentProcessPathProvider libraryPath]` <- `cachesPath` <- backboardd main+0x1d858 (StartWindowServer, shader cache path). BaseBoard: libraryPath = `BSSystemSharedResourcesDirectoryForIdentifier` = `BSSystemSharedDirectoryForIdentifier(id)` + "/Library"; that calls `container_system_path_for_identifier` (libsystem_containermanager -> `_container_legacy_lookup` -> containermanagerd XPC), which returned NULL (BaseBoard logs "Error getting shared system container ..."). With 0050 the sandbox denials are gone. containermanagerd.log.0 in the pulled (pre-0050) image: "Did not receive any persona attributes", "Expected to find at least one persona", notify_register_dispatch failed 9; `/private/var/containers` does NOT exist in the root image (on iOS it lives on the data volume). usermanagerd does create kernel personas 99/199/1000, but fails to save `/private/var/keybags/usersession.kb` and `persona.kb`: "Failed to atomically swap writing file: Operation not supported (45)" (HFS has no RENAME_SWAP). NEXT: create `/private/var/containers` (and check what containermanagerd needs for system group containers), fix or emulate RENAME_SWAP on HFS, then re-check backboardd.
- **Disk housekeeping (2026-10-17):** /home was at 4 GiB free. Moved (not deleted) `xnu/out-0010..0044` and old `shim/out/*.img`/`payload-*.bin` (everything before 0046) to `/run/media/dipa/android/ios-sweet-work/archive/{xnu,shim-out}` (6.3 GiB); /home now 8.7 GiB free. Large work files (phone-root.img 16 GiB, logs, tracev3 dumps) live in `/run/media/dipa/android/ios-sweet-work/`. **Patch 0051** (`xnu/patches/0051-sweet-crash-heap-strings.patch`, CI `39041440935`): on SIGABRT of a process in boot-arg `sweetscan` (default backboardd) the crash log prints heap text runs as `STR ...` (to find the NSException reason). Boot 0051n 14:41 UTC.
- **Boot 0049n (14:11 UTC, `logs/boot-0049n.txt`, patch 0049 trace): backboardd's IOKit lookups before it dies** (each run): `IODeviceTree:/arm-io/pearl-sep` -> none, matching ApplePearlSEPDriver -> none, `IOService:/IOResources/AppleKeyStore` open OK, matching IOHIDDevice (DeviceUsagePairs) / `HIDServiceSupport` notifications, `usb-drd,t8027` notification; **never any IOMobileFramebuffer / display lookup** - the exception happens before display detection. launchd (tracev3) shows backboardd's mach lookups denied with `error = 159: Sandbox restriction`: com.apple.mobilegestalt.xpc, com.apple.iohideventsystem, com.apple.system.notification_center, com.apple.logd, containermanagerd, ACCHWComponentAuthService, oscard. libsystem_sandbox uses `__mac_syscall("Sandbox", op, arg)` (ops: 1 init, 2 check, 3 note, 4 container path, 5/6/7/8 extensions, 0x15 check_bulk, ...); with no policy named "Sandbox" every call gets ENOPOLICY. **Patch 0050** (`xnu/patches/0050-sweet-sandbox-policy.patch`): built-in permissive MAC policy "Sandbox" in sweet_amfi.c (mpo_policy_syscall returns 0, container/extension ops ENOENT; logs first use of each op as `SWEET Sandbox: proc op N`).
- **Phone root pulled (16 GiB, 12 min, `adb exec-out dd if=/dev/block/sda34`) to `/run/media/dipa/android/ios-sweet-work/phone-root.img` (loop-mounted ro at /run/media/dipa/iOSRoot).** No .ips crash reports. logd tracev3 (Persist, LZ4 `bv41` blocks, decompressed strings in `ios-sweet-work/tracev3/all.txt`): /private/var/db/uuidtext is EMPTY so only launchd's own messages are readable. Findings: v8 launch failure = `Service could not initialize: posix_spawn(/usr/libexec/backboardd), error 0xd - Permission denied` (xpcproxy exit 78) - /dev/console not openable for the mobile user; backboardd[98] spawned `com.apple.MTLCompilerService` before SIGABRT; **launchd denies many mach lookups with `error = 159: Sandbox restriction`** (mediaserverd -> com.apple.backboard.display.services, remoted, mobiletimerd -> sleepd, identityservicesd -> apsd) and **tccd exits OS_REASON_SANDBOX "profile not found"** - no Sandbox kext/profiles on SWEET; likely cause of many daemon crash loops (next wall after the display). CF's uncaught-exception text never reaches stderr for daemons (no CF handler; libc++abi prints only the type). **Patch 0049** (`xnu/patches/0049-sweet-iokit-trace.patch`): `IOK name: ...` console lines for registry path lookups, child iterators, matching (with result count/class), matching notifications and IOServiceOpen of the processes in boot-arg `sweetiolog` (default backboardd), max 400 lines.
- **CONFIRMED: launchd StandardOut/ErrorPath=/dev/console stops backboardd from launching.** After the in-place rename (boot 0047n-b, log `logs/boot-0047n-b.txt`) backboardd launches again and dies as on v7: sig 6, `___pthread_kill <- abort <- demangling_terminate_handler <- _objc_terminate <- std::terminate <- _dispatch_client_callout <- _dispatch_once_callout <- main+0x9334` (window-server dispatch_once). It never opened AppleCLCD or IOCoreSurfaceRoot (no `SWEET FB/SURF: backboardd` lines) -> throws before/at display detection. **Patch 0048** (`xnu/patches/0048-sweet-devnull-tee.patch`, CI `39037749668` -> `xnu/out-0048`, image `shim/out/shim-boot-0048n.img`): writes to /dev/null by processes named in boot-arg `sweetnull` (default `backboardd,SpringBoard`) are printed as `|name| text`. Boot 0048n (13:48 UTC, log `logs/boot-0048n.txt`): only `|backboardd| libc++abi: terminating due to uncaught exception of type NSException` (CF's reason line goes to os_log, not stderr, despite CFLOG_FORCE_STDERR/OS_ACTIVITY_DT_MODE). Next: pull the whole 16 GiB root from recovery (`adb exec-out dd if=/dev/block/sda34`) to `/run/media/dipa/android/ios-sweet-work/phone-root.img` and read ReportCrash .ips files / logd tracev3 for the exception reason.
- **Persistent log WORKS (boot 0047n on v8, 13:31 UTC; pulled from OrangeFox: 70 KB, 111 flushes, `/run/media/dipa/android/ios-sweet-work/logs/boot-0047n.txt`).** In 3 min **backboardd was never exec'd** (v7 ran it), ~70 bare `exec xpcproxy`, SpringBoard loops on FBSDisplayMonitor (no display), mediaserverd sig 11 loop, locationd, lockdownd sig 5. Suspect the v8 plist (StandardOut/ErrorPath=/dev/console on backboardd). **In-place plist edit from recovery (no reflash):** launchd.plist is one extent at image/partition byte offset 0x1e025f000 (195 blocks; verified bytes identical on phone vs local v8 mount); renamed StandardOutPath->StandardOutPatX and StandardErrorPath->StandardErrorPatX (same length, both jobs) in blocks 68 and 105 via `adb push` + `dd of=/dev/block/sda34 seek=... conv=notrunc,fsync`, read back VERIFIED. Phone now differs from local v8 image in those 2 blocks (files in `/run/media/dipa/android/ios-sweet-work/`). Test boot 0047n 13:38:42 UTC. Recovery kernel has no hfsplus (raw block edits only).
- **Patch 0047: persistent console log (CI `39036478663` -> `xnu/out-0047`, QEMU no panic; phone image `shim/out/shim-boot-0047n.img` = 0047 + sweet-0046hi.adt + 0045n cmdline).** `_cnputs` (all console output: kernel printf + daemons' /dev/console) also appends to a 4 MiB ring in sweet_ufs.c; after the UFS partition is ready and writable (ufsrw=1) a thread writes new ring blocks + header to the LAST 1025 blocks (4 KiB) of userdata every ~1 s and SYNCHRONIZE CACHE (prints `SWEET LOG: console log to the last 4100 KiB ...`). Read: phone to fastboot -> `fastboot boot recovery/recovery.img` (OrangeFox) -> `tools/sweet-log-pull.sh OUT.txt` (adb dd of that area + `tools/sweet-log.py`). Not yet verified on the phone. Panics after the last flush are not in it (screen still shows them). 2x font attempt reverted: XNU's v_scale only scales the progress icon.
- **Boot 0046n on v8 (13:05 UTC, VID_20261017_150522_HSR_120):** phone prints `SWEET SURF: IOCoreSurfaceRoot registered` and `SWEET FB: AppleCLCD 1080x2400 stride 4320 at 0x9c000000, default surface 1` (nubs + match work on hardware). Visible userspace: early boot tasks, launchd_cache_loader, `exec SpringBoard`; no `exec backboardd` / `SWEET FB: backboardd` line seen in the readable frames (video blurry). Frame 00:47: lower half of the screen shows OLDER console text (16:01:12) below newer lines -> unconfirmed hint that a swap copied an old snapshot of the panel (CA reads the default/displayed surface = panel memory). SpringBoard still dies in `-[FBSDisplayMonitor _initWithBookendObserver:transformer:]+1160` (sig 5, slide 0x30960000). **Shim: 2x console font** (`shim/loader.c` Video.v_depth scale field = 1) so phone videos are readable; image `shim/out/shim-boot-0046b.img` = 0046n + 2x font.
- **Patch 0046: built-in IOSurface + IOMobileFramebuffer (2026-10-17, offline, NOT phone-tested).** `xnu/patches/0046-sweet-iosurface-iomfb.patch`: new `iokit/Kernel/arm/SweetSurface.{h,cpp}` (IOCoreSurfaceRoot + IOSurfaceRootUserClient: sel 13/0/4/34/35, traps 0-5, wired buffers mapped into the caller, per-client refs) and `SweetFramebuffer.cpp` (AppleCLCD : IOMobileFramebuffer on /arm-io/disp0: sizes, swap = CPU copy of enabled layers into the ABL panel memory, 60 Hz vsync via sendAsyncResult64WithOptions(CanDrop), panel memory published as the default IOSurface, kernel text console paused on the first swap only with `sweetfb_noconsole=1` (default keeps the console: pausing switches it to serial and would hide panics)); SweetPlatformExpert creates nubs for /arm-io children (not gic) attached to the platform expert (IOPlatformDevice::compareName casts its provider to IOPlatformExpert, so nubs under the arm-io nub never matched - first CI build showed that in QEMU). mkadt: /arm-io/disp0 {device_type display-subsystem, compatible sweet,display, canvas-width 1080, canvas-height 2400}. CI `39021572169` -> `xnu/out-0046`. **QEMU** (`research/q0046-hi.adt`, RAM disk init, msgbuf): `SWEET SURF: IOCoreSurfaceRoot registered`, `SWEET FB: AppleCLCD 1080x2400 stride 4320 at 0x9c000000, default surface 1`, init alive, no panic. Phone image **`shim/out/shim-boot-0046n.img`** (SHA256 9c4d2fe9..., CI `39024108588` with the review fixes: swap bounds check, zeroed 64-bit async ref, port release, 1.5 GiB wired budget, ref leak/race fixes; QEMU re-checked) = 0046 kernel + `shim/out/sweet-0046hi.adt` + the 0045n cmdline; boot it on image v8 (backboardd/SpringBoard log to console) and film. Expected new console lines: `SWEET SURF: <proc> create id ...`, `SWEET FB: backboardd sel N ...`, `SWEET FB: swap ...`. Open question for the next wall: QuartzCore's IOMFB server builds its renderer from Metal first (`CAMetalContextCreate`), GLES only when enabled; how the CPU renderer gets selected on a device without a GPU is not yet established.
- **IOSurface values ABI (offline RE, `/run/media/dipa/android/ios-sweet-work/iosurface-values.md`) - TODO in SweetSurface (0046 only accepts and drops values, so IOSurfaceCopyValue always returns NULL):** sel 9 SetValue in = {u32 id, u32 pad, IOCFSerialize([value, key]) or ([dict] = merge)}, sel 0xb RemoveValue in = {u32 id, u32 pad, key\0} (empty key = remove all); both out 4 bytes = new generation, client accepts only (gen+2)|1. Kernel after each change: gen = (gen+2)|1 (odd, never 0) -> state+0x20, serialized size (>=1) -> state+0x28. sel 0xa in {u32 id, u32 0, u8 0}, out {u32 ?, u32 gen, serialized non-bulk dict}; too small -> 0xe00002db + needed size (client retries x16). sel 0x1b in 0x88: bulk struct 0x70 @0, u64 valid size @0x70, u64 changed mask @0x78, u32 id @0x80 -> copy masked fields into state+0x30 (bit0 32B @0, bit1 16B @0x20, bit2 8B @0x30, bits3-10 1B @0x38..0x3f, bits11-14 24B @0x40/4B @0x58/8B @0x5c/1B @0x64).
- **IOMFB display matching confirmed (offline RE, `/run/media/dipa/android/ios-sweet-work/iomfb-match.md`):** the framework never matches on "AppleCLCD"; any registered IOMobileFramebuffer subclass works. `iomfb_match_callback` reads only `dfr`/`AppleTV`/`external` (CFBoolean, service itself, no parents); internal main display = all absent/false (type 0, name "primary"). Display count = /arm-io children whose device_type starts with "display-subsystem" (count 0 -> CreateDisplayList returns NULL; more nodes than services -> 30 s wait). IOMobileFramebufferOpen fails only on IOServiceOpen failure; canvas-width/height read as 4-byte CFData from the IOService-plane parent (optional). CopyProperty = IORegistryEntrySearchCFProperty on the service only. Patch 0046 (disp0 node, `external`=false, AppleCLCD : IOMobileFramebuffer) fits all of this.
- **IOMobileFramebuffer swap + notification ABI (2026-10-17, offline).** Swap record = fb+0x18, **0x46c bytes**, zeroed by SwapBegin and sent whole by `kern_SwapEnd` = IOConnectCallStructMethod(sel 5, rec, 0x46c, no output). **SwapBegin** = sel 4, no input, 1 scalar out = swap id (stored at rec+0x50). `kern_SwapSetLayer(fb, layer<4, IOSurfaceRef, CGRect a, CGRect b, flags)`: rec+0x54+4*layer = **IOSurface id**; rec+0x104 bit layer = layer enabled (rec+0x108 bit cleared); rect a (int x,y,w,h, scaled) at rec+0x64+16*layer, rect b at rec+0xc4+16*layer; rec+0x114+4*layer = transform from flags&0xf; flag bits 5/31/6/7/8/9 set bytes rec+0x2ca/0x2cc/0x2e3/0x2e5/0x2e6/0x467+layer. A NULL surface only sets the enable bit with zero id. SwapWait = sel 6 scalars [swap id, timeout, 0].
  - **Notifications**: `IOMobileFramebufferScheduleWithDispatchQueue`/`GetRunLoopSource` create an IONotificationPort and `IOConnectSetNotificationPort(conn, type, port, 0)` (kernel `registerNotificationPort`). `kern_EnableNotifications(fb, type, cb, ctx)` = **sel 72 scalars [NotifyCallbackFuncs[type], fb, type, 0]** -> the kernel keeps an async reference {port, func, refcon=fb} per type and fires it with `sendAsyncResult64`. Types: 0 HotPlug, 1 Power, 3 FrameInfo (args[0] = mask of 31-bit keys, args[1] u32, then values), 4 CRC, **5 Vsync**: 6 args, each a 32-bit half in a u64 slot: (ts lo, ts hi), (t2 lo, hi) passed through the time-ingest helper, (t3 lo, hi); the framework then calls the client's vsync callback(fb, ts, t2', t3, ctx). Vsync callbacks are dropped while the notification port has queued messages.

- **IOSurface.framework user-client ABI reversed (2026-10-17, offline, step 2 of the GUI plan).** `ipsw dyld disass research/dsc/dyld_shared_cache_arm64 --image IOSurface` (selector scan script: scratchpad `selscan.py`).
  - Connect (`_iosConnectInitalize`, pthread_once): `IOServiceGetMatchingService(IOServiceNameMatching("IOCoreSurfaceRoot"))`, retried with sleep(1) up to 241 times (a missing service stalls every client ~4 min, no crash); `IOServiceOpen(type 0)`; then **sel 13** (no inputs, struct out 0x18 bytes = `_ioSurfaceLimits`) and requires u16 at out+0x16 == 1 (ABI version); out+0 = offset/plane-base alignment mask, out+4 = bytes-per-row alignment mask (used as (x+m)&~m), +0..+0x14 also copied into IOSurface remote-method init, otherwise logs and closes the connection.
  - **Create = sel 0**: scalar in [parent id or 0], struct in = `IOCFSerialize(props, kIOCFSerializeToBinary)` (OSUnserializeBinary format; keys IOSurfaceWidth/Height/BytesPerRow/BytesPerElement/PixelFormat/AllocSize/PlaneInfo/CacheMode/IsGlobal/...), struct out **0xa68 bytes** ("lock result"). **Lookup = sel 4**: scalar in [id], same struct out. LookupFromMachPort = sel 0x22 (scalar in [port name]); CreateMachPort = sel 0x23 (scalar in [id, options], scalar out [port name]).
  - Lock result (copied to client+0x68, size 0x68 + planes*0x80, min 0xe8): 0x00 u64 base address **mapped in the caller's task**; 0x08 u64 task VA of a per-surface shared state page (+0 u64 registry id, +8/+0xa u16 bound accel ids, +0xc u32 seed, +0x14 u8 tiled, +0x20 u32 value generation, +0x24 YCbCr matrix, +0x28 u32 non-bulk values size, +0x2d u8 displayable, +0x2e u8 sysmem-only, +0x30 0x70 bytes bulk attachments); 0x10 u64 task VA of timestamp page (4 u64 indexed timestamps, +0x20 detach code); 0x18 u32 surface id; 0x1c u32 alloc size; 0x20 width; 0x24 height; 0x28 bytes per row; 0x2c buffer offset; 0x30 pixel format; 0x34 u32 (dcache flush length); 0x38 plane count; 0x40 u16 bytes/element; 0x42 u8 element width; 0x43 u8 element height; 0x44 cache mode; 0x4c u8 subsampling; 0x4d u8 prohibit-use count; 0x50 parent id; 0x54 slice count; 0x58 u64 trace id; 0x60 u64 protection options; planes[n] at 0x68+n*0x80 (+0 width, +4 height, +8 bytes/row, +0xc offset, +0x14 size, +0x18 u16 bpe, +0x1a/+0x1b u8 element w/h, +0x1c u8 component count, +0x1d address format, +0x54 u8 compression type (non-zero -> no CPU base address)).
  - **Traps** (IOConnectTrapN -> `IOUserClient::getTargetAndTrapForIndex`): 0 IncrementUseCount(id, category), 1 DecrementUseCount(id, category), 2 **Lock**(id, options, &seed_out), 3 **Unlock**(id, options, &seed_out), 4 Release(id), 5 Release after a failed create/lookup setup (id).
  - Other selectors: 5 SetYCbCrMatrix, 6 WrapClientImage, 7 WrapClientMemory, 9 SetValue (serialized), 0xa UpdateNonBulkValueCache (struct in 9), 0xb RemoveValue, 0xc BindAccel, 0x11 SetSurfaceNotify (async), 0x12 RemoveSurfaceNotify, 0x13 Log, 0x14 SetPurgeable, 0x15 SetOwnership, 0x16 SetTiled, 0x18 SetTimestamp, 0x19 GetTileFormat, 0x1a CopyDataValueBytes, 0x1b SetBulkAttachments (struct 0x88), 0x1e/0x2e-0x31 (via outlined helpers), 0x1f SetCompressedTileDataRegionMemoryUsed, 0x20 GetGraphicsCommPageAddress, 0x21 SetIndexedTimestamp, 0x24-0x26/0x2d IOSurfaceAccelerator, 0x27-0x29 shared events, 0x2a SignalEvent, 0x2b Set/InitDetachModeCode, 0x2c SetOwnershipIdentity, 0x32-0x34 data properties.
  - => SWEET kernel service: class/name **IOCoreSurfaceRoot** + IOSurfaceRootUserClient; minimum = sel 13, 0, 4, 9/0xa/0xb (values), traps 0-5, 0x22/0x23 later for cross-process surfaces (CA sends surfaces to backboardd by mach port). Memory: IOBufferMemoryDescriptor per surface, mapped into each task with createMappingInTask; ids from a global table.

- **Image v8: daemon logs on the console.** `tools/patch-launchd-plist.py IN OUT LABEL...` rewrites launchd.plist (binary, plistlib): renames every `_PanicOnCrash` to `_PanicOnCrasX` and gives the listed jobs `StandardOutPath`/`StandardErrorPath` `/dev/console` (devfs console is 0622, writable by mobile) plus `OS_ACTIVITY_DT_MODE=YES` (os_log mirrored to stderr) and `CFLOG_FORCE_STDERR=1`. v8 = v7 + that plist for com.apple.backboardd and com.apple.SpringBoard, written through the mount (796310 bytes, root:80 0644), SHA256 in `ios16-root-20H392-v8.img.sha256`, `.simg` ready; boot with `shim/out/shim-boot-0045n.img`. Goal: see backboardd's uncaught exception text and the window server's display probing. ODDITY (unresolved): the v5 raw-image rename at offset 0x1e025f000 is present in the v5-v7 image bytes, but the plist read through a Linux mount of v7 still had the original `_PanicOnCrash` keys; filefrag shows the file as one extent. Never patch file contents through raw offsets again; write through the mount.
- **IOMobileFramebuffer.framework reversed (step 1 of the GUI plan).** `ipsw dyld disass research/dsc/dyld_shared_cache_arm64 --image IOMobileFramebuffer`.
  - Display discovery (`IOMobileFramebufferCreateDisplayList` -> `getDisplayListNumber`): iterates children of `IODeviceTree:/arm-io`, counts nodes whose `device_type` is "display-subsystem" or "ext-display-subsystem" (or `compatible` "paravirtualizedgraphics,gpu"); then `iomfb_populate_display_infos` adds an IOServiceAddMatchingNotification(IOServiceFirstMatch, **IOServiceMatching("IOMobileFramebuffer")**) and runs the run loop up to 30 s until that many services matched. `iomfb_match_callback` reads service properties `dfr`, `AppleTV`, `external` (CFBoolean) and names displays (external ones "%s-%d").
  - `IOMobileFramebufferOpen(service, task, type, &fb)`: `__ioMobileFramebufferAlloc` (CFPreferences com.apple.iokit.IOMobileGraphicsFamily: canvas_width/height, override_display_width/height, override_panel_width/height, benchmark, enable_ktrace), `IOServiceOpen(service, task, type)` (GetMainDisplay passes type 0), `getEDTProperty` reads `canvas-width`/`canvas-height` from the service's IODeviceTree parent, then fills a table of `kern_*` function pointers.
  - User client selectors (`kern_*` -> IOConnectCall*): 3 _kern_GetLayerDefaultSurface[ScalarMethod_stub]; 4 _kern_SwapBegin[ScalarMethod_stub]; 5 _kern_SwapEnd[StructMethod_stub]; 6 _kern_SwapWaitWithTimeout[ScalarMethod_stub] _kern_SwapWait[ScalarMethod_stub]; 7 _kern_GetID[ScalarMethod_stub]; 8 _kern_GetDisplaySize[ScalarMethod_stub]; 10 _kern_SetTVOutMode[ScalarMethod_stub]; 11 _kern_SetWSSInfo[ScalarMethod_stub]; 12 _kern_RequestPowerChange[ScalarMethod_stub]; 13 _kern_EnableStatistics[ScalarMethod_stub]; 14 _kern_SetFlags[ScalarMethod_stub]; 15 _kern_SetDebugFlags[ScalarMethod_stub]; 16 _kern_SetTVOutSignalType[ScalarMethod_stub]; 17 _kern_SetGammaTable[StructMethod_stub]; 18 _IOMobileFramebufferIsMainDisplay[ScalarMethod_stub]; 19 _kern_SetWhiteOnBlackMode[ScalarMethod_stub]; 20 _kern_SwapSignal[ScalarMethod_stub]; 22 _kern_SetDisplayDevice[ScalarMethod_stub]; 23 _kern_SetDigitalOutMode[ScalarMethod_stub]; 24 _kern_GetHDCPDownstreamState[StructMethod_stub]; 25 _kern_GetDigitalOutState[ScalarMethod_stub]; 26 _kern_printDisplayRegs[ScalarMethod_stub]; 27 _kern_GetGammaTable[StructMethod_stub]; 28 _kern_GetDotPitch[ScalarMethod_stub]; 29 _kern_GetDisplayArea[StructMethod_stub]; 30 _kern_EnableDisableDithering[ScalarMethod_stub]; 31 _kern_SetUnderrunColor[ScalarMethod_stub]; 33 _kern_EnableDisableVideoPowerSavings[ScalarMethod_stub]; 34 _kern_SetVideoDACGain[ScalarMethod_stub]; 35 _kern_SetLine21Data[ScalarMethod_stub]; 41 _IOMobileFramebufferEnableMirroring[ScalarMethod_stub]; 42 _IOMobileFrameBufferGetMirroringCapability[StructMethod_stub]; 43 _IOMobileFramebufferSetRenderingAngle[StructMethod_stub]; 44 _IOMobileFramebufferSetMirrorContentRegion[StructMethod_stub]; 47 _kern_HDCPSendRequest[ScalarMethod_stub]; 48 _kern_HDCPGetReply[ScalarMethod_stub]; 49 _kern_SurfaceIsReplaceable[ScalarMethod_stub]; 50 _kern_SetBrightnessCorrection[ScalarMethod_stub]; 51 _kern_SetColorRemapMode[ScalarMethod_stub]; 52 _kern_SwapCancel[ScalarMethod_stub]; 53 _IOMobileFramebufferSetCanvasSize[ScalarMethod_stub]; 54 _IOMobileFramebufferGetMatrix[Method_stub]; 55 _IOMobileFramebufferSetMatrix[Method_stub]; 56 _IOMobileFramebufferKernelTests[StructMethod_stub]; 57 _kern_GetColorRemapMode[ScalarMethod_stub]; 66 _kern_SPLCSetBrightness[ScalarMethod_stub]; 67 _kern_SPLCGetBrightness[ScalarMethod_stub]; 68 _kern_SetParameter[Method_stub]; 69 _kern_SwapSetColorMatrix[StructMethod_stub]; 72 _kern_DisableNotifications[ScalarMethod_stub] _kern_EnableNotifications[ScalarMethod_stub]; 73 _kern_ChangeFrameInfo[ScalarMethod_stub]; 74 _kern_SupportedFrameInfo[Method_stub]; 75 _kern_FactoryPortal[StructMethod_stub]; 77 _kern_GetCurrentAbsoluteTime[ScalarMethod_stub]; 78 _kern_SetBlock[Method_stub]; 79 _kern_GetBlock[Method_stub]; 80 _kern_GetLinkQuality[ScalarMethod_stub]; 81 _kern_SwapCancelAll[ScalarMethod_stub]; 82 _kern_GetProtectionOptions[ScalarMethod_stub]; 83 _kern_CopyLayerDisplayedSurface[ScalarMethod_stub]; 84 _kern_SetContrast[StructMethod_stub]; 85 _kern_GetBufBlock[Method_stub]; 86 _IOMFBGainEncoderFinishEncoding[Method_stub]; UNKNOWN {}
  - => Kernel needs: an `/arm-io` child node with device_type "display-subsystem" (+ canvas-width/height) and an IOService of class **IOMobileFramebuffer** (subclass name match) attached under it, opened with type 0, implementing at least GetDisplaySize(8), IsMainDisplay(18), GetID(7), GetLayerDefaultSurface(3), SwapBegin(4)/SwapEnd(5 struct)/SwapWait(6), Enable/DisableNotifications(72), frame info(73/74), CopyLayerDisplayedSurface(83), plus IOSurface for the swapped buffers. NEXT: CoreAnimation's AppleDisplay/IOMFBDisplay usage of these (constructor, first swap, vsync), then IOSurface.framework's IOSurfaceRoot selectors.
- **GUI PLAN (decided 2026-10-16): CPU rendering + kernel IOMobileFramebuffer.** User: CPU rendering is fine for now (goal = prove the GUI runs), may later research an Apple-style GPU driver for the Adreno 618 -> keep display output and renderer separable. QuartzCore findings (symbols from the cache's .symbols subcache: `ipsw dyld symaddr research/dsc/dyld_shared_cache_arm64 --image QuartzCore`; strings: `ipsw dyld macho ... QuartzCore --strings`):
  - Renderers: `sw_new_context` (CA::OGL::SWContext, full CPU renderer incl. blur, images, IOSurface-backed surfaces, make_buffer_current(WindowServer::Surface)), `gles_new_context`, `metal_new_context`, `new_null_context`. Env knobs include CA_ENABLE_OGL, CA_DISPLAY_TYPE, CA_FORCE_LOCAL_SERVER, CA_FORCE_TIMER, CA_CANVAS_WIDTH/HEIGHT, CA_MAIN_DISPLAY_SCALE/ORIENTATION, CA_DISABLE_RENDER, CA_ALWAYS_RENDER (selection logic not traced yet).
  - `-[CAWindowServer _detectDisplays]` (0x1884e3150) iterates static tables `open_funcs`/`count_funcs` = AppleCLCDDisplay, AppleRGBOutDisplay, AppleWirelessDisplay only; each `count()` = `display_count_of_type(IOMFBDisplayType)` over **`IOMobileFramebufferCreateDisplayList()`**, `open(i)` = `create_display_of_type` -> `CA::WindowServer::AppleDisplay(CFString name, ..., IOMFBDisplayType)` (an IOMFBDisplay driven by IOMFBServer: vsync_callback, frame_info_callback, swaps). `CA::WindowServer::VirtualDisplay` exists but is never auto-detected (explicit API only). => the main display MUST come from an IOMobileFramebuffer kernel service.
  - NEXT: reverse IOMobileFramebuffer.framework: IOMobileFramebufferCreateDisplayList / IOMobileFramebufferOpen (service matching, display type property), the user-client selectors used by IOMFBServer (display size/modes, swap begin/set-layer/end with IOSurface ids, vsync notifications), then the IOSurface kernel side (IOSurfaceRoot user client: create/lookup/lock, memory mapping) that both IOMFB swaps and CA surfaces need. Kernel: SWEET IOMobileFramebuffer service that copies the swapped IOSurface to the 1080x2400 framebuffer at 0x9c000000.
- **logd fixed; backboardd = DISPLAY WALL (boot 0045n on v7, 21:08:57 UTC, frames VID_20261016_230850 00:55-01:28, slide 0x4c3ec000, `research/crash-0045n-v7.txt`).** No `CRASH logd` any more; new daemons run (runningboardd, WirelessRadioManagerd, networkserviceproxy, dasd, cloudpaird, magicswitchd, atc, askpermissiond, ManagedSettingsAgent, containermanagerd uses AKS 0/17). New: locationd sig 11 at CFRunLoopAddSource+132 (NULL source) from its main+0x2af138 in a dispatch_once. **backboardd** sig 6: abort <- std::terminate <- _objc_terminate <- dispatch_once <- main+0x9334 = the "start %{public}@..." wrapper (0x100009264) for **"window server"** (block 0x10000a770 -> dispatch_once body 0x10001d7f0 = StartWindowServer): MTLSetShaderCachePath, `[CAWindowServer serverWithOptions:@{kCAWindowServerDisableUpdatesOnMainDisplay: @YES}]`, `setRendererFlags:`, **`mainDisplay`** -> `displayId` -> `[CADisplay displayWithDisplayId:]`, setWindowServerDisplay:, bounds, pointScale, currentMode, preferredScale, nativeOrientation, touchScales... With no display, mainDisplay is nil and it throws. (HID system and GS start fine before it.) SpringBoard dies on the same missing display (FBSDisplayMonitor). QuartzCore display backends (from the cache's .symbols subcache, `ipsw dyld str`): `CA::WindowServer::AppleCLCDDisplay` (IOMobileFramebuffer hardware) and **`CA::WindowServer::VirtualDisplay`** (open(), new_server, clone_update). `CA_DISPLAY_TYPE` and `CA_FORCE_LOCAL_SERVER` strings exist in QuartzCore but have no direct xref (likely read via a table of CA_* env names). NEXT: find how CA::WindowServer::Server enumerates displays (IOMobileFramebuffer services vs VirtualDisplay / CA_DISPLAY_TYPE) and choose: (a) kernel IOMobileFramebuffer service + IOSurface, or (b) a VirtualDisplay rendered by CA's CPU path (CA::OGL::SW) and copied to the framebuffer.
- **watchdogd + CommCenter + identityservicesd fixed (boot 0045n on v6, 20:41:30 UTC, frames VID_20261016_224133 00:39-01:13, slide 0x20fec000).** `SWEET WDT: watchdogd sel 0 in 0/0 out 1/0 -> ok`, no watchdogd/CommCenter/identityservicesd crashes (CommCenter/identityservicesd now call AKS 0/17/7). usermanagerd boot task runs (UMD_INIT creates primary session uid 501 "mobile", personas 99 System and 199 Default registered with the kernel); `Failed to atomically swap writing file /private/var//keybags/usersession.kb: Operation not supported (45)` (HFS lacks the atomic swap rename; non-fatal so far). Remaining: SpringBoard (FBSDisplayMonitor, no display), backboardd (uncaught exception), mediaserverd, lockdownd (crash inside obfuscated code, main+0x4c1b4?), logd. **logd**: main+0x18160 = `BUG IN LIBTRACE: Failed to migrate directory` from 0x10001801c(dir 0): 0x100016538 requires the dir to exist with uid/gid/mode from the table at 0x10002df14 (0: /private/var/db/diagnostics 272:272 0751, 1: /private/var/db/uuidtext 272:272 0755, 2: /private/var/db/diagnostics/timesync 272:272 0755) plus a `.migrated` file, else XPC "operation 6" to a helper and crash. **Image v7** = v6 + those dirs/markers (also in mkiosroot.sh), SHA256 in `ios16-root-20H392-v7.img.sha256`, `.simg` ready. Boot with `shim/out/shim-boot-0045n.img`.
- **Exit-reason text works (boot 0044n, frames VID_20261016_221726 00:32-00:53, slide 0x22d5c000).** CommCenter/identityservicesd: `couldn't dlopen libobjc-trampolines.dylib: dlopen(/usr/lib/libobjc-trampolines.dylib, 0x0106): tried: '/usr/lib/libobjc-trampolines.dylib' (no such file, not in dyld cache)`: the file only exists in the OS cryptex and dyld does not search cryptexes at ignition_level=1. 19 cryptex files have no root counterpart (OS: DriverKit dyld cache + .symbols, VisualTestKit, libffi-trampolines, libobjc-trampolines, libstdc++ 6.0.9 + 2 symlinks; App: SafariSupport.bundle, AuthenticationServicesAgent, com.apple.Safari.History, passwordbreachd, safarifetcherd, webbookmarksd, webinspectord, webpushd) -> hard-linked (symlinks copied: Linux hfsplus cannot hard-link symlinks); `tools/mkiosroot.sh` does it generically. watchdogd still crashed: the `-wdt_no_pmu` / `/arm-io/wdt no-pmu` check (0x10000a01c) only runs when os_variant_has_internal_diagnostics; otherwise 0x100009b18 looks up IOServiceMatching("IOService") + IOPropertyMatch {IOPMUPrimary: 1} (NSConstantDictionary) and crashes if absent, then IORegistryEntrySetCFProperty(boot stage 0xff) (failure only logged). Patch **0045**: IOWatchdog sets IOPMUPrimary = 1 and accepts setProperties; CI `38961814194` -> `xnu/out-0045`. **Image v6** = v5 + the 19 cryptex links, SHA256 7c610c6a...297a, `ios16-root-20H392-v6.simg` (full flash needed). Boot image `shim/out/shim-boot-0045n.img` (0045 + sweet-0044hi.adt). Still open: SpringBoard (no display), backboardd (uncaught exception, reason none), mediaserverd (Fig NULL dict), logd (main+0x18160), lockdownd (main+0x4c1b4).
- **System survives daemon crashes (boot 0043p, video frames VID_20261016_215006 00:25/00:42/00:54).** With the v5 plist patch no panic: launchd keeps launching (runningboardd, powerd, tccd, healthd, peopled, cryptexd, routined, aksd, mediaremoted, familynotificationd, nanoprefsyncd, navd, cloudpaird, passd, amsaccountsd, accessoryupdaterd, wcd ...). Shared cache slide that boot 0x406b4000 (`research/crash-0043p.txt`). watchdogd still crashed at main+0xb82c from the PMU step: `-wdt_no_pmu` is only honored when os_variant_has_internal_diagnostics; customer builds read `no-pmu` from IODeviceTree:/arm-io/wdt (IORegistryEntrySearchCFProperty) -> mkadt adds /arm-io/wdt {no-pmu}. **cryptexd** sig 6: abort_with_payload <- os_crash_fmt <- `__darwin_arm_secure_boot_chip.cold.7` ("panic: failed to get crypto algorithm") <- `_img4_chip_select_personalized_ap`: reads /chosen use-ddi-secure-boot, allow-ecid-mismatch, crypto-hash-method ("sha1" | "sha2-384"), /chosen/asmb lp-smb0/1 -> mkadt adds crypto-hash-method "sha2-384". **identityservicesd** sig 6 = same `_objc_fatal` in imp_implementationWithBlock as CommCenter (block trampolines; message needed). lockdownd sig 5 at main+0x4c1b4. Patch **0044**: crash report adds `CRASH name reason ns N code X: text` (exit reason description = abort_with_payload text). CI `38959096811` -> `xnu/out-0044`, QEMU OK. Image `shim/out/shim-boot-0044n.img` = 0044 + `shim/out/sweet-0044hi.adt` (wdt no-pmu, crypto-hash-method) + cmdline (wdt=-1, no -wdt_no_pmu).
- **First symbolicated daemon crashes (boot 0043u on journaled v4, 19:38:53 UTC; video frame chat image 36; transcribed in `research/crash-0043u.txt`; shared cache slide 0x40d60000 for every process).** (Gemini's video transcription invented values, use frames only.) `tools/sweet-crash.py research/dsc/dyld_shared_cache_arm64 x research/crash-0043u.txt`:
  - **watchdogd** pc main+0xb82c (`_os_crash` trap helper) from 0x100009bb0 = set PMU boot stage via IORegistry (no PMU) -> fix: boot-args `wdt=-1 -wdt_no_pmu` (Apple's own test mode writes "%s wdt=-1 -wdt_no_pmu"; watchdogd logs "skipping setting PMU boot stage because -wdt_no_pmu found in boot-args or no-pmu found in EDT"). Kernel effect of wdt=-1: sched hygiene debug off, zone_exhausted_timeout -1 (harmless).
  - **SpringBoard** sig 5 in `-[FBSDisplayMonitor _initWithBookendObserver:transformer:]+1160` <- `+[FBDisplayManager sharedInstance]` <- `FBSystemShellInitialize` <- `SBSystemAppMain`: no main display. GUI WALL: display service (IOMobileFramebuffer / CoreAnimation display).
  - **backboardd** sig 6: abort <- std::terminate <- _objc_terminate (uncaught exception; message not shown).
  - **CommCenter** sig 6: `_objc_fatal` in `imp_implementationWithBlock` (from `+[_PFRoutines initialize]`, CoreData): objc block trampolines cannot be allocated -> likely kernel gap (trampoline page remap); will hit many processes.
  - **mediaserverd** sig 11: CFDictionaryGetValue(NULL) in FigNotificationListenerStartNotifications (routing session manager).
  - **logd** sig 5 at its main+0x18160 (bt main+0x9dfc); lockdownd sig 5 (not yet symbolicated).
  - Image v5 = v4 + launchd.plist (`/System/Library/xpc/launchd.plist`, contiguous at image offset 0x1e025f000, 1456980 bytes) with the 7 `_PanicOnCrash` keys renamed `_PanicOnCrasX` in place (raw image patch, no metadata change) -> `diff-v4-v5.simg` = 7 blocks; v5 SHA256 78f96974...185a. Boot image `shim/out/shim-boot-0043p.img` = 0043 + `wdt=-1 -wdt_no_pmu`.
- **0043 console crash reports (QEMU verified); image `shim/out/shim-boot-0043u.img`; NEXT: flash v4 + boot 0043u.** Boot 0042u (video photo IMG_20261016_211646): short exec lines work; watchdogd crashes with NO `SWEET WDT:` line (fails before its first IOWatchdog call: lookup or IOServiceOpen, or elsewhere); lockdownd, SpringBoard, mediaserverd, CommCenter, identityservicesd, backboardd, watchdogd all crash repeatedly ("Too many corpses being created" = corpse limit, no crash reports). AKS callers: lockdownd (0, 7), imagent/sleepd (0, 17, 7), backboardd (0, 17), UserEventAgent (0, 7, 102, 103 -> unsupported). Patch **0043**: `sweet_crash_log` (osfmk/kern/exception.c, called from proc_prepareexit for crash exits on the current proc) prints `CRASH name[pid] sig S code (exc<<32|code) sub X slide SR mh MH`, `CRASH name pc lr sp fp far`, `CRASH name bt` (10 fp frames); AKS sel 103 notify_state_is_set -> 0. CI `38954520419` -> `xnu/out-0043`. QEMU test: init forks, child `brk #1`: `CRASH launchd[2] sig 5 code 0x600000001 sub 0x1000004f0 slide 0x0`, pc correct, parent keeps running (pid 1 crashes panic before proc_prepareexit, so test with a child). `tools/sweet-crash.py CACHE ROOT [report]` symbolicates typed-in CRASH lines (`ipsw dyld a2s` with addr - slide; main binary offsets = addr - mh + 0x100000000).
- **v3 reflashed 18:50-18:55 UTC (`research/flash-userdata-v3b.log`, 24/24 OKAY); 0042u booted 19:01:17 UTC on the clean disk (`research/boot0042u-2.log`), SLOW MO VID pending (watchdogd failure reason).** ABL hangs on the first `fastboot boot` after every big flash; user re-enters fastboot. User gave standing approval to reflash/boot without asking (memory standing-flash-approval). Commits now end with `Co-Authored-By: dipa-studio <183933817+dipa-studio@users.noreply.github.com>` (user request; never a Claude trailer).
  - watchdogd flow: connect_to_kext (0x100005408): IOServiceGetMatchingService("IOWatchdog") fails -> "failed to discover" + _os_crash; IOServiceOpen(type 1) fails -> "IOServiceOpen failed with error : 0x%x" + _os_crash. Then sel 0 (out 1 scalar): 0 -> "userspace monitoring disabled", 0x100009bb0, sleep 2, exit(0); nonzero -> "userspace monitoring enabled", normal operation.
  - **Image v4 (JOURNALED):** `tools/mkiosroot.sh` now does `mkfs.hfsplus -J`, mounts with `-o loop,force`, adds the /System/Library/Caches/com.apple.dyld hard links (44) and /private/var/keybags/systembag.kb (0700/0600 root). Built from the IPSW dmgs (OS 087-86698-044, SystemOS 087-86593-047, AppOS 087-86715-047) -> `/run/media/dipa/android/ios-sweet-ipsw/ios16-root-20H392-v4.img` SHA256 fba4aeae...ec0f9 + `.simg`. Header: attr 0x80002100 (unmounted, journaled), journal info block 129, journal 8 MiB at 532480 flagged need-init. Linux `fsck.hfsplus -n` reports "Volume header needs minor repair" on any fresh journaled volume even after -y (quirk). QEMU: 64 MB journaled test root (`rd=md0 rootrw=1`, 0042 kernel): `hfs: Initializing the journal (joffset 0x3000 sz 0x80000)` -> mounted -> init runs, no panic. NEXT: flash v4 (full), boot 0042u.
- **SPRINGBOARD STARTS (boot 0041u 18:39:53 UTC, photo IMG_20261016_204142).** backboardd, bluetoothd, fairplayd.H2, SpringBoard (pid 111, crashed: "Too many corpses"), xpcproxy run; `SWEET AKS: backboardd sel 0 -> 0`, `sel 17 in 1/0 out 0/4096 -> 0`. Panic: watchdogd[113] exited, namespace 2 subcode 5 (SIGTRAP = its _os_crash): watchdogd crashes on purpose when IOServiceGetMatchingService("IOWatchdog") fails ("connect_to_kext() unexpectedly failed") or IOServiceOpen(type 1) fails ("IOServiceOpen failed with error"); IOWatchdog DOES register (QEMU msgbuf: `SWEET WDT: IOWatchdog registered`), cause not on screen yet -> need video. Note `wdt_test=no_user_checkin` makes watchdogd log "detected testing boot-args to not run, exiting" (path not reached here?). **HFS CORRUPTION:** `hfs_swap_BTNode: offset #0 invalid (0xBC1D) (blockSize 0x2000 numRecords 81)`, `node=19677 fileID=4` (catalog), `hfs_mark_inconsistent` repeated. Likely cause: non-journaled HFS + unclean panics while writing (0038e wrote a 2.7 GB core then panicked; every boot since ends in panic). Plan: reflash v3 (clean), longer term HFS journaling. Patch **0042**: one short `exec NAME` console line instead of the 3-line "Allowing spawn of iOS binary" notice; CI `38949451276` -> `xnu/out-0042`; image `shim/out/shim-boot-0042u.img` (same cmdline as 0041u).
- **LAUNCHD DAEMONS RUN (boot 0039u, 18:29:13 UTC, photo IMG_20261016_203052).** With `launchd_unsecure_cache=1` all boot tasks pass and launchd starts LaunchDaemons (pids > 100: identityservicesd 114 and lockdownd 106 crash, "Too many corpses being created"). Fatal: `watchdogd: ERROR: failed to discover watchdog KEXT service` -> exit (namespace 2 = signal, subcode 5) -> `_PanicOnCrash` panic. watchdogd: IOServiceMatching("IOWatchdog"), IOServiceOpen type 1, IOConnectCallScalarMethod sel 0/1 (check in)/3/4 (disable/enable userspace monitoring)/5, IOConnectCallStructMethod sel 2 (1 KiB in) and 9 (small out); VM path ("detected virtual machine environment and no watchdog KEXT found, exiting...") only when it detects a VM. Console also flooded with `hfs: set hardlink bit on vol=iOSRoot cnid=321318` (Linux-made hard links lack kHFSHasLinkChainBit; repaired only in memory on each lookup). Patches **0040** (`iokit/Kernel/arm/SweetWatchdog.cpp`: IOWatchdog + IOWatchdogUserClient, all selectors succeed with zeroed outputs, each logged once as `SWEET WDT: ...`) and **0041** (sweet_hfs hfs_catalog.c: the three link-repair printfs limited to 8 per boot); CI `38948245372` PASSED -> `xnu/out-0041` (QEMU regression OK). Image `shim/out/shim-boot-0041u.img` (0041 + sweet-0038hi.adt + ufsrw rootrw + launchd_unsecure_cache=1) booted 18:39:53 UTC (`research/boot0041u.log`), photo pending.
- **v3 FLASHED + keybag passes; next wall AMFI (launchd_cache_loader).** User said "flash, nothing to lose": `fastboot -S 512M flash userdata ios16-root-20H392-v3.simg` 17:51:52-17:57:01 UTC, 24/24 chunks OKAY (`research/flash-userdata-v3.log`). userdata = v3 (SHA256 fa84274c...22df) until the next rw boot. ABL fastboot then hung ("Sending" forever, `reboot bootloader` timed out) until the user re-entered fastboot by hand (common Xiaomi ABL crash). Boot 0038e 18:06:15 UTC (`research/boot0038e-3.log`), photos IMG_20261016_200812/200838: keybag OK, then boot tasks tzinit (`Bad zoneinfo link`, resets to system partition, OK), finish-restore, finish-demo-restore, sysstatuscheck, prng_seedctl (`failed to load kernel prng seed`, `failed to load virtual random (-147)`, AllowCrash), auearlyboot, then **launchd_cache_loader: `abort: Unable to find AMFI`** -> 2.7 GB core written to /cores in 91 s -> launchd panic `launchd_cache_loader[22] exited -- exit reason namespace 7 subcode 0x1`. launchd_cache_loader: SecStaticCodeCheckValidity of /System/Library/xpc/launchd.plist with detached .sig, then IOServiceMatching("AppleMobileFileIntegrity") + IOServiceOpen type 0 + IOConnectCallMethod sel 6 (1 scalar = 1, struct in = cdhash) = trust the cdhash, then sends the cache to launchd. Boot-arg `launchd_unsecure_cache=1` skips signature + AMFI ("Using unsecure cache"); the value is parsed with strtoul base 10 (helper 0x100002da8), so a path = 0 = off: boot 0039w (18:17:13 UTC, `=/System/Library/xpc/launchd.plist`, photo IMG_20261016_202008) still aborted `Unable to find AMFI` (core dump now skipped: `Failed to generate core file ... error 14`, so 0039 works). Image `shim/out/shim-boot-0039u.img` uses `launchd_unsecure_cache=1`. Patch **0039**: do_coredump = 0 on SWEET (kern.coredump sysctl still works); CI `38945267341` -> `xnu/out-0039` (_do_coredump now in __common). Image `shim/out/shim-boot-0039w.img` = 0039 + sweet-0038hi.adt + ufsrw rootrw + `launchd_unsecure_cache=/System/Library/xpc/launchd.plist`. TODO later: real AppleMobileFileIntegrity IOService (sel 6 trust cdhash etc.).
- **Image v3 ready, awaiting user "flash".** Boot 0038w 17:38:10 UTC, photo (chat image 30): `SWEET AKS: keybagd sel 0 -> 0x0`, `sel 14 out 1/0 -> 0x0` (x2), `MKB_INIT: mount is with NO CPROTECT ... does not support Data Protection`, `System Keybag loaded`; then keybagd still opens /private/var/keybags/systembag.kb (0x100012d3c, for BackupKeyBagKeys) -> ENOENT, `no-effaceable-storage` not set -> `Can't load the keybag. tears in rain... Time to die` -> `FATAL KEYBAG ERROR: kb_load` -> reboot -> Halt/Restart Timed Out panic. Fix: ADT `/defaults/no-effaceable-storage` (mkadt.py; `shim/out/sweet-0038hi.adt`, `research/q0038-hi.adt`, QEMU OK) + file `/private/var/keybags/systembag.kb` (0600 root, dir 0700; XML plist {KeyBagKeys: data}). **v3 image** `/run/media/dipa/android/ios-sweet-ipsw/ios16-root-20H392-v3.img` = v2 + that file, fsck OK, SHA256 fa84274c...22df; `ios16-root-20H392-v3.simg` (img2simg: zero blocks become FILL chunks, so a full flash overwrites every block the rw boots changed). Flash: `fastboot -S 512M flash userdata ios16-root-20H392-v3.simg`, then boot `shim/out/shim-boot-0038e.img` (0038 + sweet-0038hi.adt + ufsrw=1 rootrw=1).
- **0038 AppleKeyStore (CI 38938744130 PASSED -> `xnu/out-0038`; QEMU msgbuf: `SWEET AKS: AppleKeyStore registered (no passcode, unlocked)`; phone image `shim/out/shim-boot-0038w.img` booted 17:38:10 UTC, `research/boot0038w.log`, photo pending).** QEMU full kernel log trick (fb.txt is only the last screen): `llvm-nm KERNEL | grep _msgbufp` -> `--hmp "x /1gx ADDR"` gives struct msgbuf address (static, 0xfffffe0007b56678 on 0038) -> `--hmp "x /3gx STRUCT"` gives bufc (3rd quad) -> `--hmp "memsave BUFC 0x20000 \"FILE\""` (quote the file name), `tr -d "\0" < FILE`. Same inputs give the same addresses. Boot 0037w 17:08:35 UTC, photo IMG_20261016_191052: bindfs fixed mount; mount-phase-1/2 pass; `cc_fips_test` boot task: all corecrypto FIPS POST tests PASSED in userspace; then keybag boot task `keybagd --init`: `MKB_INIT: FATAL KEYBAG ERROR: failed to load system bag`, `Could not get options entry from the device tree` (x2, IODeviceTree:/options = NVRAM, non-fatal), `REBOOTING INTO RECOVERY MODE` -> reboot -> panic `Halt/Restart Timed Out @IOPlatformExpert.cpp:884` (no restart path on SWEET).
  - keybagd (static libaks): load_devicebag (0x100012c30) calls aks_get_system (sel 14, 0-1 scalar in, 1 out) and loads /private/var/keybags/systembag.kb only if the result is 0xe00002f0 (NotFound); any other error -> fatal; SUCCESS -> skip the file (userspace-reboot path). systembag.kb is a plist {KeyBagKeys}; decrypted with effaceable storage unless IODeviceTree:/defaults has `no-effaceable-storage`. Image has no /private/var/keybags. has_data_protection: statfs of /private/var; no cprotect on our HFS -> device-bag volume mapping skipped.
  - libaks connection: IORegistryEntryFromPath / IOServiceMatching("AppleKeyStore"), IOServiceOpen type 0, then selector 0 (no args) must succeed.
  - **AppleKeyStore selector map (iOS 16.7 AppleKeyStore.framework, via `ipsw dyld disass`):** 0 open, 2 create_bag, 3 save_bag, 4 unload_bag, 5 set_system_with_passcode, 6 load_bag, 7 get_lock_state (1 in, 1 out; bit 2 = unlocked since boot), 9 unlock_device, 10 wrap_key, 11 unwrap_key, 12 unlock_bag/test_stashed_kek, 13 lock_bag, 14 get_system, 15 change_secret_se, 16 internal_state, 17 get_device_state (1 in, struct out <=4K: DER SET of SEQUENCE{UTF8 key, INTEGER}: ss state, sls lock_state (MKBGetDeviceLockState returns it), sb backoff, sbo, sfa failed attempts, sfao, sgs generation, sas assertions, sgpe grace, srcd countdown, sr reserved), 18 recover_with_escrow_bag, 19 obliterate_class_d, 20 drain_backup_keys, 21/22 set/clear_backup_bag, 23 get_bag_uuid, 24 rewrap_key_for_backup, 26/27 assert_hold/drop, 30/31 set/get_configuration, 33-37 stash, 38 auth_token_create, 40 generation, 41 fdr_hmac_data, 42 verify_password, 43 _aks_operation, 44 remote_session, 49/50 signing keys, 51/53/54 stash enable/persist/escrow, 55 unload_session_bags, 57/58 remote peer, 59-62 smartcard, 63 migrate_s_key, 65 set_keybag_for_volume_with_cookie_persona, 66/67 sync bags, 68 copy_volume_cookie_persona, 69-73 se_*, 74-79/84/85/99 fv_* (FileVault/VEK), 80/81 absinthe, 82 make_public_backup_bag, 83 drop_auxiliary_auth, 86 kext get/set options, 87 invalidate_bag, 88-91/94/95/106/107 se_*, 92 lower_iteration_count, 93 get_internal_info, 96-98/117 keybag_persona create/list/delete, 100/101 assert promote/consume, 102/103 notify_state set/is_set, 104 fairplay, 105 change_secret_epilogue, 108 delete_xart_leak, 110-113 backup volume, 114 sealed_hashes_set, 115 prewarm_sps, 118-128 AKSIdentity*/AKSGetLastUser.
  - Patch **0038**: `iokit/Kernel/arm/SweetKeyStore.cpp` (class AppleKeyStore on IOResources, IOUserClientClass AppleKeyStoreUserClient; personality in KernelConfigTables.cpp): 0/4/5/9/12/13/26/27/55/102 success, 14 -> handle 0, 7 -> 0x4, 17 -> DER state (ss 4, sls 0), others kIOReturnUnsupported; logs `SWEET AKS: <proc> sel N arg0 in a/b out c/d -> ret` for every call.
  - Tools: shared cache copied to `research/dsc/` (git-ignored; ipsw needs a writable dir for its .a2s symbol cache); `ipsw dyld disass research/dsc/dyld_shared_cache_arm64 --image AppleKeyStore|MobileKeyBag`; scratchpad `annot2.py BIN DIS FIXUPS` annotates llvm-objdump output with strings and import names (`ipsw macho info --fixups`).
- **0037 bindfs (phone boot 0037w pending photo).** Boot 0036mw 16:57:47 UTC, photo IMG_20261016_190102: WRITABLE ROOT WORKS: `/dev/ufsroot0 on / (hfs, local, noatime)` after mount_hfs update (GetMasterBlock EBUSY harmless), coredump of mount written to /cores (rw). Then `mount: failed to mount /private/preboot/5CBE3601.../usr/standalone/firmware -> ...: Operation not supported by device (19)` -> exit 74 -> launchd panic `mount[2] exited`. Cause: the macOS-derived config had nullfs but no bindfs (ENODEV = unknown fs type). Caller passes env 0 -> bind not required, ENOENT (missing source dir) tolerated. Patch **0037** adds `bindfs` to FILESYS_BASE in MASTER.arm64.sweet; CI `38936550483` -> `xnu/out-0037` (bindfs_vfsops present; QEMU probe regression OK). Image `shim/out/shim-boot-0037w.img` (0037 + sweet-0036hi.adt + ufsrw=1 rootrw=1) booted 17:08:35 UTC (`research/boot0037w.log`). NOTE: userdata has now been modified by rw boots; it no longer equals the v2 image, so sparsediff with v2 as OLD is not safe any more (full reflash or a new baseline needed).
- **0036 phone: launchd boot tasks run; mount -P 1 needs /chosen/boot-manifest-hash.** Boot 0036hr 16:15:32 UTC, photo IMG_20261016_185236: platform check passes; fsck boot task runs (`fsck: not booting main or diagnostic OS. Skipping fsck on OS container`); mount-phase-1: `failed to get filesystem info` x2 (no IODeviceTree:/filesystems/fstab, non-fatal), `mount: data volume missing, but not required in env: 0`, mount_hfs update of /: `GetMasterBlock: Error 16 opening /dev/ufsroot0` (EBUSY, mounted block dev, non-fatal) then mount() EROFS (read-only boot) -> `mount: / failed with 1`; then `failed to get boot-manifest-hash` -> errx exit 66 -> launchd panic `mount[3] exited`. /sbin/mount: fn 0x100005f90 reads IODeviceTree:/chosen boot-manifest-hash (hex), bindfs-mounts /private/preboot/<HEX>/usr/standalone/firmware (ENOENT tolerated unless required). `tools/mkadt.py` now adds `boot-manifest-hash` = SHA-384("sweet boot manifest") (5CBE3601...5205). ADTs `shim/out/sweet-0036hi.adt`, `research/q0036-hi.adt` (QEMU probe OK, csops 0x26000001). Image `shim/out/shim-boot-0036mw.img` (0036 + new ADT + ufsrw=1 rootrw=1), booted 16:57:47 UTC (`research/boot0036mw.log`): FIRST WRITABLE BOOT of userdata (restore source: v2 image on SSD).
- **0036 CS_SIGNED (phone boot 0036hr pending photo).** Phone boot 0035hr 2026-10-16 15:57:02 UTC (`research/boot0035hr.log`, photo IMG_20261016_180249): highmem works on hardware; shared cache maps (trust-cache warnings only), Apple launchd runs (`Darwin Bootstrapper Version 7.0.0`, `entering ondemand mode`), starts boot task fsck, then userspace panic `boot task is not a platform binary (fsck, /sbin/fsck)`. launchd+0x3fea0: `csops(pid, CS_OPS_STATUS)` must have bit 0x04000000. Cause: nothing set CS_SIGNED (AMFI does it in vnode_check_signature), so csproc_get_blob() returns NULL for every process and csops never reports CS_PLATFORM_BINARY (also breaks per-process cdhash/entitlement queries). QEMU probe init (`csops` status printer, scratchpad csq/) on 0035: `0x02000001`; patch **0036** (`*cs_flags |= CS_SIGNED` in the SWEET AMFI hook), CI `38929635791` -> `xnu/out-0036`: `0x26000001`. Images `shim/out/shim-boot-0036hr.img` / `-0036hw.img` (same cmdlines as 0035). 0036hr booted 16:15:32 UTC (`research/boot0036hr.log`). Next launchd boot tasks (embedded __config plist): fsck -qL and mount -P 1/2 (RequireSuccess); no /etc/fstab on the image.
- **0035 ENTITLEMENTS + PLATFORM BINARIES (QEMU verified).** `xnu/patches/0035-sweet-amfi-entitlements-platform-binaries.patch`: new `iokit/Kernel/arm/SweetEntitlements.cpp` (OSObject subclass: OSDictionary from OSUnserializeXML of the signature's XML entitlements + original XML for CS_OPS_ENTITLEMENTS_BLOB); `bsd/kern/sweet_amfi.c` answers queryEntitlementBoolean/String(+WithProc, string also matches array members), copyEntitlementAsOSObject(+WithProc, retained), asdict (retained), get_xml (kalloc_data copy); built-in MAC policy "SWEET AMFI" (registered from bsd_init before vfs/exec) with mpo_vnode_check_signature: every signed binary on the MNT_ROOTFS mount gets CS_PLATFORM_BINARY (stand-in for AMFI's static trust cache: iOS system binaries are ad-hoc, cd_flags 0x2, platform byte 0), and attaches entitlements ONLY for the writable copy (cs_blob != csb_ro_addr; revalidation passes the RO blob). LESSON: first version attached in adjustContextWithoutMonitor -> QEMU `unable to adjust OSEntitlements context without monitor: 53` because ubc_cs_convert_to_multilevel_hash (4K-page signatures on 16K kernel) sets csb_entitlements_blob = NULL; ALL iOS 16 binaries (launchd, backboardd, SpringBoard) use 4K code pages, so this would have broken launchd on the phone. Boot-arg `sweet_amfi_debug=1` logs `SWEET AMFI: <ident>: N entitlements (test: ...)`. `tools/mkinit.py OBJ OUT [ENTS.plist]` adds an XML entitlements blob (special slot -5; default output byte-identical). QEMU `research/q0035-ent` (RAM disk `research/root-hfs-ent.img`, init with 3 test entitlements, highmem): `org.sweet.init: 3 entitlements (test: bool 1 string 1 array 1)` then init PID 1. MAC policies loaded: 0034 = 1, 0035 = 2 (QMP `mac_policy_list`). CI `38909807230` -> `xnu/out-0035`. Phone images: `shim/out/shim-boot-0035hr.img` (highmem, ro), `-0035hw.img` (highmem, +ufsrw=1 rootrw=1), `-0035r.img` (low mem fallback).
- **PHONE TEST ORDER (updated):** 0035hr -> if instant reset, 0035r -> then 0035hw.

- **HIGHMEM: XNU in the upper DDR bank, ~3.95 GiB (was 1.2 GiB).** Live FDT memory = <0x80000000 2G> + <0x1_00000000 0xfcc00000>; all fixed reserved-memory carve-outs are in the low bank (highest: ramdump_fb 0xaf000000, rmtfs ~0xfde01000), dynamic pools have alloc-ranges <= 0xffffffff, UFS node has no `iommus` (Linux DMAs anywhere). `tools/mkadt.py --highmem` sets /chosen dram-base 0x100000000 dram-size 0xfcc00000; `tools/mkpayload.py` now takes phys_base/mem_size from the ADT (default payloads byte-identical, verified); `tools/qemu-sweet.py` sizes -m from the payload (8G for highmem). Patch **0034** (`0034-sweet-ufs-dma-above-4g.patch`): UFS refuses DMA memory above 4G without UFSHCI CAP.64AS (bit 24), logs `DMA at 0x...`. CI `38905889883` success -> `xnu/out-0034`. **QEMU verified** (`research/q0034-hi`, ADT `research/q0034-hi.adt` --qemu --highmem, HFS RAM disk): phys_base 0x100000000, init PID 1 heartbeat, no panic; `max_mem` = `mem_size` = 0xfcc00000 read via QMP (`research/q0034-hi-mem`). Phone images: `shim/out/shim-boot-0034hr.img` (read-only) / `-0034hw.img` (+ufsrw=1 rootrw=1), ADT `shim/out/sweet-0034hi.adt` (asmb SIP + sweet-ufs + highmem). PHONE RISK: unknown runtime TZ/XPU protection in the upper bank would show as an instant reset; fall back to 0033r/w. Watchdog ruled out for the overnight reset: msm-watchdog bark is 20 s (qcom,bark-time 0x4e20) yet panic screens stay up for many minutes.

- **Offline research 2026-10-16 (user away, phone unavailable). Images rebuilt** `shim/out/shim-boot-0033r.img` / `-0033w.img` now also carry `wdt_test=no_user_checkin`. NEXT ON PHONE: boot 0033r (expect past in6_nigroup), then 0033w (first writes: rw root fixes HFS link-chain bits itself and gives /var for launchd sockets /var/run/syslog, /var/run/lockdown.sock).
- **launchd.plist** (`/System/Library/xpc/launchd.plist`, compiled; 532 daemons, 66 RunAtLoad/KeepAlive, list in scratchpad `early-daemons.txt`). `_PanicOnCrash` daemons: containermanagerd/usermanagerd (InternalOnly), lockdownd/remoted/trustd/remotepairingdeviced (AutomationOnly), **watchdogd unconditional** (KeepAlive SuccessfulExit=false). watchdogd needs IOKit `IOWatchdog` kext service; if absent it exits only when `kern.hv_vmm_present` (ADT `/defaults/vmm-present`, hvg_sysctl.c) or with boot-arg `wdt_test=no_user_checkin` ("detected testing boot-args to not run, exiting"; reads kern.bootargs). Using the boot-arg (vmm-present would change many daemons; keep as an option).
- **GUI path research (QuartzCore in the shared cache, `ipsw dyld str CACHE STR`, ~10 s/search):** CA::WindowServer has IOMFBServer/IOMFBDisplay (Apple DCP/IOMobileFramebuffer), AppleCLCDDisplay, AppleRGBOutDisplay, **VirtualServer/VirtualDisplay** and **MemorySurface**, EAGLServer. Renderers: CA::OGL::MetalContext, GLContext and a **CPU software rasterizer CA::OGL::SW** (samplers/blend modes; "image is too large for software renderer"). Env knobs: `CA_ENABLE_OGL`, `CA_DISPLAY_TYPE`, `CA_FORCE_LOCAL_SERVER` (249 CA_* vars). Hypothesis (unverified): backboardd's render server could run a VirtualServer/MemorySurface with the SW renderer and we copy the surface to the ABL framebuffer -> needs disassembly of CA::WindowServer server creation. Expected other GUI walls: IOSurface (closed-source kext; needs a reimplementation), IOMobileFramebuffer user client, IOHID touch events, AppleKeyStore/keybag (SEP) for lock state, MobileGestalt answers (AppleCLCD etc.).

- **0032r RESULT (boot 05:07:50 UTC, `research/boot0032r.log`, photo IMG_20261016_071200): SHARED CACHE MAPPED, LAUNCHD RUNS.** With SIP relaxed (ADT asmb) the `not in trust cache` lines are only warnings for every subcache (.31 ... .42.dyldlinkedit); no SIP rejection; libSystem loads; launchd configures networking (`skip attaching fsw to lo0 using legacy TX model`) -> kernel data abort far 0x28 in `SHA1Init` (symbolized as sha1_init) from `in6_nigroup` (IPv6 on lo0): g_crypto_funcs NULL. Kernel addresses are unslid: `~/swift/usr/bin/llvm-symbolizer --obj=KERNEL ADDR` works directly.
- **0032** BearSSL SHA-1 (`0032-sweet-bearssl-sha1.patch`), **0033** BearSSL SHA-384/512 (`0033-sweet-bearssl-sha384-sha512.patch`, BearSSL ctx stored in SHA512_CTX, static-asserted to fit; ubc_subr.c uses SHA-384 for code directories). `0020-stage-bearssl.sh` now also stages hash/sha1.c, hash/sha2big.c, codec/{dec,enc}{32,64}be.c. CI `38854909053` success (0032-only run `38854802073` superseded). Kernel `xnu/out-0033` (SHA1Init -> _br_sha1_init verified by disassembly; nm symbols have a leading underscore). Images (ADT sweet-0032): `shim/out/shim-boot-0033r.img` (read-only), `shim-boot-0033w.img` (+ufsrw=1 rootrw=1). Still NULL g_crypto_funcs users: des, chacha20poly1305, rsa, aesxts, rand, flow_divert.
- `research/check-patch-order.py` now skips patches touching CI-staged sweet_hfs sources (0031) instead of stopping.

- **0031r RESULT (boot 05:03:52 UTC 2026-10-16, `research/boot0031r.log`, photo IMG_20261016_070508): SHARED CACHE FOUND.** dyld now opens `dyld_shared_cache_arm64` (v2 image hard links), kernel refuses to map it: `shared_region: ... map(...'dyld_shared_cache_arm64'): not in trust cache` -> `vnode is not SIP-protected` (vm_unix.c: macOS arm64 path needs trust cache, else root-owned + SF_RESTRICTED unless CSR_ALLOW_UNRESTRICTED_FS) -> `dyld cache '(null)' not loaded: syscall to map cache into shared region failed` -> libSystem not loaded -> coredump to /cores fails error 30 (EROFS) -> panic initproc failed -> "MACH Reboot" (spins; screen kept). Lots of `hfs: set hardlink bit on vol=iOSRoot cnid=... linkid=...` spam (Linux-made hard links lack the link-chain bit; read-only mount cannot persist the fix). FIX: ADT `/chosen/asmb` with `lp-sip0`=0x6f (u64; incl. CSR_ALLOW_UNRESTRICTED_FS) and `lp-sip1`=1 (unauthenticated root), `tools/mkadt.py` -> `shim/out/sweet-0032.adt`. Images with kernel 0031: `shim/out/shim-boot-0032r.img` (read-only) and `shim-boot-0032w.img` (+ufsrw=1 rootrw=1).

- **2026-10-16 morning:** userdata now = **v2** image (`diff-v1-v2.simg` flashed 21:06:50 UTC 2026-10-15, OKAY, `research/flash-userdata-diff-v2.log`); future diffs use `ios16-root-20H392-v2.img` as OLD. Booted `shim-boot-0029k.img` (ignition_level=1) right after (`research/boot0029k-v2.log`); **no photo** (user asleep). Next morning the phone was in PixelOS recovery = some hardware reset (ABL then booted Android, which cannot use userdata). OBSERVATION: our kernel cannot reset the SoC itself (`PE_halt_restart` is never set; reboot/halt print "MACH Reboot"/"CPU halted" and spin), so the reset came from outside XNU: Qualcomm watchdog or a TZ/XPU violation. Unknown which; re-boot 0029k and watch/video until the reset. Do NOT tap factory reset/format data in recovery (would wipe the iOS image).
- **0030** (`xnu/patches/0030-sweet-ufs-writes.patch`, CI `38852655542`): UFS WRITE(10) + read-modify-write for partial 4 KiB blocks + SYNCHRONIZE CACHE (DKIOCSYNCHRONIZE), only with boot-arg `ufsrw=1`; `ufs_write_blocks` re-checks partition bounds before every write (only place data goes out).
- **0031** (`xnu/patches/0031-sweet-read-write-root.patch`, CI `38852837176`): boot-arg `rootrw=1` clears MNT_RDONLY before the root mount (no data volume on sweet: /private/var is on the root; image has no /etc/fstab); Apple HFS accepts a dirty non-journaled ROOT read-write on SWEET (logs "mounting dirty non-journaled root read-write"). Later: journaled HFS for crash safety. Kernel `xnu/out-0031` (CI `38852837176` success, 5m31s; 0030 run cancelled by the newer push). Boot images (phone ADT `sweet-0028.adt`, ramdisk byte-matched): `shim/out/shim-boot-0031r.img` = 0029k args (read-only, ignition_level=1) and `shim/out/shim-boot-0031w.img` = same + `ufsrw=1 rootrw=1`. PLAN: boot 0031r first and film until the reset (diagnose overnight reset), then 0031w (first ever writes to userdata; v2 image on the SSD is the restore source). `research/check-patch-order.py` cannot check 0031 (staged sweet_hfs files are not in its index); CI stage scripts run first, so CI is the check.

- **ignition_level=1 result** (boot 21:01:39 UTC, `research/boot0029k.log`, photo IMG_20261015_230308): preboot/cryptex stages skipped (need >= 2/3), `dylib_cache: finding shared cache on system volume: ignition level = 1, search root fd = 4, subpath = System/Library/Caches/com.apple.dyld/` -> not found -> `ignition boot failed: 19` -> no shared cache -> libSystem not loaded. FIX IN PROGRESS: image v2 = copy of the flashed image + `/System/Library/Caches/com.apple.dyld/` with HARD LINKS to the 44 cryptex cache files (no extra space; avoids symlink-following doubts), then `tools/sparsediff.py ios16-root-20H392.img ios16-root-20H392-v2.img diff.simg` and flash only the diff. Boot with `ignition_level=1` (shim-boot-0029k.img).
- **ignition_level=0 result** (boot 20:58:07 UTC, `research/boot0029j.log`, photo IMG_20261015_230037): all stages skipped as "ignition level insufficient" (hello/preboot/cryptex1 sniff >= 2, select os cryptex path/graft >= 3, **dyld_cache >= 1**), `ignition boot failed: 89`, "ignition partially disabled", then same `Library not loaded: /usr/lib/libSystem.B.dylib (no such file, no dyld cache)`. => dyld gets the shared cache directory from ignition's dyld_cache stage. Next: `ignition_level=1` (`shim/out/shim-boot-0029k.img`) to skip preboot/cryptex stages but run dyld_cache; its log "finding shared cache on %s ... subpath = %s" will show where it searches. If it searches rootfs /System/Library/Caches/com.apple.dyld, add a symlink there (image rebuild; consider a diff-only sparse flash tool to avoid rewriting 12 GB).
- **APPLE dyld/launchd RUNNING (libignition) with `unentitled_ios_sim_launch=1`** (boot 20:53:24 UTC, `research/boot0029i.log`, photo IMG_20261015_225617): kernel prints "Allowing spawn of iOS binary ... boot-arg set to true"; `shared_region: ... check_np ... vm_shared_region_start_address() failed` (no region yet, normal); dyld's built-in **libignition** (Darwin Ignition Sequence 1.0.0, libignition-51~1974; prints rd=ufsroot0, hardware target sweet, ignition level 0x5, platform 0x2, boot spec local, 7 stages): `hello from launchd.1` -> `preboot: mounting preboot` -> `failed to lookup preboot: 25` (ENOTTY: looks for a separate Preboot volume by role) -> ignition fails -> dyld `Library not loaded: /usr/lib/libSystem.B.dylib ... (no such file, no dyld cache)` -> launchd exit -> panic initproc failed. dyld boot-args found via strings: `ignition_level`, `ignition_force_dylib_root` (forced rootfs/livefs/cryptex fallback), `ignition_halt_after`, `ignition_live_app_graft`; dyld cache search paths include /System/Cryptexes/OS, /System/Volumes/Preboot/Cryptexes/OS/, /private/preboot/Cryptexes/OS/ (present in our image). Next try `ignition_level=0` (`shim/out/shim-boot-0029j.img`).
- **APPLE launchd EXECUTED FROM UFS (2026-10-15).** Flashed iOS image: `img2simg` -> `ios16-root-20H392.simg` (12.1 GB) then `fastboot -S 512M flash userdata ...simg` (24 chunks, 307 s, `research/flash-userdata-ios16.log`; a raw-image flash was killed by earlyoom at 2.6 GB RSS - always flash the sparse image). ABL fastboot hung on getvar after the flash; power+vol-down fixed it. Boot 0029u 20:49:04 UTC (`research/boot0029u-ios16.log`), photo IMG_20261015_225134: `hfs: mounted iOSRoot` -> load_init_program /sbin/launchd -> panic `unexpected SIGKILL of launchd (CS_KILLED) with reason -- namespace 9 code 0xe` = OS_REASON_EXEC / EXEC_EXIT_REASON_WRONG_PLATFORM: our kernel is XNU_TARGET_OS_OSX, iOS-platform binaries are "alien" and refused unless spawn attr platform set or DEVELOPMENT TUNABLE `unentitled_ios_sim_launch`. Next try: same kernel, cmdline + `unentitled_ios_sim_launch=1` (`shim/out/shim-boot-0029i.img`). LONGER TERM: macOS-config kernel marks iOS maps alien (vm_map_mark_alien) and differs from iOS in many policies; an iPhoneOS-config kernel build may eventually be needed.
- **iOS 16 ROOT IMAGE BUILT:** `/run/media/dipa/android/ios-sweet-ipsw/ios16-root-20H392.img` (16 GiB case-sensitive HFS+, label iOSRoot, 12 GB used, fsck OK after `fsck.hfsplus -y` rewrote 32 non-ASCII localized WorkflowKit Shortcut names Linux decomposes differently). Built by `tools/mkiosroot.sh OS.dmg SYSTEMOS.dmg APPOS.dmg OUT.img [SIZE]` (needs sudo; apfs-fuse as root; OS dmg is UDIF -> link must end .dmg). Contents: iPhone X 20H392 OS root + SystemOS cryptex at /private/preboot/Cryptexes/OS (so /System/Cryptexes/OS -> cache, 44 files, dyld_v1 arm64) + AppOS at .../App. /sbin/launchd and /usr/lib/dyld root:wheel 0755. NEXT: (confirm) `fastboot flash userdata ios16-root-20H392.img` (auto-sparse), boot 0029u (rd=ufsroot0) -> Apple launchd attempt.
- **MILESTONE ON HARDWARE: BOOT FROM INTERNAL FLASH.** 0029 CI `38797924912` PASSED, `xnu/out-0029` SHA256 `a68bc847...2a37`. Image `shim/out/shim-boot-0029u.img` (payload-0029u = 0029 kernel + `shim/out/sweet-0028.adt` + `rd=ufsroot0`, NO RAM disk). Boots 20:01:34 and 20:12:37 UTC (`research/boot0029u*.log`), photo IMG_20261015_221403: `SWEET UFS: "userdata" on LUN 0: first block 0x2b8c00, 109643 MiB, read-only` -> `BSD root: ufsroot0, major 1, minor 0` -> `hfs: mounted SweetRoot on device b(1, 0)` -> `SWEET: root volume is not authenticated (error 25); continuing unsealed` -> `load_init_program ... /sbin/launchd` -> `*** SWEET userspace: init running as PID 1 ***` -> heartbeat (ran for minutes unattended). userdata currently holds the 8 MB `research/root-hfs.img`. NEXT: build a multi-GB HFS+ image with the iOS 16 (iPhone X 20H392) userland (OS rootfs + SystemOS cryptex contents incl. dyld shared cache at /System/Library/Caches/com.apple.dyld; preserve modes/owners/symlinks; decompress LZBITMAP via apfs-fuse), flash it to userdata (sparse, needs user OK), then try Apple's dyld/launchd. Driver is read-only (root mounts RDONLY), fine for first launchd attempts.
- **userdata FLASHED with the 8 MB HFS test volume** (user said "flash it", 2026-10-15 19:53:17 UTC, `research/flash-userdata-hfs-test.log`: `fastboot flash userdata research/root-hfs.img` OKAY; pre-checks: one sweet device, partition-size:userdata 0x1AC4BFB000, partition-type f2fs, image fsck OK, SHA256 3626ea69...). Android userdata is now destroyed (expected/approved). Boot 0028u at 19:53:20 (`research/boot0028u-hfs.log`), photo IMG_20261015_215541: `BSD root: ufsroot0` -> **`hfs: mounted SweetRoot on device b(1, 0)` from internal UFS** -> panic `rootvp not authenticated after mounting @bsd_init.c:931` (arm64 macOS-config requires FSIOC_KERNEL_ROOTAUTH sealed root for non-ramdisk roots). Patch **0029** (`dd1c284`): SWEET logs `SWEET: root volume is not authenticated (error N); continuing unsealed` instead of panicking (Apple configs keep the panic; pivot_root still requires auth). CI **`38797924912`** running. Next: download out-0029, phone image with sweet-0028.adt + rd=ufsroot0 (no RAM disk), boot -> expect init from UFS.
- **UFS ROOT DRIVER VERIFIED ON HARDWARE (read-only).** 0028 CI `38796139570` PASSED, `xnu/out-0028` SHA256 `8b981640...9da6`; QEMU HFS RAM-disk regression `research/q0028-hfs` still runs init. Phone boot 2026-10-15 19:50:24 UTC (`research/boot0028u.log`, image `shim/out/shim-boot-0028u.img`, phone ADT `shim/out/sweet-0028.adt` with /sweet-ufs, NO RAM disk, `rd=ufsroot0`), photos IMG_20261015_215151/215220: `SWEET UFS: "userdata" on LUN 0: first block 0x2b8c00, 109643 MiB, read-only` -> `BSD root: ufsroot0, major 1, minor 0` -> `hfs_ValidateHFSPlusVolumeHeader: unknown Volume Signature : f188` (Android-encrypted data, as expected) -> `cannot mount root, errno = 19`, kernel retries mountroot (no panic). Nothing written to flash. NEXT (destructive, needs user confirmation right before): `fastboot flash userdata research/root-hfs.img` (8 MB HFS with test init) then boot rd=ufsroot0 -> expect init from internal flash.
- **PATCH 0028 (`33aceac`): XNU read-only UFS root device**, CI **`38796139570`** running (next artifacts xnu/out-0028, research/bt29, run29.log). `bsd/dev/sweet_ufs.c`: reuses ABL's UFSHCI state (like the shim probe), takes over UTRL at a kmem_alloc_contig region (DMA layout: UTRL 0x0, UCD 0x1000, 1 MiB bounce 0x4000), verifies UTRLBA readback before any doorbell, IE=0 polled, one SCSI cmd at a time on LUN0 (TUR x3, READ(10) via bounce, PRDT 256 KiB chunks), flush_dcache64 by PA around each command (host not dma-coherent per DT), finds GPT partition by name (`ufsroot=` boot-arg, default `userdata`), exposes `/dev/ufsroot0`/`rufsroot0` (512-byte logical sectors, physical 4 KiB, DKIOC* ioctls), refuses writes (EROFS). IOKitBSDInit: `rd=ufsroot0` -> sweet_ufs_rootdev() (lazy init) else panic. ADT: `tools/mkadt.py` adds `/sweet-ufs` reg <0x1d84000 0x3000> for the PHONE only (not --qemu). Local compile OK, imports resolve. Sandbox research/bt28 (pre0028 originals). FIRST PHONE TEST PLAN (non-destructive): boot 0028 with phone ADT + `rd=ufsroot0` and NO RAM disk: expect `SWEET UFS: "userdata" on LUN 0: first block 0x2b8c00, 109643 MiB` + `BSD root: ufsroot0`, then root mount failure (userdata is still Android-encrypted) -> panic. That validates the driver before flashing an HFS image into userdata (needs explicit user confirmation at that time).
- **SUPERSEDES the 64 GiB iosroot GPT plan: user said "u can delete android" (2026-10-15).** Use the existing `userdata` partition (LUN0 sda34, 4K LBA 0x2B8C00, 0x1AC4B MiB ~107 GiB) directly as the iOS root: NO GPT changes. Keep bootloaders, recovery (OrangeFox), modem/persist/fsg/modemst untouched. Write the HFS image later with `fastboot flash userdata` (sparse, auto-split under the 768 MiB limit). Android will no longer boot normally (expected; reinstallable). Order: XNU UFS driver first, read-only against the current GPT; flash only once it can locate userdata. Nothing erased yet.
- **DECIDED (user, 2026-10-15): 64 GiB `iosroot` on LUN0 (sda), taken from userdata (wipes Android user data; Android/super kept).** Planned GPT (4K LBAs): userdata 0x2B8C00..0xD7D6FF (~43 GiB, keep type/unique GUIDs and attributes); iosroot 0xD7D700..0x1D7D6FF (0x1000000 blocks = 64 GiB, 1 MiB aligned); backup GPT area unchanged. Procedure: user backs up phone data -> boot OrangeFox recovery (adb) -> back up GPT (sgdisk --backup + raw dd of LBA 0-5 and last 6 blocks) to research/ -> sgdisk edit -> Format Data -> verify Android boots to setup. NOT EXECUTED YET.
- **INTERNAL UFS WORKS FROM THE SHIM (read-only), user authorized internal-UFS approach incl. flashing (2026-10-15, "i allow everything").** Shim probe `shim/ufs.c` (commit `12ed3ed` + filter): ufshc@1d84000 is UFSHCI 2.1 (ver 0x210, cap 0x1587031F, 32 slots), ABL leaves HCE=1, HCS=0x10F (device present, lists ready, UIC ready); probe takes over UTRL at its own buffer (verifies UTRLBA readback before any doorbell), TEST UNIT READY/READ CAPACITY/READ(10) all succeed. LUN0 = 0x1D7D800 x 4 KiB (~126.6 GB), valid GPT (64 entries at LBA 2). Photos IMG_20261015_212916/213325/213429. Big LUN0 partitions (start in 4K LBAs / MiB): super 0xCA00/0x2200 (8.5 GiB), logdump 0x22CA00/64, minidump 0x230A00/128, rawdump 0x238A00/128, recovery 0x240C00/128, cache 0x248C00/384 ext4, exaid 0x260C00/384, cust 0x278C00/1024 ext4, **userdata 0x2B8C00/0x1AC4B MiB (~107 GiB), fs unreadable = encrypted (metadata encryption)**. cache..cust contiguous = only 1.75 GiB (too small for iOS ~10+ GiB). Plan needing user consent: shrink userdata in GPT (wipes Android data) and add an `iosroot` partition at the end of LUN0. LUNs 1-5 not listed yet (sdb..sdf backed up in backup/lun).
- **fastboot limit measured (2026-10-15, read-only getvar):** `max-download-size: 805306368` (768 MiB); `max-fetch-size` unsupported; `is-userspace: no` (ABL fastboot). A `fastboot boot` image (shim+kernel+RAM disk) must be < 768 MiB, so the 2.5 GiB iOS shared cache cannot ride in the boot RAM disk even if XNU gets all RAM. Real userland needs storage access (UFS driver, or USB host) or a much smaller cache. Unlocking full RAM is still needed later (GUI).
- **iOS 16 USERLAND SOURCE (Claude, 2026-10-15).** Chose **iPhone X (iPhone10,3/10,6, D22/D221AP)** iOS **16.7.16 (20H392)** over iPhone 8: same A11 (no PAC -> plain arm64, runs on Kryo 470/ARMv8.2), last iOS for A11; X userland is home-button-less and tall-screen (1125x2436 vs sweet 1080x2400), better fit for later GUI. Note the X has its OWN SystemOS cryptex (different digest from iPhone 8's). IPSW URL in `research/ipsw-x/URL.txt` (+ BuildManifest). Images on the user's external SSD (NOT in git, do not format that disk: it holds the user's photos): `/run/media/dipa/android/ios-sweet-ipsw/iPhone10,3_16.7.16_20H392/` — `087-86593-047.dmg` = Cryptex1,SystemOS (2,743,074,816 B), `087-86698-044.dmg` = OS rootfs (4,730,814,044 B), both zip CRC-32 verified, plus Firmware/*.root_hash/.trustcache/.mtree. AppOS cryptex is 087-86715-047.dmg (10 MB, same as iPhone 8).
  - Images are raw APFS; files use LZBITMAP (decmpfs type 14). 7z cannot decode. Tools: `ipsw` 3.1.738 (AUR ipsw-bin, user-approved) needs apfs-fuse on Linux; **apfs-fuse** built in user space (system cmake broken: cmake 4.4.4 wants libjsoncpp.so.27, jsoncpp 1.9.6 installed = partial upgrade, NOT fixed) with pip cmake + `-DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DCMAKE_CXX_FLAGS="-include cstdint"`, installed to `~/.local/bin/apfs-fuse` (+apfs-dump-quick). Mount via a comma-free symlink (apfs-fuse splits options on ',' in `iPhone10,3`; exFAT has no symlinks -> put link elsewhere): `apfs-fuse LINK/087-86698-044.dmg MNT` -> `MNT/root/...`; unmount `fusermount3 -u MNT`.
  - Verified from headers: `dyld_shared_cache_arm64` magic `dyld_v1   arm64`; `/sbin/launchd`, `/usr/lib/dyld` = cputype 0x100000c subtype 0 (plain arm64). libSystem exists only inside the cache.
  - **BLOCKER for real userland via RAM disk:** shared cache = 3.10 GiB in 44 files (~2.5 GiB without the 592 MB `.symbols`), but the kernel manages only 1.20 GiB (0xb0000000..0xfd000000). Options: (A) give XNU the phone's full ~6 GB (banks 0x80000000+2G and 0x100000000+0xfcc00000, carve-out holes need pmap support) AND check fastboot max-download-size for a multi-GB boot image; (B) storage driver (Qualcomm UFS) to read a root from flash (no flashing allowed: would need a file/partition strategy); (C) run against individual dylibs extracted from the cache (uncertain).
- **MILESTONE ON HARDWARE: HFS+ ROOT FILESYSTEM -> PID 1.** Boot 2026-10-15 18:22:12 UTC (`research/boot0027b.log`, image `shim/out/shim-boot-0027b.img`), photo `IMG_20261015_202334.jpg`: `BSD root: md0` -> `hfs: mounted SweetRoot on device b(1, 0)` -> `load_init_program: attempting to load /sbin/launchd` -> `*** SWEET userspace: init running as PID 1 ***` -> repeated `SWEET init: still alive`, no panic. Kernel 0027 (built-in Apple OSS HFS + BearSSL MD5), init with SP alignment fix. NEXT: real iOS 16 userland on the HFS image (dyld, libSystem/dyld shared cache, launchd). Known gaps: entitlements (none granted), SHA-1/SHA-384/512 providers, no storage driver (RAM disk only), root mounted read-only.
- **PHONE HFS ROOT (0027) + SIGBUS ROOT-CAUSED.** Phone boot 2026-10-15 17:49:06 UTC (`research/boot0027.log`, photo `IMG_20261015_200031.jpg`): `hfs: mounted SweetRoot on device b(1, 0)` (HFS works on hardware), init printed its first line, then `pid 1 exited -- exit reason namespace 2 subcode 0xa` = SIGNAL/SIGBUS -> `initproc failed to start` panic. Diagnostic boot 18:08:13 UTC (`research/boot0027d.log`, image `shim/out/shim-boot-0027d.img`, diag init `research/diag-init` from scratch diag-init.S with [a][b][c] markers, `cs_debug=1`; photo `IMG_20261015_201547.jpg`): output `PID [a][b]` then SIGBUS -> fault at first `strb w21,[sp]`; no code-signing messages. Cause: kernel enters a static binary with sp at argc, not necessarily 16-aligned (depends on arg/apple string lengths, differs mockfs vs HFS); EL0 SP alignment check -> EXC_ARM_SP_ALIGN -> SIGBUS (sleh handle_sp_align). QEMU does not enforce SP alignment. NOT a kernel bug: real binaries start in dyld which aligns. Fix `1a8fc15`: sweet-init aligns sp at entry. Rebuilt `research/root-hfs.img`, QEMU `research/q0027-hfs2` OK. Phone image `shim/out/shim-boot-0027b.img` SHA256 `098ba46c...c5c` (payload-0027b, ramdisk match check-0027b) ready, awaiting FASTBOOT. Lesson: Assembly `;` is a comment in Apple arm64 asm (use .macro, not ;-joined #define).
- **HFS ROOT WORKS (QEMU).** 0027 CI `38779441895` PASSED, `xnu/out-0027` SHA256 `a8643886...5f6a`. QEMU `research/q0027-hfs` (RAM disk = `research/root-hfs.img`, rd=md0): `BSD root: md0` -> `hfs: mounted SweetRoot on device b(1, 0)` -> `load_init_program: attempting to load /sbin/launchd` -> `*** SWEET userspace: init running as PID 1 ***` + heartbeat, no panic. Phone image `shim/out/shim-boot-0027.img` (payload-0027 = 0027 kernel + sweet-0021.adt + root-hfs.img + rd=md0, ramdisk byte-match check-0027) ready; awaiting FASTBOOT for phone test.
- **HFS ROOT WORK (Claude), patches 0026-0027.**
  - 0026 (`f0e990c` + link fix `64c96f4`): Apple OSS **hfs-627.100.6** (commit `31d5ec238dfab485e78a9a30b8b92d13e8914f03`, paired with xnu-8796.141.3 in macos-135 release.json) staged by `xnu/patches/0026-stage-hfs.sh` into `bsd/sweet_hfs` (core + hfs_encodings; AppleKeyStore include/key prototypes guarded by CONFIG_PROTECT; SDK TargetConditionals copied). New config option `sweet_hfs` (MASTER + MASTER.arm64.sweet); 40 `optional sweet_hfs` files; Makefile.template foreach adds `_CFLAGS_ADD = -include sweet_hfs_compat.h -I...` (MUST come after kernel -D flags; compat undefs BSD/XNU_KERNEL_PRIVATE and the CONFIG_* HFS tests so kext-config.h decides: macOS profile, no content protection). `sweet_hfs_iokit.c` replaces hfs_iokit.cpp/hfs_encodings_kext.cpp: `sweet_hfs_register()` called in bsd_init after vfsinit (encodings init, vfs_fsadd VFS_TBLCANMOUNTROOT, zones, sysctls); is_ejectable 0, iterate_media none, serial KERN_NOT_SUPPORTED, OSKextGetCurrentLoadTag -> kOSKextInvalidLoadTag (renamed via compat macro). hfs_encodings' own `hfs_allocated` renamed per object (separate kexts on Apple; first CI `38777325964` failed on that duplicate at link). mockfs now validates Mach-O magic (its TODO) so non-Mach-O roots fall through to HFS (new fs entries come AFTER mockfs in vfsconf). CI `38778133720` PASSED, `xnu/out-0026` SHA256 `0b49170c...701a`, prints `SWEET HFS: hfs-627.100.6 registered`.
  - HFS+ image: `research/root-hfs.img` (8 MB, mkfs.hfsplus from AUR hfsprogs installed with user approval; loop-mounted with sudo; /sbin/launchd = research/sweet-init, /dev; fsck.hfsplus OK). QEMU `research/q0026-hfs`: `BSD root: md0` then data abort in MD5Init from hfs_getvoluuid (mount computes volume UUID).
  - 0027 (`14bf2b7`): 0020 stager also copies BearSSL hash/md5.c + codec/dec32le.c/enc32le.c; `corecrypto_md5.c` SWEET branch converts MD5_CTX <-> br_md5_context around br_md5_* calls; wrappers sweet_md5.c/sweet_dec32le.c/sweet_enc32le.c. Host test 40/40 match md5sum. CI **`38779441895`** running.
  - Local tooling: `tools/xnu-cc.py` has `XNU_CC_POST` (flags after logged ones). Sandbox `research/bt28/xnu` = 0025 CI tree + 0026/0027 edits; originals `research/pre0026`, `research/pre0027`. HFS local objects `research/hfs-objs`. Checker entries updated to bt28.
  - SHA-1 / SHA-384/512 still have no provider.
- **MILESTONE ON HARDWARE: USERSPACE PID 1 RUNS ON THE PHONE.** Boot 2026-10-15 17:16:00 UTC (`research/boot0025.log`: send OKAY0.410s, boot OKAY0.135s), image `shim/out/shim-boot-0025.img` SHA256 `9dbfa0b1...89db0`. Photo `IMG_20261015_191733.jpg`: `BSD root: md0` -> `load_init_program: attempting to load /sbin/launchd` -> `*** SWEET userspace: init running as PID 1 ***` -> repeated `SWEET init: still alive` (5 s heartbeat), no panic. Kernel 0025 + mockfs RAM disk + built-in no-entitlements AMFI. No flashing performed.
- **NEXT (toward real iOS userland):** real root filesystem with real binaries. Options: (a) build Apple OSS `hfs` (macOS 13.5 tag `hfs-627.100.6`) into SWEET like libpthread, then an HFS RAM disk image; (b) iOS 16 dyld + libSystem/dyld shared cache from the IPSW (needs APFS or repacking onto HFS). Expected hurdles: entitlements (sweet_amfi grants none), SHA-1/MD5/SHA-384/512 providers (BearSSL), missing kexts/daemons. Current init is a static test program, not launchd.
- **MILESTONE: USERSPACE RUNS (QEMU).** 0025 CI `38774788048` PASSED, `xnu/out-0025` SHA256 `5496069b...4877`. QEMU `research/q0025-rd` (150 s, no panic): `BSD root: md0` -> `load_init_program: attempting to load /sbin/launchd` -> `*** SWEET userspace: init running as PID 1 ***` -> `SWEET init: still alive` every 5 s. Exec, ad-hoc SHA-256 code signature, syscalls, devfs /dev/console, select timeouts all work. Phone image prepared: `shim/out/shim-boot-0025.img` 16,515,072 bytes SHA256 `9dbfa0b15140c0bd733a16c4f727f6a7df44a8741f98d8e266d5f2fa4f689db0` (payload-0025 = 0025 kernel + sweet-0021.adt + research/sweet-init + rd=md0; ramdisk byte-match check-0025). Waiting for user to put phone in FASTBOOT.
- **0024 CI `38773277811` PASSED**, `xnu/out-0024` SHA256 `a0ba964b...4348`. QEMU `research/q0024-rd` and **PHONE (boot 2026-10-15 17:05:55 UTC, `research/boot0024.log`, image `shim/out/shim-boot-0024.img` SHA256 `cf3dac86...6964`, 16,510,976 bytes, payload `shim/out/payload-0024.bin` = 0024 kernel + `shim/out/sweet-0021.adt` + RAM disk `research/sweet-init` + rd=md0; ramdisk byte-match `check-0024`)** agree: `Added memory device md0`, `BSD root: md0`, `load_init_program: attempting to load /sbin/launchd`, then data abort in accelerate_entitlement_queries (PC 0x...77d2458, FAR 0x1a0) = NULL AMFI interface. Photo `IMG_20261015_190715.jpg`. RAM disk root is physically verified.
- **0025 (`2518c79`)**: new `bsd/kern/sweet_amfi.c` registers a built-in AMFI interface at EARLY_BOOT/MIDDLE: no entitlements (adjustContextWithoutMonitor succeeds without creating a context, queries KERN_DENIED, copies NULL/KERN_NOT_FOUND, get_xml/transmuted false); WithMonitor KERN_NOT_SUPPORTED; OSEntitlements_query and query_context_to_object panic explicitly (CoreEntitlements closed; no kernel caller); TrustCache version 0 (0015 keys on trust_cache_rt==NULL, img4 absent -> still unavailable); CoreEntitlements table zero (PMAP_CS only). Compiles locally; checker updated (bt27 entries). CI **`38774788048`** running. Next artifacts `xnu/out-0025`, `research/bt29`, `research/run29.log`. Real iOS binaries will need real entitlements later (no OSS CoreEntitlements exists).
- **0021-0024 RAM-disk-root iteration (Claude), QEMU only so far, no new phone boot since 0020.** Each kernel tested with `tools/mkpayload.py KERNEL research/q0021.adt OUT --ramdisk research/sweet-init --cmdline "debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam -noprogress rd=md0"` then `tools/qemu-sweet.py OUT DIR --secs 150 --kernel KERNEL --fail-on-panic` (PATH needs ~/swift/usr/bin for llvm-nm). Fresh ADTs: `research/q0021.adt` (QEMU), `shim/out/sweet-0021.adt` (phone).
  - 0021 CI `38769532000` PASSED, `xnu/out-0021` SHA256 `2b7500a1...962e`, `research/bt25`/`run25.log`. QEMU `research/q0021-rd`: md0 root, then assert `iomediaClass` in IOService::publishHiddenMedia.
  - 0022 (`20ece9c`, publishHiddenMedia without IOMedia class) CI `38770666158` PASSED, `xnu/out-0022` SHA256 `a4d0e787...30c5`, `research/bt26`/`run26.log`. QEMU `research/q0022-rd`: data abort in SHA256_Init (NULL g_crypto_funcs) from vm_kernel_addrhash_internal.
  - 0023 (`c8089d1`, libkern SHA256_Init/Update/Final use built-in ccsha256_ltc_di + ccdigest_init/update on SWEET; also serves code-signing SHA-256; SHA-1/MD5/SHA-384/512 still have NO provider - BearSSL from 0020 could supply them later) CI `38771876423` PASSED, `xnu/out-0023` SHA256 `d763fed7...1003`, `research/bt27`/`run27.log`. QEMU `research/q0023-rd`: **mockfs mounted md0, `load_init_program: attempting to load /sbin/launchd`**, then panic `mockfs_fsnode_vnode failed to create fictitious pages ... rvalue = 5` (mockfs.c:351).
  - 0024 (`3293c80`): mockfs used memdev mi_base (4K page number of a VIRTUAL kernel address for IOKit RAMDisk, truncated to 32 bits) << PAGE_SHIFT as a physical address. Now zero-copy pager mapping only when mi_phys (with 4K units); virtual md uses pagein/blockmap/strategy -> memdev bcopy. memdev's own mdPhys path assumes 4K ppnums (unsafe on 16K arm64), so do NOT switch the RAMDisk to physical. CI **`38773277811`** running. Next artifacts `xnu/out-0024`, `research/bt28`, `research/run28.log`.
  - Sandboxes: bt25/bt26/bt27 contain the next patch's edited files; pristine copies in `research/pre0022`..`pre0024`.
- **PATCH 0021 (Claude): RAM disk root via mockfs -> first userspace program.** Commits `9c37771` (initial; CI `38768500280` FAILED: mockfs_fsnode.c kfree_type(mockfs_fsnode_t) typed-alloc static assert; local xnu-cc stubs `__builtin_xnu_types_compatible` so it can't catch this) and `193772f` (fix), CI **`38769532000`** running: https://github.com/dipa-studio/ios-sweet/actions/runs/38769532000. Next artifacts: `xnu/out-0021`, `research/bt25`, `research/run25.log`.
  - Kernel: `config/MASTER.arm64.sweet` FILESYS_BASE += `mockfs` (XNU's built-in FS: root device is itself a Mach-O, served as /sbin/launchd, plus /dev for devfs). Upstream mockfs bit-rot fixed: kalloc_type/kfree_type used the POINTER typedef mockfs_fsnode_t (nodes were 8 bytes) -> `struct mockfs_fsnode`. `IOService::setRootMedia` asserted IOBlockStorageDriver class exists (IOStorageFamily absent): SWEET-only, a missing class means root=NULL (same as IOSetImageBoot); Apple path keeps assert. All 21 patches apply (`research/check-patch-order.py`); 5 TUs compile locally with -DMOCKFS (`research/mockfs-objs`), imports resolve vs 0020 kernel. Sandbox `research/bt24/xnu` now holds 0021 versions of those 3 files; pristine 0020 copies in `research/pre0021`.
  - Tools: `tools/mkpayload.py --ramdisk IMAGE` appends IMAGE as an extra payload segment right after the kernel, moves kernel_end past it (shim unchanged: ADT+boot_args follow it, image stays below topOfKernelData), and adds ADT `/chosen/memory-map` `RAMDisk`=<phys,size>. Boot with `rd=md0`. Without --ramdisk output is byte-identical to existing 0020 QEMU and phone payloads (verified). `tools/sweet-init.S` + `tools/mkinit.py`: PIC static init (open /dev/console, print PID, heartbeat every 5 s via select, never exits) wrapped into a static arm64 Mach-O (__PAGEZERO, __TEXT@0x100000000, LC_UNIXTHREAD, ad-hoc SHA-256 CodeDirectory v0x20400, 4K pages). Build: `~/swift/usr/bin/clang -target arm64-apple-ios16.0 -c tools/sweet-init.S -o X.o && tools/mkinit.py X.o research/sweet-init` (ld64.lld cannot link static iOS). Signature not verified by a real codesign; the kernel will tell.
  - QEMU with 0020 kernel + RAM disk (`research/q0020-rd.bin`, rd=md0, 150 s `research/q0020-rd150`): `Added memory device md0`, **`BSD root: md0, major 1, minor 0`** (plumbing works), then the setRootMedia assert (now fixed in 0021). NOTE: QEMU needs >60 s to reach IOFindBSDRoot (60 s run showed nothing after stf0; likely RTC/inittodr wait), so use --secs 150.
  - NEXT: download 0021, QEMU 150 s with ramdisk; expect mockfs mount then init exec -> `*** SWEET userspace: init running as PID 1 ***`. Then phone boot with same payload (phone ADT shim/out/sweet-0020.adt pattern + --ramdisk + rd=md0).
- **0020 PHONE RESULT (user transcription of screen, 2026-10-15): KERNEL INIT COMPLETE, WAITING FOR ROOT.** After Skywalk self-tests PASSED, kminit, ifnet_attach lo0/gif0/stf0, screen prints `BSD`, then `Waiting on <dict><key>IOProviderClass</key><string>IOMedia</string><key>Content</key><string>Apple_HFS</string></dict>` and `Failed to write boot-picker-bringup-reason to NVRAM.` No panic. This is IOFindBSDRoot waiting for a root device (none exists); NVRAM warning is expected (no NVRAM driver). QEMU `cpu_idle` snapshot is presumably the same wait (not GDB-confirmed; milestone GDB run was cancelled by user since phone answered it). Draft `research/check-milestones20.gdb` (hbreaks inittodr/vfs_mountroot/IOFindBSDRoot/bsd_utaskbootstrap) left uncommitted/ignored.
- **NEXT MILESTONE: root filesystem -> launchd.** Plan: (1) RAM disk: shim places an image in RAM, ADT /chosen/memory-map `RAMDisk` entry, boot-arg `rd=md0` (XNU md driver). (2) HFS is a separate kext on Apple; build Apple OSS `hfs` (tag paired with macOS 13.5 in distribution-macOS macos-135 release.json) into SWEET like libpthread 0019. APFS is closed. (3) Minimal HFS image with iOS 16 launchd (later: dyld/shared cache; AMFI/code-signing absent will be a later hurdle). User's end goal is full iOS GUI.
- **0020 (AES) VERIFIED + PHONE BOOTED (Claude took over after Codex usage limit).** Actions `38765422261` (`ab9e23f`) PASSED; kernel `xnu/out-0020/kernel.development.sweet` checksum OK; buildtree `research/bt24`, log `research/run24.log`. Actual-kernel AES checks PASS (`research/check-aes20.gdb` / `.log`, 12 extra CBC cases match OpenSSL). 45s QEMU `research/q0020`: no panic, zero unknown glyphs, past old TCP/AES panic -> Skywalk self-tests PASSED -> bsd_autoconf kminit -> ifnet_attach lo0/gif0/stf0; final snapshot PC in `cpu_idle` (idle or waiting; NOT yet diagnosed, could be root-device wait). Image `shim/out/shim-boot-0020.img` 16,461,824 bytes SHA256 `775200cb02d95fc750981516b79d91dcdc96184bbe67a38f9d57c59b4a391828`, ramdisk byte-matches `payload-0020.bin` (`check-0020`). **Phone temporarily booted 2026-10-15 16:10:00 UTC**: one FASTBOOT product sweet, send OKAY0.407s, boot OKAY0.134s, total0.549s, exit0 (`research/boot0020.log`). Awaiting user photo; do not reboot the phone before it. NEXT: read photo; diagnose what QEMU waits on after stf0 (GDB backtrace of threads / longer run). Codex's STOP request below is complete.
- User requests STOP after completing the current0020 AES iteration (Actions/QEMU/phone), then leave a precise committed handoff for another AI. User says FASTBOOT ready again after0019 photo. Do not start a new blocker fix after this iteration.
- Goal: iOS16-generation XNU on Redmi Note10Pro sweet/SM7150. Always commit, use gh/Actions for kernel builds, keep this handoff current. Temporary fastboot boot only; preserve Android/backups. No userland/root filesystem boot yet.
- **Patch0020 update:** initial `e71098d` / Actions `38765012466` superseded by scalar-only compile flags. Added -mgeneral-regs-only to all six provider/BearSSL TUs and corecrypto_aes.c; object disassembly now confirms no SIMD. Updated implementation `ab9e23f`, Actions `38765422261` queued/running: https://github.com/dipa-studio/ios-sweet/actions/runs/38765422261. Do not launch another run. portable BearSSL AES CBC and legacy one-block ECB wired directly into SWEET corecrypto_aes.c. Genuine bitslice implementation, no CPU AES/SIMD requirement, heap or fake global crypto table. Source fetched by `0020-stage-bearssl.sh` from official BearSSL git at immutable `7bea48e5e850ab4cafbe68d3765cdaba13a86d6f`; MIT license retained, downloaded source stays out of git. Kernel limits include adapter only. All128/192/256-bit keys, CBC encrypt/decrypt, copied contexts, in-place/out-of-place; zero block count and size overflow handled, invalid keys clear context. Seven TUs compile to arm64 objects (`research/aes-objs`), imports resolve, all20 patches apply and sources match (`research/patch0020-check.log`). Sandbox `research/bt23/xnu`, originals `research/pre0020`. NEXT: Actions then actual-kernel NIST/random CBC/ECB checks and >=45s QEMU before another phone boot. Next artifacts out-0020 / bt24 / run24.log. 0020 updated CI pending. Local sources/checks match the scalar-only patch.
- **Latest built kernel0019**, implementation `256d3f0`, patches0001-0019. Actions `38763072907` PASSED (4m5s): https://github.com/dipa-studio/ios-sweet/actions/runs/38763072907. Kernel `xnu/out-0019/kernel.development.sweet`, SHA256 `a27df7568f03fb541cf0e8024c0a594fa178a85054fcf9eba29158cbd4c5ecc0`; checksum verified. Log/source `research/run23.log` / `research/bt23` (no nested .git). Seven pthread source/build/header files and staged adaptations byte-match local compile inputs.
- **0019 hardware photo received** `IMG_20261015_175306.jpg`: pthread registration visible, passes mbinit and DLIL checksum/scheduling, same AES fault as QEMU: PC`0xfffffe00079174e0` (`aes_encrypt_key128`), LR`0xfffffe000767c3a4` (`tcp_init`), FAR0x78, x8=0. Disassembly proves NULL g_crypto_funcs->ccaes_cbc_encrypt. Photo processed; no more0019 observation pending. General crypto table remains absent, other hash/mode operations may still fault after0020. DO NOT bypass TCP or install fake crypto. XNU already contains SHA256/HMAC implementations; AES source there is a dispatch wrapper. Full future provider interface libkern/libkern/crypto/register_crypto.h. Apple/corecrypto default README describes evaluation-only licensing, so no external corecrypto was fetched or staged; BearSSL selected for this portable AES integration.
- **0019 pthread FIXED in QEMU and observed beyond its init on phone**: 45s QEMU `research/q0019`, zero unknown glyphs, then AES panic. Actual-kernel API checks PASS `research/check-pthread19.gdb` / `.log`, guest `research/q0019-api`: function/callback table identity, actual provider pthread_init returns, locks/global hash/threadcall/typed zones initialized, thread_selfid via syscall shim + buffer bounds, process hash init/delete via shims restores NULL. Monitor quit prints expected remote-disconnect after PASS. All fixture guests stopped.
- **0019 provider**: genuine Apple libpthread-514.100.2 commit `a6c70ca0e544347a0377babf748f831577ec24f9`, exact paired release with xnu8796.141.3 in distribution-macOS/macos-135/release.json (`research/macos-135-release.json`). 0019 shell stage runs before patches (workflow copies *.sh); three SWEET wrapper TUs use kext BSD header view, vm_fault_external, renamed provider-side pthread_kern/current_uthread; register real function table at EARLY_BOOT SECOND, real pthread_init later. Stager applies bounded address casts, zero user addresses, proper panic format. SWEET opaque ksyn storage enlarged48->56 for trailing kwe_uth, checked with provider static assertion. Local pre-CI TargetConditionals fixture was syntax-only; artifact bt23 carries actual SDK header and CI is authoritative.
- **Phone0019 temporarily booted** 2026-10-15 15:51:36 UTC: exactly one FASTBOOT/product sweet verified; send OKAY0.406s, boot OKAY0.134s, total0.546s, exit0 (`research/boot0019.log`). Image `shim/out/shim-boot-0019.img`, 16,457,728 bytes, SHA256 `19429a57e486b856880df9e27327ed488e0139345311fdb0350974e72103a9a1`. Phone ADT/payload `shim/out/sweet-0019.adt` / `payload-0019.bin` timer19, unpacked ramdisk byte-match (`check-0019`). EntryPA0xb146b488, kernelendPA0xb2000000, boot_argsPA0xb2004000/top0xb2008000. Last user FASTBOOT+USB reply preceded this boot; do not assume phone is still in FASTBOOT.
- **CPU0018 physically verified** by `IMG_20261015_173951 (2).jpg`: boot CPU0 registered, real SGI1 verified, initialization complete -> BSD/MAC/mbinit -> old pthread-table panic. SweetCPU uses legacy IOCPU, ml_processor_register/processor_start/initCPU, real SGI1 clears SIGPdisabled before max CPUs completion; no forced flags/skipped waits. CPU APIs and two-CPU rejection passed (`research/check-cpu18.gdb`, `q0018-api`, `q0018-smp`). Single core; SMP/suspend unsupported. CURRENT SWEET has NO USE_APPLEARMSMP.
- QEMU next run: generate fresh `tools/mkadt.py research/q0020.adt --qemu` (timer27), mkpayload with `debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam -noprogress`, then `tools/qemu-sweet.py PAYLOAD OUT --secs 45 --kernel KERNEL --fail-on-panic`. 12s can miss later panics because IORTC waits30s. Runner snapshot only: panic exit2, blank/incomplete exit3; absence of panic does not mean complete boot. Qualcomm XPU/ABL/panel and phone SMC PSCI require hardware checks.
- Local checker `tools/xnu-cc.py research/run23.log research/bt23 FILTER --per-file`, XNU_CC_OBJDIR for objects. For new BearSSL TUs add XNU_CC_EXTRA with -I bt23/xnu/libkern/crypto/sweet_bearssl/{inc,src}. Patch checker `research/check-patch-order.py` uses temporary upstream index; source fixtures/artifacts ignored under research. GDB mask registers to unsigned64, use function-entry manual-call return traps, discard manipulated guests. No QEMU guest intentionally left running.

## Session log and earlier handoffs (superseded by the active summary above)

### Prior 0019 transition notes (superseded)

- Goal: iOS 16 generation XNU on sweet. Always commit completed work, use gh/Actions for kernel builds, keep this handoff current. Temporary fastboot boot only; preserve Android/backups.
- **0019 build PASSED** Actions `38763072907` (4m5s), implementation `256d3f0`. Kernel `xnu/out-0019/kernel.development.sweet`, SHA256 `a27df7568f03fb541cf0e8024c0a594fa178a85054fcf9eba29158cbd4c5ecc0`; checksum verified. Log/source `research/run23.log` / `research/bt23`; all seven patched files and staged provider adaptations match local compile inputs. Prefer bt23 as the next baseline.
- **0019 pthread FIXED in QEMU**: 45s run `research/q0019` registers provider, passes mbinit, DLIL SUM16 checks and DLIL thread scheduling. Actual-kernel GDB checks `research/check-pthread19.gdb` / `.log` PASS: function/callback table identity, real _pthread_init returns, locks/global hash/cleanup threadcall/typed zones non-NULL, thread_selfid via actual syscall shim with output bounds, process hash init/delete through actual shims restores NULL. Guest stopped after tests; no fixture left running. GDB monitor quit prints expected remote disconnect after PASS.
- **Current next blocker:** QEMU0019 panic data abort FAR0x78 at `aes_encrypt_key128` PC`0xfffffe00079174e0`, called by `tcp_init` LR`0xfffffe000767c3a4`. Disassembly confirms `g_crypto_funcs == NULL`, loading ccaes_cbc_encrypt at+0x78. General crypto registration is still absent; DO NOT bypass TCP or supply fake crypto. Next integrate a genuine compatible crypto implementation/provider (AES first needed here, other digest/mode APIs also used). XNU contains SHA256/HMAC but no AES implementation; its corecrypto_aes.c is a dispatch wrapper. Full crypto table is in libkern/libkern/crypto/register_crypto.h.
- **0019 phone image prepared and verified**, user reports FASTBOOT+USB again; exactly one device/product sweet verified. `shim/out/shim-boot-0019.img`, 16,457,728 bytes, SHA256 `19429a57e486b856880df9e27327ed488e0139345311fdb0350974e72103a9a1`; unpacked ramdisk matches phone payload (`shim/out/check-0019`, `payload-0019.bin`, `sweet-0019.adt`, timer19). EntryPA0xb146b488; kernelendPA0xb2000000; boot_argsPA0xb2004000/top0xb2008000. Usual debug cmdline cpus=1/-noprogress. **Temporarily booted 2026-10-15 15:51:36 UTC**: send OKAY0.406s, boot OKAY0.134s, total0.546s, exit0 (`research/boot0019.log`). User asked for photo after45s. Await the photo; DO NOT reboot again before observation. Bootloader acceptance only; no0019 physical progress observed yet.
- **Hardware photo confirms 0018 progress** (`IMG_20261015_173951 (2).jpg`): real phone prints `SWEET CPU: boot CPU 0 registered, SGI1 verified, initialization complete`, enters BSD/MAC, reaches `mbinit: done`, then the same missing-pthread-function-table panic as QEMU at pthread_shims.c:318. CPU completion/interrupt delivery is now physically observed. The photo was received; no further phone boot performed yet.
- **Patch0019 committed/pushed `256d3f0`; Actions `38763072907` queued/running:** https://github.com/dipa-studio/ios-sweet/actions/runs/38763072907. Do not launch a duplicate. genuine Apple OSS libpthread-514.100.2 provider (immutable commit `a6c70ca0e544347a0377babf748f831577ec24f9`), paired with xnu-8796.141.3 by Apple's `distribution-macOS/macos-135/release.json` (`research/macos-135-release.json`). `0019-stage-libpthread.sh` fetches/stages it before patches; workflow now copies shell scripts too. SWEET-only wrappers compile all three real kernel sources, rename provider-side symbols, use kext header view and vm_fault_external, register the real function table at EARLY_BOOT SECOND. Existing pthread_init then runs the actual provider initialization. No pthread wait/syscall is bypassed. Source staging includes bounded explicit address casts/zero user addresses and panic-format fixes. SWEET kernel opaque ksyn storage enlarged from48 to56 bytes to contain this provider's trailing kwe_uth, with a provider size assertion. Local compile of three provider TUs plus pthread_shims/kern_fork passed; imports resolve and provider exports do not collide with existing kernel symbols. All19 patches apply and changed sources match (`research/patch0019-check.log`). Source sandbox `research/bt22/xnu`, originals `research/pre0019`, objects `research/pthread-objs`. Local TargetConditionals fixture only has target macros for syntax; CI stages the real macOS SDK header and is authoritative. Next Actions artifacts: out-0019 / bt23 / run23.log; run QEMU >=45 seconds. 0019 CI is pending; no 0019 QEMU run yet.
- **Latest kernel implementation `e7d9550`, patches0001-0018; CI `38760004398` PASSED (3m56s)**: https://github.com/dipa-studio/ios-sweet/actions/runs/38760004398. No build is pending. Kernel `xnu/out-0018/kernel.development.sweet`, SHA256 `b3c8d59acc88f93a2c836eb2527a05ed4fbaac7c580a2ea8c3b795137f4aadf1`; checksum verified. Source/log `research/bt22` / `research/run22.log` (baseline for patch0019; no nested .git). New driver/config sources match CI exactly.
- **CPU wait FIXED in QEMU**: SweetCPU uses legacy IOCPU, validates single boot CPU, ml_processor_register -> processor_start -> initCPU real SGI1 -> scheduler/IOKit completion -> ml_set_max_cpus. It does NOT force a flag or skip a wait. CPU APIs passed: Running CPU0, processor_array[0] association, SGI signalling enabled, name, unsupported secondary-start error (`research/check-cpu18.gdb` / `.log`, `research/q0018-api`). Single-core only; SMP and suspend unsupported. Two-CPU topology fails explicitly (`research/q0018-smp`).
- **Next blocker reproduced in 45s QEMU** (`research/q0018-long`, zero unknown glyphs): BSD initialization reaches MAC framework, network mcache and `mbinit: done`, then **`pthread kernel extension not loaded (function table is NULL). @pthread_shims.c:318`**. Do not bypass pthread_init: find/integrate the matching open-source libpthread kernel implementation and register its real function table. A 12s run `research/q0018` looked panic-free before the 30s IORTC wait elapsed; use >=45s or GDB checkpoints for the next iteration. No userland/root filesystem boot yet.
- **Phone 0018 TEMPORARILY BOOTED** 2026-10-15 **15:31:15 UTC**: exactly one FASTBOOT device verified product sweet; send OKAY0.400s, boot OKAY0.134s, total0.539s, exit0. Local log `research/boot0018.log`. This confirms bootloader acceptance only. User was asked for a photo; await it, DO NOT reboot the phone again before their observation. No flashing performed.
- Current hardware image `shim/out/shim-boot-0018.img`, **16,437,248 bytes**, SHA256 **`b7a23595d143a76c72c9fe2cfcc5d77a8f16987b5af1a2703bbffdfa6922908c`**. Phone ADT/payload `shim/out/sweet-0018.adt` / `shim/out/payload-0018.bin` (timer19), unpacked ramdisk exactly matches payload (`shim/out/check-0018`). EntryPA0xb146b488; kernelendPA0xb1ffc000; boot_argsPA0xb2000000/top0xb2004000. Command line `debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam -noprogress`.
- QEMU payload/ADT `research/q0018.bin` / `research/q0018.adt` (timer27). Run `python3 tools/qemu-sweet.py research/q0018.bin research/NEW-OUT --secs 45 --kernel xnu/out-0018/kernel.development.sweet --fail-on-panic`; fresh ADT seed for a new payload. Output fb.png/fb.txt/regs.txt/qemu.log/result.json. Visible panic exit2; blank/incomplete decode exit3; no_panic_observed is snapshot-only, not successful boot. -noprogress prevents the graphical indicator corrupting console text. Qualcomm XPU/bootloader/panel and SMC PSCI still need physical validation.
- Patches0014-0017 fixed PRNG registration/direct SHA256, explicit unavailable trust-cache service with rejected loads/no matches, built-in SweetPlatformExpert, and timer PPI from ADT (phone19/default19, QEMU27). All their checks/artifacts are preserved in the history below. CURRENT SWEET has NO USE_APPLEARMSMP; do not assume gCPUIC/gAIC/gPMGR AppleARMSMP globals exist.
- Local single-file checker: tools/xnu-cc.py research/run22.log research/bt22 FILTER --per-file, output via XNU_CC_OBJDIR. Patch checker `research/check-patch-order.py` applies all18 via temporary index, matches sandbox sources. Sandbox for0018 `research/bt21/xnu`, originals `research/pre0018`, objects `research/cpu-objs`. First compiler issues were missing machine/atomic.h and nonexistent getNameSymbol; fixed and both TUs compiled successfully before CI. Fixtures/artifacts under research are local-only/ignored.
- GDB: mask int(register)&((1<<64)-1) for unsigned kernel pointers; use function-entry manual-call return traps, discard manipulated guests. No QEMU fixture is intentionally left running.

### Earlier active handoff snapshot (superseded)


- **0018 milestone:** Actions `38760004398` PASSED (3m56s), checksums passed, new CPU/build files byte-match CI tree. Kernel `xnu/out-0018/kernel.development.sweet`, SHA256 `b3c8d59acc88f93a2c836eb2527a05ed4fbaac7c580a2ea8c3b795137f4aadf1`; log/tree `research/run22.log` / `research/bt22`. QEMU `research/q0018` 12s: boot CPU registered, SGI1 verified, CPU initialization complete, **BSD initialization entered** (copyright, MAC framework, buffer headers), no panic/zero unknown glyphs. Direct CPU API checks PASS (`research/check-cpu18.gdb`, `.log`, `research/q0018-api`): CPU0 Running, processor matches processor_array[0], real SGI enabled, CPU name correct, secondary-start returns KERN_NOT_SUPPORTED. Two-CPU ADT correctly panics before registration (`research/q0018-smp`). Longer 45s run `research/q0018-long` still running; next BSD wait/fault not yet identified.
- **Prepared 0018 phone image:** `shim/out/shim-boot-0018.img`, 16,437,248 bytes, SHA256 `b7a23595d143a76c72c9fe2cfcc5d77a8f16987b5af1a2703bbffdfa6922908c`. Phone ADT/payload `shim/out/sweet-0018.adt` / `shim/out/payload-0018.bin`, usual debug args with cpus=1 and -noprogress. Unpacked ramdisk byte-compared (`shim/out/check-0018`). Entry PA remains 0xb146b488; kernel end PA 0xb1ffc000, boot_args 0xb2000000/top0xb2004000. User reports FASTBOOT+USB ready; read-only check found exactly one product sweet. NEXT: temporary fastboot boot of this verified image, record send/boot results, then await hardware photo without rebooting again.
- Patch 0018 committed/pushed **`e7d9550`**; Actions **`38760004398`** queued/running: https://github.com/dipa-studio/ios-sweet/actions/runs/38760004398. Do not launch a duplicate run.
- Active continuation: patch **0018** implemented in `iokit/Kernel/arm/SweetCPU.cpp` + arm64 source list + exact qcom,kryo470 personality. Keeps legacy IOCPU, accepts ONLY the single boot CPU, fills ml_processor_info from parsed topology with CPU object as cpu_id, calls ml_processor_register and processor_start. initCPU sends SGI1 via ICC_SGI1R_EL1 and waits (1-second deadline) for real cpu_signal_handler to clear SIGPdisabled. Only after successful startup calls ml_cpu_init_completed/cpusRunning and publishes completion/max CPUs. Secondary startup/suspend are explicitly unsupported. Local C++ compile passed for both TUs (`research/cpu-objs`), all imports resolve, object contains dsb ishst / ICC_SGI1R / isb; all18 patches apply in order and match sources. Sandbox `research/bt21/xnu`, originals `research/pre0018`; next CI artifacts should use `xnu/out-0018`, `research/bt22`, `research/run22.log`. User has the phone available; first run QEMU, then prepare/temporarily boot useful hardware progress.
- Goal: iOS 16 generation XNU on Redmi Note 10 Pro / sweet. User wants persistent progress, commits, kernel builds via `gh` Actions, and this handoff kept current across agent switches. Temporary `fastboot boot` only; preserve Android and backups.
- Latest kernel implementation: **`aa3f991`**, patches **0001-0017**. All four new Actions builds PASSED: 0014 `38748543058` (4m0s), 0015 `38749549779` (4m3s), 0016 `38750733996` (4m3s), 0017 **`38751507437` (4m7s)**. Latest: https://github.com/dipa-studio/ios-sweet/actions/runs/38751507437. No build is pending.
- **Current blocker: CPU initialization has no SWEET CPU driver.** QEMU registers SweetPlatformExpert, then kernel_bootstrap_thread waits in **kperf_init_early -> ml_wait_max_cpus**. Confirmed via actual-kernel GDB call stack (`research/locate-cpu-wait2.log` / `.symbols`) and normal-run `max_cpus_initialized == 2` (MAX_CPUS_WAIT). Do not force the flag or remove the wait. Next implement real CPU registration and completion using XNU's CPU/processor interfaces. CURRENT SWEET uses legacy IOCPU (`USE_APPLEARMSMP` is absent); enabling AppleARMSMP is a separate architectural change requiring GIC/PMGR services. No userland/root filesystem boot yet.
- Fixed this session: PC=0 unregistered PRNG callback (0014, built-in HMAC-SHA256 provider + direct entropy/write_random hashing); absent Image4/AMFI trust-cache service (0015, unavailable runtime, loads rejected and queries no-match); missing platform driver (0016, SweetPlatformExpert exact personality); incorrect QEMU timer IRQ (0017, validated ADT PPI property, phone default19/QEMU27).
- **Latest kernel** `xnu/out-0017/kernel.development.sweet`, SHA256 `055a80190ab998b4df9203f1102072dcc78faad1779a537a514e522b682b582f`. Buildtree/log **`research/bt21` / `research/run21.log`**; all nine changed C/C++/header/config files byte-match local checked sources. Checksums passed. Entry PA `0xb146b488`, kernel end PA `0xb1ff4000`. Preferred baseline for patch 0018: `research/bt21/xnu` (no nested .git).
- **QEMU verified**: `research/q0017-noprogress` ran **30 seconds**, no visible panic, **zero unknown glyphs**, IRQ exceptions returned normally (4 IRQs, tickless idle). It still waits for CPU completion, so this is NOT a completed boot. Earlier 15s run `research/q0017` captured 122 IRQs, timer value27, GICR_ISENABLER0 `0x08000002`, and CPU WAIT; graphical progress overlay corrupted 13 glyphs. Add **`-noprogress`** to keep the console readable. New runner classifies incomplete/blank decoding explicitly (exit3 with --fail-on-panic), visible panic exits2. Snapshot-only; use regs/GDB to diagnose stalls.
- Current QEMU payload/ADT: **`research/q0017-noprogress.bin` / `research/q0017.adt`**. Run: `python3 tools/qemu-sweet.py research/q0017-noprogress.bin research/NEW-OUT --secs 30 --kernel xnu/out-0017/kernel.development.sweet --fail-on-panic`. Generate fresh seed with mkadt for a new payload. QEMU virt models generic ARM execution, not Qualcomm XPU/bootloader/panel or the phone's SMC PSCI conduit.
- **Prepared phone image**: **`shim/out/shim-boot-0017.img`**, 16,416,768 bytes, SHA256 `51ff7fe30b4a6668c3452ffe1da922c5ac30cb8de60625c2a652587ecbd0ec92`. Phone ADT/payload `shim/out/sweet-0017.adt` / `shim/out/payload-0017.bin` (timer19). Unpacked ramdisk exactly matches payload (`shim/out/check-0017`). Command line **`debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam -noprogress`**. NOT sent to phone this session: known CPU-driver wait should be addressed in QEMU first. Last actual phone boot remains 0013; user's latest photo `IMG_20261015_160033.jpg` confirmed the old PRNG PC=0 panic.
- Direct QEMU/GDB API checks: PRNG 600-byte chunking, buffer bounds, changing output, zero-length reads/writes, user reseed, contended refresh, generator1 init/output PASS again on latest0017 (`research/check-prng17.gdb` / `.log`, guest `research/q0017-api`). Trust-cache unavailable-service/argument/output cases PASS on0015 (`research/check-trustcache.gdb` / `.log`). Platform registration + target/product normal/truncated/zero/null/bounds PASS on0016 (`research/check-platform.gdb`, `research/check-platform3.log`). Different platform ID correctly retains IOPanicPlatform fallback (`research/q0016-negative`). Timer PPI32 and size2 correctly panic (`research/q0017-badppi`, `research/q0017-badsize`); omitted property selects19 (`research/q0017-default`). These are API/bring-up checks, not crypto certification or SMP scheduling validation.
- Local checker **`research/check-patch-order.py`** verifies all17 patches and changed source equality using a temporary upstream git index. Fixtures/logs/artifacts under research are local-only and ignored. For GDB unsigned kernel pointers, mask `int(register_value) & ((1<<64)-1)`; x30/x29 may be rendered signed. Stop at a function entry for manual-call return traps, and discard each manipulated guest after API tests. All fixture QEMU guests have been stopped.


- User wants persistent progress toward iOS 16, commits for completed changes, builds through `gh` / GitHub Actions.
- Keep this file current at every milestone so another agent can resume immediately, including when usage limits interrupt a session.
- Patch 0017 committed/pushed `aa3f991`, Actions `38751507437` running: https://github.com/dipa-studio/ios-sweet/actions/runs/38751507437. Next artifacts: xnu/out-0017, research/bt21, research/run21.log. Do not duplicate.
- Patch 0016 kernel downloaded/checksum verified: SHA256 `d06336c54baa06e0df6561a8bd7df98a9b9f7502c9381c62d1a44c045cd1ce46`, `xnu/out-0016/kernel.development.sweet`; buildtree/log `research/bt20` / `research/run20.log`. QEMU `research/q0016` (10s) prints platform expert registered, zero unknown glyphs, no panic observed BUT stalls (timer mapping still wrong until 0017). Direct actual-kernel GDB tests passed for registered instance and target/product names, including maxLength=1/0 and NULL, sentinels intact (`research/check-platform.gdb`, `research/check-platform3.log`, `research/q0016-api3`). First two fixture attempts used premature/wrong return breakpoints; discarded, corrected fixture uses start-return observation then a function-entry return trap. No phone boot yet.
- Patch 0016 CI `38750733996` PASSED (4m3s); artifacts not yet downloaded/booted. Patch 0017 prepared to fix QEMU timer fidelity BEFORE interpreting future no-panic/stall runs: actual `qemu-system-aarch64 -M virt,gic-version=3,dumpdtb=research/qemu-virt.dtb ...` timer property has virtual PPI 11 => INTID 27, while phone uses INTID 19. Kernel formerly hardcoded 19. New optional /arm-io/gic virtual-timer-intid property selects the PPI (validate exact u32 and 16..31); missing property retains phone default 19. One RO-late global drives GIC enable and sleh_irq dispatch. tools/mkadt.py emits phone19/QEMU27. Both C TUs compile (`research/timer-objs`), ADT serialize/parse checks confirm values/addresses, all 17 patches apply and match. Sandbox `research/bt19/xnu`, originals `research/pre0017`; initial local sleh compile failed due read-only exported header not updated, fixed export and BOTH recompiled successfully. CI exports normally.
- Architecture correction for next agent: CURRENT SWEET board_config does NOT define USE_APPLEARMSMP; it compiles the legacy IOCPU path, not cpu_boot_thread/IOPMGR AppleARMSMP. Existing roadmap mentions AppleARMSMP as a future approach. Do not look for gCPUIC/gAIC/gPMGR globals in the current kernel: they are absent. Determine the actual CPU-init wait after platform registration before choosing the next driver architecture.
- Patch 0016 committed/pushed as `0dcdf5c`; Actions `38750733996` running: https://github.com/dipa-studio/ios-sweet/actions/runs/38750733996. Next artifacts: `xnu/out-0016`, `research/bt20`, `research/run20.log`.
- Patch 0016 implemented: new `iokit/Kernel/arm/SweetPlatformExpert.cpp`, arm64 source list, built-in personality in KernelConfigTables.cpp guarded by ARM64_BOARD_CONFIG_SWEET. Matches only xiaomi,sweet at score 10000, keeps IOPanicPlatform fallback for other hardware. Uses IODTPlatformExpert base initialization/power domain and createNubs CPU logical-ID annotation; overrides top-level publishing because base requires nonexistent Apple NVRAM /options. Publishes real CPU/top-level nodes, provides bounded target/product names, and registers the platform service. GIC/PMGR and arm-io child-bus drivers remain separate work. Both C++ TUs compile (`research/platform-objs`), all imports resolve against 0015/own objects, all 16 patches apply and sources match. Sandbox `research/bt19/xnu`; originals `research/pre0016`. NEXT: full Actions/QEMU; inspect CPU boot waits after the platform registers, do not equate absence of panic with successful boot.
- Patch 0015 CI `38749549779` PASSED (4m3s), checksum verified. Kernel `xnu/out-0015/kernel.development.sweet`, SHA256 `ca1b424a596c7058550ad1659080a333e7643270f019656401d80bf2b876645f`; buildtree/log `research/bt19` / `research/run19.log`. QEMU `research/q0015` (10s, zero unknown glyphs) passes trust-cache handling and machine lockdown, then panics `Unable to find driver for this platform: "xiaomi,sweet" @IOPlatformExpert.cpp:2319` (IOPanicPlatform fallback). Next concrete work: add a built-in SWEET IODTPlatformExpert personality/class; keep the fallback for mismatched platforms. No phone boot yet.
- Direct trust-cache API checks PASSED in the actual 0015 kernel under QEMU/GDB (`research/check-trustcache.gdb`, `research/check-trustcache.log`, `research/q0015-api`): runtime pointers NULL, hash/UUID queries return NOT_FOUND, typed/untyped/legacy loads return NOT_SUPPORTED, capabilities outputs zero and bounds preserved, invalid-argument cases still reject. Second PRNG check also verifies contended refresh returns immediately (`research/check-prng2.log`, `research/q0014-api2`).
- Patch 0015 committed/pushed `8f851d4`, Actions run `38749549779` running: https://github.com/dipa-studio/ios-sweet/actions/runs/38749549779. Do not duplicate.
- Direct PRNG API checks passed in the REAL 0014 kernel under QEMU/GDB, stopped before trust-cache init (`research/check-prng.gdb`, log `research/check-prng.log`, guest `research/q0014-api`). Invoked read_random for 600 bytes (chunking and buffer sentinel intact), repeated output differed, zero-length read/write succeeded, write_random(64-byte input) succeeded, secondary generator 1 initialized and generated distinct output. QEMU log has no exceptions during these checks; guest was discarded after the tests. This tests API behavior, not a cryptographic certification or SMP scheduling.
- Patch 0015 implemented in `bsd/kern/kern_trustcache.c`: SWEET with missing Image4/AMFI marks both runtime pointers NULL and logs service unavailability. Existing static loader handles NULL. Public load APIs return KERN_NOT_SUPPORTED; hash/UUID queries return KERN_NOT_FOUND; capabilities outputs are zero with KERN_NOT_SUPPORTED. Invalid-input checks remain, and Apple paths/available-provider initialization retain existing behavior. No trust is granted. Local arm64 compile passed (`research/trustcache-objs`), all 15 patches apply and sources match. Sandbox `research/bt18/xnu`, baseline `research/pre0015`. Next: Actions/QEMU and direct unavailable-service API checks using GDB.
- Patch 0014 CI `38748543058` PASSED (4m0s), artifact checksum passed. Kernel `xnu/out-0014/kernel.development.sweet`, SHA256 `741de20c851755d333759d7e668346f3edb4f325efac4cc7c142d80d1f5ff75c`; buildtree/log `research/bt18` / `research/run18.log`. QEMU run `research/q0014` (10s, zero unknown glyphs) prints `SWEET PRNG: HMAC-SHA256 registered`, passes commpage initialization, loads vnguard policy, THEN panics `image4 interface not available @kern_trustcache.c:253`. PC=0 fault FIXED IN QEMU. No new phone boot performed.
- Next work: SWEET currently has neither AppleImage4 nor AMFI. `trust_cache_runtime_init` unconditionally requires both; unlike BCM2837, SWEET enters this startup path. Investigate an explicitly unavailable trust-cache runtime with rejected loads/no query matches while providers are absent; preserve all Apple-platform checks. Merely skipping the startup call would leave later AMFI/IMG4 dereferences unsafe. Existing load_static_trust_cache already handles trust_cache_rt == NULL.
- QEMU runner now supports `--kernel MATCHING_KERNEL --fail-on-panic`: runtime font extraction from the payload produces exact `fb.txt`, plus `result.json`; a visible panic returns 2. Baseline 0013 re-run `research/q0013-text` detects the same NULL callback panic with zero unknown glyphs. Synthetic glyph roundtrip (including literal `?`) and invalid-VA rejection passed. Screen rows remain circular, not a full log; `no_panic_observed` does not prove successful boot. README has the invocation.
- Patch 0014 committed/pushed as `be61f99`; Actions run `38748543058` is running: https://github.com/dipa-studio/ios-sweet/actions/runs/38748543058. Do not start a duplicate build.
- 2026-10-15 active: hardware photo `IMG_20261015_160033.jpg` confirms the same PC=0 instruction-fetch abort as QEMU (LR `0xfffffe0007443fe4` = read_random). Independently reproduced with kernel 0013 in `research/q0013` (8-second run); prior allocator fix works. Latest tooling commit reviewed: `8d66d2d`.
- Patch 0014 implemented: registers a built-in HMAC-SHA256 DRBG provider at EARLY_BOOT/FIRST, before commpage creation. A shared mutex serializes output/reseed across CPUs (correctness first; no per-CPU scaling yet), initgen validates CPU identities, refresh uses try-lock and the existing entropy filter/health tests. SWEET entropy accumulation and write_random now use the built-in SHA256 directly; no incomplete g_crypto_funcs table is registered. The existing bootloader-seed requirement remains enforced.
- Local validation: both PRNG translation units compile to arm64 objects in `research/prng-objs`; no SHA256 wrapper imports remain. All 14 patches apply in CI order and resulting PRNG sources match local inputs. Sandbox `research/bt17/xnu`, originals `research/pre0014`, checker `research/check-patch-order.py`. NEXT: Actions kernel build, download to `xnu/out-0014`, run the QEMU payload before requesting another phone boot. Baseline QEMU ADT/payload are `research/q0013.adt` / `research/q0013.bin`.
- 2026-10-15 08:15 QEMU EMULATION WORKS (`tools/qemu-sweet.py`, see "QEMU emulation" below). Patch 0013 VERIFIED in QEMU: boot passes kmem_crypto_init and ulock_initialize. NEXT BLOCKER (reproduced in QEMU, expected on hardware too): `pmap_create_commpages -> random() -> RandomULong -> read_random -> prng_funcs.refresh == NULL` (instruction fetch abort at pc 0, lr read_random+0x34). Nobody calls `register_and_init_prng` (closed corecrypto kext does it on Apple). Fix = patch 0014: SWEET-registered cckprng_funcs provider (osfmk/prng/prng_random.c); note random_cpu_init also panics while !prng_ready. The 07:26 hardware boot of 0013 will most likely show this same panic.
- Previous hardware boot: patch 0013 (`a3a46e2`) CI `38686345689` PASSED (3m44s), image `shim/out/shim-boot-0013.img` was temporarily booted on 2026-10-15 at 05:26 UTC: send OKAY (0.407s), boot OKAY (0.134s), total 0.546s. Superseded by the hardware/QEMU PC=0 observation and patch 0014 work above.
- Latest kernel implementation commit: `8f851d4`. Latest successful kernel CI: `38749549779` (patch 0015), https://github.com/dipa-studio/ios-sweet/actions/runs/38749549779.
- CURRENT image: `shim/out/shim-boot-0013.img`, 16,412,672 bytes, SHA256 `110d1c46aee4b60253db24b6535e9781c4cf0fd25ca2a70e9016cf81378cea25`. Kernel `xnu/out-0013/kernel.development.sweet`, SHA256 `f0b1d375995316c550ce7014ff234d8271e9b9ac2857795ceff41b76ba2cd740`, plain arm64. CI log confirms 0013 applied; checksums passed. Entry PA `0xb146b488`, kernel end PA `0xb1ff4000`.
- Current log/buildtree: `research/run17.log`, `research/bt17` (extracted, no nested .git; preferred baseline for patch 0014). Payload/ADT: `shim/out/payload-0013.bin`, `shim/out/sweet-0013.adt` (includes /defaults). Unpacked ramdisk byte-compared with payload in `shim/out/check-0013`.
- Patch-0012 original image: `shim/out/shim-boot-0012.img`, 16,412,672 bytes, SHA256 `cf4b8ec4a65a51888d71c17d09cd0831d6b761b90e2531fdb8e575c32f4fd24a`. Kernel `xnu/out-0012/kernel.development.sweet`, SHA256 `69b78f49f6459cc63a0af44e7cf73c1779ef72130ef72b12ae86c88183ffc742`; checksums passed and sweet_early_relocate symbol present. Entry PA remains `0xb146b488`, kernel end PA `0xb1ff4000`.
- Patch-0012 log/tree: `research/run16.log`, `research/bt16` (extracted, no nested .git; preferred baseline for next patch). CI log confirms 0012 applied. Payload `shim/out/payload-0012.bin`, ADT `shim/out/sweet-0012.adt`; packed ramdisk byte-compared with payload in `shim/out/check-0012`.
- Active payload command line: `debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam`.
- Latest observed photo: `/home/dipa/Downloads/IMG_20261015_071346.jpg` (local only). Stages 9 (kernel framebuffer VA), 10 (TTBR0 off/TLB flush), 11 (physmap table pointers) and 12 (calling pmap_bootstrap) all visible. Persistent diagnostics are VERIFIED ON HARDWARE.
- pmap.c:1987 is the assert after SecureDTLookupEntry(NULL, "/defaults", &entry). The pmap-max-asids property itself is optional; an empty /defaults uses XNU's MAX_ASIDS. Do not bypass the assertion or guess an ASID limit.
- Previous payload-only fix image: `shim/out/shim-boot-0012-defaults.img`, SHA256 `3ff61a268853c6ea7cbf284833f1346a1d791980ca366b6e1a215a86e040512b` (16,412,672 bytes). Same kernel/CI as 0012; ADT 2516 bytes (`shim/out/sweet-0012-defaults.adt`), root /defaults present with no ASID override. Payload `shim/out/payload-0012-defaults.bin`; unpacked ramdisk exactly matches payload (`shim/out/check-0012-defaults`). This boot reached the allocator crypto NULL-pointer fault below.
- Latest hardware photo: `/home/dipa/Downloads/IMG_20261015_071608.jpg` (local only). Normal serial framebuffer console works. VM bootstrap/zone initialization, logging, scheduler, IPC, KDP and ulock_initialize print before the kmem_crypto_init data abort. gPanicBase warnings are expected because PLATFORM_PANIC_LOG_DISABLED is configured, and are not the faulting call.
- Faulting instruction: `ldr x0, [x8, #0x150]` in crypto_random_kmem_ctx_size; x8 = NULL g_crypto_funcs. Source: libkern/crypto/corecrypto_rand.c and osfmk/vm/vm_kern.c:2448. rand.h explicitly permits NON-cryptographic kmem RNGs, but requires no locking in generation and context size <=256. Do not substitute read_random here: the global PRNG provider is also unregistered and kmem generation must remain lock-free. early_random may seed contexts during single-CPU bootstrap; it uses the built-in HMAC-SHA256 DRBG with the host-generated ADT seed.
- Patch 0013 keeps the replacement entirely private to vm_kern.c: SplitMix64 state is 8 bytes per CPU/sizeclass, initialized using early_random. Uniform selection uses rejection sampling to avoid modulo bias. Other platforms retain the original corecrypto calls; SWEET's generic crypto APIs/registration remain untouched. Reference: https://prng.di.unimi.it/splitmix64.c (Sebastiano Vigna, public domain).
- Validation: vm_kern.c compiles to arm64 (`research/kmem-rng-objs`, using `research/run16.log` + `research/bt16`). Undefined symbols include early_random and NO crypto_random_* references. All 13 patches apply in CI order and match the checked source. Original saved as `research/vm_kern.pre0013.c`.
- RNG host checks: extracted actual new helper in `research/kmem-rng-check.c`; 16,384 outputs match the author's downloaded reference (`research/splitmix64-reference.c`), 147,456 bounded outputs satisfy their limits (including 1 and UINT64_MAX), and a forced rejection advances correctly. Full kernel crypto services and the registered kernel PRNG provider remain future work; this patch only supplies the allocator RNG contract.
- Patch-0011 artifacts: kernel `xnu/out-0011/kernel.development.sweet`, log `research/run15.log`, extracted buildtree `research/bt15` (no nested .git). CI log confirms patch 0011 applied; artifact checksums passed. Kernel is plain arm64, entry VA `0xfffffe000746b488` -> PA `0xb146b488`, kernel end PA still `0xb1ff4000`.
- Patch-0011 image: 16,412,672 bytes, SHA256 `29ad5cbfc752473de4af2c471a24a8b34f92da4bff5afec65c614b90cd3ad53a`. Kernel SHA256 `8ac3a956894b09f7bd0d890de8c5de38c65513287feb1e1bcd12db8ca772ee5c`. Payload/ADT in `shim/out/payload-0011.bin`, `shim/out/sweet-0011.adt`. Header unpacked/checked in `shim/out/check-0011`.
- First patch-0011 attempt timed out waiting for FASTBOOT; superseded by the successful send/boot recorded above. Do not repeat the boot before the user reports the current screen.
- Patch-0011 photo: `/home/dipa/Downloads/IMG_20261015_070218.jpg` (local only). Visible stages 1-8 and old red shim text; entry PA B146B488, boot args PA B1FF8000 / top B1FFC000. No evidence yet locating execution after stage 8.
- Patch-0012 sandbox: `research/bt15/xnu` (NO nested .git). Proposed permanent debug VA: VM_MIN_KERNEL_ADDRESS + ARM_TT_L2_SIZE, in the reserved gap below gVirtBase and above low globals; map the same PA framebuffer as Normal-NC in the final TTBR1 before arm_vm_physmap_init changes phystokv(). Keep the early panic sink until normal kprintf startup.
- Patch 0012 validation: all 4 changed C translation units compiled to arm64 objects in `research/post-ttbr0-objs`; internal header export added to osfmk/arm64/Makefile and recreated locally in EXPORT_HDRS for pe_serial.c. All 12 patches apply in CI order and match all 6 edited files. Baselines are saved under `research/pre0012/`.
- Actual mapping-helper host model (`research/early-map-check.c`, barrier stubbed only for host compilation) confirms: VA `0xfffffe0002000000`, L1 index 2016, L2 index 1; descriptor `0x006000009c000605` = framebuffer PA, Normal-NC, outer-shareable, EL1 RW, PXN+UXN. All other L2 entries preserved. The gap is excluded by ARM_LARGE_MEMORY's pmap_virtual_region(0).
- Next boot command line MUST add `-enable_kprintf_spam`: DEVELOPMENT disables kprintf_output by default even when DB_KPRT is set (`pexpert/arm/pe_kprintf.c`). Planned command line: `debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam`.

### Patch 0012 screen legend (after original stages 1-8)
- 9: kernel framebuffer VA live; 10: TTBR0 off / TLB flushed; 11: physmap pointers rebound.
- 12: calling pmap_bootstrap; 13: pmap_bootstrap returned; 14: early I/O page tables ready; 15: arm_vm_init returned.
- 16: calling serial_init; 17: fbcon config read / mapping; 18: fbcon mapping returned; 19: serial_init returned; 20: kprintf startup complete.
- Normal serial initialization clears the screen, so earlier stages may disappear before 19. If serial exists, early console disables after 20; otherwise early panic output stays enabled.
- Local source sandbox: `research/bt13/xnu` (git baseline `623b060`, patches 0001-0008 already in baseline; uncommitted export edits correspond to patch 0009). Preserve those edits when producing patch 0010.
- Previous compile log/tree: `research/run13.log`, `research/bt13`; previous kernel: `xnu/out/kernel.development.sweet`. New successful log/tree: `research/run14.log`, `research/bt14`; new kernel: `xnu/out-0010/kernel.development.sweet`.
- Current device access: patch-0012 image was temporarily started from FASTBOOT; no adb connection is expected. Never flash partitions for bring-up; use `fastboot boot` with the shim image.
- Patch `0010` lives in `xnu/patches/0010-sweet-early-framebuffer-debug.patch`. Its exact compiled sources are under `research/bt13/xnu`; generated objects are in `research/early-objs`.
- Local checks passed: all 5 changed/new translation units compiled to arm64 Mach-O objects; new console only imports `_doprnt` and `iso_font` (both exist in the previous kernel). All 10 patches applied to a temporary upstream git index in CI order, and all 7 resulting changed source files matched the local compile inputs.
- Reproduce changed-file compilation: `XNU_CC_OBJDIR="$PWD/research/early-objs" python3 tools/xnu-cc.py research/run13.log research/bt13 arm_init.c arm_vm_init.c kern/debug.c arm64/start.s osfmk/arm64/sweet_early.c --per-file` (create the output directory first). The helper now accepts explicit new source paths absent from the old artifact's Makefiles and rejects empty selections.
- Device command result: `adb reboot bootloader`, then `timeout 30s fastboot boot shim/out/shim-boot-0010.img`: send OKAY (16028 KB), boot OKAY, total 0.541s. This confirms bootloader acceptance only, not XNU progress.
- The successful boot above was on 2026-10-14. On 2026-10-15, `timeout 45s fastboot boot ...` timed out waiting for a device; no image was sent. Boot image SHA256 rechecked and unchanged. No new build is needed to repeat the trial.
- Earlier retry: `timeout 90s fastboot boot shim/out/shim-boot-0010.img` timed out (exit 124). This is superseded by the successful 2026-10-15 repeat boot recorded above; do not repeat it until the user reports the screen.
- User observation confirms MMU-on C entry, platform expert, CPU topology/bootstrap, startup bootstrap and cpu_init all complete. Failure is within arm_vm_physmap_init (non-XNU_MONITOR branch), before stage 8 / TTBR0 teardown. Old red shim text remains behind the early console; this is expected because only written rows are cleared.
- New edit/compile sandbox is `research/bt14/xnu` (extracted artifact, NO nested .git; `git diff` there would act on the parent project). Use a saved baseline file / generated unified diff, or explicitly initialize a local baseline before editing. `research/bt13/xnu` does have its own baseline git repo.
- Exact user-reported panic: `arm_vm_init.c:1606 Assertion failed: (temp_ptov_table[ptov_index - 1].va + temp_ptov_table[ptov_index - 1].len) <= physmap_end`.
- Root cause: MacOSX build sets `ARM_LARGE_MEMORY=1`; `XNU_MONITOR` is off. Block alignment in arm_vm_physmap_slide can add gaps, but the non-PPL large-memory physmap_end omitted the padding already present in the small-memory branch. Patch 0011 reserves PTOV_TABLE_SIZE*ARM_TT_TWIG_SIZE (8*32MB) in both the aperture bound and its L1 allocation; monitor/PPL builds retain zero padding. The assertion is preserved.
- Validation: `arm_vm_init.c` compiled to an arm64 object using `research/run14.log` + `research/bt14` (object in `research/physmap-objs`). All 11 patches apply in CI order and produce exactly that source. Host harness `research/physmap-check.c` extracts the real XNU slide function with page-table-write stubs: all 65,536 page-aligned slides within 1GB checked against the current kernel memory layout; old bound fails 65,504 cases, padded bound fails zero; worst overrun 0x1ffc000 bytes. Baseline source saved as `research/arm_vm_init.pre0011.c`.
- CI: https://github.com/dipa-studio/ios-sweet/actions/runs/38638702083 (success; artifacts and full log downloaded).
- New image: `shim/out/shim-boot-0010.img` (16,412,672 bytes, SHA256 `ed2c270e0081bad5ff517be415f9bfe8805463aea7866732203fa97ac737e64e`). Previous image preserved as `shim/out/shim-boot-pre0010.img`.
- New kernel SHA256: `3ee05270cc291c49589a101678f904b1b69cb2f2575e05398bce8a4e052f409a`. Artifact checksums passed; arm64 (not arm64e), early-console symbols present. Payload entry VA `0xfffffe000746a488` -> PA `0xb146a488`; kernel end PA `0xb1ff4000`. Command line remains `debug=0xc serial=3 cpus=1 keepsyms=1`.

### Patch 0010 screen legend
- Bottom-left white 64x32 tile: assembly entered `start_first_cpu`, before page tables/MMU.
- Text `SWEET EARLY 1`: entered `arm_init` with MMU on; 2: platform expert done; 3: CPU topology done; 4: CPU bootstrap done; 5: startup bootstrap done; 6: CPU init done; 7: entering `arm_vm_init`; 8: leaving bootstrap TTBR0.
- `SWEET EARLY PANIC:` prints a copy of panic arguments before normal panic handling needs per-CPU/thread state.
- In patches 0010/0011 the console disabled before TTBR0 invalidation; patch 0012 replaces that with a persistent kernel VA alias and diagnostics through normal serial/kprintf startup (see its legend above).
- Screen contents require a physical observation from the user: adb cannot capture a framebuffer after Android has been replaced by a bare-metal kernel.

## QEMU emulation (2026-10-15)
- `tools/mkadt.py OUT.adt --qemu` = same ADT with QEMU virt GICD 0x08000000 / GICR 0x080a0000 / CNTFRQ 62.5 MHz.
- `tools/qemu-sweet.py PAYLOAD OUTDIR [--secs N] [--hmp "x /8gx ADDR"] [--gdb]`: host-side copy of shim/loader.c
  (segments + ADT + boot_args at their PAs, 6-instruction stub sets x0 and jumps), `-M virt,gic-version=3 -cpu cortex-a76`
  (same ID_AA64MMFR0 as Kryo 470), 4G RAM so 0x9c000000 fb and 0xb0000000 kernel are plain RAM.
  Outputs `fb.png` (the screen), `regs.txt`, `qemu.log` (exceptions with ESR/FAR/ELR). `--gdb` halts with a stub on :1234
  (system `gdb` + `set architecture aarch64`, `hbreak *VA` works with the MMU on).
- Not emulated: Qualcomm XPUs, ABL, real panel, PSCI conduit (QEMU virt uses hvc). Hardware still decides those.
- Example: `python3 tools/mkadt.py /tmp/q.adt --qemu && python3 tools/mkpayload.py xnu/out-0013/kernel.development.sweet /tmp/q.adt /tmp/pq.bin --cmdline 'debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam' && python3 tools/qemu-sweet.py /tmp/pq.bin /tmp/q`

## Layout
- `backup/`  partition dumps + full sdb..sdf LUNs, `SHA256SUMS` (all verified on-device == local)
- `dtb/`     live FDT (from OrangeFox), PixelOS boot.img dtb, dtbo, dts versions
- `shim/`    bare-metal boot shim (`./build.sh` -> `out/shim-boot.img`)
- `research/` mainline sm7150 dts, XNU pe_fiq.c etc, PocketDarwin patches
- `tools/unpack_bootv2.py`

## Device access
- No root in PixelOS 17 (user build, adb root disabled). Root = `fastboot boot recovery/recovery.img` (OrangeFox R12.0_2, temp boot, not flashed).
- `fastboot boot` works for stock boot.img, OrangeFox, and our shim.
- Shim resets itself via PSCI SYSTEM_RESET; IMEM restart_reason 0x77665500 is seen
  (bootreason=bootloader) but ABL still boots Android, so it does not stop in fastboot.

## Hardware facts (live DT + shim measurements)
- Framebuffer (ABL cont splash): 0x9c000000, 1080x2400, stride 4320, a8r8g8b8, panel is DSC *video* mode (no kick needed).
- RAM: 0x80000000+2G, 0x100000000+0xfcc00000. Live reserved-memory = PixelOS base dtb + sweet dtbo fixups.
- GICv3: GICD 0x17a00000, GICR 0x17a60000 (stride 0x20000, 8 PEs). GICD_TYPER 0x007B041D: SecurityExtn=1 (DS=0).
  ABL leaves GICD_CTLR = 0x10 (ARE_NS on, groups off). Writing 0x13 reads back 0x12: EnableGrp1A (bit1) is the one that matters.
- GIC Group 1 VERIFIED (shim 2c): vtimer INTID 19 = 30 IRQs/300ms, ptimer INTID 18 = 30, SGI 1 to self = 10/10.
  ICC_SRE=1 already, ICC_CTLR 0x8440, priority/enable writes stick. GICR_IGROUPR0 and GICD_IGROUPRn read 0 from NS
  even though Group 1 delivery works (RAZ in NS view) - do not use them as a health check.
  INTID 28 shows pending constantly (unknown PPI 12).
- Timer 19.2 MHz. Qualcomm PPI numbering: secure-phys/phys/virt/hyp = PPI 1/2/3/0 -> vtimer INTID 19, ptimer 18 (NOT 27/30).
- PSCI 1.1 via SMC, SMCCC 1.1. CPU_ON ok; SYSTEM_SUSPEND and SYSTEM_RESET2 unsupported.
- SMP: CPU_ON works for all 7 secondaries (MPIDR 0x81000n00).
- Entry EL1, MMU off, x0 = DTB (magic ok). ID_AA64MMFR0 = ...101122: 16K granule YES, 4K YES.
- No serial console: debug UART SE is in SPI mode on sweet. Screen is the only debug channel.

## XNU implications
- XNU GICv3 path (pexpert/arm/pe_fiq.c, VMAPPLE) puts the timer (PPI 27) in Group 0 = FIQ. With SecurityExtn=1,
  Group 0 is secure -> impossible from NS EL1. Need: Group 1 IRQ, ICC_IGRPEN1, INTID 19, and the timer handled in the IRQ path.
- XNU VMAPPLE PSCI uses `hvc`; sweet needs `smc`.
- PocketDarwin NonAppleGenericCpu.patch only swaps -mcpu=apple-h7 for -march=armv8-a.

## Milestone 3 (2026-10-14): 16K MMU verified
- ABL loads the Image at 0x80080000 (base 0x80000000 + 0x80000) regardless of text_offset=0.
- 16K granule, T0SZ=28 (L2 start, 32MB blocks), MAIR 0x44ff00, TCR 0x1409CB51C, PARange=2 (40-bit PA).
- Only own image pages WB (Qualcomm XPUs: never map carve-outs cacheable); fb Normal-NC; rest Device.
- AT S1E1R checks all as expected; unmapped -> translation fault L2.
- Fill fb: 110 ms (MMU off) -> 3.5 ms (NC). Memory loop 70 ms -> 0.7 ms. vtimer + SGI IRQs still fine with MMU on.

## XNU loader design notes (xnu-8796)
- Entry: `_start` -> `start_first_cpu`, x0 = boot_args (PA), MMU off, EL1. boot_args: Revision/Version 2,
  virtBase/physBase/memSize/topOfKernelData, Boot_Video (fb 0x9c000000, rowBytes 4320, 1080x2400, depth 32),
  deviceTreeP/Length (ADT), CommandLine[608], bootFlags, memSizeActual.
- start.s maps [kernel mach header .. physBase+memSize) with cacheable BLOCKS. On Qualcomm every XPU carve-out
  must therefore lie below the kernel: use physBase = 0xb0000000 (above ramdump_fb 0xaf000000+16M,
  cdsp_sec, qseecom), end before rmtfs 0xfde01000 -> memSize ~0x4d000000 for bring-up.
- Base ADT: iPhone 8 d20ap DeviceTree from iOS 16.7.16 IPSW (tools/remotezip.py + tools/adt.py; LZFSE payload).
  Template values are empty: the loader must fill chosen/*, memory-map, cpu*/reg etc. like iBoot.
- XNU build: GitHub Actions (dipa-studio/ios-sweet, xnu.yml) via blacktop/darwin-xnu-build, MACOS_VERSION=13.5.
  New-clang fixes in xnu/patches; Xcode 16 iig is incompatible (IORPC.kernelContent) -> macos-14 runner, oldest Xcode.

## Kernel architecture plan (SWEET machine config)
- First stock build (VMAPPLE) is arm64e (PAC). Kryo 470 = ARMv8.2, no PAC -> SWEET must build plain arm64
  (HAS_APPLE_PAC is only defined for __arm64e__, so arm64 drops PAC automatically).
- Template: VMAPPLE (16K pages, GICv3 code in pe_fiq.c) minus APPLEVIRTUALPLATFORM hypercalls/paravirt PAC,
  plus BCM2837 (generic ARM: no APPLE_ARM64_ARCH_FAMILY Apple sysregs). Do not link the KDK lib<cfg>.os.*.a.
- Timer: XNU expects it on FIQ (sleh_fiq -> rtclock_intr). SWEET: GIC Group 1, so sleh_irq must ack ICC_IAR1,
  route INTID 19 to the same timer path, SGIs to cpu_signal_handler, EOI via ICC_EOIR1.
- SMP/interrupts: open-source AppleARMSMP (USE_APPLEARMSMP) needs an IOInterruptController (AIC role) and an
  IOPMGR (CPU power -> PSCI CPU_ON via SMC). Plan: built-in IOKit classes (SweetGIC, SweetPMGR, platform
  expert) compiled into the kernel and matched via iokit/KernelConfigTables.cpp -> no closed kexts needed.
- Debug: xnu patch 0003 sweet-fbcon = kprintf drawn on the framebuffer (ADT node "sweet-fbcon").
- ADT /arm-io ranges must not map to parent 0 (pe_arm_get_soc_base_phys()==0 disables serial): use parent 0x1000000.

## Status 2026-10-14 late: first XNU boot attempt
- SWEET kernel builds (CI run 38635343732, patches 0001-0009). Verified offline: arm64, no PAC, no >v8.2 code,
  70300 classic relocs all in range (slide 0 = no loader work), entry = __start.
- Boot: shim loader worked (initrd 0x846F0000-0x855FE3E0, BOOTARG 0xB1FF8000, JUMP 0xB146A488) but screen stayed
  red -> xnu died/hung before serial_init (fbcon). kprintf is a no-op before STARTUP_SUB_KPRINTF.
- Historical next-step plan (patch 0010, now implemented and built; see active handoff above): early fb debug channel
  1. start.s start_first_cpu (after mov x20,x0 / mov x21,#0): PA marker band (MMU off, direct store to 0x9c000000).
  2. start.s after both create_bootstrap_mapping calls: add ONE block entry to the existing V=P L2 table
     (x25 + 2*PGBYTES; do NOT call create_bootstrap_mapping again: fb and RAM share L1 entry 0, it would replace
     the L2 table). Entry = TYPE_BLOCK|VALID|SH(OUTER)|ATTRINDX(CACHE_ATTRINDX_WRITECOMB=1)|AF|PNX|NX|0x9c000000,
     index = (va & ARM_TT_L2_INDEX_MASK) >> ARM_TT_L2_SHIFT.
  3. new osfmk/arm64/sweet_early.c (+files.arm64 entry): sweet_early_mark(n) colored bands at screen bottom and
     sweet_early_putc using iso_font via VA=PA while the bootstrap TTBR0 is live; disable before
     arm_vm_init's set_mmu_ttb(invalid_ttep) (arm_vm_init.c:2148).
  4. markers in arm_init after PE_init_platform, ml_parse_cpu_topology, cpu_bootstrap, kernel_startup_bootstrap,
     cpu_init, before arm_vm_init.
  5. panic hook at top of panic_trap_to_debugger: va_copy + _doprnt(fmt, &copy, sweet_early_putc, 16).
  Verify with tools/xnu-cc.py (compile+symbols) and patch-order simulation before the single CI run.

## Status 2026-10-21: pre-XNU ramoops handoff probe prepared
- The prior `boot_b` pmsg probe returned no XNU marker in Android pstore. This did not distinguish an XNU
  early stop from failure to reach the XNU logger.
- Updated `shim/loader.c` to append `SHIM VEUX ramoops: XNU handoff` to the verified Linux ramoops pmsg
  ring immediately before entering XNU. Built on the Ubuntu VPS with the VEUX `dtb_1.dtb` and the existing
  `payload-veux-pmsg-probe.bin`.
- Image: `shim/out/shim-boot-veux-pmsg-handoff.img` (16,957,440 bytes; SHA-256
  `006ba309a26f990bd7cc8b7d77766c68fd11e50e45881f37179154b4c2a96a1c`). Offline unpack confirmed boot
  header v2, kernel size 180,224 bytes, ramdisk hash identical to the pmsg payload, and DTB hash identical
  to `dtb/vendor_boot_b_unpacked/dtb_1.dtb`. The shim marker is present in the compiled loader object.
- Interpretation: a retained shim marker would confirm shim access to pmsg; the separate
  `XNU VEUX ramoops log start` marker would confirm the XNU logger initialized. Missing markers alone do
  not locate the failure, especially if the RAM-backed pmsg buffer is cleared before it can be read.
- Test result: user authorized this exact image only on `boot_b`. Fastboot wrote `boot_b` successfully,
  slot B was selected for the attempt, and after about 50 seconds neither ADB nor fastboot enumerated the
  phone. The user returned it to fastboot; we selected slot A (no partition write) and Android booted
  successfully. Android reports ramoops `mem_address=0xd0000000`, `mem_size=0x200000`,
  `pmsg_size=record_size=0x100000`, `ecc=0`; `/sys/fs/pstore` is mounted but empty, so there is no
  `pmsg-ramoops-0` to inspect and `logcat -L` has no retained log. The shim/XNU markers therefore remain
  unobserved; the forced return through fastboot may have cleared the RAM-backed pmsg buffer.
- Follow-up per-device recovery check: rebooted Android A to fastboot, selected B and booted the probe,
  then after the phone returned to fastboot selected A and used `fastboot reboot recovery` before Android.
  Recovery ADB was root. Recovery dmesg again confirms ramoops registered at `0xd0000000`, size `0x200000`,
  ECC 0, and `/dev/pmsg0` exists, but `/sys/fs/pstore` is empty. Neither marker was recoverable even when
  checking recovery before Android; this still cannot distinguish no shim write from firmware clearing RAM.

## >>> UPDATE 2026-10-21 (VEUX QEMU pmsg mapping fix) <<<

- The corrected VEUX kernel from CI run `39639812065` passed the CPU-registration and kmem RNG source guards and disassembly no longer called the null corecrypto kmem RNG callback. Its QEMU run exposed a separate failure in our diagnostic logger: the first panic was `pmap_map_bd_with_options: no PTE` while `PE_init_kprintf` attempted to map the pmsg physical range `0xd0100000–0xd0200000` before `pmap_bootstrap`. The later debugger trap obscured this message on the blank virtual screen. This is an identified pre-pmap logger bug, not evidence that the physical VEUX device will fail the same way.
- Added patch `0091-veux-defer-pmsg-init.patch`: the early kprintf hook no longer maps ramoops; after `pmap_bootstrap`, XNU initializes pmsg and flushes the buffered VEUX milestones. Added a CI source guard to reject an early pmsg mapping. Patch 0091 applies to the exact buildtree from run `39639812065`; `tools/validate-repo.py` passes with 91 contiguous patches.
- Rebuild and repeat QEMU probe pending. No phone boot or flash was performed. Generic QEMU still lacks VEUX's Qualcomm UFS, UART and display hardware, so its outcome only diagnoses generic execution and patch-induced failures.

## >>> UPDATE 2026-10-21 (VEUX pmsg timing fixed; trust-cache fallback next) <<<

- CI run `39646338761` passed with the deferred pmsg mapping after the stage-14 early I/O page-table allocation. Kernel SHA-256: `3359d530877f46d42b2d9d4ace01602e027fac4e34cb936dd17109cd5bc58bf9`.
- Re-ran that kernel on generic QEMU 8.2.2 `virt` / Cortex-A76, one CPU, no root volume, for 45 seconds. The pmsg header became `DBGC` and the persisted log reached VEUX early stages 1–20, through `arm_vm_init returned` and `kprintf startup complete`. The old missing-PTE panic is gone. The next panic is `image4 interface not available @kern_trustcache.c:268`; captured outputs are in `shim/out/qemu-veux-39646338761/vps-out/`.
- This trust-cache path is a known SWEET-only bring-up fallback: patch 0015 marks caches unavailable when Image4/AMFI are absent, but its guards do not include VEUX. Added patch 0092 to enable that same unavailable-service behavior for VEUX without granting trust. CI run `39648190769` is pending. Later AMFI/entitlement behavior remains a separate question.
- This QEMU run confirms early XNU execution and the pmsg logger under the generic virtual machine. It does not validate Qualcomm hardware, UFS, display or physical-phone boot. No phone boot or flash was performed.

## >>> UPDATE 2026-10-21 (VEUX trust-cache fallback; AES provider next) <<<

- CI run `39648190769` succeeded after patch 0092 broadened the unavailable trust-cache guards to VEUX. Kernel SHA-256: `6ad3773796cb32cd13e6b4c5ebf42afdf108c4785e0c610321bb339d63e0a428`.
- QEMU 8.2.2 `virt` / Cortex-A76, one CPU and no root volume passed the previous `image4 interface not available` panic. The persisted VEUX log then reported a data abort at `FAR=0x78`; symbol resolution identifies `_aes_encrypt_key128`, whose legacy wrapper still read null `g_crypto_funcs` (`x8 == 0`). Saved run output is in `shim/out/qemu-veux-39648190769/vps-out/`.
- Added patch 0093 to enable SWEET's already-staged BearSSL portable AES CBC/ECB implementation for VEUX, including the source guards and Makefile flags. It does not populate the broader corecrypto function table. Patch 0093 applies cleanly to the saved source tree; CI/QEMU are pending.
- No phone boot or flash was performed.

## >>> UPDATE 2026-10-21 (VEUX QEMU reaches CPU idle) <<<

- CI run `39649899996` succeeded with the portable AES fallback. Kernel SHA-256: `33cb960893c7c27caaeb76a54f84874d62fd2eec7355812f6318f55b46327f9b`.
- Re-ran on QEMU 8.2.2 generic `virt`, Cortex-A76, one CPU, no root volume, for 45 seconds. The captured pmsg log has no panic after the early startup milestones. QEMU logged one data abort at `_skmem_sysctl_init+0x18` for `0xfffffe300a9a8000`, then returned to the faulting instruction; the final PC was `_cpu_idle+0x1ec`. This is consistent with a handled page fault and XNU reaching its idle loop. QEMU reports `blank_screen`, and this run does not demonstrate a mounted root, `launchd`, userspace or VEUX hardware behavior. Artifacts are in `shim/out/qemu-veux-39649899996/vps-out/`.
- The QEMU-specific pmsg mapping fault, VEUX trust-cache startup panic and legacy AES null-table abort are resolved in the build tested here. The generic QEMU result cannot establish whether the same kernel will boot on the phone.
- No phone boot or flash was performed.

## >>> UPDATE 2026-10-21 (recovery ADB and pmsg inspection) <<<

- ADB is available in root recovery on slot A (`ro.boot.slot_suffix=_a`; the recovery kernel command line also says `_a`). This is the Android recovery environment, not an XNU boot.
- `/sys/fs/pstore` contains only `pmsg-ramoops-0` (1,979 bytes); there is no console ramoops dump, and `/proc/last_kmsg` is absent. The pmsg capture has text fragments adjacent to the expected `VEUX_WARM_RESET_TEST_20261021` marker, but the marker is not present as a clean contiguous string, so this is not conclusive evidence that the exact marker survived the reset. No XNU startup marker or panic trace was found.
- Read the final 1,025 4 KiB blocks of userdata from recovery and compared them with the saved pre-probe backup. Both are 4,198,400 bytes and SHA-256 `06955cde7f98b9503653b906e9634732d59a17a6dc2cb1a0e453fbdd4adaab86`; the logger wrote nothing to that region, so no restore was needed. No partition was modified during this ADB check.
- Current evidence does not establish whether XNU ran on the phone. Next useful change is a robust pre-XNU marker capture that can be read after an ordinary warm reset, or an external early log path; do not infer a phone boot from the QEMU idle-loop result.

## >>> UPDATE 2026-10-21 (final QEMU kernel flashed to boot_b) <<<

- Downloaded the successful CI `xnu-kernel` artifact from run `39649899996`; its kernel SHA-256 is `33cb960893c7c27caaeb76a54f84874d62fd2eec7355812f6318f55b46327f9b`, matching the QEMU-tested kernel. Built a phone payload using the existing `veux-log.adt` (SHA-256 `12e51ef4abcb0a9112ae9247e3f519a2a3046b6645c83f1f569bb954f564f068`) and the same `rd=ufsroot0 veuxlog=1`, `cpus=1` command line as the earlier logger attempt. Wrapped it with the known shim and selected board DTB `dtb_1.dtb` (SHA-256 `08284b0f3b0d3810abda6d617598370099f36f0f54110668bfe89f6ee35b4e2e`). The resulting Android boot v2 image is `shim/out/shim-boot-veux-xnu-39649899996.img`, 17,039,360 bytes, SHA-256 `d140fe8a653b14c7c27807e943d4fe4519b6fb9ab36fb677e334c185283b9e0d`. Unpacked verification confirmed the kernel, payload and DTB hashes match their inputs; the image is below the 128 MiB boot partition size.
- Before flashing, recovery ADB read the entire current `boot_b` partition. Saved it to `/Users/vivien/Documents/ChatGPT/iosxia/backup/veux-device/boot_b.before-xnu-39649899996.img` (128 MiB, SHA-256 `d2dbfaf52c98398ec8af09fe89caae1eb4e3ab30e315cdf17407240ea2e72aca`). The separate stock `boot_b.img` backup remains untouched. Fastboot reported product `veux`, current slot A, and 128 MiB each for `boot_a` and `boot_b`; it successfully flashed only `boot_b`, set slot B active, and rebooted. `boot_a` was not written.
- User clarified that the test showed the bootloader splash and unlocked logo, not a black screen; there was no visible handoff beyond that splash. After approximately 65 seconds, neither ADB nor fastboot enumerated the phone. From fastboot, slot A was selected and `fastboot reboot recovery` succeeded. Recovery ADB was initially unauthorized; it later became available as root on slot A. The splash alone is not evidence of XNU execution or failure.
- Recovery inspection after the boot-B test: `/sys/fs/pstore` is empty (the prior `pmsg-ramoops-0` file is no longer present); recovery dmesg says ramoops found an existing invalid buffer and then registered the backend at `0xd0000000`, size `0x200000`. `/dev/pmsg0` exists, but there is no retained pmsg file to inspect. The final 1,025 userdata 4 KiB blocks were read again (4,198,400 bytes); their SHA-256 is still `06955cde7f98b9503653b906e9634732d59a17a6dc2cb1a0e453fbdd4adaab86`, identical to `backup/veux-device/userdata-tail-pre-veuxlog.bin`. The XNU logger did not modify its reserved region, so no restore was needed. No partition was written during this recovery inspection. These results do not establish whether the shim or XNU executed on the phone.
- Provenance audit of the flashed candidate: GitHub Actions run `39649899996` built with `MACOS_VERSION=13.5`, `KERNEL_CONFIG=DEVELOPMENT`, `MACHINE_CONFIG=VEUX`; the build log selects `DEVELOPMENT_ARM64_VEUX`. The arm64 XNU artifact contains `VeuxPlatformExpert` and `VeuxCPU`. In the phone and QEMU payloads, all ten XNU load segments have identical virtual addresses, sizes, and SHA-256 hashes. The phone package uses the VEUX payload (`rd=ufsroot0`, `veuxlog=1`) and its outer DTB byte-matches the selected `vendor_boot_b` `dtb_1.dtb` (SHA-256 `08284b0f...35b4e2e`). QEMU used a different QEMU `virt` ADT and `rd=md0`; those QEMU harness settings are not in the phone image. This verifies VEUX-targeted configuration and phone packaging, but not successful execution on the Qualcomm hardware.
- Display-state comparison: the earlier `shim-boot-veux-ufs-probe.img` (reported black screen) was also built in `--veux` mode after `VEUX_NO_FB` was added, so its shim clear/text writes were no-ops and it omitted XNU `Boot_Video` fields. Its outer DTB SHA-256 matches the current image's selected `dtb_1.dtb`. The older and current shim binaries differ, but neither source path intentionally clears the VEUX display. Why that test showed black while the latest test retained the Xiaomi/unlocked splash is unknown; neither appearance establishes whether XNU ran.

## >>> UPDATE 2026-10-21 (latest boot-B attempt: XNU handoff confirmed) <<<

- After the latest boot-B attempt, fastboot returned. Set slot A active and booted recovery without reflashing `boot_b`; recovery ADB is now root on slot A.
- Recovery `/sys/fs/pstore/pmsg-ramoops-0` contains an exact `SHIM VEUX ramoops: XNU handoff` marker, followed by an `XNU VEUX ramoops log start` marker and VEUX early milestones through stage 20 (`kprintf startup complete`). This confirms the shim jumped into XNU and XNU ran through early VM initialization and kprintf startup; the previous splash-only observation could not establish that.
- The captured pmsg is 762 bytes (SHA-256 `0ac129881286dd2ce8d04446d9261c8d7a3ad38857a0d93858277a31c0e165aa`). Text after the initial markers is substantially corrupted; a `VEUX EARLY PANIC:` fragment is present, but its formatted panic body cannot be decoded reliably. Recovery dmesg reports an invalid existing ramoops buffer before registering the backend. Exact panic cause and stop point remain unknown; next diagnostic work should repair/validate the XNU pmsg writer before relying on its panic text.
- Re-read the reserved userdata tail (4,198,400 bytes); SHA-256 `06955cde7f98b9503653b906e9634732d59a17a6dc2cb1a0e453fbdd4adaab86` still matches the pre-test backup, so no restore was needed and this inspection wrote no partition. Slot A recovery is active; the VEUX test image remains on `boot_b`.

## >>> UPDATE 2026-10-21 (pmsg corruption mitigation) <<<

- Compared the recovered 762-byte pmsg with the expected early-stage strings. The shim handoff marker is exact; the first XNU text mismatch is at payload byte 56, shortly after the 64-byte mapped-line boundary (the 12-byte persistent-RAM header is outside the pstore payload). The XNU milestones remain recognizable through stage 20, but later characters are heavily corrupted. This points to the XNU writer/mapping path; it does not by itself prove which instruction caused the damage.
- Source review found that XNU maps this ring with `ml_io_map_wcomb()` but then ran `CleanPoC_DcacheRegion_Force()` on every data byte and on the header. Linux ramoops also uses a write-combining mapping by default and writes through its I/O mapping. The forced cache maintenance is unnecessary for that mapping and is the strongest source-level suspect for corruption around a cache-line boundary.
- Added patch `0094-veux-safe-pmsg-writes.patch` and committed it as `e03c862`: remove cache-clean-by-VA from the write-combining pmsg path, use `dsb sy` to order data before the persistent-RAM cursor/header and ensure header stores complete, and route VEUX pmsg kprintf directly to the ring without relying on the unverified UART. Patch `--dry-run` applies cleanly to the saved XNU source snapshot after patch 0091. At that commit no full compile, QEMU run, phone boot, or flash had been performed; follow-up CI result is recorded below.
- The phone remains in recovery on slot A; the existing XNU candidate remains on `boot_b` and no partition was changed during this source fix. At this point the next step was to build the kernel; follow-up results are recorded below.

## >>> UPDATE 2026-10-21 (pmsg mitigation kernel built) <<<

- GitHub Actions run `39692593719` completed successfully for source commit `6c3289cce3bed2b5e9210da649d21141cf92ab52` with `MACOS_VERSION=13.5`, `KERNEL_CONFIG=DEVELOPMENT`, and `MACHINE_CONFIG=VEUX`. The build step and VEUX source guards passed. Kernel artifact: `xnu/out-39692593719/kernel.development.veux`, SHA-256 `d619228c4970e7d7a4d83d96ef6f90bb8322017b8c873a0feba8405253e6cefb`; the artifact checksum file verifies and `file` identifies it as arm64 Mach-O.
- Built the new XNU payload `shim/out/payload-veux-xnu-39692593719.bin` from that kernel and the existing high-memory `veux-log.adt`, preserving the prior boot args (`debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam -noprogress rd=ufsroot0 veuxlog=1`). Payload SHA-256 `39ac43b6de4817762cb503e9b93c11de58f7f9fe6b3c18e3b6dfa9a0a8083a94`; selected outer DTB remains `dtb_1.dtb`, SHA-256 `08284b0f3b0d3810abda6d617598370099f36f0f54110668bfe89f6ee35b4e2e`.
- No QEMU run or phone boot was performed. The new payload has not yet been wrapped as an Android boot-v2 image or flashed. The phone is still visible in root recovery ADB on slot A; `boot_b` still contains the previous XNU candidate. Next step: package this payload with the known shim and matching DTB, verify the resulting image, then review before any boot-B test.

## >>> UPDATE 2026-10-21 (ordered-write pmsg phone test) <<<

- Packaged `shim/out/payload-veux-xnu-39692593719.bin` into `shim/out/shim-boot-veux-pmsg-fix-39692593719.img` (17,039,360 bytes; SHA-256 `47133501c79105c6b478fc36cb80015881e69b4495276309e6df304eddd44a54`). Android v2 unpack-and-compare checks confirmed the outer shim kernel, embedded XNU payload, and selected VEUX DTB match their inputs.
- On the user's “do it,” flashed this test image to `boot_b` only, selected B, and rebooted. Fastboot accepted the flash and slot switch. After about 60 seconds neither ADB nor fastboot enumerated the phone; the user then returned it to fastboot. Selected A and booted recovery; recovery ADB is root on slot A. `boot_a` and userdata were not written.
- Recovery exposed `/sys/fs/pstore/pmsg-ramoops-0` (1,932 bytes; SHA-256 `3d440586d9bc50590ccae4f8c95dfd702d8791717c8b2ddf8f086e690003c0d4`). The byte stream contains Android pmsg records plus garbled XNU-like early text; no exact shim handoff or XNU logger-start string is present. Recovery dmesg registered ramoops at `0xd0000000` without the earlier invalid-buffer warning. Because this candidate lacked a unique build marker and the pmsg text is damaged, this read does not conclusively identify which XNU build produced the fragments or the stop point.
- Patch 0094's ordered write-combining stores did not yield a clearly readable phone log. The source cause remains unconfirmed. Next candidate: change the logger to `ml_io_map()`'s device I/O mapping and give it a unique start marker; build/package it first. Do not flash that new candidate until the user approves it. Current phone state is slot A recovery; the last tested image remains on `boot_b`.
# iOS 16 on sweet (Redmi Note 10 Pro, SM7150) - working notes

## >>> UPDATE 2026-10-21 (VEUX recovery framebuffer inspection before build) <<<

- Before any new XNU build, inspected the currently attached root ADB recovery on slot A (`veux`, model `2201116SG`). No phone partitions were written.
- Recovery sysfs exposes `/sys/class/drm/card0-DSI-1` as connected and enabled, and a Qualcomm `sde-crtc-0`; it exposes no fbdev node or DRM active-plane/framebuffer metadata. The connector's `modes` file is empty. The panel reports as `dsi_k6s_38_0c_0a_fhdp_dsc_vid_display`.
- Recovery `/proc/config.gz` confirms `CONFIG_DRM=y` and `# CONFIG_DEBUG_FS is not set`. A temporary debugfs mount attempt failed with `No such device`, so the kernel cannot provide the SDE/DRM debug state at runtime. Its dmesg only says `cont_splash enabled in 1 of 1 display(s)`; it has no plane FourCC or scanout base/stride dump. The SDE CRTC reports measured FPS 0.0 and the log reports an ESD `PANEL_DEAD`, so this recovery session is not evidence of a live panel scanout.
- This confirms only that recovery's DRM connector is enabled and that the driver accepted a continuous-splash handoff. It does not establish the bootloader's active scanout address, framebuffer format/channel order, or prove that `0x85200000` is being scanned out. Keep framebuffer writes disabled.
- GitHub Actions run `39696554499` (head `4c7cc91ea672b3ec539ad1d45f5c96784aa43f25`) is now confirmed cancelled. No replacement XNU build was started.
- To obtain a framebuffer format from DRM, a debug-capable recovery kernel or a read-only DRM diagnostic is needed; that would describe recovery's display state. To identify the bootloader/XNU handoff buffer, state must be captured before recovery or Android reprograms SDE, for example by an early handoff register/state logger. Static DT and ABL artifacts alone have not supplied the active plane format/address.

## >>> UPDATE 2026-10-21 (guarded VEUX framebuffer marker) <<<

- Patch `0096-veux-sde-framebuffer-marker.patch` adds the board-matched SDE
  handoff probe and a tiny, opt-in screen marker. The probe maps SDE at
  `0x05e00000`, checks revision `0x60090000`, and logs CTL0, LM0, VIG0 and
  DMA0 state to pmsg when `veuxsde=1` or `veuxfb=1` is present.
- `veuxfb=1` permits one 32x32 white RAM marker at offset (16,16) in the
  candidate `0x85200000` splash buffer. Before mapping or writing, XNU must
  observe active DSI, a 1080x2400 LM0, a routed VIG0/DMA0 plane whose address
  equals the reserved splash base, zero source/output offsets, an accepted
  linear 8888 format and unpack layout, no rotate/flip/BWC mode, and a bounded
  4320/4352-byte stride within the 12 MiB reservation. Unexpected SDE revision,
  mapping failure, or any mismatch skips the write. The marker does not write
  display MMIO and is not a full framebuffer console.
- The 12 MiB region and SDE register addresses are supported by the
  board-matched DT and Qualcomm SDE source, but no pre-XNU live register read
  has yet confirmed the current scanout address/format. Until the opt-in probe
  runs on the phone, the guard's match and visible marker remain unverified.
- `.github/workflows/xnu.yml` now asserts the opt-in path, the address/mode/
  format/stride guards, and that the framebuffer map and marker store occur
  only after those checks. The complete ordered patch series 0091-0096 applies
  to saved buildtree `39639812065`, the exact embedded workflow guard passes,
  and `tools/validate-repo.py` reports 96 contiguous patches. CI run
  `39698775780` failed because the zero-context 0095 hunk was skipped and the
  0096 call landed outside `PE_init_veux_pmsg()`. Rebuilt 0095/0096 with
  contextual hunks and strengthened the workflow guard to require the probe
  call inside pmsg initialization. Corrected CI run `39699826454` succeeded
  on macOS 13.5 / DEVELOPMENT / VEUX; its log confirms both patches applied
  and the SDE/framebuffer source guards passed. The downloaded arm64 kernel is
  `xnu/out-39699826454/kernel.development.veux` (17,088,616 bytes; SHA-256
  `b4772dfbeff1c06ad7d5776d4dc0ba58cbafea8d0bf52a18423c69efc7865197`).
- Binary strings confirm the probe and marker are present. This is only a
  successful compile: no phone boot or flash was performed, and the live
  scanout guards have not yet been observed on-device.
- Prepared `shim/out/payload-veux-fb-marker-39699826454.bin` with the existing
  high-memory/pmsg ADT and boot args ending in `rd=ufsroot0 veuxfb=1` (SHA-256
  `1b95df7a884e13d8c66324ebac9d16aa7fabdd4f0faad70ea23d7c91bc9c2dc5`).
  It omits `veuxlog=1`, so this framebuffer probe does not enable the separate
  userdata-tail log writer.
  Wrapped it as Android boot-v2 image
  `shim/out/shim-boot-veux-fb-marker-39699826454.img` (17,055,744 bytes;
  SHA-256 `c71422a155ae2315d23c06b6bbb50522ef351a80ebef73323f8579d6c2b62e30`).
  The v2 packer was checked by reconstructing the prior known image byte for
  byte; unpacking the new image confirms the shim kernel, payload and selected
  `dtb_1.dtb` each match their source. It fits the 128 MiB `boot_b` partition.
- Flashed `shim/out/shim-boot-veux-fb-marker-39699826454.img` to `boot_b`
  only. Fastboot reported `Sending 'boot_b' (16656 KB) OKAY` and
  `Writing 'boot_b' OKAY`; set slot B active and rebooted. Slot A and userdata
  were untouched. The device left fastboot, but after 12 seconds neither ADB
  nor fastboot enumerated it. This is expected for XNU unless it exposes a
  transport; no display observation is available here, so marker visibility
  and the live SDE guard result remain unknown. The tested image remains on
  `boot_b`; slot B was selected active for this test.

# iOS 16 on sweet (Redmi Note 10 Pro, SM7150) - working notes

## >>> UPDATE 2026-10-23 (VEUX HFS UUID panic; portable MD5 follow-up) <<<

- The 0111 image from CI run `39942134414` booted through the first successful UFS READ(10), the selected filesystem mountroot callback, and `vfs_mountroot`; the phone photos show the expected cells 16 and 6-9. The later `bsd_utaskbootstrap` and launchd markers remained dark.
- Panic dump: ESR `0x96000005`, FAR `0x20`, PC `0xfffffe000798bc40`, LR `0xfffffe00077b8294`. Symbolization against the run's kernel (`__TEXT` base `0xfffffe0007004000`) gives `MD5Init+0x34` called from `hfs_getvoluuid+0x64`. The faulting instruction loads `[x22, #0x20]`; `x22` came from `_g_crypto_funcs` at `0xfffffe00072490d0`, which is NULL for this VEUX build. The HFS UUID helper therefore entered the legacy corecrypto MD5 path even though VEUX has no corecrypto kext.
- Candidate patch 0112 extends the existing BearSSL legacy MD5 provider to `ARM64_BOARD_CONFIG_VEUX`, including its MD5 and little-endian codec translation units. It does not change the pmap barriers, root mount mode, journal handling, UFS path, or the SWEET/VEUX IOKit gate.
- Added workflow source checks for all four VEUX MD5 gates. Local patch-sequence/syntax validation passes (112 contiguous patches); patch 0112 applies cleanly to the saved XNU source snapshot. The synthetic framebuffer/stack/VM host tests require the patched CI source tree and are left to the workflow. No follow-up CI or image exists yet; do not flash until that run passes.
- The photo's `handshake structure not initialized` text is a hardware-debugger/KDP handshake diagnostic; the panic PC/LR and FAR identify the independent MD5 null-table fault above.

## >>> UPDATE 2026-10-22 (VEUX direct framebuffer build dispatch) <<<

- Dispatched GitHub Actions run `39789142904` on `59c84486t9-alt/ios-veux`, branch `veux-xnu-build`, head `1aab246be4a361392f1c7683ca799a6b11e76f64`; no workflow was run on `ios-sweet`.
- The head includes commit `c27fda0` (`Port direct VEUX simple framebuffer path`) as an ancestor. `.github/workflows/xnu.yml` copies `xnu/patches/*.patch` into the pinned XNU source before building, so `0103-veux-simple-framebuffer.patch` is included in this run's source.
- Run `39789142904` ended `cancelled` after 15 minutes with an empty step list. The workflow never reached checkout, XNU compilation, or artifact upload. There is no new kernel artifact or boot image from this run, and no device/partition action was taken during this dispatch.
- The workflow uses the free standard `macos-14` image to obtain Xcode 15 `iig`. GitHub announced reduced macOS 14 runner capacity ahead of retirement; all three recent dispatches on this branch ended without build steps. `macos-15` standard runners have Xcode 16, whose `iig` output references `IORPC.kernelContent` absent from XNU 8796's `IORPC` struct; moving the build requires resolving that toolchain compatibility or obtaining a macOS 14 runner. Larger macOS runners are paid and were not selected.
- Next: resume with a free macOS 14 runner when available, or separately adapt and verify the Xcode 16 `iig` compatibility before switching the workflow. Do not flash a stale image as a substitute for the missing fresh kernel.

## >>> UPDATE 2026-10-22 (VEUX workflow rerun after hosted-runner acquisition error) <<<

- In response to the user's request to retry GitHub's internal runner-acquisition error, reran workflow `39789142904` (attempt 2), preserving its head `1aab246be4a361392f1c7683ca799a6b11e76f64` and original `DEVELOPMENT` / `VEUX` / macOS 13.5 inputs.
- At 14:13 UTC, job `119872313567` remained queued after about 7 minutes, with no steps executed. No kernel artifact has been produced by this retry so far. The phone and its partitions were not accessed or changed.

## >>> UPDATE 2026-10-22 (macOS 15 / Xcode 16 build path) <<<

- To avoid the repeated hosted-runner acquisition failures on `macos-14`, prepared a VEUX-only workflow update for the standard `macos-15` runner and pinned selection of Xcode 16. The Xcode 16 `iig` ABI difference is addressed by new patch `0104-xcode16-iig-iorpc-compat.patch`, which adds the kernel-conditional `IORPCMessage * kernelContent` field to both XNU 8796 IORPC header copies, matching newer open-source XNU.
- Patch 0104 dry-runs successfully against the saved XNU 8796 tree from `/tmp/veux-local-xnu`; `tools/validate-repo.py` passes with 104 contiguous patches and `git diff --check` is clean. This is source/patch validation only, not a kernel compile or runtime validation.
- The previous macOS 14 rerun (run `39789142904`, attempt 2) was still queued at the time of this change. A new manual dispatch on `ios-veux` will supersede that queued attempt through the workflow's existing concurrency group. No phone or partition has been accessed or changed.

- GitHub's runner annotation specifically cites capacity constraints for macOS arm64. The first macOS 15 retry, run `39794656055`, used the `macos-15` arm64 label and remained queued with no steps after about 12 minutes. Updated the workflow to use standard `macos-15-intel` instead; it retains macOS 15 / Xcode 16 and the same XNU compatibility patch, while avoiding the arm64 runner pool. Static repo validation and the 0104 patch dry-run still pass. A new VEUX workflow dispatch is pending.

- Dispatched Intel-hosted macOS 15 build `39796431519` on commit `5d0b74c` (`macos_version=13.5`, `DEVELOPMENT`, `VEUX`, `keep_going=true`). GitHub confirms job label `macos-15-intel`. At 14:39 UTC it was still queued after about 7 minutes, with no steps/runner assigned. The prior arm64 macOS 15 run `39794656055` also remains queued; GitHub's cancel endpoint refuses queued jobs, but the current preferred run is the Intel-labelled one. No artifact or device action yet.

## >>> UPDATE 2026-10-23 (VEUX PSCI reset path and reboot origin) <<<

- Added XNU patch 0115: VEUX-only `IOPlatformExpert::haltRestart()` reads the normalized `/psci` `method` and issues PSCI SYSTEM_RESET (`0x84000009`) or SYSTEM_OFF (`0x84000008`) through SMC or HVC; stage cell 5 lights immediately before the call. The earlier `PE_halt_restart` pointer is null and `IODTPlatformExpert::haltRestart()` delegates to the base implementation.
- The timeout is scheduled before synchronous `IOPMrootDomain::handlePlatformHaltRestart()`. On arm64, its 30-second callback panics with `Halt/Restart Timed Out`; a blocked notification can prevent the new platform hook from running. The pre-PSCI stage cell distinguishes this from a reset call that returns. Reboot request instrumentation records `howto`, process/PID and stack frames; the panic region also records the `haltRestart()` frames when reached.
- Live VEUX DT says `/soc/psci` method `smc`; watchdog bark is 11,000 ms. Built a standalone RGB + visible five-second counter probe, SHA-256 `67382ebf4227f82328af1e14ed623eed8a997927fa77389bffe78678ef47189f`, and flashed it to `boot_b` after CI passed. Fastboot reported product `veux`, current slot `b`, and both flash and reboot returned OKAY. The timing result is not yet confirmed.
- Candidate commit `54694a90e1357ce905f8418002be6164ccf1b794` passed CI run `39965956106` (macOS 13.5 / DEVELOPMENT / VEUX). The exact kernel artifact `kernel.development.veux` is 16 MiB with SHA-256 `24529c64de00f59e49f53f8e114394a835dd66bd8614e9c87fbab823459956fa` (verified against the artifact manifest). This kernel has not been flashed; test the standalone PSCI reset timing first. The last confirmed XNU boot before this probe was RW (`rootrw=1 ufsrw=1`).

## >>> UPDATE 2026-10-23 (PSCI probe confirmed; run 399659 kernel flashed) <<<

- Inspected user video `IMG_0646.mov` (9.12 s). The RGB probe appears around video t=2 s, its visible counter advances through t=7 s, and the display is dark after reboot by t=8 s. This is consistent with SYSTEM_RESET about 5-6 s after probe start, before the live-DT watchdog bark interval of 11 s; PSCI reset is therefore confirmed on this device.
- Packaged the CI kernel from successful run `39965956106` / head `54694a90e1357ce905f8418002be6164ccf1b794` with the VEUX ADT `/psci method=smc`, existing shim and selected vendor `dtb_1.dtb`. Boot args retain `cpus=1`, diagnostics, `unentitled_ios_sim_launch=1`, and `rootrw=1 ufsrw=1` (RW test mode from the last confirmed XNU boot).
- Kernel SHA-256: `24529c64de00f59e49f53f8e114394a835dd66bd8614e9c87fbab823459956fa`. Final Android boot-v2 image: `shim/out/veux-xnu-39965956106/shim-boot-veux-xnu-39965956106-rw.img`, 17,121,280 bytes; SHA-256 `b82f69cf81a745c6a3ee96c8e4225271d24d869d94f649bd3b90213c3e6357f1`. Packaging/unpack verification, patch/tool validation (115 patches), and `tools/test-veux-psci-adt.py` passed.
- Fastboot identified product `veux`, current slot B. Flashed only `boot_b`; send/write both returned OKAY. Set B active and reboot returned OKAY. The phone is now running the new RW diagnostic XNU candidate; no post-flash XNU outcome is known yet. Await the user's screen observation before another reboot or flash.

## >>> UPDATE 2026-10-23 (PSCI SMC register fix candidate) <<<

- The latest user photos show `Halt/Restart Timed Out` at `IOPlatformExpert.cpp:884`. One photo appears to show the root-domain restart notification completing in about 35 ms before the timeout. This means the actual restart is still failing; the photo is not clear enough to read whether the pre-PSCI marker or the SMC return status was displayed. Last flashed XNU image was the RW diagnostic candidate (`rootrw=1 ufsrw=1`).
- Found a concrete defect in patch 0115: the inline SMC/HVC call used a generic C `uint64_t x0` with a `+r` constraint. The PSCI function ID must be in architectural register X0, but that constraint does not bind the operand to X0. Changed it to a register-bound `x0` variable, matching the tested shim's PSCI helper. This is a correctness fix; the phone photos alone do not prove that it was the failure cause.
- Added a CI post-patch assertion for the fixed X0 binding. Repository validation (115 patches), VEUX PSCI ADT test, `git diff --check`, and local AArch64-target Clang syntax validation pass. CI run `39973136957` passed on commit `f2c92747e60d4cf5dbf54845e78ad007c23a4afc` (macOS 13.5 / DEVELOPMENT / VEUX); kernel SHA-256 is `018f16ad435bb30a5086380927c84b41cb86236136f86faed3619e3424b2dd3a`.
- Packaged that exact kernel in the existing XNU payload/VEUX shim boot-v2 template with the prior diagnostic args (`rootrw=1 ufsrw=1`). Unpack verification confirmed the payload matches the CI-derived payload, while the shim kernel and selected VEUX DTB are byte-identical to the prior tested image. Image `shim/out/veux-xnu-39973136957/shim-boot-veux-xnu-39973136957-rw.img` is 17,121,280 bytes, SHA-256 `81d1cc655197edb6363cdd9ca697584437b14b77edf980cd903b46e2ab918b54`.
- Fastboot verified product `veux`, current slot `b`, and `boot_b` capacity `0x8000000`; flashed only `boot_b`, set B active, and reboot returned OKAY. This test image contains the register-bound PSCI X0 fix; the reset result is pending the next phone observation. No userdata or other partition was touched.

## >>> UPDATE 2026-10-23 (VEUX reboot loop; persistent log enabled) <<<

- User confirms the phone reboot-loops. Video `IMG_0661.mov` is 3.57 seconds: the visible XNU console is at the Skywalk self-tests, then the display goes black by the final frame. No panic string or reboot-request/howto line is visible. This is consistent with a reset, but does not identify the requester or prove the screen returned to the same stage.
- The current `veux-xnu-39973136957-rw.img` boot args had `veuxlog=0`, so the existing VEUX bounded userdata tail logger was disabled. Prepared a diagnostic repack of the exact run-39973136957 kernel with only `veuxlog=1` changed; root mode remains `rootrw=1 ufsrw=1`. The persistent logger writes its bounded 4 MiB ring plus 4 KiB header in userdata tail slack and flushes with SYNCHRONIZE CACHE. It starts only after the UFS userdata path is recognized, so a reset before that point may still leave no ring.
- Diagnostic image `shim/out/veux-xnu-39973136957/shim-boot-veux-xnu-39973136957-rw-log.img`, 17,121,280 bytes, SHA-256 `0095ec0b94c6e2fe1efd3cb86d2f09f4aa8a18d964abd2155623c4f31ecd852b`. Android boot-v2 unpack verification: XNU payload matches the generated log-enabled payload; shim kernel and selected VEUX DTB match the known template byte-for-byte. It uses the same CI-passed kernel from run `39973136957`; no XNU source or binary changed.
- Fastboot verified `veux`, slot `b`, and `boot_b` capacity `0x8000000`; flashed only `boot_b`, selected B, and reboot returned OKAY. The phone reappeared in fastboot after the loop. `fastboot reboot recovery` returned OKAY, but neither ADB nor fastboot had re-enumerated 35 seconds later, so the tail ring has not yet been retrieved. Need recovery ADB to read it and identify the initiating reboot path. Userdata/root image is expendable per user.

## >>> UPDATE 2026-10-23 (launchd bootstrap boot-args test) <<<

- Recovery ADB was explicitly reached by switching the active slot to A before
  `fastboot reboot recovery`. The read-only tail-ring pull succeeded as root;
  the log is `research/veux-logs/xnu-veux-20261023-083041.txt` (same ring,
  flush sequence 2 on the repeat pull at 08:34:18).
- The log confirms `rootrw=1 ufsrw=1`, first successful UFS read and write,
  successful HFS journaled root mount, launchd exec, and mount helper exit
  status 0. It then records ignition failing to find Preboot (error 25), cache
  entries not in the unavailable trust cache, and launchd starting the
  `finish-obliteration` task (`mobile_obliterator`). The ring ends there.
- Prepared a boot-args-only repack of the exact CI kernel from run
  `39973136957` (SUCCESS, commit `f2c92747e60d4cf5dbf54845e78ad007c23a4afc`,
  kernel SHA-256
  `018f16ad435bb30a5086380927c84b41cb86236136f86faed3619e3424b2dd3a`). Added
  `ignition_level=1 launchd_unsecure_cache=1 wdt=-1 wdt_test=no_user_checkin`
  to the previous RW/logger arguments. The XNU payload outside its command-line
  field, shim kernel, and VEUX DTB are unchanged.
- Candidate image:
  `shim/out/veux-xnu-39973136957/shim-boot-veux-xnu-39973136957-rw-log-launchd.img`,
  17,121,280 bytes, SHA-256
  `0d50527f71e7685dd438c5000ac7218167663b24191918fac19569fb1d0c57fc`.
  Unpack verification confirmed the ramdisk payload, shim kernel and DTB.
- Fastboot confirmed product `veux`, unlocked bootloader, slot A, and `boot_b`
  capacity `0x8000000`; flashed only `boot_b`, selected slot B, and reboot
  returned OKAY. No userdata write or root-image change was made by the host.
  Neither ADB nor fastboot had re-enumerated 50 seconds after reboot; outcome
  of this boot-args test remains unknown pending phone re-enumeration/log pull.

## >>> UPDATE 2026-10-23 (diagnostic repack boot follow-up) <<<

- Recovery ADB was available in slot A (`veux`, serial `4078cac030c8`). Pulled
  `research/veux-logs/xnu-veux-20261023-adb-on.txt`; it is still the prior
  22,826-byte ring at flush sequence 3, ending at `exec keybagd`. It confirms
  mount-phase-2's mount helper exited 0; missing data volume and optional
  BindFS paths were reported, but did not fail that helper. No panic, reset
  request, or later boot-stage output was flushed.
- Re-selected already flashed slot B and issued `fastboot reboot` (OKAY). The
  device did not re-enumerate as ADB or fastboot after about 52 seconds, so the
  new boot has not yet yielded a readable ring. It is not possible to identify
  the reset source from the available capture. No further flash or userdata
  write was performed.
- User reported fastboot; verified `veux`, slot B, then restored slot A and
  issued `fastboot reboot recovery`. Recovery ADB came up as root. A new ring
  pull (`research/veux-logs/xnu-veux-20261023-recovery-again.txt`) reports
  flush 2 and ends at `exec MSUEarlyBootTask`; it has no panic/reset-request
  text. The boot args in that capture still include `unentitled_ios_sim_launch=1`
  and `rootrw=1 ufsrw=1`; mount-phase-1 and mount-phase-2 helpers both exit 0.

## >>> UPDATE 2026-10-23 (MSU task and reboot-path instrumentation candidate) <<<

- Latest recovered ring (`research/veux-logs/xnu-veux-20261023-recovery-again.txt`) is an RW boot (`rootrw=1 ufsrw=1`). Both mount phases exit 0 and the HFS+ root mounts journaled. The visible ring ends at launchd starting `MSUEarlyBootTask`; this is a capture boundary, not evidence the task caused the reboot. Its launchd timestamp is `1970-01-01`, a known clock issue for later time-based checks.
- Extracted `/usr/libexec/MSUEarlyBootTask` from `/Users/vivien/Downloads/ios16-root-20H392.simg`; it is arm64 Mach-O, SHA-256 `4461470c4bcb4afe3b5bc89209d8983765af9a8112141e410635e0fcec7f763f`. Ghidra pseudocode shows the no-update path prints `MSUEarlyBootTask: I have nothing to do. Goodbye!!`; the observed missing booted-OS-data path also only prints an error. The direct callee list has no reboot/restart call. This does not identify the actual reset source.
- `/System/Library/xpc/launchd.plist` has 530 `LaunchDaemons` entries but no `MSUEarlyBootTask` string or ordered boot-task list; the task sequence is not represented there. The current ring ends before any later task. SWEET's `tools/sweet-root-tweaks.py` does not disable MSUEarlyBootTask; its root-image edits instead remove CommCenter jobs and disable VirtualAudio/recorder paths. No VEUX userland edit is warranted for the normal no-update branch. Later hardware-bound daemons remain candidates, but their order after MSU is not established by this capture.
- Extended VEUX patch 0115 to log the reboot caller PID/name, `howto`, full message text and its hex bytes at `reboot_kernel` entry, then synchronously flush the ring before shutdown. This central entry covers reboot syscalls and in-kernel callers; there is no separate `boot()` function in this source tree. Panic rendering and `IOPlatformExpert::haltRestart()` also call the bounded, nonblocking UFS ring flush; flush failures are reported in the console.
- Before PSCI, `haltRestart()` prints a ten-second countdown, flushes the countdown to the ring, then uses `/psci` `method` to select SMC/HVC and issues the existing PSCI reset/off IDs. Standalone PSCI reset timing was confirmed by `IMG_0646.mov` before the known 11-second watchdog bark. The current root remains RW for the next diagnostic boot.
- CI run `40047161029` failed at compile: `kern_shutdown.c` lacked a declaration for `veux_log_flush_sync()`. Added the local VEUX-only prototype in patch 0115; rerun CI before packaging or flashing. The failed run produced no kernel image.
- CI run `40048143567` compiled XNU but failed its post-build source assertions: patch 0097 was skipped because patch 0088 had already changed the same UFS file. Consolidated the safe opt-in userdata/LUN0 log guard, bounded lock-safe ring snapshot, and printk-to-ring tap into patch 0088 and removed the duplicate patch 0097. Rerun CI; the failed run produced no kernel image.
- CI run and final image hash: pending.
- CI run `40049901404` failed during `pe_serial.c` compilation. The earlier consolidated logger patch had inserted a duplicate printk tap at a stale line number, outside any function; the active console tap is already in `osfmk/console/serial_console.c`. Removed the misplaced hunk, updated the CI assertion to check the actual console path, and taught repo validation that historical patch 0097 was merged into 0088. Local repo validation, the PSCI ADT check, and `git diff --check` pass. No kernel artifact was produced; rerun CI before packaging or flashing.

## >>> UPDATE 2026-10-23 (reboot observability and PSCI reset test) <<<

- Corrected console ring hookup: `veux_log_append(c, size)` is in the active
  XNU console path (`osfmk/console/serial_console.c`). Removed a duplicate
  hunk that had landed outside a function in `pe_serial.c` and caused CI's
  compile failure. Source check now verifies the actual path. Repo validation
  recognizes that removed patch 0097 was consolidated into patch 0088.
- Commit `1ce5f7a966a8bab8140cbb82529285c28ecc471a` passed CI run
  `40051486458` (macOS 13.5 / DEVELOPMENT / VEUX; all build and diagnostics
  steps passed). Kernel artifact `kernel.development.veux` SHA-256:
  `7fd61d08151886aa79c18f470a68b8b48d57c10b49bcfb15c36e78325d27912b`.
- Built the XNU payload with fresh VEUX high-memory ADT (`/psci method=smc`),
  unchanged current root mode and diagnostics:
  `rootrw=1 ufsrw=1 veuxlog=1`, framebuffer console enabled, launchd/cache
  diagnostics, and `unentitled_ios_sim_launch=1`. The Android boot-v2 wrapper
  uses the existing VEUX DTB and the CI-derived payload. Extracted components
  match the payload, shim kernel, and DTB inputs. Boot image SHA-256:
  `ee68fe5fa4b67f3de22807d92792f0d65ca2b6caaeb24630b8a0b7859bccd460`.
- Host did not have `aarch64-linux-gnu-gcc` or `mkbootimg`; the shim was built
  with the installed Android NDK Clang/LLD cross-target, and boot-v2 components
  were assembled with the verified header layout. XNU itself is the CI-built
  kernel above. The standalone PSCI probe video previously showed reset around
  5-6 seconds, ahead of the 11-second watchdog period; this image adds a
  10-second countdown for filming.
- Fastboot verified product `veux`, unlocked bootloader, active slot A, and
  `boot_b` size `0x8000000`. Flashed only `boot_b`, selected slot B, and reboot
  returned OKAY. At 75 seconds after reboot, neither ADB nor fastboot had
  re-enumerated. New ring has not yet been retrieved, so the reboot requester
  and reached stage remain unknown.

## >>> UPDATE 2026-10-24 (skip fatal keybag init boot task) <<<

- Captured ring `research/veux-logs/xnu-veux-20261024-after-psci-test.txt`
  identifies the reboot source: launchd runs `keybagd --init`; keybagd logs
  `FATAL KEYBAG ERROR: failed to load system bag`, two missing device-tree
  options messages, then `MKB_INIT: Rebooting...`. The reboot hook records
  `VEUX reboot requested howto=0x0 caller=keybagd pid=0xb message="<none>"`.
  It is keybagd itself, not launchd reacting to a fatal-job policy. PSCI reset
  executes after the visible countdown; this boot had `rootrw=1 ufsrw=1`, and
  mount helpers both exited 0 before keybag initialization.
- Root image `/Users/vivien/Downloads/ios16-root-20H392.simg` contains a
  `KeyBagKeys=SWEET` systembag and the ADT has `/defaults/no-effaceable-storage`.
  The failure is therefore keybagd's inability to load a device-backed system
  bag/SEP state; it is not an absent systembag file. The ordinary
  `com.apple.mobile.keybagd.plist` has `RunAtLoad=true`, `OnDemand=true`,
  `EnablePressuredExit=true`, and first-unlock notify/Mach services, but no
  `KeepAlive`, `Critical`, or `ExitTimeOut`. Separately, the embedded
  `launchd.__config` boot task has `AllowCrash=true`; removing that task is the
  minimum way to prevent its explicit reboot while leaving the daemon plist
  untouched. Exact before/after task config and reversible diff are in
  `research/veux-logs/launchd-config-keybag-{before,after}.plist` and
  `research/veux-logs/launchd-config-keybag.diff`.
- Built host-side candidate
  `/Users/vivien/Downloads/ios16-root-20H392-keybag-skip.simg` by removing
  only `Boot.keybag` (`/usr/libexec/keybagd --init`) from the embedded launchd
  config, preserving the original fixed-size section with padding, and
  ad-hoc re-signing `/sbin/launchd`. The regular keybagd daemon plist and all
  kernel files are unchanged. Candidate is a structurally verified Android
  sparse image with 244 changed filesystem blocks. SHA-256:
  `f7d7bfe0e4dd12d44f38a41d8e0c3b131f6503fe0682c798e0b75e946fdd1b3e`.
  Baseline image SHA-256 remains
  `9d20904cf584270fbb47ca968141cc33508e10ac7f649c03b0dd3581020cbf77`.
- The existing kernel is unchanged; CI run `40051486458` passed and the
  already-flashed boot image hash is
  `ee68fe5fa4b67f3de22807d92792f0d65ca2b6caaeb24630b8a0b7859bccd460`.
  Host-side root image edit adds no kernel build. Recovery ADB is online as
  root on slot A; device reports `veux`, serial `4078cac030c8`. Next action is
  to flash the candidate to userdata and retest before considering any further
  changes.
- If boot proceeds, SEP/keybag consumers likely include `securityd` (keychain
  and protected key operations), `lockdownd` (pairing/protected services),
  `authd`/`akd` (authentication and identity), and later SpringBoard/backboardd
  services (device-unlock and protected-data state). A missing SEP can make
  operations unavailable or cause individual jobs to fail; it does not imply
  every consumer must crash. Existing SWEET XNU patch 0038 adds an AppleKeyStore
  IOKit stand-in; this VEUX test deliberately prefers the minimal userland
  bypass and does not port that kernel patch yet.
- For headless progress, hardware-dependent candidates to disable only when
  the ring shows they block boot are CommCenter/baseband, Wi-Fi, AppleKeyStore
  consumers that demand SEP-backed keys, mediaserverd camera/audio services,
  GPU/display acceleration, sensor/motion/location services, and restore or
  provisioning tasks. Existing root tweaks already remove CommCenter jobs and
  disable VirtualAudio/recorder paths. Keep changes per-job and record each
  edit here; launchd timestamps at 1970 remain a known clock issue.
- Flashed the candidate to `userdata` from fastboot on verified product
  `veux` (slot A recovery was active before switching to bootloader). All 16
  sparse chunks reported `OKAY`; then selected slot B and issued `fastboot
  reboot`. As of 2026-10-24, neither ADB nor fastboot has re-enumerated after
  roughly two minutes. The edited boot's result and ring are not yet available;
  do not infer the next failure from the old ring.
- The first candidate's photo showed `initproc exited -- exit reason namespace
  7 subcode 0x1 description: undefined boot task keybag`: launchd requires the
  `Boot.keybag` task name to exist. Corrected the host image from the preserved
  raw baseline by retaining the task and setting `Program=/usr/bin/true`,
  `ProgramArguments=['true']`, `PerformAfterUserspaceReboot=true`, and
  `AllowCrash=true`. The keybagd LaunchDaemon plist is still unchanged.
  Re-signed `/sbin/launchd` ad hoc; `codesign --verify` reports valid on disk
  and its designated requirement is satisfied. Embedded config re-parses
  with the expected task dictionary. The corrected full-write sparse image
  `/Users/vivien/Downloads/ios16-root-20H392-keybag-noop.simg` has SHA-256
  `5da713f38323460f33b20679368fc97f808b40eb1b5129ad8d84f51e01cabd0d`.
- Flashed the corrected image to `userdata` from fastboot, with `-S 512M`;
  all 24 chunks reported `OKAY` (297 seconds). This candidate writes zero
  blocks explicitly to clear stale data from the failed first edit. It is a
  root-image-only change; the kernel and its CI-passing hash are unchanged.
  Recovery ADB later read the persistent VEUX ring from userdata; it is saved
  as `research/veux-logs/xnu-veux-20261024-after-keybag-noop.txt` (36,437
  bytes, flush sequence 5). The candidate ran with `rootrw=1 ufsrw=1`; HFS
  mounted successfully (`errno=0`), both mount phases exited 0, MSUEarlyBootTask
  and FIPS completed, and launchd logged `Early boot complete. Continuing
  system boot.` The `keybag` boot task logged “optional boot task not present”;
  keybagd did not run and the old keybag reboot is absent. The exact reason the
  embedded task was treated as absent despite the host-side no-op plist change
  still needs verification. Later in launchd startup, the ring logs
  `shared_region ... vm_shared_region_start_address() failed` and 20
  `dyld_shared_cache_arm64.*: not in trust cache` warnings. No panic or reboot
  request appears after this change in the ring. After returning to slot B and
  rebooting, the phone did not enumerate over ADB or fastboot for 60 seconds,
  so SpringBoard is not confirmed and another ring cannot be read until the
  device returns to recovery. CI/kernel/boot image are unchanged; no new kernel
  build or flash was made in this check. The original sparse baseline was
  removed temporarily to make room for image conversion; its expanded raw
  baseline is still at `/tmp/ios16-root-20H392-keybag-base.raw`.

## >>> UPDATE 2026-10-24 (visible post-launchd userland probe) <<<

- Reopened the exact previously flashed boot image
  `shim/out/veux-xnu-40051486458/shim-boot.img`, SHA-256
  `ee68fe5fa4b67f3de22807d92792f0d65ca2b6caaeb24630b8a0b7859bccd460`.
  Extracted the XNU payload ADT at offset `0xfc26d0` (11,468 bytes), rather
  than relying on the ADT generator. `/chosen/asmb/lp-sip0=0x6f` and
  `lp-sip1=1`; the same payload has `/chosen/framebuffer@85200000`
  (1080x2400 simple-framebuffer), `/veux-ufs`, and `/psci` compatible
  `arm,psci-1.0`, method `smc`. Payload command line is
  `debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam -noprogress
  rd=ufsroot0 unentitled_ios_sim_launch=1 veuxlog=1 veuxfb=1
  veuxfbconsole=1 ignition_level=1 launchd_unsecure_cache=1 wdt=-1
  wdt_test=no_user_checkin rootrw=1 ufsrw=1`. ADT matches the generator's
  semantic values; phandles/random per-build details can differ. ADT does not
  encode boot-args; those are in the payload header.
- SWEET's raw boot logs are not in the local checkout, but retained notes cite
  boot 0029's `vm_shared_region_start_address() failed` followed by launchd's
  ignition failure for a separate missing-preboot reason, and boot 0032's
  `not in trust cache` warnings followed by successful shared-cache mapping and
  launchd startup. The current VEUX ring likewise reaches
  `Early boot complete. Continuing system boot.` after the warnings. Treat
  these as non-blocking evidence; they are not the current screen freeze cause.
- `veux-hello.c` is an ad-hoc-signed iOS arm64 LaunchDaemon candidate. The
  existing VEUX AMFI policy recognizes signed rootfs executables as platform
  binaries and attaches signature entitlements; this test needs no special
  entitlements. The source sends a hello and `VEUX_FB_GREEN_BLOCK` token to
  `/dev/console`, emits an os_log message, and records the console open errno
  to `/private/var/log/veux-hello.log`. `com.veux.hello.plist` requests RunAtLoad
  and routes stdout/stderr to `/dev/console`. XNU patch 0116 mirrors
  `/dev/console` writes to the existing simplefb text console and paints a
  green square on the marker. This is a limited bring-up diagnostic, not the
  missing IOSurface/IOMobileFramebuffer service.
- Root-image installation is not yet verified: the only packaged hello sparse
  image used an earlier binary without the marker and is superseded. Its
  external `/Volumes/savedrive` disappeared before readback; do not flash that
  package. The original sparse root image remains untouched, but the current
  hello candidate must be installed and repacked after the drive returns.
  The HFS mount was made `noowners`; we have not validated launchd's expected
  root ownership in the final image. Keep this as an explicit packaging check.
  Reversible edit inventory and hashes are in
  `research/veux-logs/veux-hello-root-image.diff`.
- Current VEUX has simplefb for kernel text only. Patch 0116 exposes userspace
  `/dev/console` text and a single-color marker, but no IOMobileFramebuffer,
  IOSurface mapping/user client, backboardd display service, or HID touch path.
  SWEET notes document the longer path: AppleCLCD/IOMobileFramebuffer,
  IOSurface, backboardd swaps, HID, then SpringBoard/Setup. For VEUX the
  incremental target is first a visible hello block and console line; after
  that, a headless shell/service proof; a home screen requires the display and
  IOSurface/backboardd path. This boot's ring only proves early boot tasks and
  launchd's early-boot completion; it cannot enumerate jobs after the lost
  tail. No job exits after that point are confirmed.
- Keybag review: the tested no-op landed in embedded `launchd.__config` boot
  task configuration, not the ordinary `com.apple.mobile.keybagd.plist`.
  Latest ring says the optional `keybag` boot task was absent and does not show
  keybagd execution. No keybag dependency is established from the captured
  post-early-boot tail.
- Wall clock remains 1970 in launchd logs. No new root image was flashed and no
  new CI result exists yet for patch 0116. The earlier flashed image remains
  hash `ee68fe5f...`; the superseded hello sparse candidate hash
  `45eeb1e576ce7d9732b2d96b61c4f48739854b057c512f32b2b88ce91c54f3b8` is not
  suitable for flashing.
- The hello plist and ad-hoc-signed executable were installed in the disposable
  expanded HFS+ working copy and checked, but `img2simg` ran out of host disk
  space during repacking. The generated file
  `/Users/vivien/Downloads/ios16-root-20H392-veux-hello.simg` was truncated
  (hash `cfbd130cc77fb7bbd67ea3b902b6584318f9be572229a8d8fbf945a5d3693488`)
  and its Android sparse chunk table extended past EOF. It was deleted and
  must never be flashed. No hello changes were flashed to userdata. The valid
  keybag-noop source remains unchanged at
  `/Users/vivien/Downloads/ios16-root-20H392-keybag-noop.simg`, SHA-256
  `5da713f38323460f33b20679368fc97f808b40eb1b5129ad8d84f51e01cabd0d`.
  Host HFS used `noowners`, so UID/GID could not be verified; `fsck_hfs -fn`
  was cancelled after several minutes without output. Full source/hash state is
  recorded in `research/veux-logs/veux-hello-root-image.diff`.
- CI for commit `832f02d353201b76f93c68e4f0754b479a574929` passed in run
  `40092567840`: https://github.com/59c84486t9-alt/ios-veux/actions/runs/40092567840.
  Kernel artifact SHA-256 `76128eb5f03dc234ad09c2e93c0e44a023237f357c58edfb37c270d2b75edb8b`.
  Repacked Android boot-v2 image at
  `shim/out/veux-xnu-40092567840/shim-boot.img`, 17,121,280 bytes,
  SHA-256 `0ac083af37c44833afb9a622ee91da48e838dbdbe89d57e11504ce47df3ae8aa`.
  In-memory unpack validation confirmed the v2 header, unchanged shim kernel
  and VEUX DTB, exact CI payload and image ID. The phone enumerated in
  fastboot as product `veux`, unlocked, current slot B; ADB was absent. The
  new boot image was flashed to `boot_b` successfully; the root image flash
  failed before transfer (`Failed reading from userdata`). Userdata still has
  the prior keybag-noop root. The next boot will test console mirroring only;
  the hello LaunchDaemon is absent from the flashed root.

## >>> UPDATE 2026-10-24 (slot-A recovery and recovered VEUX boot ring) <<<

- User requested slot A recovery. Fastboot identified the phone, active slot B;
  `fastboot set_active a` and `fastboot reboot recovery` both returned OKAY.
  Recovery ADB connected as root and reports `ro.boot.slot_suffix=_a`.
  No boot, recovery, or userdata contents were flashed during this collection.
- Recovery `/sys/fs/pstore` is empty. Its `/tmp/recovery.log` records recovery
  startup, clearing BCB, and ADB enablement; it contains no XNU trace. Recovery
  `dmesg` repeatedly reports missing `ipa_fws.mdt` (`rc=-2`), an Android
  recovery firmware warning unrelated to the captured iOS boot.
- Read the last 1,025 4 KiB blocks of userdata: 4,198,400 bytes at byte offset
  109,152,378,880 (partition size 109,156,577,280 bytes). The ring now has
  `VEUXLOG1`, version 1, 4 MiB capacity, 28,022 log bytes, flush sequence 6.
  Current tail SHA-256 is
  `4caecfb557ee4f9334d75e9afbc0a0f2191e6aaa087d29895e42112174e9953d`; it
  differs from the pre-logger blank-tail backup because this boot wrote the
  enabled diagnostic ring. No restore was attempted.
- Decoded ring: `research/veux-logs/recovery-slot-a-20261024/xnu-ring.txt`;
  raw tail and recovery dmesg are alongside it (research/ is git-ignored).
  Ring has not wrapped. XNU reports `rootrw=rw ufs_write=enabled`, HFS journal
  replay completes, first UFS write succeeds at LBA `0x2db428`, HFS mounts, and
  root mount returns errno 0. Launchd reaches “Early boot complete. Continuing
  system boot.” with no panic/reboot text in the complete captured ring.
- `MSUEarlyBootTask` executes but cannot query `BootManifestHash` and cannot
  find the booted OS data path; boot proceeds into FIPS, keybag (optional task
  absent), usermanagerd, and the remaining listed early tasks. FIPS POST passes.
  `prng_seedctl` later cannot access `kern.prng.user_reseed_count` and reports
  virtual-random load failure; launchd cache loading then succeeds. Missing
  BindFS paths under factory/Pearl produce `ENOENT`, while the mount helper
  returns raw status 0. The log ends at launchd's early-boot-complete message;
  it does not identify why the screen remains at the console afterward.
- Recovery is the current device state on slot A. The experimental XNU image is
  still on boot_b; the last CI image was run `40092567840`, SHA-256
  `0ac083af37c44833afb9a622ee91da48e838dbdbe89d57e11504ce47df3ae8aa`.

## >>> UPDATE 2026-10-24 (post-early-boot liveness and cached hello job) <<<

- User reports iOS reaches launchd's “Early boot complete. Continuing system
  boot.” while the framebuffer remains on the console. The most recent captured
  ring still ends at that message, so the post-early-boot process state is not
  known yet; the phone is in slot-A recovery while this candidate is prepared.
- Added XNU patch `0117-veux-post-early-boot-liveness.patch`. It starts once
  `console_write` sees launchd's early-boot-complete line. Every 10 seconds it
  prints process/thread totals, up to 16 processes (PID/PPID, name, numeric
  state, user/system CPU microseconds and interval deltas, thread count, saved
  user PC), marks direct launchd children and PIDs newly seen since the prior
  sample, reports launchd's first listed thread wait event/block hint/user PC,
  reports the already-running idle sampler's sample/tick/runqueue values, and
  synchronously flushes the diagnostic ring. Console `printf` reaches the
  framebuffer and ring through the existing VEUX console paths. CI has not yet
  tested this patch.
- Launchd's current binary contains boot-argument strings
  `launchd_verbose_coalition_logs=` and `launchd_log_verbose_meta_limit=`;
  there is no general `launchd_verbose` string. Existing launchd boot-task
  messages are already sent through `/dev/console` and therefore mirrored to
  the screen/ring. The next payload will set the two recognized coalition
  logging arguments (`launchd_verbose_coalition_logs=1` and
  `launchd_log_verbose_meta_limit=128`) for additional coalition metadata;
  this is not evidence of a universal verbose-job switch.
- In the mounted temporary HFS working image, the hello plist and ad-hoc-signed
  arm64 executable were present but absent from the embedded launchd plist's
  `LaunchDaemons` cache. Added the plist dictionary to that cache and created
  a 512-byte `/private/var/db/prng.seed`. The exact root-image edits and
  reversal steps are recorded in
  `research/veux-logs/veux-postboot-liveness-root-image.diff`; verified hashes:
  launchd cache `bd2a421fe37bf1748d0cc9bc9a9bd4bfafd945e61cf6d70e08e608b50c9bfd4f`,
  hello plist `e3d8bf685248e6935e36843aba1071174d7b79a1f4d08d350d383f775254e44c`,
  hello binary `ea59048d1967eba76bebdb3ab87fc851aff05c0baed5d83cacbf7eedc1acbf13`,
  seed `5a6c4536f5e188dda65185cee3ae0a3f69ab8936edbf68f0587ed41066306fd0`.
  Source sparse image is unchanged. This temporary mounted image has no
  flashable repack yet, and none of these root edits are on the phone.
- The sparse root source is 11.3 GiB; the macOS data volume has only 5.5 GiB
  free. The mounted expanded image's backing file was unlinked by an earlier
  failed repack. Its current changes are verified in place but must be
  preserved or recreated before detaching the mount. No flashable image hash
  or new CI run is claimed yet.


## >>> UPDATE 2026-10-24 (liveness CI and boot test) <<<

- CI run `40103755855` built commit `b8c37de23d8bfeb238ef282c72f246eab091e1e8`; all workflow steps passed. The earlier run `40102803176` checked out stale remote SHA `1e1196722b11f33ec86bba85fd0af702e01af4e8`, was cancelled, and was not used for the build result.
- Kernel artifact SHA-256: `600ff2842699f5e0b92565f37f811e14446f7725487f4607bafaa55b5fba8874`. Reused the existing 18.0.0 VEUX shim boot-image layout and replaced the equal-size XNU payload only; verified the packed boot image unpacks to the new payload and the existing DTB. Payload SHA-256 `991c02b2d6b4d65fb3fc74656ae721e7f815e273a1a64983cdbada6160034e64`; boot image SHA-256 `984cbdcbcd17c340aa48e56195de462b1a4a2704fa2fe7002975fe0664d0b294`. Payload boot args retain the known `rootrw=1 ufsrw=1` configuration and add `launchd_verbose_coalition_logs=1 launchd_log_verbose_meta_limit=128`.
- The host working HFS target was applied from recovery to `/dev/block/by-name/userdata` as 1,675 changed 4 KiB blocks in 285 writes (6,860,800 bytes); no other userdata ranges were written. Readback covered all 2,155 host-target delta blocks and exactly matched the prepared target (SHA-256 `9f4ba7897a62c750fc5ba33c78dfbfb485d650867c9e4b66dae425ae2519bba7`). The original sparse source is still unchanged. Changes and reversal steps are listed in `research/veux-logs/veux-postboot-liveness-root-image.diff`.
- Flashed the verified image to `boot_b`, selected slot B (fastboot confirmed), and rebooted. Awaiting screen/console observation to determine whether the liveness sampler and cached hello job ran. Recovery/ADB had no mount of userdata during the block update.
- Launchd binary recognizes only the coalition verbosity args above; no general verbose-job boot arg is present. Its boot-task messages already reach `/dev/console`; the patched console mirror carries them to the framebuffer and ring. The raw SWEET log files referenced by `../ios-sweet/NOTES.md` are absent from this checkout, so a definitive job-by-job SWEET/VEUX post-early-boot comparison and first missing job remain unverified.
- The PRNG seed file exists in the edited root. The device clock has not been set: earlier launchd lines show 1969/1970, and recovery provides no known RTC/time source for this boot.
## >>> UPDATE 2026-10-24 (HFS mount failure and userdata restore) <<<

- Latest phone photos show the HFS+ root mount failing before launchd:
  `hfs_mountfsplus: encountered error 5`, `hfs_mountroot failed: 5`,
  `VEUX ROOT mount result errno=0x13`, and `cannot mount root, errno = 19`.
  The log also reports catalog key #27 with invalid length (0) and
  `hfs_mark_inconsistent: Runtime corruption detected on ., fsck will be
  forced on next mount`. These are direct screen observations; the precise
  cause of the catalog corruption is not yet established.
- Slot-A recovery was reachable over ADB using SDK platform-tools 37.0.0
  (`adb` Homebrew 37.0.1 had a local server ACK failure). Recovery confirmed
  `_a`; userdata is `/dev/block/sda22`, 109,156,577,280 bytes. No `fsck_hfs`
  utility is present in that recovery environment.
- Restored userdata with the known original sparse image
  `/Users/vivien/Downloads/ios16-root-20H392-keybag-noop.simg`, SHA-256
  `5da713f38323460f33b20679368fc97f808b40eb1b5129ad8d84f51e01cabd0d`.
  Fastboot product was `veux`; all 16 sparse chunks returned OKAY. This
  overwrote only userdata. The later fastboot set-active/reboot command did
  not execute: the device disconnected from USB after the flash, and neither
  ADB nor fastboot currently enumerates it. Replug and confirm fastboot
  enumeration before selecting slot B and booting the already-installed
  liveness kernel. No new kernel build or CI run was made in this step.
- The restored source image is clean with respect to the saved source hash but
  does not contain the newer host-side hello plist/cache edits; those edits
  existed only in the prior device-side sector delta and were overwritten by
  this restore. Do not claim the hello daemon is installed in the current
  userdata image.
- Follow-up phone photo after the restore shows launchd output, including
  `Early boot complete. Continuing system boot.`, validated-cache delivery,
  and boot tasks `finish-restore`, `finish-demo-restore`, and `sysstatuscheck`.
  This confirms the restored HFS root mounted and launchd progressed beyond
  early boot; it does not confirm SpringBoard or that the hello job ran. No
  ADB or fastboot device is currently enumerated, so leave the phone running
  and request another screen capture rather than rebooting it.
- A later photo after several minutes still shows the same launchd cache and
  boot-task lines, with no `VEUX LIVE:` process snapshot, task completion,
  panic, or SpringBoard. The 0117 sampler is intended to report within 10
  seconds of early-boot completion; this observation means the live sampler
  is not visibly reporting (whether because the flashed kernel differs or
  its worker failed to run is unproven). Further passive waiting on this
  screen is unlikely to resolve that diagnostic gap.

## >>> UPDATE 2026-10-24 (passive sysstatuscheck investigation; no reboot) <<<

- No phone interaction that can change state was performed. Both `adb devices`
  and `fastboot devices` currently return no device; the screen photo is the
  only evidence for the current live boot. Do not claim a current PID list,
  thread count, wait event, idle-PC sample, or UFS lifetime counters: the photo
  shows the kernel register/diagnostic panel, not the `VEUX LIVE:` format, and
  the kernel has no issued/completed/outstanding UFS counter panel.
- Existing saved ring `research/veux-logs/recovery-slot-a-20261024/xnu-ring.txt`
  contains `Doing boot task` then `exec sysstatuscheck` at 16:01:12.329415;
  14 ms later it logs `exec prng_seedctl`, followed by cache delivery and
  `Early boot complete. Continuing system boot.` Thus launchd did exec the
  helper and moved on in that captured boot. The current photo lacking the
  `exec` line is a different/incomplete console capture and does not establish
  that this current attempt executed or is still running.
- Read-only host inspection of the restored clean root image found the
  `sysstatuscheck` check marker absent at
  `/private/var/mobile/Library/MemoryMaintenance/sysstatuscheck_should_check`.
  `sysstatuscheck` is arm64 Mach-O (109,280 bytes), SHA-256
  `c2ca9544e4a141c9e7dea2f493f12c6305f7def277445839196a970209d2fa57`.
  Ghidra analysis of its entry path shows it first stats and removes that
  marker; when absent it returns status 1 immediately. When present, it checks
  debug/KASAN boot args and jetsam properties, samples kernel memory, and
  compares against `KernelHighWaterMark`. On the low-memory branch it rechecks
  after a 60-second delay, checking in to `IOWatchdog` during that delay; if
  still over the threshold it writes `/var/mobile/Library/Logs/khwm.log`,
  syncs, then requests `_reboot_np(0x1c00, message)` (and has a dark-boot/
  `_reboot(0)` fallback). The only explicit child wait in the examined entry
  call tree is `wait4()` for `/usr/bin/zprint`, on the low-memory measurement
  path. This entry path does not wait on a Mach service; IOWatchdog check-in is
  a scalar IOKit call and its failure is printed to stderr. Static evidence
  does not prove which branch ran on the current phone.
- The extracted launchd boot-task configuration at
  `research/veux-logs/launchd-config-keybag-noop.plist` specifies
  `PerformAfterUserspaceReboot = true`, `Program = /usr/libexec/sysstatuscheck`,
  and `RebootOnSuccess = true`; it has no task execution timeout. The global
  `SIGTERMTimeout = 3` is only a termination grace period, not a boot-task
  timeout. The captured ring's continuation proves the helper did not hold up
  boot in that run. Because the marker is absent from the restored host image,
  an optional/absent task configuration or a zero-exit stub is premature; first
  obtain the live PID/wait/counter snapshot with the correct kernel running.
- The UFS code issues one polled transfer at a time and gives a command a
  5-second deadline; it clears the transfer-list doorbell and reports
  `ETIMEDOUT` on expiry, or logs OCS/UPIU/response/status and returns `EIO` on
  controller/protocol failure. The captured ring proves a successful initial
  read, successful write, HFS journal replay, and root mount errno 0. It does
  not prove all later reads completed, nor expose current queue/interrupt state.
  A paging read stuck for minutes is therefore not supported by the captured
  evidence; current counters are still needed to rule it out conclusively.
- No image or source changes were made for this investigation, so there is no
  new root-image diff, CI run, or image hash. Last liveness candidate remains CI
  `40103755855`, kernel SHA-256
  `600ff2842699f5e0b92565f37f811e14446f7725487f4607bafaa55b5fba8874`, payload
  SHA-256 `991c02b2d6b4d65fb3fc74656ae721e7f815e273a1a64983cdbada6160034e64`,
  and boot image SHA-256
  `984cbdcbcd17c340aa48e56195de462b1a4a2704fa2fe7002975fe0664d0b294`. The
  recorded userdata restore source SHA-256 is
  `5da713f38323460f33b20679368fc97f808b40eb1b5129ad8d84f51e01cabd0d`.

## >>> UPDATE 2026-10-24 (verified B readback and controlled boot) <<<

- User reported ADB enabled; connected to slot-A recovery as root. Read-only
  slot-B image readback of exactly 17,121,280 bytes SHA-256 matched the
  recorded CI image `984cbdcbcd17c340aa48e56195de462b1a4a2704fa2fe7002975fe0664d0b294`
  byte-for-byte. The boot header's 184,320-byte kernel is the unchanged shim
  (`09e0955c...`); the ramdisk payload is the XNU payload and matched
  `991c02b2d6b4d65fb3fc74656ae721e7f815e273a1a64983cdbada6160034e64`.
  The liveness XNU build in the payload was produced by successful CI run
  `40103755855` (commit `b8c37de23d8bfeb238ef282c72f246eab091e1e8`), kernel
  SHA-256 `600ff2842699f5e0b92565f37f811e14446f7725487f4607bafaa55b5fba8874`.
- Pulled the persistent ring in recovery to
  `research/veux-logs/xnu-veux-20261024-after-fastboot-recovery.txt` (36,048
  bytes, 5 flushes). It records `exec sysstatuscheck`, `exec prng_seedctl`,
  `exec launchd_cache_loader`, successful cache delivery, and
  `Early boot complete. Continuing system boot.` No later panic/reboot or
  `VEUX LIVE:` sample appears in this ring capture. It does record missing
  PRNG seed errors and the incorrect 1969/1970 wall clock. This establishes
  launchd progressed through early boot, but not the live process list or
  SpringBoard state.
- From recovery A, rebooted to bootloader, confirmed current slot A, set active
  slot B, confirmed current slot B, then issued `fastboot reboot`. No ADB or
  fastboot enumeration appeared during the first 45 seconds. No image was
  flashed in this step; no new CI run was needed. Await screen observation.

## >>> UPDATE 2026-10-24 (liveness patch was skipped by CI) <<<

- New screen photo shows the same launchd early-boot-complete text with a
  changing register/diagnostic panel and no later console messages. This proves
  continuing kernel-side activity, not launchd job progress. ADB and fastboot
  are not enumerating while the phone is in this state.
- Investigated why `VEUX LIVE` was absent: GitHub run `40103755855` explicitly
  logged `Skipping patch 0117-veux-post-early-boot-liveness.patch ... error:
  patch failed: bsd/conf/files:105`. The builder treated it as a warning and
  CI nevertheless succeeded. The actual boot-B readback matches image hash
  `984cbdcbcd17c340aa48e56195de462b1a4a2704fa2fe7002975fe0664d0b294`, but
  that image contains no `VEUX LIVE:` / `VEUX IDLE:` strings or liveness
  symbols in its XNU payload. So the liveness instrumentation was not present;
  the lack of its output says nothing about whether launchd is blocked.
- Corrected patch 0117's `bsd/conf/files` insertion hunk and added required
  CI greps for its registration, console trigger, and output string. This
  change is not yet built or flashed; the prior run must not be treated as
  validating the liveness patch.

### Strict CI follow-up: 2026-10-24

- CI run [40131401609](https://github.com/59c84486t9-alt/ios-veux/actions/runs/40131401609) failed at the newly strict patch phase, as intended: `0031-sweet-read-write-root.patch` could not apply to `bsd/vfs/vfs_subr.c` after 0110 had already integrated and extended its `rootrw` logic for SWEET and VEUX. Its second change is also superseded by 0111's VEUX-aware dirty-root/journal handling. Added it to the explicit skip allowlist with the expected apply-failure signature and explanation. No kernel image from this run is accepted or flashed.
- macOS 13.5 remains the selected base: the workflow fetches XNU 8796 and the SWEET/VEUX patches are authored against that tree. Changing the host's current macOS version would not make a different XNU source version compatible; the workflow's `macos_version` selects the XNU release.
- Strict CI run [40131633045](https://github.com/59c84486t9-alt/ios-veux/actions/runs/40131633045) then exposed `0032-sweet-bearssl-sha1.patch`, a SWEET-only SHA-1 fallback whose build-file hunk conflicts with the current tree. The VEUX-targeted equivalent is `0089-veux-bearssl-sha1.patch`; added an exact, signature-checked allowlist entry for the SWEET-only patch. This run also failed safely before compilation; no image is accepted or flashed.
- Strict CI run [40132445120](https://github.com/59c84486t9-alt/ios-veux/actions/runs/40132445120) accepted the exact 0031/0032 allowlisted signatures and stopped on 0033 at `libkern/conf/files: patch does not apply`. 0033's SHA-384/512 source selection and implementation are SWEET-guarded, so skipping this patch adds no VEUX objects/symbols/behavior. Added the exact failure signature to the allowlist. No kernel was produced or flashed.

### Verification of allowlisted 0031 (2026-10-24)

`0031-sweet-read-write-root.patch` has two hunks across two files. Its changes are both represented in the patched source; the skip loses no VEUX behavior:

| 0031 hunk | Equivalent in the patched source snapshot | Result |
|---|---|---|
| `bsd/vfs/vfs_subr.c`: clear `MNT_RDONLY` when `rootrw` is set | `shim/out/0110-work/bsd/vfs/vfs_subr.c:1272-1283`; line 1279 parses `rootrw` (initialized to 0 at 1278) and line 1280 clears `MNT_RDONLY`. The mount begins with `MNT_RDONLY | MNT_ROOTFS` at line 1157. | Same rootrw behavior, widened to SWEET or VEUX by 0110. With no rw boot arg, the zero default leaves the root read-only. |
| `bsd/sweet_hfs/core/hfs_vfsutils.c`: allow a dirty, non-journaled root to mount read-write | `shim/out/0110-work/bsd/sweet_hfs/core/hfs_vfsutils.c:203-220`; root-only branch logs and continues, while non-root volumes still return `EINVAL`. | Same dirty-root exception, widened to SWEET or VEUX by 0110. |

The CI kernel manifest checks for the embedded `rootrw` and `ufsrw` strings and the compiled `VEUX ROOT mode=` diagnostic, including the read-only default and opt-in policy. It also checks the source invariants: the root mount starts with `MNT_RDONLY`, `rootrw` initializes to zero and gates clearing that flag, `ufsrw` initializes to zero, and UFS writability requires `rw == 1`. The manifest renders the allowlist record as `allowlisted skip: 0031 (SWEET rootrw and dirty-root exception are already present and VEUX-enabled by 0110; no unique VEUX behavior is omitted.)`.

Strict run [40132841012](https://github.com/59c84486t9-alt/ios-veux/actions/runs/40132841012) accepted allowlisted skips 0031, 0032 and 0033, then stopped at 0035. The 0035 patch's legacy multi-file diff format breaks the strict `git apply --recount` parser; adding standard per-file diff headers preserves the hunks and lets it be checked/applied strictly. 0035 must apply because 0099 extends its built-in AMFI and entitlements implementation to VEUX. This run produced no usable kernel and nothing was flashed.

Follow-up: added Git diff boundaries for every file in 0035, including `new file mode 100644` for `SweetEntitlements.cpp`. Verified `git apply --recount --check` succeeds against the exact XNU source tree packaged by run 40132841012. The source change and strict allowlist still need a new green CI run; no image is ready and nothing was flashed.

- Strict run [40133559927](https://github.com/59c84486t9-alt/ios-veux/actions/runs/40133559927) confirmed 0035 now applies with zero fuzz. It stopped at 0038 because that patch was checked against the stale pre-entitlements source context. Updated its file-list hunk and added Git diff boundaries; `git apply --recount --check` now succeeds against the exact tree packaged by 40133559927. 0038 remains required by following SWEET patches and is not allowlisted. No image from this run is usable or flashed.
- Strict run [40134165652](https://github.com/59c84486t9-alt/ios-veux/actions/runs/40134165652) confirmed 0038 applies with zero fuzz, then found 0040 had the same legacy multi-file diff-header issue. Added per-file Git boundaries and the new-file mode; `git apply --recount --check` now succeeds against the exact tree packaged by 40134165652. No image from this run is usable or flashed.

## Patch-series preflight — 2026-10-24

- Normalized the patch series to independent `diff --git` file sections so each patch is parsed as a complete, reviewable diff. The repository validator now rejects repeated file sections in a patch. `tools/strictify-dxb.py` records every patch outcome, rejects any non-allowlisted skip, enforces skip signatures and staleness, applies with exact context (zero fuzz), and rejects `.rej`/`.orig` artifacts.
- Replayed patches 0116–0119 in order against the current tree after 0115. Regenerated stale 0116 console context and 0117 post-early-boot scanner context from that source. All four patches apply sequentially in the scratch replay tree.
- Found a real RW-policy mismatch: the VEUX root mount path cleared `MNT_RDONLY` on `rootrw=1`, while the UFS writer independently needed `ufsrw=1`. Added 0119 so both the root mount and UFS writer require the explicit pair `rootrw=1 ufsrw=1`; the diagnostic reports the effective mode. CI source checks and manifest checks verify both gates.
- The persistent console ring in 0088 writes a fixed userdata-tail range and does not derive safety from HFS+ volume geometry. The candidate workflow therefore boots read-only and omits `veuxlog=1`; enabling the tail logger before proving the range is outside the root volume is unsafe.
- Removed the obsolete workflow assertion for `su.writable = (rw == 1)`, which contradicted the corrected dual-argument policy and would have caused a false CI failure.
- Local preflight: all 118 patch files parse; repository, Python, and shell checks pass; dual-argument mount/UFS policy checks pass on the replayed source. The full macOS kernel CI has not yet run. No image is ready or flashed.

### Patch audit and 0117 compile repair — 2026-10-24

- Reviewed the complete patch inventory and strict application path before retrying CI. The four currently skipped upstream patches remain explicitly signature-checked in `xnu/patches/SKIP_ALLOWLIST.txt`; they are reported in the manifest and fail CI if their skip signature changes or they begin applying. Patch application is exact-context with zero fuzz and rejects failed hunks and `.rej`/`.orig` output.
- The last full CI run, [40137575145](https://github.com/59c84486t9-alt/ios-veux/actions/runs/40137575145), passed strict patch application and source/manifest assertions, then failed compiling 0117. The diagnostics showed missing complete task/thread and `pstats` definitions plus three local saved-state declarations that conflicted with XNU's canonical signatures. No image from that run is usable.
- Corrected 0117 to include the XNU private task/thread and resource headers, use the canonical ARM saved-state declarations, add a visible start-function prototype, and isolate the BSD/Mach duplicate task accessor and proc/task zone declarations while including `proc_internal.h`. Added repository validation that guards this private-header contract. The sampler still uses screen diagnostics and does not add barriers or storage flushes on fault paths.
- `python3 tools/validate-repo.py` passes with 118 patches, 27 Python tools, and 8 shell scripts; `git diff --check` passes; `git apply --numstat` parses 0117 and reports 167 added lines. A local syntax probe against the downloaded build artifact is not authoritative: the artifact omits generated kernel headers, and local Xcode is newer than the CI Xcode 16 toolchain. The next full CI compile remains the required validation.
- No new kernel image has been built or flashed after run 40137575145. The corrected patch and validator are pending CI.

- Follow-up strict run [40140019424](https://github.com/59c84486t9-alt/ios-veux/actions/runs/40140019424) passed patch application but failed compiling the new liveness source: defining `MACH_KERNEL_PRIVATE` before `<sys/param.h>` caused its transitive `osfmk/string.h` include to request bare `<types.h>`, which is not on the BSD compile include path. Moved the private macro definition after `<sys/param.h>` so common BSD headers use their public type path, while subsequent task/thread headers still expose private structures. Updated validation to enforce this ordering. No kernel manifest/image was produced and nothing was flashed.
- Follow-up run [40141040867](https://github.com/59c84486t9-alt/ios-veux/actions/runs/40141040867) exposed the other side of that workaround: defining `MACH_KERNEL_PRIVATE` after BSD includes mixed public and private Mach header guards, then required private `kern/misc_protos.h` unavailable to a BSD compile. Moved the liveness implementation into `osfmk/kern`, whose compile includes the XNU private header roots and libsa `types.h`, and restored private mode before all includes. CI assertions now verify its OSF registration and source. The run failed at compile, before manifest/image production; nothing was flashed.
- Follow-up run [40142194143](https://github.com/59c84486t9-alt/ios-veux/actions/runs/40142194143) passed repository validation and dependencies but strict patch application caught a malformed first hunk in 0117: its header claimed six old lines while the hunk contained five context lines. Corrected the hunk location/count to insert after `osfmk/kern/arcade.c`; confirmed that hunk applies with exact context to XNU 8796.141.3. No kernel was produced or flashed.
- Follow-up run [40142747811](https://github.com/59c84486t9-alt/ios-veux/actions/runs/40142747811) showed `git apply --recount --check` still rejects the valid 0117 hunk although ordinary `git apply --check` accepts it against the exact packaged source. Removed `--recount` from strict application; ordinary `git apply` rejects malformed hunk counts and uses exact context without fuzz, so it enforces the intended policy and avoids recount-induced false negatives. Corrected the 0117 hunk to include its leading source line as actual context. Run stopped before compilation; no image was produced or flashed.
- Follow-up strict run [40143199580](https://github.com/59c84486t9-alt/ios-veux/actions/runs/40143199580) passed checkout/dependencies but correctly stopped at a corrupt declared hunk count in 0111. A full hunk-count audit across all patches found three mismatches: 0085, 0111, and 0117. Corrected their declared old/new counts; the audit now reports zero malformed hunk headers. Repository validation and `git diff --check` pass locally. No kernel was produced or flashed.

- Patch 0117 follow-up before rerunning CI: the exact-context check found its BSD registration hunk was anchored before `bsd/dev/mem.c`, but the current XNU 8796 tree has SWEET device registrations between `sweet_ufs.c` and `mem.c`. Re-anchored the insertion between `sweet_sample.c` and `sweet_keys.c`; `git apply --check --include=bsd/conf/files` now passes against the source artifact from failed run 40143589015. Updated the BSD source comment to describe the BSD/OSFMK division accurately.
- Local checks after that correction: `tools/validate-repo.py` passes for 118 patches, `git diff --check` passes, 0117 parses with the expected source files, and the exact BSD registration hunk applies. A syntax-only probe using the prior CI Makefile command lines (`tools/xnu-cc.py ... --per-file`) compiled both `bsd/dev/veux_liveness.c` and `osfmk/kern/exception.c` with 0 failures. Full macOS CI is still required to prove the complete target build and generated headers; no image from run 40143589015 is accepted or flashed.
- CI run [40150336192](https://github.com/59c84486t9-alt/ios-veux/actions/runs/40150336192) passed strict patch application and compiled XNU, including 0117, but the post-build assertion looked for `patch-status.txt` inside `dxb/` while the strictifier writes it at the workspace root. The only Build-step error was `grep: patch-status.txt: No such file or directory`; fixed the assertion to read `../patch-status.txt` from `dxb/`. CI did not produce an accepted kernel manifest because the step exited before the manifest; no image was flashed.

### Read-only first boot flash: 2026-10-24

- Strict CI run [40151171910](https://github.com/59c84486t9-alt/ios-veux/actions/runs/40151171910) passed all patch, build, and kernel-manifest checks on `b4731fb8de611b3cecce0e271f4c0ed60a64edde`.
- Expected on-screen build ID: `40151171910` (`VEUX BUILD: ID=40151171910`).
- Reflashed the known-good iOS root image to `userdata`: `/Users/vivien/Downloads/ios16-root-20H392-keybag-noop.simg`, SHA-256 `5da713f38323460f33b20679368fc97f808b40eb1b5129ad8d84f51e01cabd0d`. Fastboot completed all 24 sparse chunks successfully.
- Flashed the CI-verified wrapper to `boot_b`: `shim/out/veux-xnu-40151171910/shim-boot-veux-xnu-40151171910.img`, SHA-256 `29d00ae9553af650f7138278614140b3868bc84c4be3bef2d489142eb09a30c1`. Fastboot reported `Sending 'boot_b' (16720 KB) OKAY` and `Writing 'boot_b' OKAY`.
- Selected slot B and issued `fastboot reboot`. The host no longer sees fastboot or ADB after the reboot command. First boot is RO: boot args omit `rootrw=1`, `ufsrw=1`, and `veuxlog=1`; no rw boot-arg was added. Await an on-device screen observation before changing mode.
- Wrapper manifest: `shim/out/veux-xnu-40151171910/shim-boot-veux-xnu-40151171910.img.manifest.json`; CI kernel SHA-256 `5e24b3067f27b6d9766abe918917c18e0e6fb1d865057d3a6514752e19661b31`; phone DTB SHA-256 `08284b0f3b0d3810abda6d617598370099f36f0f54110668bfe89f6ee35b4e2e`.

### RO handoff stall follow-up: 2026-10-24

- Corrected chronology from the user: the boot stalled at the shim's `XNU jumping (fbcon clears screen)` message; the user manually entered fastboot; I then selected slot A and issued `fastboot reboot recovery`. Do not describe this as an automatic kernel reboot or fallback.
- Recovery ADB is connected through the existing server on port 5039 (`4078cac030c8`, recovery, `_a`). Recovery `/sys/fs/pstore` is empty. The recovered userdata-tail ring decodes to 27,992 bytes, flush sequence 5, and ends at the older launchd `Early boot complete. Continuing system boot.` message. The flashed RO wrapper omitted `veuxlog=1`, so this ring does not capture the handoff-stall attempt; it cannot identify a panic or post-handoff kernel state.
- Read back the first 17,121,280 bytes of `/dev/block/by-name/boot_b` from recovery. The bytes match the flashed wrapper exactly: SHA-256 `29d00ae9553af650f7138278614140b3868bc84c4be3bef2d489142eb09a30c1`. Thus the stall is not explained by a host-side wrapper mismatch.
- Current evidence establishes that the shim printed its XNU handoff message. The device was manually interrupted before a post-handoff screen capture or fresh persistent kernel trace was obtained; no conclusion about whether XNU began executing is warranted.

### Early-console patch retry: 2026-10-25

- Strict CI run [40155572906](https://github.com/59c84486t9-alt/ios-veux/actions/runs/40155572906) stopped before compilation because 0120 had zero-context hunks and the workflow correctly checks patches with ordinary `git apply` (fuzz limit zero). My first local check used `--unidiff-zero`, so it did not match CI's exact apply policy. No kernel or image from this run is accepted.
- Regenerated 0120 from the actual post-0119 source in the failed run's `xnu-buildtree` artifact with normal three-line unified-diff context. Replayed the same plain `git apply --check` and `git apply` successfully against that source, then verified repository structure. This keeps the framebuffer console and build-ID display independent of `veuxfb`/`veuxfbconsole` boot arguments.

### Unconditional early console and verified candidate: 2026-10-25

- Strict CI run [40156009502](https://github.com/59c84486t9-alt/ios-veux/actions/runs/40156009502) passed after fixing 0120's exact-context hunk. The patch places the build ID and early stage markers directly on the framebuffer console, independent of `veuxfb`/`veuxfbconsole`; manifest source-policy checks confirm this, and kernel string checks pass. Patch 0117 remains screen-only and adds no barriers on fault paths.
- CI build ID: `40156009502`. Kernel SHA-256: `800d92a3d9f515d2efd2ae0ef07def450b7ddedc059e3242c4aaeb8a41252824`. Run artifact directory: `/tmp/veux-401560-kernel-2/`; manifest and patch-status list are in that directory.
- Wrapper `shim/out/veux-xnu-40156009502/shim-boot-veux-xnu-40156009502-ro.img` was assembled from that exact CI kernel, the known-good phone DTB, and embedded ADT. Wrapper SHA-256: `a2db42866c7a26ed59c0153b56cba2fa5a8a4332cdffae43aab0af4a6e196b08`. Phone DTB SHA-256: `08284b0f3b0d3810abda6d617598370099f36f0f54110668bfe89f6ee35b4e2e`. Wrapper manifest: `shim/out/veux-xnu-40156009502/shim-boot-veux-xnu-40156009502-ro.img.manifest.json`; verification against the CI kernel, bootargs, DTB, patch list, and build ID passed.
- Bootargs restore the baseline configuration except `rootrw=1` and `ufsrw=1` remain omitted: `debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam -noprogress rd=ufsroot0 unentitled_ios_sim_launch=1 veuxlog=1 veuxfb=1 veuxfbconsole=1 ignition_level=1 launchd_unsecure_cache=1 wdt=-1 wdt_test=no_user_checkin launchd_verbose_coalition_logs=1 launchd_log_verbose_meta_limit=128`. This candidate is RO by default.
- Patch comparison: relative to the older baseline, 0117 adds the liveness sampler, 0118 prevents root mount retries after failure, and 0119 requires both `rootrw=1` and `ufsrw=1` for RW mode. 0065/0078 (SMP/PSCI), 0004/0010 (early framebuffer), 0047 (ring), 0038 (AppleKeyStore), and crypto patches were already in the baseline set. `cpus=1` is preserved, so secondary CPU startup remains disabled. 0120 is the new unconditional build-ID/early-cell output.
- Wrapper address layout was verified against the baseline shim: virtual base `0xfffffe0006000000`, entry `0xfffffe0007490488`, physical base `0x100000000`, managed memory size `0xf8600000`, framebuffer `0x85200000` (12 MiB). Kernel end is `0x1028b0000` (4 KiB larger than the baseline `0x1028ac000`); ADT/bootargs were relocated by the wrapper packer after the image. The initrd remains at `0xA4739000..0xA56FE730`, below 4 GiB. No overlap was found among kernel, initrd, framebuffer, and the shim's early alias region.
- Device state at verification: `fastboot devices` and `adb -P 5039 devices` both returned no device. The candidate wrapper has **not** been flashed. User requested flashing the last-known-good RO wrapper first; this requires the phone to enumerate in fastboot. After that baseline boot, accept the candidate only after a screen photo shows `VEUX BUILD: ID=40156009502` and early stage cells.

### Writable-root retry candidate — 2026-10-25

- User corrected the boot target: VEUX/SWEET must mount root read-write; the previous RO-first requirement and fstab workaround are withdrawn. The known prepared root image is `/Users/vivien/Downloads/ios16-root-20H392-keybag-noop.simg`, SHA-256 `5da713f38323460f33b20679368fc97f808b40eb1b5129ad8d84f51e01cabd0d`. It is the saved full sparse image used for userdata restores; reflash it before each RW experiment. It contains the existing host-prepared keybag workaround, not the removed fstab approach.
- Reused the already green CI kernel from run `40156009502`; no kernel rebuild. Built a new payload and replaced only the wrapper ramdisk payload while preserving the verified shim/header/DTB. Wrapper: `shim/out/veux-xnu-40156009502-rw/shim-boot-veux-xnu-40156009502-rw.img`. Wrapper verification passed against the CI kernel, the original embedded ADT, and the phone DTB.
- RW boot args are `debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam -noprogress rd=ufsroot0 unentitled_ios_sim_launch=1 rootrw=1 ufsrw=1 veuxfb=1 veuxfbconsole=1 ignition_level=1 launchd_unsecure_cache=1 wdt=-1 wdt_test=no_user_checkin launchd_verbose_coalition_logs=1 launchd_log_verbose_meta_limit=128`. `veuxlog=1` is intentionally absent because its fixed tail window overlaps the HFS+ volume. `cpus=1` remains set. No fstab edit was made.
- Candidate identifiers: build ID `40156009502`; CI run `40156009502`; kernel SHA-256 `800d92a3d9f515d2efd2ae0ef07def450b7ddedc059e3242c4aaeb8a41252824`; wrapper SHA-256 `1d700e48f780817cfa774cadaea3f3dbae1f63f5055baeef573151bab3353b89`; DTB SHA-256 `08284b0f3b0d3810abda6d617598370099f36f0f54110668bfe89f6ee35b4e2e`. Wrapper manifest is adjacent to the image and contains these values plus complete patch status.
- The green kernel manifest reports 0118 `APPLIED` (terminal root mount failure panics immediately; no retry), 0119 `APPLIED` (both `rootrw=1` and `ufsrw=1` are required for root/UFS writes), 0030 `APPLIED` (write and sync-cache path), and 0114 `APPLIED` (UFS write diagnostics). Manifest source checks plus these paired args imply expected runtime line `VEUX ROOT mode=rw rootrw=1 ufsrw=1`; only the next phone photo can establish that it actually printed.
- Flush review from the final patch series: HFS journal sync invokes `DKIOCSYNCHRONIZE`; the custom UFS driver's RW ioctl dispatch calls `ufs_sync_cache()`, which sends SCSI `SYNCHRONIZE CACHE(10)` CDB opcode `0x35` through the UFS command UPIU and waits for a checked command completion. This is not a no-op in writable mode (the RO branch is the only path that returns success without issuing it). Writes use ordinary WRITE(10); no FUA bit/path is implemented. Access is serialized through the single command slot and UFS mutex; command timeout returns `ETIMEDOUT`. The driver neither queries nor configures the device's volatile write cache/WriteBooster, so whether WriteBooster is enabled on this handset is unknown. No evidence ties the prior catalog damage to a missing flush; the overlapping persistent log ring is excluded from this candidate.
- At candidate-build time, fastboot was unavailable; the subsequent flash attempt is recorded below. The intended sequence remains: flash the saved sparse root image to userdata, flash this wrapper to boot_b, select slot B, reboot once; avoid hard reset while the RW root is mounted. If it stalls, report that state and wait for the user to power down cleanly. After a clean RW boot, photograph the build ID, early cells, and RW mode line; then boot recovery and verify the volume read-only (`fsck_hfs -n` if available, otherwise compare relevant volume bytes against the pristine image) before another experiment.
- Flash attempt 2026-10-25: device `4078cac030c8` enumerated as fastboot/product `veux`, current slot B. Reflashed the saved userdata image with SDK fastboot 37.0.1: all 24/24 sparse chunks and final `Finished` returned OKAY (312.025 s). Image SHA-256 remained `5da713f38323460f33b20679368fc97f808b40eb1b5129ad8d84f51e01cabd0d`.
- The subsequent `boot_b` flash did not report a `Sending` or `Writing` result. Both host fastboot variants hung during device I/O and fastboot enumeration disappeared while those commands were active; they were interrupted. A simple SDK `fastboot getvar product` also hung. After stopping the commands the device enumerated again, but protocol requests still hang. **Do not reboot or assume boot_b was updated.** User was asked to unplug/reconnect USB while keeping the phone in fastboot; pending response. Root image is restored; boot_b/RW experiment remains pending.
- Follow-up flash 2026-10-25 after the user confirmed fastboot: verified wrapper SHA-256 `1d700e48f780817cfa774cadaea3f3dbae1f63f5055baeef573151bab3353b89`; SDK fastboot 37.0.0 reported `Sending 'boot_b' (16720 KB) OKAY` and `Writing 'boot_b' OKAY`. `getvar current-slot` returned `b`. Issued one `fastboot reboot`, which returned OKAY. The RW boot is now awaiting a screen photo; if it stalls, avoid a hard reset while root may be mounted RW and request a clean power-off. Reflash the saved userdata image before the next RW experiment after any reset.

### Sampler flood confirmed on phone — 2026-10-25

- Latest user photo still shows only `launchd` (PID 1) and `kernel_task` (PID 0), with approximately 59 total threads. Launchd's reported wait hint remains `0`, its displayed user PC is stable, and both run-queue counters are empty at the sample points. That does not measure CPU utilization or identify a wait object, and does not prove which Mach service/port is involved.
- The repeated `VEUX LIVE`/`VEUX IDLE` output is still from the already-flashed kernel. Edited patch 0117 in the working tree so process snapshots print only on process/thread/state/CPU/PC/name changes; launchd wait output prints only when its sampled event/hint/PC changes; idle output prints only when a run-queue count changes. Increased the panic-only console tail ring from 20 to 25 lines and expanded its panic viewport to fit 25 rows. These source edits have not been built, CI-verified, wrapped, or flashed. The 25-line tail remains panic-screen output, not a continuous scrollback window during normal boot.
- Not yet determined: waitq primitive/owner/name, all launchd thread waits, launchd VM regions/shared-region slide and host symbolication, IOKit busy services, post-early-boot job logs, system-domain/on-demand state, and whether the hello daemon was loaded. Current screen alone cannot answer those items.
- Flash-order correction: the last confirmed writes were boot_b first, followed by the saved userdata sparse image (`5da713f38323460f33b20679368fc97f808b40eb1b5129ad8d84f51e01cabd0d`); there was no host-issued reboot after that sequence. User subsequently booted the phone and supplied the photo above. The kernel now on screen is still the prior build; no new CI build or image hash exists for the edited sampler.

### Launchd wait / VM / IOKit / hello follow-up — 2026-10-25

- Source classification: `/tmp/veux-source-401560-extracted/xnu/osfmk/kern/block_hint.h` defines `kThreadWaitNone = 0x00`, `kThreadWaitPortReceive = 0x02`, and `kThreadWaitSemaphore = 0x06`; `/tmp/veux-source-401560-extracted/xnu/bsd/sys/proc.h` defines `SRUN = 2`. Thus photo `hint=0` means “no classified wait”; the `wait_event` address alone cannot identify a waitq. The current 0117 sampler selects the first thread in `task->threads`, not a guaranteed launchd main thread, and prints no thread IDs or other launchd thread waits. The photo's `state=2` is runnable (`SRUN`), not a blocked state. The sampler does not measure CPU utilization, so it cannot establish whether the CPU is idle or executing a particular thread.
- VM evidence: the existing sampler prints only a saved user PC. It reports no launchd VM regions or `task->shared_region` data. Historical rings contain `vm_shared_region_start_address() failed` at `check_np`, then shared-cache map lines marked `not in trust cache`; neither supplies the boot's shared-region base/slide or the region containing the photo PC. No matching dyld cache or map snapshot was available in the host artifacts, so this PC remains unsymbolicated. Source leads are `vm_map_region_recurse_64()` and `vm_shared_region_get(task)`; the shared-region struct holds `sr_base_address`, `sr_first_mapping`, `sr_size`, and `sr_slide`.
- IOKit evidence: there is no captured root `IOService::getServiceRoot()->getBusyState()` or busy/matching service list. Source offers `getBusyState()`, `waitQuietWithOptions()`, and service-plane traversal, but this boot cannot be attributed to a UFS node, platform expert, missing driver, or unfinished matching without live output.
- Launchd history: saved rings `xnu-veux-20261023-recovery-again.txt`, `xnu-veux-20261023-adb-on.txt`, and `xnu-veux-20261024-after-psci-test.txt` show `exec sysstatuscheck`, subsequent boot tasks, and `Early boot complete`; it did not block those earlier boots. The 2026-10-23/24 rings show `(system) entering ondemand mode` and `(system) created`, so the system domain and on-demand stage were reached in those boots. The 2026-10-24 recovery ring ends at early boot; the current photo has no post-handoff job lines. The exact flashed launchd cache and its complete RunAtLoad label list are absent from available artifacts, so no complete inventory is claimed. Wall-clock timestamps remain 1969/1970.
- Hello daemon: `veux-postboot-liveness-root-image.diff` documents a prior disposable root edit with a RunAtLoad plist and ad-hoc-signed binary, plus an entry in `/System/Library/xpc/launchd.plist` because launchd consumes that cache. `launchd_unsecure_cache=1` affects cache trust; it does not scan arbitrary added plist paths. The latest documented userdata write restored the pristine sparse root (`5da713f...`), so the hello job is not established as present in the phone's current root. No `VEUX USERLAND HELLO` line or job-start record appears in saved boot evidence. The archived candidate image was not mounted during this check; no image was altered.
- Definitive live answers require a subsequent build/boot that records each launchd thread's TID, saved state, block hint, waitq type and safe IPC owner/name/kobject; bounded VM regions and shared-region fields; plus IOKit root busy count and bounded busy/matching service names. Preserve post-early-boot console lines separately from the sampler. No new CI run, wrapper, or image hash was produced here.

### Panic after CI 40188018336 liveness sampler — 2026-10-25

- User photo shows `PANIC: Kernel data abort` at PC `0xfffffe00073283e4`, LR `0xfffffe00073283b4`, ESR `0x96000005`, FAR `0`. The panic-region frame list includes `frame5=0xfffffe00073283b4`; the console tail still shows launchd `Early boot complete. Continuing system boot.` followed by the liveness panel (`processes=2`, around 60 threads). Thus launchd reached the handoff; this image panics in the new sampler before it can provide a useful wait snapshot.
- Symbolicated against the exact CI 40188018336 Mach-O: PC = `veux_live_task_snapshot + 236`; LR = `veux_live_task_snapshot + 188`. Disassembly at PC: `ldr w8, [x8]`; preceding instruction loads `x8` from `[x24, #0x30]`, the thread's waitq's `wq_q` pointer. The pointer is null. `waitq_type()` directly dereferences `wq.wq_q->waitq_type`, so the sampler faulted while classifying a runnable/non-waiting thread. This is a bug in 0117, not evidence of an independent launchd failure. Frame list symbolization: `frame0 panic_trap_to_debugger+68`, `frame1 Assert`, `frame2 sleh_synchronous_sp1`, `frame5 veux_live_task_snapshot+188`; remaining saved frame values are `frame3 0xfffffe000748ebd4`, `frame4 0xfffffe000748d614`, `frame6 0xfffffe0007eee794`, `frame7 Call_continuation+64` (the first two do not resolve cleanly with atos from this release artifact).
- Fixed 0117 to test `thread->waitq.wq_q != NULL` before calling `waitq_type()` and classify a null waitq as 0. Added source and manifest assertions for the guard. Local repository validation and `git diff --check` pass. The guarded change has not yet been built by CI or flashed; do not use run 40188018336 as a successful liveness diagnostic boot.

### Liveness sampler null-waitq fix — CI 40191831328 (2026-10-25)

- CI completed green on commit `cd31089ca5570c9c59093ccb9f95614724baf61b` (run [40191831328](https://github.com/59c84486t9-alt/ios-veux/actions/runs/40191831328)). Strict patch preflight, XNU build, synthetic bounds check, kernel feature manifest, packaging, and artifact upload all passed. CI emitted only the Node.js 20 deprecation annotation.
- Build ID: `40191831328`. Kernel SHA-256: `2a846aa2a3828a672e9aea4f194207ed4719b1fdd4f5339a7add714be6c724ae`. CI manifest and patch-status list are in `/tmp/veux-ci-40191831328/xnu-kernel/` on the host. The only allowlisted skips are `iobuffermemd_monterey.patch`, `skywalk_sonoma.patch`, `syntax_checker_sonoma.patch`, and `TrustCache.patch`; 0117 applied.
- Built wrapper for the phone DTB using the CI kernel, extracted boot-v2 ADT, and the established RW debug args (no `veuxlog=1`). Wrapper SHA-256: `cf20975d4e943a3254ad4960a538cba184484625ba6f5b3ca0bf6c9896e5a73b`. DTB SHA-256: `08284b0f3b0d3810abda6d617598370099f36f0f54110668bfe89f6ee35b4e2e`. The adjacent `.manifest.json` records CI run ID, build ID, kernel/payload/wrapper/DTB hashes, boot args, and patch statuses. `verify-veux-wrapper.py` confirmed the wrapper payload reconstructs byte-for-byte from the CI kernel and its embedded ADT, and that the wrapped DTB and arguments match.
- Expected on-screen/ring marker: `VEUX BUILD: ID=40191831328`.
- This corrects the prior sampler panic (`veux_live_task_snapshot` dereferenced a null `thread->waitq.wq_q`). It is a diagnostic recovery build, not proof of the outstanding launchd wait owner/kobject, complete VM map, IOKit quiescence, or post-early-boot job state. The current patch prints a shared-region summary and the VM region containing the sampled PC when the wait snapshot changes; it does not enumerate every launchd VM region or IOKit busy services. The 25-line console tail is shown on the panic display, not continuously during normal boot.
- No flash was attempted: `fastboot devices -l`, `adb devices`, and macOS USB inventory returned no connected phone at this host check, despite the phone being reported in Fastboot. Preserve the required order when it enumerates: write the wrapper to `boot_b` first; restore the pristine root image before the RW experiment; then boot once. Do not claim this build was tested on device until a photo confirms the expected build ID and sampler output.
- Flash/boot execution after CI 40191831328: confirmed `product=veux`, `current-slot=b`, `has-slot:boot=yes`, `is-userspace=no`; flashed the verified wrapper to `boot_b` successfully, then restored `/Users/vivien/Downloads/ios16-root-20H392-keybag-noop.simg` to `userdata` (SHA-256 `5da713f38323460f33b20679368fc97f808b40eb1b5129ad8d84f51e01cabd0d`, 24/24 sparse chunks OKAY), then issued `fastboot reboot`. Host no longer enumerates the device over Fastboot or ADB after reboot. Awaiting a screen photo to confirm build ID and see whether the sampler reaches post-early-boot diagnostics; no claim of on-device success yet.

### Launchd wait and VM output from phone photos — 2026-10-25

- The latest screen photos show `VEUX WAIT: launchd threads=8` and eight records. Recorded thread state is the raw `thread->state` bitmask, not BSD `p_stat`: `0x1` is `TH_WAIT`; `0x4` is `TH_RUN` (runnable). Correcting the earlier note that interpreted a thread's `state=2` as `SRUN`; that enum applies to BSD process state, not these thread records.
- Wait hints decode from this tree's `osfmk/kern/block_hint.h`: `hint=0x6` is `kThreadWaitSemaphore`; `hint=0xf` is `kThreadWaitParkedWorkQueue`; `hint=0x0` means no classified wait. `waitq=1` is the generic queue type from the sampler, not an IPC port. The photo's repeated `event=0xfffffe00070091c8`, `hint=0x6`, `waitq=1`, `pc=0x1f289cfac` records are semaphore waits. The `hint=0xf` records at `pc=0x1f289d4f0` are parked workqueue waits. One `hint=0` record at `pc=0x1f28a492c` has no classified wait. One `state=0x4`, `event=0`, `waitq=0` record at `pc=0x1f289f030` is runnable with no waitq. This evidence does not identify which TID is launchd's main thread or any semaphore owner/IPC port owner.
- The photos show shared-region fields `shared_base=0x180000000`, `first=0x3028c000`, `slide=0x3928c000`, `size=0x10000000`; the sampled launchd PC is `0x1f289d4f0` and the sampler reports its containing VM region `0x180000000-0x2c0000000`, `prot=1/1`, `tag=32`. The PC is within that region. No matching dyld shared cache or launchd image is present in the host's available files, so it remains unsymbolicated. The pristine Android-sparse root image expands to 16 GiB, while only 5.7 GiB was free on the data volume; it was not expanded or mounted for this check.
- The photos establish that kernel sampling is running and can enumerate launchd wait records. They do not show process-child launches, launchd's post-early-boot console output, hello-daemon execution, IOKit root busy state, or service matching state. No new CI build, root image edit, wrapper, or flash was made for this analysis.

### Follow-up launchd thread snapshot — 2026-10-25

- New user photo shows launchd's sampled thread set changed since the prior eight-thread snapshot. It includes TID 765 with raw state `0x39`, event 0, hint 0, waitq 0; TIDs 779, 783, and 788–790 show state `0x1`, event `0xfffffe00070091c8`, hint `0x6`, waitq 1, PC `0x1f289cfac`; TIDs 791 and 792 show state `0x4`, event 0, hint 0, waitq 0, PC `0x201e26724`. A later visible record for TID 203 is also state `0x4` with no waitq. The photo is partly cropped/blurred, so this is not a complete thread inventory or reliable total count.
- XNU raw state `0x39` combines `TH_WAIT|TH_UNINT|TH_TERMINATE|TH_TERMINATE2`; `thread->state & TH_TERMINATE` denotes a terminating/halted thread, not a normal blocked launchd main thread. State `0x4` is `TH_RUN`. The semaphore and parked-workqueue interpretation from the prior photo remains unchanged. No wait owner, Mach port identity, or launchd-main-thread identity is exposed.

### Launchd wait-owner and kernel-stack diagnostic follow-up — pending CI

- User reports the device is in Fastboot. Host `fastboot devices -l` confirms `4078cac030c8` is present; ADB has not been used for this state.
- Extended patch 0117 to label launchd waits from XNU `block_hint`, obtain semaphore owner PID and semaphore context via `kdp_sema_find_owner`, and capture up to six kernel frames for each sampled launchd thread via `machine_trace_thread64`. The wait snapshot hash includes owner/context/frame values, so changed ownership or stack output is reported even when the wait event itself stays constant. Sampling remains screen/ring output and does not add storage flushes.
- Added workflow source checks and final-kernel manifest needles for semaphore owner/context and stack-frame output. Local `tools/validate-repo.py`, `py_compile tools/kernel-manifest.py`, and `git diff --check` pass. CI has not yet run; the patch has not been flashed.
- Evidence interpretation remains: the photo's repeated `hint=0x6` is `kThreadWaitSemaphore`, `hint=0xf` is parked workqueue, and `waitq=1` means a generic queue. This is not a Mach IPC port wait, so a receive-right name/kobject lookup is not indicated by the photographed wait records. No live owner PID, kernel stack, complete VM map, dyld-cache symbolication, IOKit busy-state report, or post-early-boot job inventory is available until a successful diagnostic image boots.
- If CI passes, keep the phone in Fastboot until the verified wrapper is ready. Follow the user's boot_b-first constraint; restore the pristine root image before the RW diagnostic boot, and do not force-reset while it is mounted RW. The target on-screen build ID will be that CI run ID.

### Strict CI patch syntax repair — 2026-10-25

- CI run [40195239811](https://github.com/59c84486t9-alt/ios-veux/actions/runs/40195239811) stopped in strict patch preflight before compiling: patch 0117 had a malformed exception.c unified-diff header (`+1050,126` declared but 130 inserted lines were present). Corrected the declared new-line count to 130. This is a patch-format correction only; no kernel behavior changed.
- `tools/validate-repo.py`, `python3 -m py_compile tools/kernel-manifest.py`, and `git diff --check` pass. `git apply --numstat` parses patch 0117. A full `git apply --check` from the repository root cannot apply because this checkout does not contain the XNU source tree; strict CI applies it against the fetched source and remains authoritative.

### Launchd wait owner/stack diagnostic build and RW boot — 2026-10-25

- Strict CI run [40195827498](https://github.com/59c84486t9-alt/ios-veux/actions/runs/40195827498) is green on commit `0a9735d180422991cb30e1844a3a590166ba98dc`. Strict patch application, XNU build, host synthetic bounds checks, kernel feature manifest, packaging, and artifact upload passed. Patch 0117 applied; the four skip entries remain allowlisted with reasons. CI emitted only the Node.js 20 deprecation annotation.
- Build ID `40195827498`; CI kernel SHA-256 `1f1a477a49e19a87ad78032482e102c1f547b27239d558a73cb867b931f598c5`. Kernel and patch status artifacts downloaded to `/tmp/veux-ci-40195827498/xnu-kernel/`.
- Created `shim/out/veux-xnu-40195827498-rw/shim-boot-veux-xnu-40195827498-rw.img` with the new CI payload, existing verified VEUX boot-v2 shim/header, phone DTB `dtb/vendor_boot_b_unpacked/dtb_1.dtb`, and established RW args. `mkbootimg` and the GNU cross compiler are absent on this host, so preserved the existing verified v2 wrapper's shim kernel/header/DTB and replaced only its aligned ramdisk payload/header size. `tools/verify-veux-wrapper.py` passed: payload reconstructs byte-for-byte from CI kernel plus embedded ADT; payload boot args and phone DTB match. Build ID marker is present in the CI kernel.
- Wrapper SHA-256 `61061f33ee5432ba6ec1ffce3badd1e6f149b2e74a9bb39429feaddba0cb3b9a`; DTB SHA-256 `08284b0f3b0d3810abda6d617598370099f36f0f54110668bfe89f6ee35b4e2e`. Adjacent manifest: `shim/out/veux-xnu-40195827498-rw/shim-boot-veux-xnu-40195827498-rw.img.manifest.json`. Boot args: `debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam -noprogress rd=ufsroot0 unentitled_ios_sim_launch=1 rootrw=1 ufsrw=1 veuxfb=1 veuxfbconsole=1 ignition_level=1 launchd_unsecure_cache=1 wdt=-1 wdt_test=no_user_checkin launchd_verbose_coalition_logs=1 launchd_log_verbose_meta_limit=128` (`veuxlog=1` remains off).
- Fastboot confirmed product `veux`, current slot `b`, and `has-slot:boot=yes`. Followed user's order: wrote wrapper to `boot_b` first (`Sending`/`Writing` both OKAY), then restored `/Users/vivien/Downloads/ios16-root-20H392-keybag-noop.simg` to userdata (SHA-256 `5da713f38323460f33b20679368fc97f808b40eb1b5129ad8d84f51e01cabd0d`; all 16 sparse chunks and writes OKAY), selected slot B, and issued reboot. Fastboot/ADB no longer enumerate the device after the reboot command. The host has no screen capture; wait for the user's photo before claiming the build ID or RW mode appeared or that diagnostics produced a result. Avoid forced reset while this RW boot may be writing; if it stalls, have the user power off cleanly and reflash root before a subsequent RW attempt.

### Recovery handoff for launchd stall diagnosis — 2026-10-25

- After the user reported Fastboot, confirmed device `4078cac030c8`, product `veux`, slot B. Switched active slot to A and issued `fastboot reboot recovery`; both commands returned OKAY. No partitions were flashed.
- Fastboot no longer enumerates. Default ADB sees `4078cac030c8` as `unauthorized`; the ADB server on port 5039 sees no device. No recovery shell, pstore, current userdata check, or filesystem check has been collected yet.
- Last user photos from RW boot show launchd wait records classified as semaphores (`hint=0x6`, waitq type 1), with `owner_pid=1` and repeated user PC around `0x1daa60fac`. This indicates launchd-owned semaphore waits but does not prove a deadlock; the photos show no child-job launch output. The CI 40195827498 patch can print kernel frames, but no `VEUX STACK` lines are visible in the supplied photos. Need authorized recovery ADB plus the dyld shared cache (or legible stack-frame output) to identify the blocked path. Root was mounted RW and HFS/UFS writes occurred; no clean filesystem check is available after this reset.

### Recovery ADB read-only snapshot — 2026-10-25

- Host now sees `4078cac030c8` as `recovery` (`product:veux`, `device:veux`), not Fastboot. `adb shell` is root and `ro.boot.slot_suffix` is `_a`; recovery `/proc/cmdline` is Android recovery's, not the prior XNU command line.
- `/sys/fs/pstore` is empty and `/proc/last_kmsg` is absent, so this boot provides no persisted XNU panic/console record. `logcat` is unavailable in this recovery image. Recovery `dmesg` identifies the SKhynix H9HQ15AECMBDAR UFS device and has no UFS timeout or I/O error in the captured UFS-related output; this only describes the recovery boot and does not rule out a transient XNU-side UFS issue.
- Userdata is not mounted in recovery. No partition was written, no image was reflashed, and no filesystem check was run. To diagnose the prior stall, the next useful evidence must come from a reproduced XNU boot: a bounded console tail plus all launchd wait records and kernel frames; the current recovery environment cannot inspect live XNU threads or recover the missing XNU ring.

### SWEET comparison and bounded launchd wait sampler — 2026-10-25

- SWEET's boot records do **not** document the same launchd-after-handoff stall: its launchd entered on-demand mode and started boot tasks, and later boots launched backboardd, SpringBoard and Setup. The captured SWEET stall was later in GUI startup: during repeated data migration, SpringBoard waited in a synchronous XPC request while backboardd held system-shell check-in. SWEET's root-image v12 edit set `LastSystemVersion=20H392` in `/var/mobile/Library/Preferences/com.apple.migration.plist`; a separate earlier diagnosis traced missing ByHost preference writes to absent IOPlatformUUID and added the needed synthetic ADT identity. SWEET's 0054 sampler targeted SpringBoard/backboardd after a 90-second delay, not launchd. See entries around 1249 and 1252. Thus it is useful precedent for sampled userland stalls, but not evidence that the present VEUX launchd wait has the same cause or fix.
- Reduced VEUX 0117 diagnostic overhead: wait records are capped at eight; wait-class mask starts at zero and output is emitted only for the initial sample or a change in observed wait classes. Semaphore owner lookup is limited to those eight records, and kernel stack capture is limited to that first bounded snapshot. This avoids repeatedly unwinding/querying every launchd worker (photos show the worker count growing into the hundreds/thousands) and suppresses per-TID churn. It does not yet identify launchd's blocked operation; stack frames from the next boot are needed.
- Added a kernel-manifest source assertion for the bounded/change-gated profile. Patch parses via `git apply --numstat`; CI/build/manifest and device reproduction remain pending. No image was flashed in this update.
- Follow-up review of the downloaded 40195827498 development kernel found the stack hook was embedded (`VEUX STACK: tid=%llu frames=` and `machine_trace_thread64` were present), but its code printed no line at all when `machine_trace_thread64()` returned zero. The photos therefore cannot distinguish “not attempted,” no kernel stack, and a zero-frame unwind. Updated 0117 to always print `VEUX STACK: tid=... attempted=... frames=... flags=...`; actual addresses now have their own `VEUX STACK FRAMES:` line. The wait signature now includes the bounded wait event/state/hint/kind/user-PC/semaphore-owner/context fields and omits TID/stack frames to avoid churn; the wait class mask still summarizes all launchd threads. Only the initial eight-thread snapshot is unwound, and no fault-path barriers were added.
- Updated `tools/kernel-manifest.py` and the workflow source grep to require both stack status and frame-value format strings. Fixed a duplicate dict key and a contradictory source check found during review. Local verification: `python3 -m py_compile tools/kernel-manifest.py`, `python3 tools/validate-repo.py` (119 patches, 27 Python tools, 8 shell scripts), `git diff --check`, and `git apply --numstat` for 0117 all pass. CI for this follow-up and a device boot are pending; no phone partitions were modified in this turn.

### SWEET comparison and launchd stack-outcome CI — 2026-10-25

- Strict CI run [40201418780](https://github.com/59c84486t9-alt/ios-veux/actions/runs/40201418780) passed after the 0117 diagnostic update. Build ID: `40201418780`. The downloaded kernel SHA-256 was independently checked as `a691c7a67ac874509418dd5e15627d3e9f8de91a57c832e8bdfd86b09cab5b12`.
- CI manifest reports all required string and source-policy checks true, including bounded/change-gated launchd waits, signed trace result and frame-value marker, 0113/0114/0118/0119/0120 and root RW selection. Patch 0117 applied with zero fuzz. The only skips are the four existing allowlisted upstream/macOS-incompatible patches; reasons and statuses are in the artifact `manifest.json` and `patch-status.txt`.
- This run produced a CI kernel artifact and manifest; a phone-specific boot-v2 wrapper was not assembled or flashed. No phone partitions were written in this follow-up. Do not identify this kernel as the image currently on the device until a wrapper is made, flashed to `boot_b`, and its build ID is seen on screen.
- SWEET has no recorded instance of the same launchd-after-early-boot stall and no matching fix: its recorded later stall was SpringBoard waiting on synchronous XPC while backboardd held system-shell check-in. SWEET fixed the migration loop with `LastSystemVersion=20H392` in its migration preferences; that does not explain VEUX's launchd-owned semaphore waits. The VEUX photos do show launchd-owned semaphore waitq entries, but a wait event is not itself proof of deadlock. The next boot's `VEUX STACK` status and frame lines are needed to identify the waiting code path.

### Diagnostic wrapper flashed to boot_b — 2026-10-25

- Assembled `shim/out/veux-xnu-40201418780-rw/shim-boot-veux-xnu-40201418780-rw.img` from CI run/build ID `40201418780`, the phone DTB, the existing verified v2 shim/header, and the established RW diagnostic boot args (both `rootrw=1` and `ufsrw=1`; `veuxlog=1` off). `tools/verify-veux-wrapper.py` passed: embedded payload reconstructs byte-for-byte from the CI kernel and ADT; DTB and boot args match. Wrapper SHA-256 `b1440c4207403a7308ac746a9c6c0734f397d859c06ea6d7f975d07e96f8492c`; kernel SHA-256 `a691c7a67ac874509418dd5e15627d3e9f8de91a57c832e8bdfd86b09cab5b12`; phone DTB SHA-256 `08284b0f3b0d3810abda6d617598370099f36f0f54110668bfe89f6ee35b4e2e`. Adjacent manifest records complete patch statuses and all hashes.
- Recovery ADB was present, so issued `adb reboot bootloader`; Fastboot then identified product `veux`, `is-userspace=no`, current slot A, and `has-slot:boot=yes`. Flashed the wrapper to `boot_b` (`Sending` and `Writing` both `OKAY`), selected slot B (`OKAY`), confirmed current slot B, and issued `fastboot reboot` (`OKAY`). No userdata write occurred in this sequence. Therefore the filesystem state at the start of this RW diagnostic boot is whatever was already on userdata; do not assume it was freshly restored from the pristine image. Wait for the user's screen photo before claiming the build ID or stack output appeared. If the system stalls, avoid a forced reset while its RW root may be mounted; restore the pristine root before the next RW experiment.

### Launchd instrumentation build and CI verification — 2026-10-25

- Pushed commits `98e971a` and `cdc5572` to `veux-xnu-build`, then dispatched CI run [40215797761](https://github.com/59c84486t9-alt/ios-veux/actions/runs/40215797761) on commit `cdc5572edea54bdf934cb91b6c82d23c24d26ddb` (macOS 13.5, DEVELOPMENT, VEUX). The run completed green in 12m34s: repository/patch preflight, XNU build, host diagnostic bounds checks, kernel feature manifest, build-tree packaging, and artifact uploads all passed. Only annotation is upstream actions' Node.js 20 deprecation notice.
- Patch 0121 applied at fuzz limit 0. Manifest confirms the expected launchd main-thread stack status/frame strings, wait classifier, pid-1 exec/spawn/exit/MAC traces, VM region markers, build-ID marker, root RW dual-argument checks, mount-failure no-retry, read-only journal guard, and synchronous UFS ring flush. The four explicit allowlisted skips (`iobuffermemd_monterey.patch`, `skywalk_sonoma.patch`, `syntax_checker_sonoma.patch`, `TrustCache.patch`) are listed with reasons in the manifest; no unlisted skip occurred.
- Build ID: `40215797761`. Kernel SHA-256: `cb5697249fdf100bed326ddfcaddc98d5858b184031ca80aec565c52310f63ad`. Independently recomputed from the downloaded artifact and matched `SHA256SUMS` and `manifest.json`. `strings` on the actual kernel confirms `VEUX BUILD: ID=40215797761`, `VEUX STACK MAIN`, `VEUX ROOT mode`, `VEUX MOUNTROOT: failure; no retry`, `VEUX HFS: read-only root journal replay disabled`, and the mount-helper exit marker.
- CI boot args request RW (`rootrw=1 ufsrw=1`) with `cpus=1`, framebuffer console enabled, launchd verbose logging, and `veuxlog=1` off. No phone-specific wrapper has been assembled or flashed for this run, and no device boot/photo verifies the new build ID or runtime traces. Do not call this image device-tested or flash it until a matching wrapper manifest and the required pristine-root/boot sequence are completed.


### CI 40215797761 wrapper build and boot_b-first restore — 2026-10-25

- Built the boot-v2 wrapper on the supplied Ubuntu VPS using the CI payload/kernel, the known-good phone DTB, and the existing verified boot-v2 template. Ubuntu's packaged `mkbootimg` entry point failed because its optional `gki` Python module is absent; used a local v2-only packer against the verified template, then ran the repository verifier. The shim cross-build and host console test completed successfully.
- CI run/build ID: `40215797761` (green). Kernel SHA-256: `cb5697249fdf100bed326ddfcaddc98d5858b184031ca80aec565c52310f63ad`. Wrapper SHA-256: `288db74541cbc24de1a41f679a46c98e72bf58c5bf354c7b82c390b5bd57fa42` (17,117,184 bytes). Phone DTB SHA-256: `08284b0f3b0d3810abda6d617598370099f36f0f54110668bfe89f6ee35b4e2e`. The independently rerun local verifier matched the VPS manifest. Manifest: `/tmp/veux-wrap-40215797761/local-verified.manifest.json`; VPS build directory `/root/veux-wrap-40215797761/input/`.
- Boot args include `rootrw=1 ufsrw=1`, `cpus=1`, `veuxfb=1`, `veuxfbconsole=1`, and launchd verbosity; `veuxlog=1` is off.
- Fastboot reported `product=veux`, slot B, boot_b size 128 MiB. Flashed wrapper to `boot_b` first; send/write both returned OKAY. Then restored the pristine userdata sparse image to userdata; SHA-256 `5da713f38323460f33b20679368fc97f808b40eb1b5129ad8d84f51e01cabd0d`; all 16/16 chunks returned OKAY. This follows the user's required partition order.
- After the userdata restore, Fastboot no longer enumerated the phone. A subsequent host `fastboot set_active b` command did not return, so it was interrupted; no reboot command was issued. The phone has not yet booted build `40215797761`, and there is no on-device photo/runtime validation. User needs to reset/reconnect Fastboot so slot B can be selected and the wrapper booted.
- Follow-up: Fastboot re-enumerated `4078cac030c8`, product `veux`, current slot B. Confirmed `boot_b` partition size `0x8000000` (128 MiB) and issued `fastboot reboot`; boot command returned OKAY. Awaiting a screen photo to verify build ID `40215797761` and observe the RW boot. Do not force-reset if it stalls with RW root mounted; ask the user to power off cleanly and restore pristine userdata before another RW run.

### launchd xpcproxy EPERM instrumentation — 2026-10-25

- The latest device photo reports pid 1 repeatedly spawning `/usr/libexec/xpcproxy`, `errno=1`, `path_errno=0`. This identifies a policy-style failure, but does not by itself prove which kernel gate returned it.
- XNU 8796 `bsd/kern/kern_exec.c` has an early `exec_validate_spawnattr_policy()` check: a nonzero process-type mask with `POSIX_SPAWN_PROC_TYPE_DRIVER` requires `IOCurrentTaskHasEntitlement(POSIX_SPAWN_ENTITLEMENT_DRIVER)`, otherwise it returns `EPERM`. It runs before `exec_activate_image()`. This is a concrete candidate for the observed errno.
- Added patch `0122-veux-xpcproxy-driver-spawn-gate.patch`: bounded pid-1 traces record the exact spawn-attribute denial, process type/flags/options/launch type/MAC extension size, image activation/activator returns, vnode exec policy hook errors, launch-constraint hook errors and resulting CS flags. Repeated xpcproxy failures are summarized rather than flooding the screen.
- `veux_spawn_driver=1` enables a narrow diagnostic exception only for pid 1, exact `/usr/libexec/xpcproxy`, DRIVER process type, and the early missing-entitlement `EPERM`. It leaves image signature validation, vnode MAC, and launch-constraint checks in the path. This is a diagnostic development boot switch, not evidence that the binary has passed those later checks.
- Root image files are not present in this checkout, so xpcproxy's architecture/slices, LC_BUILD_VERSION, CDHash, signature flags, entitlements, and launch-constraint blobs remain uninspected. No post-fix phone boot has yet confirmed the first failure or the next one.

### xpcproxy spawn-gate diagnostic image and pristine-root restore — 2026-10-25

- The newly supplied screen photo shows the older generic `VEUX SPAWN: pid=1 parent=0 name=launchd path=/usr/libexec/xpcproxy errno=1 path_errno=0` record. It proves the path lookup succeeded and the attempted spawn returned EPERM, but it does not show a `return_site` or build ID; it therefore does not verify the 0122 diagnostic build or identify the exact return point. The latest 0122 build is expected to print `VEUX SPAWN FAIL` with a stage and attempt count, followed by a specific `VEUX SPAWN DENY` or activation/MAC return record.
- Re-verified the wrapper for CI/build ID `40231594906` with `tools/verify-veux-wrapper.py`. Build ID `40231594906`; CI run `40231594906`; kernel SHA-256 `1bdd04ee4368e506086ac6c3847fdd0186f5f2023c61e1c3e33fc44a22d9bde7`; wrapper SHA-256 `139149567d400794f7e864684071ebc1d2a04ced0c5674441df787b5d39b4ad1`; phone DTB SHA-256 `08284b0f3b0d3810abda6d617598370099f36f0f54110668bfe89f6ee35b4e2e`. The manifest confirms the payload matches the CI kernel/embedded ADT, wrapper DTB, boot arguments, and strict patch-status list. The boot arguments include `veux_spawn_driver=1`, `rootrw=1 ufsrw=1`, `cpus=1`, and framebuffer console; `veuxlog=1` is absent.
- Fastboot reported serial `4078cac030c8`, product `veux`, current slot B. Flashed the verified wrapper to `boot_b` first (`Sending` and `Writing` both OKAY). Then restored `/Users/vivien/Downloads/ios16-root-20H392-keybag-noop.simg` to `userdata`. Its SHA-256 was recomputed immediately before flashing and matched the recorded pristine image hash `5da713f38323460f33b20679368fc97f808b40eb1b5129ad8d84f51e01cabd0d`; all 16/16 sparse chunks completed OKAY.
- After the userdata restore, Fastboot stopped enumerating the phone and ADB also shows no device. This matches the user's observed USB behavior after userdata flashes. No reboot command could be issued because neither interface currently enumerates. The next action is to return the phone to Fastboot; then verify slot B and boot the just-flashed wrapper. Do not claim the 0122 gate fix or any later spawn behavior is tested until the screen shows build ID `40231594906` and the new stage/return-site traces.

### Follow-up USB check and attached photo evidence — 2026-10-25

- Current host checks: `fastboot devices` and `adb devices` list no device. No reboot, slot change, or partition write was issued in this follow-up. User explicitly says not to restore userdata again unless needed for a fresh RW test; this supersedes older blanket per-attempt restore guidance for the pending first boot.
- Inspected the three attached HEIC photos. The second and third show the 0122-style `VEUX SPAWN FAIL` / `VEUX SPAWN REPEAT` records for launchd spawning `/usr/libexec/xpcproxy`, `stage=posix_spawn-setup errno=1`; visible repeat counts include 32, 64, 352, 384, and 416. The second also shows a SpringBoard spawn failure record, but its errno is clipped. The third shows launchd-owned semaphore waits and parked workqueue threads. The first shows FIPS POST passes.
- None of these photos visibly identifies build `40231594906`, the specific `VEUX SPAWN DENY` return site, or a diagnostic bypass record. The photos establish presence of the newer trace format in a photographed boot, but cannot establish its exact CI identity, timing relative to the restore, or the failing policy gate. Do not infer the DRIVER exception ran or succeeded from the generic setup-stage label.
- Pending: reconnect/return phone to Fastboot, verify product and current slot, select B if necessary, then reboot the already-flashed boot_b image. Capture build ID and the earliest DENY/bypass/activation records. No userdata restore is needed for this still-pending first boot.

### User correction: diagnostic boot completed; Fastboot returned — 2026-10-25

- User confirms the attached photos are the outcome of the flashed diagnostic boot. The previous pending-first-boot handoff is superseded: this build has booted, and the photographed result is repeated xpcproxy EPERM at `stage=posix_spawn-setup`. Exact build ID is not legible in the photos; boot attribution is supplied by the user.
- Host now confirms Fastboot device present, `product=veux`, `current-slot=b`. Only read-only enumeration/getvar commands were issued; no reboot or flash was performed. Userdata has already undergone the photographed RW boot and must no longer be described as an unbooted pristine restore.
- Source interpretation: 0122 initializes the generic stage to `posix_spawn-setup` and changes it immediately before `exec_activate_image`. Its dedicated spawnattr denial sets `veux_spawn_specific_policy`, suppressing the generic FAIL record. Thus the photographed generic setup-stage EPERM points to another pre-activation failure (or an instrumentation gap), not proof that the DRIVER entitlement denial remains. Next work is to inspect/instrument remaining pre-activation EPERM exits before spending another device boot.

### Root cause candidate repaired: launchd lost its entitlements — 2026-10-25

- Extracted launchd and xpcproxy directly from the pristine saved keybag-noop sparse root, without mounting it. launchd has no XML/DER entitlement slots after the historical ad-hoc re-sign; xpcproxy retains its entitlements. XNU persona validation returns EPERM when launchd lacks persona-mgmt, before the 0122 DRIVER check. This is a concrete defect and a strong explanation for the photographed pre-activation EPERM; exact runtime return-site confirmation is still absent.
- Recovered the older launchd XML dictionary (22 keys, including persona-mgmt=true) from leftover sparse-image data and verified its SHA-256 against slot 5 of the associated com.apple.xpc.launchd CodeDirectory. Repaired only the current launchd signature in a separate clone, preserving all executable/config bytes and HFS metadata. Re-extracted repaired binary passes strict codesign verification.
- Candidate `/Users/vivien/Downloads/ios16-root-20H392-keybag-noop-entitlements.simg`, SHA-256 `d7777c229e7dc012a3e86a5d9f54ab4fc4bf74e443526fe2f11562f0d2b2d691`. Original image unchanged. Full evidence and hashes: `docs/VEUX-LAUNCHD-ENTITLEMENTS-REPAIR.md`; ignored local reconstruction artifacts: `research/veux-logs/launchd-entitlements-repair/`.
- Fastboot is available, product veux / slot B. No flash/reboot occurred. No new kernel CI needed: test with existing 40231594906 boot_b after confirmed restore of the repaired root for a fresh RW test. Waiting for the per-destructive-step confirmation required by AGENTS.md before writing userdata.

### Repaired entitlement root flashed; USB lost before reboot — 2026-10-25

- User explicitly approved flashing the repaired root and rebooting existing boot_b. Immediately before the write, Fastboot confirmed product veux, current slot B; image SHA-256 recomputed as `d7777c229e7dc012a3e86a5d9f54ab4fc4bf74e443526fe2f11562f0d2b2d691`.
- Ran SDK Fastboot 37.0.1 with `-S 512M flash userdata /Users/vivien/Downloads/ios16-root-20H392-keybag-noop-entitlements.simg`. All 24/24 sparse chunks and writes returned OKAY; final Finished reported 297.030 seconds. No boot partition write occurred; boot_b remains the previously flashed CI 40231594906 wrapper.
- Fastboot briefly listed the device immediately after the flash, but the subsequent product query hung and both Fastboot/ADB enumeration became empty. Terminated the waiting query and its parent shell before subsequent slot/reboot commands could run. No reboot was issued and the repaired root has NOT yet booted.
- Next: user returns the phone to Fastboot/reconnects it; verify product/slot and reboot existing slot B. Reboot authorization is already granted. Do not reflash userdata: the repaired pristine RW image was just successfully restored. Await screen evidence for build ID, xpcproxy spawn success or exact next failure; entitlement repair is not yet runtime-validated.

### Repaired root boot issued — 2026-10-25

- User reported Fastboot available. Host verified product veux, current slot B, then issued `fastboot reboot`; Rebooting returned OKAY, Finished 0.001 s. No partitions were flashed in this follow-up.
- This boots the existing 40231594906 boot_b wrapper against the just-restored entitlement-repaired root (`d7777c229e7dc012a3e86a5d9f54ab4fc4bf74e443526fe2f11562f0d2b2d691`). Await screen photos to confirm build identity and whether xpcproxy setup EPERM is resolved or another gate is reached. Reboot success is not proof of successful XNU/userland startup.

### Video verifies daemon launch after entitlement repair — 2026-10-25

- Inspected user video IMG_0724.mov (8.537 seconds), extracting frames at 0/2/4/6/8 seconds and checking the images visually alongside OCR. Local evidence is saved under ignored `research/veux-logs/entitlements-fixed-boot-0724/`. Video does not show the early build-ID line; attribution to 40231594906 plus repaired root follows the verified slot-B flash/reboot sequence above.
- Runtime milestone: xpcproxy executes, followed by SpringBoard, mediaserverd, bluetoothd, identityservicesd, mDNSResponder, watchdogd, fairplayd.H2 and backboardd. This demonstrates progression past the prior repeated spawn-setup EPERM after restoring launchd entitlements. The exact earlier failing hook remains inferred (persona validation), and no visible DEV ALLOW line establishes whether the DRIVER diagnostic exception is exercised.
- New failures: SpringBoard repeatedly SIGTRAP (5), PC/LR `0x1eeefcca8`, shared-cache slide `0x53594000`, reason namespace 2/code 5 with no text. At ~4 seconds its backtrace includes `0x1f5c24438 0x1e112c780 0x1e10fcddc 0x1f5bd5a30 0x1f5c381b4 0x218df95c8 0x1f7bb8344` (manual transcription; symbolication pending). backboardd pid 214 SIGABRT (6) at ~8 seconds, PC `0x215bab198`, LR `0x22513a5f8`, reason namespace 2/code 6, no text. mediaserverd SIGSEGV (11), visible PC `0x1da3f28cc` / FAR 0. identityservices aborts; mDNSResponder exits 71.
- watchdogd explicitly prints `ERROR: failed to discover watchdog KEXT service`, then SIGTRAP at `0x100ba71d8` (main image base `0x100b9c000`). The corpse-limit message is downstream crash-report saturation, not evidence of the original crash cause. Adjacent xpcproxy EXIT records and same-PID target exec records must not be treated as fresh spawn-policy failures.
- Current source/notes already identify the VEUX GUI gap: framebuffer console is present, but IOSurface/IOMobileFramebuffer/backboardd display/HID support is not ported to VEUX; the SWEET 0046 surface/display implementations remain SWEET-guarded. SWEET's historical SpringBoard FBSDisplayMonitor trap, backboardd uncaught exception, and missing watchdog service are relevant precedents, not yet exact symbolication of this video's stacks. Next: symbolize the captured SpringBoard/backboardd addresses against this root's cache and plan the VEUX display-service compatibility port, with watchdog service registration considered separately. No device reset, flash, or source behavior change was made while reviewing the video.

### Exact GUI crash symbolication and software display experiment — 2026-10-25

- Exact saved-root cache resolves SpringBoard PC to FBSDisplayMonitor `_initWithBookendObserver:transformer:+1160`, the same pre-display trap documented on SWEET. Backboardd resolves through pthread_kill/abort/_objc_terminate/std::terminate; exact exception text still unknown. Full evidence and limitations: `docs/VEUX-GUI-BRINGUP.md`. REA Ghidra import failed on CoreFoundation dependency; successful symbolication/disassembly is from local ipsw, not REA decompilation.
- Added 0123 software display-service port: VEUX-only startup gate `veux_gui=1`, existing software IOSurface/AppleCLCD/watchdog compatibility, only disp0 nub publishing, exact validated ADT framebuffer geometry. No HID/SEP/panel-controller MMIO port. `veux_gui_noconsole=1` optionally hands pixels to first valid copied BGRA layer; normal console/bitdump pauses, last25 capture continues, panic reclaims pixels and stops GUI refresh.
- Local checks: all7 modified TUs syntax compile, final2 affected TUs recompiled after review fixes, zero-fuzz patch applicability, repository integrity and Python syntax checks pass. Workflow/manifest now require patch0123, GUI boot args, binary strings and source constraints. Next: commit/push and strict CI; no phone write or reboot was performed for this experiment yet.

### VEUX GUI clipping audit, strict CI and wrapper — 2026-10-25

- Checked the requested `display_audit` follow-up. No live agent with that name
  appeared in the collaboration inventory, and the tracked working tree had no
  uncommitted follow-up. The framebuffer rectangle clipping correction was
  completed in commit `d2933ae`; `0f66997` aligns the patch hunk with the exact
  XNU 8796 `present()` source after patches 0046/0056/0061. Layer coordinates
  and crop math now use 64-bit intermediates, clamp to display/surface bounds,
  validate source byte-extent arithmetic before copying, and iterate rows with
  a 64-bit counter. The host console test harness supplies the new GUI mute and
  panic-state symbols.
- CI run `40249653049` failed in the synthetic console host compile because
  that harness lacked `veux_gui_console_muted` and `panic_active`. Run
  `40251140627` then failed strict patch application because the new clipping
  hunk targeted the wrong source position. The hunk was reconstructed and
  checked against XNU 8796.141.3, and the host console test passed against the
  patched source. Run `40251701960` applied patches and built the kernel; its
  manifest failed only on a source-policy predicate spelling mismatch. The
  manifest then passed locally against that run's exact kernel and build-tree
  source. Commit `c68caf2` corrected the predicate.
- Final CI run `40252779285` is green on commit
  `c68caf286b7f2da68b5734fcbc80a0f660236424`. Strict zero-fuzz patch
  application, XNU compile, synthetic host bounds checks, kernel feature
  manifest, packaging, and artifact upload all passed. Kernel SHA-256:
  `96c2d29e2a459bc6954cf835857eb8fd8cd76ca1432225fdc8562fe6b2f1ed4e`.
- Assembled and independently verified
  `shim/out/veux-xnu-40252779285-rw-gui/shim-boot-veux-xnu-40252779285-rw-gui.img`
  from the CI kernel, the ADT embedded in the verified boot-v2 template, and
  phone DTB `dtb/vendor_boot_b_unpacked/dtb_1.dtb`. Wrapper SHA-256:
  `046a61d1db7d5602233df7cdd55a55063fced16b2cc93cdf77b632eeb284570f`;
  payload SHA-256:
  `ab6fe647afa5024ae1426d1248d1621588912573e12092cbe45755fee8bf843e`;
  DTB SHA-256:
  `08284b0f3b0d3810abda6d617598370099f36f0f54110668bfe89f6ee35b4e2e`.
  The adjacent wrapper manifest confirms that the payload reconstructs from
  the CI kernel and embedded ADT and that wrapper payload, DTB and boot args
  match the supplied inputs. Boot args include `veux_gui=1
  veux_gui_noconsole=1` with the established RW pair.
- User confirmed flashing. Fastboot verified serial `4078cac030c8`, product
  `veux`, unlocked, active slot B, and `boot_b` size `0x8000000`; the wrapper
  hash matched the verified manifest. Flashed only the wrapper to `boot_b`
  (`Sending` and `Writing` both OKAY), then issued `fastboot reboot` (OKAY).
  No userdata or other partition was written; the entitlement-repaired root
  was left in place. Do not restore the older stripped-entitlement image.
- After reboot, both ADB and Fastboot enumeration were empty. The subsequent
  user video is documented below; it does not visibly identify build ID
  `40252779285`, so attribution follows the verified flash/reboot sequence.
  The display handoff has not succeeded in the observed footage. No userdata
  or other partition was written; do not restore the older stripped-entitlement
  image.

### IMG_0729 video evidence — 2026-10-25

- Reviewed the 8.2-second attached `IMG_0729.mov` using extracted frames and
  OCR. The phone remains on the diagnostic framebuffer with its colored bottom
  strip throughout; there is no visible SpringBoard GUI handoff. The screen
  says `sweet milestone: 4: xnu loader`, but does not show the CI run/build ID.
- The footage shows SpringBoard SIGTRAP (signal 5, namespace 2/code 5; visible
  PC `0x1de83cca8`), mediaserverd SIGSEGV (signal 11; visible PC
  `0x1c9d320cc`), identityservices aborting, and backboardd SIGABRT (signal 6,
  namespace 2/code 6), followed by repeated crash/corpse-limit output. This
  establishes userland launch and a failed GUI runtime outcome, not successful
  display-service behavior. Exact build attribution is not legible on-screen.
- CI run `40252779285` remains green, and the verified wrapper was flashed to
  `boot_b` with Fastboot send/write and reboot returning OKAY. Those are build
  and partition-write results only; they do not mean GUI bring-up passed.
  Investigate the new runtime addresses against the correct cache/build before
  making another wrapper or phone write. Keep the entitlement-repaired root;
  never restore the old stripped-entitlement image.

### GUI crash root cause and enumeration trace follow-up — 2026-10-25

- Re-expanded the entitlement-repaired 20H392 sparse root to a temporary raw
  image and mounted its HFSX volume read-only. The dyld cache reports iOS 16.7;
  the video slide `0x42ed4000` maps SpringBoard PC `0x1de83cca8` to unslid
  `0x19b968ca8`, exactly
  `-[FBSDisplayMonitor _initWithBookendObserver:transformer:]+1160`.
- Disassembly shows this trap is the `CADisplay.displays.firstObject == nil`
  branch. `FrontBoardServices` contains the associated error string
  `failed to find the main CADisplay`. Therefore userland is not enumerating a
  main display; no first valid layer can reach the framebuffer handoff. The
  exact missing kernel-side link is still unknown. The shim ADT does contain
  `/arm-io/disp0` with `device_type=display-subsystem` and
  `compatible=sweet,display`, so static ADT intent is present but does not
  establish that the IOKit nub and service start on-device.
- Added patch `0124-veux-display-enumeration-trace.patch` to emit bounded
  markers for the `/arm-io/disp0` nub, AppleCLCD start/setup/registration,
  IOMobileFramebuffer user-client start, and first swaps. Workflow and kernel
  manifest require these markers. Local patch-format, Python syntax,
  `git diff --check`, and repository integrity checks pass. The follow-up has
  not yet been compiled by XNU CI or run on-device. No phone write occurred.
- Next: commit and push the trace patch, run strict XNU CI, assemble/verify its
  wrapper, then obtain confirmation before writing the new wrapper to `boot_b`.
  Keep the entitlement-repaired root and do not restore the older image.

### Display enumeration trace patch-application repair — 2026-10-26

- CI run `40257589855` failed before XNU compilation: patches through `0123`
  applied, but trace patch `0124` was authored against the pre-`0123`
  `SweetFramebuffer.cpp` layout. The package-buildtree failure was downstream
  because no kernel object was produced.
- Rebuilt the framebuffer portion of `0124` from the successful CI run
  `40252779285` packaged source tree, which contains the exact post-`0123`
  source. The updated trace hunks cover AppleCLCD startup/setup/registration,
  first display presents and IOMFB user-client start. The patch applies with
  `git apply --check` to that packaged source; `tools/validate-repo.py` and
  Python syntax validation pass.
- Next: commit and push the correction, run strict XNU CI, then package and
  independently verify the new wrapper. Keep the entitlement-repaired root;
  phone writes remain limited to the confirmed `boot_b` wrapper operation.

### VEUX display trace build 40258406080 and slot-B flash — 2026-10-26

- CI run `40257589855` failed before compilation because trace patch `0124`
  used pre-`0123` `SweetFramebuffer.cpp` hunk context. Commit `cddfa2a`
  regenerated the framebuffer hunks from the exact packaged post-`0123`
  source tree. Local repository/Python validation passed and the corrected
  patch applies to that source snapshot.
- CI run `40258406080` completed successfully: strict patch application,
  XNU compilation, synthetic host bounds checks, kernel feature manifest,
  build-tree packaging and artifact upload passed. Patch status confirms
  `0124-veux-display-enumeration-trace.patch APPLIED`. Kernel SHA-256:
  `d9df6c247e6da4f7b39840c273a1a4edd19b277d86e1d62729e42ea4c88b739a`.
- Assembled and independently verified
  `shim/out/veux-xnu-40258406080-rw-gui/shim-boot-veux-xnu-40258406080-rw-gui.img`
  using the exact CI kernel, the ADT embedded in the prior verified wrapper,
  and phone `dtb_1.dtb`. Wrapper SHA-256:
  `bc3e23941a64cf27ea2aefd6820730503b692a1eb2fa5c462b5bbcf55d6bf25f`;
  DTB SHA-256:
  `08284b0f3b0d3810abda6d617598370099f36f0f54110668bfe89f6ee35b4e2e`.
  The verifier confirms exact payload reconstruction, boot args, build/run ID,
  and DTB.
- User explicitly requested flashing. Fastboot identified serial `4078cac030c8`,
  product `veux`, unlocked, active slot B, and `boot_b` size `0x8000000`. Only
  `boot_b` was written (`Sending`/`Writing` OKAY); `fastboot reboot` returned
  OKAY. No userdata or other partition was written. The entitlement-repaired
  root remains in place; do not restore the older image.
- After reboot both ADB and Fastboot enumeration were empty. No fresh screen
  capture or visible build ID is available, so the runtime result and GUI
  handoff remain unverified despite the green CI and successful flash.

### IMG_0735 and IMG_0736 display trace evidence — 2026-10-26

- Reviewed both new clips with frame sampling and OCR. IMG_0735 (6.0 s) and
  IMG_0736 (8.1 s) stay on the diagnostic framebuffer; neither demonstrates a
  GUI handoff or visibly prints a build ID.
- IMG_0736 visibly prints
  `VEUX GUI: IOMFB user client provider=AppleCLCD framebuffer=1`. This proves
  the IOMobileFramebuffer user-client start hook is reached and its provider
  successfully casts to AppleCLCD. The message occurs before the call to
  `IOUserClient::start`, so it does not alone prove the base start completed.
  No first-valid-present marker is visible.
- The same clip records SpringBoard SIGTRAP at PC `0x1b0814ca8`, slide
  `0x146ac000`, unslid `0x19b968ca8`, resolving to the known
  `FBSDisplayMonitor+1160` nil-main-CADisplay trap. It also shows
  `IOMFB_FDR_Loader` exiting with status 1. Its root launchd plist runs it on
  the `com.apple.fdr.load` matching event for services with
  `IOMFBLaunchFDR=true`; this exit is not yet tied to missing `CADisplay`.
  The trace marker supports that 0124 code ran, but the build ID is not visible;
  exact CI-run attribution remains unconfirmed.
- Next: inspect the IOMobileFramebuffer-to-CADisplay registration path and the
  `IOMFB_FDR_Loader` failure. No phone write was made for these clips; do not
  claim GUI bring-up succeeded.

### Earlier IMG_0731–IMG_0733 boot sequence and registry-path follow-up — 2026-10-26

- The user clarified these clips predate IMG_0735/0736. OCR plus visual review
  confirms AppleCLCD starts from `disp0`, validates the firmware framebuffer,
  creates its surface/mapping/workloop/lock/client list, registers at
  1080x2400, and finds `/arm-io/disp0`. Nub publication and AppleCLCD startup
  are therefore not the remaining gap.
- Extracted the exact ADT embedded in wrapper 40258406080 (not the stale local
  `shim/out/veux.adt`): it has `/arm-io/disp0` with
  `device_type=display-subsystem`, `compatible=sweet,display`, canvas
  1125x2436, and the validated 1080x2400 / 4320-stride framebuffer node.
- Patch `0125-veux-software-framebuffer-registry-properties.patch` explicitly
  republishes geometry on the live IOKit provider, sets
  `IOMFBLaunchFDR=false` because this service has no panel firmware loader,
  and logs the process name/result through user-client init/start. This tests
  whether the main display path opens the connection and calls selectors. The
  FDR exit is not yet proven causal; no GUI success is claimed.
- Patch `0125` applies with zero fuzz to the 40258406080 packaged post-0124
  XNU source. `tools/validate-repo.py` passes. Next: local compile-check the
  changed translation unit, update the kernel feature manifest, commit/push,
  run strict CI, package and independently verify the wrapper, then flash only
  `boot_b` when the phone is available. At last check, both ADB and Fastboot
  were disconnected. Preserve the repaired root and do not touch userdata.

### VEUX software-display registry experiment 40262764380 — CI, wrapper, flash — 2026-10-26

- User supplied earlier boot-sequence clips (IMG_0731–IMG_0733), already reviewed in the preceding handoff. They show `/arm-io/disp0` discovery, AppleCLCD start and registration, and a 1080x2400 framebuffer. The later IMG_0736 evidence also showed the IOMobileFramebuffer user-client hook reached with AppleCLCD as provider, followed by the established SpringBoard nil-main-CADisplay trap. These observations place the remaining failure after service startup; they do not identify the exact missing CADisplay registration edge.
- Added patch `0125-veux-software-framebuffer-registry-properties.patch`: explicitly publishes display-subsystem type/canvas dimensions on AppleCLCD's live IOKit provider, disables panel FDR launch for the software framebuffer, and adds user-client init/ready process markers. `IOMFBLaunchFDR=false` is a hypothesis for a software-only framebuffer; its causal role has not been demonstrated.
- Strict CI run [40262764380](https://github.com/59c84486t9-alt/ios-veux/actions/runs/40262764380) passed patch preflight/application, XNU compilation, synthetic bounds checks, kernel feature manifest, build-tree packaging, and artifact upload. Patch 0125 is recorded APPLIED. Kernel SHA-256: `2149765497827cc6ed2cd516a0e369d85062037dd5b0aada76382a9cfab60167`.
- Created the boot-v2 wrapper using the exact shim-kernel bytes and header from the previously verified 40258406080 wrapper, the new CI payload, the exact ADT embedded in that verified wrapper, and the phone DTB. The stale local `shim/out/Image` differed byte-for-byte from the verified wrapper's shim kernel, so it was not substituted. The host shim console test passed. `tools/verify-veux-wrapper.py` passed exact CI-kernel/embedded-ADT reconstruction, payload, DTB, build/run ID, boot-args, and patch-status checks. Wrapper SHA-256: `d1589c81376e77dc9640b0c5d53c499d5915b6f08feea0c18fc5cc8bf844b2a5`; DTB SHA-256: `08284b0f3b0d3810abda6d617598370099f36f0f54110668bfe89f6ee35b4e2e`. Manifest is alongside the image under `shim/out/veux-xnu-40262764380-rw-gui/`.
- Fastboot identified serial `4078cac030c8`, product `veux`, current slot B, and `boot_b` size `0x8000000`. `fastboot flash boot_b` returned Sending/Writing OKAY; `fastboot reboot` returned OKAY. Only `boot_b` was written. No userdata write occurred; retain the entitlement-repaired root and do not restore the older stripped-entitlement image.
- Immediately after reboot, neither ADB nor Fastboot enumerated the device. There is no screen/build-ID observation for 40262764380. Therefore CI/build and flash are confirmed, but the registry-property hypothesis and GUI handoff remain unvalidated on-device. Next: inspect the phone's next boot evidence for build ID `40262764380`, `IOMFB client initialized/ready` markers, and SpringBoard's FBSDisplayMonitor result. Do not call the GUI issue fixed until that runtime evidence shows CADisplay enumeration and handoff.

### IMG_0738–IMG_0740 analysis and IOMFB client fallback build 40265617103 — 2026-10-26

- Reviewed all three post-402627 clips with frame sampling and OCR. IMG_0738 shows launchd launching SpringBoard. IMG_0739 shows `IOMFB client initialized process=IOMFB_FDR_Loader type=0` and `IOMFB user client provider=AppleCLCD framebuffer=1`; the loader then receives SIGABRT, driverkitd is killed, and backboardd receives SIGABRT. IMG_0740 continues the SpringBoard restart loop with SIGTRAP at PC `0x1b75c8ca8`, the known FBSDisplayMonitor nil-main-CADisplay trap. No `IOMFB client ready` marker or GUI handoff is visible. The clips demonstrate that 0125's init/provider hooks ran, but do not prove whether `start` completed before the loader aborted.
- Added patch `0126-veux-iomfb-client-start-fallback.patch`: sets `IOMFBLaunchFDR=false` on both `/arm-io/disp0` and the AppleCLCD service (0125 only set it on the service), explicitly initializes user-client framebuffer/port/notification state, and lets the VEUX software client complete registration if its superclass start returns false. It adds an FDR policy result marker; the existing client-ready marker confirms completion. This is an experiment to address the loader/client path, not proof that FDR caused the SpringBoard failure.
- Strict CI run [40265617103](https://github.com/59c84486t9-alt/ios-veux/actions/runs/40265617103) passed repository preflight, zero-fuzz patch application (0126 APPLIED), XNU compile, synthetic bounds checks, feature manifest, build-tree packaging, and artifact upload. Kernel SHA-256: `9402dc7e1033db8e72d5be67e03e93644f0609a37af9f141e8dd5f68b70af7b1`.
- Assembled wrapper `shim/out/veux-xnu-40265617103-rw-gui/shim-boot-veux-xnu-40265617103-rw-gui.img` from that exact CI kernel, the exact ADT embedded in the prior verified wrapper, the phone DTB, and the previously verified shim kernel/header. Independent verification passed. Wrapper SHA-256: `7c33d9018630e6d0cc3c56136c58fd1136f05052b10272a68bbea6b1ab0a5b3a`; DTB SHA-256: `08284b0f3b0d3810abda6d617598370099f36f0f54110668bfe89f6ee35b4e2e`.
- Fastboot identified serial `4078cac030c8`, product `veux`, current slot B, `boot_b` size `0x8000000`. Flashed only `boot_b`; Sending/Writing and reboot returned OKAY. No userdata write occurred; preserve the entitlement-repaired root and do not restore the stripped-entitlement image. Immediately after reboot, neither ADB nor Fastboot enumerated the phone. Wait for post-flash evidence showing build ID `40265617103`, the FDR policy/client-ready markers, and the SpringBoard CADisplay outcome before claiming the GUI issue is fixed.

### IMG_0742–IMG_0744 early-boot review — 2026-10-26

- All three clips show `VEUX GUI: FDR policy provider=1 service=1`; AppleCLCD
  validates the framebuffer and registers 1080x2400. This confirms the 0126
  property writes were accepted and that the software service started. The
  clips end before `IOMFB client initialized/ready`, SpringBoard, or the
  FBSDisplayMonitor result. There is no visible CI run ID, so do not treat this
  footage as GUI validation or unique attribution to run 40265617103.
- IMG_0744 shows FIPS POST passing. The keybag task's `/usr/bin/true` attempt
  returns `errno=2` while `path_errno=0`; launchd then says the optional boot
  task is absent and starts usermanagerd. A separate exit trace is for PID 11,
  process name `launchd`, signal 1/SIGHUP; it is not PID 1 and does not show
  that the main launchd exited. These lines do not currently explain the
  missing main `CADisplay`.
- The `display_audit` agent is not present in the live agent inventory. The
  tracked tree had no outstanding implementation diff: the 64-bit clipping
  correction is already in commit `d2933ae`, with exact XNU hunk alignment in
  `0f66997`; subsequent green GUI CI runs include it.
- Confirmed CI run 40265617103 completed successfully on
  `7ba9087e3c3714894864ff350dd931e9dd6d4898`. Device Fastboot variables before
  reboot were product `veux`, unlocked, current slot B, `boot_b` size
  `0x8000000`. A read-only `fastboot reboot` returned OKAY; after 20 seconds
  neither Fastboot nor ADB enumerated. No partition or root image was written.
- The 0126 candidate remains the latest successful CI and `boot_b` flash; the
  new footage is too short to decide whether its client-start fallback reaches
  the main display path. Continue only after obtaining boot evidence past the
  usermanagerd task or another observable run; preserve the repaired root and
  limit any future phone write to the already authorized `boot_b` partition.

### IMG_0747 and IOMFB display-list property experiment — 2026-10-26

- The user identifies IMG_0747 as later footage from the same boot as
  IMG_0742–IMG_0744. The screen shows backboardd aborting and SpringBoard's
  repeated SIGTRAP. SpringBoard PC `0x1c9e84ca8` minus slide `0x2e51c000` is
  unslid `0x19b968ca8`, the known FBSDisplayMonitor+1160 nil-main-CADisplay
  trap. No client-ready/first-present marker or build ID is visible in this
  clip. The main display still does not enumerate.
- The iOS 16 IOMobileFramebuffer discovery path reads `dfr`, `AppleTV`, and
  `external` from each matching service. Existing AppleCLCD code sets only
  `external=false` explicitly. Added patch `0127` to set all three service
  flags false and log whether the registry property writes were accepted. This
  is a targeted hypothesis; no causal success is claimed yet.
- Patch 0127 applies with zero fuzz to the exact XNU source tree packaged by
  successful CI 40265617103. `tools/xnu-cc.py` compiles the changed
  `SweetFramebuffer.cpp` against that build's arm64 configuration with 0 of 1
  files failed. `tools/validate-repo.py`, Python syntax compilation, and
  `git diff --check` pass. Workflow and kernel manifest now require patch 0127,
  its binary marker, and source assertions for all three properties.
- Next: commit and push this candidate, dispatch strict macOS 13.5 DEVELOPMENT
  VEUX CI, assemble and independently verify a wrapper from the green artifact,
  then flash only `boot_b` under the existing authorization. Preserve the
  entitlement-repaired root and distinguish build/flash success from a GUI
  runtime pass.

### IOMFB display-list metadata experiment 0127 — CI and verified wrapper

- User's IMG_0747 confirms same-boot backboardd/SpringBoard crashes; SpringBoard
  PC `0x1c9e84ca8` minus slide `0x2e51c000` resolves to the known
  FBSDisplayMonitor+1160 nil-main-CADisplay trap. It shows no IOMFB client
  ready/first-present marker or build ID.
- Patch 0127 explicitly sets the three display-list flags (`dfr`, `AppleTV`,
  `external`) false on AppleCLCD and logs setter results. Local zero-fuzz
  application against packaged XNU 402656 source, single-file ARM64 compile,
  repository validation, and Python syntax checks passed. Commit
  `30ed37b93539c62a0b0137b212dd8b1ec0e4c149` was pushed to `veux-xnu-build`.
- Strict CI run [40268776775](https://github.com/59c84486t9-alt/ios-veux/actions/runs/40268776775)
  succeeded: repository/patch preflight, XNU compile, host bounds checks,
  feature manifest (0127 APPLIED and marker/source assertions), packaging, and
  artifact upload all passed. Kernel SHA-256:
  `e5e5715c365cc0390b59bc0fa6510e2fae94d862e2a4b4e0c982a53a86b7c062`.
- Built and independently verified wrapper
  `shim/out/veux-xnu-40268776775-rw-gui/shim-boot-veux-xnu-40268776775-rw-gui.img`
  from the CI kernel, the verified prior shim/header, embedded ADT, and phone
  DTB. Wrapper SHA-256:
  `21d6bb6a2bf80d84d6ef11a7bcd76924664e5083d46f7f0f8851faa47e32b7e7`;
  DTB SHA-256:
  `08284b0f3b0d3810abda6d617598370099f36f0f54110668bfe89f6ee35b4e2e`.
- Flash is pending because repeated Fastboot/ADB and IOUSB checks found no
  connected phone. No partition/root write occurred this turn. Once it returns
  in Fastboot, verify product/unlock/slot/partition capacity and write only
  `boot_b`, as previously authorized. Preserve the entitlement-repaired root.
  Build and wrapper verification do not prove GUI success; get later on-device
  evidence for client-ready/first-present and SpringBoard outcome.

### Patch 0127 boot_b flash — 2026-10-26

- After the user reconnected the phone, Fastboot reported serial `4078cac030c8`,
  product `veux`, unlocked `yes`, current slot `b`, and `boot_b` capacity
  `0x8000000`. The verified wrapper SHA-256 matched its adjacent manifest:
  `21d6bb6a2bf80d84d6ef11a7bcd76924664e5083d46f7f0f8851faa47e32b7e7`.
- Flashed only `boot_b` with wrapper from CI 40268776775. Fastboot `Sending`
  and `Writing` both returned OKAY; `fastboot reboot` returned OKAY. No
  userdata or other partition was written. The entitlement-repaired root was
  preserved; do not restore the stripped-entitlement image.
- Fifteen seconds after reboot, neither Fastboot nor ADB enumerated. This
  confirms the flash/reboot command sequence, not on-device GUI success. Await
  longer runtime evidence for patch 0127's list-property marker, IOMFB client
  ready/first present, and SpringBoard's main-display result.

### IMG_0757 follow-up — 2026-10-26

- The photo shows patch-0127-specific `IOMFB list properties dfr=1 AppleTV=1 external=1` after AppleCLCD registered its validated 1080x2400 software framebuffer. These are setter-success booleans; patch 0127 stores false for each property. The image does not show a client initialized/ready marker or first software present.
- Both 8.05-second clips show the same SpringBoard signal-5 report followed by backboardd abort. The SpringBoard PC OCR is `0x1cd158cab`, slide `0x24af0000`; the repaired iOS 16.7 shared cache maps the unslid address near `0x1a8628cab` to `GameCenterUI.AchievementHighlightLayout.init(...)` around +0x47. The stack includes `FBDisplayManager.sharedInstance` and `FBSystemShellInitialize`. This differs from the earlier FBSDisplayMonitor+1160 PC, but OCR transcribes an unaligned arm64 address, so verify with a sharper crash frame/report before asserting an exact symbol.
- The frame also reports FAR `0x2068e5b28`; at the nearest aligned instruction (`stp q0, q1, [x21, #0xa0]`) this is consistent with a fault while writing the GameCenterUI layout result. It does not yet reveal why the destination is invalid. The display-manager singleton remains on the stack, so keep the display bring-up path under investigation.
- The evidence confirms framebuffer setup and accepted property writes, not that IOMFB produced a `CADisplay`, that a client opened, or that GUI handoff happened. The clips lack a build ID; the photo's 0127 marker does confirm the current experiment's code ran.
- Fastboot/ADB are absent on this host now. No new partition write was made. Keep the repaired root; any next test remains limited to the already authorized `boot_b` write after a new candidate passes CI and wrapper verification.

### Recovery check for SpringBoard crash report — 2026-10-26

- At the user's request, verified Fastboot serial `4078cac030c8`, product `veux`, unlocked, current slot B, then selected slot A and rebooted to recovery; both commands returned OKAY. Recovery ADB connected as root after restarting the host ADB server with `ADB_LIBUSB=1` (the default macOS USB backend exited with `e00002be`).
- Read-only ADB showed `/dev/block/sda22` is the 109,156,577,280-byte userdata partition. Recovery does not mount it and has no HFS+ filesystem support. Its first blocks contain an HFSX `iOSRoot` volume with 4,194,304 × 4096-byte blocks (16 GiB). Copied only that volume to a temporary host file, made a copy-on-write clone for analysis, repaired that clone locally with `fsck_hfs -fy`, and mounted the clone read-only. Neither the phone nor the original capture was repaired or written.
- No `.ips`, `.crash`, `.panic`, or `.hang` report was found. `/private/var/mobile/Library/Logs/CrashReporter` contained only `Assistant` and an empty `DiagnosticLogs`; `/private/var/logs/CrashReporter` and `Panics` were empty. The temporary raw copies were deleted after the search. The result is that no saved SpringBoard report is present in those locations in this snapshot; it cannot rule out an unflushed report lost on reboot.
- The phone is left in recovery with root ADB available. No additional Fastboot or ADB write command was issued.

### Next GUI diagnostics — patch 0128 candidate — 2026-10-26

- Recovery ADB is root on slot A recovery; `/sys/fs/pstore` and `/proc/last_kmsg` are empty. The previous boot's iOS HFSX root contains no saved SpringBoard report in the standard CrashReporter or Panics directories. No phone partition writes were made.
- Added candidate patch `0128-veux-gui-exit-summary.patch`: on SpringBoard/backboardd exit, print a compact state snapshot for AppleCLCD registration, FDR/list property setter results, IOMFB client init/ready counts and processes, selector mask/last caller, swap count, and first valid present. It adds no display behavior and is intended to preserve the trace after console scrolling.
- Patch 0128 applied with zero fuzz to the exact source extracted from successful CI 40268776775. `tools/xnu-cc.py` compiled both changed translation units with 0/2 failures; repository validation, Python syntax compilation, and `git diff --check` passed. CI, wrapper verification, and a `boot_b` test subsequently passed; see the entry below. The entitlement-repaired root was preserved.

### Patch 0128 CI, verified wrapper, and boot_b flash — 2026-10-26

- Strict CI run [40329697379](https://github.com/59c84486t9-alt/ios-veux/actions/runs/40329697379) passed on commit `e899b868b4ef8d9ee64a6f499aeef67dade56361`. XNU build, synthetic framebuffer bounds checks, kernel feature manifest, build-tree packaging, and artifact upload all succeeded; patch `0128-veux-gui-exit-summary.patch` is `APPLIED`. Kernel SHA-256: `29337e2eb8323317f0275597b49335d1540cd5c613b802fb662d6e898a5ce984`.
- Built `shim/out/veux-xnu-40329697379-rw-gui/shim-boot-veux-xnu-40329697379-rw-gui.img` from the exact CI kernel, previously verified shim kernel/header and embedded ADT, established GUI/RW boot args, and phone DTB. `tools/verify-veux-wrapper.py` passed payload reconstruction, DTB, build/run ID, boot-argument, and patch-status checks. Wrapper SHA-256: `e35b50e5920c2bb3575a8f30f6f51fcb52f9412239e7608ebf5cb2413d9488b2`; phone DTB SHA-256: `08284b0f3b0d3810abda6d617598370099f36f0f54110668bfe89f6ee35b4e2e`.
- Recovery ADB was connected as root, then rebooted to Fastboot. Fastboot confirmed serial `4078cac030c8`, product `veux`, unlocked `yes`, current slot A, boot slot support, and `boot_b` capacity `0x8000000`. Flashed only `boot_b` (send/write `OKAY`), selected slot B (`OKAY`), and rebooted (`OKAY`). No userdata or other partition was written; the entitlement-repaired root was preserved.
- At the 10-second post-reboot check, neither ADB nor Fastboot enumerated. This verifies the flash/reboot command sequence, not runtime or GUI success. Await a screen capture showing build ID `40329697379` and the patch-0128 SpringBoard/backboardd exit summary, including IOMFB client readiness, selector callers, presents, and exit status.

### IMG_0763 — patch 0128 exit summary and repeated nil-display trap — 2026-10-26

- Sampled both clips at one-second intervals and ran OCR on the early registration and post-crash frames. The patch-0128-specific exit summary confirms this is the diagnostic boot following CI 40329697379, although no build ID is legible in the clips.
- The summary reads: `registered=1 fdr=0x3 list=0x7 init=1/0:IOMFB_FDR_Loader ready=1:IOMFB_FDR_Loader last=4294967295/none selectors=0x0 swaps=0 present=0`. AppleCLCD registered; both FDR setter calls and all three display-list setter calls reported success. These bit fields are setter-success flags, not observed stored values. Exactly one user-client init and ready are recorded, both for `IOMFB_FDR_Loader` with type 0. There are no selectors, swaps, or software presents before SpringBoard exits.
- SpringBoard reports PC `0x1dbcf4ca8` with slide `0x4038c000`, giving unslid `0x19b968ca8`. `ipsw dyld a2s` against the local 20H392 cache resolves it to `-[FBSDisplayMonitor _initWithBookendObserver:transformer:]+1160`, the same nil-main-CADisplay trap seen in earlier boots. SpringBoard exits signal 5; backboardd later exits signal 6. Lockdownd also hits “Too many corpses being created.” No GUI handoff is shown.
- This places the remaining gap before a window-server client reaches the kernel display service: the FDR loader can initialize and ready a client, but no display selectors or presents occur. It does not establish whether the IOMobileFramebuffer matching callback rejected AppleCLCD or SpringBoard failed before the matching/open path. Next inspect the framework display-list matcher/main-display selection against the generated DeviceTree and live IOKit service properties. Rectangle clipping and surface-copy code are downstream of this failure.

### Recovery unified-log analysis and sandbox opt-in candidate — 2026-10-26

- Recovery ADB was authorized by the user and connected as root. Read-only extraction of the previous boot's 16 GiB HFSX root found no SpringBoard `.ips`/`.crash` report. The root contains 92 MiB of persisted tracev3 Unified Logs; `/private/var/db/uuidtext` has no format strings, so the external parser can recover launchd lifecycle text, not app/framework log messages. The store contains eight boot UUIDs; aggregate counts must not be attributed to one build.
- Across the persisted boots, launchd repeatedly records `error = 159: Sandbox restriction` for SpringBoard lookups including `com.apple.backboard.system-app-server`, `com.apple.CARenderServer`, and `com.apple.chronoservices`, and for backboardd lookups including `com.apple.iohideventsystem`, `com.apple.mobilegestalt.xpc`, and `com.apple.containermanagerd`. The archive also contains SpringBoard SIGTRAP and backboardd SIGABRT exit records. These are recurring records; the archive spans multiple boots.
- Existing patch `0099-veux-amfi-sandbox.patch` registers a permissive `Sandbox` MAC-policy stand-in only when `veuxsandbox=1` is present. CI 40329697379 confirms patch 0099 is APPLIED, but the flashed wrapper boot args omitted `veuxsandbox=1`. Earlier notes already document that without the stand-in, libsystem_sandbox receives `ENOPOLICY`, which launchd reports as error 159. This is now the strongest actionable cause for the missing backboard display service and nil `CADisplay`; it remains a hypothesis until the policy is seen registered and runtime display lookup succeeds.
- The current trace-only wrapper `shim/out/veux-xnu-40329697379-iokit-trace/shim-boot-veux-xnu-40329697379-iokit-trace.img` has SHA-256 `2ac8585049fa0d2c6765d05a84bb53045a4a6382b201efae1eb67f2eddcbc0b5`. It reuses the green CI 40329697379 kernel and adds `veuxiolog=backboardd,SpringBoard`; only `boot_b` was written, slot B selected, then rebooted. ADB/Fastboot did not enumerate at the eight-second check, so this boot has no runtime assessment yet.
- Prepared the next wrapper from that same green CI kernel, adding both `veuxsandbox=1` and `veuxiolog=backboardd,SpringBoard`. Remote build and local `tools/verify-veux-wrapper.py` both passed; exact kernel SHA-256 remains `29337e2eb8323317f0275597b49335d1540cd5c613b802fb662d6e898a5ce984`, DTB SHA-256 remains `08284b0f3b0d3810abda6d617598370099f36f0f54110668bfe89f6ee35b4e2e`, wrapper SHA-256 is `6f4ff70eb38990a9cc454b21d917d23655d92e56188056ebf1109ccd563b6786`. No source changed, so this reuses the successful CI result rather than dispatching a redundant kernel build. The phone has not been seen in Fastboot after the previous reboot; this wrapper is ready but not yet flashed.
- Fastboot reappeared on serial `4078cac030c8`; product `veux`, unlocked `yes`, current slot B, and `boot_b` capacity `0x8000000` were verified. Flashed only `boot_b` with the wrapper above, selected B, and rebooted; all Fastboot operations returned OKAY. No userdata or root-image write occurred. At 10 seconds after reboot, neither ADB nor Fastboot enumerated. The sandbox-enabled build is flashed, but its runtime effect and GUI outcome are not yet observed.
- Next: obtain the current boot's full screen or reconnect ADB. Look for `VEUX Sandbox: permissive policy registered`, then IOKit matching/open traces from backboardd and SpringBoard's main `CADisplay` outcome. Treat successful CI, wrapper verification, flash, and GUI validation as separate results. Preserve the entitlement-repaired root and do not write userdata.

### IMG_0777–IMG_0778 sandbox-enabled boot evidence — 2026-10-26

- The still repeats patch-0127 framebuffer setup: AppleCLCD registers the
  validated 1080x2400 software surface and the FDR/display-list property
  setters report success. This confirms provider setup, not a framework
  `CADisplay` or GUI handoff.
- Both clips show `SWEET Sandbox: ... op ...` callbacks for `containermanager`,
  `distnoted`, and `cfprefsd`. The sandbox syscall hook is active in these
  boots. The explicit policy-registration result is not visible.
- IMG_0777 shows launchd starting SpringBoard, then `driverkitd` terminated
  with SIGKILL and `logd privilege 1002 denied`. IMG_0778 shows backboardd
  terminating with SIGABRT (Mach exception namespace 2/code 6), followed by
  `IOMFB_FDR_Loader` SIGABRT. The full patch-0128 exit summary, build ID, and a
  readable SpringBoard CADisplay result are not visible.
- The sandbox-omission hypothesis is no longer sufficient: sandbox syscall
  callbacks are visibly running. Privilege denial is a separate MAC check;
  current code grants only `PRIV_WORK_INTERVAL` and returns `EPERM` for other
  privileges. Investigate the exact process/privilege denials and the FDR
  loader/backboardd stacks before changing grants or display behavior.
- The phone was detected in Fastboot on slot B. `fastboot reboot recovery`
  returned OKAY, but neither ADB nor Fastboot enumerated afterward. No new
  recovery log read or partition write occurred in this turn. Preserve the
  entitlement-repaired root and the already-flashed sandbox wrapper.

### Recovery crash reports identify the framebuffer property type bug — 2026-10-26

- After the user clarified recovery ADB is available only from slot A, selected
  A and rebooted to recovery. ADB authorization was approved; recovery ADB is
  root. `/sys/fs/pstore` and `/proc/last_kmsg` are empty. The userdata
  partition was captured read-only to the host; all HFS repair work below was
  on an APFS copy-on-write clone, never on the phone.
- The captured HFSX root contains `IOMFB_FDR_Loader` crash reports at 60 and
  82 seconds uptime and repeated `backboardd` reports. There is no
  `SpringBoard*.ips` in the captured CrashReporter directories. The latest
  backboardd report is at 640 seconds uptime, crash count 50.
- `IOMFB_FDR_Loader` throws an Objective-C exception in
  `getEDTProperty+104`, called by `IOMobileFramebufferOpen+160` while opening
  the display. Disassembly shows `getEDTProperty` looks up `canvas-width` and
  `canvas-height`, then calls `CFDataGetLength` on the returned property.
  `SweetFramebuffer.cpp` published those values with the numeric
  `setProperty(key, uint64, 32)` overload, which creates `OSNumber`, not
  `OSData`/`CFData`. This type mismatch explains the `doesNotRecognizeSelector`
  exception. The backboardd report independently shows the resulting abort in
  `IOMobileFramebufferCreateDisplayList+252`, under
  `CA::WindowServer::display_count_of_type` and
  `-[CAWindowServer _detectDisplays]`. This is the direct display-enumeration
  failure; the sandbox-omission theory is superseded for this crash.
- Corrected patch 0125 to publish each 32-bit geometry value through
  `IORegistryEntry::setProperty(key, bytes, length)`, which wraps it as
  `OSData`, the type expected by IOMFB. The patch applies with zero fuzz after
  0123 and 0124. `tools/xnu-cc.py` compiled the changed
  `SweetFramebuffer.cpp` against CI 40329697379's build tree with 0/1 failures.
- CI 40355196690 stopped before compile because downstream patch 0126 still
  matched the pre-fix numeric canvas setters. Commit `a1d2cbc` updates its
  context, and follow-up CI 40356435384 confirmed the full patch stack/build.

### Framebuffer CFData fix — green CI and boot_b flash — 2026-10-26

- Commit `fb2cda0` changes patch 0125 to publish `canvas-width` and
  `canvas-height` as OSData bytes. Commit `a1d2cbc` updates patch 0126's
  downstream context so the ordered patch stack applies.
- Strict CI run [40356435384](https://github.com/59c84486t9-alt/ios-veux/actions/runs/40356435384)
  succeeded. Repository preflight, XNU build, synthetic host bounds checks,
  feature manifest, build-tree packaging and artifact uploads passed. Patches
  0123–0128 are all marked APPLIED. Kernel SHA-256:
  `f929f22561d6bb618456eaaa3b4785cf8e6459a8226d511adc38e589c124e419`.
- Built wrapper
  `shim/out/veux-xnu-40356435384-sandbox-iokit-trace/shim-boot-veux-xnu-40356435384-sandbox-iokit-trace.img`
  from that exact CI kernel and patch-status artifact, using the verified
  phone DTB and embedded ADT plus `veuxsandbox=1` and
  `veuxiolog=backboardd,SpringBoard`. `verify-veux-wrapper.py` passed payload
  reconstruction, build/run ID, boot-argument and DTB checks. Wrapper
  SHA-256: `392420bf8340a7033b2f090ca192bb44fe4b8a5fb376a8f4a8f7cfc6b0e7cd0125`.
- Fastboot confirmed serial `4078cac030c8`, product `veux`, unlocked state,
  slot A active, and a 128 MiB `boot_b`. Only `boot_b` was flashed; send/write
  both returned OKAY. Selected B and rebooted. No userdata or root image was
  changed; the entitlement-repaired root remains preserved.
- After reboot, neither ADB nor Fastboot enumerated at the immediate check.
  This confirms the flash/reboot command sequence, not runtime GUI success.
  Next: capture the display/serial boot and verify build ID 40356435384,
  `canvas-width`/`canvas-height` setup, IOMFB client ready/selector/present
  markers, and SpringBoard/backboardd outcome.

### Backboardd display-list `device_type` correction — 2026-10-26

- The user's 17:53 clip is an earlier segment of the same boot as the 17:51
  clip: it shows launchd, SpringBoard, and xpcproxy activity before the later
  display setup/failure. In the later frame, AppleCLCD is registered and
  MobileGestaltHelper is the only visible ready client; swaps/presents remain
  zero. Treat these as one continuous boot trace, not separate runs.
- Recovery's latest backboardd crash report (uptime 640, crash count 50)
  terminates with an Objective-C exception in
  `__IOMobileFramebufferCreateDisplayList_block_invoke+316`. The caller chain
  is `IOMobileFramebufferCreateDisplayList+252` ->
  `CA::WindowServer::display_count_of_type` ->
  `-[CAWindowServer _detectDisplays]`. Disassembly reads each `/arm-io` child's
  `device_type` using `CFDataGetLength`/`CFDataGetBytes`. The earlier claim
  that patch 0125's three-argument setter produced OSString was incorrect: that
  call uses XNU's `void *` byte-data overload. Commit `1f46527` changed the
  original two-argument string setter to this three-argument form and therefore
  did publish OSData. The crash report has no build ID, so it may be persisted
  from an earlier boot. The later explicit cast in `bed5c50` is redundant.
- The framebuffer rectangle clipping in 0123 uses 64-bit intermediates and
  checks source byte extents before copying; no further signed-overflow defect
  was apparent in that audit. The follow-up patch 0129 normalizes every direct
  `/arm-io` child before display-nub publication in case another child has a
  non-Data `device_type`; details and runtime caveats are in the latest section
  below. Preserve the entitlement-repaired root.

### Device-type correction — green CI, verified wrapper, and boot_b flash — 2026-10-26

- Commit `1f46527d7c86d956da5c2ee27fc379f8ee099e72` was pushed. Local
  `SweetFramebuffer.cpp` compile against the previous successful CI build tree
  passed (0/1 failures); repo validation and `git diff --check` passed.
- CI [40369369423](https://github.com/59c84486t9-alt/ios-veux/actions/runs/40369369423)
  completed successfully. XNU compile, host framebuffer bounds tests, feature
  manifest and artifact uploads passed; patches 0123–0128 are APPLIED. Kernel
  SHA-256: `09be0aeefe7d435a5895f7cf886cfc795fe216e91633caf7ab86afc014dea663`.
- Built payload from that CI kernel and the ADT in the prior verified wrapper.
  Reused its verified shim/header/phone DTB, adding `veuxsandbox=1` and
  `veuxiolog=backboardd,SpringBoard`. Independent verification passed for the
  CI build ID, exact payload reconstruction, DTB, boot args and patch status.
  Wrapper:
  `shim/out/veux-xnu-40369369423-sandbox-iokit-trace/shim-boot-veux-xnu-40369369423-sandbox-iokit-trace.img`
  SHA-256: `2a7badfbd2139f9ff472754f33f48d138b7ca42da84f8304e437afa92652d628`.
- Fastboot confirmed device `4078cac030c8`, product `veux`, unlocked, slot A
  active, `boot_b` size `0x8000000`. Wrote only `boot_b` (send/write OKAY),
  selected slot B (OKAY), and rebooted (OKAY). The entitlement-repaired root
  remains untouched. At 15 and 45 seconds neither ADB nor Fastboot enumerated;
  there is no current screen evidence. This confirms build and flash, not GUI
  success. Request a current screen/video capture to verify build ID 40369369423,
  display-list enumeration, client selectors/present, and SpringBoard handoff.
- Removed temporary userdata raw/clone captures, analysis mount, dyld symbol
  cache, downloaded buildtree and compile logs after analysis. The verified
  wrapper and adjacent manifest are retained; no entitlement-repaired root or
  user-provided media was removed.

### IOMFB display-list property normalization follow-up — 2026-10-26

- The recovery-captured backboardd report has `imageOffset=31420` in
  `IOMobileFramebuffer`, mapping to the instruction immediately after
  `CFDataGetBytes` in the iOS 16.7.16 display-list block. It has no unique build
  ID, so it cannot be attributed conclusively to CI 40369369423 or prove which
  `/arm-io` child supplied the unexpected object.
- Correction to the earlier diagnosis: XNU's two-argument string setter creates
  OSString; the three-argument `setProperty(key, char *, length)` call in patch
  0125 resolves to the `void *` byte-data setter and already creates OSData.
  Commit `bed5c50`'s explicit mutable `void *` cast is behaviorally redundant.
  The overload implementations are in
  [IORegistryEntry.cpp](https://github.com/apple-oss-distributions/xnu/blob/main/iokit/Kernel/IORegistryEntry.cpp).
- Patch 0129 normalizes `device_type` on every direct `/arm-io` child in the
  DeviceTree plane before creating the display nub: `disp0` gets canonical
  `display-subsystem` OSData; strings become OSData; missing or unsupported
  values become empty OSData. It logs each child type/length. This addresses
  the unchecked framework byte reads if any sibling has a non-Data value, but
  remains a hypothesis pending runtime enumeration evidence.
- Local compile against build tree 40369369423 passed (0/1 failures), and
  patch application reproduced the compiled source byte-for-byte. Repository
  validation checks 128 patches and passes. CI 40380782893, dispatched for the
  redundant cast, was canceled. The new 0129 CI has not started; no new wrapper
  has been assembled and no phone partition has been written.
- Phone remains connected to root recovery ADB with slot `_a`; no partition was
  written. The large host-only raw/COW captures were detached and deleted. The
  entitlement-fixed userdata image remains untouched.

### 0129 runtime capture and recovery handoff — 2026-10-26

- The latest strict CI is **40384236283** on commit `adfb75d`; it passed the
  XNU build, synthetic framebuffer bounds check, feature manifest and artifact
  packaging. Patch 0129 is applied. The locally assembled, verified wrapper is
  `shim/out/veux-xnu-40384236283-iomfb-type-normalization/shim-boot-veux-xnu-40384236283-iomfb-type-normalization.img`
  (SHA-256 `7024eba36ca05c9c17cee70bb342b1890b40d64eeffc5751da64e3445e711d76`).
  Its manifest proves payload reconstruction from the CI kernel, phone-DTB
  match and boot arguments. Those arguments include `rootrw=1 ufsrw=1` for the
  already-authorized writable-root experiment; no userdata write was made in
  this handoff.
- Reviewed the user's 90.69-second Drive clip and `IMG_0787 (1).HEIC`. The
  clip shows the XNU diagnostic display, repeated backboardd IOKit matching
  queries for `IOAcceleratorES` returning `0 found`, then the Apple logo by
  about 80 seconds. Those zero-result queries concern the accelerator class;
  they do not prove that IOMFB display-list enumeration failed. The clip does
  not show a GUI handoff, a panic/reset reason, or a ten-minute wait. The still
  shows the Apple logo only; no separate asterisk is visible in it.
- Read-only Fastboot checks found product `veux`, unlocked `yes`, slot B active,
  and a 128 MiB `boot_b`. ADB was absent. `fastboot fetch boot_b` is unsupported,
  so the currently installed boot image cannot be matched to the 403842 wrapper
  from this host. Following the previously authorized recovery path, selected
  slot A and rebooted to recovery; no partition or userdata was written.
- Recovery ADB enumerates serial `4078cac030c8` as `unauthorized`, even with
  the existing host key explicitly loaded. No recovery files/logs have been
  read yet. Next: the user must accept the USB debugging authorization on the
  phone; then inspect pstore/last-kmsg and the latest boot's logs read-only
  before choosing another kernel or display change.
