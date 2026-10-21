#!/bin/sh
# Read the VEUX XNU log ring from userdata while the phone is in recovery ADB.
set -eu

usage() {
    echo "Usage: $(basename "$0") [-s SERIAL] [OUT.txt]" >&2
    echo "Reads only the final 4 MiB + 4 KiB of userdata and decodes it on the Mac." >&2
}

ADB="adb"
if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
    usage
    exit 0
fi
if [ "${1:-}" = "-s" ]; then
    [ "$#" -ge 2 ] || { usage; exit 2; }
    ADB="adb -s $2"
    shift 2
fi

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
out=${1:-"$repo_dir/research/veux-logs/xnu-veux-$(date +%Y%m%d-%H%M%S).txt"}
command -v adb >/dev/null 2>&1 || { echo "adb not found in PATH" >&2; exit 1; }

# Partition sysfs size is expressed in 512-byte sectors; UFS uses 4096-byte blocks.
dev=$($ADB shell 'readlink -f /dev/block/by-name/userdata' 2>/dev/null | tr -d '\r')
[ -n "$dev" ] || { echo "userdata block device not found" >&2; exit 1; }
name=${dev##*/}
sectors=$($ADB shell "cat /sys/class/block/$name/size" | tr -d '\r')
case "$sectors" in *[!0-9]*|'') echo "invalid userdata block count: $sectors" >&2; exit 1;; esac
blocks=$((sectors / 8))
ring_blocks=1025
[ "$blocks" -gt "$ring_blocks" ] || { echo "userdata partition is too small" >&2; exit 1; }
skip=$((blocks - ring_blocks))
raw=$(mktemp "${TMPDIR:-/tmp}/veux-log.XXXXXX")
trap 'rm -f "$raw"' EXIT HUP INT TERM
$ADB exec-out "dd if=$dev bs=4096 skip=$skip count=$ring_blocks 2>/dev/null" > "$raw"
python3 "$repo_dir/tools/veux-log.py" "$raw" "$out"
echo "Saved decoded XNU log: $out" >&2
