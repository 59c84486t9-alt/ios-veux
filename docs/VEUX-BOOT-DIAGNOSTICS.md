# VEUX boot diagnostics

The latest XNU run 39805058203 passed CI; its fresh boot image was flashed
to boot_b and the user still sees the Xiaomi logo. This is a runtime issue.
Older recovered pmsg contains the shim's XNU handoff and early XNU fragments,
but it is corrupted and does not identify the current boot's stopping point.
Do not present an older log fragment as the last line from this boot.

## Standalone live-FDT probe v2

```sh
PATH=/usr/local/opt/aarch64-elf-binutils/bin:$PATH python3 tools/build-veux-fb-probe.py \
  --template shim/out/shim-boot-veux-directfb-probe-oldxnu-20261022.img \
  --dtb dtb/vendor_boot_b_unpacked/dtb_1.dtb \
  --out-dir shim/out/veux-fdt-probe-v2
python3 tests/test_veux_fb_probe.py
```

Uses Clang and AArch64 ELF binutils; override `--clang` and `--cross-prefix`
for other installations. The template must be the previously accepted VEUX
shim boot-v2 package with the selected DTB. The builder issues no device commands.
The original fixed-address white-screen image remains in its separate output
folder as a historical artifact; v2 replaces that implementation in source.

The assembly preserves ABL's live FDT pointer in x0, checks EL1/MMU-off/cache-off,
sets a private stack and enters the bounded C parser. No XNU, UFS, GIC, timer,
MMU setup or display MMIO driver is linked. The probe waits indefinitely after
completion or a skipped draw; it never returns to firmware.

It accepts one enabled, complete `simple-framebuffer` under root or `/chosen`,
or an identity-mapped reserved-memory bus. Base, allocation, width, height,
stride and format all come from that live node. Supported formats are
`a8r8g8b8`, `x8r8g8b8`, `a8b8g8r8`, `x8b8g8r8`. Addresses must additionally
fit VEUX's independently verified 12 MiB splash reservation. This is a safety
bound, not a fallback scanout address. Incomplete, unsupported, ambiguous or
translated framebuffer descriptions are skipped.

The pattern has vertical red, green and blue bars, a white top-left square,
and a black border. Padding bytes remain untouched. The known board-matched
K6S panel source declares `dsi_video_mode`; that is source evidence, not a
live controller-state measurement. The probe does not send a DSI refresh kick.

If the live FDT confirms the known ramoops reservation, the probe appends a
uniquely marked text record to the previously runtime-verified 1 MiB pmsg ring
at 0xd0100000. It retains that observed runtime split rather than deriving it
from the differing DT pmsg-size property. Stores are ordered before updating
the Linux persistent-RAM cursor. It logs the FDT address, framebuffer count,
geometry, RGB/BGR selection and stages:

| Marker | Meaning |
| --- | --- |
| `stage=1 parsed live FDT` | FDT parsing completed and pmsg writes began. |
| `stage=2 SKIP ...` | No usable unique framebuffer; no display write attempted. |
| `stage=2 validated ...` | About to draw the RGB pattern. |
| `stage=3 RGB fill complete ...` | RAM stores completed; panel visibility is still a separate observation. |

Malformed FDT or unexpected entry state halts without logging. If ramoops is
not confirmed, logging is disabled. Persistent RAM retention and log integrity
still require device validation; the prior XNU logs were corrupted. A missing
marker alone does not prove that the probe never entered.

Both saved inputs (`dtb_1.dtb` and recovery-fdt.dtb) parse successfully, contain
the known ramoops reservation, and have no simple-framebuffer node. Unless ABL
adds one to the live handoff FDT, expect SKIP. Adding an invented node to the
input DTB would not verify the bootloader's actual scanout layout.

## Next device step

Recover logs from the current XNU attempt before overwriting boot_b again.
Neither ADB nor fastboot was connected after the logo report; the user must
return the phone to fastboot. Use slot-A recovery for the pstore and bounded
userdata-tail read. Record the exact new log, or its absence, separately from
older captures. Flashing a new probe is a separate device action; no new
probe has been flashed in this update.
