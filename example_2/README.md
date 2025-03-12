# Tasmota Relay Test Example

This example demonstrates how to test Sonoff relays running Tasmota firmware using the Onnyx test framework. The tests communicate with the Tasmota device over a serial connection.

## Features

- Auto-detection of Tasmota devices on available serial ports
- Prioritizes FTDI USB-to-Serial adapters (VID 0403, PID 6001)
- Firmware version checking
- Relay control testing (ON/OFF cycles)
- Comprehensive error handling and reporting
- Relay response profile measurement using Rigol oscilloscope
- Waveform capture and analysis for rise/fall times and contact bounce

## Requirements

- Python 3.7+
- Sonoff relay with Tasmota firmware
- FTDI USB-to-Serial adapter (VID 0403, PID 6001)
- Serial connection to the Tasmota device
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
    "relay_number": 1,    # Relay number to test (1-8)
    "test_cycles": 3,     # Number of ON/OFF cycles to test
    "delay_between_cycles": 1.0,  # Delay between cycles in seconds
    "min_firmware_version": "9.5.0",  # Minimum required Tasmota version (optional)

    # Oscilloscope configuration (optional)
    "oscilloscope_ip": "192.168.1.100",  # IP address of the Rigol oscilloscope
    "oscilloscope_port": 5555,           # SCPI port (default: 5555)
    "oscilloscope_timebase": 0.001,      # Timebase in seconds/div (default: 1ms/div)
    "enable_oscilloscope_test": True,    # Set to True to enable oscilloscope test
    "waveform_output_dir": "waveforms",  # Directory to save waveform data
}
```

### Firmware Version Format

The test supports various Tasmota firmware version formats:

- Standard numeric versions (e.g., "9.5.0")
- Versions with suffixes (e.g., "14.5.0(release-tasmota)")

When comparing versions, only the numeric parts are considered. For example, "14.5.0(release-tasmota)" is treated as "14.5.0" for comparison purposes.

### Relay Configuration

The test is designed to work with Tasmota devices that have one or more relays. For devices with a single relay, the relay is typically referred to as "POWER" in the Tasmota firmware. For devices with multiple relays, they are referred to as "POWER1", "POWER2", etc.

The `relay_number` parameter in the configuration specifies which relay to test:

- For a single-relay device, use `relay_number: 1`
- For multi-relay devices, use the appropriate relay number (1-8)

If you're testing a single-relay device but experiencing issues, make sure `relay_number` is set to 1, as this is the default for most Tasmota devices.

## Running the Tests

To run the tests:

```
python example_flow.py
```

## Test Flow

1. **Device Detection**: Detects and connects to the Tasmota device on the specified or auto-detected serial port, prioritizing FTDI USB-to-Serial adapters.
2. **Firmware Check**: Verifies that the device is running a compatible firmware version (if `min_firmware_version` is specified).
3. **Relay Control Test**: Tests the relay by performing multiple ON/OFF cycles and verifying the state changes.
4. **Relay Response Profile** (if enabled): Measures the relay's response profile using a Rigol oscilloscope, capturing waveforms for both rising and falling edges.

## Tasmota Driver

The `TasmotaSerialDriver` class provides a comprehensive interface for communicating with Tasmota devices over serial:

- Connection management
- Command sending and response parsing
- Relay control (ON/OFF/TOGGLE)
- Status and firmware version queries

### Relay State Detection

The driver uses multiple methods to detect the relay state:

1. First tries using the Status 11 command which returns all power states
2. Then tries direct Power query with multiple pattern matching
3. Finally falls back to the device status

This multi-layered approach helps ensure compatibility with different Tasmota firmware versions and response formats.

### Relay State Handling

The test is designed to cycle the relay through ON and OFF states. If the relay is already in the ON state when the test starts, the test will first turn it OFF before starting the test cycles. This ensures that we can properly test both the ON and OFF transitions.

When setting a relay to a state it's already in, Tasmota may respond with "SAME" instead of confirming the new state. The driver handles this case by:

1. First checking if the relay is already in the requested state
2. Looking for various success patterns in the response, including "SAME"
3. Verifying the actual state after sending the command

This approach ensures that the test works correctly regardless of the initial state of the relay.

## Troubleshooting

### Common Issues

- **No FTDI devices found**:

  - Ensure you're using an FTDI USB-to-Serial adapter with VID 0403 and PID 6001. These are commonly used with Tasmota devices.
  - Check that the adapter is properly connected to your computer.
  - Try a different USB port.

- **No serial ports found**:

  - Ensure the USB-to-Serial adapter is connected and recognized by the system.
  - Check if you need to install drivers for your adapter.

- **Connection failed**:

  - Verify that the device is powered on.
  - Check that the correct port is specified.
  - Ensure the baudrate matches the device configuration (default is 115200).

- **Invalid response**:

  - Check that the device is running Tasmota firmware.
  - Verify the baudrate is correct.
  - Try increasing the timeout values if the device is slow to respond.

- **Failed to get initial state of relay**:

  - This can happen if:
    - The relay number specified doesn't exist on your device
    - The device uses a different naming convention for relays
    - The device is not responding to power state queries
  - For single-relay devices, make sure `relay_number` is set to 1
  - Check the device's web interface to confirm the relay exists and is operational
  - Try increasing the timeout and retry values in the code

- **Relay control failed**:

  - Ensure the relay number is correct.
  - Verify the device supports the specified relay.
  - Check if the relay can be controlled manually through the device's web interface.
  - Try increasing the delay between commands.

- **Relay state mismatch**:

  - The test expects the relay to change state immediately after sending a command.
  - If your device has a delay, try increasing the `delay_between_cycles` parameter.
  - Some devices may have different response formats; check the logs for details.

- **Firmware version check failed**:
  - The test may continue even if the firmware version check fails.
  - Check the logs for details about the version comparison.
  - Update your device to a newer firmware if needed.

### Debugging Tips

1. **Check the logs**: The test produces detailed logs that can help identify issues. Look for warning and error messages.

2. **Increase delays**: If the device is slow to respond, try increasing the `delay_between_cycles` parameter.

3. **Verify with web interface**: If possible, access the Tasmota web interface to verify the device is working correctly.

4. **Try different commands**: You can modify the code to try different Tasmota commands if the default ones aren't working.

5. **Check response formats**: Different Tasmota versions may have slightly different response formats. The logs will show the actual responses received.

6. **Reset the device**: If all else fails, try resetting the Tasmota device to factory defaults and reconfiguring it.

### Response Format Variations

Tasmota devices can respond in different formats depending on the firmware version and configuration. The driver tries to handle these variations, but you may need to add additional patterns if your device uses a different format.

Common response formats for power state:

- `POWER ON` / `POWER OFF` (single relay)
- `POWER1 ON` / `POWER1 OFF` (multi-relay)
- `{"POWER":"ON"}` / `{"POWER":"OFF"}` (JSON format, single relay)
- `{"POWER1":"ON"}` / `{"POWER1":"OFF"}` (JSON format, multi-relay)

If your device uses a different format, you may need to modify the `get_power_state` method in the `TasmotaSerialDriver` class.

## Code Structure and Design

The code has been designed with simplicity, robustness, and maintainability in mind:

1. **Modular Design**: The code is organized into separate modules:

   - `tasmota_driver.py`: Contains the `TasmotaSerialDriver` class for communicating with Tasmota devices
   - `tasmota_tests.py`: Contains the test functions that use the driver
   - `example_flow.py`: Orchestrates the test flow
   - `utils.py`: Contains utility functions used across the codebase

2. **Robust Pattern Matching**: The driver uses comprehensive pattern matching to handle various Tasmota response formats:

   - Supports both JSON parsing and raw response pattern matching
   - Handles both single-relay and multi-relay devices
   - Recognizes various response formats (e.g., "POWER ON", "POWER=ON", "POWER: ON")

3. **Helper Functions**: The test code uses helper functions to reduce redundancy:

   - `set_relay_state`: Handles setting relay states with retries
   - `verify_relay_state`: Verifies relay states with retries and increasing delays
   - `extract_version_numbers`: Extracts numeric parts from version strings
   - `compare_versions`: Compares version strings to check compatibility

4. **Multi-layered Approach**: The driver uses multiple methods to determine and set relay states:

   - First tries using Status 11 command (most reliable)
   - Then tries direct Power query
   - Finally falls back to Status 0 command
   - Verifies states directly when command responses are ambiguous

5. **Comprehensive Error Handling**: The code includes detailed error handling:

   - Retries operations with increasing delays
   - Provides detailed error messages and logging
   - Gracefully handles various failure scenarios

6. **DRY Principle**: The code follows the "Don't Repeat Yourself" principle:
   - Common functionality is extracted into utility functions
   - Version handling logic is centralized in the utils module
   - Pattern matching is consolidated using lists of patterns

## Oscilloscope Integration

The test can integrate with a Rigol DS1054 oscilloscope to measure the relay's response profile, including rise/fall times and contact bounce. This provides valuable insights into the relay's performance characteristics.

### Hardware Setup

1. Connect the oscilloscope to your network via Ethernet.
2. Connect Channel 1 of the oscilloscope to one side of the relay.
3. Connect a 5V power source to the other side of the relay.
4. Use a pull-down resistor (e.g., 10kΩ) to ensure a clean signal.

### Waveform Analysis

The test captures and analyzes waveforms for both rising (OFF→ON) and falling (ON→OFF) transitions, measuring:

- **Transition Time**: The time it takes for the relay to switch states (10% to 90% of the transition).
- **Bounce Count**: The number of times the relay contacts bounce during the transition.
- **Bounce Duration**: The total duration of contact bounce.

### Waveform Data

Waveform data is saved as CSV files in the specified output directory (default: `waveforms/`). Each file contains time and voltage data that can be further analyzed or plotted using external tools.

Example CSV format:

```
Time (s),Voltage (V)
0.000000,0.012345
0.000001,0.012346
...
```

### Waveform Visualization

A utility script `plot_waveforms.py` is provided to visualize the captured waveforms. This script can plot individual waveforms or all waveforms in a directory.

Usage:

```
# Plot a single waveform
python plot_waveforms.py waveforms/relay_rising_20230101_120000.csv

# Plot all waveforms in a directory
python plot_waveforms.py --dir waveforms
```

The script generates PNG images with annotations showing:

- Transition time (10% to 90% of the transition)
- Bounce count
- Bounce duration
- Highlighted bounce regions

For directories containing both rising and falling edge waveforms, it also generates a combined plot showing both transitions for easy comparison.

### Interpreting Results

- **Rise Time**: Typically in the range of 1-10ms for mechanical relays. Faster rise times indicate better performance.
- **Fall Time**: Usually similar to rise time, but can be different depending on the relay design.
- **Bounce Count**: Lower is better. High-quality relays may have minimal or no bounce.
- **Bounce Duration**: Shorter is better. Excessive bounce can cause issues in sensitive circuits.

## Oscilloscope Functionality

This example includes functionality to capture and analyze relay transition waveforms using a Rigol oscilloscope. The oscilloscope is used to measure the transition time and contact bounce of the relay when it switches between ON and OFF states.

### Waveform Analysis

The example includes a utility module `waveform_utils.py` that provides functions for analyzing relay transition waveforms. This module is used by both the `rigol_driver.py` and `analyze_waveforms.py` scripts to:

- Detect transition types (rising or falling)
- Calculate transition times
- Identify contact bounce
- Analyze waveform characteristics

The shared utility module eliminates code redundancy and ensures consistent analysis results across different parts of the application.

### Waveform Data Analysis

A utility script (`analyze_waveforms.py`) is included to analyze the captured waveforms and save the results to CSV files. This script can:

- Analyze individual waveforms
- Process all waveforms in a directory
- Generate detailed CSV reports with transition metrics
- Create summary reports for multiple waveforms

To use the analysis utility:

```bash
# Analyze a single waveform
python analyze_waveforms.py path/to/waveform.csv

# Analyze all waveforms in a directory
python analyze_waveforms.py --dir path/to/waveform/directory

# Specify a custom output directory
python analyze_waveforms.py --dir path/to/waveform/directory --output path/to/output
```

The analysis results are saved as CSV files that include:

- Transition type (rising or falling)
- Transition time in milliseconds
- Bounce count
- Bounce duration in milliseconds
- Start and end voltages
- Detailed bounce region information

All CSV files use static filenames (without timestamps) to ensure compatibility with the Onnyx platform, which expects consistent file naming across test runs. The following files are generated:

- `relay_rising.csv` - Raw waveform data for rising edge transition
- `relay_falling.csv` - Raw waveform data for falling edge transition
- `relay_response_summary.csv` - Summary of both rising and falling edge analyses
- `relay_response_detailed.csv` - Detailed parameters for both transitions
- `waveform_analysis_summary.csv` - Summary when analyzing multiple waveforms

These CSV files are automatically uploaded to the Onnyx platform for further analysis and reporting.
