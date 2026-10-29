#!/usr/bin/env python3
"""Check that the generated VEUX ADT exposes XNU's GIC lookup node."""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mkadt


def child_named(node, name):
    return [child for child in node.children
            if dict((key, value) for key, _flags, value in child.props).get("name") == name.encode() + b"\0"]


adt_root = mkadt.build(seed=bytes(64), highmem=True, veux=True)
arm_io = child_named(adt_root, "arm-io")
assert len(arm_io) == 1, "VEUX ADT must contain one /arm-io node"
gic = child_named(arm_io[0], "gic")
assert len(gic) == 1, "VEUX ADT must expose /arm-io/interrupt-controller for XNU lookup"
props = dict((key, value) for key, _flags, value in gic[0].props)
assert props.get("compatible") == b"arm,gic\0"
assert props.get("interrupt-controller") == b"master\0"
assert int.from_bytes(props["#interrupt-cells"], "little") == 3
assert struct.unpack("<QQQQ", props["reg"]) == (0x0e200000, 0x10000, 0x0e240000, 0x100000), \
    "VEUX GIC reg must map to GICD 0x0f200000 and GICR 0x0f240000 through /arm-io/ranges"
assert struct.unpack("<III", props["interrupts"]) == (1, 8, 4)
ranges = dict((key, value) for key, _flags, value in arm_io[0].props)["ranges"]
assert struct.unpack("<QQQ", ranges) == (0, 0x01000000, 0xff000000), \
    "XNU requires nonzero soc_phys=0x01000000; zero short-circuits interrupt mapping"
print("VEUX ADT /arm-io/gic master: GICD 0x0f200000, GICR 0x0f240000, soc_phys 0x01000000")
