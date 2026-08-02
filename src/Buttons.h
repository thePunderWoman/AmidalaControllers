#pragma once

#include <cstddef>

#include "PinConfig.h"

// All digital buttons and their current GPIO pin, in prototyping (UART
// XBee) configuration. See PinConfig.h for the pin-mapping caveats.
namespace Buttons {

enum Index : size_t {
  kDigitalTrigger = 0,
  kThumbstickClick,
  kMacro1,
  kMacro2,
  kMacro3,
  kMacro4,
  kMacro5,
  kMacro6,
  kVolUp,
  kVolDown,
  kCount
};

constexpr int kPins[kCount] = {
    PinConfig::kDigitalTrigger,   PinConfig::kThumbstickClick,
    PinConfig::kMacro1,           PinConfig::kMacro2,
    PinConfig::kMacro3,           PinConfig::kMacro4,
    PinConfig::kMacro5,           PinConfig::kMacro6,
    PinConfig::kVolUp,            PinConfig::kVolDown,
};

}  // namespace Buttons
