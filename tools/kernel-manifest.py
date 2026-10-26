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
    "0122-veux-xpcproxy-driver-spawn-gate.patch",
    "0123-veux-software-display-services.patch",
    "0124-veux-display-enumeration-trace.patch",
    "0125-veux-software-framebuffer-registry-properties.patch",
    "0126-veux-iomfb-client-start-fallback.patch",
    "0127-veux-iomfb-display-list-properties.patch",
    "0128-veux-gui-exit-summary.patch",
    "0129-veux-normalize-iomfb-device-types.patch",
    "0130-veux-register-software-applekeystore.patch",
    "0131-veux-touch-readonly-se8-probe.patch",
):
    if not any(line.startswith(f"PATCH_STATUS: {patch} APPLIED") for line in status):
        raise SystemExit(f"required patch was not applied: {patch}")

needles = {
    "build_id_screen_and_ring": f"VEUX BUILD: ID={a.build_id}".encode(),
    "early_framebuffer_console_entry": b"VEUX simplefb console 1080x2400 stride=4320 format=a8r8g8b8",
    "software_gui_validated_scanout": b"VEUX GUI: validated firmware framebuffer; software scanout only",
    "software_gui_invalid_scanout_rejected": b"VEUX GUI: refusing unvalidated firmware framebuffer",
    "software_gui_first_present": b"VEUX GUI: first valid software display present",
    "software_gui_disp0_enumeration_trace": b"VEUX GUI: /arm-io found; disp0=%u",
    "software_gui_driver_start_trace": b"VEUX GUI: AppleCLCD start provider=%s",
    "software_gui_driver_state_trace": b"VEUX GUI: surface=%u id=%u mapping=%u workloop=%u lock=%u clients=%u",
    "software_gui_userclient_start_trace": b"VEUX GUI: IOMFB user client provider=%s framebuffer=%u",
    "software_gui_userclient_init_trace": b"VEUX GUI: IOMFB client initialized process=%s type=%u",
    "software_gui_userclient_ready_trace": b"VEUX GUI: IOMFB client ready process=%s",
    "software_gui_fdr_provider_policy": b"VEUX GUI: FDR policy provider=%u service=%u",
    "software_gui_iomfb_list_properties": b"VEUX GUI: IOMFB list properties dfr=%u AppleTV=%u external=%u",
    "software_gui_exit_summary": b"VEUX GUI SUMMARY: registered=%u fdr=0x%x list=0x%x",
    "software_gui_iomfb_device_type_normalization": b"VEUX GUI: disp0 device_type canonicalized=%u previous=%s",
    "software_gui_userclient_base_fallback": b"VEUX GUI: IOMFB base start rejected; continuing software client",
    "software_gui_swap_trace": b"VEUX GUI: framebuffer swap %u mask=0x%x",
    "software_apple_keystore_service": b"SWEET AKS: AppleKeyStore registered (no passcode, unlocked)",
    "veux_touch_readonly_probe": b"VEUX TOUCH PROBE: read-only SE8 fw=",
    "surface_service": b"IOCoreSurfaceRoot",
    "mobile_framebuffer_service": b"IOMobileFramebufferUserClient",
    "watchdog_compatibility_service": b"IOWatchdog registered (accepts check-ins, never fires)",
    "process_sampler": b"VEUX LIVE: processes=",
    "launchd_thread_wait_classifier": b"VEUX WAIT: launchd threads=",
    "waitq_kind_classifier": b"waitq_kind: 1=queue 2=turnstile 3=port",
    "launchd_wait_kind_names": b"semaphore",
    "launchd_semaphore_owner_context": b"owner_pid=%llu context=0x%llx",
    "launchd_main_thread_wait": b"VEUX MAIN WAIT: tid=%llu state=0x%x kind=%s",
    "launchd_main_thread_stack_each_sample": b"VEUX STACK MAIN: tid=%llu attempted=%u skipped: %s result=%d frames=%u flags=0x%x",
    "launchd_main_thread_stack_frames": b"VEUX STACK MAIN FRAMES: tid=%llu",
    "pid1_spawn_attempts": b"VEUX SPAWN FAIL: pid=1 parent=%d name=%s path=%s stage=%s errno=%d path_errno=%d attempt=%u",
    "pid1_spawn_repeat_dedup": b"VEUX SPAWN REPEAT: pid=1 parent=%d name=%s path=%s stage=%s errno=%d count=%u",
    "xpcproxy_driver_entitlement_deny": b"VEUX SPAWN DENY: return_site=exec_validate_spawnattr_policy policy=IOCurrentTaskHasEntitlement",
    "xpcproxy_driver_bootarg_allow": b"VEUX SPAWN DEV ALLOW: rule=pid1-xpcproxy-driver-bootarg hook=exec_validate_spawnattr_policy/IOCurrentTaskHasEntitlement",
    "xpcproxy_target_signature_state": b"VEUX SPAWN TARGET: path=%s stage=exec_activate_image result=0 csflags=0x%x CS_VALID=%u CS_PLATFORM_BINARY=%u",
    "exec_activation_failure_return": b"VEUX SPAWN RETURN: return_site=exec_activate_image stage=exec_mach_imgact+exec_activate_image",
    "exec_imgact_return_trace": b"VEUX IMGACT RETURN: return_site=exec_activate_image activator=%s",
    "exec_mac_hook_deny_trace": b"VEUX MAC HOOK DENY: stage=mac_vnode_check_exec policy=%s hook=mpo_vnode_check_exec",
    "launch_constraint_hook_deny_trace": b"VEUX MAC DENY: policy=%s hook=mpo_proc_check_launch_constraints",
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
touch_probe = (a.source_root / "bsd/dev/veux_touch_probe.c").read_text()
early = (a.source_root / "osfmk/arm64/veux_early.c").read_text()
fb_init = serial.split("veux_fb_init(void)", 1)[1].split("veux_fb_console_putc(char c)", 1)[0]
stage_fn = early.split("veux_stage_mark_nb(unsigned int cell)", 1)[1].split("veux_stage_flush(void)", 1)[0]
source_checks["framebuffer_console_and_marker_are_unconditional"] = (
    'PE_parse_boot_argn("veuxfb"' not in fb_init
    and 'PE_parse_boot_argn("veuxfbconsole"' not in fb_init
    and "int write_marker = 1;" in fb_init
    and "int enable_console = 1;" in fb_init
)
source_checks["veux_touch_probe_is_opt_in_and_read_only"] = (
    'PE_parse_boot_argn("veuxtouchprobe", &enabled, sizeof(enabled))' in touch_probe
    and "VEUX_TOUCH_SE_PA       0x04c88000u" in touch_probe
    and "VEUX_TOUCH_GCC_PA      0x01400000u" in touch_probe
    and "VEUX_TOUCH_GCC_SIZE    0x80000u" in touch_probe
    and "VEUX_TOUCH_TLMM_PA     0x00400000u" in touch_probe
    and "no GPIO/GCC/SE writes and no I2C transfer" in touch_probe
    and "touch_wr(" not in touch_probe
    and "SE_CMD" not in touch_probe
    and "sweet_hid_touch" not in touch_probe
    and 'veux_touch_probe_init();' in ufs
)
source_checks["direct_framebuffer_build_id_print"] = (
    'VEUX BUILD: ID=' in fb_init and 'veux_fb_console_putc(build_id_line[i])' in fb_init
)
live_sampler = (a.source_root / "bsd/dev/veux_liveness.c").read_text()
exception = (a.source_root / "osfmk/kern/exception.c").read_text()
exit_source = (a.source_root / "bsd/kern/kern_exit.c").read_text()
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
source_checks["gui_exit_summary_only_on_springboard_or_backboard_exit"] = (
    'strcmp(p->p_comm, "SpringBoard") == 0' in exit_source
    and 'strcmp(p->p_comm, "backboardd") == 0' in exit_source
    and "veux_gui_process_exit_summary();" in exit_source
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
exec_source = (a.source_root / "bsd/kern/kern_exec.c").read_text()
source_checks["pid1_exec_spawn_exit_and_mac_trace_hooks"] = (
    "veux_trace_spawn = (proc_getpid(ap) == 1);" in exec_source
    and "VEUX SPAWN FAIL: pid=1 parent=%d name=%s path=%s stage=%s errno=%d path_errno=%d attempt=%u" in exec_source
    and "veux_trace_exec = (proc_getpid(p) == 1);" in exec_source
    and "VEUX EXEC: pid=1 name=%s path=%s errno=%d path_errno=%d" in exec_source
    and "VEUX MAC DENY: policy=mac_vnode_check_exec" in exec_source
    and "VEUX MAC DENY: policy=vnode_authorize" in exec_source
    and "VEUX EXIT: pid=%d name=%s status=0x%x exit_status=%d signal=%d" in (a.source_root / "bsd/kern/kern_exit.c").read_text()
    and "WIFEXITED(veux_status)" in (a.source_root / "bsd/kern/kern_exit.c").read_text()
    and "WIFSIGNALED(veux_status)" in (a.source_root / "bsd/kern/kern_exit.c").read_text()
)

source_checks["xpcproxy_driver_spawn_exception_is_bootarg_gated_entitlement_only"] = (
    'strcmp(veux_spawn_path, "/usr/libexec/xpcproxy") == 0' in exec_source
    and 'PE_parse_boot_argn("veux_spawn_driver", &dev_allow, sizeof(dev_allow))' in exec_source
    and "dev_allow == 1" in exec_source
    and "error == EPERM" in exec_source
    and "proctype == POSIX_SPAWN_PROC_TYPE_DRIVER" in exec_source
    and "POSIX_SPAWN_ENTITLEMENT_DRIVER" in exec_source
    and "veux_spawn_deferred_driver_policy = 1;" in exec_source
    and "error = 0; /* Bypass only this entitlement gate; image and MAC checks still run. */" in exec_source
    and "if (error != 0 && !veux_spawn_deferred_driver_policy)" in exec_source
    and "flags=0x%x setexec=%u options=0x%x launch_type=0x%x mac_extensions_size=%u" in exec_source
    and "VEUX SPAWN DEV ALLOW: rule=pid1-xpcproxy-driver-bootarg" in exec_source
    and "followup=normal-image-signature-vnode-exec-and-launch-constraints" in exec_source
    and "VEUX SPAWN TARGET: path=%s stage=exec_activate_image result=0 csflags=0x%x CS_VALID=%u CS_PLATFORM_BINARY=%u" in exec_source
    and "exec_resettextvp(p, imgp);" in exec_source
    and "veux_spawn_deferred_driver_policy && (imgp->ip_csflags" not in exec_source
    and "VEUX SPAWN DENY: return_site=exec_validate_spawnattr_policy policy=IOCurrentTaskHasEntitlement" in exec_source
    and "VEUX SPAWN RETURN: return_site=exec_activate_image stage=exec_mach_imgact+exec_activate_image" in exec_source
    and "VEUX IMGACT RETURN: return_site=exec_activate_image activator=%s" in exec_source
    and "if (proc_getpid(vfs_context_proc(ctx)) == 1 && hook_result != 0)" in (a.source_root / "security/mac_vfs.c").read_text()
    and "veux_exec_mac_denials % 32" in (a.source_root / "security/mac_vfs.c").read_text()
    and "VEUX MAC HOOK DENY: stage=mac_vnode_check_exec policy=%s hook=mpo_vnode_check_exec" in (a.source_root / "security/mac_vfs.c").read_text()
    and "VEUX MAC DENY: policy=%s hook=mpo_proc_check_launch_constraints" in (a.source_root / "security/mac_process.c").read_text()
)

fb = (a.source_root / "iokit/Kernel/arm/SweetFramebuffer.cpp").read_text()
surface = (a.source_root / "iokit/Kernel/arm/SweetSurface.cpp").read_text()
watchdog = (a.source_root / "iokit/Kernel/arm/SweetWatchdog.cpp").read_text()
platform = (a.source_root / "iokit/Kernel/arm/VeuxPlatformExpert.cpp").read_text()
source_checks["veux_gui_services_require_explicit_bootarg"] = all(
    'PE_parse_boot_argn("veux_gui", &gui, sizeof(gui))' in text
    and 'gui != 1' in text for text in (fb, surface, watchdog)
) and 'gui == 1' in platform and "('disp0')" in platform
source_checks["veux_gui_scanout_requires_exact_firmware_geometry"] = all(
    text in fb for text in (
        '"/chosen/framebuffer@85200000"', 'reg[0] != 0x85200000ULL',
        'reg[1] != 0x00c00000ULL', '*width != 1080', '*height != 2400',
        '*stride != 4320', 'memcmp(format, "a8r8g8b8", sizeof("a8r8g8b8"))',
        's->pixelFormat != SWEET_FB_FORMAT_BGRA',
    )
)
source_checks["veux_gui_trace_covers_nub_driver_and_userclient"] = all(
    token in text for text, token in (
        (platform, "VEUX GUI: /arm-io found; disp0=%u"),
        (platform, "VEUX GUI: /arm-io missing; no display nub published"),
        (fb, "VEUX GUI: AppleCLCD start provider=%s"),
        (fb, "VEUX GUI: AppleCLCD registered size=%ux%u surface=%u"),
        (fb, "VEUX GUI: IOMFB user client provider=%s framebuffer=%u"),
        (fb, "VEUX GUI: framebuffer swap %u mask=0x%x"),
    )
)
source_checks["veux_gui_display_list_flags_are_explicit"] = all(
    token in fb for token in (
        'setProperty("dfr", false)',
        'setProperty("AppleTV", false)',
        'setProperty("external", false)',
        'VEUX GUI: IOMFB list properties dfr=%u AppleTV=%u external=%u',
    )
)
clip = fb.split("/* Clip in 64-bit coordinates:", 1)[1].split("uint64_t last = 0;", 1)[0]
source_checks["veux_gui_rectangle_clipping_uses_checked_wide_arithmetic"] = (
    "int64_t csx" in clip and "cdx = (int64_t)dx - fOffX" in clip
    and "INT32_MAX" in clip and "sx = (int32_t)csx" in clip
    and "dx -= fOffX" not in clip and "w += dx" not in clip
    and "(int32_t)s->width - sx" not in clip
)
source_checks["veux_gui_surface_extent_checks_prevent_unsigned_wrap"] = all(
    token in fb for token in (
        "bool extent_ok = w > 0 && h > 0;", "UINT64_MAX - base - x_end",
        "row * s->bytesPerRow + x_end", "if (!extent_ok || s->elementWidth != 1",
    )
)
source_checks["veux_gui_console_handoff_is_explicit_after_valid_present"] = (
    'PE_parse_boot_argn("veux_gui_noconsole", &quiet, sizeof(quiet)) && quiet == 1' in fb
    and fb.index('VEUX GUI: first valid software display present') > fb.index('if (src != 0 && bpe == 4)')
    and 'veux_fb_gui_handoff();' in fb
    and 'if (veux_gui_console_muted) return;' in early
    and 'veux_gui_console_muted = 0;' in serial
)

console_putc = serial.split("veux_fb_console_putc(char c)\n{", 1)[1].split("const uint32_t cols", 1)[0]
source_checks["veux_gui_mute_preserves_capture_and_panic_screen"] = (
    console_putc.index("veux_panic_tail_capture(c);") < console_putc.index("veux_gui_console_muted")
    and fb.count("if (panic_active()) return;") >= 2
    and "veux_gui_console_muted = 0; /* Terminal diagnostics reclaim the screen. */" in early
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
