# VEUX Wi-Fi discovery: current evidence and safe next step

Updated 2026-10-29 from live root recovery ADB, the live device tree, the local
SM6375 reference kernel, and the XNU build tree. The reference kernel is the
community `kernel_xiaomi_sm6375` checkout; it is not established as the exact
source for the installed Paimon recovery kernel.

## Hardware identification

The recovery live DT contains `/soc/qcom,icnss@C800000`, with `compatible =
"qcom,icnss"`, `reg = <0x0c800000 0x00800000 0xb0000000 0x00010000>`, and
`reg-names = "membase", "smmu_iova_ipa"`. In the local Qualcomm vendor
binding, `qcom,icnss` denotes the Adrastea architecture; `qcom,wcn6750`
denotes iWCN. The local SM6375 reference driver's OF match table maps
`qcom,icnss` to `ADRASTEA_DEVICE_ID` (`0xabcd`) and `qcom,wcn6750` to
`WCN6750_DEVICE_ID` (`0x6750`). Thus the live DT strongly identifies an
Adrastea-style ICNSS configuration and argues against a standard WCN6750
configuration. It does not prove the physical package marking or runtime
silicon ID; recovery does not expose the ID in its current logs or sysfs.

Its supplies are `vdd-cx-mx`, `vdd-1.8-xo`, `vdd-1.3-rfa`, `vdd-smps`,
`vdd-3.3-ch0`, and `vdd-3.3-ch1`. Its interrupt property encodes GIC SPI
values 0x166–0x171 (decimal SPI numbers 358–369), an
SMMU reference, and a WLAN SMP2P crash/error input. The source ICNSS2 driver
supports both IDs, but this DT does not use the WCN6750 match.

This differs materially from the reference WCN6750 node in `yupik.dtsi`: that
node uses `compatible = "qcom,wcn6750"`, `reg-names = "msi_addr",
"smmu_iova_ipa", "tcs_cmd"`, and 32 CE interrupt entries beginning at GIC
SPI 768. VEUX instead has two regions named `membase` and `smmu_iova_ipa`,
12 interrupt entries beginning at encoded SPI 0x166, and no `tcs_cmd` or
`msi_addr` region. The ICNSS register region at 0xc800000 is not an MSI BAR
and should not be treated as a PCIe root-complex window.

The live tree also contains a separate `qcom,wcn3990` Bluetooth node. Its
`qcom,bt-sw-ctrl-gpio` tuple is `<0xa7 0x45 0>`, i.e. GPIO 69 using the
referenced TLMM controller. The recovery log reports that `bt-reset-gpio` and
`wl-reset-gpio` were not provided. No dedicated WLAN_EN GPIO appears in the
saved ICNSS properties. Do not equate the Bluetooth switch-control GPIO with
WLAN enable or reset.

The saved live DT archive contains no node/property path matching WPSS,
remoteproc, `qcom,rproc-handle`, or a WCN6750 compatible. In the local
reference WCN6750 tree, WPSS is a separate subsystem/remoteproc node and
GLINK/QRTR endpoint, rather than a `qcom,rproc-handle` property on ICNSS. Its
absence in this archive means no DT-declared WPSS instance is evidenced; it
does not establish whether the proprietary recovery firmware starts a remote
processor through another mechanism.

The two SDHCI hosts are at `0x04744000` (DT interrupt cells `0x15c` and
`0x160`) and `0x04784000` (cells `0x15e` and `0x161`). Both have `no-sdio`;
the first also has `no-sd`, and the
second has `no-mmc`. Recovery logged `mmc0` and `mmc1` as ADMA 64-bit hosts,
but neither is an SDIO WLAN interface. The live DT archive has no PCI/PCIe
host node. The ICNSS block is at `0x0c800000`; do not call that address a PCIe
root-complex address. The reference WCN6750 path uses QMI/MHI with a WPSS
firmware-enumerated PCIe endpoint, rather than a normal SDIO function; the
saved VEUX DT does not confirm that WCN6750 path.
The precise external endpoint/config-space discovery path is not established
from these saved records.

## Recovery ground truth available locally

The recovery log contains:

- `icnss2 c800000.qcom,icnss: Adding to iommu group 8`
- `icnss2: Recursive recovery allowed for WLAN`
- `icnss2: Platform driver probed successfully`
- `ipa ... ipa_smmu_wlan: Adding to iommu group 3`
- SDHCI host registration at 0x04744000 and 0x04784000
- `bt-reset-gpio not provided in devicetree` and `wl-reset-gpio not provided in device tree`

This establishes Linux platform-driver binding for ICNSS2, not that WLAN
firmware booted or the radio enumerated. Live root recovery ADB on slot A
returned the complete requested Wi-Fi-related dmesg matches:

```text
[    0.732528] cnss_utils: Unable to create debugfs -19
[    0.762187] wlan_hdd_state wlan major(505) initialized
[    1.157732] ipa 5800000.qcom,ipa:ipa_smmu_wlan: Adding to iommu group 3
[    1.160609] icnss2 c800000.qcom,icnss: Adding to iommu group 8
[    1.160624] icnss2: Recursive recovery allowed for WLAN
[    1.160853] icnss2 c800000.qcom,icnss: for wcss_msa0 segments only will be dumped.
[    1.160910] icnss2: Platform driver probed successfully
[    1.172742] uaudio-qmi soc:usb_audio_qmi_dev: Adding to iommu group 25
[    3.130600] sysmon-qmi: ssctl_new_server: Connection established between QMI handle and adsp's SSCTL service
```

There is no WPSS/remoteproc running message, runtime device ID, WLAN QMI
service arrival, or radio firmware request in that output. `/sys/bus/platform/
drivers/icnss2/` has the bound `c800000.qcom,icnss` device. Its uevent reports
`DRIVER=icnss2`, `OF_NAME=qcom,icnss`, `OF_FULLNAME=/soc/qcom,icnss@C800000`,
and `OF_COMPATIBLE_0=qcom,icnss`. The node has write-only `wpss_boot` and
`wlan_en_delay` attributes. The local reference driver's `wpss_boot` handler
is WCN6750-only, but that attribute's existence alone does not show WPSS is
running; it was not written.

The live ICNSS properties are `compatible=qcom,icnss`,
`reg=<0x0c800000 0x00800000 0xb0000000 0x00010000>`,
`reg-names=membase,smmu_iova_ipa`, 12 interrupt entries (encoded GIC SPI
0x166–0x171), and IOMMU specifier `<0xa4 0x80 1>`. There is no
`qcom,rproc-handle`. Matching live-tree paths include ICNSS and the separate
WCN3990 Bluetooth node, but no WCN/WPSS/remoteproc node. The recovery driver
bound via `qcom,icnss`, which the local source maps to Adrastea ID `0xabcd`;
this is strong DT/driver-match evidence against standard WCN6750, not a
runtime silicon ID read.

The recovery image has no `/vendor/firmware_mnt/image` directory. I extracted
the contiguous `vendor_a` logical-partition extent from `super` to a host file
using read-only `adb exec-out dd`, then inspected its ext4 directory tree with
read-only `debugfs`; no device partition was mounted or changed. In `vendor_a`,
`/firmware_mnt` is empty (there is no `image/` or `adrastea/` directory), and
the only WLAN-specific vendor firmware entry is
`/firmware/wlan/qca_cld/WCNSS_qcom_cfg.ini`. No `wpss.mdt`, `wlanmdsp.mbn`,
`bdwlan.*`, `regdb.bin`, or `qca6750/` payload is present in that vendor
firmware tree. The separate `modem_a` partition is mounted read-only at
`/firmware`; its `/firmware/image` contains `wlanmdsp.mbn`, `bdwlan.bin`,
numerous `bdwlan.<board-id>` and `bdwlan.b<board-id>` files, plus
`bdwlanu.b65` and `bdwlanu.b69`. This confirms the image placement, not that
the Adrastea ICNSS path consumes or has loaded those modem-partition files.
The vendor boot DTB and both dtbo_a overlays were also inspected read-only:
they contain no WPSS/remoteproc node or Adrastea rproc handle. No
`/sys/class/remoteproc` is exposed in recovery.

Recovery has no `/sys/bus/pci/devices` directory; `/sys/bus/mmc/devices` is
empty. The two SDHCI hosts exist but declare `no-sdio` in the live DT. There
is no `wlan0` in `ifconfig -a`; `ip` and `iw` are unavailable. No matching
WPSS/WLAN/PCI/MSI memory regions appear in `/proc/iomem`. Thus recovery does
not provide a working radio reference and exposes no APSS PCI or SDIO
enumeration. The 0xc800000 ICNSS platform region is not a PCI host aperture.

The ICNSS supplier regulators all reported `disabled`, `num_users=0`, and
zero requested current in regulator sysfs. Their displayed microvolt values
are framework configuration metadata, not measured rail voltages. Four
regulator phandles are shared with the separate WCN3990 Bluetooth node. The
BT node has GPIO69 as `bt-sw-ctrl-gpio`; recovery reports missing
`bt-reset-gpio` and `wl-reset-gpio`. No WLAN enable GPIO is exposed in the
ICNSS node. Debugfs is unavailable (`cnss_utils: Unable to create debugfs
-19`), so GPIO line values, regulator debugfs summaries, and clock state
could not be read. No sysfs attributes or hardware controls were written.

## Linux bring-up sequence from the local reference driver

The reference `drivers/soc/qcom/icnss2` code recognizes WCN6750 (0x6750) and
Adrastea (0xabcd). The checked-in SM6375 source snapshot is older than the
public Android `wlan-platform` source inspected for this follow-up; use the
latter for Adrastea rproc and firmware-prefix behavior. For Adrastea, ICNSS2
provisions MSA memory, waits for the WLAN firmware QMI service, registers
indications, sends MSA memory-info, sends MSA-ready, requests capabilities,
then powers the ICNSS platform. Its server-arrival branch skips
`wlfw_host_cap`; the WCN6750/WCN6450 path sends host-cap instead. The local
recovery DT lacks `bdf-download-support`, so the Adrastea `cal_report`/BDF
download branch is not evidenced as enabled on VEUX.

The newer source defines `ADRASTEA_PATH_PREFIX` as `adrastea/`, but only uses
that prefix when the ICNSS DT node has the boolean `qcom,fw-prefix`. The live
VEUX ICNSS node does not have that property. When enabled, the prefix helper
applies to ICNSS firmware requests such as board-data and QDSS config; it does
not name the WPSS executable. ICNSS2 itself does not request `wpss.mdt` or
`wlanmdsp.mbn` in this flow. The WPSS image is selected by the separate
remoteproc node/backend. Therefore no exact Adrastea WPSS image filename or
`/vendor/firmware_mnt/image/adrastea/` contents are established for this
device. The Android `vendor_a` logical partition is not mounted in recovery;
we did not mount it or extract its filesystem. The only inspected firmware
directory remains the read-only `/firmware` view of `modem_a`, which contains
`wlanmdsp.mbn` and `bdwlan.*` but not an `adrastea/` directory or `wpss.mdt`.
Those modem-partition files do not prove that this ICNSS path loaded them.

For the optional Adrastea BDF request, enabling `bdf-download-support` selects
the BIN naming branch: board ID `0xff` produces `bdwlan.bin`; IDs below
`0x100` produce `bdwlanb<two-hex-digits>`; IDs `>=0x100` produce
`bdwlan<three-hex-digits>`. If `qcom,fw-prefix` is also set, the constructed
name is prefixed by `adrastea/`. The live VEUX node lacks both enabling
properties, so no such request/string is expected from this observed DT.
These are optional BDF names, not WPSS firmware names.

The newer ICNSS2 source does contain an Adrastea WPSS remoteproc option. It is
gated by the DT boolean `wpss-support-enable`; the loader reads the exact
`qcom,rproc-handle` property, calls `rproc_get_by_phandle()`, then
`rproc_boot()`. It does not find WPSS by name or compatible. In this source
the loader is scheduled by writing `1` to the `wpss_boot` sysfs attribute;
that attribute was not written. VEUX's live node has neither
`wpss-support-enable` nor `qcom,rproc-handle`, and the saved live DT has no
WPSS/remoteproc node. Recovery has no `/sys/class/remoteproc`. Thus this
specific source-controlled rproc boot path cannot be established as wired up
on VEUX. Whether a different proprietary recovery/modem service starts WPSS
is still unknown. This is source-derived behavior, cross-checked against the
runtime DT; it is not evidence that WPSS booted.

The exact standard WLFW QMI requests are service `0x45`, MSA_INFO request
`0x2d`, and MSA_READY request `0x2e`. MSA_INFO request payload has two QMI
TLVs: type `0x01`, an 8-byte little-endian MSA physical address, and type
`0x02`, a 4-byte MSA size. The successful response returns up to two memory
regions, each with address, size, and secure flag. MSA_READY has a zero-byte
request body and a normal QMI response. These IDs and shapes are source
derived; no WLFW server arrived in recovery. ios-topaz implements these two
messages already, but its state machine is
`ind_register -> host_cap -> MSA_INFO -> MSA_READY -> CAP`. VEUX's Adrastea
path must skip `host_cap` and enter MSA_INFO directly after indication
registration, then proceed to MSA_READY and CAP. Its MSA placement and secure
region assignment must be target-specific; Topaz's hard-coded values cannot
be copied.

The downstream QCA host-CMN Adrastea register definitions confirm 12 CEs. CE0
starts at ICNSS `membase + 0x240000` (`0x0ca40000` for the VEUX DT base
`0x0c800000`); CE1 is at `+0x241000`, consistent with 4 KiB per CE. This
confirms the Topaz patch's CE aperture and stride. The downstream QCA_WIFI_3_0
source/destination ring descriptors are four 32-bit words (16 bytes): low
buffer address; a control word containing the high address bits and flags;
length plus metadata; and Toeplitz result. Topaz's descriptor also occupies
16 bytes, but packs the address as a contiguous 64-bit field, so its layout
must not be assumed binary-compatible. Downstream source config reports no
Adrastea CE MSI registers; the live DT supplies 12 direct GIC interrupt
specifiers, encoded SPI values `0x166..0x171`. The `+0x32000` shadow window in
Topaz is a candidate implementation detail; the source register definitions
also distinguish APSS shadow/RRI registers and their exact offsets, so XNU
must use the Adrastea-specific register table rather than treating the whole
window as a generic shadow page.

On this phone, `/firmware/image/wlanmdsp.mbn` and the BDF family live in the
read-only `modem_a` partition, not the extracted `vendor_a` firmware tree.
Source inspection does not show ICNSS2 directly requesting `wlanmdsp.mbn` or
`wpss.mdt`: ICNSS2 requests BDF/QDSS files over `request_firmware()` and the
Adrastea BDF branch is disabled by the live DT; the optional WPSS path obtains
its image through the remoteproc/subsystem backend. The local SM6375 branch's
`wpss_boot` path calls `subsystem_get("wpss")` and is guarded for WCN6750;
the newer ICNSS2 source has a separate Adrastea remoteproc option gated by
`wpss-support-enable`, reading `qcom,rproc-handle` literally and calling
`rproc_get_by_phandle()`/`rproc_boot()`. VEUX's live DT, vendor boot DTB, and
overlays do not wire up that path. Recovery emitted no `wlanmdsp.mbn`,
`wlanfw`, or board-data load message. Thus the *file placement* is now
runtime-confirmed, but which component loads `wlanmdsp.mbn` for this target
remains unresolved. The clean runtime identity evidence would be the WLFW
capability response's chip/family ID and board ID; the shared `wlanfw`
service name is not identifying by itself.

For comparison, the separate WCN6750 path powers the platform, obtains device
info and maps firmware-returned BAR/MHI state, then sends `regdb.bin` and the
selected board-data BDF through WLFW QMI. The source names `bdwlan.bin`,
board-specific BDF variants, and `regdb.bin`; exact installed paths/payloads
must be captured from the target Android vendor image. Do not assume the
unrelated `ipa_fws.mdt` request is Wi-Fi firmware. No reset pulse width or
board-level regulator enable order has been established from recovery.

The WCN6750 rail list in this reference source specifies `vdd-cx-mx` at
824–952 mV, `vdd-1.8-xo` at 1.872 V, and `vdd-1.3-rfa` at 1.256–1.352 V;
the DT also exposes 3.3 V channel rails. These are driver constraints, not
proof of the board's actual enable order or measured voltage. The saved source
shows QMI firmware service and MHI state handling, but the exact firmware
boot handshake and reset timing require inspection of the matching ICNSS,
MHI, and firmware-service code plus target logs. This reference tree's
ICNSS2 and firmware service are not SWEET patches.

## SWEET and XNU status

SWEET has no Wi-Fi hardware driver or Wi-Fi bring-up patch. Its `sweet` XNU
patch set contains generic networking trace changes and unrelated network
plumbing, but no Qualcomm CNSS/ICNSS, WCN, PCIe WLAN, or SDIO WLAN initialization.
The VEUX XNU source has no Qualcomm PCIe root-complex, SDHCI, or ICNSS/SNOC
WLAN host driver. XNU IOKit contains generic PCI abstractions, which alone do
not enumerate a Qualcomm host or power a link. No Skywalk hardware hook for
this radio is present.

## Existing XNU Wi-Fi ports

HackiOS is structurally the closer starting point only if the runtime device
turns out to be WCN6750. Its published Wi-Fi port is more than ath11k plus
LinuxKPI:
the WCN6750-specific XNU side supplies SMEM/SMP2P, power/mailbox handling,
WPSS firmware loading and TrustZone start, GLINK/QRTR, QMI and WLFW, then
exposes the hybrid AHB/PCIe device to ath11k through `wifi/lx`. The public
HackiOS README documents WCN6750 operation and the `wpss.mdt`/segment firmware
inputs. It is a reference implementation for the exact candidate chip, but
its redwood SoC addresses, rails, GIC, SMMU, mailbox and firmware packaging
cannot be copied to VEUX.

ios-topaz's `TopazModem` patches (0113–0130) implement modem PAS boot, GLINK/
QRTR, WLFW, SNOC copy engines, and the WLAN data/control path on SM6225 topaz.
Its WLFW implementation uses the standard QMI service and message IDs and
implements `ind_register -> host_cap -> MSA info -> MSA ready -> capabilities`.
Adrastea uses the same MSA message pair but skips `host_cap`, so the Topaz
QMI state machine is the closer adaptable reference: the server-arrival
transition and MSA region parameters would need to change. It is not a
drop-in port. Topaz hardcodes its MSA base/size, secure VMIDs, modem PAS
layout, board-data policy, and WCN3988 CE/service map. Its CE aperture at
`0x0c800000 + 0x240000`, 12 engines, and 4 KiB stride match the downstream
Adrastea register definitions. Its ring descriptor encoding and shadow/RRI
register handling do not thereby become VEUX-compatible. The VEUX DT
independently confirms ICNSS membase `0x0c800000` size `0x00800000`, 12 direct
GIC CE interrupt specifiers `0x166–0x171`, and the IOMMU specifier. These are
SNOC/GIC resources, not PCI BARs/MSI. The QCA host-CMN configuration uses SNOC
for ICNSS/Adrastea; its CE programming model is memory-mapped ring registers
plus DMA descriptor rings, with the 12 CE interrupts routed directly to the
GIC.

Therefore ios-topaz is structurally closer than HackiOS for the DT-described
Adrastea target, at the WLFW protocol and SNOC HIF layers. HackiOS's
ath11k/LinuxKPI layer is downstream of WPSS startup, GLINK/QRTR/QMI and a
WCN6750-oriented AHB/PCIe path, none of which VEUX XNU currently exposes.
Topaz's GLINK/QRTR/QMI framing and MSA message codecs are adaptable, with the
Adrastea state transition and memory/VMID values changed; its CE ring layout
is not directly reusable without conversion to the downstream Adrastea
descriptor format. The single largest missing piece in VEUX XNU remains the
platform bootstrap that gets a WLFW service running and provides its MSA
memory. After that, the missing SNOC host layer must map/program the CE DMA
rings through the VEUX SMMU and handle its direct GIC interrupts. The live
recovery DT/rproc facts mean this is not currently a diagnostic-only MMIO
probe: the firmware service and powered CE block have not been demonstrated.

Do not select the WCN6750 `wifi/lx` path based only on the presence of the
generic `wpss_boot` sysfs attribute. ath11k/LinuxKPI comes later and cannot
discover or start this platform by itself.

## Diagnostic build decision

Do not report an XNU radio enumeration result yet: XNU currently has no
Adrastea/SNOC host driver that can perform one. Do not read arbitrary ICNSS
registers as a substitute; the CE offset map and clock/power state have not
been verified for VEUX. The DT identifies an ICNSS membase and CE interrupt
range, but not an APSS PCI host window. A meaningful first diagnostic should
be strictly read-only and should report separate outcomes for (1) host
controller found, (2) controller/link state accessible, (3) endpoint ID
read, (4) WLAN enable/reset pin state, and (5) rail/clock state. Unsupported
must be displayed explicitly as `NOT PROBED`, not as absent or powered off.

Remaining hardware questions are the runtime WLFW chip/family ID, whether
Android's full vendor image contains and starts matching radio firmware, and
the actual WLAN pin/clock states. The recovery-only data does not justify an
XNU diagnostic that claims to probe a radio endpoint: recovery exposes no
PCI/SDIO function, and XNU has no Adrastea WPSS/rproc bootstrap. A
future diagnostic must report these items as `NOT EXPOSED` or `NOT PROBED`,
not as a confirmed absent chip or measured-off rail. No Wi-Fi code, CI build,
image build, or partition write was made. Recovery was selected on slot A;
no image was written to boot_a or boot_b.

## Source references for the Adrastea follow-up

- [Android `wlan-platform` ICNSS2 main source](https://android.googlesource.com/kernel/msm-modules/wlan-platform/+/refs/heads/android-msm-eos-android13-wear-kr3-pixel-watch/icnss2/main.c)
  and [QMI source](https://android.googlesource.com/kernel/msm-modules/wlan-platform/+/refs/heads/android-msm-eos-android13-wear-kr3-pixel-watch/icnss2/qmi.c)
- [WLFW generated message definitions](https://android.googlesource.com/kernel/msm/+/fb60953788da42586b6ef4f982c4c97602efa281/drivers/net/wireless/cnss2/wlan_firmware_service_v01.h)
- [QCA host-CMN Adrastea register definitions](https://android.googlesource.com/kernel/msm/+/8158d57467c4332c1b144c5dc4cc21d5ade64ce6/drivers/staging/qca-wifi-host-cmn/hif/src/adrastea_reg_def.h), [CE descriptor definitions](https://android.googlesource.com/kernel/msm/+/efc684e83e29f4a8d0dd0f6cde762c78897f769a/drivers/staging/qca-wifi-host-cmn/hif/src/ce/ce_internal.h), and [Adrastea HIF selection](https://android.googlesource.com/kernel/msm/+/8158d57467c4332c1b144c5dc4cc21d5ade64ce6/drivers/staging/qca-wifi-host-cmn/hif/src/hif_main.c)
- [ios-topaz WLFW implementation](https://github.com/MakrSas/ios-topaz/blob/topaz/xnu/patches/0122-topaz-modem-wlfw.patch) and [SNOC WLAN/CE implementation](https://github.com/MakrSas/ios-topaz/blob/topaz/xnu/patches/0123-topaz-wlan-scan.patch)
