#!/usr/bin/env python3
"""Build an unflashed, XNU-free marker/reset probe (optional live-FDT RGB pattern) using a known boot-v2 header.

Requires clang and AArch64 ELF binutils. No device commands are issued.
The template must be an existing VEUX shim image, not a stock boot-v3 image.
"""
import argparse
import gzip
import hashlib
from pathlib import Path
import shutil
import struct
import subprocess


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--template', type=Path, required=True)
    ap.add_argument('--dtb', type=Path, required=True)
    ap.add_argument('--out-dir', type=Path, required=True)
    ap.add_argument('--clang', default='clang')
    ap.add_argument('--cross-prefix', default='aarch64-elf-')
    ap.add_argument('--screen', action='store_true', help='enable RGB drawing; default is marker/reset only')
    args = ap.parse_args()
    root = Path(__file__).resolve().parent.parent
    header = args.template.read_bytes()
    if header[:8] != b'ANDROID!' or len(header) < 1660:
        ap.error('template is not an Android boot image')
    fields = struct.unpack_from('<10I', header, 8)
    ks, _, rs, _, ss, _, _, page, version, _ = fields
    if version != 2 or page != 4096 or ss or struct.unpack_from('<I', header, 1632)[0]:
        ap.error('template must be boot v2 / 4096-byte pages with no second or recovery DTBO')
    align = lambda n: (n + page - 1) // page * page
    dtb_size = struct.unpack_from('<I', header, 1648)[0]
    dtb_offset = page + align(ks) + align(rs)
    dtb = args.dtb.read_bytes()
    if dtb[:4] != b'\xd0\x0d\xfe\xed' or header[dtb_offset:dtb_offset + dtb_size] != dtb:
        ap.error('DTB must match the selected DTB in the known VEUX template')
    for tool in (args.clang, args.cross_prefix + 'ld', args.cross_prefix + 'objcopy', args.cross_prefix + 'readelf'):
        if not shutil.which(tool):
            ap.error('missing tool: ' + tool)
    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    for source, obj in [('veux-fb-probe.S', 'entry.o'), ('veux-fb-probe.c', 'probe.o')]:
        subprocess.run([args.clang, '--target=aarch64-none-elf', '-O2', '-ffreestanding',
                        '-fno-builtin', '-fno-stack-protector', '-fno-pic', '-mgeneral-regs-only',
                        '-mstrict-align', '-ffunction-sections', '-fdata-sections',
                        f'-DPROBE_SCREEN={int(args.screen)}', '-Wall', '-Wextra', '-Werror', '-c',
                        str(root / 'shim' / source), '-o', str(out / obj)], check=True)
    relocs = subprocess.check_output([args.cross_prefix + 'readelf', '-r', str(out / 'probe.o')], text=True)
    if 'R_AARCH64_ABS64' in relocs:
        raise SystemExit('C objects contain absolute pointers; ABL relocation is unsupported')
    subprocess.run([args.cross_prefix + 'ld', '--gc-sections', '-T', str(root / 'shim/veux-fb-probe.ld'),
                    str(out / 'entry.o'), str(out / 'probe.o'), '-o', str(out / 'probe.elf')], check=True)
    subprocess.run([args.cross_prefix + 'objcopy', '-O', 'binary',
                    str(out / 'probe.elf'), str(out / 'Image')], check=True)
    kernel = (out / 'Image').read_bytes()
    image_size = struct.unpack_from('<Q', kernel, 16)[0]
    assert len(kernel) <= image_size <= 0x100000 and kernel[56:60] == b'ARM\x64'
    kernel += bytes(image_size - len(kernel))
    (out / 'Image').write_bytes(kernel)
    # Empty newc archive, with a nonempty compressed ramdisk for ABL.
    fields = [0] * 13
    fields[4], fields[11] = 1, 11  # nlink, namesize incl. NUL
    cpio = b'070701' + ''.join(f'{n:08x}' for n in fields).encode() + b'TRAILER!!!\0'
    cpio += bytes((-len(cpio)) % 4)
    ramdisk = gzip.compress(cpio, mtime=0)
    (out / 'ramdisk.gz').write_bytes(ramdisk)
    packed = bytearray(header[:page])
    struct.pack_into('<I', packed, 8, len(kernel))
    struct.pack_into('<I', packed, 16, len(ramdisk))
    digest = hashlib.sha1()
    for part in (kernel, ramdisk, b'', dtb):
        digest.update(part)
        digest.update(struct.pack('<I', len(part)))
    packed[576:608] = digest.digest() + bytes(12)
    for part in (kernel, ramdisk, dtb):
        packed.extend(part)
        packed.extend(bytes(align(len(part)) - len(part)))
    image = out / ('shim-boot-veux-rgb-reset.img' if args.screen else 'shim-boot-veux-marker-reset.img')
    image.write_bytes(packed)
    print(f'{image}\n{len(packed)} bytes; SHA-256 {hashlib.sha256(packed).hexdigest()}')
    print('Mode:', 'screen + marker' if args.screen else 'marker only (no framebuffer/FDT access)')
    print('Requests standard PSCI reset after a 10-second counter wait; active slot stays unchanged.')


if __name__ == '__main__':
    main()
