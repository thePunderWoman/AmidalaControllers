# Amidala Controller PCB

A wireless handheld controller for R2-D2 droid operation, designed for use at public events and conventions. Communicates with the droid via XBee3 Zigbee radio in a packetized state-report architecture.

## Hardware Overview

| Component | Part | Notes |
|---|---|---|
| MCU | Adafruit KB2040 | RP2040, Pro Micro form factor, USB-C |
| ADC | ADS1115 | 16-bit, 4-channel, I2C |
| Display | SSD1306 1.3" OLED | 128x64, monochrome, I2C |
| Radio | XBee3 | Zigbee, SPI mode |
| Hall trigger | DRV5055 | Ratiometric linear hall effect, 3.3V |
| Thumbstick | GuliKit hall effect module | Native 3.3V, analog X/Y + click |
| Buttons | Omron B3F series | Tactile momentary, all inputs to GND |
| Charger | bq25185 | USB/DC input, power path management |
| Buck | TPS62569 | 3.3V output |
| Battery | 18650 or 14500 Li-ion | Swappable, single cell |

## GPIO Assignment

### SPI0 (XBee) — Silkscreen-labeled SPI pins
| Function | Board Label | GPIO |
|---|---|---|
| XBee SCK | CLK | GPIO18 |
| XBee MOSI | MOSI | GPIO19 |
| XBee MISO | MISO | GPIO20 |
| XBee CS | D10 | GPIO10 |

### Bottom Edge — Buttons & Control
| Function | Board Label | GPIO |
|---|---|---|
| Vol up | TX/D0 | GPIO0 |
| Vol down | RX/D1 | GPIO1 |
| Digital trigger (bumper) | D2 | GPIO2 |
| Thumbstick click (KEY) | D3 | GPIO3 |
| Macro button 1 | D4 | GPIO4 |
| Macro button 2 | D5 | GPIO5 |
| Macro button 3 | D6 | GPIO6 |
| Macro button 4 | D7 | GPIO7 |
| Macro button 5 | D8 | GPIO8 |
| Macro button 6 | D9 | GPIO9 |

### Analog Pins — Misc Control Signals
| Function | Board Label | GPIO |
|---|---|---|
| LED indicator | A0 | GPIO26 |
| Charge status (bq25185 STAT) | A1 | GPIO27 |

### Spare GPIO
| Board Label | GPIO |
|---|---|
| A2 | GPIO28 |
| A3 | GPIO29 |

### I2C — STEMMA QT (no GPIO cost)
| Device | Notes |
|---|---|
| ADS1115 | Shares bus with OLED |
| SSD1306 OLED | Shares bus with ADS1115 |

#### ADS1115 Channel Assignments
| Channel | Function |
|---|---|
| A0 | Analog trigger (DRV5055) |
| A1 | Thumbstick X (GuliKit) |
| A2 | Thumbstick Y (GuliKit) |
| A3 | Battery voltage sense |

### Reserved / Onboard
| Board Label | GPIO | Notes |
|---|---|---|
| — | GPIO17 | Onboard NeoPixel — do not use |

---

## Passives & Support Components

### Decoupling Caps
| Component | Value | Notes |
|---|---|---|
| DRV5055 VCC | 100nF ceramic | Place close to supply pin |
| GuliKit VCC | 100nF ceramic | Place close to supply pin |
| ADS1115 VDD | 100nF ceramic + 10µF bulk | Both recommended |

### Pull-up Resistors
| Signal | Value | Notes |
|---|---|---|
| bq25185 STAT pin | 10kΩ | STAT is open-drain, pull up to 3.3V |
| I2C SDA/SCL | 4.7kΩ | Verify not already present on breakout boards before adding external pull-ups |

### Current Limiting Resistors
| Component | Value | Notes |
|---|---|---|
| LED indicator | 330Ω–1kΩ | 330Ω ~8-10mA (bright), 1kΩ for lower power |

### Buttons
No external components needed. All buttons wire to GND; enable RP2040 internal pull-ups in firmware (`INPUT_PULLUP`).

### KB2040
No additional passives needed — all decoupling is onboard.

### XBee
Refer to AmidalaShield V1.2 design for XBee3 support circuitry (decoupling, RESET pull-up, RC filter). Same approach applies here.

---

## Communication Architecture

Controllers communicate with the droid via XBee3 in **packetized state-report** mode. The KB2040 firmware reads all inputs locally (button states, ADS1115 ADC values) and assembles them into a structured payload transmitted periodically over SPI to the XBee3 radio. The receiving AmidalaShield deserializes the packet and interprets controller state.

This approach is preferred over per-signal transmission as it is more efficient, easier to deserialize, and robust to timing issues.

### Network Configuration
- Each droid has its own coordinator with a unique PAN ID
- All coordinators share the same AES encryption key
- Controllers are configured as routers
- "Switch droid" functionality is implemented via XBee API commands to leave the current network and rejoin a different PAN ID on demand
- Active droid name and connection status are shown on the OLED display

---

## Bringup Sequence

For breadboard bringup, GPIO0 (TX) and GPIO1 (RX) can be temporarily used for XBee UART communication with a serial XBee prototyping board, freeing the SPI pins. Vol up and Vol down are remapped to A0/A1 (GPIO26/27) during this phase.

Recommended bringup order:
1. KB2040 alone — verify USB enumeration, flash blink sketch
2. OLED on STEMMA QT — verify I2C, get something on screen
3. ADS1115 on STEMMA QT — read all four channels, verify thumbstick and trigger respond
4. Buttons — verify all 10 digital inputs, pull-ups, and debounce
5. LED + charge status — verify GPIO26/27 high/low behavior
6. XBee over UART — verify basic communication with serial prototyping board

---

## Power Architecture

- Battery → bq25185 (charger + power path) → TPS62569 (3.3V buck) → KB2040 RAW pin and all 3.3V logic
- bq25185 STAT pin → GPIO27 (open-drain, 10kΩ pull-up to 3.3V)
- Battery voltage sense → ADS1115 A3 channel (via voltage divider if needed)
- All logic is 3.3V — KB2040, ADS1115, DRV5055, GuliKit thumbstick are all 3.3V native

## Power Management

Firmware implements tiered power saving:
- **Active**: full brightness OLED, normal polling rate
- **Idle (short timeout)**: OLED dimmed via SSD1306 contrast command
- **Idle (long timeout)**: OLED off
- **Sleep**: MCU sleep, wake on any button press via GPIO interrupt