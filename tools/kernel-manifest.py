#!/usr/bin/env python3
"""Verify required VEUX features in a built kernel and emit build evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ap = argparse.ArgumentParser()
ap.add_argument("--kernel", required=True, type=Path)
ap.add_argument("--patch-status", required=True, type=Path)
ap.add_argument("--build-id", required=True)
ap.add_argument("--boot-args", required=True)
ap.add_argument("--output", required=True, type=Path)
a = ap.parse_args()

kernel = a.kernel.read_bytes()
status = a.patch_status.read_text().splitlines()
if any("FAILED" in line or "SKIPPED" in line for line in status):
    raise SystemExit("patch status contains a failure or skip")
if not any(line.startswith("PATCH_STATUS: 0117-veux-post-early-boot-liveness.patch APPLIED") for line in status):
    raise SystemExit("0117 liveness patch was not recorded as applied")
if not any(line.startswith("PATCH_STATUS: 0118-veux-stop-mountroot-retries.patch APPLIED") for line in status):
    raise SystemExit("0118 no-retry patch was not recorded as applied")

needles = {
    "build_id_on_console_and_ring": f"VEUX BUILD: ID={a.build_id}".encode(),
    "process_sampler": b"VEUX LIVE: processes=",
    "mount_failure_no_retry": b"VEUX MOUNTROOT: failure; no retry",
    "ufs_flush_symbol": b"veux_log_flush_sync",
    "ufs_first_write_marker": b"first successful UFS write",
    "panic_region": b"VEUX EARLY PANIC:",
    "panic_console_tail_symbol": b"veux_fb_panic_console_tail",
}
checks = {name: needle in kernel for name, needle in needles.items()}
missing = [name for name, passed in checks.items() if not passed]
if missing:
    raise SystemExit("kernel manifest checks failed: " + ", ".join(missing))

image = None
image_note = "Android boot-v2 wrapper is assembled on the host from the verified kernel payload and device DTB; CI has no device DTB input."
manifest = {
    "build_id": a.build_id,
    "patch_status": status,
    "string_checks": checks,
    "kernel": str(a.kernel),
    "kernel_sha256": hashlib.sha256(kernel).hexdigest(),
    "boot_image_sha256": image,
    "boot_image_note": image_note,
    "boot_args": a.boot_args,
}
a.output.parent.mkdir(parents=True, exist_ok=True)
a.output.write_text(json.dumps(manifest, indent=2) + "\n")
print(f"VEUX BUILD ID: {a.build_id}")
print(f"kernel_sha256={manifest['kernel_sha256']}")
print("boot_image_sha256=NOT_PACKAGED_IN_CI")
print(a.output)
