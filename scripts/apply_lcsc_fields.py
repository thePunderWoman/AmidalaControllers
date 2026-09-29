#!/usr/bin/env python3
"""Apply reviewed JLC matches to Stackup orders and the PCB's LCSC fields.

Usage: python3 scripts/apply_lcsc_fields.py /tmp/jlc_match.csv
Close the PCB in KiCad before running this script, or reload it afterwards.
"""

import csv
import re
import sys
import uuid

from stackup_parts import (
    PARTS_FILE, PCB_FILE, balanced, pcb_footprints, quoted, read_parts,
    replace_placement_property,
)


def load_targets(csv_path):
    targets = {}
    with open(csv_path, newline="") as source:
        for row in csv.DictReader(source):
            lcsc = row.get("LCSC", "").strip()
            if not lcsc:
                continue
            for ref in row["Refs"].split(","):
                targets[ref.strip()] = lcsc
    return targets


def set_pcb_lcsc(block, code):
    field = re.search(r'\(property "LCSC" "(?:[^"\\]|\\.)*"', block)
    if field:
        replacement = '(property "LCSC" ' + quoted(code)
        return block[:field.start()] + replacement + block[field.end():]
    source = re.search(r'\(property "Manufacturer_Part_Number" ', block)
    if not source:
        raise ValueError("PCB footprint has no Manufacturer_Part_Number property")
    end = balanced(block, source.start())
    clone = block[source.start():end]
    clone = clone.replace('"Manufacturer_Part_Number"', '"LCSC"', 1)
    clone = re.sub(r'^(\(property "LCSC" )"(?:[^"\\]|\\.)*"',
                   lambda match: match.group(1) + quoted(code), clone, count=1)
    clone = re.sub(r'\(uuid "[^"]+"\)',
                   lambda _: '(uuid "' + str(uuid.uuid4()) + '")', clone, count=1)
    return block[:end] + "\n\t\t" + clone + block[end:]


def main():
    if len(sys.argv) != 2:
        sys.exit(f"Usage: {sys.argv[0]} <jlc_match.csv>")
    targets = load_targets(sys.argv[1])
    parts = read_parts()
    kdl = PARTS_FILE.read_text()
    pcb = PCB_FILE.read_text()
    applied = set()

    for ref, start, end, block in reversed(list(pcb_footprints(pcb))):
        if ref not in targets:
            continue
        part = parts.get(ref)
        if part is None or not part.mpn:
            continue
        try:
            changed = set_pcb_lcsc(block, targets[ref])
        except ValueError:
            continue
        pcb = pcb[:start] + changed + pcb[end:]
        kdl = replace_placement_property(kdl, ref, "lcsc", targets[ref])
        applied.add(ref)

    if applied:
        PARTS_FILE.write_text(kdl)
        PCB_FILE.write_text(pcb)
    print(f"{len(applied)}/{len(targets)} references updated in Stackup and PCB")
    for ref in sorted(set(targets) - applied):
        print(f"not updated: {ref}")
    return 1 if set(targets) - applied else 0


if __name__ == "__main__":
    sys.exit(main())
