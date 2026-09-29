# 3D models

Models for parts whose stock KiCad model is missing, plus simplified placeholders for parts that have
no vendor model. The footprints reference them as `${KIPRJMOD}/libraries/3dmodels/...`, so they work on
any machine that has the repo. `scripts/set_3d_models.py` writes the model entries (paths, offsets,
rotations). `scripts/set_3d_models.py --check` fails if any footprint on the board has no model, or has
a model that does not resolve.

| File | Part | Source | Alignment notes |
|---|---|---|---|
| `USB_C_Receptacle_HRO_TYPE-C-31-M-12.step` | J_USB1, HRO TYPE-C-31-M-12 | EasyEDA/LCSC C165948, fetched with `easyeda2kicad` | Rotated 180° and offset -1.05mm in Y so the shell legs, pegs and SMD tails land on the KiCad footprint's pads |
| `SW_Alps_SKRTLAE010.step` | SW_PWR1, SW_VOL_*, SW_THR_*, SW_TRIG_DIG1 (side buttons) | EasyEDA/LCSC C110293 | Pegs, terminals and plunger already match the KiCad footprint. No offset |
| `QMA6100P_LGA-12_2x2mm.step` | U_ACCEL1 | EasyEDA/LCSC C2887190 | Centred, pin 1 matches. No offset |
| `Thumbstick_ALPS_RKJXV1224005.step` | J_STICK1 (DNP) | EasyEDA/LCSC C146170 (ALPS RKJXV1224005) | **Stand-in**: the GuliKit hall stick is a drop-in for this ALPS footprint family, but its body may differ. Z offset +11.4mm puts the housing standoffs on the board |
| `XBee3_TH_UFL_placeholder.step` | U_XBEE1 (DNP) | Built by `scripts/build_placeholder_3d_models.py` from the Digi XBee 3 HRM (90001543) U.FL through-hole drawing | **Envelope only**: outline, U.FL position, shield can and heights. It sits on two stock KiCad 2.00mm 1x10 sockets (5.6mm), which the footprint adds as separate models |

Models taken from KiCad's own library (`${KICAD10_3DMODEL_DIR}`) with no local copy:

- U_MCU1: `RF_Module.3dshapes/ESP32-S3-WROOM-1.step`, offset +3mm in Y because the project footprint's origin is 3mm off the stock one's.
- D_RGB1: `LED_SMD.3dshapes/LED_SK6812MINI-E_3.2x2.8mm_P1.5mm_ReverseMount.step`.

U_CHG1 uses the SnapEDA model already in `../BQ25185DLHR/`, rotated -90° about X because that file is Y-up.

## Why the stock models were missing

KiCad 10's `SW_Push_1P1T-MP_NO_Horizontal_Alps_SKRTLAE010` and `USB_C_Receptacle_HRO_TYPE-C-31-M-12`
footprints point at model files that KiCad 10 does not ship, and that are not in the upstream
kicad-packages3D repository either. The ESP32 footprint pointed at an old `${KICAD8_3RD_PARTY}` path.
The custom footprints (SK6812MINI-E-012, QMA6100P, GuliKit_HallStick, BQ25185DLHR) had no model at all.

## Caveats

- EasyEDA models are community/vendor-provided and are good for enclosure design, not guaranteed
  exact. Check critical dimensions (USB-C opening, button plunger, stick height) against the datasheet
  or a real part before finalising a shell.
- The SK6812MINI-E is a reverse-mount part. Its body sits 0.84mm below the pad plane, and in the model
  it intersects the board, because the SK6812MINI-E-012 footprint has no board cutout.
