"""Read purchasing choices from Stackup's BOM and edit reviewed placement fields."""

from __future__ import annotations

import csv
import io
import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PARTS_FILE = ROOT / "PCB" / "stackup" / "board.kdl"
PCB_FILE = ROOT / "PCB" / "snips_controller.kicad_pcb"


@dataclass(frozen=True)
class Part:
    ref: str
    value: str
    footprint: str
    manufacturer: str
    mpn: str
    lcsc: str
    hand: bool
    dnp: bool


PLACEMENT = re.compile(r'^    place \S+ "([A-Za-z0-9_]+)" .*$', re.M)


def _string(block: str, pattern: str) -> str:
    match = re.search(pattern + r'("(?:[^"\\]|\\.)*")', block, re.M)
    return json.loads(match.group(1)) if match else ""


def read_bom_rows() -> list[dict[str, str]]:
    """Use the Cargo-locked Stackup engine, including library ordering defaults."""
    binary = os.environ.get("STACKUP_BIN")
    command = ([binary] if binary else [
        "cargo", "+1.96.0", "run", "--quiet", "--locked", "--manifest-path",
        str(ROOT / "ci" / "stackup" / "Cargo.toml"), "--",
    ]) + ["bom", str(PARTS_FILE), "--locked"]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError(f"stackup bom failed:\n{result.stderr or result.stdout}")
    rows = list(csv.DictReader(io.StringIO(result.stdout)))
    if not rows:
        raise ValueError(f"no components in {PARTS_FILE}")
    return rows


def read_parts() -> dict[str, Part]:
    """Expand grouped BOM rows by designator for scripts that edit placements."""
    parts = {}
    for row in read_bom_rows():
        refs = [ref.strip() for ref in row["Refs"].split(",")]
        if len(refs) != int(row["Quantity"]):
            raise ValueError(f"bad Stackup BOM quantity for {row['Refs']}")
        for ref in refs:
            if ref in parts:
                raise ValueError(f"duplicate Stackup BOM reference {ref}")
            parts[ref] = Part(
                ref=ref,
                value=row["Value"],
                footprint=row["Footprint"],
                manufacturer=row["MF"],
                mpn=row["MPN"],
                lcsc=row["LCSC"],
                hand=row["Hand"] == "Yes",
                dnp=row["DNP"] == "Yes",
            )
    if not parts:
        raise ValueError(f"no components in {PARTS_FILE}")
    return parts


def quoted(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def replace_placement_property(text: str, ref: str, key: str, value: str) -> str:
    for match in PLACEMENT.finditer(text):
        if match.group(1) != ref:
            continue
        line = match.group()
        pattern = re.compile(r"\b" + re.escape(key) + r'="(?:[^"\\]|\\.)*"')
        new, count = pattern.subn(key + "=" + quoted(value), line, count=1)
        if count == 0:
            cut = line.find(" { ")
            if cut < 0:
                cut = len(line)
            new = line[:cut] + " " + key + "=" + quoted(value) + line[cut:]
        return text[:match.start()] + new + text[match.end():]
    raise KeyError(ref)


def balanced(text: str, start: int) -> int:
    """Return the byte after the closing parenthesis, ignoring quoted strings."""
    depth = 0
    quoted = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index + 1
    raise ValueError("unbalanced PCB expression")


def pcb_footprints(text: str):
    for match in re.finditer(r'\n\t\(footprint "', text):
        start = match.start() + 2
        end = balanced(text, start)
        block = text[start:end]
        ref = _string(block, r'\(property "Reference" ')
        yield ref, start, end, block


def pcb_property(block: str, name: str) -> str:
    return _string(block, r'\(property "' + re.escape(name) + r'" ')
