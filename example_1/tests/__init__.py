# Export all test functions and FailureCodes for easy importing
from .failure_codes import FailureCodes
from .system_tests import check_system_dependencies
from .network_tests import check_internet_connection
from .storage_tests import is_drive_present, disk_test
from .hardware_tests import take_picture, get_screen_resolution, check_battery_status
from .performance_tests import cpu_stress_test

__all__ = [
    "FailureCodes",
    "check_system_dependencies",
    "check_internet_connection",
    "is_drive_present",
    "disk_test",
    "take_picture",
    "get_screen_resolution",
    "check_battery_status",
    "cpu_stress_test",
]