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

The recovery image has no `/vendor/firmware_mnt/image` directory. Its visible
`/vendor/firmware` contains Goodix touchscreen files only; no `qca6750`,
`wpss.mdt`, `bdwlan.*`, or `regdb.bin` files were found there. The Android
`vendor_a` logical partition is inside `super` and is not mounted in this
recovery; it was not mistaken for the recovery `/vendor`. The separate
`modem_a` partition is mounted read-only at `/firmware`. Its `/firmware/image`
contains `wlanmdsp.mbn`, `bdwlan.bin`, numerous `bdwlan.<board-id>` and
`bdwlan.b<board-id>` files, plus `bdwlanu.*`; no `adrastea/` or `wpss.mdt`
path was found. These files show a WLAN firmware/BDF package is present in
the modem partition, but do not establish which chip uses it or that it has
loaded. No `/sys/class/remoteproc` is exposed.

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
Adrastea (0xabcd). For the DT-selected Adrastea path, ICNSS2 provisions MSA
memory, waits for the WLAN firmware QMI service, registers indications, sends
MSA memory-info, sends MSA-ready, requests capabilities, then powers the
ICNSS platform and continues the WLFW exchange. The key server-arrival branch
skips `wlfw_host_cap` for Adrastea; WCN6750 sends host-cap and follows its
device-info/BAR/MHI path. The `wpss_boot` sysfs control is WCN6750-only in
this source. The Adrastea ICNSS2 branch does not directly request `wlanmdsp`
or BDF files; its QMI client expects the firmware service to have been
started by the separate modem/remote-subsystem path. In this local tree,
`request_firmware()` is used by BDF/QDSS download helpers, but the server
arrival path calls BDF download only for WCN6750. Thus this source alone does
not define an Adrastea executable filename or directory.

On this phone the read-only modem partition supplies
`/firmware/image/wlanmdsp.mbn` and board-data `bdwlan.*` files. The most likely
downstream boot path is therefore the modem/WLAN subsystem loader starting a
WLAN firmware domain, after which ICNSS2 performs the MSA/QMI handshake. That
association is an inference from the file placement and the Q6-based ICNSS
binding, not a confirmed loader trace. Recovery emitted no `wlanmdsp.mbn`,
`wlanfw`, or board-data load message. The single clean runtime identity
evidence would be the WLFW capability response's reported chip ID/family
(and board ID); the `wlanfw` service name is shared and is not identifying by
itself.

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
layout, board-data policy, and WCN3988 CE/service map. Its SNOC CE routine
maps registers at `0x0c800000 + 0x240000`, 12 engines at 4 KiB strides, and
shadow registers at `0x0c832000`; that is a useful candidate map, not yet
verified against VEUX's exact CE offsets. The VEUX DT independently confirms
ICNSS membase `0x0c800000` size `0x00800000`, 12 direct GIC CE interrupt
specifiers `0x166–0x171`, and the IOMMU specifier. These are SNOC/GIC
resources, not PCI BARs/MSI. The QCA host-CMN configuration uses SNOC for
ICNSS/Adrastea; its CE programming model is memory-mapped ring registers plus
DMA descriptor rings, with the 12 CE interrupts routed directly to the GIC.

Therefore ios-topaz is structurally closer than HackiOS for the DT-described
Adrastea target, at both the WLFW protocol and SNOC HIF layers. The single
largest missing piece in VEUX XNU is the VEUX-specific WLAN platform host
stack: safely start the modem/WLAN firmware service, allocate/assign its MSA
regions, then map/program the Adrastea SNOC CE/DMA and GIC interrupts. There
is no existing VEUX implementation of that path. The Topaz QMI and CE code is
an adaptable reference, but the hardware parameters and boot flow need
independent confirmation from a live WLFW capability response and downstream
HIF configuration.

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

Remaining hardware questions are the physical silicon/runtime ID, whether
Android's full vendor image contains and starts matching radio firmware, and
the actual WLAN pin/clock states. The recovery-only data does not justify an
XNU diagnostic that claims to probe a radio endpoint: recovery exposes no
PCI/SDIO function, and XNU has no verified Adrastea SNOC CE map. A
future diagnostic must report these items as `NOT EXPOSED` or `NOT PROBED`,
not as a confirmed absent chip or measured-off rail. No Wi-Fi code, CI build,
image build, or partition write was made. Recovery was selected on slot A;
no image was written to boot_a or boot_b.
