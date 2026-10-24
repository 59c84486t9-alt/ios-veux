#!/usr/bin/env python3
"""Validate repository integrity, patch sequences, and script syntax.

  tools/validate-repo.py [--verbose]

Checks:
  1. Patch sequence in xnu/patches/:
     - Sequential numbering starting at 0001 with no duplicates or gaps,
       except 0097, which was merged into 0088.
     - Patch files are non-empty and have valid unified diff markers.
  2. Python script syntax:
     - All tools/*.py compile cleanly via py_compile.
  3. Shell script syntax:
     - All tools/*.sh, shim/*.sh, and xnu/patches/*.sh pass bash -n check.
"""
import argparse, glob, os, py_compile, re, subprocess, sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def green(text): return f"\033[92m{text}\033[0m"
def red(text): return f"\033[91m{text}\033[0m"
def bold(text): return f"\033[1m{text}\033[0m"


def validate_patches(verbose=False):
    patch_dir = os.path.join(REPO_ROOT, 'xnu/patches')
    patch_files = sorted(glob.glob(os.path.join(patch_dir, '*.patch')))
    if not patch_files:
        print(red("[-] Error: No patch files found in xnu/patches/"))
        return False

    errors = []
    seen_numbers = {}

    for path in patch_files:
        fname = os.path.basename(path)
        m = re.match(r'^(\d{4})-(.+)\.patch$', fname)
        if not m:
            errors.append(f"Invalid patch filename format: {fname}")
            continue

        num = int(m.group(1))
        if num in seen_numbers:
            errors.append(f"Duplicate patch number {num:04d}: {fname} and {seen_numbers[num]}")
        seen_numbers[num] = fname

        size = os.path.getsize(path)
        if size == 0:
            errors.append(f"Patch is empty: {fname}")
            continue

        with open(path, 'r', errors='ignore') as f:
            patch_text = f.read()
            head = patch_text[:2048]
            if not ('--- ' in head or 'diff ' in head or 'Index:' in head):
                errors.append(f"Patch missing standard diff header: {fname}")

            # Repeated diff sections for one path usually mean a malformed
            # patch boundary (a common cause of silent/partial application).
            diff_paths = re.findall(r'^diff --git a/(.*?) b/.*$', patch_text, re.M)
            duplicates = sorted({p for p in diff_paths if diff_paths.count(p) > 1})
            if duplicates:
                errors.append(f"Repeated diff section(s) in {fname}: {', '.join(duplicates)}")

            if '.rej' in fname or '.orig' in fname:
                errors.append(f"Patch artifact must not be tracked as a patch: {fname}")

    # Check contiguous sequence
    if seen_numbers:
        sorted_nums = sorted(seen_numbers.keys())
        expected = 1
        for num in sorted_nums:
            # Patch 0097 was intentionally folded into 0088 after both patches
            # targeted sweet_ufs.c. Keep the historical numbering of later
            # patches so notes and diagnostics remain stable.
            if expected == 97 and num == 98:
                expected = num
            if num != expected:
                errors.append(f"Gap in patch sequence: expected {expected:04d}, found {num:04d} ({seen_numbers[num]})")
                expected = num + 1
            else:
                expected += 1

    # The liveness patch directly inspects kernel task/thread and process
    # accounting structures. Keep its private-header contract explicit: the
    # build must see complete definitions and the canonical saved-state
    # helpers, rather than local declarations that can conflict with XNU.
    liveness_path = os.path.join(patch_dir, '0117-veux-post-early-boot-liveness.patch')
    if os.path.exists(liveness_path):
        with open(liveness_path, 'r', errors='ignore') as f:
            liveness = f.read()
        required_liveness = (
            '+#define MACH_KERNEL_PRIVATE 1',
            '+#include <kern/zalloc.h>',
            '+#include <sys/resourcevar.h>',
            '+#define task_get_proc_raw veux_unused_task_get_proc_raw',
            '+#define ZONE_DECLARE_ID(id, type)',
            '+#undef ZONE_DECLARE_ID',
            '+#undef task_get_proc_raw',
            '+#include <kern/task.h>',
            '+#include <kern/thread.h>',
            '+#include <arm/thread.h>',
            '+#include <mach/arm/thread_status.h>',
            '+void veux_liveness_start(void);',
        )
        for token in required_liveness:
            if token not in liveness:
                errors.append(f"0117 liveness source is missing required XNU API declaration/include: {token[1:]}")
        forbidden_liveness = (
            '+extern uint64_t get_saved_state_pc(',
            '+extern boolean_t is_saved_state64(',
            '+extern arm_saved_state_t *find_user_regs(',
        )
        for token in forbidden_liveness:
            if token in liveness:
                errors.append(f"0117 must use XNU's canonical declaration, not redeclare: {token[1:]}")

    if errors:
        print(red(f"[-] Patch validation failed with {len(errors)} error(s):"))
        for err in errors:
            print(f"    - {err}")
        return False

    print(green(f"[✓] Validated {len(patch_files)} patches (0001-{max(seen_numbers):04d}; 0097 merged into 0088; format OK)"))
    return True


def validate_python_scripts(verbose=False):
    tools_dir = os.path.join(REPO_ROOT, 'tools')
    py_files = sorted(glob.glob(os.path.join(tools_dir, '*.py')))
    errors = []

    for path in py_files:
        fname = os.path.basename(path)
        try:
            py_compile.compile(path, doraise=True)
            if verbose:
                print(f"    [OK] {fname}")
        except py_compile.PyCompileError as e:
            errors.append(f"{fname}: {e}")

    if errors:
        print(red(f"[-] Python syntax validation failed with {len(errors)} error(s):"))
        for err in errors:
            print(f"    - {err}")
        return False

    print(green(f"[✓] Validated {len(py_files)} Python tools (syntax OK)"))
    return True


def validate_shell_scripts(verbose=False):
    sh_files = sorted(
        glob.glob(os.path.join(REPO_ROOT, 'tools/*.sh')) +
        glob.glob(os.path.join(REPO_ROOT, 'shim/*.sh')) +
        glob.glob(os.path.join(REPO_ROOT, 'xnu/patches/*.sh'))
    )
    errors = []

    for path in sh_files:
        rel = os.path.relpath(path, REPO_ROOT)
        res = subprocess.run(['bash', '-n', path], capture_output=True, text=True)
        if res.returncode != 0:
            errors.append(f"{rel}: {res.stderr.strip()}")
        elif verbose:
            print(f"    [OK] {rel}")

    if errors:
        print(red(f"[-] Shell syntax validation failed with {len(errors)} error(s):"))
        for err in errors:
            print(f"    - {err}")
        return False

    print(green(f"[✓] Validated {len(sh_files)} Shell scripts (syntax OK)"))
    return True


def main():
    ap = argparse.ArgumentParser(description="Validate repository integrity, patches, and scripts.")
    ap.add_argument('-v', '--verbose', action='store_true', help='Show detailed per-file output')
    a = ap.parse_args()

    print(bold("=== Running ios-sweet Repository Validation ==="))
    ok_patches = validate_patches(a.verbose)
    ok_python = validate_python_scripts(a.verbose)
    ok_shell = validate_shell_scripts(a.verbose)

    if ok_patches and ok_python and ok_shell:
        print(bold(green("\nAll repository integrity checks PASSED successfully!")))
        return 0
    else:
        print(bold(red("\nRepository integrity check FAILED.")))
        return 1


if __name__ == '__main__':
    sys.exit(main())
