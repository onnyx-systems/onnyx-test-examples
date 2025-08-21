# ESP8266 Relay Test Firmware

Modular test firmware for ESP8266 relay module with manufacturing test CLI.

## Project Structure

```
src/
├── main.cpp          # Main application loop and setup
├── config.h          # Pin definitions and configuration constants
├── test_state.h      # Global test state structure
├── hardware.h        # Hardware control interface
├── hardware.cpp      # Hardware control implementation
├── commands.h        # Command processing interface
└── commands.cpp      # Command processing implementation
```

## Architecture

- **config.h**: Centralized configuration and pin definitions
- **test_state.h**: Global state management with TestState structure
- **hardware.cpp**: Low-level hardware control (relay, LED, button)
- **commands.cpp**: CLI command processing and parsing
- **main.cpp**: Application entry point and main loop

## Features

- Modular design with clear separation of concerns
- Header guards to prevent multiple inclusions
- Centralized configuration management
- Clean API interfaces between modules
- Manufacturing test commands (BURN, TEST, JSON, etc.)

## Build

```bash
platformio run
```

## Flash

```bash
platformio run --target upload
```