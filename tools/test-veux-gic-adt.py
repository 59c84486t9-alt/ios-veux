#!/usr/bin/env python3
"""Keep the generated VEUX GIC node identical to the known-good GUI ADT."""
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
arm_props = dict((key, value) for key, _flags, value in arm_io[0].props)
assert struct.unpack("<QQQ", arm_props["ranges"]) == (0, 0x01000000, 0xff000000), \
    "match the working GUI ADT; XNU reports soc_phys=0x01000000 here"
gic_nodes = child_named(arm_io[0], "gic")
assert len(gic_nodes) == 1, "XNU pe_init_fiq() requires /arm-io/gic"
gic = gic_nodes[0]
props = dict((key, value) for key, _flags, value in gic.props)
assert props.get("compatible") == b"arm,gic-v3\0"
assert props.get("interrupt-controller") == b"", "match the known-good boolean property"
assert struct.unpack("<QQQQ", props["reg"]) == (0x0e200000, 0x10000, 0x0e240000, 0x100000), \
    "SOC_BASE 0x01000000 resolves these to VEUX GICD/R at 0x0f200000/0x0f240000"
assert set(props) == {"name", "AAPL,phandle", "compatible", "interrupt-controller",
                       "virtual-timer-intid", "reg"}, \
    "do not add properties that differ from the known-good GUI GIC node"
assert int.from_bytes(props["virtual-timer-intid"], "little") == 19
print("VEUX GIC node matches working GUI ADT: /arm-io/gic, soc_phys=0x01000000, GICD/R=0x0f200000/0x0f240000")
