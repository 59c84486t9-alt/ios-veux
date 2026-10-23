#!/usr/bin/env python3
"""Ensure only the VEUX ADT publishes its firmware-advertised PSCI conduit."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mkadt


def children_named(root, wanted):
    return [child for child in root.children
            if dict((key, value) for key, _flags, value in child.props).get("name") == wanted.encode() + b"\0"]


veux = mkadt.build(seed=bytes(64), highmem=True, veux=True)
psci = children_named(veux, "psci")
assert len(psci) == 1, "VEUX ADT must contain one /psci node"
props = dict((key, value) for key, _flags, value in psci[0].props)
assert props.get("compatible") == b"arm,psci-1.0\0"
assert props.get("method") == b"smc\0", "live VEUX FDT advertises the SMC conduit"

sweet = mkadt.build(seed=bytes(64), highmem=True, veux=False)
assert not children_named(sweet, "psci"), "keep the new PSCI node VEUX-only"
print("VEUX /psci method=smc; SWEET ADT unchanged")
