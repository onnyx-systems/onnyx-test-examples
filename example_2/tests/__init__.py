# Export all test functions and FailureCodes for easy importing
from .failure_codes import FailureCodes
from .relay_tests import (
    detect_relay_serial_port,
    check_firmware_version,
    test_relay_response,
)
from .scope import (
    connect_oscilloscope,
    detect_oscilloscope,
)

__all__ = [
    "FailureCodes",
    "detect_relay_serial_port",
    "check_firmware_version",
    "test_relay_response",
    "connect_oscilloscope",
    "detect_oscilloscope",
]
