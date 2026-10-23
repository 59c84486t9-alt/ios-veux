# VEUX root and post-root boot audit

Audit basis: the XNU 8796 source assembled through patch 0109, the 39929665498 VEUX artifact, `tools/mkadt.py`, `tools/mkpayload.py`, and `tools/mkiosroot.sh`. The grep found 124 SWEET-related preprocessor lines and 190 SWEET string literals across `bsd/`, `iokit/`, `osfmk/`, `pexpert/`, `libkern/`, and `config/`. The classifications below cover the behavior-bearing hits by source area. Shared UFS/HFS/root messages now identify both boards; remaining SWEET device log strings belong to SWEET-only drivers and selectors.

## SWEET-only behavior review

| Area | VEUX decision | Reason / change |
|---|---|---|
| `IOService::setRootMedia` (`iokit/Kernel/IOService.cpp`, patch 0021) | Same behavior, VEUX-gated | No IOStorageFamily means no `IOBlockStorageDriver` metaclass. Treat that as image/UFS root without asserting. Added `ARM64_BOARD_CONFIG_VEUX` alongside SWEET in patch 0021. |
| `publishHiddenMedia` (`iokit/Kernel/IOService.cpp`, patch 0022) | Same behavior, VEUX-gated | No `IOMedia` class exists to unhide; skip the class assertion and avoid dereferencing a null class. Added VEUX to patch 0022. |
| `IOFindBSDRoot` | Already shared | VEUX already recognizes `rd=ufsroot0` and calls `sweet_ufs_rootdev`; generic `rd=md0` handling consumes `/chosen/memory-map/RAMDisk` when present. No new device-matching shortcut needed. |
| `bsd_init` | Same unsealed-root policy | The build is unsigned and has no Image4 chain; root-auth ioctl failure must be reported and tolerated for VEUX. Added the VEUX board gate. Built-in AMFI policy and SWEET_HFS registration already cover VEUX. `bsd_utaskbootstrap` itself is common code, not SWEET-gated. |
| mockfs / ramdisk root | Available but not active in this image | `MASTER.arm64.veux` already enables `mockfs` and `sweet_hfs`. The generic ramdisk-to-`md0` code is present. Patch 0021 does not connect the shim payload to mockfs by itself. The current boot args use `rd=ufsroot0`, and the generated ADT has no RAMDisk property, so mockfs is not selected by the current build. If `rd=md0` were used with this ADT, root lookup would stop because no `RAMDisk` entry created `md0`. If a RAMDisk entry were added for the current `SWEETXNU` payload, `mockfs_mountroot` would reject its non-Mach-O header; the payload is not a mockfs root image. |
| `vfs_mountroot` / HFS+ | Same root policies | VEUX has one root volume and no separate data volume in this setup; `rootrw=1` clears `MNT_RDONLY`. Its unsigned, not-yet-cleanly-unmounted root also needs SWEET’s dirty-root allowance. Both gates now include VEUX. HFS+ registration/config is already present. |
| launchd bootstrap / exec | Same diagnostics; common bootstrap | `bsd_utaskbootstrap` and `load_init_program` are generic. Added launchd `execve` entry/failed-return markers. The short iOS-exec log style now applies to VEUX. `kern_mib.c` excludes VEUX from the macOS-style machine/model branch. `pid_hibernate` is exposed because the iOS SpringBoard userland calls it. |
| default core dumps | Same bounded default | Disable core files by default for VEUX as for SWEET; iOS shared-region dumps can be extremely large on the root volume. |
| HFS+ root and iOS syscalls | Same boot policy | VEUX can boot a real HFS+ root whose journal may be dirty after a reset; allow that root as SWEET does. Keep the HFS hard-link repair messages rate-limited because the root image is assembled with Linux tools. Expose `pid_hibernate` to iOS userland. |
| in-kernel SHA-256 for entropy | Same built-in implementation | VEUX already links the SWEET corecrypto SHA-2 implementation. Its entropy code must not wait for a corecrypto kext that is not part of this boot. Added VEUX to those gates. |
| IOKit/platform matching | Do not copy SWEET selectors or skip matching | `KernelConfigTables.cpp` has separate VEUX platform-expert and Kryo CPU matches. Sweet framebuffer, surface, watchdog, key-store, HID and SoC drivers are device-specific and remain SWEET-only. No blanket kext/IOKit matching skip is justified. |
| early MMU, CPU, GIC, timer, serial and FIQ gates | Keep device-specific branches | VEUX has its own framebuffer alias, memory-map and platform setup; SWEET's SM7150 MPIDR, GIC/serial/display paths are not interchangeable. Existing shared VEUX branches remain in startup, VM, FIQ and diagnostic code. |
| SWEET network logging, buttons/touch/USB, sampling, and UFS peripheral probes | Keep SWEET-only | These are optional observation/device drivers, not boot prerequisites. VEUX uses the separate VEUX UFS path and bounded log writer. |
| crypto primitives and trust-cache compatibility | Already shared where needed | The files needed by VEUX already use `ARM64_BOARD_CONFIG_VEUX`; unrelated per-file Sweet-only endian/MD5 variants remain unchanged. |

The patch series therefore changes the no-storage-class behavior specifically under `ARM64_BOARD_CONFIG_VEUX`, plus the adjacent root-auth, dirty/read-write-root, iOS syscall/identity, entropy and diagnostic policies justified above. It does not disable IOKit matching globally.

## ADT, INITRD, and root filesystem

`tools/mkadt.py --veux --highmem` creates `/chosen/memory-map` with only its name and phandle. It has no `RAMDisk` property. The SWEET ADT from the same generator has the same empty memory-map; it also has no `/chosen/boot-args` or `rd=` property. Boot arguments live in the `SWEETXNU` payload header instead. For this VEUX artifact they are:

```
debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam -noprogress rd=ufsroot0 veuxlog=1 veuxfb=1 veuxfbconsole=1
```

The Android boot-v2 header labels a 16,518,272-byte segment as its ramdisk and gives its load address as `0x01000000`. The shim does not use that header address as a fixed pointer: it reads the live ABL DTB's `/chosen/linux,initrd-start` and `linux,initrd-end`, prints those runtime `INITRD lo=` and `hi=` values, and searches that range for the `SWEETXNU` payload. The exact runtime lo/hi are therefore boot-specific; they are not constants in the image or ADT.

The segment begins with `SWEETXNU` (verified in the packaged artifact), and is the kernel payload, not a root filesystem. It contains no `/sbin/launchd`, and is neither an HFS+ volume nor a mockfs image. `mkpayload.py --ramdisk IMAGE` is the separate path that appends an image as a kernel segment and adds the ADT RAMDisk property for `rd=md0`.

The current root choice is `rd=ufsroot0`, so `IOFindBSDRoot` selects the VEUX UFS-backed `userdata` device. The project root-builder, `tools/mkiosroot.sh`, produces a real case-sensitive HFS+ iOS root image for that UFS target; this is the expected root format, not mockfs. The current XNU boot image does not itself prove what is presently written to userdata. If userdata does not contain that HFS+ root image, `IOFindBSDRoot` can still return the UFS device, but `vfs_mountroot` will fail its filesystem probes and `bsd_init` will log `cannot mount root` and retry. The next decisive signal is the new mountroot/vfs markers. If HFS+ root mounting succeeds, the next stages are `bsd_utaskbootstrap`, `load_init_program`/`execve("/sbin/launchd")`, then launchd's dyld startup and shared-cache lookup. Missing launchd or cache files fail after root mount and are distinct from `IOFindBSDRoot`.

## New display markers

The third diagnostic strip remains at y=2080, cells 32x32 with 64-pixel horizontal spacing. Existing cells 0-5 retain their meaning. New cells 6-15 are:

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

## Panic text region

The normal console ends at y=800. The wait-page renderer is capped at y=1815 (four threads per page); other diagnostic hex rows end above y=1780. Panic text is drawn in its own y=1816..2071 region, before the cell strip at y=2080 and fault bit rows at y=2120+. It uses the already initialized framebuffer font, prints the full formatted panic string, `panic_caller`, and up to eight bounded frame-chain return addresses in hex. It does not call the scrolling console; the original first-fault dump and early alias are retained.
