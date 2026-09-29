# PCB Layout Diagrams

Suggested top-copper floorplans for the circuits in this project with real
layout stakes — tight switching loops, thermal pads, or current-carrying
parts — originally derived from the KiCad schematic plus component datasheets,
not guessed. Model your KiCad layout after these rather than placing
parts from scratch.

## Diagrams

| Diagram | Stackup net group | Why it needed one |
|---|---|---|
| [Buck converter](power_buck_layout.md) | `/Power_Buck/*` | Switching regulator — tight input loop, short switch node, feedback routed clear of noise |
| [Charger](power_charger_layout.md) | `/Power_Charger/*` | Linear charger in a WSON-10 — thermal pad via array is the whole story |
| [Power latch](power_control_layout.md) | `/Power_Control/*` | One transistor carries the entire board's current; the power button's position is a mechanical constraint, not an electrical one |
