#!/usr/bin/env python3
"""Build an unflashed, XNU-free white-screen probe using a known boot-v2 header.

Requires clang and AArch64 ELF binutils. No device commands are issued.
The template must be an existing VEUX shim image, not a stock boot-v3 image.
"""
import argparse
import gzip
import hashlib
from pathlib import Path
import re
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
    profile = (root / 'shim/console.h').read_text().split('#ifdef DEVICE_VEUX', 1)[1].split('#else', 1)[0]
    values = {}
    for name in ('BASE', 'W', 'H', 'STRIDE', 'SIZE'):
        values[name] = int(re.search(r'#define\s+FB_' + name + r'\s+(0x[0-9a-fA-F]+|[0-9]+)', profile)[1], 0)
    if not (0 < values['W'] * 4 <= values['STRIDE'] and values['H'] > 0
            and values['STRIDE'] * values['H'] <= values['SIZE']
            and values['BASE'] % 4 == values['STRIDE'] % 4 == 0):
        ap.error('framebuffer geometry exceeds the reservation or is unaligned')
    for tool in (args.clang, args.cross_prefix + 'ld', args.cross_prefix + 'objcopy'):
        if not shutil.which(tool):
            ap.error('missing tool: ' + tool)
    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    definitions = [f'-DPROBE_FB_{name}={values[key]}' for name, key in
                   [('BASE', 'BASE'), ('WIDTH', 'W'), ('HEIGHT', 'H'), ('STRIDE', 'STRIDE')]]
    subprocess.run([args.clang, '--target=aarch64-none-elf', *definitions, '-c',
                    str(root / 'shim/veux-fb-probe.S'), '-o', str(out / 'probe.o')], check=True)
    subprocess.run([args.cross_prefix + 'ld', '-Ttext=0', '-e', '_head',
                    str(out / 'probe.o'), '-o', str(out / 'probe.elf')], check=True)
    subprocess.run([args.cross_prefix + 'objcopy', '-O', 'binary',
                    str(out / 'probe.elf'), str(out / 'Image')], check=True)
    kernel = (out / 'Image').read_bytes()
    assert len(kernel) == 4096 and kernel[56:60] == b'ARM\x64'
    assert struct.unpack_from('<Q', kernel, 16)[0] == len(kernel)
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
    image = out / 'shim-boot-veux-fb-only.img'
    image.write_bytes(packed)
    print(f'{image}\n{len(packed)} bytes; SHA-256 {hashlib.sha256(packed).hexdigest()}')
    print('Expected: solid white screen, then halt. Visibility is not yet verified on hardware.')


if __name__ == '__main__':
    main()
