#include "ButtonState.h"

void ButtonState::setPressed(size_t index, bool pressed) {
  if (index < pressed_.size()) {
    pressed_[index] = pressed;
  }
}

bool ButtonState::isPressed(size_t index) const {
  return index < pressed_.size() ? pressed_[index] : false;
}
