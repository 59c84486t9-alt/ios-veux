#!/usr/bin/env python3
"""Verify required VEUX features in the final kernel and write build evidence."""
import argparse
import hashlib
import json
import re
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--kernel", required=True, type=Path)
ap.add_argument("--patch-status", required=True, type=Path)
ap.add_argument("--build-id", required=True)
ap.add_argument("--boot-args", required=True, help="full normal-variant boot args")
ap.add_argument("--held-boot-args", required=True, help="full held-probe boot args")
ap.add_argument("--modem-held-boot-args", required=True, help="exact modem diagnostic held boot args")
ap.add_argument("--source-root", required=True, type=Path)
ap.add_argument("--output", required=True, type=Path)
a = ap.parse_args()

boot_args = set(a.boot_args.split())
held_boot_args = set(a.held_boot_args.split())
modem_held_boot_args = a.modem_held_boot_args.split()
expected_modem_held_boot_args = (
    "debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam -noprogress "
    "rd=ufsroot0 modem=1 modem_watch=180 veuxfbconsole=1"
)
if a.modem_held_boot_args != expected_modem_held_boot_args:
    raise SystemExit("modem-held boot args must match the exact Phase-1 string")
modem_held_set = set(modem_held_boot_args)
if not {"modem=1", "modem_watch=180", "veuxfbconsole=1"}.issubset(modem_held_set):
    raise SystemExit("modem-held boot args require modem=1, modem_watch=180, and veuxfbconsole=1")
modem_forbidden_boot_args = {
    "rootrw", "ufsrw", "veuxlog", "veux_gui", "veuxsandbox", "veuxiolog",
    "veux_spawn_driver", "veuxgpipreflight", "veuxtouchprobe",
}
if any(arg.split("=", 1)[0] in modem_forbidden_boot_args for arg in modem_held_boot_args):
    raise SystemExit("modem-held boot args contain a forbidden write, GUI, or probe argument")
if not {"rootrw=1", "ufsrw=1", "veuxvariant=normal"}.issubset(boot_args):
    raise SystemExit("normal variant requires the explicit RW pair and veuxvariant=normal")
if {"veuxtouchprobe=1", "veuxtouchprobehold=1", "veuxfb=1", "veuxfbconsole=1", "veuxvariant=held"} - held_boot_args:
    raise SystemExit("held variant requires the held read-only probe and diagnostic display args")
if {"rootrw=1", "ufsrw=1", "veuxtouchprobeactive=1", "veuxlog=1"} & held_boot_args:
    raise SystemExit("held variant must not enable UFS writes or the active touch sequence")
if "veuxtouchprobe=1" in boot_args or "veuxtouchprobehold=1" in boot_args or "veuxfb=1" in boot_args or "veuxfbconsole=1" in boot_args:
    raise SystemExit("normal variant must not enable the held probe or full framebuffer console")
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
    "0131-veux-touch-tlmm-mapping-diagnostic.patch",
    "0132-veux-touch-bounded-goodix-id-probe.patch",
    "0133-veux-gpi-smmu-readonly-preflight.patch",
    "0134-veux-repeat-gpi-preflight-summary.patch",
    "0135-veux-start-gpi-summary-from-probe.patch",
    "0140-veux-touch-tlmm-physical-map-check.patch",
    "0141-veux-touch-nofault-tlmm-translation.patch",
    "0142-veux-held-tlmm-ab-probe-and-normal-boot.patch",
    "0143-veux-tlmm-alt-first-compact.patch",
    "0144-veux-tlmm-two-read-fault-context.patch",
    "0145-veux-touch-use-regbase-adjusted-tlmm.patch",
    "0146-veux-touch-gui-status.patch",
    "0147-veux-touch-status-persistent-present.patch",
    "0148-veux-geni-fifo-linux-sequence.patch",
    "0149-veux-tlmm-per-read-checkpoints-and-touch-overlay.patch",
    "0150-veux-touch-gpio-i2c-when-fifo-disabled.patch",
    "0151-veux-disable-touch-lockscreen-overlay.patch",
    "0152-veux-ipcc.patch",
    "0153-veux-modem-pool.patch",
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
    "veux_touch_probe_before": b"VEUX TLMM BEFORE #%u pin=%u CFG PA=",
    "veux_touch_probe_after": b"VEUX TLMM AFTER pin=%u CFG PA=",
    "veux_touch_probe_fault": b"VEUX TLMM FAULT pin=%u PA=",
    "veux_touch_probe_hold": b"held before root mount; read-only per-pin CFG comparison complete; GPIO0-3 skipped; no UFS/GPIO writes",
    "veux_variant_held": b"variant=held",
    "veux_variant_normal": b"variant=normal ID=",
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
    "read_only_gpi_summary": b"VEUX GPI SUMMARY: state=%s hook=%u arg=%u enabled=%u map=%u/%u",
    "read_only_smmu_summary": b"VEUX SMMU SUMMARY: idr=%#x/%#x/%#x scr0=%#x gbpa=%#x",
    "gpi_summary_thread_started": b"VEUX GPI SUMMARY THREAD: started; three delayed read-only reports",
}
checks = {name: needle in kernel for name, needle in needles.items()}
ipcc_path = a.source_root / "osfmk/arm64/veux_ipcc.c"
ipcc_source = ipcc_path.read_text() if ipcc_path.exists() else ""
ipcc_init = ipcc_source.split("veux_ipcc_init(void)", 1)[-1]
ipcc_selftest = ipcc_init.split("raw_recv =", 1)[-1] if "raw_recv =" in ipcc_init else ""
ipcc_signal_body = ipcc_source.split("veux_ipcc_signal(uint8_t client_id, uint16_t signal_id)", 1)[-1].split("bool\nveux_ipcc_poll", 1)[0]
ipcc_poll_body = ipcc_source.split("veux_ipcc_poll(uint8_t client_id, uint16_t signal_id)", 1)[-1].split("/* Private IOKit", 1)[0]
ipcc_defines = {line.split()[1]: line.split()[-1] for line in ipcc_source.splitlines()
                if line.startswith("#define VEUX_IPCC_") and len(line.split()) >= 3}
ipcc_source_checks = {
    "source_file_exists": ipcc_path.is_file(),
    "signal_and_poll_functions": "veux_ipcc_signal(uint8_t client_id, uint16_t signal_id)" in ipcc_source and "veux_ipcc_poll(uint8_t client_id, uint16_t signal_id)" in ipcc_source,
    "both_functions_log_marker": "VEUX IPCC:" in ipcc_signal_body and "VEUX IPCC:" in ipcc_poll_body,
    "client_and_signal_constants": all(ipcc_defines.get(name) == value for name, value in (
        ("VEUX_IPCC_CLIENT_APSS", "8u"), ("VEUX_IPCC_CLIENT_MPSS", "2u"),
        ("VEUX_IPCC_CLIENT_AOP", "0u"), ("VEUX_IPCC_SIGNAL_SMP2P", "2u"),
        ("VEUX_IPCC_SIGNAL_GLINK_QMP", "0u"))),
    "base_and_registers": all(x in ipcc_source for x in (
        "VEUX_IPCC_PA                 0x00208000u", "VEUX_IPCC_REG_SEND_ID",
        "VEUX_IPCC_REG_RECV_ID", "VEUX_IPCC_REG_RECV_SIGNAL_CLEAR")),
    "verified_mmio_layout": all(x in ipcc_source for x in (
        "VEUX_IPCC_SIZE               0x1000u",
        "VEUX_IPCC_REG_RECV_ID        0x10u",
        "VEUX_IPCC_NO_PENDING         0xffffffffu",
        "ml_io_map(VEUX_IPCC_PA, VEUX_IPCC_SIZE)")),
    "qualcomm_packed_order": "((uint32_t)client_id << 16) | (uint32_t)signal_id" in ipcc_source,
    "selftest_format_and_read_only_path": "VEUX IPCC: selftest raw_recv_id=0x%08x" in ipcc_source and "VEUX IPCC: selftest raw_recv_id=0x%08x".encode() in kernel and "veux_ipcc_signal(" not in ipcc_init and "veux_ipcc_poll(" not in ipcc_init and "VEUX_IPCC_REG_RECV_SIGNAL_CLEAR] =" not in ipcc_selftest,
    "no_apcs_legacy_mapping": not any(x in ipcc_source for x in ("APCS", "APCS_IPC", "0x0f111000")),
    "no_interrupt_or_gic_setup": not any(x in ipcc_source for x in (
        "register_interrupt", "irq_install", "IOInterruptEventSource", "GIC_SPI", "0x14E")),
    "binary_marker": b"VEUX IPCC:" in kernel,
}
if not all(ipcc_source_checks.values()):
    raise SystemExit("VEUX IPCC Phase-2 sub-gate failed: " + repr(ipcc_source_checks))
print("VEUX IPCC Phase-2 source assertions: PASS " + repr(ipcc_source_checks))
print("VEUX IPCC Phase-2 binary marker and read-only self-test string: PASS")
pool_path = a.source_root / "osfmk/arm64/veux_modem_pool.c"
pool_source = pool_path.read_text() if pool_path.exists() else ""
pool_assertions = "\n".join(line for line in pool_source.splitlines() if "_Static_assert" in line)
pool_heap_calls = re.findall(r"\b(?:kmem_alloc|IOMalloc)\s*\(", pool_source)
pool_patch_lines = [line for line in status if line.startswith("PATCH_STATUS: 0153-veux-modem-pool.patch")]
pool_patch_results = [line for line in pool_patch_lines if line.endswith((" APPLIED", " ALLOWLISTED_SKIP"))]
pool_source_checks = {
    "source_file_and_allocator": pool_path.is_file() and "veux_modem_pool_alloc(uint64_t size, uint64_t *pa)" in pool_source,
    "region_and_allocation_log_markers": "VEUX MODEM POOL: 0x%llx + 0x%llx (from %s)" in pool_source and "VEUX MODEM POOL: alloc 0x%llx + 0x%llx" in pool_source,
    "selected_reserved_region_constants": all(x in pool_source for x in (
        "VEUX_MODEM_POOL_BASE                 0xc0000000ULL",
        "VEUX_MODEM_POOL_SIZE                 0x05100000ULL",
        "removed_region@c0000000")),
    "write_combined_mapping_without_pool_writes": "ml_io_map_wcomb" in pool_source and "VEUX_MODEM_POOL_ALIGNMENT" in pool_source and "allocation[i] = 0" not in pool_source and "0xdeadbeef" not in pool_source,
    "early_startup_maps_pool_before_io_submap": "STARTUP(KMEM, STARTUP_RANK_FIRST, veux_modem_pool_init);" in pool_source and "#include <kern/startup.h>" in pool_source,
    "ipcc_selftest_precedes_pool_mapping": pool_source.find("veux_ipcc_init();") < pool_source.find("ml_io_map_wcomb") and "extern void veux_ipcc_init(void);" in pool_source,
    "no_direct_heap_allocator_calls_for_reserved_pool": not pool_heap_calls,
    "static_asserts_cover_required_regions": all(x in pool_assertions for x in (
        "overlaps pil_mpss_wlan_mem", "overlaps wlan_msa", "overlaps ramoops",
        "overlaps framebuffer", "overlaps smem", "overlaps kernel image",
        "overlaps recovery initrd")),
    "static_asserts_cover_other_fixed_carveouts": all(x in pool_assertions for x in (
        "overlaps hyp", "overlaps xbl_aop_mem", "overlaps reserved_xbl_uefi",
        "overlaps fw_mem", "overlaps cdsp_secure_heap", "overlaps adsp",
        "overlaps cdsp", "overlaps video", "overlaps ipa_fw",
        "overlaps ipa_gsi", "overlaps gpu_micro_code", "overlaps memshare_region")),
    "runtime_overlap_panic_guard": "veux_modem_pool_has_forbidden_overlap" in pool_source and "panic(\"VEUX MODEM POOL overlaps reserved carve-out\")" in pool_source,
    "pool_init_is_read_only": "0xdeadbeef" not in pool_source and "VEUX MODEM POOL: selftest" not in pool_source and "allocation[i] = 0" not in pool_source and "veux_modem_pool_alloc(0x1000ULL" not in pool_source,
    "no_legacy_or_topaz_pool_constants": not any(x in pool_source for x in ("APCS", "APCS_IPC", "0x0f111000", "0xe0000000")),
    "patch_0153_applied_without_skip": len(pool_patch_results) == 1 and pool_patch_results[0].endswith(" APPLIED"),
}
if not all(pool_source_checks.values()):
    raise SystemExit("VEUX MODEM POOL Phase-3 sub-gate failed: " + repr(pool_source_checks))
print("VEUX MODEM POOL Phase-3 source assertions: PASS " + repr(pool_source_checks))
pool_binary_checks = {
    "region_marker": b"VEUX MODEM POOL: 0x%llx + 0x%llx (from %s)" in kernel,
    "allocation_marker": b"VEUX MODEM POOL: alloc 0x%llx + 0x%llx" in kernel,
    "no_pool_write_selftest_log": b"VEUX MODEM POOL: selftest" not in kernel,
}
if not all(pool_binary_checks.values()):
    raise SystemExit("VEUX MODEM POOL Phase-3 binary marker gate failed: " + repr(pool_binary_checks))
print("VEUX MODEM POOL read-only init/allocation binary markers: PASS " + repr(pool_binary_checks))
phase4_patch_names = (
    "0154-veux-modem-pas.patch",
    "0155-veux-modem-firmware.patch",
    "0156-veux-modem-glink.patch",
    "0157-veux-modem-pdmapper.patch",
    "0158-veux-modem-wlfw.patch",
    "0159-veux-dt-crc-diagnostics.patch",
    "0160-veux-ipcc-clock-note.patch",
    "0161-veux-ipcc-mapping-diagnostic.patch",
    "0162-veux-ufs-multilun.patch",
)
phase4_patch_texts = {}
phase4_status = {}
for name in phase4_patch_names:
    patch_path = Path("xnu/patches") / name
    phase4_patch_texts[name] = patch_path.read_text() if patch_path.is_file() else ""
    terminal = [line for line in status if line.startswith(f"PATCH_STATUS: {name} ") and
                line.endswith((" APPLIED", " ALLOWLISTED_SKIP"))]
    phase4_status[name] = len(terminal) == 1 and terminal[0].endswith(" APPLIED")
phase4_text = "\n".join(phase4_patch_texts.values())
dt_crc_patch = phase4_patch_texts["0159-veux-dt-crc-diagnostics.patch"]
dt_crc_checks = {
    "boot_args_device_tree_pointer": "args->deviceTreeP" in dt_crc_patch and "args->deviceTreeLength" in dt_crc_patch,
    "crc32_implementation": "0xedb88320U" in dt_crc_patch and "veux_dt_crc32" in dt_crc_patch,
    "before_and_after_thread_logs": all(x in dt_crc_patch for x in (
        'veux_dt_crc_log("before_modem_thread")', 'veux_dt_crc_log("after_modem_thread")')),
    "log_format": "VEUX DT: crc=0x%08x stage=%s\\n" in dt_crc_patch,
}
if not all(dt_crc_checks.values()):
    raise SystemExit("VEUX DT CRC Phase-4.11 source gate failed: " + repr(dt_crc_checks))
print("VEUX DT CRC Phase-4.11 source assertions: PASS " + repr(dt_crc_checks))
phase4_lower = phase4_text.lower()
phase4_forbidden = {
    "legacy_apcs_or_topaz_pool": any(x in phase4_lower for x in ("apcs", "0x0f111000", "0xe0000000")),
    "host_cap_path": re.search(r"\bhost_cap\b", phase4_lower) is not None,
    "bdf_or_post_cap_paths": any(re.search(p, phase4_lower) for p in (
        r"\bbdf(?:_\w*)?\b", r"\bcal_report\b", r"\bwlan_cfg\b",
        r"\bwlan_mode\b", r"\bhtt\b", r"\bwmi\b", r"\bce_\w*",
        r"\bscan_\w*")),
}
ufs_source_path = a.source_root / "bsd/dev/sweet_ufs.c"
ufs_source = ufs_source_path.read_text(errors="replace") if ufs_source_path.is_file() else ""
ufs_read_body = ufs_source.split("ufs_read_blocks(uint64_t lba", 1)[-1].split("\n}", 1)[0]
modem_fw_entries = [
    (name, int(offset, 16), int(size))
    for name, offset, size in re.findall(
        r'^\+\s*\{ "(modem\.b[0-9a-f]+)",\s*(0x[0-9a-fA-F]+)U,\s*(\d+)U,',
        phase4_patch_texts["0155-veux-modem-firmware.patch"], re.MULTILINE)
]
modem_fw_ranges = sorted((offset, offset + size, name) for name, offset, size in modem_fw_entries)
modem_fw_no_overlap = all(left[1] <= right[0] for left, right in zip(modem_fw_ranges, modem_fw_ranges[1:]))
phase4_sources = {
    "nine_unique_patch_files": all(phase4_patch_texts.values()),
    "patches_applied_without_skip": all(phase4_status.values()),
    "firmware_table_116_rows": phase4_patch_texts["0155-veux-modem-firmware.patch"].count("{ \"") == 116,
    "modem_bxx_table_has_33_unique_aligned_nonoverlapping_ranges": len(modem_fw_entries) == 33 and len({name for name, _, _ in modem_fw_entries}) == 33 and all(offset % 0x1000 == 0 and size > 0 for _, offset, size in modem_fw_entries) and modem_fw_no_overlap,
    "pas_and_modem_worker_hold": "veux_modem_start(void)" in phase4_text and "veux_modem_hold(void)" in phase4_text,
    "modem_a_read_only_api": "sweet_ufs_read_part(\"modem_a\"" in phase4_text,
    "glink_qrtr_pdm_wlfw_functions": all(x in phase4_text for x in (
        "veux_glink_poll", "veux_pdmap_rx", "veux_wlfw_rx", "veux_scm_assign")),
    "smem_allocator_zeroes_with_volatile_bytes": all(x in phase4_text for x in (
        "VEUX GLINK: zeroing SMEM item=%u size=0x%x",
        "volatile uint8_t *zero_ptr=(volatile uint8_t *)v",
        "for(uint32_t i=0;i<n;i++)zero_ptr[i]=0")) and "bzero(v,n)" not in phase4_text,
    "glink_smem_null_range_and_init_diagnostics": all(x in phase4_text for x in (
        "veux_smem_contains(const void *ptr, uint32_t size)",
        "VEUX GLINK: requesting SMEM items 478, 479, 480",
        "VEUX GLINK: desc va=0x%llx tx_va=0x%llx rx_va=0x%llx",
        'panic(\"GLINK SMEM alloc failed\")',
        'panic(\"GLINK SMEM range invalid\")',
        'panic(\"GLINK assembly buffer alloc failed\")',
        "VEUX GLINK: mapped SMEM",
        "load_u32_unaligned(const void *p)",
        "return safe_read_u32(p);",
        "typ=safe_read_u32(p+4)", "node=safe_read_u32(p+8)",
        "svc=safe_read_u32(p+hlen+4)", "txn=safe_read_u16(p+hlen+1)",
        "VEUX GLINK: copying RX data",
        "VEUX QRTR: processing packet",
        "const volatile uint8_t *src_ptr=(const volatile uint8_t *)(grx+t)",
        "const volatile uint8_t *src_ptr=(const volatile uint8_t *)p",
        "volatile uint8_t *dst_ptr=(volatile uint8_t *)(gtx+h)",
        "for(uint32_t i=0;i<a;i++)dst_ptr[i]=src_ptr[i]",
        "VEUX GLINK: mapped SMEM (write-combine)",
        "VEUX GLINK: sending VERSION",
        "VEUX GLINK: poll loop entered",
        "ml_io_map_wcomb(SMEM_PA,SMEM_SIZE)")) and
        "*(const uint32_t*)p" not in phase4_text and
        (lambda line: "memcpy(" not in line and "for(uint32_t i=0;i<a;i++)dst_ptr[i]=src_ptr[i]" in line)(phase4_text.split("static void peek(", 1)[1].splitlines()[0]) and
        (lambda line: "memcpy(" not in line and "for(uint32_t i=0;i<a;i++)dst_ptr[i]=src_ptr[i]" in line)(phase4_text.split("static uint32_t put(", 1)[1].splitlines()[0]) and
        (lambda line: line.find("if(!gd||!gtx||!grx)") < line.find("panic(\"GLINK SMEM alloc failed\")") < line.find("gd[1]=gd[2]=0"))(
            phase4_text.split("void veux_glink_init(void){", 1)[1].splitlines()[0]),
    "pas_metadata_uses_contiguous_standard_ram": all(x in phase4_text for x in (
        "const vm_size_t meta_alloc_size=(vm_size_t)ms;",
        "IOMallocContiguous(meta_alloc_size,0x1000,&meta_pa)",
        "IOFreeContiguous(meta,meta_alloc_size)",
        "(uint64_t)meta_pa", "VEUX MODEM PAS: copying mdt metadata",
        "VEUX MODEM PAS: metadata copied", "VEUX MODEM PAS: calling init_image")) and
        "veux_modem_pool_alloc(ms,&mpa)" not in phase4_text.replace(" ", ""),
    "pas_scm_pool_buffers_still_use_pool_va": "veux_modem_pool_alloc(0x1000,&pa)" in phase4_text.replace(" ", "") and "veux_modem_pool_va(pa,0x1000)" in phase4_text.replace(" ", ""),
    "pas_segments_use_per_segment_io_mapping_without_heap_alloc": all(x in phase4_text for x in (
        "veux_modem_map_phys(map_pa,map_len)", "MODEM_PA+ph[i].paddr",
        'extern "C" uintptr_t ml_io_map(uintptr_t, uintptr_t)', "ml_io_map((uintptr_t)pa,(uintptr_t)size)")) and
        "IOMemoryDescriptor::withPhysicalAddress" not in phase4_text and
        "veux_modem_segment_maps" not in phase4_text and
        not any(x in phase4_text.split("VEUX MODEM PAS: loading segments", 1)[1].split("VEUX MODEM PAS: segments loaded", 1)[0]
                for x in ("kmem_alloc(", "IOMalloc(", "veux_modem_pool_alloc(", "MODEM_POOL_SIZE")),
    "pas_carveout_zeroing_uses_volatile_pointer": all(x in phase4_patch_texts["0154-veux-modem-pas.patch"] for x in (
        "volatile uint8_t *zero_ptr=(volatile uint8_t *)(dst+ph[i].filesz)",
        "for(uint64_t k=0;k<(ph[i].memsz-ph[i].filesz);k++){zero_ptr[k]=0;}")) and
        "strb wzr" not in phase4_patch_texts["0154-veux-modem-pas.patch"] and
        "bzero(dst+ph[i].filesz" not in phase4_patch_texts["0154-veux-modem-pas.patch"],
    "ufs_modem_destination_copy_uses_volatile_pointer": all(x in phase4_patch_texts["0155-veux-modem-firmware.patch"] for x in (
        "volatile uint8_t *dest_ptr = (volatile uint8_t *)((uint8_t *)dst + done)",
        "const uint8_t *src_ptr = (const uint8_t *)(su.dma + DMA_BOUNCE) + skip",
        "dest_ptr[k] = src_ptr[k];")) and
        all(x in phase4_patch_texts["0162-veux-ufs-multilun.patch"] for x in (
            "volatile uint8_t *dest_ptr = (volatile uint8_t *)((uint8_t *)dst + done)",
            "dest_ptr[k] = src_ptr[k];")) and
        "ldrb %w0" not in phase4_patch_texts["0155-veux-modem-firmware.patch"] and
        "strb %w0" not in phase4_patch_texts["0155-veux-modem-firmware.patch"] and
        "ldrb %w0" not in phase4_patch_texts["0162-veux-ufs-multilun.patch"] and
        "strb %w0" not in phase4_patch_texts["0162-veux-ufs-multilun.patch"] and
        not any("memcpy((uint8_t *)dst + done" in line for line in
                phase4_patch_texts["0155-veux-modem-firmware.patch"].splitlines() if line.startswith("+")) and
        not any("memcpy((uint8_t *)dst + done" in line for line in
                phase4_patch_texts["0162-veux-ufs-multilun.patch"].splitlines() if line.startswith("+")),
    "ufs_modem_read_uses_existing_bounce_without_temp_heap": all(x in phase4_patch_texts["0162-veux-ufs-multilun.patch"] for x in (
        "BOUNCE_SIZE - skip", "su.dma + DMA_BOUNCE", "ufs_read_blocks(target_first + lba, blocks)")) and
        not any(re.search(r"\b(?:kalloc_data|kmem_alloc|IOMalloc|IOMallocContiguous)\s*\(", line)
                for line in phase4_patch_texts["0162-veux-ufs-multilun.patch"].splitlines() if line.startswith("+")),
    "glink_device_fifo_writes_use_volatile_bytes": all(x in phase4_text for x in (
        "static void peek(", "static uint32_t put(",
        "volatile uint8_t *dst_ptr=(volatile uint8_t *)dst",
        "volatile uint8_t *dst_ptr=(volatile uint8_t *)(gtx+h)",
        "for(uint32_t i=0;i<a;i++)dst_ptr[i]=src_ptr[i]")) and
        not any("memcpy(" in line or "memset(" in line for line in (
            phase4_text.split("static void peek(", 1)[1].splitlines()[0],
            phase4_text.split("static uint32_t put(", 1)[1].splitlines()[0])),
    "safe_unaligned_read_helpers_are_bytewise": all(x in phase4_patch_texts["0154-veux-modem-pas.patch"] for x in (
        "static inline uint16_t safe_read_u16(const void *p)",
        "static inline uint32_t safe_read_u32(const void *p)",
        "static inline uint64_t safe_read_u64(const void *p)",
        "const volatile uint8_t *b = (const volatile uint8_t *)p;",
        "return (uint64_t)safe_read_u32(b) | ((uint64_t)safe_read_u32(b + 4) << 32);")),
    "pdmap_unaligned_tlv_length_uses_safe_reader": "safe_read_u16(data+o+1)" in phase4_patch_texts["0157-veux-modem-pdmapper.patch"] and "memcpy(&l,data+o+1,2)" not in phase4_patch_texts["0157-veux-modem-pdmapper.patch"] and "((const volatile uint8_t *)(data+o+3))[k]" in phase4_patch_texts["0157-veux-modem-pdmapper.patch"] and "memcpy(name,data+o+3" not in phase4_patch_texts["0157-veux-modem-pdmapper.patch"],
    "wlfw_unaligned_fields_use_safe_readers": all(x in phase4_patch_texts["0158-veux-modem-wlfw.patch"] for x in (
        "safe_read_u16(d+o+1)", "safe_read_u16(v)", "safe_read_u16(v+2)",
        "safe_read_u16(d+3)", "safe_read_u64(v+1+13*i)", "safe_read_u32(v+9+13*i)",
        "safe_read_u32(v)", "safe_read_u32(v+4)")) and not any(
        x in phase4_patch_texts["0158-veux-modem-wlfw.patch"] for x in (
            "memcpy(&n,d+o+1,2)", "memcpy(&result,v,2)", "memcpy(&error,v+2,2)",
            "memcpy(&msg,d+3,2)", "memcpy(&a,v+1+13*i,8)", "memcpy(&z,v+9+13*i,4)",
            "memcpy(build,v,n)")) and "((const volatile uint8_t *)v)[i]" in phase4_patch_texts["0158-veux-modem-wlfw.patch"],
    "pas_free_sizes_match_captured_allocation_sizes": all(x in phase4_patch_texts["0154-veux-modem-pas.patch"] for x in (
        "const vm_size_t mdt_alloc_size=(vm_size_t)n;uint8_t *mdt=kalloc_data(mdt_alloc_size",
        "kfree_data(mdt,mdt_alloc_size)",
        "const vm_size_t meta_alloc_size=(vm_size_t)ms;",
        "IOMallocContiguous(meta_alloc_size,0x1000,&meta_pa)",
        "IOFreeContiguous(meta,meta_alloc_size)")),
    "ufs_read_blocks_has_no_temporary_heap_buffer": bool(ufs_read_body) and "ufs_scsi(cdb, sizeof(cdb), count * UFS_BLOCK, false)" in ufs_read_body and not re.search(r"\b(?:kalloc_data|kmem_alloc|IOMalloc|IOMallocContiguous)\s*\(", ufs_read_body),
    "forbidden_apcs_host_cap_bdf_wlan_paths_absent": not any(phase4_forbidden.values()),
    "ipcc_clock_note_is_evidence_gated": "no IPCC clock ID or branch" in phase4_text and "Do not guess a GCC write" in phase4_text,
    "ipcc_mapping_diagnostic_source": "VEUX IPCC: mapped pa=0x%08x va=%p size=0x%x attr=IO\\n" in phase4_patch_texts["0161-veux-ipcc-mapping-diagnostic.patch"],
    "modem_a_scans_luns_0_to_5_and_caches_location": all(x in phase4_patch_texts["0162-veux-ufs-multilun.patch"] for x in (
        "for (uint8_t lun = 0; lun <= 5; lun++)",
        "veux_modem_a_partition_valid", "veux_modem_a_first_block", "veux_modem_a_nblocks",
        "VEUX UFS: cached modem_a on LUN=%u")),
    "modem_main_thread_waits_uninterruptibly": all(x in phase4_text for x in (
        "assert_wait(&veux_modem_wait_chan,THREAD_UNINT)",
        "thread_block(THREAD_CONTINUE_NULL)", "veux_modem_hold();")),
}
if not all(phase4_sources.values()):
    raise SystemExit("VEUX Phase-4 source assertions failed: " + repr(phase4_sources) + " forbidden=" + repr(phase4_forbidden))
print("VEUX MODEM Phase-4 source assertions: PASS " + repr(phase4_sources))
phase4_binary = {
    "smem_zeroing_diagnostic": b"VEUX GLINK: zeroing SMEM item=%u size=0x%x\n" in kernel,
    "firmware_marker": b"VEUX MODEM FW:" in kernel,
    "pdmapper_marker": b"VEUX PDMAP:" in kernel,
    "adt_crc_log_format": b"VEUX DT: crc=0x%08x stage=%s\n" in kernel,
    "adt_crc_before_after_thread": b"before_modem_thread" in kernel and b"after_modem_thread" in kernel,
    "ipcc_mapping_diagnostic": b"VEUX IPCC: mapped pa=0x%08x va=%p size=0x%x attr=IO\n" in kernel,
    "modem_a_multilun_cache": b"VEUX UFS: cached modem_a on LUN=%u first=0x%llx blocks=0x%llx\n" in kernel,
    "pas_metadata_copy_checkpoints": all(x in kernel for x in (
        b"VEUX MODEM PAS: copying mdt metadata\n",
        b"VEUX MODEM PAS: metadata copied\n",
        b"VEUX MODEM PAS: calling init_image\n")),
    "pas_segment_copy_checkpoints": all(x in kernel for x in (
        b"VEUX MODEM PAS: loading segments\n",
        b"VEUX MODEM PAS: segments loaded\n")),
    "glink_startup_diagnostics": all(x in kernel for x in (
        b"VEUX GLINK: requesting SMEM items 478, 479, 480\n",
        b"VEUX GLINK: desc va=0x%llx tx_va=0x%llx rx_va=0x%llx\n",
        b"VEUX GLINK: mapped SMEM\n",
        b"VEUX GLINK: mapped SMEM (write-combine)\n",
        b"VEUX GLINK: copying RX data\n",
        b"VEUX QRTR: processing packet\n",
        b"VEUX GLINK: sending VERSION\n",
        b"VEUX GLINK: poll loop entered\n")),
}
if not all(phase4_binary.values()):
    raise SystemExit("VEUX Phase-4 binary marker checks failed: " + repr(phase4_binary))
print("VEUX MODEM Phase-4 binary markers: PASS " + repr(phase4_binary))
modem_needles = {
    "pas_parameters": b"VEUX MODEM PAS: pas_id=4 carveout=0x8b800000+0x10000000 smem=0x80900000 tcsr=0x00340000 hwlock=3",
    "pas_mdt_copying": b"VEUX MODEM PAS: copying mdt metadata",
    "pas_metadata_copied": b"VEUX MODEM PAS: metadata copied",
    "pas_calling_init_image": b"VEUX MODEM PAS: calling init_image",
    "pas_loading_segments": b"VEUX MODEM PAS: loading segments",
    "pas_segments_loaded": b"VEUX MODEM PAS: segments loaded",
    "ipcc_parameters": b"VEUX IPCC: pa=0x00208000 mpss=2 smp2p=2 glink_qmp=0 gic_spi=334",
    "smp2p_ready": b"VEUX MODEM: SMP2P READY",
    "glink_version_ack": b"VEUX GLINK: VERSION_ACK",
    "glink_smem_request": b"VEUX GLINK: requesting SMEM items 478, 479, 480",
    "glink_smem_addresses": b"VEUX GLINK: desc va=0x%llx tx_va=0x%llx rx_va=0x%llx",
    "glink_send_version": b"VEUX GLINK: sending VERSION",
    "glink_poll_loop_entered": b"VEUX GLINK: poll loop entered",
    "glink_smem_map_attr": b"VEUX GLINK: mapped SMEM",
    "glink_copy_rx_data": b"VEUX GLINK: copying RX data",
    "qrtr_processing_packet": b"VEUX QRTR: processing packet",
    "smem_zeroing": b"VEUX GLINK: zeroing SMEM item=%u size=0x%x",
    "glink_open_ack_ipcrtr": b"VEUX GLINK: OPEN_ACK IPCRTR",
    "qrtr_hello": b"VEUX QRTR: HELLO",
    "qrtr_wlfw_server": b"VEUX QRTR: NEW_SERVER 0x45",
    "wlfw_ind_register": b"VEUX WLFW: ind_register ok",
    "wlfw_msa_info": b"VEUX WLFW: msa_info ok",
    "wlfw_msa_ready": b"VEUX WLFW: msa_ready ok",
    "wlfw_cap": b"VEUX WLFW: cap ok",
    "wlfw_chip_id": b"VEUX WLFW: chip_id",
    "modem_hold": b"VEUX MODEM HOLD: wfe",
}
missing_modem = [name for name, marker in modem_needles.items() if marker not in kernel]
if missing_modem:
    raise SystemExit("missing modem markers: " + ", ".join(missing_modem))

forbidden_modem_markers = (
    b"VEUX WLFW: host_cap sent",
    b"VEUX WLFW: bdf",
    b"VEUX WLFW: cal_report",
    b"VEUX WLFW: wlan_cfg",
    b"VEUX WLFW: wlan_mode",
    b"VEUX CE:",
    b"VEUX HTC:",
    b"VEUX WMI:",
    b"VEUX SCAN:",
)
present_forbidden_modem = [marker.decode("ascii") for marker in forbidden_modem_markers if marker in kernel]
if present_forbidden_modem:
    raise SystemExit("forbidden modem/WLAN markers in kernel: " + ", ".join(present_forbidden_modem))

modem_sources = [p for p in a.source_root.rglob("*") if p.is_file() and p.suffix in {".c", ".cc", ".cpp", ".h"}]
modem_source_text = "\n".join(p.read_text(errors="replace") for p in modem_sources)
missing_modem_source = [name for name, marker in modem_needles.items()
                        if marker.decode("ascii") not in modem_source_text]
if missing_modem_source:
    raise SystemExit("missing modem source markers: " + ", ".join(missing_modem_source))
forbidden_modem_source = (
    "VEUX WLFW: host_cap sent", "VEUX WLFW: bdf", "VEUX WLFW: cal_report",
    "VEUX WLFW: wlan_cfg", "VEUX WLFW: wlan_mode", "VEUX CE:", "VEUX HTC:",
    "VEUX WMI:", "VEUX SCAN:",
)
present_forbidden_source = [marker for marker in forbidden_modem_source if marker in modem_source_text]
if present_forbidden_source:
    raise SystemExit("forbidden modem/WLAN source markers: " + ", ".join(present_forbidden_source))

checks.update({f"modem_{name}": marker in kernel for name, marker in modem_needles.items()})
source_checks = {}
vfs = (a.source_root / "bsd/vfs/vfs_subr.c").read_text()
ufs = (a.source_root / "bsd/dev/sweet_ufs.c").read_text()
serial = (a.source_root / "pexpert/arm/pe_serial.c").read_text()
touch_probe = (a.source_root / "bsd/dev/veux_touch_probe.c").read_text()
touch_active = (a.source_root / "bsd/dev/veux_touch_active.c").read_text()
touch_driver = (a.source_root / "bsd/dev/sweet_touch.c").read_text()
early = (a.source_root / "osfmk/arm64/veux_early.c").read_text()
fb_init = serial.split("veux_fb_init(void)", 1)[1].split("veux_fb_console_putc(char c)", 1)[0]
stage_fn = early.split("veux_stage_mark_nb(unsigned int cell)", 1)[1].split("veux_stage_flush(void)", 1)[0]
source_checks["framebuffer_console_is_bootarg_gated_and_normal_status_is_temporary"] = (
    'PE_parse_boot_argn("veuxfb", &diagnostic, sizeof(diagnostic))' in fb_init
    and 'PE_parse_boot_argn("veuxfbconsole", &diagnostic, sizeof(diagnostic))' in fb_init
    and "veux_fb_normal_status_draw(void)" in serial
    and "veux_fb_normal_status_clear(void)" in serial
    and "veux_fb_normal_status_clear();" in (a.source_root / "iokit/Kernel/arm/SweetFramebuffer.cpp").read_text()
    and "variant=normal ID=" in serial
)
source_checks["veux_touch_tlmm_ab_dump_is_read_only_and_held_before_mount"] = (
    'PE_parse_boot_argn("veuxtouchprobe", &enabled, sizeof(enabled))' in touch_probe
    and 'PE_parse_boot_argn("veuxtouchprobehold", &hold, sizeof(hold))' in touch_probe
    and "VEUX_TOUCH_TLMM_ALT_PA 0x00500000u" in touch_probe
    and "VEUX_TOUCH_TLMM_PA     0x00400000u" in touch_probe
    and "volatile uint32_t" in touch_probe
    and "touch_probe_tlmm_cfg_once(alt, VEUX_TOUCH_TLMM_ALT_PA, pin, seq)" in touch_probe
    and "touch_probe_tlmm_cfg_once(primary, VEUX_TOUCH_TLMM_PA, pin, seq)" in touch_probe
    and "static const unsigned touch_pins[] = {19, 20, 21, 22, 44, 51}" in touch_probe
    and "for (unsigned pin = 4; pin < 64; ++pin)" in touch_probe
    and "VEUX TLMM BEFORE #%u pin=%u CFG PA=" in touch_probe
    and "VEUX TLMM AFTER pin=%u CFG PA=" in touch_probe
    and "VEUX TLMM FAULT pin=%u PA=" in touch_probe
    and "veux_fb_touch_probe_checkpoint(seq, pin," in touch_probe
    and "read-only per-pin CFG comparison complete; GPIO0-3 skipped; no UFS/GPIO writes" in touch_probe
    and "veux_touch_probe_fault_note(esr, far, get_saved_state_pc(&context->ss))" in (a.source_root / "osfmk/arm64/sleh.c").read_text()
    and 'for (;;) __asm__ volatile("wfe"' in touch_probe
    and "VEUX TOUCH PROBE: refusing non-held mode; this diagnostic is read-only" in touch_probe
    and 'veux_touch_probe_init();' in ufs
    and ufs.index('veux_touch_probe_init();') < ufs.index('sweet_ufs_rootdev(')
)

source_checks["pmap_nofault_translation_probe_removed_from_touch_startup"] = (
    "touch_tlmm_map_check" not in (a.source_root / "bsd/dev/sweet_touch.c").read_text()
    and "pmap_find_phys_nofault" not in (a.source_root / "bsd/dev/sweet_touch.c").read_text()
)
source_checks["both_full_boot_variants_are_manifested_and_safe"] = (
    {"rootrw=1", "ufsrw=1", "veuxvariant=normal"}.issubset(boot_args)
    and {"veuxtouchprobe=1", "veuxtouchprobehold=1", "veuxvariant=held"}.issubset(held_boot_args)
    and not ({"rootrw=1", "ufsrw=1", "veuxtouchprobeactive=1", "veuxlog=1"} & held_boot_args)
)
source_checks["active_touch_probe_remains_separate_from_read_only_held_path"] = (
    "veux_touch_active_probe" not in touch_probe
    and "0x4022" in touch_active
    and "touch_active_gpio_cfg" in touch_active
)
source_checks["veux_active_touch_uses_regbase_adjusted_tlmm"] = (
    "#define TOUCH_NORTH_PA   0x00500000u /* phone DT base + Blair REG_BASE */" in touch_driver
    and "#define TOUCH_GPIO_SDA   19u" in touch_driver
    and "#define TOUCH_GPIO_SCL   20u" in touch_driver
    and "#define TOUCH_GPIO_RESET 21u" in touch_driver
    and "#define TOUCH_GPIO_IRQ   22u" in touch_driver
)
source_checks["veux_geni_fifo_sequence_matches_linux"] = (
    "/* Linux arms TX FIFO watermark after issuing I2C_WRITE. */" in touch_driver
    and touch_driver.index("touch_wr(st.se, SE_CMD", touch_driver.index("touch_msg_run(uint8_t addr"))
        < touch_driver.index("touch_wr(st.se, SE_TX_WM, 1u);", touch_driver.index("touch_msg_run(uint8_t addr"))
    and "touch_wr(st.se, 0x810, tx_depth - 1u);" in touch_driver
    and "touch_wr(st.se, 0x814, tx_depth);" in touch_driver
    and "touch_wr(st.se, 0xe1c, 0); /* mask external IRQ routing; poll local status */" in touch_driver
)
source_checks["veux_gpio_i2c_fallback_when_fifo_disabled"] = (
    "st.gpio_i2c = if_disable != 0;" in touch_driver
    and "FIFO disabled by hardware; using GPIO I2C" in touch_driver
    and "touch_gpio_i2c_read_reg(addr, reg, wide, buf, len)" in touch_driver
    and "touch_gpio_i2c_write_reg(0x5d, GOODIX_EVENT_REG, 0)" in touch_driver
    and "unsigned bus_mux = st.gpio_i2c ? 0u : 1u;" in touch_driver
    and "TOUCH: I2C transfer=0x" in serial
    and "veux_fb_touch_status(17, goodix ? 0x9896u : 0x5452u);" in touch_driver
    and "TOUCH: IC detected=0x" in serial
)
source_checks["veux_touch_overlay_disabled_with_touch_driver_enabled"] = (
    "veux_fb_touch_status_draw(unsigned int state, unsigned int detail, unsigned int row)" in serial
    and "Touch works; keep the diagnostic lockscreen overlay disabled." in serial
    and "(void)state;" in serial
    and "(void)detail;" in serial
    and "Do not clear the overlay area on GUI handoff." in serial
    and "static int\ntouch_gpio_i2c_read_reg" in touch_driver
    and "st.gpio_i2c = if_disable != 0;" in touch_driver
    and "void sweet_touch_init(void)" in touch_driver
    and "veux_fb_touch_status(17, goodix ? 0x9896u : 0x5452u);" in touch_driver
)

source_checks["direct_framebuffer_build_id_print"] = (
    'veux_fb_print_build_id();' in fb_init
    and 'VEUX BUILD: ID=' in serial
    and 'veux_fb_console_putc(build_id_line[i])' in serial
)
live_sampler = (a.source_root / "bsd/dev/veux_liveness.c").read_text()
exception = (a.source_root / "osfmk/kern/exception.c").read_text()
exit_source = (a.source_root / "bsd/kern/kern_exit.c").read_text()
source_checks["read_only_gpi_summary_replayed_after_console_scroll"] = (
    "veux_gpi_preflight_report();" in live_sampler
    and "gpi_report_count < 3" in live_sampler
    and "gpi_summary_complete" in (a.source_root / "bsd/dev/veux_gpi_preflight.c").read_text()
    and "VEUX GPI SUMMARY: state=%s hook=%u arg=%u enabled=%u map=%u/%u" in (a.source_root / "bsd/dev/veux_gpi_preflight.c").read_text()
    and "kernel_thread_start(gpi_summary_thread" in (a.source_root / "bsd/dev/veux_gpi_preflight.c").read_text()
    and "tsleep(&gpi_summary_sleep_chan" in (a.source_root / "bsd/dev/veux_gpi_preflight.c").read_text()
)
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
    "variants": {
        "normal": {"boot_args": a.boot_args, "root_mode_requested": "rw"},
        "held": {"boot_args": a.held_boot_args, "root_mode_requested": "ro", "probe": "read-only CFG reads at PA 0x503000 and 0x513000; WFE before root mount"},
        "modem-held": {"boot_args": a.modem_held_boot_args, "root_mode_requested": "ro", "probe": "read-only modem PAS/GLINK/QRTR/WLFW CAP diagnostic; WFE before root mount"},
    },
    "boot_args": a.boot_args,
    "held_boot_args": a.held_boot_args,
    "modem_held_boot_args": a.modem_held_boot_args,
    "root_mode_requested": "rw",
    "wrapper": "assembled on host with the phone DTB; see adjacent wrapper manifest",
}
a.output.parent.mkdir(parents=True, exist_ok=True)
a.output.write_text(json.dumps(manifest, indent=2) + "\n")
print(f"VEUX BUILD ID: {a.build_id}")
print(f"kernel_sha256={manifest['kernel_sha256']}")
print(a.output)
