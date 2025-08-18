from onnyx.failure import FailureCode, BaseFailureCodes


class FailureCodes(FailureCode):
    # Include base failure codes
    NO_FAILURE = BaseFailureCodes.NO_FAILURE
    EXCEPTION = BaseFailureCodes.EXCEPTION
    
    # Test-specific failure codes
    DEVICE_NOT_FOUND = (-200, "Minimal firmware device not found")
    CONNECTION_ERROR = (-201, "Failed to connect to device")
    FIRMWARE_ERROR = (-202, "Firmware version check failed")
    RELAY_ERROR = (-203, "Relay operation failed")
    OSCILLOSCOPE_ERROR = (-204, "Oscilloscope error")
    OSCILLOSCOPE_MEASUREMENT_FAILED = (-205, "Oscilloscope measurement failed")
    BURN_IN_START_FAILED = (-206, "Failed to start burn-in test")
    BURN_IN_PROGRESS_ERROR = (-207, "Burn-in progress error")
    BURN_IN_TIMEOUT = (-208, "Burn-in test timeout")
    BUTTON_TEST_FAILED = (-209, "Button test failed")
    TIMING_TEST_FAILED = (-210, "Timing test failed")
    TIMING_MEASUREMENT_ERROR = (-211, "Timing measurement error")
    FIRMWARE_NOT_DETECTED = (-212, "Minimal firmware not detected")
    CONFIGURATION_ERROR = (-213, "Configuration error")