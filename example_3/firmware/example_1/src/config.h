#ifndef CONFIG_H
#define CONFIG_H

// Pin definitions for Sonoff Basic
#define RELAY_PIN 12
#define LED_PIN 13
#define BUTTON_PIN 0

// Serial configuration
#define SERIAL_BAUD 115200

// Test configuration
#define FIRMWARE_VERSION "1.0.0"
#define DEFAULT_BURN_INTERVAL 1000
#define MIN_BURN_INTERVAL 100
#define BUTTON_DEBOUNCE_MS 50

#endif // CONFIG_H