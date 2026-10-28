# VEUX Wi-Fi discovery: current evidence and safe next step

Collected 2026-10-28 from the saved recovery device tree, archived recovery
logs, the local SM6375 reference kernel, and the XNU build tree. The reference
kernel is the community `kernel_xiaomi_sm6375` checkout; it is not established
as the exact source for the installed Paimon recovery kernel.

## Hardware identification

The recovery live DT contains `/soc/qcom,icnss@C800000`, with `compatible =
"qcom,icnss"`, `reg = <0x0c800000 0x00800000 0xb0000000 0x00010000>`, and
`reg-names = "membase", "smmu_iova_ipa"`. Its supplies are `vdd-cx-mx`,
`vdd-1.8-xo`, `vdd-1.3-rfa`, `vdd-smps`, `vdd-3.3-ch0`, and
`vdd-3.3-ch1`. It has GIC interrupts 0x166–0x171 (decimal 358–369), an
SMMU reference, and a WLAN SMP2P crash/error input. The source ICNSS2 driver
supports WCN6750 and Adrastea IDs. The saved live DT says only `qcom,icnss`,
not `qcom,wcn6750`; therefore the ICNSS node is confirmed, while the exact
radio model is not confirmed by that property alone. WCN6750 is a plausible
board-level candidate, not a ground-truth result yet.

The live tree also contains a separate `qcom,wcn3990` Bluetooth node. Its
`qcom,bt-sw-ctrl-gpio` tuple is `<0xa7 0x45 0>`, i.e. GPIO 69 using the
referenced TLMM controller. The recovery log reports that `bt-reset-gpio` and
`wl-reset-gpio` were not provided. No dedicated WLAN_EN GPIO appears in the
saved ICNSS properties. Do not equate the Bluetooth switch-control GPIO with
WLAN enable or reset.

The two SDHCI hosts are at `0x04744000` (DT interrupt cells `0x15c` and
`0x160`) and `0x04784000` (cells `0x15e` and `0x161`). Both have `no-sdio`;
the first also has `no-sd`, and the
second has `no-mmc`. Recovery logged `mmc0` and `mmc1` as ADMA 64-bit hosts,
but neither is an SDIO WLAN interface. The live DT archive has no PCI/PCIe
host node. The ICNSS block is at `0x0c800000`; do not call that address a PCIe
root-complex address. Linux's ICNSS/WCN6750 path uses QMI and MHI-related
resources, with remote WCSS firmware, rather than a normal SDIO function.
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
firmware booted or the radio enumerated. The saved log has no WLAN/QMI server
arrival, no radio firmware request, and no PCI device vendor/device ID. The
only observed firmware failures in this excerpt are unrelated `ipa_fws.mdt`
requests. No recovery regulator debugfs dump or live GPIO value dump is
present in the available files, and the device is currently absent from both
ADB and Fastboot.

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

## Diagnostic build decision

Do not report an XNU enumeration result yet: XNU currently has no host driver
that can perform one. Do not read arbitrary ICNSS or PCIe registers as a
substitute; the saved device tree does not identify a confirmed PCIe host
window or a safe clocked register set. A meaningful first diagnostic should
be strictly read-only and should report separate outcomes for (1) host
controller found, (2) controller/link state accessible, (3) endpoint ID
read, (4) WLAN enable/reset pin state, and (5) rail/clock state. Unsupported
must be displayed explicitly as `NOT PROBED`, not as absent or powered off.

To complete that diagnostic, reconnect VEUX to recovery with `adb root` and
capture `lspci -vvv` (if available), `/sys/bus/pci/devices`,
`/sys/bus/mmc/devices`, WLAN-related `dmesg`, `/sys/kernel/debug/regulator`,
`/sys/kernel/debug/gpio`, and ICNSS platform sysfs/uevent state. Then establish
the exact VEUX downstream `veux.dtsi` / `sm6375.dtsi` source revision or
decode the live DT nodes and their phandle targets. Once the actual host and
safe read-only register set are confirmed, add the diagnostic through strict
CI/manifest and boot the verified candidate from `boot_b` only. No image was
built or flashed for Wi-Fi in this investigation.
