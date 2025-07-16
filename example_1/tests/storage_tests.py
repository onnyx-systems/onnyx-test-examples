import os
import time
import platform
import subprocess
from onnyx.results import TestResult
from onnyx.decorators import test
from onnyx.context import gcc
from onnyx.utils import range_check_list
from onnyx.failure import BaseFailureCodes
from .failure_codes import FailureCodes
from .file_utils import write_csv, write_json


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
                # check=True,
            )
            drives_present = result.stdout.strip().split("\n")

            if drive_letter in drives_present:
                # Write drive info to JSON
                drive_info = {
                    "platform": "Windows",
                    "requested_drive": drive_letter,
                    "drive_found": True,
                    "all_drives": drives_present,
                    "timestamp": time.time()
                }
                json_file = write_json(drive_info, "drive_check_success")
                
                return TestResult(
                    f"Drive {drive_letter}: is present",
                    return_value={
                        "drive_present": True,
                        "drive_count": len(drives_present),
                        "details_file": json_file
                    },
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
                ["df", "-h"], capture_output=True, text=True,
            )
            mounts = result.stdout.strip().split("\n")[1:]  # Skip header
            drives_present = [line.split()[-1] for line in mounts]

            if os.path.exists(mount_point) and mount_point in drives_present:
                # Write mount info to JSON
                mount_info = {
                    "platform": "Linux",
                    "requested_mount": mount_point,
                    "mount_found": True,
                    "all_mounts": drives_present,
                    "timestamp": time.time()
                }
                json_file = write_json(mount_info, "mount_check_success")
                
                return TestResult(
                    f"Mount point {mount_point} is present",
                    return_value={
                        "mount_present": True,
                        "mount_count": len(drives_present),
                        "details_file": json_file
                    },
                )

        # If we get here, the drive/mount point wasn't found
        path_name = (
            "Drive " + drive_letter
            if platform.system() == "Windows"
            else "Mount point " + mount_point
        )
        
        # Write failure info to JSON
        failure_info = {
            "platform": platform.system(),
            "requested_path": drive_letter if platform.system() == "Windows" else mount_point,
            "path_found": False,
            "available_paths": drives_present,
            "timestamp": time.time()
        }
        json_file = write_json(failure_info, "drive_check_failure")
        
        return TestResult(
            f"{path_name} is not present",
            FailureCodes.DRIVE_NOT_PRESENT,
            return_value={
                "path_present": False,
                "available_count": len(drives_present),
                "details_file": json_file
            },
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



        results = []
        write_speeds = []

        # Increase test file size to 100MB for more accurate measurements
        TEST_FILE_SIZE_MB = 100
        data = os.urandom(1024 * 1024 * TEST_FILE_SIZE_MB)  # Create test data once

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

        # Write detailed results to CSV
        if results:
            csv_file = write_csv(results, "disk_test_results")
        
        if not write_speeds:
            # Write failure details to JSON
            failure_info = {
                "test_name": "disk_test",
                "error": "All write speed measurements were 0 MB/s",
                "possible_causes": [
                    "Insufficient disk permissions",
                    "No available disk space",
                    "Disk write errors"
                ],
                "test_results": results,
                "timestamp": time.time()
            }
            json_file = write_json(failure_info, "disk_test_failure")
            
            return TestResult(
                "All write speed measurements were 0 MB/s. Check disk permissions and space.",
                FailureCodes.ERROR_SAVING_DATA,
                return_value={
                    "all_failed": True,
                    "details_file": json_file
                },
            )

        # Check write speeds against range using write_speed_mbps config
        rc = range_check_list(
            write_speeds, "write_speed_mbps", cellConfig, prefix="disk_test"
        )

        if rc.failure_code != BaseFailureCodes.NO_FAILURE:
            # Write failure details to JSON
            failure_info = {
                "test_name": "disk_test",
                "error": f"Write speed out of range: {rc.message}",
                "write_speeds": write_speeds,
                "average_speed_mbps": sum(write_speeds) / len(write_speeds),
                "min_speed_mbps": min(write_speeds),
                "max_speed_mbps": max(write_speeds),
                "expected_range": cellConfig.get("write_speed_mbps"),
                "test_results": results,
                "timestamp": time.time()
            }
            json_file = write_json(failure_info, "disk_test_speed_failure")
            
            return TestResult(
                f"Write speed out of range: {rc.message}",
                FailureCodes.WRITE_SPEED_BELOW_MIN,
                return_value={
                    "average_speed_mbps": round(sum(write_speeds) / len(write_speeds), 2),
                    "out_of_range": True,
                    "details_file": json_file
                },
            )

        avg_speed = sum(write_speeds) / len(write_speeds)
        
        # Write success summary to JSON
        summary = {
            "test_name": "disk_test",
            "status": "success",
            "num_files_tested": num_files,
            "file_size_mb": TEST_FILE_SIZE_MB,
            "average_speed_mbps": round(avg_speed, 2),
            "min_speed_mbps": round(min(write_speeds), 2),
            "max_speed_mbps": round(max(write_speeds), 2),
            "total_data_written_mb": TEST_FILE_SIZE_MB * num_files,
            "test_results": results,
            "timestamp": time.time()
        }
        json_file = write_json(summary, "disk_test_summary")
        
        return TestResult(
            f"Data saved successfully. Average write speed: {avg_speed:.2f} MB/s",
            FailureCodes.NO_FAILURE,
            return_value={
                "average_speed_mbps": round(avg_speed, 2),
                "files_tested": num_files,
                "details_file": json_file
            },
        )
    except Exception as e:
        return TestResult(
            f"Error saving data: {e}",
            FailureCodes.ERROR_SAVING_DATA,
        )