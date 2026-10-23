# VEUX root and post-root boot audit

Audit basis: XNU 8796 as staged through 0112, the 0112 source candidate, `tools/mkadt.py`, `tools/mkpayload.py`, `tools/mkiosroot.sh`, and the phone history in `NOTES.md`. The grep found 124 SWEET-related preprocessor lines and 190 SWEET string literals across `bsd/`, `iokit/`, `osfmk/`, `pexpert/`, `libkern/`, and `config/`. The classifications below cover behavior-bearing hits; remaining SWEET device strings belong to SWEET-only drivers and selectors.

## SWEET-only behavior review

The table lists the behavior-bearing SWEET conditions in the boot/root path. Line numbers refer to the assembled source after 0111; diagnostic and device-only SWEET strings are not platform gates.

| File:line | SWEET condition/behavior | VEUX decision | Reason |
|---|---|---|---|
| `iokit/Kernel/IOService.cpp:5129,5140,5191` | Missing `IOBlockStorageDriver`/`IOMedia` classes are tolerated on SWEET | Apply the same narrow behavior under `ARM64_BOARD_CONFIG_VEUX` in 0021/0022 | The VEUX root is a BSD UFS disk and does not instantiate IOStorageFamily classes; no blanket matching bypass. |
| `iokit/bsddev/IOKitBSDInit.cpp:769-785` | `rd=ufsroot0` selects SWEET UFS helper | Shared with VEUX | The helper reads `/veux-ufs` from the VEUX ADT and locates `userdata` on LUN 0. |
| `bsd/dev/sweet_ufs.c:21,282-296,690-704` | Compile helper and optional `ufsrw`/SWEET peripherals | Compile for VEUX; first read/failure cells; `ufsrw=1` is opt-in | Reuse ABL's host state, bounded READ(10), and keep the root read-only by default. SWEET-only buttons/touch/sample/USB calls remain SWEET-only. |
| `bsd/kern/bsd_init.c:697,949` | Tolerate an unsealed root for SWEET | Share with VEUX | The development kernel has no Image4-sealed root; fail-fast root authentication would prevent the known UFS root from continuing. |
| `bsd/vfs/vfs_subr.c:1272-1281` | `rootrw=1` clears the default root `MNT_RDONLY` | Share with VEUX, off by default | First boot must stay read-only; `rootrw=1` is the explicit mount-mode opt-in. Actual UFS writes also require `ufsrw=1`. |
| `bsd/sweet_hfs/core/hfs_vfsutils.c:203-220` | Permit SWEET's dirty, non-journaled root when mounted read-write | Share the root exception, but only after 0111's VEUX read-only policy | A read-only first mount does not enter this read-write exception. A read-write dirty, non-journaled root is accepted without fsck and is not a safe first-boot mode. |
| `bsd/sweet_hfs/core/hfs_vfsops.c:1419,1571-1593`; `bsd/sweet_hfs/core/hfs_vfsutils.c:734-739` | Open/replay HFS journal during root mount | VEUX read-only root skips early and late journal init/replay; rw opt-in uses normal XNU journal path | `journal_open()` replays pending journal transactions and may write the volume. The read-only VEUX path sets `jnl_disable` and also skips the legacy late-journal initializer. |
| `bsd/vfs/vfs_subr.c:1215-1291`; `bsd/kern/bsd_init.c:1201` | Generic `mountroot`, `vfs_mountroot`, and `bsd_utaskbootstrap` | Keep common code and add VEUX stage cells | These functions are not SWEET-only; the new markers localize mount and bootstrap progress. |
| `bsd/kern/bsd_init.c:1097-1122`; `bsd/kern/kern_exec.c:6836-6840` | Common init loader / exec path | Keep common code; VEUX marks launchd exec entry and error return | A successful exec does not return; entry and returned-error cells distinguish it. |
| `config/MASTER.arm64.veux` and `bsd/vfs/vfs_conf.c:198-224` | SWEET HFS and mockfs registration | Existing VEUX config already enables both | Mockfs is available but not used by this `rd=ufsroot0` payload. |
| `bsd/kern/kern_mib.c`, `bsd/kern/syscalls.master` | iOS machine identity and `pid_hibernate` accommodations | Share the required iOS-userland behavior with VEUX | The target is iOS 16 userland; unrelated SWEET-specific interfaces remain gated. |
| `osfmk/prng/entropy.c:40,97,482` | Use SWEET's built-in SHA-256 implementation | Share with VEUX | VEUX needs early entropy without waiting for an absent crypto kext. |
| `iokit/Kernel/KernelConfigTables.cpp` and SWEET device drivers | Board matching and optional SWEET display/HID/SoC devices | Keep VEUX's platform and Kryo matches; leave Sweet-specific drivers gated | VEUX has its own platform expert and hardware. No global kext/IOKit skip is needed. |
| `libkern/crypto/corecrypto_md5.c:20`; `sweet_md5.c`, `sweet_dec32le.c`, `sweet_enc32le.c` | Use BearSSL MD5 when the corecrypto function table is absent | Share the portable provider with VEUX under `ARM64_BOARD_CONFIG_VEUX` | The phone's panic PC resolved to `MD5Init+0x34`; `_g_crypto_funcs` was NULL and the following load faulted at FAR `0x20` during HFS UUID discovery. |
| `osfmk` CPU/MMU/GIC/timer/serial/FIQ gates | SM7150-specific early hardware behavior | Keep VEUX's independent branches | SM6375 addresses and CPU identifiers differ; reusing SWEET constants would be unsafe. |

The patch series therefore changes the no-storage-class behavior specifically under `ARM64_BOARD_CONFIG_VEUX`, plus the adjacent root-auth, dirty/read-write-root, iOS syscall/identity, entropy and diagnostic policies justified above. It does not disable IOKit matching globally.

## ADT, INITRD, and root filesystem

`tools/mkadt.py --veux --highmem` creates `/chosen/memory-map` with only its name and phandle. It has no `RAMDisk` property. The SWEET ADT from the same generator has the same empty memory-map; it also has no `/chosen/boot-args` or `rd=` property. Boot arguments live in the `SWEETXNU` payload header instead. For this VEUX artifact they are:

```
debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam -noprogress rd=ufsroot0 veuxlog=1 veuxfb=1 veuxfbconsole=1
```

The Android boot-v2 header labels a 16,518,272-byte segment as its ramdisk and gives its load address as `0x01000000`. The shim does not use that header address as a fixed pointer: it reads the live ABL DTB's `/chosen/linux,initrd-start` and `linux,initrd-end`, prints those runtime `INITRD lo=` and `hi=` values, and searches that range for the `SWEETXNU` payload. The exact runtime lo/hi are therefore boot-specific; they are not constants in the image or ADT.

The segment begins with `SWEETXNU` (verified in the packaged artifact), and is the kernel payload, not a root filesystem. It contains no `/sbin/launchd`, and is neither an HFS+ volume nor a mockfs image. `mkpayload.py --ramdisk IMAGE` is the separate path that appends an image as a kernel segment and adds the ADT RAMDisk property for `rd=md0`.

The root choice is `rd=ufsroot0`, so `IOFindBSDRoot` selects `userdata` on the VEUX UFS disk. The last documented phone state is iOS root image v15 on userdata, a 16 GiB case-sensitive HFSX volume (the case-sensitive HFS+ variant); it was written from a sparse image with `fastboot -S 512M flash userdata ...simg`. Earlier phone logs show HFS mounted from UFS and Apple's `/sbin/launchd` executed, so this storage path and userland have been exercised on this phone. That is historical evidence, not a fresh readback of userdata during the 0110 build. The current 0110 boot-image test did not write userdata.

The image was built from iPhone X iOS 16.7.1 / build 20H392 OS and cryptex contents. `/sbin/launchd` is an arm64 Mach-O; the previous successful phone run reached launchd and later iOS GUI startup, so architecture and shared-cache placement were already validated on device. The image creation/flash history is in `NOTES.md` entries for 0029 and v15. The pre-flash userdata copy is present at `/Volumes/savedrive/veux_userdata.img`; its length is 109,156,577,280 bytes (213,196,440 512-byte sectors), matching the saved Android sysfs partition size. The user confirms the iOS sparse image can be reflashed if needed, so preserving the old data is not a constraint on the boot experiment.

If the userdata image is missing or damaged, `IOFindBSDRoot` can still return the UFS device, but `vfs_mountroot` will fail HFS probing and `bsd_init` logs `cannot mount root` and retries. If mount succeeds, the next stages are `bsd_utaskbootstrap`, `load_init_program`/`execve("/sbin/launchd")`, then launchd's dyld startup and shared-cache lookup. Missing launchd or cache files fail after root mount and are distinct from UFS discovery.

## VEUX UFS helper and read failure behavior

The helper maps the `/veux-ufs` ADT register range, but does not cold-initialize the controller or UIC link. It reuses ABL's already-enabled UFSHCI host/link state, verifies that the host is ready and no request is outstanding, disables UFS interrupts, replaces the transfer-request-list base with a kernel-owned DMA allocation, and verifies the new base before issuing commands. It creates one command slot (UTRL entry 0), one command descriptor/response UPIU with PRDT entries, and a 1 MiB physically contiguous bounce buffer. Commands are polled one at a time; it does not set up an interrupt-driven queue.

It sends TEST UNIT READY up to three times, reads GPT LBA 1 and the GPT entries, then finds the partition named `userdata` (overridable with `ufsroot=`). Reads use SCSI READ(10) on **LUN 0**, in 4 KiB device blocks, with 512-byte BSD logical sectors. The known userdata partition starts at 4 KiB LBA `0x2b8c00` (byte offset `0x2b8c00000` from LUN 0); HFS offsets are relative to that partition start. `ufscache=1` enables cache maintenance optimized for the host, while `ufswait=1` permits bounded sleeps during commands; the current boot args set neither.

Phone evidence already goes beyond the shim log writer: XNU located the GPT userdata partition, read the HFS volume, mounted HFS from UFS, and previously executed launchd. The shim's userdata log writer independently establishes that some shim-side UFS commands work, but does not by itself validate this XNU driver's reads.

Each UFS command has a 5-second deadline. If its doorbell remains set, the driver clears the request and returns `ETIMEDOUT` (`0x3c`); nonzero OCS or failed response status returns `EIO` (`0x5`); invalid arguments/ranges return `EINVAL` (`0x16`). During initial GPT discovery, an error bubbles to `sweet_ufs_rootdev()` and `IOFindBSDRoot` panics because the selected root device is unavailable. After the disk is registered, a read error completes the BSD buffer with that errno; HFS mount receives the I/O failure, `vfs_mountroot` returns an error, and `bsd_init` logs the failure and retries its mount loop. The read itself does not retry, panic, or hang beyond the command's bounded timeout (the initial TUR has three attempts). Patch 0111 adds a first-success cell and a first-read-failure cell; the failure line includes the errno in hex.

## Root write and journal policy

The generic root mount begins `MNT_RDONLY`. The current boot args omit both `rootrw=1` and `ufsrw=1`. VEUX keeps this safe default. To opt in to a writable root in a future image, include both `rootrw=1` (mount HFS read-write) and `ufsrw=1` (permit bounded in-partition UFS writes); neither is present in the current candidate. The persistent logger remains a separate, explicit `veuxlog=1` write limited to its reserved tail window.

XNU's normal journaled-HFS mount calls `journal_open()`, which replays pending transactions and can write both journal and filesystem blocks, even if the mount began read-only for a root volume. A dirty non-journaled read-write root is accepted by the earlier SWEET exception without running fsck; the filesystem can therefore remain inconsistent. Patch 0111 changes the VEUX read-only root path to set `jnl_disable` before early journal setup and skips HFS's legacy late-journal initializer. The first read-only mount neither replays nor initializes the journal. It inspects the filesystem without recovery; if on-disk metadata cannot be read safely, HFS mount may fail and the root-mount retry path remains the signal. `rootrw=1 ufsrw=1` explicitly restores XNU's normal writable journal behavior, including replay, and should only be used after choosing a recoverable image.

### Userdata tail logger versus the HFSX volume

The root artifact `/Users/vivien/Downloads/ios16-root-20H392.simg` is Android sparse; its logical raw size is 17,179,869,184 bytes = 33,554,432 512-byte sectors = 4,194,304 4 KiB blocks. The HFSX volume header agrees: `blockSize=4096`, `totalBlocks=4,194,304`, so the HFS+ volume itself also occupies 17,179,869,184 bytes. The SHA-256 of the expanded raw image is `7ed18fac9b9ecdab38ca3c3adc8a6abac3086e41235ba91d2d82788587bb760d`.

The pre-flash partition copy is 213,196,440 512-byte sectors, or 26,649,555 4 KiB blocks. With the recovery sysfs start of 23,961,920 512-byte sectors (4 KiB LBA `0x2db428`), the tail logger's partition-relative 1025-block reservation is relative 4 KiB LBA `0x1969fd2..0x196a3d2`; its partition-relative 512-byte sectors are `0xcb4fe90..0xcb51e97`. If that saved GPT geometry is unchanged, its absolute UFS 4 KiB LBA is `0x1c453fa..0x1c457fa` (512-byte LUN sectors `0xe229fd0..0xe22bfd7`). There is a mismatch to resolve: an older XNU console line reports `first block 0x2b8c00, 109643 MiB`, which conflicts with the pre-flash Android sysfs start/size above. The logger derives its base from its parsed GPT entry (`su.first_block + su.nblocks`), so the exact absolute ring LBA on the currently flashed phone is not established without a fresh GPT readback. Its intended and bounded location is the final 4,198,400 bytes of userdata.

The alternate header starts at volume-relative byte `0x3fffffc00`, 512-byte sector `0x1fffffe`; it occupies the 512-byte HFS+ volume-header structure there, 512 bytes before the volume end. The HFSX allocation file is only `0x80000` bytes with extent `(start=1, count=128)`, ending at relative block `0x80`. Even using the smaller verified pre-flash userdata size, the 16 GiB volume leaves about 85.6 GiB after its end, so the intended tail ring is in userdata slack and cannot overlap the volume's last blocks, alternate header, or allocation-file tail. Verdict: **ring in slack (OK)**. The earlier `109643 MiB` XNU size/start discrepancy affects the absolute ring address, not the fact that a 4 MiB tail reservation lies outside a 16 GiB volume in a ~104 GiB partition. A recovery readback of the first 16 GiB of current userdata was not captured in this session; the expected expanded-image SHA above is available for that comparison when the phone returns to recovery.

### UFS write path and crash exposure

The staged UFS implementation reuses ABL's controller state and serializes one polled UTRL slot under the driver mutex; it does not create an interrupt-driven queue. With `ufsrw=1`, `sweet_ufs_strategy` permits B_WRITE and `ufs_write_blocks` issues SCSI WRITE(10) with a data-out UPIU, after validating every range against the userdata partition. Partial 4 KiB blocks use read/merge/write. `DKIOCSYNCHRONIZE`/`DKIOCSYNCHRONIZECACHE` issues SYNCHRONIZE CACHE(10) for the LUN. WRITE(10) does not set its FUA bit, so durability depends on the explicit sync path and device behavior. The software's writable flag is controlled by the boot arg; this code does not independently query a hardware write-protect switch. Commands remain serialized and polled.

There is no phone evidence that this VEUX ordinary filesystem write path has completed a write. Earlier logger-tail readback was byte-identical to the saved pre-logger tail, so it also did not demonstrate a successful persistent logger write. The new diagnostic candidate marks the first successful WRITE(10) green and the first failed WRITE(10) red, with errno in hex. A five-second command timeout returns `ETIMEDOUT` (`0x3c`); bad OCS/response returns `EIO` (`0x5`); invalid range/disabled write returns `EPERM` (`0x1`). The request error is returned to the buffer caller (not silently dropped); logger errors are printed and stop the logger thread. The source does not deliberately panic or wait forever on a completed error path.

The saved HFSX image is journaled: its volume-header attributes are `0x80002100` and journal-info block 129 has flags `0x5` (`in filesystem` plus `needs initialization`). This source image's journal is marked for initialization, so it does not prove there is an existing pending transaction to replay. With `rootrw=1`, normal XNU journal setup is re-enabled: it initializes a journal that needs initialization, or replays any pending transactions in an already initialized journal. Replay writes journaled metadata to the journal and home locations, then advances/clears journal state. The full pre-flash userdata copy is at `/Volumes/savedrive/veux_userdata.img`; its old Android contents are not needed to recover this boot because the iOS sparse image can be reflashed. The 4 MiB logger-tail snapshot is separate.

A power cut during a write can leave the current metadata operation incomplete. A correctly functioning HFS+ journal is designed to recover metadata transactions on the next writable mount, but it does not make arbitrary file contents or non-journaled data writes atomic, and a damaged/uninitialized journal can prevent a safe mount. The default candidate stays root read-only; `rootrw=1` opts into a writable HFS mount, and `ufsrw=1` separately enables UFS writes. The candidate reports both selected settings and the mount errno. Its `veuxlog=1` option is a distinct bounded write exception to the final 4 MiB+header window; disable that boot arg for a strictly no-write debugging boot.

## New display markers

The BSD diagnostic strip is at y=2080, cells 32x32 with 64-pixel horizontal spacing. Existing cells 0-5 retain their meaning. Cells 6-15 are:

| Cell | Event |
|---:|---|
| 6 | filesystem/selected `mountroot` callback entry |
| 7 | filesystem/selected callback returned |
| 8 | `vfs_mountroot` entry |
| 9 | `vfs_mountroot` returned to `bsd_init` |
| 10 | `bsd_utaskbootstrap` returned |
| 11 | init/launchd bootstrap task entry |
| 12 | `load_init_program` returned |
| 13 | `vfs_mountroot` succeeded and root device is mounted |
| 14 | launchd `execve` entry |
| 15 | launchd `execve` returned an error |
| 18 | process named `mount` enters exec |
| 19 | process named `mount` exits; numeric exit status is printed |
| 20 | first successful UFS WRITE(10), including the bounded log writer |
| 21 | first failed UFS WRITE(10), errno printed in hex |

The labels intentionally distinguish a return from success: cell 12 means control returned from the init loader; cell 15 means `execve` returned an error. A successful exec may not reach either return marker.

### 2026-10-23 boot result (CI 39945294859)

The 0112 photos show HFS mounted and launchd exec reached. UFS cell 16 (first READ(10)) is green; adjacent red cell 17 (first read failure) is dark, and no UFS read error is visible. The far-right red cell 15 in the upper BSD strip means `execve("/sbin/launchd")` returned an error. Panic text: `unexpected SIGKILL of launchd (CS_KILLED) with reason -- namespace 9 code 0xe`. Caller `0xfffffe0007af1af8` resolves against the CI kernel to `psignal_internal.cold.3`, matching `OS_REASON_EXEC / EXEC_EXIT_REASON_WRONG_PLATFORM`; this is not a storage or HFS panic.

The kernel remains macOS-target XNU (`XNU_TARGET_OS_OSX`) with VEUX board configuration. In `mach_loader.c`, the iOS device platform is read from `LC_BUILD_VERSION` (or arm64 `LC_VERSION_MIN_IPHONEOS`); under the macOS target it calls `vm_map_mark_alien(map)` for `PLATFORM_IOS`. The actual exec rejection is in `kern_exec.c`: under `#if XNU_TARGET_OS_OSX`, when `proc_platform(p) == PLATFORM_IOS`, a missing/zero spawn platform requires the no-sandbox entitlement; in DEVELOPMENT/DEBUG, `unentitled_ios_sim_launch` satisfies that requirement. If a spawn platform is supplied, the branch requires `psa->psa_platform == PLATFORM_IOS`. `PLATFORM_IOSSIMULATOR` is distinct; this guard addresses device `PLATFORM_IOS`, not a simulator platform.

SWEET did not change XNU to `XNU_TARGET_OS_IOS`; its historical boot used the same macOS target plus `unentitled_ios_sim_launch=1`. SWEET and VEUX differ in `MACHINE_CONFIG`/board macros (`SWEET` versus `VEUX`), CPUs, platform drivers and ADT, while the XNU target OS remains macOS. The VEUX test image adds that boot-arg only. It bypasses the missing no-sandbox-entitlement exec rejection for device-iOS binaries; it does not add entitlements, remove the OSX `vm_map_mark_alien` classification, disable sandboxing, or solve dyld/cache/trust issues.

Other target-OS differences to expect after launchd starts:

| Area | OSX-target behavior relevant here | VEUX status / likely next signal |
|---|---|---|
| Loader and VM | iOS maps are marked alien; the OSX VM path disables the protected cache pager for alien maps. | Still active after the boot-arg. A dyld shared-cache/protected-page mapping failure remains possible. |
| AMFI, sandbox and entitlements | The exec boot-arg changes only the platform gate. MACF launch constraints and entitlement queries still run. | VEUX builds the SWEET-compatible AMFI/entitlement providers; watch for launch-constraint, codesign or sandbox denials. |
| Trust caches | Runtime Image4/AMFI trust-cache services are unavailable in this bring-up. | VEUX returns not-found/not-supported for unavailable runtime caches; its built-in AMFI marks root binaries for development. This is not a production trust chain. |
| dyld/shared cache | XNU retains the OSX shared-region implementation and alien-map rules; dyld is still the iOS userland binary and chooses cache/volume paths. | The iOS cache content exists on root, but the earlier SWEET launch reached libignition and failed looking for a separate Preboot volume. Watch for dyld cache open/map/slide errors. |
| Hibernation | OSX omits the embedded `pid_hibernate` syscall path by default. | Patch 0110 enables it for VEUX. The shared `config/MASTER` enables `CONFIG_FREEZE`, so the real freeze path is compiled; actual freeze behavior still depends on compressor/jetsam state and needs runtime validation. |
| Memory and task policy | OSX compile-time resource/accounting, VM/compressor, and task-policy defaults remain. Embedded iOS app-lifecycle policies differ. | Not comprehensively normalized. Watch memory-pressure kills and `task_policy`/`proc_policy` errors before changing target OS. |

The panic region, caller/eight-frame display, first-fault dump, stage cells, and early alias remain in the 0112 kernel. CI run `39945294859` succeeded on commit `7359133bbf46343c86fb82785155d62368ffd127`. A separate image with the boot-arg is locally repackaged from that CI kernel; its SHA-256 is in `NOTES.md`. No kernel source change was needed for this test.

The UFS read markers use the two 32x32 cells at y=2208: index 16 (green) means the first successful READ(10), and index 17 (red) means the first failed read. The failure also prints `error=0x...`, LBA, and block count in the top console. The stage strip at y=2240 remains separate.

## Panic text region

The normal console ends at y=800. The wait-page renderer is capped at y=1815 (four threads per page); other diagnostic hex rows end above y=1780. Panic text is drawn in its own y=1816..2071 region, before the cell strip at y=2080 and fault bit rows at y=2120+. It uses the already initialized framebuffer font, prints the full formatted panic string, `panic_caller`, and up to eight bounded frame-chain return addresses in hex. It does not call the scrolling console; the original first-fault dump and early alias are retained.
