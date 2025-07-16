from onnyx.context import test_context
from tests.example_tests import (
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

def example_flow(test_document: dict, settings: str):
    print("Starting example_flow")
    print("Test document:", test_document)
    print("Settings:", settings)

    cellSettings = test_document["_cell_settings_obj"]
    cellConfig = test_document["_cell_config_obj"]

    # Use the context manager correctly
    with test_context(settings, test_document, FailureCodes.get_descriptions()) as ctx:
        ctx.logger.info("Starting example tests")

        failure_code = FailureCodes.NO_FAILURE

        if failure_code == FailureCodes.NO_FAILURE and cellConfig.get("enable_intentional_fail", False):
            ctx.set_banner("Running intentional test fail...", "info", BannerState.SHOWING)
            ctx.logger.info("Starting test: Intentional test fail")
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
                cellConfig.get("ping_url", "https://www.google.com"),
                cellConfig.get("num_pings", 5),
                cellConfig.get("ping_interval", 1.0),
            )
            ctx.logger.info(rc.__dict__)
            if rc.failure_code != FailureCodes.NO_FAILURE:
                ctx.logger.info("Test failed with failure code: %s", rc.failure_code)
                failure_code = rc.failure_code
            else:
                ctx.record_values(rc.return_value)
            ctx.logger.info("Test completed: %s", rc.return_value)

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
            ctx.logger.info("Test completed: %s", rc.return_value)

        if failure_code == FailureCodes.NO_FAILURE:
            ctx.logger.info("Starting test: Checking disk speed")
            min_mbps = cellConfig.get("min_write_speed_mbps", 10)
            num_test_files = cellConfig.get("num_test_files", 5)
            rc = disk_test("Storage Test", "Save data", min_mbps, num_test_files)
            if rc.failure_code != FailureCodes.NO_FAILURE:
                failure_code = rc.failure_code
            else:
                ctx.record_values(rc.return_value)
            ctx.logger.info("Test completed: %s Failure code: %s", rc.return_value, rc.failure_code)

        if failure_code == FailureCodes.NO_FAILURE and cellConfig.get(
            "enable_camera_test", True
        ):
            ctx.logger.info("Starting test: Taking picture")
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
                cellConfig.get("cpu_stress_duration", 5),
            )
            if rc.failure_code != FailureCodes.NO_FAILURE:
                failure_code = rc.failure_code
            else:
                ctx.record_values(rc.return_value)
            ctx.logger.info("Test completed: %s Failure code: %s", rc.return_value, rc.failure_code)

        if failure_code == FailureCodes.NO_FAILURE:
            ctx.logger.info("Starting test: Getting screen resolution")
            rc = get_screen_resolution("Display Test", "Get screen resolution")
            if rc.failure_code != FailureCodes.NO_FAILURE:
                failure_code = rc.failure_code
            else:
                ctx.record_values(rc.return_value)
            ctx.logger.info("Test completed: %s Failure code: %s", rc.return_value, rc.failure_code)

        if failure_code == FailureCodes.NO_FAILURE and cellConfig.get(
            "battery_test_enable", True
        ):
            ctx.logger.info("Starting test: Checking battery status")
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
            "battery_test_enable": False,
            "cpu_stress_duration": 5,
            "cpu_usage_range": {"max": 100, "min": 1},
            "drive_letter": "C",
            "enable_camera_test": False,
            "min_write_speed_mbps": 50,
            "num_test_files": 10,
            "ping_url": "https://www.google.com",
            "write_speed_mbps": {"max": 10000, "min": 50},
            "enable_intentional_fail": False,
        },
        "_cell_settings_obj": {
            "not_used_in_this_example": "This is not used in this example",
        },
    }
    example_flow(test_document, "DEV")
