#ifndef TEST_STATE_H
#define TEST_STATE_H

#include <Arduino.h>

// Test state structure
struct TestState {
  bool relay_state = false;
  bool led_state = false;
  unsigned long button_press_count = 0;
  unsigned long last_button_press = 0;
  unsigned long relay_toggle_count = 0;
  unsigned long test_start_time = 0;
  unsigned long relay_on_time = 0;
  unsigned long relay_off_time = 0;
  bool burn_in_active = false;
  unsigned long burn_in_cycles = 0;
  unsigned long burn_in_target = 0;
  unsigned long burn_in_interval = 1000;
};

extern TestState test_state;

#endif // TEST_STATE_H