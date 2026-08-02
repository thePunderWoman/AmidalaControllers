#include <unity.h>

#include "ButtonState.h"
#include "Buttons.h"

void test_button_pins_are_unique() {
  for (size_t i = 0; i < Buttons::kCount; ++i) {
    for (size_t j = i + 1; j < Buttons::kCount; ++j) {
      TEST_ASSERT_NOT_EQUAL(Buttons::kPins[i], Buttons::kPins[j]);
    }
  }
}

void test_button_pins_within_gpio_range() {
  for (size_t i = 0; i < Buttons::kCount; ++i) {
    TEST_ASSERT_TRUE(Buttons::kPins[i] >= 0 && Buttons::kPins[i] <= 29);
  }
}

void test_button_state_defaults_to_not_pressed() {
  ButtonState state;
  TEST_ASSERT_FALSE(state.isPressed(Buttons::kMacro1));
}

void test_button_state_tracks_press_and_release() {
  ButtonState state;

  state.setPressed(Buttons::kVolUp, true);
  TEST_ASSERT_TRUE(state.isPressed(Buttons::kVolUp));

  state.setPressed(Buttons::kVolUp, false);
  TEST_ASSERT_FALSE(state.isPressed(Buttons::kVolUp));
}

void test_button_state_ignores_out_of_range_index() {
  ButtonState state;
  state.setPressed(Buttons::kCount + 5, true);
  TEST_ASSERT_FALSE(state.isPressed(Buttons::kCount + 5));
}

int main(int argc, char **argv) {
  UNITY_BEGIN();
  RUN_TEST(test_button_pins_are_unique);
  RUN_TEST(test_button_pins_within_gpio_range);
  RUN_TEST(test_button_state_defaults_to_not_pressed);
  RUN_TEST(test_button_state_tracks_press_and_release);
  RUN_TEST(test_button_state_ignores_out_of_range_index);
  return UNITY_END();
}
