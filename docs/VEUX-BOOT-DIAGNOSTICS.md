# VEUX boot diagnostics

The local project is `ios-veux-build`, branch `veux-xnu-build`. The upstream
README describes SWEET; its working home screen is not a VEUX result.
Recovered pmsg logs already contain the shim's XNU handoff and early XNU text.
The remaining problem is an unknown XNU stopping point and unverified scanout.

## Standalone white-screen probe

Build from the existing known VEUX shim package (paths relative to this repo):

```sh
PATH=/usr/local/opt/aarch64-elf-binutils/bin:$PATH python3 tools/build-veux-fb-probe.py \
  --template shim/out/shim-boot-veux-directfb-probe-oldxnu-20261022.img \
  --dtb dtb/vendor_boot_b_unpacked/dtb_1.dtb \
  --out-dir shim/out/veux-fb-only-20261022
```

Uses Clang and AArch64 ELF binutils; override `--clang` and `--cross-prefix`
for other installations. The template must be a previously accepted VEUX shim
boot-v2 package, with the exact supplied DTB. Do not use a stock v3/v4 image
as the template. The builder issues no device commands.

The resulting `shim-boot-veux-fb-only.img` contains a 4096-byte standalone
probe and empty compressed cpio ramdisk. It checks EL1 with MMU and D-cache
off, writes white pixels into the existing configured framebuffer, and halts.
No XNU or storage driver is linked. It does not reprogram the display controller.

| Observation | Interpretation |
| --- | --- |
| White replaces the logo | Entry, the fill loop and visible scanout at this address worked; proceed to the corrected XNU image. |
| Logo remains | Still ambiguous: entry-state check, image entry, a RAM write fault, or the scanout/layout assumption could be responsible. |
| Reset | Record timing and USB enumeration; this probe contains no reset request. |

The existing profile is base `0x85200000`, 1080x2520, stride 4320,
`a8r8g8b8`, in 12 MiB. The reservation is independently supported by DT;
active bootloader scanout and geometry remain unconfirmed. White avoids
red/blue channel-order ambiguity, but cannot compensate for compression,
a different address, or an inactive panel. Lack of ADB is expected.

This phone previously rejected temporary `fastboot boot`. Testing requires
explicit approval for writing the exact candidate to `boot_b`; preserve slot A,
recovery and backups. Do not flash userdata for this diagnostic.

## Kernel build repair

Run 39796431519 compiled but skipped patch 0103 (zero-context hunks), then
failed source verification. The patch now uses contextual hunks verified
with standard `git apply` against that run's actual source. The IORPC check
also accepts alignment whitespace. Local source assertions pass; a fresh CI
compile and hardware result must be recorded separately in NOTES.md.
