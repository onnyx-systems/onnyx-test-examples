#ifndef CONFIG_H
#define CONFIG_H

/*
 * ESP8266 GPIO Pin Mapping for Arduino/PlatformIO
 * ================================================
 * 
 * Arduino Pin Number -> ESP8266 GPIO -> NodeMCU Label -> Function/Notes
 * ----------------------------------------------------------------------
 * 0                  -> GPIO0         -> D3           -> FLASH/BOOT (pulled up)
 * 1                  -> GPIO1         -> TX           -> UART TX
 * 2                  -> GPIO2         -> D4           -> Built-in LED (pulled up)
 * 3                  -> GPIO3         -> RX           -> UART RX
 * 4                  -> GPIO4         -> D2           -> I2C SDA
 * 5                  -> GPIO5         -> D1           -> I2C SCL
 * 6                  -> GPIO6         -> -            -> Flash SPI CLK (unusable)
 * 7                  -> GPIO7         -> -            -> Flash SPI MISO (unusable)
 * 8                  -> GPIO8         -> -            -> Flash SPI MOSI (unusable)
 * 9                  -> GPIO9         -> SD2          -> Flash SPI HD (unusable)
 * 10                 -> GPIO10        -> SD3          -> Flash SPI WP (unusable)
 * 11                 -> GPIO11        -> -            -> Flash SPI CS (unusable)
 * 12                 -> GPIO12        -> D6           -> MISO/HSPI MISO
 * 13                 -> GPIO13        -> D7           -> MOSI/HSPI MOSI/CTS
 * 14                 -> GPIO14        -> D5           -> HSPI CLK
 * 15                 -> GPIO15        -> D8           -> HSPI CS (pulled down)
 * 16                 -> GPIO16        -> D0           -> Deep sleep wakeup
 * 
 * ESP8266 Relay Module Pin Usage
 * ================================
 * GPIO0  (0)  -> Button (inverted, pressed = LOW)
 * GPIO12 (12) -> Relay control (HIGH = ON)
 * GPIO13 (13) -> Green LED (inverted, LOW = ON)
 * GPIO1  (TX) -> Serial TX for debug output
 * GPIO3  (RX) -> Serial RX for commands
 * 
 * Important Notes:
 * - GPIO6-11 are connected to flash memory and CANNOT be used
 * - GPIO0 must be HIGH during boot for normal operation (LOW enters flash mode)
 * - GPIO2 must be HIGH during boot (has internal pull-up)
 * - GPIO15 must be LOW during boot (has internal pull-down)
 * - In Arduino/PlatformIO code, use the Arduino pin number (left column)
 */

// Pin definitions for ESP8266 Relay Module
#define RELAY_PIN 12    // GPIO12 - Controls the relay
#define LED_PIN 13      // GPIO13 - Green status LED (inverted logic)
#define BUTTON_PIN 0    // GPIO0  - User button (inverted logic)

// Serial configuration
#define SERIAL_BAUD 115200

// Test configuration
#define FIRMWARE_VERSION "14.5.0(relay-compat)"
#define DEFAULT_BURN_INTERVAL 1000
#define MIN_BURN_INTERVAL 100
#define BUTTON_DEBOUNCE_MS 50

#endif // CONFIG_H