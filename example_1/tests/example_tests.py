import requests
import os
import time
from onnyx.failure import FailureCode, BaseFailureCodes
from onnyx.results import TestResult
from onnyx.decorators import test
from onnyx.context import gcc
from onnyx.mqtt import BannerState
from onnyx.utils import range_check_list, range_check
import subprocess
import cv2
import numpy as np
import ctypes
import psutil
import csv
from datetime import datetime
from typing import List
import platform
from shutil import which
from onnyx.context import ButtonResponse


class FailureCodes(FailureCode):
    # Include base failure codes
    NO_FAILURE = BaseFailureCodes.NO_FAILURE
    EXCEPTION = BaseFailureCodes.EXCEPTION

    # Add specific failure codes
    INTERNET_CONNECTION_FAILED = (-1, "Internet connection failed")
    DRIVE_NOT_PRESENT = (-2, "Drive not present")
    ERROR_CREATING_DATA = (-3, "Error creating data")
    ERROR_SAVING_DATA = (-4, "Error saving data")
    NO_BATTERY = (-5, "No battery detected")
    CAMERA_NOT_AVAILABLE = (-6, "Camera not available")
    IMAGE_CAPTURE_FAILED = (-7, "Image capture failed")
    WRITE_SPEED_BELOW_MIN = (-8, "Write speed below minimum threshold")
    MISSING_DEPENDENCIES = (-9, "Missing system dependencies")
    CPU_PERFORMANCE_FAILED = (-10, "CPU performance below requirements")
    INPUT_TIMEOUT = (-11, "Input request timed out")


@test()
def check_internet_connection(
    category: str = None,
    test_name: str = None,
    url: str = "https://www.google.com",
    num_pings: int = 5,
    interval: float = 1.0,
):
    """Check if there's an active internet connection and log ping times.

    Args:
        category (str, optional): Test category. Used internally by the test framework.
        test_name (str, optional): Test name. Used internally by the test framework.
        url (str): The URL to test the connection against. Defaults to "https://www.google.com".
        num_pings (int): Number of pings to perform. Defaults to 5.
        interval (float): Time between pings in seconds. Defaults to 1.0.

    Returns:
        TestResult: Test result with possible outcomes:
            - Success (NO_FAILURE):
                "Internet connection successful. Average ping time: {avg_ping:.2f} ms"
                return_value: {
                    "ping_results": List of ping results,
                    "average_ping_ms": Average ping time in milliseconds
                }

            - Failure (INTERNET_CONNECTION_FAILED):
                "Internet connection failed"
                return_value: {
                    "ping_results": List of ping results up to failure
                }
                Condition: Connection error during ping attempts
    """
    context = gcc()  # Get current context
    ping_results = []
    csv_path = "ping_results.csv"

    # Only update banner at start and end of test
    context.set_banner("Starting internet connection test", "info", BannerState.SHOWING)

    # Create/open CSV file with headers if it doesn't exist
    file_exists = os.path.isfile(csv_path)
    with open(csv_path, "a", newline="") as csvfile:
        fieldnames = ["timestamp", "url", "ping_time_ms", "status"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        for i in range(num_pings):
            try:
                start_time = time.time()
                response = requests.get(url, timeout=5)
                end_time = time.time()
                ping_time_ms = (end_time - start_time) * 1000  # Convert to milliseconds
                status = "success"

                result = {
                    "timestamp": datetime.now().isoformat(),
                    "url": url,
                    "ping_time_ms": round(ping_time_ms, 2),
                    "status": status,
                }

                writer.writerow(result)
                ping_results.append(result)

                if interval > 0 and i < num_pings - 1:  # Don't sleep after last ping
                    time.sleep(interval)

            except requests.ConnectionError:
                context.set_banner(
                    "Internet connection failed!", "error", BannerState.SHOWING
                )
                result = {
                    "timestamp": datetime.now().isoformat(),
                    "url": url,
                    "ping_time_ms": None,
                    "status": "failed",
                }
                writer.writerow(result)
                ping_results.append(result)

                return TestResult(
                    "Internet connection failed",
                    FailureCodes.INTERNET_CONNECTION_FAILED,
                    return_value={"ping_results": ping_results},
                )

    # Calculate average ping time from successful pings
    successful_pings = [
        p["ping_time_ms"] for p in ping_results if p["status"] == "success"
    ]
    avg_ping = sum(successful_pings) / len(successful_pings) if successful_pings else 0

    # Clear the banner on success
    context.set_banner("", state=BannerState.HIDDEN)

    return TestResult(
        f"Internet connection successful. Average ping time: {avg_ping:.2f} ms",
        return_value={"ping_results": ping_results, "average_ping_ms": avg_ping},
    )


@test()
def is_drive_present(
    category: str = None, test_name: str = None, drive_letter: str = None
):
    """Check if a specified drive/mount point is present.

    On Windows, checks for drive letter.
    On Linux, checks for mount point in /media or custom path.

    Args:
        category (str, optional): Test category. Used internally by the test framework.
        test_name (str, optional): Test name. Used internally by the test framework.
        drive_letter (str, optional):
            Windows: drive letter to check (defaults to "C")
            Linux: mount point path (defaults to "/")

    Returns:
        TestResult: Test result with possible outcomes:
            - Success (NO_FAILURE):
                "Drive {drive_letter}: is present" or "Mount point {path} is present"
                return_value: {
                    "drives_present": List of available drives/mount points
                }

            - Failure (DRIVE_NOT_PRESENT):
                "Drive/mount point {path} is not present"
                return_value: {
                    "drives_present": List of available drives/mount points
                }

            - Failure (EXCEPTION):
                "Error checking drive presence: {error}"
                return_value: {
                    "error": Error message string
                }
    """
    try:
        if platform.system() == "Windows":
            # Use "C" as default for Windows
            drive_letter = drive_letter or "C"
            # Strip any path separators and take first character
            drive_letter = drive_letter.replace("/", "").replace("\\", "")[0].upper()

            ps_command = "Get-PSDrive -PSProvider 'FileSystem' | Select-Object -ExpandProperty Name"
            result = subprocess.run(
                ["powershell", "-Command", ps_command],
                capture_output=True,
                text=True,
                check=True,
            )
            drives_present = result.stdout.strip().split("\n")

            if drive_letter in drives_present:
                return TestResult(
                    f"Drive {drive_letter}: is present",
                    return_value={"drives_present": drives_present},
                )
        else:
            # Use "/" as default for Linux
            mount_point = drive_letter if drive_letter else "/"

            # If it looks like a Windows drive letter, use root instead
            if mount_point and (
                mount_point[0].isalpha()
                and (len(mount_point) == 1 or mount_point[1] == ":")
            ):
                mount_point = "/"

            result = subprocess.run(
                ["df", "-h"], capture_output=True, text=True, check=True
            )
            mounts = result.stdout.strip().split("\n")[1:]  # Skip header
            drives_present = [line.split()[-1] for line in mounts]

            if os.path.exists(mount_point) and mount_point in drives_present:
                return TestResult(
                    f"Mount point {mount_point} is present",
                    return_value={"drives_present": drives_present},
                )

        # If we get here, the drive/mount point wasn't found
        path_name = (
            "Drive " + drive_letter
            if platform.system() == "Windows"
            else "Mount point " + mount_point
        )
        return TestResult(
            f"{path_name} is not present",
            FailureCodes.DRIVE_NOT_PRESENT,
            return_value={"drives_present": drives_present},
        )

    except subprocess.CalledProcessError as e:
        return TestResult(
            f"Error checking drive presence: {e}",
            FailureCodes.EXCEPTION,
            return_value={"error": str(e)},
        )


@test()
def disk_test(
    category: str = None,
    test_name: str = None,
    min_mbps: float = 10.0,
    num_files: int = 5,
):
    """Save test files and measure write performance.

    Args:
        category (str, optional): Test category. Used internally by the test framework.
        test_name (str, optional): Test name. Used internally by the test framework.
        min_mbps (float): Minimum required write speed in MB/s.
        num_files (int): Number of files to write. Defaults to 5.

    Returns:
        TestResult: Test result with possible outcomes:
            - Success (NO_FAILURE):
                "Data saved successfully. Average write speed: {avg_speed:.2f} MB/s"
                return_value: {
                    "disk_test_results": List of per-file test results,
                    "write_speeds": List of write speeds in MB/s
                }

            - Failure (WRITE_SPEED_BELOW_MIN):
                "Write speed out of range: {message}"
                return_value: {
                    "disk_test_results": List of per-file test results,
                    "write_speeds": List of write speeds in MB/s
                }
                Condition: Write speeds outside configured range

            - Failure (ERROR_SAVING_DATA):
                "Error saving data: {error}"
                Condition: Exception during file operations
    """
    try:
        context = gcc()
        cellConfig = context.document.get("_cell_config_obj", {})

        # Use write_speed_mbps from cellConfig if available, otherwise create default range
        if not "write_speed_mbps" in cellConfig:
            cellConfig["write_speed_mbps"] = {
                "min": min_mbps,
                "max": 10000.0,
            }  # Up to 10GB/s

        results = []
        write_speeds = []
        csv_path = f"disk_test_results.csv"

        # Increase test file size to 100MB for more accurate measurements
        TEST_FILE_SIZE_MB = 100
        data = os.urandom(1024 * 1024 * TEST_FILE_SIZE_MB)  # Create test data once

        with open(csv_path, "w", newline="") as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(
                [
                    "File",
                    "Write Time (s)",
                    "Write Speed (MB/s)",
                    "File Size (MB)",
                    "Start Time",
                    "End Time",
                ]
            )

            for i in range(num_files):
                file_path = f"disk_test_file_{i+1}.dat"

                try:
                    # Ensure we start with a clean file
                    if os.path.exists(file_path):
                        os.remove(file_path)

                    # Get high precision time
                    start_time = time.perf_counter()

                    with open(file_path, "wb") as f:
                        f.write(data)
                        # Force flush to disk
                        f.flush()
                        os.fsync(f.fileno())

                    end_time = time.perf_counter()
                    write_time = end_time - start_time

                    # Verify file was written correctly
                    actual_size = os.path.getsize(file_path)
                    actual_size_mb = actual_size / (1024 * 1024)

                    if actual_size != len(data):
                        context.logger.error(
                            f"File size mismatch! Expected {TEST_FILE_SIZE_MB}MB, got {actual_size_mb:.2f}MB"
                        )
                        write_speed_mbps = 0
                    elif write_time <= 0:
                        context.logger.error(f"Invalid write time: {write_time}s")
                        write_speed_mbps = 0
                    else:
                        write_speed_mbps = TEST_FILE_SIZE_MB / write_time

                    # Log detailed timing info
                    context.logger.info(
                        f"File {i+1}: Size={actual_size_mb:.2f}MB, "
                        f"Time={write_time:.4f}s, Speed={write_speed_mbps:.2f}MB/s"
                    )

                    csvwriter.writerow(
                        [
                            file_path,
                            f"{write_time:.4f}",
                            f"{write_speed_mbps:.2f}",
                            f"{actual_size_mb:.2f}",
                            start_time,
                            end_time,
                        ]
                    )

                    results.append(
                        {
                            "file": file_path,
                            "write_time_seconds": write_time,
                            "write_speed_mbps": write_speed_mbps,
                            "file_size_mb": actual_size_mb,
                            "start_time": start_time,
                            "end_time": end_time,
                        }
                    )

                    if write_speed_mbps > 0:  # Only include non-zero speeds
                        write_speeds.append(write_speed_mbps)

                finally:
                    # Clean up test file
                    try:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                    except Exception as e:
                        context.logger.error(f"Error cleaning up file {file_path}: {e}")

        if not write_speeds:
            return TestResult(
                "All write speed measurements were 0 MB/s. Check disk permissions and space.",
                FailureCodes.ERROR_SAVING_DATA,
                return_value={
                    "disk_test_results": results,
                    "write_speeds": write_speeds,
                },
            )

        # Check write speeds against range using write_speed_mbps config
        rc = range_check_list(
            write_speeds, "write_speed_mbps", cellConfig, prefix="disk_test"
        )

        if rc.failure_code != BaseFailureCodes.NO_FAILURE:
            return TestResult(
                f"Write speed out of range: {rc.message}",
                FailureCodes.WRITE_SPEED_BELOW_MIN,
                return_value={
                    "disk_test_results": results,
                    "write_speeds": write_speeds,
                },
            )

        avg_speed = sum(write_speeds) / len(write_speeds)
        return TestResult(
            f"Data saved successfully. Average write speed: {avg_speed:.2f} MB/s",
            FailureCodes.NO_FAILURE,
            return_value={
                "disk_test_results": results,
                "write_speeds": write_speeds,
            },
        )
    except Exception as e:
        return TestResult(
            f"Error saving data: {e}",
            FailureCodes.ERROR_SAVING_DATA,
        )


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

        return TestResult(
            "Image captured successfully",
            FailureCodes.NO_FAILURE,
            return_value={
                "camera_metrics": {
                    "image_shape": frame.shape,
                    "avg_color": avg_color.tolist(),
                    "contrast": contrast,
                    "brightness": brightness,
                    "saturation": saturation,
                }
            },
        )
    except Exception as e:
        return TestResult(
            f"Error capturing image: {e}",
            FailureCodes.EXCEPTION,
        )


@test()
def cpu_stress_test(
    category: str = None, test_name: str = None, duration_seconds: int = 5
):
    """Perform a CPU stress test for a specified duration.
    Uses a computationally intensive single-threaded operation to stress test the CPU.

    Args:
        category (str, optional): Test category. Used internally by the test framework.
        test_name (str, optional): Test name. Used internally by the test framework.
        duration_seconds (int): Duration of the stress test in seconds.

    Returns:
        TestResult: Test result with possible outcomes:
            - Success (NO_FAILURE):
                "CPU stress test completed successfully"
                return_value: {
                    "duration_seconds": Actual test duration,
                    "operations_completed": Number of operations performed,
                    "initial_cpu_percent": Initial CPU usage percentage,
                    "final_cpu_percent": Final CPU usage percentage,
                    "cpu_cores": Number of CPU cores,
                    "cpu_freq": CPU frequency information dictionary,
                    "cpu_percentages": List of CPU usage percentages
                }

            - Failure (CPU_PERFORMANCE_FAILED):
                "CPU usage out of expected range: {message}"
                return_value: Same as success
                Condition: CPU usage outside configured range

            - Failure (EXCEPTION):
                "Error during CPU stress test: {error}"
                Condition: Exception during test execution
    """
    try:
        context = gcc()
        start_time = time.time()
        end_time = start_time + duration_seconds
        operations_count = 0
        last_banner_update = start_time
        BANNER_UPDATE_INTERVAL = 0.5  # Update banner every 0.5 seconds
        cpu_percentages = []  # List to store CPU percentages for range check

        # Get initial CPU usage
        initial_cpu_percent = psutil.cpu_percent(interval=0.1)
        context.set_banner(
            f"Starting CPU stress test ({duration_seconds}s)",
            "info",
            BannerState.SHOWING,
        )

        # Run CPU-intensive calculations
        while time.time() < end_time:
            # Matrix operations and other CPU-intensive calculations
            for _ in range(10000):
                _ = sum(i * i for i in range(100))
            operations_count += 1

            # Update banner less frequently
            current_time = time.time()
            if current_time - last_banner_update >= BANNER_UPDATE_INTERVAL:
                elapsed = current_time - start_time
                remaining = max(0, duration_seconds - elapsed)
                current_cpu = psutil.cpu_percent(interval=0)
                cpu_percentages.append(current_cpu)  # Store CPU percentage
                context.set_banner(
                    f"CPU Test: {remaining:.1f}s remaining | CPU Usage: {current_cpu}%",
                    "warning" if current_cpu > 80 else "info",
                    BannerState.SHOWING,
                )
                last_banner_update = current_time

        actual_duration = time.time() - start_time

        # Get final CPU usage
        final_cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_percentages.append(final_cpu_percent)

        # Check CPU usage range
        cellConfig = context.document.get("_cell_config_obj", {})
        if not "cpu_usage_range" in cellConfig:
            cellConfig["cpu_usage_range"] = {"min": 10.0, "max": 100.0}  # Default range

        rc = range_check_list(
            cpu_percentages, "cpu_usage_range", cellConfig, prefix="cpu_stress"
        )

        return_value = {
            "duration_seconds": actual_duration,
            "operations_completed": operations_count,
            "initial_cpu_percent": initial_cpu_percent,
            "final_cpu_percent": final_cpu_percent,
            "cpu_cores": psutil.cpu_count(),
            "cpu_freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
            "cpu_percentages": cpu_percentages,
        }

        if rc.failure_code != BaseFailureCodes.NO_FAILURE:
            return TestResult(
                f"CPU usage out of expected range: {rc.message}",
                FailureCodes.CPU_PERFORMANCE_FAILED,
                return_value=return_value,
            )

        return TestResult(
            f"CPU stress test completed successfully",
            FailureCodes.NO_FAILURE,
            return_value=return_value,
        )
    except Exception as e:
        if "context" in locals():
            context.set_banner(
                f"CPU test failed: {str(e)}", "error", BannerState.SHOWING
            )
        return TestResult(
            f"Error during CPU stress test: {e}",
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

        # Set default ranges if not in config
        if not "min_resolution_width" in cellConfig:
            cellConfig["min_resolution_width"] = {"min": 1024, "max": 100000}
        if not "min_resolution_height" in cellConfig:
            cellConfig["min_resolution_height"] = {"min": 768, "max": 100000}

        if platform.system() == "Windows":
            user32 = ctypes.windll.user32
            width = user32.GetSystemMetrics(0)
            height = user32.GetSystemMetrics(1)
        else:
            # Linux implementation using xrandr
            try:
                output = subprocess.check_output(["xrandr"]).decode()
                # Parse the current resolution
                current = [line for line in output.split("\n") if " connected" in line][
                    0
                ]
                resolution = current.split()[2]
                if "x" in resolution:
                    width, height = map(int, resolution.split("x"))
                else:
                    # Fallback if primary method fails
                    width = height = 0
            except (subprocess.CalledProcessError, IndexError):
                # Fallback for systems without X11
                width = height = 0

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

        return TestResult(
            f"Screen resolution: {width}x{height}",
            FailureCodes.NO_FAILURE,
            return_value={
                "width": width,
                "height": height,
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

        # Set default ranges if not in config
        if not "battery_percentage_range" in cellConfig:
            cellConfig["battery_percentage_range"] = {"min": 10.0, "max": 100.0}
        if not "battery_voltage_range" in cellConfig:
            cellConfig["battery_voltage_range"] = {
                "min": 10.8,
                "max": 12.6,
            }  # Typical laptop battery range

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

                        return TestResult(
                            f"Battery at {percent}%, {'plugged in' if power_plugged else 'not plugged in'}",
                            FailureCodes.NO_FAILURE,
                            return_value={
                                "battery_percent": percent,
                                "power_plugged": power_plugged,
                                "seconds_left": -1,
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

        return TestResult(
            f"Battery at {battery.percent}%, {'plugged in' if battery.power_plugged else 'not plugged in'}",
            FailureCodes.NO_FAILURE,
            return_value={
                "battery_percent": battery.percent,
                "power_plugged": battery.power_plugged,
                "seconds_left": battery.secsleft,
            },
        )
    except Exception as e:
        return TestResult(
            f"Error checking battery status: {e}",
            FailureCodes.EXCEPTION,
        )


@test()
def check_system_dependencies(category: str = None, test_name: str = None):
    """Check if all required system dependencies are installed.

    Verifies presence of required system tools and libraries for both Windows and Linux.

    Args:
        category (str, optional): Test category. Used internally by the test framework.
        test_name (str, optional): Test name. Used internally by the test framework.

    Returns:
        TestResult: Test result with possible outcomes:
            - Success (NO_FAILURE):
                "All required dependencies are installed"
                return_value: {
                    "dependencies": Dict of dependency names and their status
                }

            - Failure (MISSING_DEPENDENCIES):
                "Missing required dependencies: {missing_deps}"
                return_value: {
                    "dependencies": Dict of dependency names and their status,
                    "missing": List of missing dependencies
                }
    """
    dependencies = {}
    missing = []

    # Common dependencies
    common_deps = {
        "python-opencv": lambda: cv2.__version__,
        "psutil": lambda: psutil.__version__,
    }

    # Platform specific dependencies
    if platform.system() == "Windows":
        platform_deps = {
            "powershell": lambda: subprocess.run(
                ["powershell", "-Command", "$PSVersionTable.PSVersion.ToString()"],
                capture_output=True,
                text=True,
            ).stdout.strip(),
        }
    else:  # Linux
        platform_deps = {
            "xrandr": lambda: subprocess.run(
                ["xrandr", "--version"], capture_output=True, text=True
            ).stdout.split("\n")[0],
            "df": lambda: which("df") is not None,
        }

    # Check common dependencies
    for dep_name, check_func in common_deps.items():
        try:
            result = check_func()
            dependencies[dep_name] = {
                "installed": True,
                "version": str(result) if result is not True else "Available",
            }
        except Exception as e:
            dependencies[dep_name] = {"installed": False, "error": str(e)}
            missing.append(dep_name)

    # Check platform specific dependencies
    for dep_name, check_func in platform_deps.items():
        try:
            result = check_func()
            dependencies[dep_name] = {
                "installed": True,
                "version": str(result) if result is not True else "Available",
            }
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            dependencies[dep_name] = {"installed": False, "error": str(e)}
            missing.append(dep_name)

    # Check camera access
    try:
        cap = cv2.VideoCapture(0)
        camera_available = cap.isOpened()
        cap.release()
        dependencies["camera"] = {
            "installed": camera_available,
            "version": "Available" if camera_available else "Not available",
        }
        if not camera_available:
            missing.append("camera")
    except Exception as e:
        dependencies["camera"] = {"installed": False, "error": str(e)}
        missing.append("camera")

    if missing:
        return TestResult(
            f"Missing required dependencies: {', '.join(missing)}",
            FailureCodes.MISSING_DEPENDENCIES,
            return_value={"dependencies": dependencies, "missing": missing},
        )

    return TestResult(
        "All required dependencies are installed",
        return_value={"dependencies": dependencies},
    )


@test()
def interactive_test(
    category: str = None,
    test_name: str = None,
    buttons: List[str] = None,
    message: str = None,
):
    """Test that demonstrates the interactive functionality

    Args:
        category (str, optional): Test category. Used internally by the test framework.
        test_name (str, optional): Test name. Used internally by the test framework.
        buttons (List[str], optional): List of button options. Defaults to ["A", "B", "Abort"]
        message (str, optional): Message to show to user. Defaults to "Select an option"
    """
    context = gcc()

    # Use default values if not provided
    if buttons is None:
        buttons = ["A", "B", "Abort"]
    if message is None:
        message = "Select an option"

    # Show some buttons and wait for response
    response = context.wait_for_input(
        buttons=buttons,
        message=message,
        timeout=30.0,
    )

    if response == ButtonResponse.TIMEOUT:
        return TestResult(
            "Test timed out waiting for user input",
            FailureCodes.INPUT_TIMEOUT,
            return_value={
                "timeout_duration": 30.0,
                "available_buttons": buttons,
            },
        )
    elif response == ButtonResponse.CANCELLED:
        return TestResult(
            "Test was cancelled by user",
            FailureCodes.EXCEPTION,
            return_value={"cancelled": True},
        )
    elif response == "Abort":
        return TestResult(
            "Test aborted by user",
            FailureCodes.EXCEPTION,
            return_value={"aborted": True},
        )

    # Continue with test...
    return TestResult(
        "Test completed successfully",
        FailureCodes.NO_FAILURE,
        return_value={"user_response": response},
    )
