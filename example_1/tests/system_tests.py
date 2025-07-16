import platform
import subprocess
from shutil import which
import psutil
import cv2
import time
from onnyx.results import TestResult
from onnyx.decorators import test
from .failure_codes import FailureCodes
from .file_utils import write_json


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

    # Write detailed dependency report to JSON
    dependency_report = {
        "test_name": "check_system_dependencies",
        "platform": platform.system(),
        "platform_version": platform.version(),
        "python_version": platform.python_version(),
        "status": "failed" if missing else "success",
        "total_dependencies_checked": len(dependencies),
        "dependencies_found": len([d for d in dependencies.values() if d["installed"]]),
        "dependencies_missing": len(missing),
        "dependencies": dependencies,
        "missing_list": missing,
        "timestamp": time.time()
    }
    json_file = write_json(dependency_report, "system_dependencies_report")
    
    if missing:
        return TestResult(
            f"Missing required dependencies: {', '.join(missing)}",
            FailureCodes.MISSING_DEPENDENCIES,
            return_value={
                "missing_count": len(missing),
                "missing_list": missing,
                "details_file": json_file
            },
        )

    return TestResult(
        "All required dependencies are installed",
        return_value={
            "all_installed": True,
            "total_checked": len(dependencies),
            "details_file": json_file
        },
    )