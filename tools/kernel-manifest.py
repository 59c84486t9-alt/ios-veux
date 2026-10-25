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

boot_args = set(a.boot_args.split())
if not {"rootrw=1", "ufsrw=1"}.issubset(boot_args):
    raise SystemExit("VEUX build manifest requires the explicit rootrw=1 ufsrw=1 experiment args")
if "veuxlog=1" in boot_args:
    raise SystemExit("VEUX build manifest refuses veuxlog=1 because its userdata-tail range may overlap HFS+")

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
    "0119-veux-require-explicit-rw-pair.patch",
    "0120-veux-unconditional-early-console-build-id.patch",
    "0121-veux-launchd-main-stack-exec-trace.patch",
):
    if not any(line.startswith(f"PATCH_STATUS: {patch} APPLIED") for line in status):
        raise SystemExit(f"required patch was not applied: {patch}")

needles = {
    "build_id_screen_and_ring": f"VEUX BUILD: ID={a.build_id}".encode(),
    "early_framebuffer_console_entry": b"VEUX simplefb console 1080x2400 stride=4320 format=a8r8g8b8",
    "process_sampler": b"VEUX LIVE: processes=",
    "launchd_thread_wait_classifier": b"VEUX WAIT: launchd threads=",
    "waitq_kind_classifier": b"waitq_kind: 1=queue 2=turnstile 3=port",
    "launchd_wait_kind_names": b"semaphore",
    "launchd_semaphore_owner_context": b"owner_pid=%llu context=0x%llx",
    "launchd_main_thread_wait": b"VEUX MAIN WAIT: tid=%llu state=0x%x kind=%s",
    "launchd_main_thread_stack_each_sample": b"VEUX STACK MAIN: tid=%llu attempted=%u skipped: %s result=%d frames=%u flags=0x%x",
    "launchd_main_thread_stack_frames": b"VEUX STACK MAIN FRAMES: tid=%llu",
    "pid1_spawn_attempts": b"VEUX SPAWN: pid=1 parent=%d name=%s path=%s errno=%d path_errno=%d",
    "pid1_exec_attempts": b"VEUX EXEC: pid=1 name=%s path=%s errno=%d path_errno=%d",
    "process_exit_status_and_signal": b"VEUX EXIT: pid=%d name=%s status=0x%x exit_status=%d signal=%d",
    "exec_mac_denials": b"VEUX MAC DENY: policy=mac_vnode_check_exec",
    "launchd_vm_region_and_shared_cache": b"VEUX VM: launchd shared_base=",
    "panic_region_marker": b"VEUX EARLY PANIC:",
    "panic_console_tail_header": b"Last console lines (oldest first; includes mount output):",
    "panic_console_tail_symbol": b"veux_fb_panic_console_tail",
    "mount_helper_start": b"VEUX MOUNT helper start name=",
    "mount_helper_exit": b"VEUX MOUNT helper exit raw-status=",
    "root_mount_result": b"VEUX ROOT mount result errno=",
    "root_mode_reports_effective_dual_arg_state": b"VEUX ROOT mode=%s rootrw=%u ufsrw=%u",
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
serial = (a.source_root / "pexpert/arm/pe_serial.c").read_text()
early = (a.source_root / "osfmk/arm64/veux_early.c").read_text()
fb_init = serial.split("veux_fb_init(void)", 1)[1].split("veux_fb_console_putc(char c)", 1)[0]
stage_fn = early.split("veux_stage_mark_nb(unsigned int cell)", 1)[1].split("veux_stage_flush(void)", 1)[0]
source_checks["framebuffer_console_and_marker_are_unconditional"] = (
    'PE_parse_boot_argn("veuxfb"' not in fb_init
    and 'PE_parse_boot_argn("veuxfbconsole"' not in fb_init
    and "int write_marker = 1;" in fb_init
    and "int enable_console = 1;" in fb_init
)
source_checks["direct_framebuffer_build_id_print"] = (
    'VEUX BUILD: ID=' in fb_init and 'veux_fb_console_putc(build_id_line[i])' in fb_init
)
live_sampler = (a.source_root / "bsd/dev/veux_liveness.c").read_text()
exception = (a.source_root / "osfmk/kern/exception.c").read_text()
source_checks["liveness_does_not_emit_unchanged_cpu_counters"] = (
    "old->user_us != e->user_us" not in live_sampler
    and "old->system_us != e->system_us" not in live_sampler
    and "old->user_pc != e->user_pc" not in live_sampler
)
source_checks["launchd_waits_are_classified_by_waitq_type"] = (
    "waitq_type(thread->waitq)" in exception
    and "thread->waitq.wq_q != NULL" in exception
    and "thread_tid(thread)" in exception
    and "VEUX WAIT: tid=" in exception
)
source_checks["launchd_main_stack_is_attempted_each_sample_with_explicit_skip_reason"] = (
    "struct veux_wait_record waits[8];" in exception
    and "if (count == 1)" in exception
    and "if (thread->kernel_stack != 0)" in exception
    and "main_trace_attempted = 1;" in exception
    and "main_trace_result = machine_trace_thread64(thread" in exception
    and "MIN((uint32_t)main_trace_result, 12)" in exception
    and 'main_trace_skipped = "no-kernel-stack";' in exception
    and 'main_trace_skipped = "no-main-thread";' in exception
    and "VEUX STACK MAIN: tid=%llu attempted=%u skipped: %s result=%d frames=%u flags=0x%x" in exception
    and "VEUX STACK MAIN FRAMES: tid=%llu" in exception
    and "previous_launchd_wait_hash != wait_hash" in exception
    and "if (!previous_launchd_wait_valid && thread->kernel_stack != 0)" not in exception
)
source_checks["pid1_exec_spawn_exit_and_mac_trace_hooks"] = (
    "veux_trace_spawn = (proc_getpid(ap) == 1);" in (a.source_root / "bsd/kern/kern_exec.c").read_text()
    and "VEUX SPAWN: pid=1 parent=%d name=%s path=%s errno=%d path_errno=%d" in (a.source_root / "bsd/kern/kern_exec.c").read_text()
    and "veux_trace_exec = (proc_getpid(p) == 1);" in (a.source_root / "bsd/kern/kern_exec.c").read_text()
    and "VEUX EXEC: pid=1 name=%s path=%s errno=%d path_errno=%d" in (a.source_root / "bsd/kern/kern_exec.c").read_text()
    and "VEUX MAC DENY: policy=mac_vnode_check_exec" in (a.source_root / "bsd/kern/kern_exec.c").read_text()
    and "VEUX MAC DENY: policy=vnode_authorize" in (a.source_root / "bsd/kern/kern_exec.c").read_text()
    and "VEUX EXIT: pid=%d name=%s status=0x%x exit_status=%d signal=%d" in (a.source_root / "bsd/kern/kern_exit.c").read_text()
    and "WIFEXITED(veux_status)" in (a.source_root / "bsd/kern/kern_exit.c").read_text()
    and "WIFSIGNALED(veux_status)" in (a.source_root / "bsd/kern/kern_exit.c").read_text()
)

source_checks["launchd_vm_report_is_present"] = (
    "veux_live_launchd_vm(task, pc);" in exception
    and "VEUX VM: launchd pc=" in exception
)
source_checks["early_stage_cells_do_not_depend_on_boot_args"] = (
    "veux_stage_mark_nb(unsigned int cell)" in early
    and "if (cell >= 22) return;" in stage_fn
    and "PE_parse_boot_argn" not in stage_fn
    and "veux_stage_mark(2);" in early
    and "veux_stage_mark(3);" in early
)
root_alloc = vfs.split("vfs_rootmountalloc_internal(struct vfstable *vfsp", 1)[1].split("vfs_rootmountalloc(", 1)[0]
source_checks["root_mount_starts_read_only"] = "mp->mnt_flag = MNT_RDONLY | MNT_ROOTFS;" in root_alloc
mountroot = vfs.split("vfs_mountroot(void)", 1)[1]
root_mount_alloc = mountroot.split('mp = vfs_rootmountalloc_internal(vfsp, "root_device")', 1)
root_mount_alloc = root_mount_alloc[1].split("if (vfsp->vfc_mountroot)", 1)[0] if len(root_mount_alloc) == 2 else ""
source_checks["rootrw_and_ufsrw_both_required_for_rw_mount"] = (
    "uint32_t rootrw = 0, ufsrw = 0;" in root_mount_alloc
    and 'PE_parse_boot_argn("rootrw", &rootrw, sizeof(rootrw));' in root_mount_alloc
    and 'PE_parse_boot_argn("ufsrw", &ufsrw, sizeof(ufsrw));' in root_mount_alloc
    and "if (rootrw == 1 && ufsrw == 1)" in root_mount_alloc
    and "mp->mnt_flag &= ~MNT_RDONLY;" in root_mount_alloc
)
source_checks["rootrw_and_ufsrw_both_required_for_writable_ufs"] = (
    "uint32_t rw = 0;" in ufs
    and 'PE_parse_boot_argn("ufsrw", &rw, sizeof(rw));' in ufs
    and 'PE_parse_boot_argn("rootrw", &rootrw, sizeof(rootrw));' in ufs
    and "su.writable = (rw == 1 && rootrw == 1);" in ufs
)
if not all(source_checks.values()):
    raise SystemExit("kernel source policy check failed: " + repr(source_checks))
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
if not any("0031-sweet-read-write-root.patch APPLIED" in line for line in status):
    raise SystemExit("manifest requires 0031 to apply; its rootrw gate is a prerequisite for the VEUX extension")

manifest = {
    "build_id": a.build_id,
    "patch_status": status,
    "allowlisted_skips": allowlisted_skips,
    "string_checks": checks,
    "source_policy_checks": source_checks,
    "kernel_sha256": hashlib.sha256(kernel).hexdigest(),
    "kernel_path": str(a.kernel),
    "boot_args": a.boot_args,
    "root_mode_requested": "rw" if {"rootrw=1", "ufsrw=1"}.issubset(boot_args) else "ro",
    "wrapper": "assembled on host with the phone DTB; see adjacent wrapper manifest",
}
a.output.parent.mkdir(parents=True, exist_ok=True)
a.output.write_text(json.dumps(manifest, indent=2) + "\n")
print(f"VEUX BUILD ID: {a.build_id}")
print(f"kernel_sha256={manifest['kernel_sha256']}")
print(a.output)
