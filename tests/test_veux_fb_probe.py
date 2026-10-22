#!/usr/bin/env python3
"""Host tests for the bare-metal FDT parser and bounded RGB renderer."""
import ctypes as C
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
u32 = lambda *v: struct.pack('>' + 'I' * len(v), *v)


def fdt(nodes):
    strings = bytearray()
    offsets = {}
    def emit(node):
        name, props, children = node
        data = u32(1) + name.encode() + b'\0'
        data += bytes(-len(data) % 4)
        for key, value in props:
            if key not in offsets:
                offsets[key] = len(strings)
                strings.extend(key.encode() + b'\0')
            data += u32(3, len(value), offsets[key]) + value + bytes(-len(value) % 4)
        for child in children:
            data += emit(child)
        return data + u32(2)
    tree = emit(('', [('#address-cells', u32(2)), ('#size-cells', u32(2))], nodes)) + u32(9)
    return u32(0xd00dfeed, 56 + len(tree) + len(strings), 56, 56 + len(tree),
               40, 17, 16, 0, len(strings), len(tree)) + bytes(16) + tree + strings


def display(**changes):
    props = {'compatible': b'simple-framebuffer\0', 'reg': u32(0, 0x85200000, 0, 0xc00000),
             'width': u32(96), 'height': u32(64), 'stride': u32(400), 'format': b'a8r8g8b8\0'}
    props.update(changes)
    return ('framebuffer@85200000', [(k, v) for k, v in props.items() if v is not None], [])


class Display(C.Structure):
    _fields_ = [('base', C.c_uint64), ('size', C.c_uint64), ('width', C.c_uint32),
                ('height', C.c_uint32), ('stride', C.c_uint32), ('bgr', C.c_uint32)]


class Info(C.Structure):
    _fields_ = [('fb', Display), ('count', C.c_uint32), ('valid', C.c_uint32), ('ramoops', C.c_uint32), ('splash', Display),
                ('splash_count', C.c_uint32), ('splash_valid', C.c_uint32)]


class ProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        lib = Path(cls.tmp.name) / 'probe.so'
        subprocess.run(['clang', '-shared', '-fPIC', '-DPROBE_HOST', '-Wall', '-Wextra', '-Werror',
                        str(ROOT / 'shim/veux-fb-probe.c'), '-o', str(lib)], check=True)
        cls.lib = C.CDLL(str(lib))
        cls.lib.probe_parse.argtypes = [C.c_void_p, C.c_size_t, C.POINTER(Info)]
        cls.lib.probe_select.argtypes = [C.POINTER(Info)]
        cls.lib.probe_pattern.argtypes = [C.POINTER(C.c_uint32), C.POINTER(Display)]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def parse(self, data):
        buf, info = C.create_string_buffer(data), Info()
        ok = self.lib.probe_parse(buf, len(data), C.byref(info))
        return ok, info

    def test_complete_display_and_pmsg_reservation(self):
        pmsg = ('ramoops', [('compatible', b'ramoops\0'), ('reg', u32(0, 0xd0000000, 0, 0x200000))], [])
        ok, info = self.parse(fdt([display(), pmsg]))
        self.assertEqual((ok, info.valid, info.ramoops), (1, 1, 1))
        self.assertEqual((info.fb.base, info.fb.stride), (0x85200000, 400))

    def test_no_invented_display_from_splash_reservation(self):
        ok, info = self.parse(fdt([('splash', [('reg', u32(0, 0x85200000, 0, 0xc00000))], [])]))
        self.assertEqual((ok, info.valid, info.count), (1, 0, 0))

    def test_reject_incomplete_unsafe_or_unsupported(self):
        for changes in [dict(stride=None), dict(format=b'r5g6b5\0'), dict(width=u32(0)),
                        dict(stride=u32(1)), dict(height=u32(4097)), dict(status=b'disabled\0'),
                        dict(reg=u32(0, 0x9c000000, 0, 0xc00000)),
                        dict(reg=u32(0, 0x85200000, 0, 100)), dict(format=b'a8r8g8b8')]:
            with self.subTest(changes=changes):
                self.assertEqual(self.parse(fdt([display(**changes)]))[1].valid, 0)
        self.assertEqual(self.parse(fdt([display(), display()]))[1].valid, 0)

    def test_chosen_and_untranslated_bus(self):
        chosen = ('chosen', [('#address-cells', u32(2)), ('#size-cells', u32(2))], [display()])
        self.assertEqual(self.parse(fdt([chosen]))[1].valid, 1)
        bus = ('soc', [('#address-cells', u32(2)), ('#size-cells', u32(2))], [display()])
        self.assertEqual(self.parse(fdt([bus]))[1].valid, 0)

    def test_truncated_and_corrupt_fdt(self):
        data = fdt([display()])
        for length in range(len(data)):
            self.assertEqual(self.parse(data[:length])[0], 0)
        for offset, value in [(0, 0), (8, 0xfffffffc), (12, 0xffffffff), (32, 0xffffffff), (36, 0xffffffff)]:
            damaged = bytearray(data)
            struct.pack_into('>I', damaged, offset, value)
            self.assertEqual(self.parse(bytes(damaged))[0], 0)

    def test_ordered_splash_fallback(self):
        def reserved(base=0x85200000, size=0xc00000, duplicate=False):
            child = ('splash_region@0x85200000', [('reg', u32(0, base, 0, size))], [])
            return ('reserved-memory', [('#address-cells', u32(2)), ('#size-cells', u32(2)),
                                        ('ranges', b'')], [child] * (2 if duplicate else 1))
        info = self.parse(fdt([reserved()]))[1]
        self.assertEqual(self.lib.probe_select(C.byref(info)), 2)
        self.assertEqual((info.fb.base, info.fb.width, info.fb.height, info.fb.stride),
                         (0x85200000, 1080, 2400, 4320))
        info = self.parse(fdt([display(), reserved()]))[1]
        self.assertEqual(self.lib.probe_select(C.byref(info)), 1)
        self.assertEqual(info.fb.stride, 400)
        for nodes in [[reserved(0x9c000000)], [reserved(size=100)],
                      [reserved(duplicate=True)], [display(stride=None), reserved()]]:
            info = self.parse(fdt(nodes))[1]
            self.assertEqual(self.lib.probe_select(C.byref(info)), 0)

    def test_rgb_bgr_corner_and_stride_padding(self):
        for fmt, red, blue in [(b'a8r8g8b8\0', 0xffff0000, 0xff0000ff),
                               (b'a8b8g8r8\0', 0xff0000ff, 0xffff0000)]:
            info = self.parse(fdt([display(format=fmt)]))[1]
            sentinel = 0x12345678
            pixels = (C.c_uint32 * (100 * 64 + 2))(*([sentinel] * (100 * 64 + 2)))
            start = C.cast(C.byref(pixels, 4), C.POINTER(C.c_uint32))
            self.lib.probe_pattern(start, C.byref(info.fb))
            self.assertEqual((pixels[0], pixels[-1]), (sentinel, sentinel))
            self.assertEqual((start[40 * 100 + 5], start[40 * 100 + 40], start[40 * 100 + 80]),
                             (red, 0xff00ff00, blue))
            self.assertEqual(start[100 + 1], 0xffffffff)
            self.assertEqual(start[0], 0xff000000)
            for y in range(64):
                self.assertTrue(all(start[y * 100 + x] == sentinel for x in range(96, 100)))


if __name__ == '__main__':
    unittest.main()
