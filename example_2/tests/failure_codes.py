from onnyx.failure import FailureCode, BaseFailureCodes


class FailureCodes(FailureCode):
    # Include base failure codes
    NO_FAILURE = BaseFailureCodes.NO_FAILURE
    EXCEPTION = BaseFailureCodes.EXCEPTION
    
    # Test-specific failure codes
    DEVICE_NOT_FOUND = (-100, "Tasmota device not found")
    CONNECTION_ERROR = (-101, "Failed to connect to device")
    FIRMWARE_ERROR = (-102, "Firmware version check failed")
    RELAY_ERROR = (-103, "Relay operation failed")
    OSCILLOSCOPE_ERROR = (-104, "Oscilloscope error")
    MEASUREMENT_ERROR = (-105, "Measurement error")
    WAVEFORM_ERROR = (-106, "Waveform analysis error")
    AC_FREQUENCY_ERROR = (-107, "AC frequency out of acceptable range")
    AC_VOLTAGE_ERROR = (-108, "AC voltage out of acceptable range")
    TIMING_MEASUREMENT_ERROR = (-109, "Failed to obtain timing measurements")
    INVALID_TIMING_DATA = (-110, "Invalid timing measurement data received")
    DUTY_CYCLE_ERROR = (-111, "Duty cycle out of acceptable range")
    VOLTAGE_STABILITY_ERROR = (-112, "Voltage stability out of acceptable range")
    MEASUREMENT_PROCESSING_ERROR = (-113, "Error processing measurement data")
    CONFIGURATION_ERROR = (-114, "Configuration error") 