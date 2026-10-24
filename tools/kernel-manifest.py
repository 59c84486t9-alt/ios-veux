#!/usr/bin/env python3
"""Verify required VEUX features in the final kernel and write build evidence."""
import argparse
import hashlib
import json
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--kernel", required=True, type=Path)
ap.add_argument("--patch-status", required=True, type=Path)
ap.add_argument("--build-id", required=True)
ap.add_argument("--boot-args", required=True)
ap.add_argument("--source-root", required=True, type=Path)
ap.add_argument("--output", required=True, type=Path)
a = ap.parse_args()

kernel = a.kernel.read_bytes()
status = a.patch_status.read_text().splitlines()
bad = [line for line in status if " FAILED" in line or "ALLOWLIST_STALE" in line]
if bad:
    raise SystemExit("patch status contains failed/stale entries: " + "; ".join(bad))
for patch in (
    "0111-veux-readonly-hfs-and-ufs-read-markers.patch",
    "0113-veux-panic-console-tail.patch",
    "0114-veux-mount-ufs-write-diagnostics.patch",
    "0117-veux-post-early-boot-liveness.patch",
    "0118-veux-stop-mountroot-retries.patch",
):
    if not any(line.startswith(f"PATCH_STATUS: {patch} APPLIED") for line in status):
        raise SystemExit(f"required patch was not applied: {patch}")

needles = {
    "build_id_screen_and_ring": f"VEUX BUILD: ID={a.build_id}".encode(),
    "process_sampler": b"VEUX LIVE: processes=",
    "panic_region_marker": b"VEUX EARLY PANIC:",
    "panic_console_tail_header": b"Last console lines (oldest first; includes mount output):",
    "panic_console_tail_symbol": b"veux_fb_panic_console_tail",
    "mount_helper_start": b"VEUX MOUNT helper start name=",
    "mount_helper_exit": b"VEUX MOUNT helper exit raw-status=",
    "root_mount_result": b"VEUX ROOT mount result errno=",
    "root_mode_and_ro_default": b"VEUX ROOT mode=%s ufs_write=%s (read-only default; rw requires rootrw=1 and ufsrw=1)",
    "rootrw_boot_arg": b"rootrw",
    "ufsrw_boot_arg": b"ufsrw",
    "ufs_first_write_success": b"VEUX UFS: first successful UFS write",
    "ufs_first_write_failure": b"VEUX UFS: first UFS write failure error=",
    "mount_failure_no_retry": b"VEUX MOUNTROOT: failure; no retry errno=",
    "readonly_root_journal_guard": b"VEUX HFS: read-only root journal replay disabled",
    "synchronous_ufs_ring_flush": b"veux_log_flush_sync",
}
checks = {name: needle in kernel for name, needle in needles.items()}
source_checks = {}
vfs = (a.source_root / "bsd/vfs/vfs_subr.c").read_text()
ufs = (a.source_root / "bsd/dev/sweet_ufs.c").read_text()
root_alloc = vfs.split("vfs_rootmountalloc_internal(struct vfstable *vfsp", 1)[1].split("vfs_rootmountalloc(", 1)[0]
source_checks["root_mount_starts_read_only"] = "mp->mnt_flag = MNT_RDONLY | MNT_ROOTFS;" in root_alloc
mountroot = vfs.split("vfs_mountroot(void)", 1)[1]
rootrw_block = mountroot.split('PE_parse_boot_argn("rootrw", &rootrw, sizeof(rootrw))', 1)
source_checks["rootrw_only_clears_readonly_when_one"] = (
    len(rootrw_block) == 2
    and "uint32_t rootrw = 0;" in mountroot
    and "&& rootrw)" in rootrw_block[1][:100]
    and "mp->mnt_flag &= ~MNT_RDONLY;" in rootrw_block[1][:180]
)
source_checks["ufsrw_defaults_off_and_requires_one"] = (
    "uint32_t rw = 0;" in ufs
    and
    'PE_parse_boot_argn("ufsrw", &rw, sizeof(rw));' in ufs
    and "su.writable = (rw == 1);" in ufs
)
if not all(source_checks.values()):
    raise SystemExit("rootrw/ufsrw source policy check failed: " + repr(source_checks))
missing = [name for name, passed in checks.items() if not passed]
if missing:
    raise SystemExit("kernel manifest checks failed: " + ", ".join(missing))

allowlisted_skips = []
for line in status:
    prefix = "PATCH_STATUS: "
    marker = " ALLOWLISTED_SKIP (reason: "
    if line.startswith(prefix) and marker in line:
        patch_name, rest = line[len(prefix):].split(marker, 1)
        reason = rest.split("; detail:", 1)[0].rstrip(")")
        patch_id = patch_name.split("-", 1)[0]
        allowlisted_skips.append({
            "display": f"allowlisted skip: {patch_id} ({reason})",
            "patch_id": patch_id,
            "patch": patch_name,
            "reason": reason,
        })
if not any(item["patch_id"] == "0031" for item in allowlisted_skips):
    raise SystemExit("manifest requires the explicit 0031 allowlisted skip record")

manifest = {
    "build_id": a.build_id,
    "patch_status": status,
    "allowlisted_skips": allowlisted_skips,
    "string_checks": checks,
    "source_policy_checks": source_checks,
    "kernel_sha256": hashlib.sha256(kernel).hexdigest(),
    "kernel_path": str(a.kernel),
    "boot_args": a.boot_args,
    "wrapper": "assembled on host with the phone DTB; see adjacent wrapper manifest",
}
a.output.parent.mkdir(parents=True, exist_ok=True)
a.output.write_text(json.dumps(manifest, indent=2) + "\n")
print(f"VEUX BUILD ID: {a.build_id}")
print(f"kernel_sha256={manifest['kernel_sha256']}")
print(a.output)
