# Snips Controller Stackup design

`board.kdl` defines the electrical design and imports parts from the library
pinned in the repository's `manifest.kdl`. `parts.kdl` defines the Snips-specific
thumbstick. Component choices and purchasing details are specified on the
placements in `board.kdl`.

The board layout is in `../snips_controller.kicad_pcb`. To check the design, run
`stackup check PCB/stackup/board.kdl` from the repository root. To update the
PCB, use the Stackup KiCad plugin with `PCB/snips_controller.stackup_sch`.
CI checks both the design and whether the PCB is in sync with it.
Run `stackup bom PCB/stackup/board.kdl --locked` to export the purchasing CSV.
Parts installed after outsourced assembly use `hand=#true` on their placement;
they remain in the BOM and are marked `DNP` for the assembler.
