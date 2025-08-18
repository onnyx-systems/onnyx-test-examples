from onnyx.context import test_context

from tests.minimal_firmware_tests import (
    FailureCodes,
    detect_minimal_firmware_serial_port,
    check_firmware_version,
    test_basic_relay_control,
    test_relay_reliability,
)


def check_required_config_flow(ctx, config, required_keys):
    """Helper function to check required configuration in flow context."""
    for key in required_keys:
        if key not in config:
            ctx.logger.error(f"Missing required configuration: {key}")
            return FailureCodes.CONFIGURATION_ERROR
    return None


def example_flow(test_document, settings):
    """
    Main test flow for minimal firmware relay testing.
    
    This simplified test flow demonstrates:
    1. Detecting and connecting to a minimal firmware device
    2. Checking firmware version
    3. Testing basic relay control
    """
    print("Starting minimal firmware relay test flow")
    print("Test document:", test_document)
    print("Settings:", settings)

    cellSettings = test_document["_cell_settings_obj"]
    cellConfig = test_document["_cell_config_obj"]

    with test_context(settings, test_document, FailureCodes.get_descriptions()) as ctx:
        ctx.logger.info("Starting minimal firmware relay tests")

        failure_code = FailureCodes.NO_FAILURE

        # Check required configuration
        config_check = check_required_config_flow(ctx, cellConfig, [
            "baudrate",
            "test_cycles",
        ])
        if config_check:
            failure_code = config_check
            ctx.wrap_up(failure_code)
            return

        # Get configuration values
        config = cellConfig
        
        ctx.logger.info("=== MINIMAL FIRMWARE RELAY TEST START ===")
        ctx.logger.info(f"Configuration: {config}")

        # STEP 1: Detect and connect to minimal firmware device
        ctx.logger.info("STEP 1: Detecting and connecting to minimal firmware device")
        rc = detect_minimal_firmware_serial_port(
            "MinimalFirmware",  # category
            "Detect and connect to device",  # test_name
            config.get("serial_port"),  # port
            config.get("baudrate", 115200),  # baudrate
        )

        if rc.failure_code != FailureCodes.NO_FAILURE:
            ctx.logger.error(f"Failed to detect minimal firmware device: {rc.message}")
            failure_code = rc.failure_code
            ctx.wrap_up(failure_code)
            return
        else:
            ctx.record_values(rc.return_value)
            serial_port = rc.return_value["port"]
            ctx.logger.info(f"Successfully connected to minimal firmware device on {serial_port}")

        # STEP 2: Check firmware version
        ctx.logger.info("STEP 2: Checking firmware version")
        rc = check_firmware_version(
            "MinimalFirmware",  # category
            "Check firmware version",  # test_name
            serial_port,
            config.get("min_firmware_version", "1.0.0"),
        )

        if rc.failure_code != FailureCodes.NO_FAILURE:
            ctx.logger.error(f"Firmware version check failed: {rc.message}")
            failure_code = rc.failure_code
            ctx.wrap_up(failure_code)
            return
        else:
            ctx.record_values(rc.return_value)
            ctx.logger.info(f"Firmware version check passed")

        # STEP 3: Test basic relay control
        ctx.logger.info("STEP 3: Testing basic relay control")
        rc = test_basic_relay_control(
            "Relay",  # category
            "Basic relay control",  # test_name
            serial_port,
            config.get("test_cycles", 5),
        )

        if rc.failure_code != FailureCodes.NO_FAILURE:
            ctx.logger.error(f"Basic relay control test failed: {rc.message}")
            failure_code = rc.failure_code
            ctx.wrap_up(failure_code)
            return
        else:
            ctx.record_values(rc.return_value)
            ctx.logger.info("Basic relay control test passed")

        # STEP 4: Test relay reliability (catch race conditions and bugs)
        if config.get("enable_reliability_test", True):
            ctx.logger.info("STEP 4: Testing relay reliability (bug detection)")
            rc = test_relay_reliability(
                "Reliability",  # category
                "Relay reliability test",  # test_name
                serial_port,
                config.get("reliability_cycles", 30),
            )

            if rc.failure_code != FailureCodes.NO_FAILURE:
                ctx.logger.error(f"Reliability test failed: {rc.message}")
                # Note: This is likely to fail with buggy firmware
                failure_code = rc.failure_code
                ctx.wrap_up(failure_code)
                return
            else:
                ctx.record_values(rc.return_value)
                ctx.logger.info("Relay reliability test passed")
        else:
            ctx.logger.info("STEP 4: Skipping reliability test (disabled)")

        ctx.logger.info("All essential hardware tests completed successfully")

        ctx.logger.info("=== ALL TESTS COMPLETED SUCCESSFULLY ===")
        
        # Wrap up the test
        ctx.wrap_up(failure_code)


if __name__ == "__main__":
    test_document = {
        "_id": "0",  # this can be anything
        "_cell_config_obj": {
            "serial_port": "/dev/ttyUSB0",  # Specific port for testing
            "baudrate": 115200,
            "test_cycles": 3,
            "min_firmware_version": "1.0.0",  # Minimum required firmware version
            "enable_reliability_test": True,  # Enable bug detection test
            "reliability_cycles": 30,  # Number of reliability test cycles
        },
        "_cell_settings_obj": {
        },
    }
    example_flow(test_document, "DEV")