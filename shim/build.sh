#!/bin/bash
# Build the shim and wrap it in a boot.img v2 that mirrors the stock PixelOS header.
set -euo pipefail
cd "$(dirname "$0")"
CC=${CROSS_COMPILE:-aarch64-linux-gnu-}gcc
OBJCOPY=${CROSS_COMPILE:-aarch64-linux-gnu-}objcopy
mode=sweet
dtb=../dtb/boot_unpacked/dtb
output=out/shim-boot.img
payload=
ci_kernel=
ci_run_id=
build_id=
boot_args=
patch_status=
variants_manifest=
variant=
while [ $# -gt 0 ]; do
	case "$1" in
		--veux) mode=veux; shift ;;
		--dtb) dtb=$2; shift 2 ;;
		--output) output=$2; shift 2 ;;
		--ci-kernel) ci_kernel=$2; shift 2 ;;
		--ci-run-id) ci_run_id=$2; shift 2 ;;
		--build-id) build_id=$2; shift 2 ;;
		--boot-args) boot_args=$2; shift 2 ;;
		--patch-status) patch_status=$2; shift 2 ;;
		--variants-manifest) variants_manifest=$2; shift 2 ;;
		--variant) variant=$2; shift 2 ;;
		-*) echo "usage: $0 [--veux] [--dtb DTB] [--output IMAGE] [--ci-kernel KERNEL --ci-run-id ID --build-id ID --boot-args ARGS --patch-status FILE] [PAYLOAD]" >&2; exit 2 ;;
		*) [ -z "$payload" ] || { echo "only one payload may be specified" >&2; exit 2; }; payload=$1; shift ;;
	esac
done
if [ "$variant" = modem-held ]; then
	expected='debug=0xc serial=3 cpus=1 keepsyms=1 -enable_kprintf_spam -noprogress rd=ufsroot0 modem=1 modem_watch=180 veuxfbconsole=1'
	[ "$boot_args" = "$expected" ] || { echo "modem-held wrapper requires the exact Phase-1 boot args" >&2; exit 2; }
	[ -n "$variants_manifest" ] || { echo "modem-held wrapper requires the three-variant kernel manifest" >&2; exit 2; }
fi
CFLAGS="-O2 -ffreestanding -nostdlib -fno-pic -mgeneral-regs-only -mstrict-align -fno-stack-protector -Wall -Wextra"
[ "$mode" != veux ] || CFLAGS="$CFLAGS -DDEVICE_VEUX"
mkdir -p out
for f in start.S shim.c console.c mmu.c fdt.c loader.c ufs.c; do
	$CC $CFLAGS -c $f -o out/${f%.*}.o
done
# The image runs wherever ABL puts it with no relocation pass: only the
# header's image_size (start.o, linked at 0) may be an absolute address.
abs=$(aarch64-linux-gnu-readelf -r out/shim.o out/console.o out/mmu.o out/fdt.o out/loader.o out/ufs.o | grep -c ABS64 || true)
[ "$abs" = 0 ] || { echo "error: $abs absolute relocations in C objects" >&2; exit 1; }
$CC $CFLAGS -static -T shim.ld -Wl,--build-id=none -Wl,--no-warn-rwx-segments -Wl,-N \
	out/start.o out/shim.o out/console.o out/mmu.o out/fdt.o out/loader.o out/ufs.o -o out/shim.elf
$OBJCOPY -O binary out/shim.elf out/Image
# ABL copies the file; pad to image_size so .bss/stacks exist as zeroed bytes.
size=$(aarch64-linux-gnu-nm out/shim.elf | awk '$3=="_end"{print strtonum("0x"$1)}')
truncate -s "$size" out/Image
# Ramdisk: an xnu payload (tools/mkpayload.py) if given as $1, else an empty
# newc cpio (ABL dislikes a zero-size ramdisk on some builds) -> diagnostics.
if [ -n "$payload" ]; then
	cp "$payload" out/ramdisk.bin
else
	(cd out && rm -rf rd && mkdir rd && cd rd && find . | cpio -o -H newc --quiet | gzip -9 > ../ramdisk.bin)
fi
mkbootimg --header_version 2 --kernel out/Image --ramdisk out/ramdisk.bin \
	--dtb "$dtb" --base 0 --kernel_offset 0x8000 --ramdisk_offset 0x1000000 \
	--tags_offset 0x100 --dtb_offset 0x1f00000 --pagesize 4096 \
	--os_version 17.0.0 --os_patch_level 2035-06 \
	--cmdline "console=null" -o "$output"
# Host render of the console layout.
gcc -O1 -Wall -o out/host_test console.c host_test.c && ./out/host_test
ls -l out/Image "$output"
if [ -n "$ci_kernel" ]; then
	[ -n "$payload" ] && [ -n "$ci_run_id" ] && [ -n "$build_id" ] && [ -n "$boot_args" ] && [ -n "$patch_status" ] || {
		echo "wrapper verification requires payload, CI kernel, run/build IDs, boot args, and patch status" >&2
		exit 2
	}
	verify_extra=()
	if [ -n "$variants_manifest" ]; then verify_extra+=(--variants-manifest "$variants_manifest"); fi
	if [ -n "$variant" ]; then verify_extra+=(--variant "$variant"); fi
	python3 ../tools/verify-veux-wrapper.py \
		--image "$output" --payload "$payload" --ci-kernel "$ci_kernel" \
		--dtb "$dtb" --run-id "$ci_run_id" --build-id "$build_id" \
		--boot-args "$boot_args" --patch-status "$patch_status" \
		"${verify_extra[@]}"
fi
