from onnyx.context import TestContext, test_context
from onnyx.mqtt import BannerState
import platform
import os
import sys

# Add the current directory to the path to ensure imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import test functions
from tests.tasmota_tests import (
    FailureCodes,
    detect_tasmota_serial_port,
    test_relay_control,
    check_firmware_version,
    connect_oscilloscope,
    test_relay_response_profile,
)
from tests.utils import extract_version_numbers, compare_versions


def example_flow(test_document, settings):
    print("Starting Tasmota relay test flow")
    print("Test document:", test_document)
    print("Settings:", settings)

    try:
        cellSettings = test_document["_cell_settings_obj"]
        cellConfig = test_document["_cell_config_obj"]

        # Initialize the test context
        context = TestContext.initialize(
            settings, test_document, FailureCodes.get_descriptions()
        )

        # Use the context manager correctly
        with test_context(context) as ctx:
            ctx.logger.info("Starting Tasmota relay tests")

            failure_code = FailureCodes.NO_FAILURE

            # Get configuration values with defaults
            serial_port = cellConfig.get("serial_port", None)  # Auto-detect if None
            baudrate = cellConfig.get("baudrate", 115200)
            relay_number = cellConfig.get("relay_number", 1)
            test_cycles = cellConfig.get("test_cycles", 3)
            delay_between_cycles = cellConfig.get("delay_between_cycles", 1.0)
            min_firmware_version = cellConfig.get("min_firmware_version", None)
            oscilloscope_ip = cellConfig.get("oscilloscope_ip", None)
            oscilloscope_port = cellConfig.get("oscilloscope_port", 5555)
            oscilloscope_timebase = cellConfig.get("oscilloscope_timebase", 0.001)
            enable_oscilloscope_test = cellConfig.get("enable_oscilloscope_test", False)
            waveform_output_dir = cellConfig.get("waveform_output_dir", "waveforms")

            # Step 1: Detect and connect to Tasmota device
            if failure_code == FailureCodes.NO_FAILURE:
                ctx.logger.info("Step 1: Detecting Tasmota device")
                rc = detect_tasmota_serial_port(
                    "Init", "Detect Tasmota device", serial_port, baudrate
                )

                if rc.failure_code != FailureCodes.NO_FAILURE:
                    failure_code = rc.failure_code
                else:
                    ctx.record_values(rc.return_value)
                    serial_port = rc.return_value["port"]

            # Step 2: Check firmware version if required
            if failure_code == FailureCodes.NO_FAILURE and min_firmware_version:
                ctx.logger.info("Step 2: Checking firmware version")
                rc = check_firmware_version(
                    "Firmware",
                    "Check firmware version",
                    serial_port,
                    min_firmware_version,
                )

                if rc.failure_code != FailureCodes.NO_FAILURE:
                    # Don't fail the test if firmware version check fails, just log a warning
                    ctx.logger.warning(
                        "Continuing with tests despite firmware version check failure"
                    )
                else:
                    ctx.record_values(rc.return_value)

            # Step 3: Test relay control
            if failure_code == FailureCodes.NO_FAILURE:
                ctx.logger.info("Step 3: Testing relay control")
                rc = test_relay_control(
                    "Relay Test",
                    "Test relay control",
                    serial_port,
                    relay_number,
                    test_cycles,
                    delay_between_cycles,
                )

                if rc.failure_code != FailureCodes.NO_FAILURE:
                    failure_code = rc.failure_code
                else:
                    ctx.record_values(rc.return_value)

            # Step 4: Connect to oscilloscope (if enabled)
            oscilloscope_instance = None
            if (
                failure_code == FailureCodes.NO_FAILURE
                and enable_oscilloscope_test
                and oscilloscope_ip
            ):
                ctx.logger.info("Step 4: Connecting to oscilloscope")

                # Create output directory if it doesn't exist
                os.makedirs(waveform_output_dir, exist_ok=True)

                rc = connect_oscilloscope(
                    "Oscilloscope",
                    "Connect to oscilloscope",
                    oscilloscope_ip,
                    oscilloscope_port,
                    oscilloscope_timebase,
                )

                if rc.failure_code != FailureCodes.NO_FAILURE:
                    # Don't fail the entire test if oscilloscope connection fails, just log a warning
                    ctx.logger.warning(
                        "Continuing despite oscilloscope connection failure"
                    )
                else:
                    ctx.record_values(rc.return_value)
                    oscilloscope_instance = rc.return_value.get("oscilloscope")

            # Step 5: Test relay response profile with oscilloscope (if connected)
            if (
                failure_code == FailureCodes.NO_FAILURE
                and enable_oscilloscope_test
                and oscilloscope_instance
            ):
                ctx.logger.info(
                    "Step 5: Testing relay response profile with oscilloscope"
                )

                rc = test_relay_response_profile(
                    "Oscilloscope Test",
                    "Test relay response profile",
                    serial_port,
                    relay_number,
                    oscilloscope_ip,
                    oscilloscope_port,
                    waveform_output_dir,
                    oscilloscope_timebase,
                    oscilloscope_instance,
                )

                if rc.failure_code != FailureCodes.NO_FAILURE:
                    # Don't fail the entire test if oscilloscope test fails, just log a warning
                    ctx.logger.warning("Continuing despite oscilloscope test failure")
                else:
                    ctx.record_values(rc.return_value)

            # Wrap up the test
            ctx.wrap_up(failure_code)

    except Exception as e:
        print(f"Error in Tasmota relay test flow: {e}")
        import traceback

        print("Traceback:", traceback.format_exc())
        raise


if __name__ == "__main__":
    test_document = {
        "_id": "0",  # this can be anything
        "_cell_config_obj": {
            "serial_port": None,  # Auto-detect FTDI devices
            "baudrate": 115200,
            "relay_number": 1,
            "test_cycles": 3,
            "delay_between_cycles": 1.0,
            "min_firmware_version": "9.5.0",  # Minimum required Tasmota version
            # Oscilloscope configuration
            "oscilloscope_ip": None,  # Set to your oscilloscope's IP address to enable
            "oscilloscope_port": 5555,
            "oscilloscope_timebase": 0.001,  # 1ms/div
            "enable_oscilloscope_test": False,  # Set to True to enable oscilloscope test
            "waveform_output_dir": "waveforms",
        },
        "_cell_settings_obj": {
            "not_used_in_this_example": "This is not used in this example",
        },
    }
    example_flow(test_document, "DEV")
