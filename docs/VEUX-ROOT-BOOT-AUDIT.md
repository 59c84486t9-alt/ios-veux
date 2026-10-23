# VEUX root and post-root boot audit

Audit basis: XNU 8796 as staged through 0111, the current 0111 source candidate, `tools/mkadt.py`, `tools/mkpayload.py`, `tools/mkiosroot.sh`, and the phone history in `NOTES.md`. The grep found 124 SWEET-related preprocessor lines and 190 SWEET string literals across `bsd/`, `iokit/`, `osfmk/`, `pexpert/`, `libkern/`, and `config/`. The classifications below cover behavior-bearing hits; remaining SWEET device strings belong to SWEET-only drivers and selectors.

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

The image was built from iPhone X iOS 16.7.1 / build 20H392 OS and cryptex contents. `/sbin/launchd` is an arm64 Mach-O; the previous successful phone run reached launchd and later iOS GUI startup, so architecture and shared-cache placement were already validated on device. The image creation/flash history is in `NOTES.md` entries for 0029 and v15. No full userdata partition image backup exists in this checkout; the separate saved userdata-tail image protects only 4 MiB plus a header. The Android userdata contents were explicitly declared expendable earlier, and userdata has already been replaced with the iOS root image. There is no claim of a full backup.

If the userdata image is missing or damaged, `IOFindBSDRoot` can still return the UFS device, but `vfs_mountroot` will fail HFS probing and `bsd_init` logs `cannot mount root` and retries. If mount succeeds, the next stages are `bsd_utaskbootstrap`, `load_init_program`/`execve("/sbin/launchd")`, then launchd's dyld startup and shared-cache lookup. Missing launchd or cache files fail after root mount and are distinct from UFS discovery.

## VEUX UFS helper and read failure behavior

The helper maps the `/veux-ufs` ADT register range, but does not cold-initialize the controller or UIC link. It reuses ABL's already-enabled UFSHCI host/link state, verifies that the host is ready and no request is outstanding, disables UFS interrupts, replaces the transfer-request-list base with a kernel-owned DMA allocation, and verifies the new base before issuing commands. It creates one command slot (UTRL entry 0), one command descriptor/response UPIU with PRDT entries, and a 1 MiB physically contiguous bounce buffer. Commands are polled one at a time; it does not set up an interrupt-driven queue.

It sends TEST UNIT READY up to three times, reads GPT LBA 1 and the GPT entries, then finds the partition named `userdata` (overridable with `ufsroot=`). Reads use SCSI READ(10) on **LUN 0**, in 4 KiB device blocks, with 512-byte BSD logical sectors. The known userdata partition starts at 4 KiB LBA `0x2b8c00` (byte offset `0x2b8c00000` from LUN 0); HFS offsets are relative to that partition start. `ufscache=1` enables cache maintenance optimized for the host, while `ufswait=1` permits bounded sleeps during commands; the current boot args set neither.

Phone evidence already goes beyond the shim log writer: XNU located the GPT userdata partition, read the HFS volume, mounted HFS from UFS, and previously executed launchd. The shim's userdata log writer independently establishes that some shim-side UFS commands work, but does not by itself validate this XNU driver's reads.

Each UFS command has a 5-second deadline. If its doorbell remains set, the driver clears the request and returns `ETIMEDOUT` (`0x3c`); nonzero OCS or failed response status returns `EIO` (`0x5`); invalid arguments/ranges return `EINVAL` (`0x16`). During initial GPT discovery, an error bubbles to `sweet_ufs_rootdev()` and `IOFindBSDRoot` panics because the selected root device is unavailable. After the disk is registered, a read error completes the BSD buffer with that errno; HFS mount receives the I/O failure, `vfs_mountroot` returns an error, and `bsd_init` logs the failure and retries its mount loop. The read itself does not retry, panic, or hang beyond the command's bounded timeout (the initial TUR has three attempts). Patch 0111 adds a first-success cell and a first-read-failure cell; the failure line includes the errno in hex.

## Root write and journal policy

The generic root mount begins `MNT_RDONLY`. The current boot args omit both `rootrw=1` and `ufsrw=1`. VEUX keeps this safe default. To opt in to a writable root in a future image, include both `rootrw=1` (mount HFS read-write) and `ufsrw=1` (permit bounded in-partition UFS writes); neither is present in the current candidate. The persistent logger remains a separate, explicit `veuxlog=1` write limited to its reserved tail window.

XNU's normal journaled-HFS mount calls `journal_open()`, which replays pending transactions and can write both journal and filesystem blocks, even if the mount began read-only for a root volume. A dirty non-journaled read-write root is accepted by the earlier SWEET exception without running fsck; the filesystem can therefore remain inconsistent. Patch 0111 changes the VEUX read-only root path to set `jnl_disable` before early journal setup and skips HFS's legacy late-journal initializer. The first read-only mount neither replays nor initializes the journal. It inspects the filesystem without recovery; if on-disk metadata cannot be read safely, HFS mount may fail and the root-mount retry path remains the signal. `rootrw=1 ufsrw=1` explicitly restores XNU's normal writable journal behavior, including replay, and should only be used after choosing a recoverable image.

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

The labels intentionally distinguish a return from success: cell 12 means control returned from the init loader; cell 15 means `execve` returned an error. A successful exec may not reach either return marker.

### 2026-10-23 boot result (CI 39942134414)

The photographed boot lit UFS cell 16 (first READ(10) succeeded), and BSD cells 6-9 (mountroot callback entry/return and `vfs_mountroot` entry/return). It did not light the later `bsd_utaskbootstrap` or launchd cells. The panic dump gives ESR `0x96000005`, FAR `0x20`, PC `0xfffffe000798bc40`, and LR `0xfffffe00077b8294`. Using the CI kernel at its linked `__TEXT` base `0xfffffe0007004000`, these resolve to `MD5Init+0x34` and `hfs_getvoluuid+0x64`. The faulting instruction is `ldr x20, [x22, #0x20]`; the preceding load reads `_g_crypto_funcs` at `0xfffffe00072490d0`, which was NULL. Thus this boot reached HFS UUID discovery and exposed the missed MD5 fallback gate; it does not indicate a bad UFS block read or prove the filesystem image is corrupt.

Patch 0112 extends the already staged BearSSL MD5 implementation only to `ARM64_BOARD_CONFIG_VEUX`, including its little-endian codec units. The pmap, HFS read-only/journal, and UFS policies stay unchanged. CI must verify that the new candidate compiles and the VEUX MD5 source gates are active before the next flash. The screen's “handshake structure not initialized” line refers to the separate hardware-debugger handshake diagnostic; the faulting PC/LR identify the actionable kernel abort path.

The UFS read markers use the two 32x32 cells at y=2208: index 16 (green) means the first successful READ(10), and index 17 (red) means the first failed read. The failure also prints `error=0x...`, LBA, and block count in the top console. The stage strip at y=2240 remains separate.

## Panic text region

The normal console ends at y=800. The wait-page renderer is capped at y=1815 (four threads per page); other diagnostic hex rows end above y=1780. Panic text is drawn in its own y=1816..2071 region, before the cell strip at y=2080 and fault bit rows at y=2120+. It uses the already initialized framebuffer font, prints the full formatted panic string, `panic_caller`, and up to eight bounded frame-chain return addresses in hex. It does not call the scrolling console; the original first-fault dump and early alias are retained.
