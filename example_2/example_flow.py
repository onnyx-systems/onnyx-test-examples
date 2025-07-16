from onnyx.context import test_context

from tests.tasmota_tests import (
    FailureCodes,
    detect_tasmota_serial_port,
    check_firmware_version,
    test_relay_response,
)
from tests.scope import (
    connect_oscilloscope,
    detect_oscilloscope,
)


def check_required_config_flow(ctx, config, required_keys):
    """Helper function to check required configuration in flow context.
    
    Args:
        ctx: Test context
        config: Configuration dictionary to check
        required_keys: List of required configuration keys
        
    Returns:
        FailureCode if any keys are missing, None if all present
    """
    for key in required_keys:
        if key not in config:
            ctx.logger.error(f"Missing required configuration: {key}")
            return FailureCodes.CONFIGURATION_ERROR
    return None


def example_flow(test_document, settings):
    """
    Main test flow for Tasmota relay testing with oscilloscope measurements.
    
    This test flow demonstrates:
    1. Detecting and connecting to a Tasmota device
    2. Checking firmware version
    3. Connecting to an oscilloscope
    4. Measuring relay response characteristics
    5. Capturing and analyzing AC waveforms

    Args:
        test_document: Test document with configuration
        settings: Test settings (e.g., "DEV", "PROD")
    """
    print("Starting Tasmota relay test flow")
    print("Test document:", test_document)
    print("Settings:", settings)

    cellSettings = test_document["_cell_settings_obj"]
    cellConfig = test_document["_cell_config_obj"]

    with test_context(settings, test_document, FailureCodes.get_descriptions()) as ctx:
        ctx.logger.info("Starting Tasmota relay tests")

        failure_code = FailureCodes.NO_FAILURE

        # Check required configuration
        config_check = check_required_config_flow(ctx, cellConfig, [
            "baudrate",
            "oscilloscope_port", 
            "oscilloscope_timebase",
            "relay_number",
            "enable_intentional_fail"
        ])
        if config_check:
            failure_code = config_check
            ctx.wrap_up(failure_code)
            return
        
        # Check required settings configuration
        settings_check = check_required_config_flow(ctx, cellSettings, [
            "oscilloscope_ip"
        ])
        if settings_check:
            failure_code = settings_check
            ctx.wrap_up(failure_code)
            return
        
        # Get configuration values
        serial_port = cellConfig.get("serial_port")  # None means auto-detect
        baudrate = cellConfig.get("baudrate")
        min_firmware_version = cellConfig.get("min_firmware_version")  # None means skip version check
        oscilloscope_ip = cellSettings.get("oscilloscope_ip")
        oscilloscope_port = cellConfig.get("oscilloscope_port")
        oscilloscope_timebase = cellConfig.get("oscilloscope_timebase")
        relay_number = cellConfig.get("relay_number")

        # STEP 1: Detect and connect to Tasmota device
        ctx.logger.info("STEP 1: Detecting and connecting to Tasmota device")
        rc = detect_tasmota_serial_port(
            "Tasmota",  # category
            "Detect and connect to device",  # test_name
            serial_port,  # port
            baudrate,  # baudrate
        )

        if rc.failure_code != FailureCodes.NO_FAILURE:
            ctx.logger.error(f"Failed to detect Tasmota device: {rc.message}")
            failure_code = rc.failure_code
            ctx.wrap_up(failure_code)
            return
        else:
            ctx.record_values(rc.return_value)
            serial_port = rc.return_value["port"]
            ctx.logger.info(
                f"Successfully connected to Tasmota device on {serial_port}"
            )

        # STEP 2: Check firmware version if required
        if min_firmware_version:
            ctx.logger.info("STEP 2: Checking firmware version")
            rc = check_firmware_version(
                "Tasmota",  # category
                "Check firmware version",  # test_name
                serial_port,
                min_firmware_version,
            )

            if rc.failure_code != FailureCodes.NO_FAILURE:
                ctx.logger.error(f"Firmware version check failed: {rc.message}")
                failure_code = rc.failure_code
                ctx.wrap_up(failure_code)
                return
            else:
                ctx.record_values(rc.return_value)
                firmware_version = rc.return_value["firmware_version"]
                ctx.logger.info(
                    f"Firmware version {firmware_version} meets requirements"
                )

        # STEP 3: Connect to oscilloscope
        oscilloscope_instance = None
        ctx.logger.info("STEP 3: Connecting to oscilloscope")

        # Check if oscilloscope IP is provided
        if not oscilloscope_ip:
            ctx.logger.error("No oscilloscope IP address provided")
            failure_code = FailureCodes.OSCILLOSCOPE_ERROR
            ctx.wrap_up(failure_code)
            return

        # Check if oscilloscope is available
        rc = detect_oscilloscope(
            "Oscilloscope",  # category
            "Check availability",  # test_name
            oscilloscope_ip,
            oscilloscope_port,
        )

        if rc.failure_code != FailureCodes.NO_FAILURE:
            ctx.logger.error(f"Oscilloscope check failed: {rc.message}")
            failure_code = rc.failure_code
            ctx.wrap_up(failure_code)
            return
        else:
            ctx.record_values(rc.return_value)
            ctx.logger.info(
                f"Found oscilloscope: {rc.return_value['oscilloscope_idn']}"
            )

        # Connect and configure oscilloscope
        rc = connect_oscilloscope(
            "Oscilloscope",  # category
            "Connect and configure",  # test_name
            oscilloscope_ip,
            oscilloscope_port,
            oscilloscope_timebase,
        )

        if rc.failure_code != FailureCodes.NO_FAILURE:
            ctx.logger.error(f"Oscilloscope connection failed: {rc.message}")
            failure_code = rc.failure_code
            ctx.wrap_up(failure_code)
            return
        else:
            ctx.record_values(rc.return_value)
            ctx.logger.info(
                f"Successfully connected to oscilloscope at {oscilloscope_ip}"
            )

        # STEP 4: Test relay response with oscilloscope
        ctx.logger.info("STEP 4: Testing relay response")
        rc = test_relay_response(
            "Relay", "Test response", serial_port, relay_number  # category  # test_name
        )

        if rc.failure_code != FailureCodes.NO_FAILURE:
            ctx.logger.error(f"Relay test failed: {rc.message}")
            failure_code = rc.failure_code
            # Record measurements even if test failed
            if rc.return_value:
                ctx.record_values({"measurements": rc.return_value})
        else:
            ctx.record_values({"measurements": rc.return_value})
            ctx.logger.info("Relay test passed")

        # Disconnect from oscilloscope if connected
        if oscilloscope_instance:
            try:
                oscilloscope_instance.disconnect()
                ctx.logger.info("Disconnected from oscilloscope")
            except Exception as e:
                ctx.logger.warning(f"Error disconnecting from oscilloscope: {str(e)}")

        # Wrap up the test
        ctx.wrap_up(failure_code)


if __name__ == "__main__":
    test_document = {
        "_id": "0",  # this can be anything
        "_cell_config_obj": {
            "serial_port": None,  # Auto-detect FTDI devices
            "baudrate": 115200,
            "relay_number": 1,
            "min_firmware_version": "9.5.0",  # Minimum required Tasmota version
            # Oscilloscope configuration
            "oscilloscope_port": 5555,
            "oscilloscope_timebase": 0.005,  # 5ms/div for 60Hz AC (3 cycles per screen)
            # Required range configurations
            "ac_frequency_range": {"min": 55.0, "max": 65.0},  # 60Hz ±5Hz
            "ac_voltage_range": {"min": 100.0, "max": 130.0},  # 120V ±10%
            "duty_cycle_range": {"min": 45.0, "max": 55.0},  # 50% ±5% for AC sine wave
            "voltage_stability_range": {"min": 0.0, "max": 2.0},  # Max 2% variation
            "enable_intentional_fail": 0.0,  # Set to 0.025 for 2.5% random failure chance
        },
        "_cell_settings_obj": {
            "oscilloscope_ip": "10.42.0.150",  # Set to your oscilloscope's IP address or None for auto-detection
        },
    }
    example_flow(test_document, "DEV")
