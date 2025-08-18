# Minimal Test Firmware Relay Testing Example

This example demonstrates how to test Sonoff relays running the custom minimal test firmware using the Onnyx test framework. The tests communicate with the minimal firmware over a serial connection.

## Features

- Auto-detection of test firmware devices on available serial ports
- Prioritizes FTDI USB-to-Serial adapters (VID 0403, PID 6001)
- Firmware version and status checking
- Relay control testing (ON/OFF cycles)
- Burn-in testing with configurable cycles and intervals
- JSON-based status reporting
- Relay response profile measurement using Rigol oscilloscope
- Waveform capture and analysis for rise/fall times and contact bounce
- Microsecond-precision timing measurements
- Button testing functionality

## Requirements

- Python 3.7+
- Sonoff relay with custom minimal test firmware
- FTDI USB-to-Serial adapter (VID 0403, PID 6001)
- Serial connection to the device
- (Optional) Rigol DS1054 oscilloscope with Ethernet connection for response profile testing

## Installation

1. Create a virtual environment:
   ```
   python -m venv .venv
   ```

2. Activate the virtual environment:
   - Windows: `.venv\Scripts\activate`
   - Linux/Mac: `source .venv/bin/activate`

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Configuration

The test can be configured through the `_cell_config_obj` in the test document:

```python
{
    "serial_port": None,  # Auto-detect FTDI devices or specify (e.g., "COM3" on Windows, "/dev/ttyUSB0" on Linux)
    "baudrate": 115200,   # Serial baudrate (fixed for minimal firmware)
    "test_cycles": 5,     # Number of ON/OFF cycles to test
    "delay_between_cycles": 1.0,  # Delay between cycles in seconds
    "burn_in_cycles": 100,        # Number of burn-in cycles
    "burn_in_interval": 500,      # Burn-in interval in milliseconds
    "enable_button_test": True,   # Enable button testing
    "button_test_duration": 10,   # Button test duration in seconds

    # Oscilloscope configuration (optional)
    "oscilloscope_ip": "192.168.1.100",  # IP address of the Rigol oscilloscope
    "oscilloscope_port": 5555,           # SCPI port (default: 5555)
    "oscilloscope_timebase": 0.001,      # Timebase in seconds/div (default: 1ms/div)
    "enable_oscilloscope_test": True,    # Set to True to enable oscilloscope test
    "waveform_output_dir": "waveforms",  # Directory to save waveform data
    "enable_timing_test": True,          # Enable microsecond timing measurements
}
```

## Minimal Test Firmware Commands

The minimal test firmware supports the following commands:

- `ON` / `OFF` / `TOGGLE` - Relay control
- `STATUS` - Get human-readable status
- `JSON` - Get machine-readable JSON status
- `TEST` - Run self-test sequence
- `TIMING` - Microsecond-precision relay timing test
- `BURN <cycles> <interval>` - Automated burn-in test
- `READ BUTTON` - Read button state
- `RESET` - Reset all counters
- `VERSION` - Get firmware version and build info
- `HELP` - Show available commands

## Running the Tests

To run the tests:

```
python example_flow.py
```

## Test Flow

1. **Device Detection**: Detects and connects to the minimal test firmware device on the specified or auto-detected serial port, prioritizing FTDI USB-to-Serial adapters.
2. **Firmware Check**: Verifies that the device is running the minimal test firmware and gets version information.
3. **Basic Relay Test**: Tests basic relay functionality with ON/OFF cycles.
4. **Burn-in Test**: Performs automated burn-in testing with configurable cycles and intervals.
5. **Button Test** (if enabled): Tests button functionality by monitoring button presses.
6. **Timing Test** (if enabled): Performs microsecond-precision relay timing measurements.
7. **Relay Response Profile** (if enabled): Measures the relay's response profile using a Rigol oscilloscope.

## Minimal Firmware Driver

The `MinimalFirmwareDriver` class provides a comprehensive interface for communicating with the minimal test firmware:

- Connection management with auto-detection
- Command sending and response parsing
- Relay control (ON/OFF/TOGGLE)
- Status and version queries in both human and JSON formats
- Burn-in test execution with progress monitoring
- Button state monitoring
- Timing measurements
- Counter management (relay toggles, button presses, uptime)

### JSON Status Format

The minimal firmware provides JSON status in this format:

```json
{
    "relay": true,
    "led": true,
    "button": false,
    "button_count": 5,
    "relay_count": 10,
    "uptime": 12345,
    "relay_on_ms": 5000,
    "relay_off_ms": 7345
}
```

### Burn-in Testing

The firmware supports automated burn-in testing:

```python
# Start burn-in test with 1000 cycles at 500ms intervals
driver.start_burn_in(1000, 500)

# Monitor progress
while driver.is_burn_in_active():
    progress = driver.get_burn_in_progress()
    print(f"Burn-in progress: {progress['current']}/{progress['total']}")
    time.sleep(1)
```

## Troubleshooting

### Common Issues

- **No FTDI devices found**:
  - Ensure you're using an FTDI USB-to-Serial adapter with VID 0403 and PID 6001
  - Check that the adapter is properly connected to your computer
  - Try a different USB port

- **No response from firmware**:
  - Verify that the device is running the minimal test firmware (not Tasmota)
  - Check that the correct port is specified
  - Ensure the baudrate is 115200 (fixed for minimal firmware)
  - Verify the device is powered on

- **Firmware not recognized**:
  - Check that the device is running the correct minimal test firmware
  - Try sending the VERSION command manually to verify firmware
  - Ensure the firmware was flashed correctly

- **Relay control failed**:
  - Check that the relay hardware is connected properly
  - Verify the device responds to STATUS commands
  - Try manual relay control with individual commands

- **Button test failed**:
  - Ensure the button is properly connected to GPIO0
  - Check that the button is not stuck or damaged
  - Verify button pulls pin low when pressed

### Debugging Tips

1. **Check the logs**: The test produces detailed logs that can help identify issues
2. **Try manual commands**: Use a serial terminal to send commands manually
3. **Verify hardware**: Check physical connections and power supply
4. **Monitor heartbeat**: The firmware sends "Alive" messages every second
5. **Check JSON responses**: Use the JSON command to get detailed status

## Code Structure

The code is organized into separate modules:

- `minimal_firmware_driver.py`: Contains the `MinimalFirmwareDriver` class
- `minimal_firmware_tests.py`: Contains the test functions
- `example_flow.py`: Orchestrates the test flow
- `file_utils.py`: File and directory utilities
- `failure_codes.py`: Error code definitions

## Oscilloscope Integration

Like example_2, this test can integrate with a Rigol DS1054 oscilloscope to measure relay response characteristics. The oscilloscope functionality is shared between examples and provides:

- Rise/fall time measurements
- Contact bounce analysis
- Waveform capture and storage
- Transition time analysis

## Advantages of Minimal Firmware

Compared to Tasmota firmware, the minimal test firmware offers:

- **Smaller size**: 253KB vs 668KB (62% smaller)
- **Faster boot**: Minimal initialization overhead
- **Deterministic responses**: Consistent command processing
- **Manufacturing focus**: Designed specifically for testing
- **JSON output**: Machine-readable status for automation
- **Built-in burn-in**: Automated cycling without external control
- **Timing precision**: Microsecond-accurate measurements
- **Real-time monitoring**: Live status updates during testing

This makes it ideal for production line testing where speed, reliability, and automation are critical.