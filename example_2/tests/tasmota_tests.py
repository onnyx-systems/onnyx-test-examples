import time
import logging
from typing import Dict, Any, Optional, List, Union
import platform
import serial.tools.list_ports
from onnyx.failure import FailureCode, BaseFailureCodes
from onnyx.results import TestResult
from onnyx.decorators import test
from onnyx.context import gcc
from onnyx.mqtt import BannerState
import datetime
import os

# Try different import approaches to handle both package and direct imports
try:
    # Try relative imports first (when running as a package)
    from .tasmota_driver import TasmotaSerialDriver
    from .utils import extract_version_numbers, compare_versions
    from .rigol_driver import RigolOscilloscopeDriver
except ImportError:
    try:
        # Try absolute imports (when running directly)
        from tests.tasmota_driver import TasmotaSerialDriver
        from tests.utils import extract_version_numbers, compare_versions
        from tests.rigol_driver import RigolOscilloscopeDriver
    except ImportError:
        # Last resort: try importing from the current directory
        import sys
        import os.path

        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from tasmota_driver import TasmotaSerialDriver
        from utils import extract_version_numbers, compare_versions
        from rigol_driver import RigolOscilloscopeDriver


class FailureCodes(FailureCode):
    # Include base failure codes
    NO_FAILURE = BaseFailureCodes.NO_FAILURE
    EXCEPTION = BaseFailureCodes.EXCEPTION

    # Add specific failure codes for Tasmota relay tests
    SERIAL_PORT_NOT_FOUND = (-1, "Serial port not found")
    CONNECTION_FAILED = (-2, "Failed to connect to Tasmota device")
    RELAY_CONTROL_FAILED = (-3, "Failed to control relay")
    INVALID_RESPONSE = (-4, "Invalid response from Tasmota device")
    FIRMWARE_VERSION_MISMATCH = (-5, "Firmware version mismatch")
    RELAY_STATE_MISMATCH = (-6, "Relay state does not match expected state")
    COMMAND_TIMEOUT = (-7, "Command timed out")
    FTDI_DEVICE_NOT_FOUND = (-8, "FTDI USB-to-Serial device not found")
    OSCILLOSCOPE_CONNECTION_FAILED = (-9, "Failed to connect to oscilloscope")
    WAVEFORM_CAPTURE_FAILED = (-10, "Failed to capture waveform")


@test()
def detect_tasmota_serial_port(
    category: str = None,
    test_name: str = None,
    port: str = None,
    baudrate: int = 115200,
) -> TestResult:
    """Detect and connect to a Tasmota device on a serial port.

    If port is not specified, attempts to auto-detect the port, prioritizing
    FTDI USB-to-Serial devices with VID 0403 and PID 6001.

    Args:
        category (str, optional): Test category. Used internally by the test framework.
        test_name (str, optional): Test name. Used internally by the test framework.
        port (str, optional): Serial port to use. If None, auto-detection is attempted.
        baudrate (int, optional): Baud rate for serial communication. Defaults to 115200.

    Returns:
        TestResult: Test result with possible outcomes:
            - Success (NO_FAILURE):
                "Connected to Tasmota device on {port}"
                return_value: {
                    "port": Serial port name,
                    "baudrate": Baud rate used,
                    "firmware_version": Tasmota firmware version,
                    "device_info": Device information
                }

            - Failure (SERIAL_PORT_NOT_FOUND):
                "No serial ports found" or "Specified port {port} not found"
                return_value: {
                    "available_ports": List of available ports
                }

            - Failure (FTDI_DEVICE_NOT_FOUND):
                "No FTDI USB-to-Serial devices found"
                return_value: {
                    "available_ports": List of available ports
                }

            - Failure (CONNECTION_FAILED):
                "Failed to connect to Tasmota device on {port}"
                return_value: {
                    "port": Port that failed,
                    "error": Error message
                }
    """
    context = gcc()
    context.set_banner("Detecting Tasmota device...", "info", BannerState.SHOWING)

    # Get list of all available serial ports
    all_ports = list(serial.tools.list_ports.comports())
    available_ports = [p.device for p in all_ports]

    if not available_ports:
        context.set_banner("No serial ports found", "error", BannerState.SHOWING)
        return TestResult(
            "No serial ports found",
            FailureCodes.SERIAL_PORT_NOT_FOUND,
            return_value={"available_ports": []},
        )

    # If port is specified, check if it exists
    if port and port not in available_ports:
        context.set_banner(f"Port {port} not found", "error", BannerState.SHOWING)
        return TestResult(
            f"Specified port {port} not found",
            FailureCodes.SERIAL_PORT_NOT_FOUND,
            return_value={"available_ports": available_ports},
        )

    # If port is not specified, prioritize FTDI devices with VID 0403 and PID 6001
    if not port:
        # Find FTDI devices
        ftdi_ports = []
        for p in all_ports:
            # Log detailed port information for debugging
            context.logger.info(
                f"Port: {p.device}, Description: {p.description}, Hardware ID: {p.hwid}"
            )

            # Check for FTDI devices with VID 0403 and PID 6001
            if "VID:PID=0403:6001" in p.hwid or "VID_0403&PID_6001" in p.hwid:
                ftdi_ports.append(p.device)
                context.logger.info(f"Found FTDI device at {p.device}")

        if ftdi_ports:
            context.logger.info(f"Found {len(ftdi_ports)} FTDI devices: {ftdi_ports}")
            ports_to_try = ftdi_ports
        else:
            context.logger.warning(
                "No FTDI devices found, will try all available ports"
            )
            ports_to_try = available_ports
    else:
        ports_to_try = [port]

    # Try connecting to each port in order
    for test_port in ports_to_try:
        context.set_banner(f"Trying port {test_port}...", "info", BannerState.SHOWING)

        try:
            # Create driver and attempt connection
            driver = TasmotaSerialDriver(test_port, baudrate)
            if driver.connect():
                # Get device information
                status = driver.get_status()
                firmware_version = driver.get_firmware_version()

                # Disconnect when done
                driver.disconnect()

                context.set_banner(
                    f"Connected to Tasmota device on {test_port}",
                    "success",
                    BannerState.SHOWING,
                )

                return TestResult(
                    f"Connected to Tasmota device on {test_port}",
                    FailureCodes.NO_FAILURE,
                    return_value={
                        "port": test_port,
                        "baudrate": baudrate,
                        "firmware_version": firmware_version,
                        "device_info": status,
                    },
                )
        except Exception as e:
            context.logger.warning(f"Failed to connect to {test_port}: {str(e)}")
            # Continue to next port

    # If we get here, no suitable port was found
    if not port and len(ftdi_ports) == 0:
        context.set_banner(
            "No FTDI USB-to-Serial devices found", "error", BannerState.SHOWING
        )
        return TestResult(
            "No FTDI USB-to-Serial devices found. Please connect an FTDI adapter with VID 0403 and PID 6001.",
            FailureCodes.FTDI_DEVICE_NOT_FOUND,
            return_value={
                "available_ports": available_ports,
                "port_details": [
                    {"device": p.device, "description": p.description, "hwid": p.hwid}
                    for p in all_ports
                ],
            },
        )
    else:
        context.set_banner("No Tasmota device found", "error", BannerState.SHOWING)
        return TestResult(
            "Failed to detect Tasmota device on any available port",
            FailureCodes.CONNECTION_FAILED,
            return_value={"available_ports": available_ports},
        )


@test()
def test_relay_control(
    category: str = None,
    test_name: str = None,
    port: str = None,
    relay_number: int = 1,
    test_cycles: int = 3,
    delay_between_cycles: float = 1.0,
) -> TestResult:
    """Test controlling a Tasmota relay by turning it on and off multiple times.

    Args:
        category (str, optional): Test category. Used internally by the test framework.
        test_name (str, optional): Test name. Used internally by the test framework.
        port (str): Serial port to use.
        relay_number (int, optional): Relay number to test. Defaults to 1.
        test_cycles (int, optional): Number of on/off cycles to test. Defaults to 3.
        delay_between_cycles (float, optional): Delay between cycles in seconds. Defaults to 1.0.

    Returns:
        TestResult: Test result with possible outcomes:
            - Success (NO_FAILURE):
                "Relay control test completed successfully"
                return_value: {
                    "port": Serial port used,
                    "relay_number": Relay number tested,
                    "cycles_completed": Number of cycles completed,
                    "final_state": Final relay state
                }

            - Failure (CONNECTION_FAILED):
                "Failed to connect to Tasmota device on {port}"

            - Failure (RELAY_CONTROL_FAILED):
                "Failed to control relay {relay_number}"
                return_value: {
                    "port": Port used,
                    "relay_number": Relay number,
                    "cycles_completed": Number of cycles completed before failure,
                    "failed_operation": Operation that failed ("ON" or "OFF"),
                    "error": Error message
                }

            - Failure (RELAY_STATE_MISMATCH):
                "Relay state does not match expected state"
                return_value: {
                    "port": Port used,
                    "relay_number": Relay number,
                    "cycles_completed": Number of cycles completed before failure,
                    "expected_state": Expected relay state,
                    "actual_state": Actual relay state
                }
    """
    context = gcc()
    max_retries = 3
    retry_delay = 1.0

    # Helper function to set relay state with retries
    def set_relay_state(driver, state, relay_num, operation_name):
        state_str = "ON" if state else "OFF"
        success = False

        for retry in range(max_retries):
            if driver.set_power(state, relay_num):
                success = True
                break
            else:
                context.logger.warning(
                    f"Failed to turn {state_str} relay, retry {retry+1}/{max_retries}"
                )
                time.sleep(retry_delay)

        if not success:
            return TestResult(
                f"Failed to turn {state_str} relay {relay_num}",
                FailureCodes.RELAY_CONTROL_FAILED,
                return_value={
                    "port": port,
                    "relay_number": relay_num,
                    "cycles_completed": cycles_completed,
                    "failed_operation": operation_name,
                },
            )
        return None  # No error

    # Helper function to verify relay state with retries
    def verify_relay_state(driver, expected_state, relay_num, operation_name):
        state_str = "ON" if expected_state else "OFF"
        state = None

        for retry in range(max_retries):
            state = driver.get_power_state(relay_num)
            if state is expected_state:
                break
            else:
                context.logger.warning(
                    f"Relay state verification failed. Expected: {state_str}, Got: {state}. Retry {retry+1}/{max_retries}"
                )
                time.sleep(retry_delay * (retry + 1))  # Increasing delay for each retry

        if state is not expected_state:
            return TestResult(
                f"Relay {relay_num} state does not match expected state",
                FailureCodes.RELAY_STATE_MISMATCH,
                return_value={
                    "port": port,
                    "relay_number": relay_num,
                    "cycles_completed": cycles_completed,
                    "expected_state": expected_state,
                    "actual_state": state,
                },
            )
        return None  # No error

    if not port:
        # Try to auto-detect port if not specified
        detect_result = detect_tasmota_serial_port(category, "Auto-detect port")
        if detect_result.failure_code != FailureCodes.NO_FAILURE:
            return detect_result
        port = detect_result.return_value["port"]

    context.set_banner(
        f"Testing relay {relay_number} control...", "info", BannerState.SHOWING
    )

    # Connect to the device
    driver = TasmotaSerialDriver(port)
    if not driver.connect():
        context.set_banner(
            f"Failed to connect to Tasmota device on {port}",
            "error",
            BannerState.SHOWING,
        )
        return TestResult(
            f"Failed to connect to Tasmota device on {port}",
            FailureCodes.CONNECTION_FAILED,
        )

    cycles_completed = 0
    final_state = None

    try:
        # First, check if the device has the specified relay
        context.logger.info(f"Checking if relay {relay_number} exists")

        # Get device status to check available relays
        status = driver.get_status()
        if status:
            context.logger.debug(f"Device status: {status}")

            # Check if we can find information about relays
            if "Status" in status:
                # Look for Power field which indicates relay support
                if "Power" in status["Status"]:
                    context.logger.info(
                        f"Device has Power field: {status['Status']['Power']}"
                    )
                else:
                    context.logger.warning(
                        f"No Power field found in Status. Available fields: {list(status['Status'].keys())}"
                    )

        # Get initial state with retries
        context.logger.info(f"Getting initial state of relay {relay_number}")
        initial_state = None
        for retry in range(max_retries):
            initial_state = driver.get_power_state(relay_number)
            if initial_state is not None:
                context.logger.info(
                    f"Initial state of relay {relay_number}: {'ON' if initial_state else 'OFF'}"
                )
                break
            else:
                context.logger.warning(
                    f"Failed to get initial state, retry {retry+1}/{max_retries}"
                )
                time.sleep(retry_delay)

        # If we still couldn't determine the state, try using Status 11 command directly
        if initial_state is None:
            context.logger.info("Initial state query failed, trying Status 11 command")
            status_response = driver.send_command("Status 11", wait_time=1.0)
            if status_response:
                context.logger.info(f"Status 11 response: {status_response}")

                # Try to determine if the device has relays from the status
                if "StatusSTS" in status_response:
                    status_sts = status_response["StatusSTS"]
                    context.logger.info(f"StatusSTS keys: {list(status_sts.keys())}")

                    # Check if POWER field exists (for single relay devices)
                    if "POWER" in status_sts:
                        context.logger.info(f"Found POWER field: {status_sts['POWER']}")
                        # Use this as the initial state for relay 1
                        if relay_number == 1:
                            initial_state = status_sts["POWER"] == "ON"
                            context.logger.info(
                                f"Using POWER field as initial state: {initial_state}"
                            )

                    # Check for POWER1, POWER2, etc. (for multi-relay devices)
                    power_key = f"POWER{relay_number}"
                    if power_key in status_sts:
                        context.logger.info(
                            f"Found {power_key} field: {status_sts[power_key]}"
                        )
                        initial_state = status_sts[power_key] == "ON"
                        context.logger.info(
                            f"Using {power_key} field as initial state: {initial_state}"
                        )
                elif "raw_response" in status_response:
                    # Try to parse the raw response
                    raw = status_response["raw_response"].upper()
                    context.logger.debug(f"Raw Status 11 response: {raw}")

                    # Look for power state in the raw response
                    if relay_number == 1:
                        if (
                            '"POWER":"ON"' in raw
                            or "POWER: ON" in raw
                            or "POWER=ON" in raw
                            or "POWER ON" in raw
                        ):
                            context.logger.info(
                                "Found power state ON in raw Status 11 response"
                            )
                            initial_state = True
                        elif (
                            '"POWER":"OFF"' in raw
                            or "POWER: OFF" in raw
                            or "POWER=OFF" in raw
                            or "POWER OFF" in raw
                        ):
                            context.logger.info(
                                "Found power state OFF in raw Status 11 response"
                            )
                            initial_state = False
                    else:
                        power_key = f"POWER{relay_number}"
                        if (
                            f'"{power_key}":"ON"' in raw
                            or f"{power_key}: ON" in raw
                            or f"{power_key}=ON" in raw
                            or f"{power_key} ON" in raw
                        ):
                            context.logger.info(
                                f"Found {power_key} state ON in raw Status 11 response"
                            )
                            initial_state = True
                        elif (
                            f'"{power_key}":"OFF"' in raw
                            or f"{power_key}: OFF" in raw
                            or f"{power_key}=OFF" in raw
                            or f"{power_key} OFF" in raw
                        ):
                            context.logger.info(
                                f"Found {power_key} state OFF in raw Status 11 response"
                            )
                            initial_state = False

        # If we still couldn't determine the state, try setting it to OFF first
        if initial_state is None:
            context.logger.warning(
                f"Could not determine initial state of relay {relay_number}, setting to OFF first"
            )
            error = set_relay_state(driver, False, relay_number, "OFF (initial)")
            if error:
                return error

            # Verify the state
            time.sleep(delay_between_cycles)
            error = verify_relay_state(driver, False, relay_number, "OFF (initial)")
            if error:
                return TestResult(
                    f"Failed to get initial state of relay {relay_number} and could not set it to a known state",
                    FailureCodes.INVALID_RESPONSE,
                    return_value={
                        "port": port,
                        "relay_number": relay_number,
                        "cycles_completed": 0,
                        "error": "Could not determine or set initial relay state",
                    },
                )

            initial_state = False

        # Run test cycles
        for cycle in range(test_cycles):
            # If the relay is already ON, toggle it OFF first to ensure we can test the ON transition
            if cycle == 0 and initial_state is True:
                context.logger.info(
                    f"Relay is already ON, toggling OFF first to test ON transition"
                )
                context.set_banner(
                    f"Preparing for cycle 1/{test_cycles}: Turning relay {relay_number} OFF first",
                    "info",
                    BannerState.SHOWING,
                )

                # Turn relay OFF and verify
                error = set_relay_state(
                    driver, False, relay_number, "OFF (preparation)"
                )
                if error:
                    return error

                time.sleep(delay_between_cycles)
                error = verify_relay_state(
                    driver, False, relay_number, "OFF (preparation)"
                )
                if error:
                    return error

                # Wait before starting the actual test cycle
                time.sleep(delay_between_cycles)

            # Turn relay ON
            context.set_banner(
                f"Cycle {cycle+1}/{test_cycles}: Turning relay {relay_number} ON",
                "info",
                BannerState.SHOWING,
            )

            error = set_relay_state(driver, True, relay_number, "ON")
            if error:
                return error

            # Verify ON state
            time.sleep(delay_between_cycles)
            error = verify_relay_state(driver, True, relay_number, "ON")
            if error:
                return error

            # Wait between state changes
            time.sleep(delay_between_cycles)

            # Turn relay OFF
            context.set_banner(
                f"Cycle {cycle+1}/{test_cycles}: Turning relay {relay_number} OFF",
                "info",
                BannerState.SHOWING,
            )

            error = set_relay_state(driver, False, relay_number, "OFF")
            if error:
                return error

            # Verify OFF state
            time.sleep(delay_between_cycles)
            error = verify_relay_state(driver, False, relay_number, "OFF")
            if error:
                return error

            # Wait between cycles
            if cycle < test_cycles - 1:
                time.sleep(delay_between_cycles)

            cycles_completed += 1

        # Restore initial state
        error = set_relay_state(driver, initial_state, relay_number, "restore")
        if error:
            context.logger.warning("Failed to restore relay to initial state")
        else:
            final_state = driver.get_power_state(relay_number)
            context.logger.info(
                f"Restored relay to initial state: {'ON' if final_state else 'OFF'}"
            )

        context.set_banner(
            f"Relay control test completed successfully", "success", BannerState.SHOWING
        )

        return TestResult(
            "Relay control test completed successfully",
            FailureCodes.NO_FAILURE,
            return_value={
                "port": port,
                "relay_number": relay_number,
                "cycles_completed": cycles_completed,
                "final_state": final_state,
            },
        )
    except Exception as e:
        context.logger.error(f"Exception during relay control test: {str(e)}")
        import traceback

        context.logger.error(traceback.format_exc())
        return TestResult(
            f"Exception during relay control test: {str(e)}",
            FailureCodes.EXCEPTION,
            return_value={
                "port": port,
                "relay_number": relay_number,
                "cycles_completed": cycles_completed,
                "error": str(e),
            },
        )
    finally:
        # Always disconnect when done
        driver.disconnect()


@test()
def check_firmware_version(
    category: str = None,
    test_name: str = None,
    port: str = None,
    min_version: str = None,
) -> TestResult:
    """Check if the Tasmota firmware version meets the minimum requirement.

    Args:
        category (str, optional): Test category. Used internally by the test framework.
        test_name (str, optional): Test name. Used internally by the test framework.
        port (str): Serial port to use.
        min_version (str, optional): Minimum required firmware version (e.g., "9.5.0").
            If None, just reports the current version without checking.

    Returns:
        TestResult: Test result with possible outcomes:
            - Success (NO_FAILURE):
                "Firmware version {version} meets minimum requirement {min_version}"
                or "Current firmware version: {version}"
                return_value: {
                    "firmware_version": Current firmware version,
                    "min_version": Minimum required version (if specified)
                }

            - Failure (CONNECTION_FAILED):
                "Failed to connect to Tasmota device on {port}"

            - Failure (INVALID_RESPONSE):
                "Failed to get firmware version"

            - Failure (FIRMWARE_VERSION_MISMATCH):
                "Firmware version {version} does not meet minimum requirement {min_version}"
                return_value: {
                    "firmware_version": Current firmware version,
                    "min_version": Minimum required version
                }
    """
    context = gcc()

    if not port:
        # Try to auto-detect port if not specified
        detect_result = detect_tasmota_serial_port(category, "Auto-detect port")
        if detect_result.failure_code != FailureCodes.NO_FAILURE:
            return detect_result
        port = detect_result.return_value["port"]

    context.set_banner("Checking firmware version...", "info", BannerState.SHOWING)

    # Connect to the device
    driver = TasmotaSerialDriver(port)
    if not driver.connect():
        context.set_banner(
            f"Failed to connect to Tasmota device on {port}",
            "error",
            BannerState.SHOWING,
        )
        return TestResult(
            f"Failed to connect to Tasmota device on {port}",
            FailureCodes.CONNECTION_FAILED,
        )

    try:
        # Get firmware version
        version = driver.get_firmware_version()
        if not version:
            context.set_banner(
                "Failed to get firmware version", "error", BannerState.SHOWING
            )
            return TestResult(
                "Failed to get firmware version",
                FailureCodes.INVALID_RESPONSE,
                return_value={"port": port},
            )

        # If min_version is specified, check if current version meets requirement
        if min_version:
            context.logger.info(
                f"Comparing version '{version}' with minimum required '{min_version}'"
            )

            # Clean up version strings to get just the numeric parts
            clean_version = extract_version_numbers(version)
            clean_min_version = extract_version_numbers(min_version)

            context.logger.info(
                f"Extracted version numbers: '{clean_version}' vs '{clean_min_version}'"
            )

            try:
                # Compare versions
                meets_requirement = compare_versions(version, min_version)

                if meets_requirement:
                    context.set_banner(
                        f"Firmware version {version} meets minimum requirement",
                        "success",
                        BannerState.SHOWING,
                    )
                    return TestResult(
                        f"Firmware version {version} meets minimum requirement {min_version}",
                        FailureCodes.NO_FAILURE,
                        return_value={
                            "firmware_version": version,
                            "min_version": min_version,
                        },
                    )
                else:
                    context.set_banner(
                        f"Firmware version {version} does not meet minimum requirement",
                        "error",
                        BannerState.SHOWING,
                    )
                    return TestResult(
                        f"Firmware version {version} does not meet minimum requirement {min_version}",
                        FailureCodes.FIRMWARE_VERSION_MISMATCH,
                        return_value={
                            "firmware_version": version,
                            "min_version": min_version,
                        },
                    )
            except Exception as e:
                context.logger.error(f"Error comparing versions: {str(e)}")
                # If version comparison fails, just report the current version
                context.set_banner(
                    f"Could not compare versions, current firmware: {version}",
                    "warning",
                    BannerState.SHOWING,
                )
                return TestResult(
                    f"Could not compare versions: {str(e)}. Current firmware: {version}",
                    FailureCodes.NO_FAILURE,
                    return_value={
                        "firmware_version": version,
                        "min_version": min_version,
                    },
                )
        else:
            # Just report the current version
            context.set_banner(
                f"Current firmware version: {version}", "info", BannerState.SHOWING
            )
            return TestResult(
                f"Current firmware version: {version}",
                FailureCodes.NO_FAILURE,
                return_value={"firmware_version": version},
            )

    except Exception as e:
        context.set_banner(
            f"Error checking firmware version: {str(e)}", "error", BannerState.SHOWING
        )
        return TestResult(
            f"Error checking firmware version: {str(e)}",
            FailureCodes.EXCEPTION,
            return_value={"error": str(e)},
        )

    finally:
        # Always disconnect
        driver.disconnect()


@test()
def connect_oscilloscope(
    category: str = None,
    test_name: str = None,
    oscilloscope_ip: str = None,
    oscilloscope_port: int = 5555,
    timebase: float = 0.001,  # 1ms/div
) -> TestResult:
    """Connect to a Rigol oscilloscope and set it up for relay testing.

    Args:
        category (str, optional): Test category. Used internally by the test framework.
        test_name (str, optional): Test name. Used internally by the test framework.
        oscilloscope_ip (str): IP address of the Rigol oscilloscope.
        oscilloscope_port (int, optional): Port for the oscilloscope. Defaults to 5555.
        timebase (float, optional): Oscilloscope timebase in seconds/div. Defaults to 0.001 (1ms/div).

    Returns:
        TestResult: Test result with possible outcomes:
            - Success (NO_FAILURE):
                "Connected to oscilloscope successfully"
                return_value: {
                    "oscilloscope": RigolOscilloscopeDriver instance
                }

            - Failure (OSCILLOSCOPE_CONNECTION_FAILED):
                "Failed to connect to oscilloscope at {oscilloscope_ip}"
                Condition: Unable to connect to the oscilloscope
    """
    context = gcc()

    if not oscilloscope_ip:
        return TestResult(
            "Oscilloscope IP address not specified",
            FailureCodes.OSCILLOSCOPE_CONNECTION_FAILED,
        )

    # Connect to the oscilloscope
    context.logger.info(f"Connecting to oscilloscope at {oscilloscope_ip}...")
    oscilloscope = RigolOscilloscopeDriver(oscilloscope_ip, oscilloscope_port)

    if not oscilloscope.connect():
        return TestResult(
            f"Failed to connect to oscilloscope at {oscilloscope_ip}",
            FailureCodes.OSCILLOSCOPE_CONNECTION_FAILED,
        )

    # Setup the oscilloscope for relay testing
    context.logger.info("Setting up oscilloscope for relay testing...")
    if not oscilloscope.setup_for_relay_test(channel=1, timebase=timebase):
        oscilloscope.disconnect()
        return TestResult(
            "Failed to setup oscilloscope",
            FailureCodes.OSCILLOSCOPE_CONNECTION_FAILED,
        )

    return TestResult(
        "Connected to oscilloscope successfully",
        return_value={"oscilloscope": oscilloscope},
    )


@test()
def test_relay_response_profile(
    category: str = None,
    test_name: str = None,
    port: str = None,
    relay_number: int = 1,
    oscilloscope_ip: str = None,
    oscilloscope_port: int = 5555,
    output_dir: str = "waveforms",
    timebase: float = 0.001,  # 1ms/div
    oscilloscope_instance=None,  # New parameter to accept an existing oscilloscope instance
) -> TestResult:
    """Test relay response profile using a Rigol oscilloscope.

    This test connects to a Tasmota relay and a Rigol oscilloscope to measure
    the relay's response time and contact bounce. It captures waveforms for
    both rising (OFF->ON) and falling (ON->OFF) transitions.

    Args:
        category (str, optional): Test category. Used internally by the test framework.
        test_name (str, optional): Test name. Used internally by the test framework.
        port (str): Serial port for the Tasmota device.
        relay_number (int, optional): Relay number to test. Defaults to 1.
        oscilloscope_ip (str): IP address of the Rigol oscilloscope.
        oscilloscope_port (int, optional): Port for the oscilloscope. Defaults to 5555.
        output_dir (str, optional): Directory to save waveform data. Defaults to "waveforms".
        timebase (float, optional): Oscilloscope timebase in seconds/div. Defaults to 0.001 (1ms/div).
        oscilloscope_instance: An existing oscilloscope instance from connect_oscilloscope.

    Returns:
        TestResult: Test result with possible outcomes:
            - Success (NO_FAILURE):
                "Relay response profile test completed successfully"
                return_value: {
                    "rising_edge": {
                        "transition_time": Rise time in ms,
                        "bounce_count": Number of bounces,
                        "bounce_duration": Total bounce duration in ms,
                        "waveform_file": Path to CSV file with waveform data
                    },
                    "falling_edge": {
                        "transition_time": Fall time in ms,
                        "bounce_count": Number of bounces,
                        "bounce_duration": Total bounce duration in ms,
                        "waveform_file": Path to CSV file with waveform data
                    }
                }

            - Failure (CONNECTION_FAILED):
                "Failed to connect to Tasmota device on {port}"

            - Failure (OSCILLOSCOPE_CONNECTION_FAILED):
                "Failed to connect to oscilloscope at {oscilloscope_ip}"

            - Failure (RELAY_CONTROL_FAILED):
                "Failed to control relay {relay_number}"

            - Failure (WAVEFORM_CAPTURE_FAILED):
                "Failed to capture waveform for {transition_type} edge"
    """
    context = gcc()

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Auto-detect Tasmota device if port not specified
    if not port:
        detect_result = detect_tasmota_serial_port(category, "Auto-detect port")
        if detect_result.failure_code != FailureCodes.NO_FAILURE:
            return detect_result
        port = detect_result.return_value["port"]

    context.logger.info(f"Testing relay {relay_number} response profile...")

    # Connect to the Tasmota device
    tasmota = TasmotaSerialDriver(port)
    if not tasmota.connect():
        return TestResult(
            f"Failed to connect to Tasmota device on {port}",
            FailureCodes.CONNECTION_FAILED,
        )

    # Use provided oscilloscope instance or create a new one
    oscilloscope = None
    should_disconnect_oscilloscope = False

    if oscilloscope_instance:
        oscilloscope = oscilloscope_instance
    elif oscilloscope_ip:
        # Connect to the oscilloscope if not provided
        context.logger.info(f"Connecting to oscilloscope at {oscilloscope_ip}...")
        oscilloscope = RigolOscilloscopeDriver(oscilloscope_ip, oscilloscope_port)
        if not oscilloscope.connect():
            tasmota.disconnect()
            return TestResult(
                f"Failed to connect to oscilloscope at {oscilloscope_ip}",
                FailureCodes.OSCILLOSCOPE_CONNECTION_FAILED,
            )

        # Setup the oscilloscope for relay testing
        context.logger.info("Setting up oscilloscope for relay testing...")
        if not oscilloscope.setup_for_relay_test(channel=1, timebase=timebase):
            oscilloscope.disconnect()
            tasmota.disconnect()
            return TestResult(
                "Failed to setup oscilloscope",
                FailureCodes.OSCILLOSCOPE_CONNECTION_FAILED,
            )

        should_disconnect_oscilloscope = True
    else:
        tasmota.disconnect()
        return TestResult(
            "No oscilloscope provided or specified",
            FailureCodes.OSCILLOSCOPE_CONNECTION_FAILED,
        )

    try:
        # Get initial state of the relay
        initial_state = tasmota.get_power_state(relay_number)
        if initial_state is None:
            return TestResult(
                f"Failed to get initial state of relay {relay_number}",
                FailureCodes.RELAY_CONTROL_FAILED,
            )

        context.logger.info(f"Initial relay state: {'ON' if initial_state else 'OFF'}")

        # Test results
        results = {
            "rising_edge": {},
            "falling_edge": {},
        }

        # Test rising edge (OFF->ON)
        context.logger.info("Testing rising edge (OFF->ON)...")

        # First, ensure the relay is OFF
        if initial_state:
            context.logger.info("Turning relay OFF to prepare for rising edge test")
            if not tasmota.set_power(False, relay_number):
                return TestResult(
                    f"Failed to turn relay {relay_number} OFF",
                    FailureCodes.RELAY_CONTROL_FAILED,
                )
            time.sleep(1)  # Wait for relay to stabilize

        # Setup oscilloscope for rising edge
        context.logger.info("Setting up oscilloscope for rising edge trigger")
        oscilloscope.send_command(":TRIG:EDGE:SLOP POS")
        oscilloscope.send_command(":TRIG:EDGE:LEV 2.5")
        oscilloscope.send_command(":SING")  # Single trigger mode
        time.sleep(0.5)  # Wait for oscilloscope to be ready

        # Turn relay ON and capture the rising edge
        context.logger.info(f"Turning relay {relay_number} ON")
        if not tasmota.set_power(True, relay_number):
            return TestResult(
                f"Failed to turn relay {relay_number} ON",
                FailureCodes.RELAY_CONTROL_FAILED,
            )

        # Wait for trigger and capture waveform
        context.logger.info("Waiting for rising edge trigger...")
        triggered = False
        start_time = time.time()
        while (time.time() - start_time) < 5:  # 5 second timeout
            status = oscilloscope.query(":TRIG:STAT?")
            if status and "STOP" in status:
                triggered = True
                break
            time.sleep(0.1)

        if not triggered:
            context.logger.warning("Rising edge trigger timeout")
            results["rising_edge"]["error"] = "Trigger timeout"
        else:
            # Capture and save waveform
            context.logger.info("Capturing rising edge waveform")
            waveform = oscilloscope.capture_waveform(channel=1)
            if waveform is not None:
                rising_file = os.path.join(output_dir, "relay_rising.csv")
                if oscilloscope.save_waveform_to_csv(waveform, rising_file):
                    context.logger.info(f"Saved rising edge waveform to {rising_file}")

                    # Analyze the waveform
                    analysis = oscilloscope.analyze_relay_transition(rising_file)
                    results["rising_edge"] = analysis
                    results["rising_edge"]["waveform_file"] = rising_file

                    context.logger.info(f"Rising edge analysis: {analysis}")
                else:
                    context.logger.error("Failed to save rising edge waveform")
                    results["rising_edge"]["error"] = "Failed to save waveform"
            else:
                context.logger.error("Failed to capture rising edge waveform")
                results["rising_edge"]["error"] = "Failed to capture waveform"

        # Wait for relay to stabilize
        time.sleep(1)

        # Test falling edge (ON->OFF)
        context.logger.info(
            "Testing falling edge (ON->OFF)...", "info", BannerState.SHOWING
        )

        # Setup oscilloscope for falling edge
        context.logger.info("Setting up oscilloscope for falling edge trigger")
        oscilloscope.send_command(":TRIG:EDGE:SLOP NEG")
        oscilloscope.send_command(":TRIG:EDGE:LEV 2.5")
        oscilloscope.send_command(":SING")  # Single trigger mode
        time.sleep(0.5)  # Wait for oscilloscope to be ready

        # Turn relay OFF and capture the falling edge
        context.logger.info(f"Turning relay {relay_number} OFF")
        if not tasmota.set_power(False, relay_number):
            return TestResult(
                f"Failed to turn relay {relay_number} OFF",
                FailureCodes.RELAY_CONTROL_FAILED,
            )

        # Wait for trigger and capture waveform
        context.logger.info("Waiting for falling edge trigger...")
        triggered = False
        start_time = time.time()
        while (time.time() - start_time) < 5:  # 5 second timeout
            status = oscilloscope.query(":TRIG:STAT?")
            if status and "STOP" in status:
                triggered = True
                break
            time.sleep(0.1)

        if not triggered:
            context.logger.warning("Falling edge trigger timeout")
            results["falling_edge"]["error"] = "Trigger timeout"
        else:
            # Capture and save waveform
            context.logger.info("Capturing falling edge waveform")
            waveform = oscilloscope.capture_waveform(channel=1)
            if waveform is not None:
                falling_file = os.path.join(output_dir, "relay_falling.csv")
                if oscilloscope.save_waveform_to_csv(waveform, falling_file):
                    context.logger.info(
                        f"Saved falling edge waveform to {falling_file}"
                    )

                    # Analyze the waveform
                    analysis = oscilloscope.analyze_relay_transition(falling_file)
                    results["falling_edge"] = analysis
                    results["falling_edge"]["waveform_file"] = falling_file

                    context.logger.info(f"Falling edge analysis: {analysis}")
                else:
                    context.logger.error("Failed to save falling edge waveform")
                    results["falling_edge"]["error"] = "Failed to save waveform"
            else:
                context.logger.error("Failed to capture falling edge waveform")
                results["falling_edge"]["error"] = "Failed to capture waveform"

        # Restore initial state
        context.logger.info(
            f"Restoring relay to initial state: {'ON' if initial_state else 'OFF'}"
        )
        tasmota.set_power(initial_state, relay_number)

        # Check if we captured at least one waveform successfully
        if "error" in results["rising_edge"] and "error" in results["falling_edge"]:
            context.set_banner(
                "Failed to capture any waveforms", "error", BannerState.SHOWING
            )
            return TestResult(
                "Failed to capture any waveforms",
                FailureCodes.WAVEFORM_CAPTURE_FAILED,
                return_value=results,
            )

        # Save analysis results to CSV for Onnyx to upload
        try:
            import csv

            # Create a summary CSV file with static name
            summary_file = os.path.join(output_dir, "relay_response_summary.csv")

            with open(summary_file, "w", newline="") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["Parameter", "Rising Edge", "Falling Edge"])
                writer.writerow(
                    [
                        "Test Time",
                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ]
                )
                writer.writerow(["Relay Number", relay_number, relay_number])

                # Add transition metrics
                rising_time = results["rising_edge"].get("transition_time_ms", "N/A")
                falling_time = results["falling_edge"].get("transition_time_ms", "N/A")
                writer.writerow(["Transition Time (ms)", rising_time, falling_time])

                rising_bounce = results["rising_edge"].get("bounce_count", "N/A")
                falling_bounce = results["falling_edge"].get("bounce_count", "N/A")
                writer.writerow(["Bounce Count", rising_bounce, falling_bounce])

                rising_bounce_duration = results["rising_edge"].get(
                    "bounce_duration_ms", "N/A"
                )
                falling_bounce_duration = results["falling_edge"].get(
                    "bounce_duration_ms", "N/A"
                )
                writer.writerow(
                    [
                        "Bounce Duration (ms)",
                        rising_bounce_duration,
                        falling_bounce_duration,
                    ]
                )

                rising_start_voltage = results["rising_edge"].get(
                    "start_voltage", "N/A"
                )
                falling_start_voltage = results["falling_edge"].get(
                    "start_voltage", "N/A"
                )
                writer.writerow(
                    ["Start Voltage (V)", rising_start_voltage, falling_start_voltage]
                )

                rising_end_voltage = results["rising_edge"].get("end_voltage", "N/A")
                falling_end_voltage = results["falling_edge"].get("end_voltage", "N/A")
                writer.writerow(
                    ["End Voltage (V)", rising_end_voltage, falling_end_voltage]
                )

                # Add waveform file paths
                rising_file = results["rising_edge"].get("waveform_file", "N/A")
                falling_file = results["falling_edge"].get("waveform_file", "N/A")
                writer.writerow(["Waveform File", rising_file, falling_file])

                # Add any errors
                rising_error = results["rising_edge"].get("error", "None")
                falling_error = results["falling_edge"].get("error", "None")
                writer.writerow(["Error", rising_error, falling_error])

            context.logger.info(f"Saved analysis summary to {summary_file}")

            # Add the summary file to the results
            results["summary_file"] = summary_file

            # Create a detailed CSV with all parameters - static name
            detailed_file = os.path.join(output_dir, "relay_response_detailed.csv")

            with open(detailed_file, "w", newline="") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["Edge Type", "Parameter", "Value"])

                # Add all parameters from rising edge
                for key, value in results["rising_edge"].items():
                    if (
                        key != "waveform_file"
                    ):  # Skip the file path to keep the CSV clean
                        writer.writerow(["Rising", key, value])

                # Add all parameters from falling edge
                for key, value in results["falling_edge"].items():
                    if (
                        key != "waveform_file"
                    ):  # Skip the file path to keep the CSV clean
                        writer.writerow(["Falling", key, value])

            context.logger.info(f"Saved detailed analysis to {detailed_file}")
            results["detailed_file"] = detailed_file

        except Exception as e:
            context.logger.error(f"Error saving analysis to CSV: {str(e)}")
            results["csv_error"] = str(e)

        # Test completed successfully
        context.set_banner(
            "Relay response profile test completed", "success", BannerState.SHOWING
        )

        return TestResult(
            "Relay response profile test completed successfully",
            FailureCodes.NO_FAILURE,
            return_value=results,
        )

    except Exception as e:
        context.logger.error(f"Exception during relay response profile test: {str(e)}")
        import traceback

        context.logger.error(traceback.format_exc())
        return TestResult(
            f"Exception during relay response profile test: {str(e)}",
            FailureCodes.EXCEPTION,
            return_value={"error": str(e)},
        )
    finally:
        # Always disconnect from devices
        tasmota.disconnect()
        if should_disconnect_oscilloscope:
            oscilloscope.disconnect()
