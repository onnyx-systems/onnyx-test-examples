from onnyx.failure import FailureCode, BaseFailureCodes


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
    CONFIGURATION_ERROR = (-11, "Configuration error")