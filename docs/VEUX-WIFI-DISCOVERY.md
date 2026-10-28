# VEUX Wi-Fi discovery: current evidence and safe next step

Collected 2026-10-28 from the saved recovery device tree, archived recovery
logs, the local SM6375 reference kernel, and the XNU build tree. The reference
kernel is the community `kernel_xiaomi_sm6375` checkout; it is not established
as the exact source for the installed Paimon recovery kernel.

## Hardware identification

The recovery live DT contains `/soc/qcom,icnss@C800000`, with `compatible =
"qcom,icnss"`, `reg = <0x0c800000 0x00800000 0xb0000000 0x00010000>`, and
`reg-names = "membase", "smmu_iova_ipa"`. In the local Qualcomm vendor
binding, `qcom,icnss` denotes the Adrastea architecture; `qcom,wcn6750`
denotes iWCN. The local SM6375 reference driver's OF match table maps
`qcom,icnss` to `ADRASTEA_DEVICE_ID` (`0xabcd`) and `qcom,wcn6750` to
`WCN6750_DEVICE_ID` (`0x6750`). Thus the live DT strongly identifies an
Adrastea-style ICNSS configuration and argues against a standard WCN6750
configuration. It does not prove the physical package marking or the runtime
ID because recovery is not currently attached.

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

The archived recovery log contains:

- `icnss2 c800000.qcom,icnss: Adding to iommu group 8`
- `icnss2: Recursive recovery allowed for WLAN`
- `icnss2: Platform driver probed successfully`
- `ipa ... ipa_smmu_wlan: Adding to iommu group 3`
- SDHCI host registration at 0x04744000 and 0x04784000
- `bt-reset-gpio not provided in devicetree` and `wl-reset-gpio not provided in device tree`

This establishes Linux platform-driver binding for ICNSS2, not that WLAN
firmware booted or the radio enumerated. The saved log has no WPSS/remoteproc
running message, WLAN/QMI server arrival, radio firmware request, or PCI
device vendor/device ID. The only observed firmware failures in this excerpt
are unrelated `ipa_fws.mdt` requests. No recovery `wlan0`/`iw`/`lspci` output,
regulator debugfs dump, live GPIO value dump, ICNSS sysfs `uevent`, or
`/vendor/firmware_mnt/image` listing is archived. The phone is currently
absent from both ADB and Fastboot, so those requested live checks could not be
rerun.

## Linux bring-up sequence from the local reference driver

The reference `drivers/soc/qcom/icnss2` code recognizes WCN6750 (0x6750) and
Adrastea (0xabcd). For WCN6750 it obtains the ICNSS power rails and RF clock,
waits for the WLAN firmware service/QMI server, exchanges WLFW capability and
host-capability messages, powers the platform, obtains device info and maps
the returned memory/BAR and MHI state information, then sends `regdb.bin` and
the selected board-data BDF through WLFW QMI. The default BDF type is set in
ICNSS driver control parameters; the filename depends on ID and board data.
The source names `bdwlan.bin`, board-specific BDF variants, and `regdb.bin`;
exact installed paths/payloads must be captured from the target recovery's
firmware requests or mounted vendor firmware. Do not assume the unrelated
`ipa_fws.mdt` request is Wi-Fi firmware.

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
The VEUX XNU source likewise has no Qualcomm PCIe root-complex or SDHCI host
driver. XNU IOKit contains generic PCI device abstractions, which alone do not
enumerate a Qualcomm host or power a link. No Skywalk hardware hook for this
radio is present.

## Existing XNU Wi-Fi ports

HackiOS is structurally the closer starting point if the runtime device turns
out to be WCN6750. Its published Wi-Fi port is more than ath11k plus LinuxKPI:
the WCN6750-specific XNU side supplies SMEM/SMP2P, power/mailbox handling,
WPSS firmware loading and TrustZone start, GLINK/QRTR, QMI and WLFW, then
exposes the hybrid AHB/PCIe device to ath11k through `wifi/lx`. The public
HackiOS README documents WCN6750 operation and the `wpss.mdt`/segment firmware
inputs. It is a reference implementation for the exact candidate chip, but
its redwood SoC addresses, rails, GIC, SMMU, mailbox and firmware packaging
cannot be copied to VEUX.

ios-topaz's `TopazModem` patches (0113–0130) implement modem/WLFW/QMI/GLINK/
QRTR services on SM6225 topaz. That is useful protocol-level reference if
VEUX's Adrastea setup needs the same WLAN firmware service, but it is not the
same SoC or proven same radio architecture. It does not supply VEUX's
ICNSS/WPSS device support.

The single largest missing piece for either route is the VEUX-specific
Qualcomm remote WLAN host stack: establish and power the actual Adrastea/iWCN
target, load/start its remote firmware if required, and implement the
SMEM/SMP2P + mailbox + GLINK/QRTR + QMI/WLFW control path. ath11k/LinuxKPI
comes later and cannot discover or start this platform by itself. Given the
DT mismatch, do not choose the WCN6750 `wifi/lx` path until recovery runtime
identifies the chip and confirms WPSS and firmware-service behavior.

## Diagnostic build decision

Do not report an XNU enumeration result yet: XNU currently has no host driver
that can perform one. Do not read arbitrary ICNSS or PCIe registers as a
substitute; the saved device tree does not identify a confirmed PCIe host
window or a safe clocked register set. A meaningful first diagnostic should
be strictly read-only and should report separate outcomes for (1) host
controller found, (2) controller/link state accessible, (3) endpoint ID
read, (4) WLAN enable/reset pin state, and (5) rail/clock state. Unsupported
must be displayed explicitly as `NOT PROBED`, not as absent or powered off.

To settle the remaining runtime questions, reconnect VEUX to recovery with
`adb root` and capture the full requested WLAN/ICNSS/WPSS dmesg, bound
`icnss2` sysfs device and `uevent`, matching device-tree nodes and phandle
targets, firmware directory listing, `/sys/bus/pci/devices`,
`/sys/bus/mmc/devices`, `ip link`, `iw dev`, `/proc/iomem`, regulator debugfs,
and GPIO debugfs. Then compare the runtime silicon ID with the DT-derived
Adrastea-style identity before making any driver choice. No image was built or
flashed for Wi-Fi in this investigation.
