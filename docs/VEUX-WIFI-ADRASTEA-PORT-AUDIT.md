# VEUX Adrastea and Topaz WLAN port audit

**Date:** 2026-10-29  
**Scope:** read-only recovery ADB and host-side firmware/partition copies. No source, build, or device changes.

## Follow-up evidence — recovery built-ins, GLINK IDs, and milestone gate

**Evidence classes:** the Adrastea device selection and WLFW state sequence remain source-derived; recovery kernel configuration and symbols are runtime-confirmed; no modem/WLFW transaction or radio interface has been runtime-confirmed. GLINK SMEM item numbers below are confirmed by public Qualcomm Linux source, but not by a VEUX runtime trace. The exact Adrastea CE target and service arrays are still not conclusively sourced.

### Recovery kernel and module locations

The connected recovery remains on slot `_a` (`4078cac030c8`), running Linux `5.4.292-Paimon`. Its live `/proc/config.gz` reports `CONFIG_ICNSS2=y`, `CONFIG_ICNSS2_QMI=y`, `CONFIG_CLD_LL_CORE=y`, `CONFIG_WLAN=y`, `CONFIG_MSM_PIL=y`, `CONFIG_MSM_SUBSYSTEM_RESTART=y`, `CONFIG_QCOM_SMP2P=y`, `CONFIG_QCOM_GLINK=y`, and `CONFIG_QRTR=y`. `/proc/kallsyms` exposes built-in symbols including `icnss_probe`, `icnss_wpss_load`, `subsystem_get`, `subsystem_get_with_fwname`, `pil_boot`, and numerous `wlan_hdd_*` functions (addresses are masked to zero). The boot_a kernel's embedded config was also previously checked and matches these built-in selections.

The repeated read-only inventory found no `.ko`, `modules.load`, or `modules.dep` under the live `/vendor`, `/system`, `/odm`, or `/lib/modules` trees. The checked GPT has no physical `vendor_dlkm`, `odm_dlkm`, or `system_dlkm`; the `super` logical partition inventory likewise had no DLKM logical partition. This settles the module-location question for the inspected images: the ICNSS2, PIL, GLINK/QRTR, and WLAN host stack are built into the vendor recovery kernel, not shipped as separate modules in those carriers. Consequently there is no module ELF to open in REA; the source tree and live kallsyms/config are the available evidence. This does not identify the external component that asks PIL to start the modem.

Recovery reports `/sys/bus/msm_subsys/devices/subsys2/name` as `modem` and its `state` as `OFFLINING`. The state attribute is mode `0444`; it is not a writable trigger in this recovery. No write or other modem-start operation was attempted. A stock Android run is still required to see the modem/WLAN-PD service arrival and runtime WLFW order.

### GLINK SMEM IDs

The VEUX DT does not encode the GLINK SMEM item numbers as properties. The standard Qualcomm GLINK-over-SMEM transport source does define them: item `478` is `SMEM_GLINK_NATIVE_XPRT_DESCRIPTOR`, `479` is `SMEM_GLINK_NATIVE_XPRT_FIFO_0`, and `480` is `SMEM_GLINK_NATIVE_XPRT_FIFO_1` ([Qualcomm kernel `qcom_glink_smem.c`](https://android.googlesource.com/kernel/msm/%2B/19181fc386f3789282f70790bdd3d05eb63a8db4/drivers/rpmsg/qcom_glink_smem.c), [SMEM enum](https://android.googlesource.com/kernel/msm/%2B/d5d2256a441456eb3548ee03b95323f111732bb5/include/soc/qcom/smem.h)). Those numbers are source-confirmed standard transport IDs, but the local VEUX kernel snapshot omits the GLINK-SMEM implementation/header and recovery has not booted the modem, so their use by the VEUX modem channel remains unverified at runtime. The SMP2P item indices 435/428 are separately declared by VEUX DT and must not be conflated with GLINK's 478–480 items.

### CE source search result

The public Android `drivers/net/wireless/ath/ath10k/snoc.c` source contains a 12-engine generic ath10k `target_ce_config_wlan`, a service map, and an empty `target_shadow_reg_cfg_map`; it also defines Adrastea source/destination write-index offsets `0x3c`/`0x40` ([source](https://android.googlesource.com/kernel/msm/%2B/748b6dc2a170e75f816e5734e94c74f236a02aa2/drivers/net/wireless/ath/ath10k/snoc.c)). Its candidate target table, in CE order 0–11, is: `(OUT,32,2048)`, `(IN,32,2048)`, `(IN,64,2048)`, `(OUT,32,2048)`, `(OUT,256,256)`, `(OUT,1024,64)`, `(INOUT,32,16384)`, `(4,0,0)`, `(IN,32,2048)`, `(IN,32,2048)`, `(IN,32,2048)`, `(IN,32,2048)` for direction, entries, and max bytes. CE4/CE5 disable interrupts; CE8 has flags zero. The service map uses VO/BK/BE/VI/control uplink CE3 and downlink CE2; reserved-control uplink CE0/downlink CE2; raw-stream uplink CE0/downlink CE2; HTT data uplink CE4/downlink CE1; IPA uplink CE5; HTT data2/data3/log downlinks CE9/10/11; then a zero terminator. The shadow map is empty.

This is a **candidate reference, not a proven Adrastea target table**: the file is ath10k SNOC rather than the downstream QCA host-CMN target-specific source selected by the VEUX vendor build, and its target association to the VEUX `0xabcd` ICNSS path is not established. Do not insert these candidate rows into patch 0123. The exact Adrastea target/service/shadow arrays requested in the gate remain unknown. The earlier descriptor finding remains: QCA_WIFI_3_0 uses four 32-bit words (16 bytes), while Topaz's 16-byte packed record places its fields differently, so equal size does not establish layout compatibility.

### Milestone image status

No milestone XNU image was built or staged. The local XNU patch queue contains no modem PAS/GLINK/QRTR/WLFW implementation corresponding to Topaz 0113/0115/0118/0121/0122; only ordinary VEUX diagnostic patches are present. A reliable staged image still needs that platform code and a verified transport/service-discovery path. The requested `veuxlog=1` argument is also rejected by the strict manifest because its persistent UFS tail may overlap the HFS+ root; the existing logger must not be enabled until that range is proved safe or moved to a separately reserved region. Therefore there is no wrapper hash, manifest, or flash plan to approve from this follow-up. No partition was flashed and neither boot slot was changed.

The recovery modem state sysfs file is read-only, so the permitted recovery trigger is unavailable here. Runtime observation should use a stock Android boot and collect modem/ICNSS/WLFW logs, remoteproc/subsystem state, GLINK/QRTR service arrival, and the WLFW CAP response. Any future recovery trigger requires explicit user approval if a writable supported control is found.

## Decision

**Architecture prototype: go. Parameter-only Topaz copy: no-go.** VEUX's live DT selects the Adrastea ICNSS path (`qcom,icnss` → `0xabcd` in the SM6375 ICNSS2 source), and the modem image contains a WLAN protection-domain declaration and WLAN firmware. This does not confirm a physical WLAN chip ID or prove that the WLAN-PD starts during recovery.

The source-derived Adrastea WLFW sequence skips `HOST_CAP`. The recovery did not start a WLAN QMI exchange, and no shipped `icnss2.ko` was found, so this cannot be labeled binary-derived or packet-capture-confirmed.

## Recovery and partition evidence

| Evidence | Result | Class |
| --- | --- | --- |
| ADB root / current slot | `uid=0`, `_a` | Runtime-confirmed |
| `/sys/bus/msm_subsys/devices` | `adsp=ONLINE`; `cdsp=OFFLINING`; `modem=OFFLINING`; `ipa_fws=OFFLINING`; `a615_zap=OFFLINING`; `venus=OFFLINING` | Runtime-confirmed |
| WLAN interfaces / bus | No `wlan0`, PCI endpoint, or SDIO function in recovery; SDHCI is `no-sdio` | Runtime-confirmed |
| Recovery modem/WLAN log matches | No modem firmware load or WLFW service-arrival record; repeated `ipa_fws` load failures were excluded from modem assessment | Runtime-confirmed |
| Slot-A module scan | No `.ko` files in extracted `vendor_a`, `system_a`, `system_ext_a`, `product_a`, `odm_a`, or inspected boot/vendor-boot/rescue ramdisks | Host-copy binary inventory |
| Recovery partitions | No `recovery_a`; `rescue` is present. Legacy LZ4/EROFS extractors unavailable; manual host ramdisk extraction was used where possible | Host-copy inventory |

Since no kernel module was found, `modinfo` and REA/Ghidra disassembly for `icnss2.ko`, `qca_cld3_*`, PIL, GLINK, QRTR, or WLAN firmware-service modules is unavailable. The APSS module that starts the WLAN PD and the exact `subsystem_get("modem")` call chain remain unknown. A stock Android boot is needed to observe init-triggered modem startup and runtime firmware service registration.

## `HOST_CAP` conflict

The downstream `drivers/soc/qcom/icnss2/main.c` server-arrival path connects to WLFW, sends `IND_REGISTER`, sends `HOST_CAP` only for `WCN6750_DEVICE_ID`, then for `ADRASTEA_DEVICE_ID` sends `MSA_INFO`, `MSA_READY`, and subsequently `CAP`. The `ADRASTEA_DEVICE_ID` is `0xabcd`; the compatible `qcom,icnss` selects it in the local OF table. The public Android source shows the same branch ([ICNSS2 `main.c`](https://android.googlesource.com/kernel/msm/%2B/d71b1a76b1a797648ec6740f1a206e597d6b139a/drivers/soc/qcom/icnss2/main.c), [device IDs](https://android.googlesource.com/kernel/msm-modules/wlan-platform/%2B/refs/heads/android-msm-eos-android13-wear-kr3-pixel-watch/icnss2/main.h)).

**Answer for VEUX's source-selected Adrastea path: no `HOST_CAP`.** This is source-derived evidence. There is no shipping module in the examined copies and no recovery WLFW exchange, so there is no binary- or runtime-derived confirmation of the modem's actual response behavior. A string scan of the extracted `wlanmdsp.mbn` found no `wlfw_host_cap`, `host_cap_req`, `host_cap_resp`, or `WLFW_HOST_CAP` strings. That is only weak negative binary evidence; the APSS driver selects the protocol branch.

**Required 0122 change:** on successful `IND_REGISTER`, send `MSA_INFO` directly. On successful `MSA_INFO`, process region and secure-memory information, then send `MSA_READY`. After successful `MSA_READY`, send `CAP`. Keep `HOST_CAP` only in a WCN6750 branch if the code remains multi-target. Do not send it and continue after a nonfatal reject.

Topaz does not contradict this. The linked [ios-topaz repository](https://github.com/MakrSas/ios-topaz) targets SM6225; its PAS patch says that the modem DSP runs WCN3988 WLAN firmware. Topaz 0122 sends `HOST_CAP` and tolerates rejection. That is evidence for its WCN3988 target, not the VEUX Adrastea path. Topaz 0123 itself describes WCN3990-style 64-bit CE descriptors. Shared bus geometry does not make those firmware/CE tables interchangeable.

## Modem/WLAN-PD metadata and trigger

`modemuw.jsn` defines `modem/wlan_pd`, QMI instance 180, with `kernel/elf_loader`, `tms/servreg`, and `wlan/fw` providers. `modemr.jsn` defines `modem/root_pd`, instance 180, with `tms/servreg`, `tms/pdr_enabled`, and `gps/gps_service`. Neither JSON contains a file path, dependency list, or boot-order field. The modem DSP ELF includes `wlanmdsp.mbn` and candidate paths under `/readonly/firmware/image/`, `/readonly/vendor/firmware_mnt/image/`, and `/readonly/vendor/firmware/`.

This supports a WLAN protection domain inside the modem subsystem, with a WLAN firmware service able to resolve its DSP image. It does not prove whether `wlan_pd` auto-starts with `modem_pd`. No separate APSS `subsystem_get("wlan")` is stated in either JSON. Recovery's `modem=OFFLINING` means the firmware service could not have arrived in this observed state. XNU will need to boot modem PAS and provide modem-PD service discovery/IPC; the exact child-PD start policy remains runtime-unknown.

## Firmware offsets and CRCs

[`VEUX-MODEM-FW-TABLE.csv`](VEUX-MODEM-FW-TABLE.csv) gives each file's FAT image byte offset, size, CRC32, cluster chain, and contiguity for 116 WLAN/modem files from a read-only copy of `modem_a`. It contains all present `modem.bNN`, `modem.mdt`, both JSNs, `wlanmdsp.mbn`, and all `bdwlan.*`/`bdwlanu.*` variants. The 0115-needed `modem.b00–b29` range is represented; `b16` and `b24` are absent. Present `b30–b34` are also listed. The JSNs do not reference segment filenames; `modem.mdt` describes the modem ELF segments. The files were read from the extracted FAT filesystem; offsets were calculated using data-area offset 77,824 bytes and 16,384-byte clusters.

Key rows:

| File | Offset | Size | CRC32 |
| --- | ---: | ---: | ---: |
| `modem.mdt` | `0x0b077000` | 9,500 | `0xd4116f84` |
| `wlanmdsp.mbn` | `0x0b92b000` | 3,970,288 | `0x190e2194` |
| `modemuw.jsn` | `0x0bcf7000` | 713 | `0x28100814` |
| `modemr.jsn` | `0x005e7000` | 719 | `0x94bf3c44` |

These values describe VEUX's modem_a only; never reuse Topaz offsets.

## Constant substitution map

| Topaz constant/assumption | VEUX value or evidence | Status / change |
| --- | --- | --- |
| PAS modem ID `4` | `blair.dtsi`, `qcom,mss@06000000`: `qcom,pas-id = <4>` | Match, source-derived. |
| PIL firmware name `modem` | `qcom,firmware-name = "modem"`; `modem.mdt` exists | Match. |
| Topaz carveout `0x4ab00000 + 0x06900000` | `pil_mpss_wlan_mem`: `0x8b800000 + 0x10000000`, referenced by `pil_modem` | Replace. It is a 256 MiB MPSS/WLAN reservation; not a dedicated WLAN pool. |
| Topaz pool `0xe0000000`, size 4/8/16 MiB | No matching VEUX DT reservation/allocation agreement | Unknown. Reserve safe XNU memory before using a pool. |
| SMEM `0x46000000 + 0x200000` | Live/downstream `smem@80900000`: `0x80900000 + 0x200000` | Replace base; size matches. |
| TCSR mutex `0x00340000` | `tcsr_mutex_block` reg `0x00340000 + 0x20000`; SMEM hwlock ID 3 | Base matches; honor mutex API/lock ID. |
| Topaz APCS PA `0x0f111000`, SMP2P bit 14, GLINK bit 12 | VEUX IPCC reg `0x00208000 + 0x1000`, GIC SPI 334; MPSS client 2; SMP2P signal 2, GLINK_QMP signal 0 | Replace raw APCS doorbell scheme with VEUX IPCC/IPCC-backed SMP2P/GLINK. Do not reuse Topaz bits. |
| SMP2P item IDs 435/428 | VEUX `qcom,smp2p-modem` has `qcom,smem = <435>, <428>` | Numeric match. |
| GLINK descriptor/TX/RX IDs 478/479/480 | Not specified by VEUX DT, JSON, or available local driver source | Unknown; Topaz values unverified. |
| MSA `0x51900000 + 0x100000` | Live ICNSS `qcom,wlan-msa-fixed-region` points to `wlan@86500000`, `0x86500000 + 0x200000` | Replace. Runtime live-DT confirmed; secure permissions still unknown. |
| VMIDs MSS_MSA `0x0f`, WLAN `0x18`, WLAN-CE `0x19` | `include/soc/qcom/secure_buffer.h` declares same values | Numeric match, source-derived; confirm actual handoff/permissions at runtime. |
| WLAN SID `0x1a0` and Topaz SMMU CB programming | VEUX ICNSS `iommus = <&apps_smmu 0x80 1>`; app SMMU at `0x0c600000` | Replace SID and derive VEUX context-bank configuration. Topaz identity mapping is not portable. |
| CE base/count/IRQs | ICNSS `0x0c800000`, resource size `0x800000`; 12 direct GIC IRQs encoded `0x166–0x171`; Topaz uses `+0x240000` and shadow `+0x32000` | 12 IRQs/runtime DT are confirmed; the CE offset needs target Adrastea source confirmation. |
| CE target, service-to-CE, shadow arrays | No Adrastea QCA host-CMN array source in this checkout. Public generic ath10k SNOC config found is WCN3990-specific. | Unknown; obtain correct Adrastea target source before sending WLAN_CFG or starting CE. |
| WLFW client ID `0x4b4e454c` | Topaz labels this `ATH10K_QMI_CLIENT_ID`; no VEUX implementation or packet capture | Candidate only. |
| WLFW service/message IDs | Common source protocol: service `0x45`, IND_REGISTER `0x20`, MSA_INFO `0x2d`, MSA_READY `0x2e`, HOST_CAP `0x34` | Keep message IDs; omit HOST_CAP on Adrastea. |
| BDF selection/fallback | `modem_a` contains dozens of BDF variants plus `bdwlan.bin` | Need runtime CAP board ID and target mapping. Do not assume `bdwlan.bin`. |

The live ICNSS SMMU IOVA aperture is `0xb0000000 + 0x10000`; the actual CE-ring IOVAs and SMMU mappings are runtime values and remain unknown. CAP chip ID/family/board/SoC IDs, actual returned secure MSA regions, firmware-selected BDF, CE ring addresses, and WLAN rail/clock state also require a stock-Android WLFW run.

## Port plan

Recommended order is **0113 + 0115 + 0118 + 0121 + corrected 0122**. Treat 0123 as conditional and later, once the exact Adrastea CE config is available. Patches 0125/0126/0129 follow only after CE/HTC/WMI work; they are not needed to prove modem/WLAN-PD/WLFW presence.

| Patch | Concrete change inventory |
| --- | --- |
| 0113 PAS | Preserve PAS/SCM sequencing and ID 4; substitute VEUX modem carveout and SMEM; rework pool reservation; replace Topaz APCS/SMP2P doorbell polling with VEUX IPCC/SMP2P. |
| 0115 firmware reader | Preserve read-only FAT/MDT parsing only after checking VEUX MDT semantics; use the linked CSV; handle missing b16/b24 and present b30–b34; keep EFS read-only. |
| 0118 GLINK/QRTR | Keep framing as a candidate; verify GLINK item IDs 478–480, FIFO layout, service/channel names, and the IPCC transport before using Topaz ring geometry or interrupt polling. |
| 0121 host services | Keep only services requested by VEUX firmware; replace pool sizing, firmware paths, TFTP source and RMTFS policy; initially avoid RMTFS writes. Use JSON instance 180 as a discovery hint, not boot-order proof. |
| 0122 WLFW | Retain common QMI codecs; reorder Adrastea to IND_REGISTER→MSA_INFO→MSA_READY→CAP; use MSA DT value; implement actual response-region assignment and target VMID permissions; capture CAP fields before selecting BDF. |
| 0123 WLAN/CE | Defer until Adrastea arrays and SMMU context are sourced; replace SID/context config, target/service/shadow arrays, descriptor type, IRQ handling and DMA policy. Only retain CE address arithmetic after confirmation. |
| 0125/0126/0129 | Defer until CE, HTC, WMI, BDF and board data work. |

**Largest missing XNU foundation:** a VEUX-specific modem PAS and IPCC-backed IPC stack to start the modem and discover the running WLAN-PD WLFW service. The absent modules prevent reproducing the Linux loader call chain, and the missing Adrastea CE tables prevent safe DMA/radio access.

## Constraints and artifacts

The phone remains in root recovery, slot A. The `super` copy and extracted slot-A logical partitions are read-only host artifacts. No `wpss_boot` write, RW mount, boot partition write, build, or flash occurred. `recovery_a` is absent; the `rescue` ramdisk was inspected instead. `lz4` and EROFS extraction utilities are missing; unblob identified these formats, and existing host-side manual ramdisk extraction/carving was used where possible.

## Source index

* Device tree: `research/kernel_xiaomi_sm6375/arch/arm64/boot/dts/vendor/qcom/blairp.dtsi` (ICNSS target override) and `blair.dtsi` (reserved memory, SMEM, TCSR, modem PAS, SMP2P, IPCC, ICNSS), plus live `/proc/device-tree` reads from recovery.
* ICNSS2 protocol: `research/kernel_xiaomi_sm6375/drivers/soc/qcom/icnss2/main.c` (server-arrival sequence and OF match), `main.h` (device IDs), and `qmi.c` (message helpers). Public cross-check: [Android ICNSS2 `main.c`](https://android.googlesource.com/kernel/msm/%2B/d71b1a76b1a797648ec6740f1a206e597d6b139a/drivers/soc/qcom/icnss2/main.c).
* VMID/IPCC: `research/kernel_xiaomi_sm6375/include/soc/qcom/secure_buffer.h` and `include/dt-bindings/soc/qcom,ipcc.h`.
* Topaz: `/tmp/ios-topaz-readonly/xnu/patches/0113-topaz-modem-pas-boot.patch`, `0115-topaz-modem-fw-from-modem-a.patch`, `0118-topaz-modem-glink-qrtr.patch`, `0121-topaz-modem-host-services.patch`, and `0122-topaz-modem-wlfw.patch` / `0123-topaz-wlan-scan.patch`; repository source is [MakrSas/ios-topaz](https://github.com/MakrSas/ios-topaz).
* Firmware: read-only `modem_a` FAT copy at `/tmp/veux-wifi-readonly/modem_a.img`, extracted files under `/tmp/veux-wifi-readonly/modem_extract/modem_a.img_extract/image/`, full file metadata in the committed CSV alongside this report.
