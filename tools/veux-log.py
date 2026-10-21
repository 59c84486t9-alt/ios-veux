#!/usr/bin/env python3
"""Decode the VEUX XNU console ring from the final userdata blocks."""
import argparse
import struct
import sys
from pathlib import Path

HEADER_SIZE = 4096
MAGIC = b"VEUXLOG1"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("area", type=Path, help="raw 4 MiB + 4 KiB ring dump")
    parser.add_argument("output", nargs="?", type=Path, help="text output (default: stdout)")
    args = parser.parse_args()

    data = args.area.read_bytes()
    if len(data) < HEADER_SIZE:
        parser.error("dump is shorter than one UFS block")
    magic, version, ring_size, total, sequence = struct.unpack_from("<8sIIQQ", data)
    if magic != MAGIC or version != 1:
        sys.exit("no VEUXLOG1 header (logger did not flush, or wrong block range)")
    if ring_size == 0 or ring_size > len(data) - HEADER_SIZE:
        sys.exit("invalid ring size in header")

    ring = data[HEADER_SIZE:HEADER_SIZE + ring_size]
    if total <= ring_size:
        payload = ring[:total]
    else:
        start = total % ring_size
        payload = ring[start:] + ring[:start]
    text = payload.decode("utf-8", "replace").replace("\r", "")
    print(f"# VEUX XNU log: {total} bytes, flush {sequence}"
          f"{' (ring wrapped; oldest output was overwritten)' if total > ring_size else ''}",
          file=sys.stderr)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
