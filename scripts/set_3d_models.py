#!/usr/bin/env python3
"""Point footprints at 3D models that actually resolve, so STEP export is complete.

KiCad 10's stock footprints for the HRO TYPE-C-31-M-12 and Alps SKRTLAE010
reference model files that KiCad 10 does not ship, and several custom/vendor
footprints had no model or a model path that only existed on an old install
(${KICAD8_3RD_PARTY}). This script rewrites the (model ...) entries of those
footprints, both in the board file and in the project's own footprint
libraries, to the table below. Offsets/rotations were derived by matching each
model's pins/pegs/legs to the footprint's pads; see
PCB/libraries/3dmodels/README.md for sources.

KiCad model axes: +X right, +Y up the board (PCB -Y), +Z out of the board.

Usage:
  python3 scripts/set_3d_models.py            # rewrite board + libraries
  python3 scripts/set_3d_models.py --check    # exit 1 if any model is missing or unresolvable
  python3 scripts/set_3d_models.py --board path/to/other.kicad_pcb

Close KiCad before rewriting: an open PCB editor will save its stale copy over
the edit.
"""
import argparse
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PCB_DIR = REPO / "PCB"
BOARD = PCB_DIR / "snips_controller.kicad_pcb"
KICAD_3D = os.environ.get(
    "KICAD10_3DMODEL_DIR",
    "/Applications/KiCad/KiCad.app/Contents/SharedSupport/3dmodels")

LOCAL = "${KIPRJMOD}/libraries/3dmodels"
STOCK = "${KICAD10_3DMODEL_DIR}"
SOCKET = f"{STOCK}/Connector_PinSocket_2.00mm.3dshapes/PinSocket_1x10_P2.00mm_Vertical.step"


def model(path, offset=(0, 0, 0), rotate=(0, 0, 0)):
    return {"path": path, "offset": offset, "rotate": rotate}


# footprint lib_id -> list of models
MODELS = {
    "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12": [
        model(f"{LOCAL}/USB_C_Receptacle_HRO_TYPE-C-31-M-12.step", (0, -1.05, 0), (0, 0, 180))],
    "Button_Switch_SMD:SW_Push_1P1T-MP_NO_Horizontal_Alps_SKRTLAE010": [
        model(f"{LOCAL}/SW_Alps_SKRTLAE010.step")],
    "Espressif:ESP32-S3-WROOM-1": [
        # Stock KiCad model is centred on the module; this footprint's origin is 3mm
        # further toward the antenna end than the stock footprint's.
        model(f"{STOCK}/RF_Module.3dshapes/ESP32-S3-WROOM-1.step", (0, 3, 0))],
    "SnipsControllers_Custom:SK6812MINI-E-012": [
        model(f"{STOCK}/LED_SMD.3dshapes/LED_SK6812MINI-E_3.2x2.8mm_P1.5mm_ReverseMount.step")],
    "SnipsControllers_Custom:QMA6100P": [
        model(f"{LOCAL}/QMA6100P_LGA-12_2x2mm.step")],
    "BQ25185DLHR:IC_BQ25185DLHR": [
        # SnapEDA model is Y-up; stand it on the board.
        model("${KIPRJMOD}/libraries/BQ25185DLHR/BQ25185DLHR.step", rotate=(-90, 0, 0))],
    "Xbee3:XB324Z8UTJ": [
        model(SOCKET),
        model(SOCKET, (22, 0, 0)),
        model(f"{LOCAL}/XBee3_TH_UFL_placeholder.step")],
    "SnipsControllers_Custom:GuliKit_HallStick": [
        # ALPS RKJXV1224005 (same footprint family); model origin is 11.4mm above
        # the standoffs that sit on the board.
        model(f"{LOCAL}/Thumbstick_ALPS_RKJXV1224005.step", (0, 0, 11.4))],
}

# project footprint library files -> lib_id whose models they should carry
LIB_FILES = {
    PCB_DIR / "libraries/Espressif.pretty/ESP32-S3-WROOM-1.kicad_mod": "Espressif:ESP32-S3-WROOM-1",
    PCB_DIR / "libraries/SnipsControllers_Custom.pretty/SK6812MINI-E-012.kicad_mod": "SnipsControllers_Custom:SK6812MINI-E-012",
    PCB_DIR / "libraries/SnipsControllers_Custom.pretty/QMA6100P.kicad_mod": "SnipsControllers_Custom:QMA6100P",
    PCB_DIR / "libraries/SnipsControllers_Custom.pretty/GuliKit_HallStick.kicad_mod": "SnipsControllers_Custom:GuliKit_HallStick",
    PCB_DIR / "libraries/BQ25185DLHR.pretty/IC_BQ25185DLHR.kicad_mod": "BQ25185DLHR:IC_BQ25185DLHR",
    PCB_DIR / "libraries/Xbee3.pretty/XB324Z8UTJ.kicad_mod": "Xbee3:XB324Z8UTJ",
}

# Footprints that intentionally have no model (board graphics, holes, fiducials).
NO_MODEL_OK = ("MountingHole:", "Fiducial:", "LOGO", "R2Builders:")


def fmt(n):
    return f"{n:g}"


def render(models, indent):
    t = "\t" * indent
    out = []
    for m in models:
        out.append(
            f'{t}(model "{m["path"]}"\n'
            f'{t}\t(offset\n{t}\t\t(xyz {" ".join(fmt(v) for v in m["offset"])})\n{t}\t)\n'
            f'{t}\t(scale\n{t}\t\t(xyz 1 1 1)\n{t}\t)\n'
            f'{t}\t(rotate\n{t}\t\t(xyz {" ".join(fmt(v) for v in m["rotate"])})\n{t}\t)\n'
            f'{t})\n')
    return "".join(out)


def matching_paren(s, i):
    """Index of the ')' closing the '(' at s[i]; skips quoted strings."""
    depth, j, in_str = 0, i, False
    while j < len(s):
        c = s[j]
        if in_str:
            if c == "\\":
                j += 1
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return j
        j += 1
    raise ValueError("unbalanced parentheses")


def strip_models(block):
    """Remove every (model ...) sub-expression, with its leading whitespace line."""
    while True:
        m = re.search(r"\n[ \t]*\(model[\s\"]", block)
        if not m:
            return block
        start = block.index("(model", m.start())
        end = matching_paren(block, start)
        block = block[:m.start()] + block[end + 1:]


def replace_models(block, models, indent):
    block = strip_models(block)
    close = block.rstrip().rfind(")")
    return block[:close].rstrip("\t ") + render(models, indent) + "\t" * (indent - 1) + ")"


def footprints(s):
    """Yield (start, end, lib_id) for each top-level footprint in a board file."""
    for m in re.finditer(r'\n\t\(footprint "([^"]+)"', s):
        start = m.start() + 1
        yield start, matching_paren(s, start), m.group(1)


def read(path):
    # newline="" keeps CRLF files (e.g. the vendor XBee footprint) byte-identical outside the edit.
    with open(path, newline="") as f:
        return f.read()


def write(path, s):
    with open(path, "w", newline="") as f:
        f.write(s)


def rewrite_board(path):
    s = read(path)
    out, pos, counts = [], 0, {}
    for start, end, lib_id in footprints(s):
        if lib_id in MODELS:
            out.append(s[pos:start])
            out.append(replace_models(s[start:end + 1], MODELS[lib_id], 2))
            pos = end + 1
            counts[lib_id] = counts.get(lib_id, 0) + 1
    out.append(s[pos:])
    write(path, "".join(out))
    for lib_id, n in sorted(counts.items()):
        print(f"  {path.name}: {n} x {lib_id}")
    missing = set(MODELS) - set(counts)
    if missing:
        print(f"  note: not on board: {', '.join(sorted(missing))}")


def rewrite_library(path, lib_id):
    s = read(path)
    crlf = "\r\n" in s
    if crlf:
        s = s.replace("\r\n", "\n")
    start = s.index("(")
    end = matching_paren(s, start)
    s = s[:start] + replace_models(s[start:end + 1], MODELS[lib_id], 1) + s[end + 1:]
    if crlf:
        s = s.replace("\n", "\r\n")
    write(path, s)
    print(f"  {path.relative_to(REPO)}")


def resolve(p, board_dir):
    return Path(p.replace("${KIPRJMOD}", str(board_dir)).replace("${KICAD10_3DMODEL_DIR}", KICAD_3D))


def check(path):
    s = path.read_text()
    problems = []
    for start, end, lib_id in footprints(s):
        block = s[start:end + 1]
        ref = re.search(r'\(property "Reference" "([^"]+)"', block)
        ref = ref.group(1) if ref else "?"
        paths = re.findall(r'\(model "([^"]+)"', block)
        if not paths:
            if not any(k in lib_id for k in NO_MODEL_OK):
                problems.append(f"{ref} ({lib_id}): no 3D model")
            continue
        for p in paths:
            if "${" in resolve(p, path.parent).as_posix() or not resolve(p, path.parent).is_file():
                problems.append(f"{ref} ({lib_id}): model not found: {p}")
    for p in problems:
        print(p)
    print(f"{len(problems)} problem(s)")
    return not problems


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="only verify every footprint has a resolvable model")
    ap.add_argument("--board", type=Path, default=BOARD)
    ap.add_argument("--no-libs", action="store_true", help="leave the project footprint libraries alone")
    args = ap.parse_args()
    if args.check:
        sys.exit(0 if check(args.board) else 1)
    print("board:")
    rewrite_board(args.board)
    if not args.no_libs:
        print("libraries:")
        for path, lib_id in LIB_FILES.items():
            rewrite_library(path, lib_id)


if __name__ == "__main__":
    main()
