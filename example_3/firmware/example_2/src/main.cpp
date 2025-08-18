#include <Arduino.h>
#include "config.h"
#include "test_state.h"
#include "hardware.h"
#include "commands.h"

// Global test state instance
TestState test_state;

// Command buffer
String command_buffer = "";

void setup() {
  // Initialize serial like Tasmota does for ESP8266
  Serial.begin(SERIAL_BAUD);
  Serial.println();  // Important for ESP8266/ESP8285
  Serial.flush();    // Ensure buffer is clear
  delay(100);        // Give serial time to stabilize
  
  // Initialize hardware
  initializeHardware();
  
  test_state.test_start_time = millis();
  
  // Print startup message
  Serial.println("================================");
  Serial.println("Sonoff Test Firmware v" FIRMWARE_VERSION);
  Serial.println("Manufacturing Test CLI");
  Serial.println("================================");
  Serial.println("Type 'help' for commands");
  Serial.print("> ");
  Serial.flush();
}

void loop() {
  // Check for serial input
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (command_buffer.length() > 0) {
        Serial.println();
        processCommand(command_buffer);
        command_buffer = "";
        if (!test_state.burn_in_active) {
          Serial.print("> ");
        }
      }
    } else {
      command_buffer += c;
      Serial.print(c);  // Echo character
    }
  }
  
  // Handle button press
  if (button_pressed) {
    button_pressed = false;
    test_state.button_press_count++;
    test_state.last_button_press = millis();
    Serial.println();
    Serial.print("BUTTON_PRESS:");
    Serial.print(test_state.button_press_count);
    Serial.print(",TIME:");
    Serial.println(millis());
    if (!test_state.burn_in_active) {
      Serial.print("> ");
    }
  }
  
  // Handle burn-in test
  if (test_state.burn_in_active) {
    static unsigned long last_toggle = 0;
    if (millis() - last_toggle >= test_state.burn_in_interval) {
      last_toggle = millis();
      setRelay(!test_state.relay_state);
      test_state.burn_in_cycles++;
      
      // Print progress every 10 cycles
      if (test_state.burn_in_cycles % 10 == 0) {
        Serial.print("BURN_IN:");
        Serial.print(test_state.burn_in_cycles);
        Serial.print("/");
        Serial.println(test_state.burn_in_target);
      }
      
      // Check if burn-in complete
      if (test_state.burn_in_cycles >= test_state.burn_in_target) {
        test_state.burn_in_active = false;
        Serial.println("BURN_IN_COMPLETE");
        Serial.print("> ");
      }
    }
  }
}