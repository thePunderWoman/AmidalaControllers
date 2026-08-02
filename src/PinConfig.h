#pragma once

// GPIO assignments for the Amidala Controller firmware (KB2040 / RP2040).
// Cross-reference: PCB/README.md, "GPIO Assignment".
//
// Prototyping note: the real PCB drives the XBee over SPI0 (GPIO18-20 plus
// CS on GPIO10) and puts Vol up/down on GPIO0/1. Until that board exists,
// the XBee talks over UART0 instead (its default pins are GPIO0/1 — see
// PCB/README.md, "Bringup Sequence"), so Vol up/down are temporarily moved
// to GPIO26/27. That leaves the LED indicator and charge-status inputs
// (also GPIO26/27 on the real PCB) without a home for now; wire those up
// once GPIO0/1 free up again on real hardware.

namespace PinConfig {

// XBee UART (prototyping only — default UART0 pins on RP2040/KB2040)
constexpr int kXbeeUartTx = 0;
constexpr int kXbeeUartRx = 1;

// Bottom edge buttons
constexpr int kDigitalTrigger = 2;
constexpr int kThumbstickClick = 3;
constexpr int kMacro1 = 4;
constexpr int kMacro2 = 5;
constexpr int kMacro3 = 6;
constexpr int kMacro4 = 7;
constexpr int kMacro5 = 8;
constexpr int kMacro6 = 9;

// Vol up/down: remapped here from their final GPIO0/1 slots (see note above)
constexpr int kVolUp = 26;
constexpr int kVolDown = 27;

// Spare GPIO, unused for now
constexpr int kSpareA2 = 28;
constexpr int kSpareA3 = 29;

// Reserved by the KB2040 board itself — never drive this pin
constexpr int kOnboardNeoPixel = 17;

// SPI0 XBee pins for the real PCB — unused while the XBee is on UART
constexpr int kXbeeSpiSck = 18;
constexpr int kXbeeSpiMosi = 19;
constexpr int kXbeeSpiMiso = 20;
constexpr int kXbeeSpiCs = 10;

}  // namespace PinConfig
