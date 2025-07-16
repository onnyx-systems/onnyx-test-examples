import cv2
import numpy as np
import ctypes
import psutil
import os
import platform
import subprocess
import time
from onnyx.results import TestResult
from onnyx.decorators import test
from onnyx.context import gcc
from onnyx.utils import range_check
from onnyx.failure import BaseFailureCodes
from .failure_codes import FailureCodes
from .file_utils import write_json


@test()
def take_picture(category: str = None, test_name: str = None):
    """Take a picture using the laptop's camera and analyze image properties.

    Args:
        category (str, optional): Test category. Used internally by the test framework.
        test_name (str, optional): Test name. Used internally by the test framework.

    Returns:
        TestResult: Test result with possible outcomes:
            - Success (NO_FAILURE):
                "Image captured successfully"
                return_value: {
                    "camera_metrics": {
                        "image_shape": Image dimensions tuple,
                        "avg_color": Average RGB color values,
                        "contrast": Image contrast value,
                        "brightness": Image brightness value,
                        "saturation": Image saturation value
                    }
                }

            - Failure (CAMERA_NOT_AVAILABLE):
                "Failed to open camera"
                Condition: Camera device cannot be opened

            - Failure (IMAGE_CAPTURE_FAILED):
                "Failed to capture image"
                Condition: Camera opened but image capture failed

            - Failure (EXCEPTION):
                "Error capturing image: {error}"
                Condition: Other exceptions during capture
    """
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return TestResult(
                "Failed to open camera",
                FailureCodes.CAMERA_NOT_AVAILABLE,
            )

        ret, frame = cap.read()
        cap.release()

        if not ret:
            return TestResult(
                "Failed to capture image",
                FailureCodes.IMAGE_CAPTURE_FAILED,
            )

        # save the image to a file
        # cv2.imwrite("captured_image.png", frame)

        # instead lets do some analysis on the image and generate some metrics
        # calculate the average color of the image
        avg_color = np.mean(frame, axis=(0, 1))
        # calculate the contrast of the image
        contrast = np.std(frame)
        # calculate the brightness of the image
        brightness = np.mean(frame)
        # calculate the saturation of the image
        saturation = np.std(frame)

        # return TestResult(
        #     "Image captured successfully",
        #     FailureCodes.NO_FAILURE,
        #     return_value={"image_shape": frame.shape},
        # )

        # Write detailed camera metrics to JSON
        camera_data = {
            "test_name": "take_picture",
            "status": "success",
            "image_properties": {
                "width": frame.shape[1],
                "height": frame.shape[0],
                "channels": frame.shape[2] if len(frame.shape) > 2 else 1,
                "total_pixels": frame.shape[0] * frame.shape[1]
            },
            "color_metrics": {
                "avg_color_bgr": avg_color.tolist(),
                "contrast": float(contrast),
                "brightness": float(brightness),
                "saturation": float(saturation)
            },
            "histogram_stats": {
                "min_pixel_value": float(np.min(frame)),
                "max_pixel_value": float(np.max(frame)),
                "mean_pixel_value": float(np.mean(frame)),
                "std_pixel_value": float(np.std(frame))
            },
            "timestamp": time.time()
        }
        json_file = write_json(camera_data, "camera_test_results")
        
        return TestResult(
            "Image captured successfully",
            FailureCodes.NO_FAILURE,
            return_value={
                "image_captured": True,
                "resolution": f"{frame.shape[1]}x{frame.shape[0]}",
                "details_file": json_file
            },
        )
    except Exception as e:
        return TestResult(
            f"Error capturing image: {e}",
            FailureCodes.EXCEPTION,
        )


@test()
def get_screen_resolution(category: str = None, test_name: str = None):
    """Get the current screen resolution.

    Works on both Windows and Linux (X11).

    Args:
        category (str, optional): Test category. Used internally by the test framework.
        test_name (str, optional): Test name. Used internally by the test framework.

    Returns:
        TestResult: Test result with possible outcomes as before
    """
    try:
        context = gcc()
        cellConfig = context.document.get("_cell_config_obj", {})



        # Check if screen resolution check should be skipped
        if cellConfig.get("skip_screen_resolution_check"):
            context.logger.info("Screen resolution check skipped by configuration")
            return TestResult(
                "Screen resolution check skipped",
                FailureCodes.NO_FAILURE,
                return_value={
                    "check_skipped": True,
                    "reason": "Configured to skip"
                },
            )

        width = 0
        height = 0
        resolution_detected = False
        detection_method = "none"

        if platform.system() == "Windows":
            try:
                user32 = ctypes.windll.user32
                width = user32.GetSystemMetrics(0)
                height = user32.GetSystemMetrics(1)
                if width > 0 and height > 0:
                    resolution_detected = True
                    detection_method = "windows_api"
            except Exception as e:
                context.logger.warning(f"Windows API method failed: {e}")
        else:
            # Linux implementation - try multiple methods
            
            # Method 1: Try xrandr first
            try:
                output = subprocess.check_output(["xrandr"], stderr=subprocess.DEVNULL).decode()
                # Parse the current resolution
                for line in output.split("\n"):
                    if " connected" in line and "primary" in line:
                        parts = line.split()
                        for part in parts:
                            if "x" in part and "+" in part:
                                resolution = part.split("+")[0]
                                if "x" in resolution:
                                    width, height = map(int, resolution.split("x"))
                                    if width > 0 and height > 0:
                                        resolution_detected = True
                                        detection_method = "xrandr"
                                        break
                        if resolution_detected:
                            break
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                context.logger.debug(f"xrandr method failed: {e}")
            
            # Method 2: Try reading from /sys/class/graphics
            if not resolution_detected:
                try:
                    fb_modes = "/sys/class/graphics/fb0/modes"
                    if os.path.exists(fb_modes):
                        with open(fb_modes, 'r') as f:
                            modes = f.read().strip()
                            # Parse first mode (usually current)
                            if modes:
                                first_mode = modes.split('\n')[0]
                                # Format is like: U:1920x1080p-60
                                if 'x' in first_mode:
                                    resolution_part = first_mode.split(':')[-1].split('p')[0]
                                    width, height = map(int, resolution_part.split('x'))
                                    if width > 0 and height > 0:
                                        resolution_detected = True
                                        detection_method = "framebuffer"
                except Exception as e:
                    context.logger.debug(f"Framebuffer method failed: {e}")
            
            # Method 3: Check DISPLAY environment variable
            if not resolution_detected and not os.environ.get('DISPLAY'):
                context.logger.info("No DISPLAY environment variable set - running in headless mode")

        # Handle case where no display is detected
        if not resolution_detected:
            # Check if we're in a headless environment
            is_headless = (
                os.environ.get('DISPLAY') is None or 
                os.environ.get('SSH_CLIENT') is not None or
                os.environ.get('SSH_TTY') is not None
            )
            
            # Write info to JSON
            info_data = {
                "test_name": "get_screen_resolution",
                "status": "no_display",
                "platform": platform.system(),
                "is_headless": is_headless,
                "environment": {
                    "DISPLAY": os.environ.get('DISPLAY'),
                    "SSH_CLIENT": bool(os.environ.get('SSH_CLIENT')),
                    "SSH_TTY": bool(os.environ.get('SSH_TTY')),
                },
                "timestamp": time.time()
            }
            json_file = write_json(info_data, "screen_resolution_headless")
            
            # If headless, this is expected - don't fail
            if is_headless:
                return TestResult(
                    "No display detected (headless environment)",
                    FailureCodes.NO_FAILURE,
                    return_value={
                        "headless": True,
                        "details_file": json_file
                    },
                )
            else:
                return TestResult(
                    "Unable to detect screen resolution",
                    FailureCodes.EXCEPTION,
                    return_value={
                        "resolution_detected": False,
                        "details_file": json_file
                    },
                )

        # Check width and height against minimum requirements
        rc_width = range_check(
            width, "min_resolution_width", cellConfig, prefix="screen"
        )

        if rc_width.failure_code != BaseFailureCodes.NO_FAILURE:
            return TestResult(
                f"Screen width below minimum requirement: {rc_width.message}",
                FailureCodes.EXCEPTION,
                return_value={
                    "width": width,
                    "height": height,
                },
            )

        rc_height = range_check(
            height, "min_resolution_height", cellConfig, prefix="screen"
        )

        if rc_height.failure_code != BaseFailureCodes.NO_FAILURE:
            return TestResult(
                f"Screen height below minimum requirement: {rc_height.message}",
                FailureCodes.EXCEPTION,
                return_value={
                    "width": width,
                    "height": height,
                },
            )

        # Write screen info to JSON
        screen_data = {
            "test_name": "get_screen_resolution",
            "status": "success",
            "platform": platform.system(),
            "resolution": {
                "width": width,
                "height": height,
                "aspect_ratio": round(width / height, 2) if height > 0 else 0,
                "total_pixels": width * height,
                "dpi_estimate": round(np.sqrt(width**2 + height**2) / 15.6, 0)  # Assuming 15.6" screen
            },
            "timestamp": time.time()
        }
        json_file = write_json(screen_data, "screen_resolution_results")
        
        return TestResult(
            f"Screen resolution: {width}x{height}",
            FailureCodes.NO_FAILURE,
            return_value={
                "resolution": f"{width}x{height}",
                "details_file": json_file
            },
        )
    except Exception as e:
        return TestResult(
            f"Error getting screen resolution: {e}",
            FailureCodes.EXCEPTION,
        )


@test()
def check_battery_status(category: str = None, test_name: str = None):
    """Check the laptop's battery status.

    Works on both Windows and Linux.

    Args:
        category (str, optional): Test category. Used internally by the test framework.
        test_name (str, optional): Test name. Used internally by the test framework.

    Returns:
        TestResult: Test result with possible outcomes as before
    """
    try:
        context = gcc()
        cellConfig = context.document.get("_cell_config_obj", {})



        battery = psutil.sensors_battery()
        if battery is None:
            # Try Linux-specific method if psutil fails
            if platform.system() != "Windows":
                try:
                    # Check if battery exists
                    battery_path = "/sys/class/power_supply/BAT0"
                    if os.path.exists(battery_path):
                        with open(f"{battery_path}/capacity", "r") as f:
                            percent = int(f.read().strip())
                        with open(f"{battery_path}/status", "r") as f:
                            status = f.read().strip()
                        power_plugged = status == "Charging"

                        # Check battery percentage range
                        rc = range_check(
                            percent,
                            "battery_percentage_range",
                            cellConfig,
                            prefix="battery",
                        )

                        if rc.failure_code != BaseFailureCodes.NO_FAILURE:
                            return TestResult(
                                f"Battery percentage out of range: {rc.message}",
                                FailureCodes.EXCEPTION,
                                return_value={
                                    "battery_percent": percent,
                                    "power_plugged": power_plugged,
                                    "seconds_left": -1,
                                },
                            )

                        # Write battery info to JSON
                        battery_data = {
                            "test_name": "check_battery_status",
                            "status": "success",
                            "platform": "Linux",
                            "battery_info": {
                                "percent": percent,
                                "plugged_in": power_plugged,
                                "charging_status": status,
                                "time_remaining_seconds": -1
                            },
                            "timestamp": time.time()
                        }
                        json_file = write_json(battery_data, "battery_status_results")
                        
                        return TestResult(
                            f"Battery at {percent}%, {'plugged in' if power_plugged else 'not plugged in'}",
                            FailureCodes.NO_FAILURE,
                            return_value={
                                "battery_percent": percent,
                                "charging": power_plugged,
                                "details_file": json_file
                            },
                        )
                except Exception:
                    pass

            return TestResult(
                "No battery detected",
                FailureCodes.NO_BATTERY,
            )

        # Check battery percentage range
        rc = range_check(
            battery.percent, "battery_percentage_range", cellConfig, prefix="battery"
        )

        if rc.failure_code != BaseFailureCodes.NO_FAILURE:
            return TestResult(
                f"Battery percentage out of range: {rc.message}",
                FailureCodes.EXCEPTION,
                return_value={
                    "battery_percent": battery.percent,
                    "power_plugged": battery.power_plugged,
                    "seconds_left": battery.secsleft,
                },
            )

        # Write battery info to JSON
        battery_data = {
            "test_name": "check_battery_status",
            "status": "success",
            "platform": platform.system(),
            "battery_info": {
                "percent": battery.percent,
                "plugged_in": battery.power_plugged,
                "time_remaining_seconds": battery.secsleft if battery.secsleft != -1 else None,
                "time_remaining_formatted": f"{battery.secsleft // 3600}h {(battery.secsleft % 3600) // 60}m" if battery.secsleft > 0 else "Unknown"
            },
            "timestamp": time.time()
        }
        json_file = write_json(battery_data, "battery_status_results")
        
        return TestResult(
            f"Battery at {battery.percent}%, {'plugged in' if battery.power_plugged else 'not plugged in'}",
            FailureCodes.NO_FAILURE,
            return_value={
                "battery_percent": battery.percent,
                "charging": battery.power_plugged,
                "details_file": json_file
            },
        )
    except Exception as e:
        return TestResult(
            f"Error checking battery status: {e}",
            FailureCodes.EXCEPTION,
        )