#pragma once

#include <array>
#include <cstddef>

#include "Buttons.h"

// Tracks the last-known pressed/released state of every button. Hardware
// agnostic — main.cpp is responsible for feeding it real digitalRead()
// values on real hardware; anything else can drive it directly.
class ButtonState {
 public:
  void setPressed(size_t index, bool pressed);
  bool isPressed(size_t index) const;

 private:
  std::array<bool, Buttons::kCount> pressed_{};
};
