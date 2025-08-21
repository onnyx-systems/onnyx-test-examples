# ESP8266 Relay Module Test Example

This example demonstrates how to test ESP8266 relay modules using the Onnyx test framework. The tests communicate with the relay module over a serial connection.

## Features

- Auto-detection of relay modules on available serial ports
- Prioritizes FTDI USB-to-Serial adapters (VID 0403, PID 6001)
- Firmware version checking
- Relay control testing (ON/OFF cycles)
- Comprehensive error handling and reporting
- Relay response profile measurement using Rigol oscilloscope
- Waveform capture and analysis for rise/fall times and contact bounce

## Requirements

- Python 3.7+
- ESP8266 relay module with compatible firmware
- FTDI USB-to-Serial adapter (VID 0403, PID 6001)
- Serial connection to the relay module
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
    "baudrate": 115200,   # Serial baudrate
    "min_firmware_version": "9.5.0",  # Minimum required firmware version (optional)

    # Oscilloscope configuration (optional)
    "oscilloscope_ip": "192.168.1.100",  # IP address of the Rigol oscilloscope
    "oscilloscope_port": 5555,           # SCPI port (default: 5555)
    "oscilloscope_timebase": 0.001,      # Timebase in seconds/div (default: 1ms/div)
    "enable_oscilloscope_test": True,    # Set to True to enable oscilloscope test
    "waveform_output_dir": "waveforms",  # Directory to save waveform data
}
```

### Firmware Version Format

The test supports various firmware version formats:

- Standard numeric versions (e.g., "9.5.0")
- Versions with suffixes (e.g., "14.5.0(relay-compat)")

When comparing versions, only the numeric parts are considered. For example, "14.5.0(relay-compat)" is treated as "14.5.0" for comparison purposes.

### Relay Configuration

The test is designed to work with relay modules that have relays. It always tests relay 1 (the primary relay). For devices with a single relay, the relay is typically referred to as "POWER" in the firmware, while multi-relay devices refer to relays as "POWER1", "POWER2", etc.

## Running the Tests

To run the tests:

```
python example_flow.py
```

## Test Flow

1. **Device Detection**: Detects and connects to the relay module on the specified or auto-detected serial port, prioritizing FTDI USB-to-Serial adapters.
2. **Firmware Check**: Verifies that the device is running a compatible firmware version (if `min_firmware_version` is specified).
3. **Relay Control Test**: Tests relay 1 by performing ON/OFF cycles and verifying the state changes.
4. **Relay Response Profile** (if enabled): Measures the relay's response profile using a Rigol oscilloscope, capturing waveforms for both rising and falling edges.

## Relay Driver

The `RelaySerialDriver` class provides a comprehensive interface for communicating with relay modules over serial:

- Connection management
- Command sending and response parsing
- Relay control (ON/OFF/TOGGLE)
- Status and firmware version queries

### Relay State Detection

The driver uses multiple methods to detect the relay state:

1. Pattern matching on status responses
2. JSON parsing of structured responses
3. Fallback to simple text parsing

This multi-layered approach helps ensure compatibility with different firmware versions and response formats.

### Handling "SAME" State Response

When setting a relay to a state it's already in, the firmware may respond with "SAME" instead of confirming the new state. The driver handles this case by:

1. Accepting "SAME" as a valid response
2. Using the requested state as the current state
3. Logging the operation for debugging

## Troubleshooting

### Common Issues

1. **Device not detected**: 
   - Ensure the USB-to-Serial adapter is properly connected.
   - Check that the device has power (LED should be on).
   - Verify the correct serial port is being used.
   - Ensure you're using an FTDI USB-to-Serial adapter with VID 0403 and PID 6001. These are commonly used with relay modules.

2. **Firmware version mismatch**: 
   - The test may require a minimum firmware version. Check the device's firmware version and update if necessary.

3. **Serial communication errors**: 
   - Check the baudrate (usually 115200).
   - Ensure the serial cable is properly connected.
   - Try resetting the device.

4. **Relay not responding**: 
   - Check that the relay is powered and connected properly.
   - Verify the device configuration (relay GPIO assignment).

### Debug Mode

Enable debug mode by setting the log level to DEBUG to see detailed communication logs:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Advanced Troubleshooting

1. **Check serial permissions** (Linux/Mac): Ensure your user has permission to access the serial port. You may need to add your user to the `dialout` group.

2. **Verify device firmware**: 
   - Check that the device is running compatible firmware.
   - Update to the latest compatible firmware if needed.

3. **Verify with web interface**: If possible, access the device's web interface to verify it is working correctly.

4. **Try different commands**: You can modify the code to try different commands if the default ones aren't working.

5. **Check response formats**: Different firmware versions may have slightly different response formats. The logs will show the actual responses received.

6. **Reset the device**: If all else fails, try resetting the device to factory defaults and reconfiguring it.

## Response Format Variations

Relay modules can respond in different formats depending on the firmware version and configuration. The driver tries to handle these variations, but you may need to add additional patterns if your device uses a different format.

Common response patterns:
- `POWER ON`
- `POWER1 ON`
- `{"POWER":"ON"}`
- `{"StatusSTS":{"POWER":"ON"}}`

If your device uses a different format, you may need to modify the `get_power_state` method in the `RelaySerialDriver` class.

## Project Structure

```
tests/
├── __init__.py
├── failure_codes.py    # Custom failure codes for relay tests
├── file_utils.py       # Utilities for file handling and CSV export
├── relay_driver.py     # Contains the `RelaySerialDriver` class for communicating with relay modules
├── relay_tests.py      # Contains the test functions that use the driver
├── rigol_driver.py     # Driver for Rigol oscilloscopes
└── scope.py           # Oscilloscope-related test functions
```

## Key Design Decisions

1. **FTDI Auto-Detection**: The test prioritizes FTDI USB-to-Serial adapters (VID 0403, PID 6001) because they are commonly used and reliable for serial communication with relay modules.

2. **Robust Pattern Matching**: The driver uses comprehensive pattern matching to handle various firmware response formats:
   - JSON responses
   - Simple text responses
   - Status messages

3. **Failure Code System**: Custom failure codes are used to provide detailed error reporting and help with debugging.

4. **Oscilloscope Integration**: When available, the test can measure electrical characteristics of the relay switching to verify proper operation and timing.