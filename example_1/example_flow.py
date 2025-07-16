from onnyx.context import test_context
from tests import (
    FailureCodes,
    check_system_dependencies,
    check_internet_connection,
    is_drive_present,
    disk_test,
    take_picture,
    cpu_stress_test,
    get_screen_resolution,
    check_battery_status,
)
from onnyx.mqtt import BannerState
import platform


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


def example_flow(test_document: dict, settings: str):
    print("Starting example_flow")
    print("Test document:", test_document)
    print("Settings:", settings)

    cellSettings = test_document["_cell_settings_obj"]
    cellConfig = test_document["_cell_config_obj"]

    # Use the context manager correctly
    with test_context(settings, test_document, FailureCodes.get_descriptions()) as ctx:
        ctx.logger.info("Starting example tests")

        # Check required configuration
        config_check = check_required_config_flow(ctx, cellConfig, [
            "ping_url",
            "num_pings", 
            "ping_interval",
            "min_write_speed_mbps",
            "num_test_files",
            "enable_camera_test",
            "cpu_stress_duration",
            "battery_test_enable",
            "skip_screen_resolution_check",
            "min_resolution_width",
            "min_resolution_height",
            "battery_percentage_range",
            "battery_voltage_range",
            "cpu_usage_range",
            "write_speed_mbps"
        ])
        if config_check:
            failure_code = config_check
            ctx.wrap_up(failure_code)
            return

        failure_code = FailureCodes.NO_FAILURE

        if failure_code == FailureCodes.NO_FAILURE and cellConfig.get("enable_intentional_fail", False):
            failure_code = FailureCodes.INTENTIONAL_TEST_FAIL

        if failure_code == FailureCodes.NO_FAILURE:
            ctx.logger.info("Starting test: Checking system dependencies")
            rc = check_system_dependencies("Init", "Check system dependencies")
            if rc.failure_code != FailureCodes.NO_FAILURE:
                ctx.logger.error("Missing required dependencies")
                failure_code = rc.failure_code
            else:
                ctx.record_values(rc.return_value)
            ctx.logger.info("Test completed: %s", rc.return_value)

        if failure_code == FailureCodes.NO_FAILURE:
            ctx.logger.info("Starting test: Checking internet connection")
            rc = check_internet_connection(
                "Init",
                "Check internet connection",
                cellConfig.get("ping_url"),
                cellConfig.get("num_pings"),
                cellConfig.get("ping_interval"),
            )
            ctx.logger.info(rc.__dict__)
            if rc.failure_code != FailureCodes.NO_FAILURE:
                ctx.logger.info("Test failed with failure code: %s", rc.failure_code)
                failure_code = rc.failure_code
            else:
                ctx.record_values(rc.return_value)
            ctx.logger.info("Test completed: %s", rc.return_value)

        # clear the banner
        ctx.set_banner("", "info", BannerState.HIDDEN)

        if failure_code == FailureCodes.NO_FAILURE:
            ctx.logger.info("Starting test: Checking if drive is present")
            # Get default drive based on platform
            default_drive = "C" if platform.system() == "Windows" else "/"
            drive_setting = cellConfig.get("drive_letter")

            # If a drive letter is specified in config, respect the platform
            if drive_setting and platform.system() != "Windows":
                # Convert Windows drive letter to Linux root
                drive_setting = "/"

            rc = is_drive_present(
                "Init",
                "Check if drive is present",
                drive_setting or default_drive,
            )
            if rc.failure_code != FailureCodes.NO_FAILURE:
                failure_code = rc.failure_code
            ctx.record_values(rc.return_value)


        if failure_code == FailureCodes.NO_FAILURE:
            min_mbps = cellConfig.get("min_write_speed_mbps")
            num_test_files = cellConfig.get("num_test_files")
            rc = disk_test("Storage Test", "Save data", min_mbps, num_test_files)
            if rc.failure_code != FailureCodes.NO_FAILURE:
                failure_code = rc.failure_code
            else:
                ctx.record_values(rc.return_value)
            ctx.logger.info("Test completed: %s Failure code: %s", rc.return_value, rc.failure_code)

        if failure_code == FailureCodes.NO_FAILURE and cellConfig.get("enable_camera_test"):
            rc = take_picture("Camera Test", "Take picture")
            if rc.failure_code != FailureCodes.NO_FAILURE:
                failure_code = rc.failure_code
            else:
                ctx.record_values(rc.return_value)
            ctx.logger.info("Test completed: %s Failure code: %s", rc.return_value, rc.failure_code)

        if failure_code == FailureCodes.NO_FAILURE:
            ctx.logger.info("Starting test: Performing CPU stress test")
            rc = cpu_stress_test(
                "CPU Test",
                "Perform CPU stress test",
                cellConfig.get("cpu_stress_duration"),
            )
            if rc.failure_code != FailureCodes.NO_FAILURE:
                failure_code = rc.failure_code
            else:
                ctx.record_values(rc.return_value)
            ctx.logger.info("Test completed: %s Failure code: %s", rc.return_value, rc.failure_code)

        # clear the banner
        ctx.set_banner("", "info", BannerState.HIDDEN)

        if failure_code == FailureCodes.NO_FAILURE:
            ctx.logger.info("Starting test: Getting screen resolution")
            rc = get_screen_resolution("Display Test", "Get screen resolution")
            if rc.failure_code != FailureCodes.NO_FAILURE:
                failure_code = rc.failure_code
            else:
                ctx.record_values(rc.return_value)
            ctx.logger.info("Test completed: %s Failure code: %s", rc.return_value, rc.failure_code)

        if failure_code == FailureCodes.NO_FAILURE and cellConfig.get("battery_test_enable"):
            rc = check_battery_status("Battery Test", "Check battery status")
            if rc.failure_code != FailureCodes.NO_FAILURE:
                failure_code = rc.failure_code
            else:
                ctx.record_values(rc.return_value)
            ctx.logger.info("Test completed: %s", rc.return_value)

        ctx.wrap_up(failure_code)


if __name__ == "__main__":
    test_document = {
        "_id": "0",  # this can be anything
        "_cell_config_obj": {
            # Required configuration
            "ping_url": "https://www.google.com",
            "num_pings": 5,
            "ping_interval": 1.0,
            "min_write_speed_mbps": 10,
            "num_test_files": 10,
            "enable_camera_test": False,
            "cpu_stress_duration": 5,
            "battery_test_enable": False,
            "skip_screen_resolution_check": False,  # Set to True for headless systems
            # Hardware test configuration
            "min_resolution_width": {"min": 1024, "max": 100000},
            "min_resolution_height": {"min": 768, "max": 100000},
            "battery_percentage_range": {"min": 10.0, "max": 100.0},
            "battery_voltage_range": {"min": 10.8, "max": 12.6},  # Typical laptop battery range
            "cpu_usage_range": {"max": 100, "min": 1},
            "write_speed_mbps": {"max": 10000, "min": 300},
            # Optional configuration
            "drive_letter": "C",
            "enable_intentional_fail": False,
        },
        "_cell_settings_obj": {
            "not_used_in_this_example": "This is not used in this example",
        },
    }
    example_flow(test_document, "DEV")
