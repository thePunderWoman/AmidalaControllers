# Snips Controller PCB

A wireless handheld controller for R2-D2 droid operation, designed for use at public events and conventions. Communicates with the droid via XBee3 Zigbee radio in a packetized state-report architecture.

The electrical design is in [Stackup KDL](stackup/board.kdl), using the pinned
Stackup library plus a [local thumbstick model](stackup/parts.kdl). The existing [KiCad PCB](snips_controller.kicad_pcb) is linked
through `snips_controller.stackup_sch`; sync it with the Stackup KiCad plugin. Run
`stackup check PCB/stackup/board.kdl` from the repository root before syncing.

## Hardware Overview

| Component | Part | Notes | Layout diagram |
|---|---|---|---|
| MCU | ESP32-S3-WROOM-1 module | Pre-certified: integrated flash, crystal, WiFi/BT radio + antenna. Same MCU family as Amidala. See `GPIO_table.md` for the full support circuitry | — |
| Display | SSD1306 1.3" OLED | 128x64, monochrome, I2C | — |
| Radio | XBee3 | Zigbee, SPI mode, THT socket (proto) | — |
| Hall trigger | DRV5055A2 | Ratiometric linear hall effect, 3.3V | — |
| Thumbstick | GuliKit hall effect module | Native 3.3V, analog X/Y + click | — |
| Buttons | Omron B3F series | Tactile momentary clicky | — |
| RGB LED | SK6812 NeoPixel-compatible | RMT-driven status indicator; specified supply begins at 3.7 V, but board supplies 3.3 V | — |
| Charger | bq25185 | USB/DC input, power path, 4.2V/500mA | [diagram](diagrams/power_charger_layout.md) |
| Buck | TLV62569 | 3.3V output, 1A | [diagram](diagrams/power_buck_layout.md) |
| Battery | 18650 or 14500 Li-ion | Swappable single cell, TBD empirically | — |
| Power switch | DMG2305UX + 2N7002 | Soft latch, hybrid hardware+firmware | [diagram](diagrams/power_control_layout.md) |

## Layout Diagrams

Suggested top-copper floorplans for the three sheets with real layout
stakes — a switching regulator, a linear charger with a thermal pad, and
the transistor carrying the whole board's current. Each is checked
against the actual component datasheet, not just the schematic. See
[`diagrams/README.md`](diagrams/README.md) for the full list and how the
files are organized.

- [Buck converter](diagrams/power_buck_layout.md) — `/Power_Buck/*` nets in Stackup
- [Charger](diagrams/power_charger_layout.md) — `/Power_Charger/*` nets in Stackup
- [Power latch](diagrams/power_control_layout.md) — `/Power_Control/*` nets in Stackup

## GPIO Assignment

> See `GPIO_table.md` for the full pin-by-pin table, including
> ESP32-S3-WROOM-1 support circuitry — this section is a summary.

### Reserved — Do Not Use
| Pin | Reason |
|---|---|
| 1, 40, 41 | GND |
| 2 | 3V3 |
| 3 (EN) | Reset/enable, pulled up via R_EN_PU |
| 13 (USB_D-) | Native USB |
| 14 (USB_D+) | Native USB |
| 27 (GPIO0/BOOT) | Boot strapping pin, pulled up via R_BOOT_PU + button |
| 26-32 (internal) | Internal SPI flash — not present on this module at all |
| 33-34 (internal) | Not broken out on the WROOM-1 module |
| 8 (GPIO15) | XBee SPI_ATTN — data-ready interrupt |
| 22 (GPIO18) | XBee ON_SLEEP status input |

Usable with care (strapping pins, sampled at boot): 15 (GPIO3), 16 (GPIO46), 26 (GPIO45).
Clean spares (default JTAG): 34-35 (GPIO41-42). 32/33 from the same group are used by BTN_VOL_DN/BTN_VOL_UP.

The module integrates the WiFi/BT radio, antenna, flash, and crystal
internally — no external wireless component, no bit-banged interface
consuming GPIO, unlike the bare-RP2350A design this replaced.

### SPI (XBee)
| Function | Pin |
|---|---|
| XBee SCK | 18 |
| XBee MOSI | 19 |
| XBee MISO | 20 |
| XBee CS | 21 |
| XBee ON_SLEEP | 22 |
| XBee SPI_ATTN | 8 |

### I2C (OLED)
| Function | Pin |
|---|---|
| SDA | 12 |
| SCL | 17 |

### ADC — ADC1 only (ADC2 is unusable while WiFi is active)
| Function | Pin |
|---|---|
| Analog trigger (DRV5055) | 4 |
| Thumbstick X (GuliKit) | 5 |
| Thumbstick Y (GuliKit) | 6 |
| VSYS battery sense | 7 |

### Digital Inputs / Outputs
| Function | Pin | Notes |
|---|---|---|
| Vol up | 33 | Active low, internal pull-up |
| Vol down | 32 | Active low, internal pull-up |
| Trigger up (mirrored VOL pair, opposite-handed variant) | 9 | Active low, internal pull-up |
| Trigger down (mirrored VOL pair, opposite-handed variant) | 10 | Active low, internal pull-up |
| Digital trigger (bumper) | 11 | Active low, internal pull-up |
| Thumbstick click (KEY) | 23 | Active low, internal pull-up |
| Macro buttons 1-6 | 24, 25, 28, 29, 30, 31 | Active low, internal pull-up — direct-wired, no scan matrix |
| Power button sense | 38 | Input, 3-second hold detect |
| Charge status STAT1 | 39 | Open-drain, 10kΩ pull-up to 3V3 |
| Power latch hold | 36 | Output, HIGH on boot to hold latch |
| RGB LED DIN (SK6812) | 37 | RMT-driven |

### Macro Buttons — Direct-Wired, No Scan Matrix
6 macro buttons, each on its own GPIO with an internal pull-up. No
anti-ghosting diodes or scan firmware needed — ESP32-S3-WROOM-1 has
enough spare GPIO (roughly 8) that the 1-pin savings a 2x3 matrix would
give isn't worth the added complexity, unlike the bare-RP2350A design
(only 1 spare pin) this replaced.

### Spare GPIO
Pins 34-35 (default JTAG, clean) and 15/16/26 (strapping, usable with care).
32/33 from the same JTAG group are used by BTN_VOL_DN/BTN_VOL_UP.

---

## MCU Support Circuitry (ESP32-S3-WROOM-1)

Far simpler than the bare-RP2350A design it replaced — the module
integrates flash, crystal, and the WiFi/BT radio + antenna internally.
What's left: EN pull-up, BOOT pull-up + button, USB series resistors,
3V3 decoupling, and the VSYS battery-sense divider — all standard
ESP32-S3 practice, matching Espressif's own reference designs. See
`GPIO_table.md` for the full component list.

**No longer needed at all:** external QSPI flash chip, crystal + load
caps, core-regulator LC filter, ADC_AVDD RC filter, per-pin IOVDD/DVDD
decoupling network, separate wireless module + its bit-banged interface
+ antenna licensing question.

> **Layout note:** the module's footprint includes the required antenna
> keepout area — keep copper/components out of it per the module's
> datasheet. Much simpler than a custom PCB trace antenna, but still a
> real layout-stage requirement.

---

## Passives & Support Components

### Decoupling Caps
| Component | Value | Notes |
|---|---|---|
| DRV5055 VCC | 100nF ceramic | Close to supply pin |
| GuliKit VCC | 100nF ceramic | Close to supply pin |
| SK6812 VCC | 100nF ceramic | Close to supply pin |
| bq25185 VIN | 10µF + 100nF ceramic | X7R/X5R, 25V rated |
| bq25185 SYS | 10µF + 100nF ceramic | X7R/X5R, 25V rated |
| bq25185 BAT | 10µF ceramic | |
| TLV62569 VIN | 10µF ceramic | |
| TLV62569 VOUT | 22µF ceramic | |
| ESP32-S3-WROOM-1 3V3 | 10µF + 100nF ceramic | Standard module decoupling |

### Pull-up Resistors
| Signal | Value | Notes |
|---|---|---|
| bq25185 STAT1 | 10kΩ | Open-drain, pull up to 3V3 |
| bq25185 TS/MR | 10kΩ to GND | REQUIRED if no thermistor — floating = no charging |
| XBee RESET | 10kΩ to 3V3 | Plus 100Ω + 100nF RC filter at pin |
| I2C SDA/SCL | 4.7kΩ | **DNP for prototyping** — Adafruit #938 has onboard pull-ups. Populate only on final PCB with bare OLED panel |
| ESP32-S3 EN | 10kΩ to 3V3 | Reset/enable |
| ESP32-S3 GPIO0/BOOT | 10kΩ to 3V3 | Plus button to GND to force UF2/download mode |

### Series Resistors
| Signal | Value | Notes |
|---|---|---|
| SK6812 DIN (pin 37) | 300–500Ω | Signal integrity, place close to pad |
| USB D+/D- (pins 13/14) | 27Ω | Between module and external USB-C connector |

### Direct Buttons (all of them — no matrix)
No external components needed. Wire to GND; enable ESP32-S3 internal
pull-ups in firmware. Applies to vol up/down, digital trigger, stick
click, and all 6 macro buttons.

### XBee
Refer to AmidalaShield V1.2 for XBee3 support circuitry. THT socket for prototyping; update footprint to SMT module for final PCB if size requires.

Beyond the 4-wire SPI bus (SCK/MOSI/MISO/CS) and RESET, three more pins are
wired per Amidala's actual netlist: DTR tied to GND, ON_SLEEP and SPI_ATTN
to pins 22/8. SPI_ATTN in particular is the XBee's data-ready interrupt —
needed for reliable SPI transfers, not just a nice-to-have.

---

## Communication Architecture

Controllers communicate with the droid via XBee3 in **packetized state-report** mode. The ESP32-S3 firmware reads all inputs locally (button states, ADC values for analog trigger and thumbstick) and assembles them into a structured payload transmitted periodically over SPI to the XBee3 radio. The receiving AmidalaShield deserializes the packet and interprets controller state.

This approach is preferred over per-signal transmission as it is more efficient, easier to deserialize, and robust to timing issues.

### Network Configuration
- Each droid has its own coordinator with a unique PAN ID
- All coordinators share the same AES encryption key
- Controllers are configured as routers
- "Switch droid" functionality is implemented via XBee API commands to leave the current network and rejoin a different PAN ID on demand
- Active droid name and connection status are shown on the OLED display

---

## Bringup Sequence

Recommended bringup order:
1. ESP32-S3-WROOM-1 alone — verify USB enumeration, flash blink sketch, confirm pin 36 latch hold works
2. OLED on I2C — verify I2C on pins 12/17, get something on screen
3. SK6812 RGB LED — verify RMT output on pin 37, cycle colors
4. Buttons — verify direct inputs on pins 9/10/11/23 and all 6 macro buttons (pins 24/25/28/29/30/31)
5. Charge status — verify STAT1 on pin 39 reads correctly
6. DRV5055 + GuliKit thumbstick — verify ADC1 readings on pins 4/5/6
7. XBee over SPI — verify basic communication

---

## Power Architecture

- Battery → bq25185 (charger + power path, 4.2V VBATREG, 500mA) → TLV62569 (3.3V buck) → ESP32-S3-WROOM-1 3V3 and all 3.3V logic
- Power switch: soft latch (DMG2305UX PFET + 2N7002 NFET) controls TLV62569 EN pin
- Boot: press power button → hardware latch enables 3V3 → ESP32-S3-WROOM-1 boots → pin 36 driven HIGH to hold latch
- Shutdown: firmware detects 3-second hold on pin 38 → graceful shutdown → pin 36 LOW → power cut
- bq25185 STAT1 → pin 39 (open-drain, 10kΩ pull-up to 3V3)
- Battery voltage sense → pin 7 via external R_VSYS1/R_VSYS2 divider (reads VSYS/3 via ADC1)
- ESP32-S3-WROOM-1, DRV5055, and GuliKit thumbstick use the 3V3 rail. The SK6812 also uses it, but its 3.7 V minimum supply makes that LED connection out of specification.

No firmware ADC-gating workaround needed for battery sense — WiFi is
fully on-die on ESP32-S3 and doesn't share any exposed GPIO/ADC path
with the VSYS sense pin, unlike the old bit-banged RP2350+CYW43439
design.

## Power Management

Firmware implements tiered power saving:
- **Active**: full brightness OLED, normal polling rate
- **Idle (short timeout)**: OLED dimmed via SSD1306 contrast command
- **Idle (long timeout)**: OLED off
- **Sleep**: MCU sleep, wake on any button press via GPIO interrupt
