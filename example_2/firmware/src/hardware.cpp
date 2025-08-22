#include "hardware.h"

// Button debounce variables
volatile bool button_pressed = false;
volatile unsigned long last_interrupt = 0;

void initializeHardware() {
  // Configure pins
  pinMode(RELAY_PIN, OUTPUT);
  pinMode(LED_PIN, OUTPUT);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  
  // Set initial states
  digitalWrite(RELAY_PIN, LOW);
  digitalWrite(LED_PIN, HIGH);  // LED is active LOW on most ESP8266 modules
  
  // Attach interrupt for button
  attachInterrupt(digitalPinToInterrupt(BUTTON_PIN), buttonISR, FALLING);
}

void setRelay(bool state) {
  unsigned long now = millis();
  
  // Handle failure simulations
  if (test_state.simulate_stuck_on) {
    // Stuck ON - always keep relay on
    state = true;
  } else if (test_state.simulate_stuck_off) {
    // Stuck OFF - always keep relay off
    state = false;
  }
  
  if (state != test_state.relay_state) {
    if (test_state.relay_state) {
      // Relay turning off - record on time
      test_state.relay_on_time = now;
    } else {
      // Relay turning on - record off time  
      test_state.relay_off_time = now;
    }
    test_state.relay_toggle_count++;
  }
  
  test_state.relay_state = state;
  digitalWrite(RELAY_PIN, state ? HIGH : LOW);
  
  // LED follows relay state (inverted because LED is active low)
  setLED(state);
}

void setLED(bool state) {
  test_state.led_state = state;
  digitalWrite(LED_PIN, state ? LOW : HIGH);  // Active low
}

void IRAM_ATTR buttonISR() {
  unsigned long now = millis();
  if (now - last_interrupt > BUTTON_DEBOUNCE_MS) {
    button_pressed = true;
    last_interrupt = now;
  }
}