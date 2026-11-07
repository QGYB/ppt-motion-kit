# SPDX-License-Identifier: AGPL-3.0-only
"""Emit native PowerPoint timing for 手书逐字飞聚. This tool does not open a deck."""
import argparse
import json
from pathlib import Path
import sys
from xml.etree import ElementTree as ET

NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
P = "{" + NS + "}"
PRESETS = Path(__file__).resolve().parents[1] / "references" / "text-gather-presets.json"
ET.register_namespace("p", NS)


def make_timing(shape_id, trigger="click", first_id=1):
    """Build a fresh timing tree for a slide with no timeline, targeting one text shape."""
    presets = json.loads(PRESETS.read_text(encoding="utf-8"))
    if trigger not in presets:
        raise ValueError("trigger must be click or slide-start")
    if not all(type(value) is int and value > 0 for value in (shape_id, first_id)):
        raise ValueError("shape_id and first_id must be positive integers")
    timing = ET.fromstring(presets[trigger])
    nodes = list(timing.iter(P + "cTn"))
    if shape_id > 4294967295 or first_id + len(nodes) - 1 > 4294967295:
        raise ValueError("shape or timing ID outside unsigned 32-bit range")
    ids = {node.get("id"): str(first_id + i) for i, node in enumerate(nodes)}
    for node in nodes:
        node.set("id", ids[node.get("id")])
    for reference in timing.iter(P + "tn"):
        reference.set("val", ids[reference.get("val")])
    for tag in ("spTgt", "bldP"):
        for target in timing.iter(P + tag):
            target.set("spid", str(shape_id))
    return timing


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shape-id", required=True, type=int, help="Target text shape cNvPr ID on this slide")
    parser.add_argument("--trigger", choices=("click", "slide-start"), default="click")
    parser.add_argument("--first-id", type=int, default=1, help="First timing-node ID")
    args = parser.parse_args()
    try:
        timing = make_timing(args.shape_id, args.trigger, args.first_id)
    except ValueError as error:
        parser.error(str(error))
    sys.stdout.buffer.write(ET.tostring(timing, encoding="utf-8") + b"\n")


if __name__ == "__main__":
    main()
