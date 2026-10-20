# VEUX hardware facts from recovery and Linux source

Collected 2026-10-20 for `veux-xnu-build`. Device access was read-only ADB in recovery. No reboot, flash, or partition write was performed. The raw live DT archive is outside this repository at `../research/veux-recovery/live-dtb.tar`; it contains bootargs/device identifiers, so keep it private and out of git.

## Source provenance

- Live DT was read from `/sys/firmware/devicetree/base` over ADB. Root model: `Qualcomm Technologies, Inc. VEUX QRD NOPMI`; compatibles include `qcom,blair-qrd` and `qcom,blair`. Board ID is `0x1000b, 0`, matching the selected `dtb_1.dtb`.
- Reference Linux source: [`dereference23/kernel_xiaomi_sm6375`](https://github.com/dereference23/kernel_xiaomi_sm6375/tree/f4b8a13a43a130a9ab83cc985ce4d4421291ae6), commit `f4b8a13a43a130a9ab83cc985ce4d4421291ae6`. Its VEUX DTS matches model/board/panel details in the live tree. It is a community reference tree, **not proven to be the exact source for the installed Paimon recovery kernel** (`5.4.292-Paimon`, build hash `1438fcba`). Treat source-code behavior below as reference until matched against the exact binary source.
- Relevant source paths in that checkout: `arch/arm64/boot/dts/vendor/xiaomi/veux*.dts*`, `dsi-panel-k6s-38-0c-0a-fhdp-dsc-video.dtsi`, `arch/arm64/boot/dts/vendor/qcom/blair.dtsi`, `techpack/display/msm/sde/sde_kms.c`, `drivers/scsi/ufs/ufs-qcom.c`, `drivers/input/touchscreen/goodix_gtx8/goodix_ts_i2c.c`, and `drivers/usb/dwc3/dwc3-msm.c`.

## Display / framebuffer

- Live bootargs select `qcom,mdss_dsi_k6s_38_0c_0a_fhdp_dsc_vid`. Panel DTS describes 1080x2400, 120/60 Hz, 24-bit DSI input and DSC. `qcom,mdss-dsi-color-order = "rgb_swap_rgb"` describes the panel/DSI channel order; **it does not establish the DRM framebuffer memory format**.
- Recovery DRM reported 1080x2400, pitch 4352 bytes, 32 bpp / depth 24. `GETFB2` failed `EINVAL`; debugfs DRM is unavailable in this recovery (`CONFIG_DEBUG_FS` off; no `modetest`/`drm_info`). Thus the XRGB/ARGB channel byte order remains unknown.
- Live DT reserves `/reserved-memory/splash_region@0x85200000` at physical `0x85200000`, size `0x00c00000` (12 MiB), label `cont_splash_region`. `/proc/iomem` also showed this interval reserved. A separate `dfps_data_region` is at `0x85e00000`, size 1 MiB.
- Reference SDE `sde_kms.c` looks up `splash_region`, takes its `reg` as `splash_buf_base`/size, then calls `one_to_one_map` with the same address as IOVA and physical address. This supports the region being intended for splash handoff. It does **not** prove the bootloader’s currently active scanout points there, nor supply actual framebuffer stride/format. Keep XNU framebuffer writes disabled until active scanout and pixel layout are independently verified.
- SDE/DSI bases from the live tree: controller `0x05e00000`, DSI controller `0x05e94000`, PHY `0x05e94400`.

## UFS

- Live UFS controller `0x04804000` (window 0x3000); ICE `0x04808000` (0x8000); ICE-HWKM `0x04810000` (0x9000); PHY `0x04807000` (0xddc). One lane, GIC SPI 356. DTS supplies clocks, resets, interconnect/bandwidth paths, and PHY bindings.
- Recovery has Qualcomm UFS (`ufshcd-qcom`) and QMP v4 Yupik PHY bound. This gives XNU port targets and addresses; it does not mean SWEET’s UFS implementation can be reused unchanged.

## Touch / power

- Touch node is Goodix GT9896 at I2C address `0x5d` on `qupv3_se8_i2c`; IRQ GPIO 22 falling-edge, reset GPIO 21, AVDD GPIO 51, DVDD GPIO 44; declared panel coordinate maxima 8640x19200 and pen support.
- Live platform includes SPMI/PM6125, PMK8350 and PMR735A; input devices include `goodix_ts`, `qpnp_pon`, gpio-keys and AW8624 haptics. Battery and USB power supplies are exposed by recovery.
- These identify the Linux bindings and wiring. XNU still needs matching GPIO/I2C/GENI/SPMI/PMIC sequencing and interrupt behavior; the DTS alone does not provide a complete power driver.

## USB

- VEUX USB wrapper (`qcom,dwc-usb3-msm`) and DWC3 are at `0x04e00000`, 1 MiB, IRQ SPI 255. QUSB2 PHY is at `0x0162b000`; QMP combo PHY at `0x01630000`. DT includes four wrapper interrupts and clock/reset/GDSC resources.
- Reference VEUX addresses differ from SWEET assumptions (SWEET DWC3 `0x0a600000`, QUSB2 `0x088e2000`). Do not carry SWEET MMIO addresses or wrapper setup over.

## What recovery could not expose

- Exact framebuffer allocation being scanned out, active DRM plane FourCC/channel byte order, and validated safe write/flush path.
- Exact Paimon 5.4.292 source corresponding to build hash `1438fcba`.
- Full XNU requirements for SDE handoff, UFS PHY/ICE and SPMI/GENI interrupt/power setup. The Linux DTS is wiring/reference evidence, not an XNU port.

## Next concrete work

1. Keep display writes disabled; first add a read-only XNU/boot diagnostic path to confirm the reserved splash handoff and capture active SDE state, or build a recovery with DRM debug enabled and query plane state/FourCC.
2. Identify the exact recovery-kernel source/build if available, then compare the relevant SDE/UFS/Goodix/PMIC/DWC3 driver revisions against this reference tree.
3. Start with headless boot prerequisites and board-specific CPU/GIC/timer/interrupt and UFS initialization; port touch, power and USB once the kernel reaches a stable diagnostic environment.
