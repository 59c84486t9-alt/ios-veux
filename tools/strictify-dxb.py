#!/usr/bin/env python3
"""Rewrite darwin-xnu-build's patch phase to enforce exact, audited outcomes."""
from pathlib import Path
import sys

build = Path(sys.argv[1])
text = build.read_text()
start = text.index('        if compgen -G "${PATCH_DIR}"\'/*.sh\' > /dev/null; then')
end = text.index('        cd "${WORK_DIR}"\n', start)
replacement = r'''        STATUS_FILE="${PATCH_STATUS_FILE:-${WORK_DIR}/patch-status.txt}"
        ALLOWLIST_FILE="${PATCH_ALLOWLIST_FILE:-${WORK_DIR}/patch-skip-allowlist.txt}"
        : > "${STATUS_FILE}"
        test -s "${ALLOWLIST_FILE}" || { echo "missing patch skip allowlist: ${ALLOWLIST_FILE}" >&2; exit 1; }
        find "${WORK_DIR}/xnu" -type f \( -name '*.rej' -o -name '*.orig' \) -print -quit | grep -q . && {
            echo "stale .rej/.orig file found before patching" >&2; exit 1;
        }
        if compgen -G "${PATCH_DIR}"'/*.sh' > /dev/null; then
            for SCRIPT in "${PATCH_DIR}"/*.sh; do
                printf 'PATCH_STATUS: %s RUNNING\n' "$(basename "${SCRIPT}")" | tee -a "${STATUS_FILE}"
                if KDKROOT="${KDKROOT}" bash "${SCRIPT}"; then
                    printf 'PATCH_STATUS: %s APPLIED\n' "$(basename "${SCRIPT}")" | tee -a "${STATUS_FILE}"
                else
                    printf 'PATCH_STATUS: %s FAILED\n' "$(basename "${SCRIPT}")" | tee -a "${STATUS_FILE}"
                    exit 1
                fi
            done
        fi
        ALLOWLIST_NAMES="|"
        while IFS=$'\t' read -r PATCH_NAME REASON EXPECTED; do
            [[ -z "${PATCH_NAME}" || "${PATCH_NAME}" == \#* ]] && continue
            [[ -n "${REASON}" && -n "${EXPECTED}" ]] || { echo "allowlist reason/signature missing: ${PATCH_NAME}" >&2; exit 1; }
            case "${ALLOWLIST_NAMES}" in *"|${PATCH_NAME}|"*) echo "duplicate allowlist entry: ${PATCH_NAME}" >&2; exit 1;; esac
            ALLOWLIST_NAMES+="${PATCH_NAME}|"
        done < "${ALLOWLIST_FILE}"
        [[ "${ALLOWLIST_NAMES}" != "|" ]] || { echo "empty patch skip allowlist" >&2; exit 1; }
        while IFS=$'\t' read -r PATCH_NAME REASON EXPECTED; do
            [[ -z "${PATCH_NAME}" || "${PATCH_NAME}" == \#* ]] && continue
            [[ -f "${PATCH_DIR}/${PATCH_NAME}" ]] || {
                printf 'PATCH_STATUS: %s ALLOWLIST_STALE (file missing)\n' "${PATCH_NAME}" | tee -a "${STATUS_FILE}"
                exit 1
            }
        done < "${ALLOWLIST_FILE}"
        PATCH_COUNT=0
        ALLOWLIST_SEEN="|"
        if ! compgen -G "${PATCH_DIR}"'/*.patch' > /dev/null; then
            echo "no patches found in selected patch directory: ${PATCH_DIR}" >&2; exit 1;
        fi
        for PATCH in "${PATCH_DIR}"/*.patch; do
            PATCH_NAME=$(basename "${PATCH}")
            PATCH_COUNT=$((PATCH_COUNT + 1))
            printf 'PATCH_STATUS: %s CHECKING (fuzz_limit=0)\n' "${PATCH_NAME}" | tee -a "${STATUS_FILE}"
            if APPLY_CHECK=$(git apply --recount --check "${PATCH}" 2>&1); then
                case "${ALLOWLIST_NAMES}" in *"|${PATCH_NAME}|"*)
                    REASON=$(awk -F '\t' -v name="${PATCH_NAME}" '$1 == name {print $2}' "${ALLOWLIST_FILE}")
                    printf 'PATCH_STATUS: %s ALLOWLIST_STALE (now applies; reason: %s)\n' "${PATCH_NAME}" "${REASON}" | tee -a "${STATUS_FILE}"
                    exit 1
                    ;;
                esac
                if git apply --recount "${PATCH}"; then
                    printf 'PATCH_STATUS: %s APPLIED\n' "${PATCH_NAME}" | tee -a "${STATUS_FILE}"
                else
                    printf 'PATCH_STATUS: %s FAILED (apply)\n' "${PATCH_NAME}" | tee -a "${STATUS_FILE}"
                    exit 1
                fi
            else
                case "${ALLOWLIST_NAMES}" in *"|${PATCH_NAME}|"*)
                    ALLOWLIST_SEEN+="${PATCH_NAME}|"
                    REASON=$(awk -F '\t' -v name="${PATCH_NAME}" '$1 == name {print $2}' "${ALLOWLIST_FILE}")
                    EXPECTED=$(awk -F '\t' -v name="${PATCH_NAME}" '$1 == name {print $3}' "${ALLOWLIST_FILE}")
                    case "${APPLY_CHECK}" in *"${EXPECTED}"*) ;;
                    *) printf 'PATCH_STATUS: %s FAILED (skip signature changed; expected: %s; detail: %s)\n' "${PATCH_NAME}" "${EXPECTED}" "${APPLY_CHECK//$'\n'/; }" | tee -a "${STATUS_FILE}"; exit 1;;
                    esac
                    printf 'PATCH_STATUS: %s ALLOWLISTED_SKIP (reason: %s; detail: %s)\n' "${PATCH_NAME}" "${REASON}" "${APPLY_CHECK//$'\n'/; }" | tee -a "${STATUS_FILE}"
                    ;;
                *)
                    printf 'PATCH_STATUS: %s FAILED (unallowlisted skip): %s\n' "${PATCH_NAME}" "${APPLY_CHECK//$'\n'/; }" | tee -a "${STATUS_FILE}"
                    exit 1
                    ;;
                esac
            fi
        done
        while IFS=$'\t' read -r PATCH_NAME REASON EXPECTED; do
            [[ -z "${PATCH_NAME}" || "${PATCH_NAME}" == \#* ]] && continue
            case "${ALLOWLIST_SEEN}" in *"|${PATCH_NAME}|"*) ;;
            *)
                printf 'PATCH_STATUS: %s ALLOWLIST_STALE (expected skip was not observed)\n' "${PATCH_NAME}" | tee -a "${STATUS_FILE}"
                exit 1
                ;;
            esac
        done < "${ALLOWLIST_FILE}"
        if find "${WORK_DIR}/xnu" -type f \( -name '*.rej' -o -name '*.orig' \) -print -quit | grep -q .; then
            echo "patch created a .rej/.orig file" >&2; exit 1
        fi
        echo "PATCH_STATUS: patch phase passed (${PATCH_COUNT} patches; allowlisted skips recorded; exact context, fuzz_limit=0)"
'''
text = text[:start] + replacement + text[end:]
build.write_text(text)
