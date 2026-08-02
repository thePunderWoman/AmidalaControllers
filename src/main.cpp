#include <Arduino.h>

#include "ButtonState.h"
#include "Buttons.h"

namespace {

// Prototyping only — the real PCB puts the XBee on SPI0 instead.
constexpr unsigned long kXbeeUartBaud = 9600;
constexpr unsigned long kPollIntervalMs = 20;

ButtonState buttonState;
unsigned long lastPollMs = 0;

}  // namespace

void setup() {
  Serial.begin(115200);

  // GPIO0/1 are UART0's default pins on RP2040, which is exactly where the
  // XBee is wired for prototyping — no pin remapping needed.
  Serial1.begin(kXbeeUartBaud);

  for (size_t i = 0; i < Buttons::kCount; ++i) {
    pinMode(Buttons::kPins[i], INPUT_PULLUP);
  }
}

void loop() {
  const unsigned long now = millis();
  if (now - lastPollMs < kPollIntervalMs) {
    return;
  }
  lastPollMs = now;

  for (size_t i = 0; i < Buttons::kCount; ++i) {
    // Buttons wire to GND with the internal pull-up enabled, so LOW = pressed.
    buttonState.setPressed(i, digitalRead(Buttons::kPins[i]) == LOW);
  }
}
