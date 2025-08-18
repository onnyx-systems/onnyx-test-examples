#include "commands.h"

void processCommand(String cmd) {
  cmd.trim();
  cmd.toUpperCase();
  
  if (cmd == "HELP") {
    printHelp();
  }
  else if (cmd == "STATUS") {
    printStatus();
  }
  else if (cmd == "RELAY ON" || cmd == "ON") {
    setRelay(true);
    Serial.println("OK:RELAY_ON");
  }
  else if (cmd == "RELAY OFF" || cmd == "OFF") {
    setRelay(false);
    Serial.println("OK:RELAY_OFF");
  }
  else if (cmd == "RELAY TOGGLE" || cmd == "TOGGLE") {
    setRelay(!test_state.relay_state);
    Serial.print("OK:RELAY_");
    Serial.println(test_state.relay_state ? "ON" : "OFF");
  }
  else if (cmd == "LED ON") {
    setLED(true);
    Serial.println("OK:LED_ON");
  }
  else if (cmd == "LED OFF") {
    setLED(false);
    Serial.println("OK:LED_OFF");
  }
  else if (cmd == "LED TOGGLE") {
    setLED(!test_state.led_state);
    Serial.print("OK:LED_");
    Serial.println(test_state.led_state ? "ON" : "OFF");
  }
  else if (cmd.startsWith("BURN ")) {
    // Parse burn-in parameters: BURN <cycles> [interval_ms]
    int space1 = cmd.indexOf(' ');
    int space2 = cmd.indexOf(' ', space1 + 1);
    
    if (space1 > 0) {
      unsigned long cycles = cmd.substring(space1 + 1, space2 > 0 ? space2 : cmd.length()).toInt();
      unsigned long interval = DEFAULT_BURN_INTERVAL;
      
      if (space2 > 0) {
        interval = cmd.substring(space2 + 1).toInt();
        if (interval < MIN_BURN_INTERVAL) interval = MIN_BURN_INTERVAL;
      }
      
      burnInTest(cycles, interval);
    } else {
      Serial.println("ERROR:INVALID_BURN_PARAMS");
    }
  }
  else if (cmd == "STOP") {
    test_state.burn_in_active = false;
    Serial.println("OK:TEST_STOPPED");
  }
  else if (cmd == "RESET") {
    // Reset all counters
    test_state.button_press_count = 0;
    test_state.relay_toggle_count = 0;
    test_state.burn_in_cycles = 0;
    test_state.relay_on_time = 0;
    test_state.relay_off_time = 0;
    test_state.test_start_time = millis();
    Serial.println("OK:COUNTERS_RESET");
  }
  else if (cmd == "READ BUTTON") {
    Serial.print("BUTTON:");
    Serial.println(digitalRead(BUTTON_PIN) ? "RELEASED" : "PRESSED");
  }
  else if (cmd == "TEST") {
    // Quick self-test sequence
    Serial.println("STARTING_SELF_TEST");
    
    Serial.print("TEST:LED...");
    setLED(true);
    delay(500);
    setLED(false);
    delay(500);
    Serial.println("OK");
    
    Serial.print("TEST:RELAY...");
    setRelay(true);
    delay(500);
    setRelay(false);
    delay(500);
    Serial.println("OK");
    
    Serial.print("TEST:BUTTON...");
    Serial.println(digitalRead(BUTTON_PIN) ? "RELEASED" : "PRESSED");
    
    Serial.println("SELF_TEST_COMPLETE");
  }
  else if (cmd == "JSON") {
    // Output status in JSON format for automated parsing
    Serial.print("{");
    Serial.print("\"relay\":");
    Serial.print(test_state.relay_state ? "true" : "false");
    Serial.print(",\"led\":");
    Serial.print(test_state.led_state ? "true" : "false");
    Serial.print(",\"button\":");
    Serial.print(digitalRead(BUTTON_PIN) ? "false" : "true");
    Serial.print(",\"button_count\":");
    Serial.print(test_state.button_press_count);
    Serial.print(",\"relay_count\":");
    Serial.print(test_state.relay_toggle_count);
    Serial.print(",\"uptime\":");
    Serial.print(millis() - test_state.test_start_time);
    Serial.print(",\"relay_on_ms\":");
    Serial.print(test_state.relay_on_time);
    Serial.print(",\"relay_off_ms\":");
    Serial.print(test_state.relay_off_time);
    Serial.println("}");
  }
  else if (cmd == "TIMING") {
    // For oscilloscope timing measurements
    Serial.println("TIMING_TEST:START");
    unsigned long start = micros();
    digitalWrite(RELAY_PIN, HIGH);
    unsigned long relay_on = micros();
    delay(10);
    digitalWrite(RELAY_PIN, LOW);
    unsigned long relay_off = micros();
    
    Serial.print("RELAY_ON_TIME_US:");
    Serial.println(relay_on - start);
    Serial.print("RELAY_OFF_TIME_US:");
    Serial.println(relay_off - relay_on);
    Serial.println("TIMING_TEST:END");
  }
  else if (cmd == "VERSION") {
    Serial.println("VERSION:" FIRMWARE_VERSION);
    Serial.print("BUILD:");
    Serial.println(__DATE__ " " __TIME__);
    Serial.print("CHIP_ID:");
    Serial.println(ESP.getChipId(), HEX);
    Serial.print("FLASH_SIZE:");
    Serial.println(ESP.getFlashChipSize());
  }
  else if (cmd == "") {
    // Empty command, just show prompt
  }
  else {
    Serial.print("ERROR:UNKNOWN_COMMAND:");
    Serial.println(cmd);
  }
}

void printStatus() {
  Serial.println("=== STATUS ===");
  Serial.print("RELAY: ");
  Serial.println(test_state.relay_state ? "ON" : "OFF");
  Serial.print("LED: ");
  Serial.println(test_state.led_state ? "ON" : "OFF");
  Serial.print("BUTTON: ");
  Serial.println(digitalRead(BUTTON_PIN) ? "RELEASED" : "PRESSED");
  Serial.print("BUTTON_PRESSES: ");
  Serial.println(test_state.button_press_count);
  Serial.print("RELAY_TOGGLES: ");
  Serial.println(test_state.relay_toggle_count);
  Serial.print("UPTIME_MS: ");
  Serial.println(millis() - test_state.test_start_time);
  
  if (test_state.burn_in_active) {
    Serial.print("BURN_IN: ");
    Serial.print(test_state.burn_in_cycles);
    Serial.print("/");
    Serial.println(test_state.burn_in_target);
  }
}

void printHelp() {
  Serial.println("=== COMMANDS ===");
  Serial.println("ON/OFF         - Control relay");
  Serial.println("TOGGLE         - Toggle relay state");
  Serial.println("LED ON/OFF     - Control LED");
  Serial.println("STATUS         - Show current status");
  Serial.println("JSON           - Output JSON status");
  Serial.println("TEST           - Run self-test");
  Serial.println("TIMING         - Relay timing test");
  Serial.println("READ BUTTON    - Read button state");
  Serial.println("BURN <n> [ms]  - Burn-in test n cycles");
  Serial.println("STOP           - Stop burn-in test");
  Serial.println("RESET          - Reset counters");
  Serial.println("VERSION        - Show version info");
  Serial.println("HELP           - Show this help");
}

void burnInTest(unsigned long cycles, unsigned long interval) {
  test_state.burn_in_active = true;
  test_state.burn_in_cycles = 0;
  test_state.burn_in_target = cycles;
  test_state.burn_in_interval = interval;
  
  Serial.print("BURN_IN_START:");
  Serial.print(cycles);
  Serial.print(",INTERVAL:");
  Serial.println(interval);
}