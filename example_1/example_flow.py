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
    interactive_test,
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

        if failure_code == FailureCodes.NO_FAILURE:
            rc = check_system_dependencies("Init", "Check system dependencies")
            if rc.failure_code != FailureCodes.NO_FAILURE:
                ctx.logger.error("Missing required dependencies")
                failure_code = rc.failure_code
            else:
                ctx.record_values(rc.return_value)

        if failure_code == FailureCodes.NO_FAILURE:
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

        # clear the banner
        ctx.set_banner("", "info", BannerState.HIDDEN)

        if failure_code == FailureCodes.NO_FAILURE:
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

        if failure_code == FailureCodes.NO_FAILURE and cellConfig.get(
            "enable_interactive_test", True
        ):
            # First interactive test - Yes/No question
            rc = interactive_test(
                "Interactive Test 1",
                "First example of prompting",
                buttons=["Yes", "No", "Abort"],
                message="Is the device powered on?",
            )
            if rc.failure_code != FailureCodes.NO_FAILURE:
                failure_code = rc.failure_code
            else:
                ctx.record_values(rc.return_value)

            # Second interactive test - Color selection
            if failure_code == FailureCodes.NO_FAILURE:
                rc = interactive_test(
                    "Interactive Test 2",
                    "Second example of prompting",
                    buttons=["Red", "Green", "Blue", "Abort"],
                    message="Select the color displayed on the device screen",
                )
                if rc.failure_code != FailureCodes.NO_FAILURE:
                    failure_code = rc.failure_code
                else:
                    ctx.record_values(rc.return_value)

        if failure_code == FailureCodes.NO_FAILURE:
            min_mbps = cellConfig.get("min_write_speed_mbps", 10)
            num_test_files = cellConfig.get("num_test_files", 5)
            rc = disk_test("Storage Test", "Save data", min_mbps, num_test_files)
            if rc.failure_code != FailureCodes.NO_FAILURE:
                failure_code = rc.failure_code
            else:
                ctx.record_values(rc.return_value)

        if failure_code == FailureCodes.NO_FAILURE and cellConfig.get(
            "enable_camera_test", True
        ):
            rc = take_picture("Camera Test", "Take picture")
            if rc.failure_code != FailureCodes.NO_FAILURE:
                failure_code = rc.failure_code
            else:
                ctx.record_values(rc.return_value)

        if failure_code == FailureCodes.NO_FAILURE:
            rc = cpu_stress_test(
                "CPU Test",
                "Perform CPU stress test",
                cellConfig.get("cpu_stress_duration", 5),
            )
            if rc.failure_code != FailureCodes.NO_FAILURE:
                failure_code = rc.failure_code
            else:
                ctx.record_values(rc.return_value)

        # clear the banner
        ctx.set_banner("", "info", BannerState.HIDDEN)

        if failure_code == FailureCodes.NO_FAILURE:
            rc = get_screen_resolution("Display Test", "Get screen resolution")
            if rc.failure_code != FailureCodes.NO_FAILURE:
                failure_code = rc.failure_code
            else:
                ctx.record_values(rc.return_value)

        if failure_code == FailureCodes.NO_FAILURE and cellConfig.get(
            "battery_test_enable", True
        ):
            rc = check_battery_status("Battery Test", "Check battery status")
            if rc.failure_code != FailureCodes.NO_FAILURE:
                failure_code = rc.failure_code
            else:
                ctx.record_values(rc.return_value)

        ctx.wrap_up(failure_code)


if __name__ == "__main__":
    test_document = {
        "_id": "0",  # this can be anything
        "_cell_config_obj": {
            "battery_test_enable": False,
            "cpu_stress_duration": 5,
            "cpu_usage_range": {"max": 100, "min": 1},
            "drive_letter": "C",
            "enable_camera_test": True,
            "enable_interactive_test": True,
            "min_write_speed_mbps": 100,
            "num_test_files": 10,
            "ping_url": "https://www.google.com",
            "write_speed_mbps": {"max": 10000, "min": 500},
        },
        "_cell_settings_obj": {
            "not_used_in_this_example": "This is not used in this example",
        },
    }
    example_flow(test_document, "DEV")
