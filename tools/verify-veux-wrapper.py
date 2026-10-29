#!/usr/bin/env python3
"""Verify a host-packed Android boot-v2 image against its exact CI kernel."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mkpayload  # noqa: E402


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def unpack_v2(data: bytes) -> dict[str, bytes | str]:
    if data[:8] != b"ANDROID!":
        raise ValueError("wrapper is not an Android boot image")
    ks, _ka, rs, _ra, ss, _sa, _ta, page, version, _osv = struct.unpack_from("<10I", data, 8)
    if version != 2 or page < 4096:
        raise ValueError(f"expected Android boot header v2, got version={version}, page={page}")
    offset = page
    kernel = data[offset:offset + ks]
    offset += (ks + page - 1) // page * page
    ramdisk = data[offset:offset + rs]
    offset += (rs + page - 1) // page * page
    second = data[offset:offset + ss]
    offset += (ss + page - 1) // page * page
    recovery_size, recovery_off, _header_size = struct.unpack_from("<IQI", data, 1632)
    if recovery_size:
        offset = max(offset, recovery_off + recovery_size)
        offset = (offset + page - 1) // page * page
    dtb_size, _dtb_addr = struct.unpack_from("<IQ", data, 1648)
    dtb = data[offset:offset + dtb_size]
    if len(kernel) != ks or len(ramdisk) != rs or len(dtb) != dtb_size:
        raise ValueError("truncated boot-v2 component")
    cmdline = (data[64:576].split(b"\0", 1)[0] + data[608:1632].split(b"\0", 1)[0]).decode("utf-8", "replace")
    return {"kernel": kernel, "ramdisk": ramdisk, "second": second, "dtb": dtb, "cmdline": cmdline}


ap = argparse.ArgumentParser()
ap.add_argument("--image", required=True, type=Path)
ap.add_argument("--payload", required=True, type=Path)
ap.add_argument("--ci-kernel", required=True, type=Path)
ap.add_argument("--dtb", required=True, type=Path)
ap.add_argument("--boot-args", required=True)
ap.add_argument("--build-id", required=True)
ap.add_argument("--run-id", required=True)
ap.add_argument("--patch-status", required=True, type=Path)
ap.add_argument("--manifest", type=Path)
ap.add_argument("--variants-manifest", type=Path, help="kernel manifest containing both full boot-arg strings")
ap.add_argument("--variant", choices=("normal", "held", "modem-held"))
a = ap.parse_args()
if a.build_id != a.run_id:
    raise SystemExit("build ID must equal the CI run ID")

image = a.image.read_bytes()
parts = unpack_v2(image)
payload = a.payload.read_bytes()
kernel = a.ci_kernel.read_bytes()
dtb = a.dtb.read_bytes()
embedded_payload = parts["ramdisk"]
if embedded_payload != payload:
    raise SystemExit("wrapper ramdisk payload differs from the supplied verified payload")
if parts["dtb"] != dtb:
    raise SystemExit("wrapper DTB differs from the supplied phone DTB")
if not isinstance(embedded_payload, bytes) or embedded_payload[:8] != b"SWEETXNU":
    raise SystemExit("wrapper ramdisk is not a SWEETXNU payload")
_magic, _version, _nsegs = struct.unpack_from("<8sII", embedded_payload, 0)
_virt, _entry, adt_off, adt_size, _kend, _phys, _mem = struct.unpack_from("<7Q", embedded_payload, 0x10)
payload_args = embedded_payload[0x48:0x48 + 608].split(b"\0", 1)[0].decode("utf-8", "replace")
if payload_args != a.boot_args:
    raise SystemExit(f"payload boot args mismatch: expected {a.boot_args!r}, got {payload_args!r}")
if a.variant == "modem-held":
    expected = "debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam -noprogress rd=ufsroot0 modem=1 modem_watch=180 veuxfbconsole=1"
    if payload_args != expected:
        raise SystemExit("modem-held wrapper boot args do not match the exact Phase-1 string")
    forbidden = {"rootrw", "ufsrw", "veuxlog", "veux_gui", "veuxsandbox", "veuxiolog",
                 "veux_spawn_driver", "veuxgpipreflight", "veuxtouchprobe"}
    if any(arg.split("=", 1)[0] in forbidden for arg in payload_args.split()):
        raise SystemExit("modem-held wrapper contains a forbidden boot argument")
variant_manifest = None
if a.variants_manifest:
    variant_manifest = json.loads(a.variants_manifest.read_text())
    variants = variant_manifest.get("variants", {})
    if set(variants) not in ({"normal", "held"}, {"normal", "held", "modem-held"}):
        raise SystemExit("variants manifest must contain normal, held, and optional modem-held entries")
    if a.variant == "modem-held" and set(variants) != {"normal", "held", "modem-held"}:
        raise SystemExit("modem-held wrapper requires the three-variant kernel manifest")
    if not a.variant:
        raise SystemExit("--variant is required with --variants-manifest")
    if variants[a.variant].get("boot_args") != payload_args:
        raise SystemExit(f"payload arguments do not match the {a.variant} boot-argument manifest")
adt_blob = embedded_payload[adt_off:adt_off + adt_size]
# Rebuild through the normal packer using the exact ADT carried by the payload.
with tempfile.NamedTemporaryFile(prefix="veux-adt-", suffix=".tmp", dir=a.image.parent) as tmp:
    tmp.write(adt_blob)
    tmp.flush()
    rebuilt, _info = mkpayload.build(str(a.ci_kernel), tmp.name, a.boot_args)
if rebuilt != payload:
    raise SystemExit("payload segments do not reconstruct byte-for-byte from the CI kernel and embedded ADT")
build_marker = f"VEUX BUILD: ID={a.build_id}".encode()
if build_marker not in kernel:
    raise SystemExit("CI kernel lacks the expected screen/ring build ID")
if a.variant == "modem-held":
    required = (
        b"VEUX MODEM PAS: pas_id=4 carveout=0x8b800000+0x10000000 smem=0x80900000 tcsr=0x00340000 hwlock=3",
        b"VEUX IPCC: pa=0x00208000 mpss=2 smp2p=2 glink_qmp=0 gic_spi=334",
        b"VEUX MODEM: SMP2P READY", b"VEUX GLINK: VERSION_ACK",
        b"VEUX GLINK: OPEN_ACK IPCRTR", b"VEUX QRTR: HELLO",
        b"VEUX QRTR: NEW_SERVER 0x45", b"VEUX WLFW: ind_register ok",
        b"VEUX WLFW: msa_info ok", b"VEUX WLFW: msa_ready ok",
        b"VEUX WLFW: cap ok", b"VEUX WLFW: chip_id",
        b"VEUX MODEM HOLD: wfe",
    )
    missing = [marker.decode("ascii") for marker in required if marker not in kernel]
    if missing:
        raise SystemExit("CI kernel lacks modem markers: " + ", ".join(missing))
    forbidden_markers = (
        b"VEUX WLFW: host_cap sent", b"VEUX WLFW: bdf", b"VEUX WLFW: cal_report",
        b"VEUX WLFW: wlan_cfg", b"VEUX WLFW: wlan_mode", b"VEUX CE:",
        b"VEUX HTC:", b"VEUX WMI:", b"VEUX SCAN:",
    )
    present = [marker.decode("ascii") for marker in forbidden_markers if marker in kernel]
    if present:
        raise SystemExit("CI kernel contains forbidden modem markers: " + ", ".join(present))
status = a.patch_status.read_text().splitlines()
manifest_path = a.manifest or a.image.with_suffix(a.image.suffix + ".manifest.json")
manifest = {
    "ci_run_id": a.run_id,
    "build_id": a.build_id,
    "kernel_sha256": sha256(kernel),
    "payload_sha256": sha256(payload),
    "wrapper_sha256": sha256(image),
    "dtb_sha256": sha256(dtb),
    "boot_args": payload_args,
    "variant": a.variant,
    "variants": variant_manifest.get("variants") if variant_manifest else None,
    "payload_matches_ci_kernel_and_embedded_adt": True,
    "wrapper_payload_matches_verified_payload": True,
    "wrapper_dtb_matches_phone_dtb": True,
    "patch_status": status,
}
manifest_path.parent.mkdir(parents=True, exist_ok=True)
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
print(f"VEUX BUILD ID: {a.build_id}")
print(f"CI run: {a.run_id}")
print(f"kernel SHA-256: {manifest['kernel_sha256']}")
print(f"wrapper SHA-256: {manifest['wrapper_sha256']}")
print(f"DTB SHA-256: {manifest['dtb_sha256']}")
print(f"boot args: {payload_args}")
print(f"manifest: {manifest_path}")
