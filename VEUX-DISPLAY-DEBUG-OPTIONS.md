# VEUX ROM and kernel options for display-state diagnostics

Research date: 2026-10-20. Goal: expose Qualcomm SDE/DRM state to learn active framebuffer format/address without flashing or changing the Android installation.

## Finding

A custom ROM alone is not the solution. Debugfs and SDE debug interfaces are kernel build features; a ROM can restrict access, but it cannot add `CONFIG_DEBUG_FS` to a running kernel that was built without it. On the currently running slot A Android image, we verified `5.4.292-Paimon-君の名は。/1438fcba`; `/proc/filesystems` omits debugfs and `/proc/config.gz` has `CONFIG_DRM=y` but no `CONFIG_DEBUG_FS`. Magisk root is working, so this absence is not a permissions problem.

## Device-specific candidates

| Candidate | Compatibility evidence | Debug-state suitability |
|---|---|---|
| **Nebula Kernel r07** (`dev-sm6375/kernel_xiaomi_sm6375`) | Maintainer release says VEUX/PEUX, Linux 5.4.300, Android 11+, AOSP/MIUI/HyperOS; offers a prebuilt AnyKernel ZIP. | The published `arch/arm64/configs/vendor/veux-qgki_defconfig` enables DRM and IKCONFIG_PROC but does not enable `CONFIG_DEBUG_FS`. So the published config is not a ready-made debug kernel. The repo is a practical source base for a debug build; verify the generated `.config` before booting. |
| **Paimon Kernel** | This is already the kernel booted on slot A (`5.4.292`, build `1438fcba`); a corresponding Paimon VEUX release exists. The builder repository is archived. | The live kernel config is confirmed to have debugfs disabled. I have not found a source revision proven to reproduce build hash `1438fcba`, so changing Paimon’s config without establishing the source revision is not yet reproducible. |
| Other ROMs (Evolution X, Project Elixir, etc.) | Device-specific builds/source trees exist for VEUX. | No ROM found that advertises an SDE debug kernel. Evolution-X's public VEUX device tree sets `PRODUCT_SET_DEBUGFS_RESTRICTIONS := true`, which is a further access restriction. A ROM change would be unnecessary and would not guarantee a debug-enabled kernel. |

References:
- Nebula r07 release/compatibility notes: https://github.com/dev-sm6375/kernel_xiaomi_sm6375/releases/tag/r07
- Nebula VEUX defconfig: https://github.com/dev-sm6375/kernel_xiaomi_sm6375/blob/r07/arch/arm64/configs/vendor/veux-qgki_defconfig
- Paimon VEUX 5.4.292 release (builder repo is archived): https://github.com/onelots/kernel_auto_builder/releases/tag/Kernel-Paimon-Veux-5.4.292-12062025
- Evolution-X VEUX tree's debugfs restriction: https://github.com/Evolution-X-Devices/device_xiaomi_veux/blob/bka/device.mk#L1547-L1549
- The SDE source tree has per-CRTC and per-plane debugfs hooks, conditional on debugfs being built in; enabling the filesystem is necessary, but the available entries may not expose physical framebuffer addresses or establish the bootloader splash handoff.

## Recommended path

Do not install a ROM for this. Build a temporary VEUX debug kernel from a source/config matching the currently installed kernel as closely as possible, with `CONFIG_DEBUG_FS=y` and the Qualcomm SDE debug hooks enabled. Check the resulting kernel config before attempting it. Boot a packaged image temporarily with `fastboot boot` (not `fastboot flash`) and inspect `/sys/kernel/debug/dri`; keep the known-good boot slots intact. Because the exact Paimon source revision is not established, first compare the published Nebula/Positron base source and the running kernel's module/config ABI. The current Paimon kernel source provenance is an open item.

Even a debug-enabled Android kernel will primarily show Android's active composition. It may not reveal the early bootloader scanout at `0x85200000`; that may require an early SDE handoff/register trace. Do not write to the candidate framebuffer based on `dumpsys` or the Android plane format alone.
