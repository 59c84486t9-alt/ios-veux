#!/usr/bin/env python3
"""Replace the SWEETXNU payload in a verified VEUX Android boot-v2 template."""

import argparse
import hashlib
from pathlib import Path
import struct


PAGE = 4096
HEADER_SIZE = 1660


def align(value: int) -> int:
    return (value + PAGE - 1) // PAGE * PAGE


def parse_template(data: bytes) -> tuple[int, int, bytes, bytes]:
    if data[:8] != b"ANDROID!":
        raise ValueError("template is not an Android boot image")

    kernel_size = struct.unpack_from("<I", data, 8)[0]
    ramdisk_size, second_size, page_size, version = struct.unpack_from(
        "<I4xI8xII", data, 16
    )
    if version != 2 or page_size != PAGE or second_size:
        raise ValueError("template must be boot v2 with 4096-byte pages and no second stage")

    recovery_size = struct.unpack_from("<I", data, 1632)[0]
    if recovery_size:
        raise ValueError("template must not contain a recovery DTBO")

    dtb_size = struct.unpack_from("<I", data, 1648)[0]
    kernel_offset = PAGE
    ramdisk_offset = kernel_offset + align(kernel_size)
    dtb_offset = ramdisk_offset + align(ramdisk_size)
    kernel = data[kernel_offset:kernel_offset + kernel_size]
    ramdisk = data[ramdisk_offset:ramdisk_offset + ramdisk_size]
    dtb = data[dtb_offset:dtb_offset + dtb_size]
    if len(kernel) != kernel_size or len(ramdisk) != ramdisk_size or len(dtb) != dtb_size:
        raise ValueError("template has truncated components")
    return kernel_size, ramdisk_size, kernel, dtb


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--dtb", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    template = args.template.read_bytes()
    payload = args.payload.read_bytes()
    dtb = args.dtb.read_bytes()
    if payload[:8] != b"SWEETXNU":
        parser.error("payload is not a SWEETXNU image")
    if len(template) < PAGE or len(template) < HEADER_SIZE:
        parser.error("template is truncated")

    _kernel_size, _ramdisk_size, kernel, template_dtb = parse_template(template)
    if template_dtb != dtb:
        parser.error("DTB does not match the template")

    header = bytearray(template[:PAGE])
    struct.pack_into("<I", header, 16, len(payload))
    digest = hashlib.sha1()
    for component in (kernel, payload, b"", dtb):
        digest.update(component)
        digest.update(struct.pack("<I", len(component)))
    header[576:608] = digest.digest() + bytes(12)

    output = bytearray(header)
    for component in (kernel, payload, dtb):
        output += component
        output += bytes(align(len(component)) - len(component))
    args.output.write_bytes(output)

    print(f"output: {args.output}")
    print(f"size: {len(output)}")
    print(f"payload_sha256: {hashlib.sha256(payload).hexdigest()}")
    print(f"wrapper_sha256: {hashlib.sha256(output).hexdigest()}")


if __name__ == "__main__":
    main()
