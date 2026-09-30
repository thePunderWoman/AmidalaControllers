# Snips Controller Stackup design

`board.kdl` defines the electrical design and imports parts from the library
pinned in the repository's `manifest.kdl`. `parts.kdl` defines the Snips-specific
thumbstick. `purchasing.kdl` declares the selected manufacturer parts and
supplier numbers. The match rules in `board.kdl` choose those parts by the
resolved value and footprint. The resulting BOM matches the previous factory
order in `../production/bom/snips_controller-bom.csv`.

The board layout is in `../snips_controller.kicad_pcb`. To check the design, run
`stackup check PCB/stackup/board.kdl` from the repository root. To update the
PCB, use the Stackup KiCad plugin with `PCB/snips_controller.stackup_sch`.
CI checks the design and whether the PCB is in sync with it.
Run `stackup bom PCB/stackup/board.kdl --locked` to export the purchasing CSV.
Parts installed after outsourced assembly use `hand=#true` on their placement;
they remain in the BOM and are marked `DNP` for the assembler.
The hand-installed GuliKit thumbstick had no recorded manufacturer part number
on the pre-port PCB; its assembly identity is checked separately.
