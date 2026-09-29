#!/usr/bin/env python3
"""Build simplified STEP placeholder models for parts that have no vendor model.

Currently: the Digi XBee 3 through-hole module (XB3-24Z8UT-J). Digi only
publishes STEP files for the Micro variants, so this builds an envelope model
from the "XBee 3 RF Module through-hole - U.FL antenna" mechanical drawing in
the Digi XBee 3 Hardware Reference Manual (90001543, p.36, units in inches).
It is meant for enclosure design (outline, height, U.FL position), not for
detailed rendering.

The model is in the Xbee3:XB324Z8UTJ footprint frame: origin at pin 1, KiCad
model axes (+X right, +Y toward the antenna end, i.e. PCB -Y, +Z up), and z
measured from the top of the main board. It assumes the module is plugged into
2.00mm 1x10 female sockets 5.6mm tall (the KiCad PinSocket_1x10_P2.00mm_Vertical
model, which the footprint places separately).

Requires the OpenCascade Python bindings:  pip install cadquery-ocp
Usage:  python3 scripts/build_placeholder_3d_models.py
"""
from pathlib import Path

from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakePolygon
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakePrism
from OCP.gp import gp_Pnt, gp_Vec
from OCP.IFSelect import IFSelect_RetDone
from OCP.Interface import Interface_Static
from OCP.STEPControl import STEPControl_AsIs, STEPControl_Writer

INCH = 25.4
OUT_DIR = Path(__file__).resolve().parent.parent / "PCB" / "libraries" / "3dmodels"

# --- XBee 3 TH geometry (mm), from the Digi drawing ---
PIN_ROW_SPACING = 22.0            # 2 x 0.433"
PIN_PITCH = 2.0
PINS_PER_ROW = 10
EDGE_MARGIN = 0.480 * INCH - 0.433 * INCH   # pin centre to board edge, ~1.19
PCB_THICKNESS = 0.031 * INCH      # 0.79
SPACER_HEIGHT = 0.079 * INCH      # header plastic under the carrier PCB, 2.0
CAN_HEIGHT = 0.087 * INCH         # shield can under the carrier PCB, 2.2
UFL_HEIGHT = 0.049 * INCH         # U.FL connector above the carrier PCB, 1.25
PIN_LENGTH = 0.24 * INCH          # pin tip to PCB bottom, 6.1
SOCKET_HEIGHT = 5.6               # KiCad PinSocket_1x10_P2.00mm_Vertical body height

# Board outline in the footprint's PCB coordinates (y down), taken from the
# footprint's F.Fab outline, which matches the drawing (0.960" x 1.087").
OUTLINE_PCB = [(-1.19, -1.19), (6.5, -7.72), (15.5, -7.72), (23.19, -1.19),
               (23.19, 19.914), (-1.19, 19.914)]
MODULE_CENTER_Y_PCB = (-7.72 + 19.914) / 2
UFL_CENTER_PCB = (PIN_ROW_SPACING / 2, MODULE_CENTER_Y_PCB - 0.324 * INCH)
UFL_SIZE = 3.0
# Shield can, from the bottom view (mirrored into top-view x). 0.247"-0.712"
# from the pin column, 0.050"-0.613" up from the last pin.
CAN_X_PCB = (PIN_ROW_SPACING - 0.712 * INCH, PIN_ROW_SPACING - 0.247 * INCH)
LAST_PIN_Y = PIN_PITCH * (PINS_PER_ROW - 1)
CAN_Y_PCB = (LAST_PIN_Y - 0.613 * INCH, LAST_PIN_Y - 0.050 * INCH)
SPACER_WIDTH = 2.0


def box(x0, y0, z0, x1, y1, z1):
    """Axis-aligned box from PCB-frame x/y (y down) and z; returns model-frame solid."""
    ya, yb = sorted((-y0, -y1))
    return BRepPrimAPI_MakeBox(gp_Pnt(min(x0, x1), ya, min(z0, z1)),
                               abs(x1 - x0), yb - ya, abs(z1 - z0)).Shape()


def prism(outline_pcb, z0, height):
    poly = BRepBuilderAPI_MakePolygon()
    for x, y in outline_pcb:
        poly.Add(gp_Pnt(x, -y, z0))
    poly.Close()
    face = BRepBuilderAPI_MakeFace(poly.Wire()).Face()
    return BRepPrimAPI_MakePrism(face, gp_Vec(0, 0, height)).Shape()


def fuse(shapes):
    result = shapes[0]
    for s in shapes[1:]:
        result = BRepAlgoAPI_Fuse(result, s).Shape()
    return result


def xbee3_th():
    spacer_bottom = SOCKET_HEIGHT
    pcb_bottom = spacer_bottom + SPACER_HEIGHT
    pcb_top = pcb_bottom + PCB_THICKNESS
    parts = [prism(OUTLINE_PCB, pcb_bottom, PCB_THICKNESS)]
    ux, uy = UFL_CENTER_PCB
    h = UFL_SIZE / 2
    parts.append(box(ux - h, uy - h, pcb_top, ux + h, uy + h, pcb_top + UFL_HEIGHT))
    parts.append(box(CAN_X_PCB[0], CAN_Y_PCB[0], pcb_bottom - CAN_HEIGHT,
                     CAN_X_PCB[1], CAN_Y_PCB[1], pcb_bottom))
    pin_tip = pcb_bottom - PIN_LENGTH
    for col in (0.0, PIN_ROW_SPACING):
        w = SPACER_WIDTH / 2
        parts.append(box(col - w, -w, spacer_bottom, col + w, LAST_PIN_Y + w, pcb_bottom))
        for i in range(PINS_PER_ROW):
            y = i * PIN_PITCH
            parts.append(box(col - 0.25, y - 0.25, pin_tip, col + 0.25, y + 0.25, spacer_bottom))
    return fuse(parts)


def write_step(shape, path):
    Interface_Static.SetCVal_s("write.step.schema", "AP214")
    w = STEPControl_Writer()
    w.Transfer(shape, STEPControl_AsIs)
    if w.Write(str(path)) != IFSelect_RetDone:
        raise RuntimeError(f"failed to write {path}")
    print(f"wrote {path}")


if __name__ == "__main__":
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_step(xbee3_th(), OUT_DIR / "XBee3_TH_UFL_placeholder.step")
