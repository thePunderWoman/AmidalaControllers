#!/usr/bin/env python3
"""ngspice check of the Power_Control soft-latch (button -> inverter -> diode-OR -> latch FET -> PMOS).

Connectivity checks (ERC/DRC/netlist) cannot show that a gate is actually driven high enough or that
a power-up transient stays quiet, so this simulates the circuit and asserts the behavior we need:

  insert    battery plugged in with the board off: PWR_EN must not pulse and the latch must stay off
  press     a held button must turn PWR_EN on quickly, across supply and FET-threshold corners
  shutdown  the 3V3 rail collapsing after shutdown must not re-trigger the latch

Uses libngspice, which KiCad bundles (there is no ngspice CLI). Set NGSPICE_LIB to override.

    python3 scripts/spice/latch_sim.py                # all scenarios, current design (exit 1 on failure)
    python3 scripts/spice/latch_sim.py --cap 0        # without C_LATCH_G1: shows the insertion blip
    python3 scripts/spice/latch_sim.py --scenario press -v

The netlist below mirrors PCB/stackup/board.kdl by hand. When that circuit changes, update the
values/topology here and rerun. See scripts/spice/README.md for what is and is not modeled.
"""
import argparse
import ctypes
import os
import sys
import tempfile

LIB_CANDIDATES = [
    os.environ.get("NGSPICE_LIB"),
    "/Applications/KiCad/KiCad.app/Contents/PlugIns/sim/libngspice.dylib",
    "/opt/homebrew/lib/libngspice.dylib",
    "/usr/local/lib/libngspice.dylib",
    "libngspice.so",
]

# Component values, mirroring PCB/stackup/parts.kdl (R_BTN_PU1 returns to 3V3, not VSYS).
R_BTN_PU1 = "100k"
C_DBNC1 = "100n"
R_INV_BASE1 = "100k"
R_INV_PU1 = "100k"
R_LATCH_G1 = "1Meg"
R_GATE1 = "100k"
R_PWR_EN_PD1 = "100k"
C_LATCH_G1 = "100n"

# Pass/fail limits.
MAX_BLIP_MS = 0.1        # PWR_EN above V_EN_HIGH on battery insertion
V_EN_HIGH = 1.2          # TLV62569 EN VIH max
MAX_OFF_LATCHG = 0.5     # latch gate must stay well under the AO3400A's 0.65V minimum threshold when it should be off
MAX_PRESS_MS = 20.0      # button press -> PWR_EN on

MODELS = """
.model QMMBT NPN(IS=6.734f XTI=3 EG=1.11 VAF=74.03 BF=416.4 NE=1.259 ISE=6.734f IKF=66.78m XTB=1.5 BR=.7371 NC=2 ISC=0 IKR=0 RC=1 CJC=3.638p MJC=.3085 VJC=.75 FC=.5 CJE=4.493p MJE=.2593 VJE=.75 TR=239.5n TF=301.2p ITF=.4 VTF=4 XTF=2 RB=10)
.model DBAT54 D(IS=1.4e-8 N=1.05 RS=3 CJO=10p M=0.4 VJ=0.5 BV=30)
.model D4148 D(IS=2.52n RS=.568 N=1.752 CJO=4p M=.4 TT=20n)
.model NAO3400 NMOS(LEVEL=1 VTO={VTHN} KP=5 LAMBDA=0.01)
.model PAO3401 PMOS(LEVEL=1 VTO={-VTHP} KP=4 LAMBDA=0.01)
.model SWM SW(RON=1 ROFF=1G VT=0.5 VH=0.1)
"""

_ng = None
_callbacks = []


def _load():
    global _ng
    if _ng is not None:
        return _ng
    lib = None
    for path in LIB_CANDIDATES:
        if not path:
            continue
        try:
            lib = ctypes.CDLL(path)
            break
        except OSError:
            continue
    if lib is None:
        sys.exit("libngspice not found. Install KiCad or set NGSPICE_LIB to a libngspice shared library.")
    send = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p)
    exit_ = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.c_bool, ctypes.c_bool, ctypes.c_int, ctypes.c_void_p)
    data = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_void_p)
    cbs = [
        send(lambda s, i, u: 0),                      # stdout/stderr text
        send(lambda s, i, u: 0),                      # status text
        exit_(lambda a, b, c, i, u: 0),
        data(lambda a, b, c, d: 0),
        data(lambda a, b, c, d: 0),
    ]
    _callbacks.extend(cbs)  # keep alive
    lib.ngSpice_Init(cbs[0], cbs[1], cbs[2], cbs[3], cbs[4], ctypes.c_void_p(0), None)
    _ng = lib
    return lib


def netlist(vthn, vthp, cap, vsys_pwl, v3v3_pwl, sw_pwl, ic, tstop, tstep, r_rail="1k"):
    mitigation = f"Clatch latchg 0 {cap}" if cap else "* no C_LATCH_G1"
    return f"""* Power_Control soft-latch
.param VTHN={vthn} VTHP={vthp}
{MODELS}
Vsys vsys 0 PWL({vsys_pwl})
* 3V3 rail: an ideal source behind r_rail (small = hard-driven/grounded, large = weak)
V3 v3src 0 PWL({v3v3_pwl})
R3 v3src v3v3 {r_rail}
C3 v3v3 0 10u
* button node
Rbtn v3v3 sense {R_BTN_PU1}
Cdb sense 0 {C_DBNC1}
Ssw sense 0 swc 0 SWM
Vsw swc 0 PWL({sw_pwl})
* inverter: own VSYS pull-up on the base, isolated from the sense node by a Schottky
Ribase vsys base {R_INV_BASE1}
Diso base sense DBAT54
Q1 trig base 0 QMMBT
Ripu vsys trig {R_INV_PU1}
* diode-OR into the latch gate (D_OR2 = MCU hold, held low here: MCU is off)
Dor1 trig latchg D4148
Dor2 hold latchg D4148
Vhold hold 0 0
Rlg latchg 0 {R_LATCH_G1}
{mitigation}
Mlatch pwrgate latchg 0 0 NAO3400 W=1 L=1
Cgs1 latchg 0 550p
Cgd1 latchg pwrgate 75p
* power switch and buck EN (pin capacitance only)
Rgate vsys pwrgate {R_GATE1}
Mpwr pwren pwrgate vsys vsys PAO3401 W=1 L=1
Cgs2 pwrgate vsys 500p
Rpd pwren 0 {R_PWR_EN_PD1}
Cen pwren 0 20p
{ic}
.tran {tstep} {tstop} uic
.end
"""


def simulate(**kw):
    """Run one transient. Returns (time list, {node: values})."""
    ng = _load()
    ng.ngSpice_Command(b"destroy all")
    lines = [l.encode() for l in netlist(**kw).strip().split("\n")] + [None]
    arr = (ctypes.c_char_p * len(lines))(*lines)
    ng.ngSpice_Circ(arr)
    ng.ngSpice_Command(b"run")
    nodes = ["sense", "base", "trig", "latchg", "pwrgate", "pwren", "v3v3"]
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "out.txt")
        ng.ngSpice_Command(f"wrdata {out} {' '.join(f'v({n})' for n in nodes)}".encode())
        rows = [[float(x) for x in line.split()] for line in open(out)]
    t = [r[0] for r in rows]
    return t, {n: [r[2 * i + 1] for r in rows] for i, n in enumerate(nodes)}


def time_above(t, v, threshold):
    return sum(t[i] - t[i - 1] for i in range(1, len(t)) if v[i] > threshold and v[i - 1] > threshold)


def first_above(t, v, threshold, after=0.0):
    return next((t[i] for i in range(len(t)) if t[i] >= after and v[i] > threshold), None)


def scenario_insert(cap, verbose):
    results = []
    for vsys, rise in ((3.0, "1m"), (3.7, "1m"), (4.2, "100u"), (4.5, "10u")):
        t, d = simulate(vthn=1.05, vthp=0.9, cap=cap, tstop="300m", tstep="5u", ic="",
                        vsys_pwl=f"0 0 {rise} {vsys} 1 {vsys}", v3v3_pwl="0 0", sw_pwl="0 0 1 0")
        blip = time_above(t, d["pwren"], V_EN_HIGH) * 1e3
        off = d["latchg"][-1]
        peak = max(d["latchg"])
        ok = blip <= MAX_BLIP_MS and off < MAX_OFF_LATCHG and peak < MAX_OFF_LATCHG
        results.append((f"insert VSYS={vsys}V", ok,
                        f"PWR_EN>{V_EN_HIGH}V for {blip:.2f} ms (max {MAX_BLIP_MS}), "
                        f"peak gate {peak:.2f}V (max {MAX_OFF_LATCHG}), ends off={off < MAX_OFF_LATCHG}"))
    return results


def scenario_press(cap, verbose):
    results = []
    # (VSYS, N-FET Vth, P-FET Vth): worst case at the bottom of the battery, typical, best case
    for vsys, vthn, vthp in ((3.0, 1.45, 1.3), (3.7, 1.05, 0.9), (4.2, 0.65, 0.6)):
        t, d = simulate(vthn=vthn, vthp=vthp, cap=cap, tstop="600m", tstep="20u", ic="",
                        vsys_pwl=f"0 0 1m {vsys} 1 {vsys}", v3v3_pwl="0 0",
                        sw_pwl="0 0 0.1 0 0.1001 1 0.6 1")
        on = first_above(t, d["pwren"], V_EN_HIGH, after=0.1)
        latency = None if on is None else (on - 0.1) * 1e3
        ok = latency is not None and latency <= MAX_PRESS_MS and d["pwren"][-1] > vsys - 0.3
        results.append((f"press VSYS={vsys}V VthN={vthn}V",
                        ok, "PWR_EN never came on" if latency is None else
                        f"PWR_EN on {latency:.1f} ms after press (max {MAX_PRESS_MS}), final {d['pwren'][-1]:.2f}V"))
    return results


def scenario_shutdown(cap, verbose):
    results = []
    for vsys in (3.7, 4.2):
        ic = (f".ic v(v3v3)=3.3 v(sense)=3.3 v(vsys)={vsys} v(pwrgate)={vsys} "
              "v(base)=0.72 v(trig)=0 v(latchg)=0 v(pwren)=0")
        t, d = simulate(vthn=1.05, vthp=0.9, cap=cap, tstop="400m", tstep="20u", ic=ic,
                        vsys_pwl=f"0 {vsys} 1 {vsys}", v3v3_pwl="0 3.3 10m 3.3 110m 0", sw_pwl="0 0 1 0")
        peak = max(d["latchg"])
        ok = peak < MAX_OFF_LATCHG and max(d["pwren"]) < MAX_OFF_LATCHG
        results.append((f"shutdown VSYS={vsys}V", ok,
                        f"peak gate {peak:.2f}V, peak PWR_EN {max(d['pwren']):.2f}V, "
                        f"lowest button node {min(d['sense']):.2f}V"))
    return results


SCENARIOS = {"insert": scenario_insert, "press": scenario_press, "shutdown": scenario_shutdown}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--scenario", choices=[*SCENARIOS, "all"], default="all")
    p.add_argument("--cap", default=C_LATCH_G1,
                   help="C_LATCH_G1 value (SPICE notation, e.g. 47n); 0 removes it. Default: %(default)s")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args()
    cap = None if args.cap in ("0", "none", "") else args.cap

    names = SCENARIOS if args.scenario == "all" else [args.scenario]
    failed = 0
    for name in names:
        for label, ok, detail in SCENARIOS[name](cap, args.verbose):
            print(f"{'PASS' if ok else 'FAIL'}  {label:32s} {detail}")
            failed += not ok
    print(f"\n{failed} check(s) failed" if failed else "\nall checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
