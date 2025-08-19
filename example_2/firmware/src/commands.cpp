#include "commands.h"

extern "C" {
#include "user_interface.h"
}

void processCommand(String cmd) {
  cmd.trim();
  String cmdUpper = cmd;
  cmdUpper.toUpperCase();
  
  // Support both Tasmota and original commands
  if (cmdUpper == "HELP") {
    printHelp();
  }
  else if (cmdUpper == "STATUS" || cmdUpper == "STATUS 0") {
    // Tasmota-style Status 0 response
    printTasmotaStatus();
  }
  else if (cmdUpper == "STATUS 1") {
    // Tasmota Status 1 - Device parameters
    printTasmotaStatus1();
  }
  else if (cmdUpper == "STATUS 2") {
    // Tasmota Status 2 - Firmware info
    printTasmotaStatus2();
  }
  else if (cmdUpper == "STATUS 3") {
    // Tasmota Status 3 - Logging (stub)
    Serial.println("{\"StatusLOG\":{\"SerialLog\":2,\"WebLog\":2,\"MqttLog\":0,\"SysLog\":0,\"LogHost\":\"\",\"LogPort\":514,\"SSId\":[\"TestAP\"],\"TelePeriod\":300,\"Resolution\":\"558180C0\",\"SetOption\":[\"00008009\",\"2805C80001000600003C5A0A192800000000\",\"00000080\",\"00006000\",\"00000000\"]}}");
  }
  else if (cmdUpper == "STATUS 4") {
    // Tasmota Status 4 - Memory info
    Serial.println("{\"StatusMEM\":{\"ProgramSize\":586,\"Free\":416,\"Heap\":25,\"ProgramFlashSize\":1024,\"FlashSize\":1024,\"FlashChipId\":\"1640C8\",\"FlashFrequency\":40,\"FlashMode\":3,\"Features\":[\"00000809\",\"8FDAC787\",\"04368001\",\"000000CF\",\"010013C0\",\"C000F981\",\"00004004\",\"00001000\"],\"Drivers\":\"1,2,3,4,5,6,7,8,9,10,12,16,18,19,20,21,22,24,26,27,29,30,35,37,45\",\"Sensors\":\"1,2,3,4,5,6\"}}");
  }
  else if (cmdUpper == "STATUS 5") {
    // Tasmota Status 5 - Network info
    Serial.println("{\"StatusNET\":{\"Hostname\":\"tasmota-test\",\"IPAddress\":\"0.0.0.0\",\"Gateway\":\"0.0.0.0\",\"Subnetmask\":\"0.0.0.0\",\"DNSServer\":\"0.0.0.0\",\"Mac\":\"24:62:AB:4B:6A:6A\",\"Webserver\":2,\"WifiConfig\":4,\"WifiPower\":17.0}}");
  }
  else if (cmdUpper == "STATUS 11") {
    // Tasmota-style Status 11 (power status)
    printTasmotaStatusSTS();
  }
  else if (cmdUpper == "POWER" || cmdUpper == "POWER1") {
    // Query power state Tasmota-style
    Serial.print("POWER1 ");
    Serial.println(test_state.relay_state ? "ON" : "OFF");
  }
  else if (cmdUpper == "POWER ON" || cmdUpper == "POWER1 ON" || cmdUpper == "RELAY ON" || cmdUpper == "ON") {
    setRelay(true);
    Serial.println("POWER1 ON");
  }
  else if (cmdUpper == "POWER OFF" || cmdUpper == "POWER1 OFF" || cmdUpper == "RELAY OFF" || cmdUpper == "OFF") {
    setRelay(false);
    Serial.println("POWER1 OFF");
  }
  else if (cmdUpper == "POWER TOGGLE" || cmdUpper == "POWER1 TOGGLE") {
    setRelay(!test_state.relay_state);
    Serial.print("POWER1 ");
    Serial.println(test_state.relay_state ? "ON" : "OFF");
  }
  else if (cmdUpper == "RELAY TOGGLE" || cmdUpper == "TOGGLE") {
    setRelay(!test_state.relay_state);
    Serial.print("POWER1 ");
    Serial.println(test_state.relay_state ? "ON" : "OFF");
  }
  else if (cmdUpper == "LED ON") {
    setLED(true);
    Serial.println("OK:LED_ON");
  }
  else if (cmdUpper == "LED OFF") {
    setLED(false);
    Serial.println("OK:LED_OFF");
  }
  else if (cmdUpper == "LED TOGGLE") {
    setLED(!test_state.led_state);
    Serial.print("OK:LED_");
    Serial.println(test_state.led_state ? "ON" : "OFF");
  }
  else if (cmdUpper.startsWith("BURN ")) {
    // Parse burn-in parameters: BURN <cycles> [interval_ms]
    int space1 = cmdUpper.indexOf(' ');
    int space2 = cmdUpper.indexOf(' ', space1 + 1);
    
    if (space1 > 0) {
      unsigned long cycles = cmdUpper.substring(space1 + 1, space2 > 0 ? space2 : cmdUpper.length()).toInt();
      unsigned long interval = DEFAULT_BURN_INTERVAL;
      
      if (space2 > 0) {
        interval = cmdUpper.substring(space2 + 1).toInt();
        if (interval < MIN_BURN_INTERVAL) interval = MIN_BURN_INTERVAL;
      }
      
      burnInTest(cycles, interval);
    } else {
      Serial.println("ERROR:INVALID_BURN_PARAMS");
    }
  }
  else if (cmdUpper == "STOP") {
    test_state.burn_in_active = false;
    Serial.println("OK:TEST_STOPPED");
  }
  else if (cmdUpper == "RESET") {
    // Reset all counters
    test_state.button_press_count = 0;
    test_state.relay_toggle_count = 0;
    test_state.burn_in_cycles = 0;
    test_state.relay_on_time = 0;
    test_state.relay_off_time = 0;
    test_state.test_start_time = millis();
    Serial.println("OK:COUNTERS_RESET");
  }
  else if (cmdUpper == "RESTART" || cmdUpper == "REBOOT" || cmdUpper == "ESP.RESTART()") {
    // Software reset - restart the ESP
    Serial.println("OK:RESTARTING");
    Serial.flush();
    delay(100);
    ESP.restart();
  }
  else if (cmdUpper == "BOOTLOADER" || cmdUpper == "DOWNLOAD") {
    // Enter bootloader mode for firmware update
    Serial.println("OK:ENTERING_BOOTLOADER");
    Serial.println("Device will restart in bootloader mode...");
    Serial.println("Note: If device doesn't enter bootloader, use physical button method");
    Serial.flush();
    delay(100);
    
    // Method 1: Write magic value to RTC memory to signal bootloader on next boot
    // Some bootloaders check this
    uint32_t magic = 0x07738135;  // Magic number for bootloader
    system_rtc_mem_write(0, &magic, sizeof(magic));
    
    // Method 2: Try to manipulate GPIO0 before reset
    // Note: This usually doesn't work because GPIO0 needs to be low DURING reset
    pinMode(0, OUTPUT);
    digitalWrite(0, LOW);
    
    // Restart with special reset reason
    system_restart();
    
    // If we get here, try ESP.restart as fallback
    delay(50);
    ESP.restart();
  }
  else if (cmdUpper == "READ BUTTON") {
    Serial.print("BUTTON:");
    Serial.println(digitalRead(BUTTON_PIN) ? "RELEASED" : "PRESSED");
  }
  else if (cmdUpper == "TEST") {
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
  else if (cmdUpper == "JSON") {
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
  else if (cmdUpper == "TIMING") {
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
  else if (cmdUpper == "VERSION") {
    // Tasmota-style version response
    Serial.print("{\"StatusFWR\":{\"Version\":\"");
    Serial.print(FIRMWARE_VERSION);
    Serial.print("\",\"BuildDateTime\":\"");
    Serial.print(__DATE__ " " __TIME__);
    Serial.print("\",\"Boot\":31,\"Core\":\"2.7.4\",");
    Serial.print("\"SDK\":\"2.2.2\",\"CpuFrequency\":80,");
    Serial.print("\"Hardware\":\"ESP8266EX\",");
    Serial.print("\"CR\":\"404/699\"}}");
    Serial.println();
  }
  else if (cmdUpper == "") {
    // Empty command, just show prompt
  }
  else {
    Serial.print("ERROR:UNKNOWN_COMMAND:");
    Serial.println(cmdUpper);
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
  Serial.println("RESTART        - Restart ESP device");
  Serial.println("BOOTLOADER     - Enter bootloader mode");
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

void printTasmotaStatus() {
  // Tasmota Status 0 format - returns general device status in JSON
  Serial.print("{\"Status\":{");
  Serial.print("\"Module\":1,");  // Sonoff Basic
  Serial.print("\"DeviceName\":\"TestDevice\",");
  Serial.print("\"FriendlyName\":[\"TestRelay\"],");
  Serial.print("\"Topic\":\"test\",");
  Serial.print("\"ButtonTopic\":\"0\",");
  Serial.print("\"Power\":");
  Serial.print(test_state.relay_state ? "1" : "0");
  Serial.print(",\"PowerOnState\":0,");
  Serial.print("\"LedState\":1,");
  Serial.print("\"SaveData\":1,");
  Serial.print("\"SaveState\":1,");
  Serial.print("\"ButtonRetain\":0,");
  Serial.print("\"PowerRetain\":0");
  Serial.println("}}");
}

void printTasmotaStatus1() {
  // Tasmota Status 1 format - Device parameters
  Serial.print("{\"StatusPRM\":{");
  Serial.print("\"Baudrate\":115200,");
  Serial.print("\"SerialConfig\":\"8N1\",");
  Serial.print("\"GroupTopic\":\"tasmotas\",");
  Serial.print("\"OtaUrl\":\"\",");
  Serial.print("\"RestartReason\":\"Software/System restart\",");
  Serial.print("\"Uptime\":\"");
  Serial.print((millis() - test_state.test_start_time) / 1000);
  Serial.print("\",");
  Serial.print("\"StartupUTC\":\"\",");
  Serial.print("\"Sleep\":50,");
  Serial.print("\"CfgHolder\":4617,");
  Serial.print("\"BootCount\":10,");
  Serial.print("\"Module\":\"Sonoff Basic\",");
  Serial.print("\"DeviceName\":\"TestDevice\",");
  Serial.print("\"FriendlyName\":[\"TestRelay\"],");
  Serial.print("\"Topic\":\"test\",");
  Serial.print("\"ButtonTopic\":\"0\",");
  Serial.print("\"Power\":0,");
  Serial.print("\"PowerOnState\":3,");
  Serial.print("\"LedState\":1,");
  Serial.print("\"LedMask\":\"FFFF\",");
  Serial.print("\"SaveData\":1,");
  Serial.print("\"SaveState\":1,");
  Serial.print("\"SwitchTopic\":\"0\",");
  Serial.print("\"SwitchMode\":[0,0,0,0,0,0,0,0],");
  Serial.print("\"ButtonRetain\":0,");
  Serial.print("\"SwitchRetain\":0,");
  Serial.print("\"SensorRetain\":0,");
  Serial.print("\"PowerRetain\":0,");
  Serial.print("\"InfoRetain\":0,");
  Serial.print("\"StateRetain\":0");
  Serial.println("}}");
}

void printTasmotaStatus2() {
  // Tasmota Status 2 format - Firmware version
  Serial.print("{\"StatusFWR\":{");
  Serial.print("\"Version\":\"");
  Serial.print(FIRMWARE_VERSION);
  Serial.print("\",\"BuildDateTime\":\"");
  Serial.print(__DATE__ " " __TIME__);
  Serial.print("\",\"Boot\":31,");
  Serial.print("\"BootCount\":10,");
  Serial.print("\"Core\":\"2.7.4\",");
  Serial.print("\"SDK\":\"2.2.2\",");
  Serial.print("\"CpuFrequency\":80,");
  Serial.print("\"Hardware\":\"ESP8266EX\",");
  Serial.print("\"CR\":\"404/699\"");
  Serial.println("}}");
}

void printTasmotaStatusSTS() {
  // Tasmota Status 11 format - returns power status in JSON
  Serial.print("{\"StatusSTS\":{");
  Serial.print("\"Time\":\"2024-01-01T00:00:00\",");
  Serial.print("\"Uptime\":\"");
  Serial.print((millis() - test_state.test_start_time) / 1000);
  Serial.print("\",");
  Serial.print("\"UptimeSec\":");
  Serial.print((millis() - test_state.test_start_time) / 1000);
  Serial.print(",\"Heap\":20,");
  Serial.print("\"SleepMode\":\"Dynamic\",");
  Serial.print("\"Sleep\":50,");
  Serial.print("\"LoadAvg\":19,");
  Serial.print("\"MqttCount\":0,");
  Serial.print("\"POWER\":\"");
  Serial.print(test_state.relay_state ? "ON" : "OFF");
  Serial.print("\",\"POWER1\":\"");
  Serial.print(test_state.relay_state ? "ON" : "OFF");
  Serial.print("\",\"Wifi\":{\"AP\":1,\"SSId\":\"TestAP\",");
  Serial.print("\"BSSId\":\"00:00:00:00:00:00\",");
  Serial.print("\"Channel\":1,\"RSSI\":100,\"Signal\":-50,");
  Serial.print("\"LinkCount\":1,\"Downtime\":\"0T00:00:00\"}");
  Serial.println("}}");
}