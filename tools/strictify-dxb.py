#!/usr/bin/env python3
"""Make the pinned darwin-xnu-build patch phase fail closed."""
from pathlib import Path
import sys

build = Path(sys.argv[1])
text = build.read_text()
start = text.index('        if compgen -G "${PATCH_DIR}"\'/*.sh\' > /dev/null; then')
end_marker = '        cd "${WORK_DIR}"\n'
end = text.index(end_marker, start)
replacement = '''        STATUS_FILE="${PATCH_STATUS_FILE:-${WORK_DIR}/patch-status.txt}"
        : > "${STATUS_FILE}"
        find "${WORK_DIR}/xnu" -type f \\( -name '*.rej' -o -name '*.orig' \\) -print -quit | grep -q . && {
            echo "stale .rej/.orig file found before patching" >&2; exit 1;
        }
        if compgen -G "${PATCH_DIR}"'/*.sh' > /dev/null; then
            for SCRIPT in "${PATCH_DIR}"/*.sh; do
                printf 'PATCH_STATUS: %s RUNNING\\n' "$(basename "${SCRIPT}")" | tee -a "${STATUS_FILE}"
                if KDKROOT="${KDKROOT}" bash "${SCRIPT}"; then
                    printf 'PATCH_STATUS: %s APPLIED\\n' "$(basename "${SCRIPT}")" | tee -a "${STATUS_FILE}"
                else
                    printf 'PATCH_STATUS: %s FAILED\\n' "$(basename "${SCRIPT}")" | tee -a "${STATUS_FILE}"
                    exit 1
                fi
            done
        fi
        PATCH_COUNT=0
        if ! compgen -G "${PATCH_DIR}"'/*.patch' > /dev/null; then
            echo "no patches found in selected patch directory: ${PATCH_DIR}" >&2; exit 1;
        fi
        for PATCH in "${PATCH_DIR}"/*.patch; do
            PATCH_NAME=$(basename "${PATCH}")
            if [ "${MACOS_VERSION}" = "13.5" ]; then
                case "${PATCH_NAME}" in
                    TrustCache.patch|iobuffermemd_monterey.patch|skywalk_sonoma.patch|syntax_checker_sonoma.patch)
                        printf 'PATCH_STATUS: %s NOT_SELECTED (not applicable to macOS 13.5 source)\\n' "${PATCH_NAME}" | tee -a "${STATUS_FILE}"
                        continue
                        ;;
                esac
            fi
            PATCH_COUNT=$((PATCH_COUNT + 1))
            printf 'PATCH_STATUS: %s CHECKING (fuzz_limit=0)\\n' "${PATCH_NAME}" | tee -a "${STATUS_FILE}"
            if APPLY_CHECK=$(git apply --check "${PATCH}" 2>&1); then
                if git apply "${PATCH}"; then
                    printf 'PATCH_STATUS: %s APPLIED\\n' "${PATCH_NAME}" | tee -a "${STATUS_FILE}"
                else
                    printf 'PATCH_STATUS: %s FAILED (apply)\\n' "${PATCH_NAME}" | tee -a "${STATUS_FILE}"
                    exit 1
                fi
            else
                printf 'PATCH_STATUS: %s FAILED (check): %s\\n' "${PATCH_NAME}" "${APPLY_CHECK}" | tee -a "${STATUS_FILE}"
                exit 1
            fi
        done
        if find "${WORK_DIR}/xnu" -type f \\( -name '*.rej' -o -name '*.orig' \\) -print -quit | grep -q .; then
            echo "patch created a .rej/.orig file" >&2; exit 1
        fi
        [ "${PATCH_COUNT}" -gt 0 ] || { echo "no patches selected" >&2; exit 1; }
        echo "PATCH_STATUS: patch phase passed (${PATCH_COUNT} selected patches checked; exact context, fuzz_limit=0)"
'''
text = text[:start] + replacement + text[end:]
build.write_text(text)
