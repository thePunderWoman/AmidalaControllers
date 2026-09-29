# SPICE check for the Power_Control soft-latch

`latch_sim.py` simulates the button, inverter, diode-OR, latch FET and power PMOS from
`PCB/stackup/board.kdl` and asserts the behavior we need. DRC and the netlist only prove
the wiring; they cannot show that a gate is driven high enough or that a power-up transient stays
quiet. This was written after exactly that kind of bug got through (see PRs #58-#60).

```sh
python3 scripts/spice/latch_sim.py              # all checks; exit 1 on any failure
python3 scripts/spice/latch_sim.py --cap 0      # without C_LATCH_G1 -> the insertion checks fail
python3 scripts/spice/latch_sim.py --cap 47n    # a smaller cap -> fails the gate-margin check
python3 scripts/spice/latch_sim.py --scenario press
```

It drives `libngspice`, which KiCad bundles at
`/Applications/KiCad/KiCad.app/Contents/PlugIns/sim/libngspice.dylib` (there is no ngspice CLI).
Set `NGSPICE_LIB` to use a different copy. No Python packages are needed.

## Checks

| Scenario | What it asserts |
|---|---|
| `insert` | Battery plugged in with the board off (VSYS 3.0-4.5V, 10us-1ms rise): `PWR_EN` stays under the buck's EN threshold, the latch gate peaks under 0.5V (below the AO3400A's 0.65V minimum threshold), and the board ends off. |
| `press` | A held button turns `PWR_EN` on within 20ms at VSYS 3.0V with worst-case FET thresholds, and at typical/best-case corners. |
| `shutdown` | The 3V3 rail collapsing after shutdown never lifts the latch gate or `PWR_EN`. |

## Keeping it in sync

The netlist is written by hand to mirror the Stackup power-control circuit. When it changes
(values, a new part on the latch/sense/EN nodes, a different FET), update the constants and topology
at the top of `latch_sim.py` and rerun. Treat a red run as a design problem first and a model problem
second, but do sanity-check the model too: an arbitrary 1uF on the EN pin once produced a fake
100ms glitch.

## What it does not model

- Generic SPICE models, not vendor ones: a 2N3904-family model for the MMBT3904, a fitted BAT54,
  1N4148, and Level-1 MOSFETs at typical and worst-case gate thresholds.
- VSYS is an ideal source with a clean ramp (no battery impedance, hot-plug bounce, or bulk caps).
- The buck's EN pin is just its pin capacitance; the buck, 3V3 loads and ESP32 boot are not simulated,
  so a short `PWR_EN` pulse is judged against the EN threshold only, not against what the MCU would do.
- Temperature, component tolerance and leakage beyond the diode/FET models.

Bench-confirm on the first real board: scope `PWR_EN` on battery insertion, and confirm a held press
latches at low battery.
