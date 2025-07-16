import time
import serial.tools.list_ports
import re
from typing import Dict, Any, Optional, List, Tuple
import numpy as np
import random

from onnyx.context import gcc
from onnyx.decorators import test
from onnyx.failure import BaseFailureCodes, FailureCode
from onnyx.results import TestResult
from onnyx.utils import range_check_list, range_check

from .tasmota_driver import TasmotaSerialDriver
from .file_utils import write_measurements_csv, save_numpy_array
from .scope import capture_relay_transition
from .failure_codes import FailureCodes

def parse_version(version_str: str) -> Tuple[int, ...]:
    """Parse version string into tuple of integers.
    
    Extracts numeric version components from strings like:
    - "9.5.0"
    - "9.5.0(release-tasmota)"
    - "v9.5.0"
    
    Args:
        version_str: Version string to parse
        
    Returns:
        Tuple of version components as integers
    """
    # Extract version numbers using regex
    matches = re.findall(r'\d+', version_str)
    if not matches:
        return (0, 0, 0)  # Default version if no numbers found
    return tuple(map(int, matches[:3]))  # Take first 3 numbers

def should_simulate_failure(failure_code: int) -> bool:
    """Helper function to determine if we should simulate a failure.
    
    Args:
        failure_code: The failure code that would be returned
        
    Returns:
        bool: True if we should simulate this failure
    """
    context = gcc()
    failure_chance = context.document.get("_cell_config_obj", {}).get("enable_intentional_fail")
    
    # If failure_chance is 0 or not set, never simulate failures
    if not failure_chance:
        return False

    fail = random.random() < failure_chance
    if fail:
        context.logger.warning(f"Simulating failure: {failure_code}")
    return fail

def check_required_config(config: Dict[str, Any], required_keys: List[str]) -> Optional[TestResult]:
    """Helper function to check if required configuration keys are present.
    
    Args:
        config: Configuration dictionary to check
        required_keys: List of required configuration keys
        
    Returns:
        TestResult with CONFIGURATION_ERROR if any keys are missing, None if all present
    """
    for key in required_keys:
        if key not in config:
            return TestResult(
                f"Missing required configuration: {key}",
                FailureCodes.CONFIGURATION_ERROR
            )
    return None

@test()
def detect_tasmota_serial_port(
    category: str,
    test_name: str,
    port: str = None,
    baudrate: int = 115200
) -> TestResult:
    """Detect and connect to Tasmota device.
    
    Args:
        category: Test category for reporting and organization
        test_name: Name of this specific test instance
        port: Serial port (auto-detect if None)
        baudrate: Serial baudrate
        
    Returns:
        TestResult with device info containing:
            - port: The connected serial port
            - device_info: Dictionary of device information
    """
    # If port not specified, try to auto-detect FTDI devices
    if not port:
        ftdi_ports = []
        for p in serial.tools.list_ports.comports():
            # Check if manufacturer exists and contains FTDI
            if p.manufacturer and ("FTDI" in p.manufacturer or "ftdi" in p.manufacturer.lower()):
                ftdi_ports.append(p.device)
                
        if not ftdi_ports or should_simulate_failure(FailureCodes.DEVICE_NOT_FOUND.value):
            return TestResult(
                "No FTDI devices found",
                FailureCodes.DEVICE_NOT_FOUND
            )
            
        # Try each FTDI port
        for test_port in ftdi_ports:
            driver = TasmotaSerialDriver(test_port, baudrate)
            if not driver.connect() or should_simulate_failure(FailureCodes.CONNECTION_ERROR.value):
                continue
                
            # Get device info to verify it's a Tasmota device
            device_info = driver.get_device_info()
            if device_info and not should_simulate_failure(FailureCodes.CONNECTION_ERROR.value):
                return TestResult(
                    f"Connected to Tasmota device on {test_port}",
                    FailureCodes.NO_FAILURE,
                    return_value={
                        "port": test_port,
                        "device_info": device_info
                    }
                )
            driver.disconnect()
                
        return TestResult(
            "No Tasmota devices found on FTDI ports",
            FailureCodes.DEVICE_NOT_FOUND
        )
    
    # Try specified port
    driver = TasmotaSerialDriver(port, baudrate)
    if not driver.connect() or should_simulate_failure(FailureCodes.CONNECTION_ERROR.value):
        return TestResult(
            f"Failed to connect to {port}",
            FailureCodes.CONNECTION_ERROR
        )
        
    device_info = driver.get_device_info()
    if device_info and not should_simulate_failure(FailureCodes.CONNECTION_ERROR.value):
        return TestResult(
            f"Connected to Tasmota device on {port}",
            FailureCodes.NO_FAILURE,
            return_value={
                "port": port,
                "device_info": device_info
            }
        )
    
    driver.disconnect()
    return TestResult(
        f"Device on {port} is not a Tasmota device",
        FailureCodes.DEVICE_NOT_FOUND
    )

@test()
def check_firmware_version(
    category: str,
    test_name: str,
    port: str,
    min_version: str
) -> TestResult:
    """Check Tasmota firmware version.
    
    Args:
        category: Test category for reporting and organization
        test_name: Name of this specific test instance
        port: Serial port
        min_version: Minimum required version
        
    Returns:
        TestResult with firmware version
    """
    driver = TasmotaSerialDriver(port)
    if not driver.connect() or should_simulate_failure(FailureCodes.CONNECTION_ERROR.value):
        return TestResult(
            f"Failed to connect to {port}",
            FailureCodes.CONNECTION_ERROR
        )
        
    try:
        version = driver.get_firmware_version()
        if not version or should_simulate_failure(FailureCodes.FIRMWARE_ERROR.value):
            return TestResult(
                "Failed to get firmware version",
                FailureCodes.FIRMWARE_ERROR
            )
            
        # Parse version strings
        current = parse_version(version)
        minimum = parse_version(min_version)
        
        if current >= minimum and not should_simulate_failure(FailureCodes.FIRMWARE_ERROR.value):
            return TestResult(
                f"Firmware version {version} meets minimum {min_version}",
                FailureCodes.NO_FAILURE,
                return_value={"firmware_version": version}
            )
        else:
            return TestResult(
                f"Firmware version {version} below minimum {min_version}",
                FailureCodes.FIRMWARE_ERROR
            )
            
    finally:
        driver.disconnect()




@test()
def test_relay_response(
    category: str,
    test_name: str,
    serial_port: str,
    relay_number: int = 1
) -> TestResult:
    """Test relay response characteristics using oscilloscope measurements.
    
    Args:
        category: Test category for reporting and organization
        test_name: Name of this specific test instance
        serial_port: Serial port for Tasmota device
        relay_number: Relay number to test (default: 1)
        
    Returns:
        TestResult: Test result with measurement data
    """
    logger = gcc().logger
    logger.info(f"Starting {test_name}")
    
    try:
        # Get oscilloscope from context
        context = gcc()
        oscilloscope = context.document.get("_oscilloscope")
        if not oscilloscope or should_simulate_failure(FailureCodes.OSCILLOSCOPE_ERROR.value):
            return TestResult(
                "No oscilloscope available - run connect_oscilloscope first",
                FailureCodes.OSCILLOSCOPE_ERROR
            )
        
        # Get cell config for range checks
        cellConfig = context.document.get("_cell_config_obj")
        
        # Check required range configurations
        config_check = check_required_config(cellConfig, [
            "ac_frequency_range",
            "ac_voltage_range"
        ])
        if config_check:
            return config_check
        
        # Connect to Tasmota device first
        logger.info("Connecting to Tasmota device...")
        tasmota = TasmotaSerialDriver(serial_port)
        if not tasmota.connect() or should_simulate_failure(FailureCodes.CONNECTION_ERROR.value):
            return TestResult(
                f"Failed to connect to Tasmota device on {serial_port}",
                FailureCodes.CONNECTION_ERROR
            )
            
        try:
            # Turn relay ON to verify AC signal
            logger.info(f"Turning relay {relay_number} ON to verify AC signal")
            if not tasmota.set_power(True, relay_number) or should_simulate_failure(FailureCodes.RELAY_ERROR.value):
                return TestResult(
                    f"Failed to turn on relay {relay_number}",
                    FailureCodes.RELAY_ERROR
                )
            time.sleep(0.5)  # Reduced: Let relay settle (was 1s)
            
            # Try to find AC signal with auto-scale
            logger.info("Auto-scaling to find AC signal...")
            oscilloscope.send_command(":AUToscale")
            time.sleep(3)  # Reduced: Give auto-scale time to work (was 5s)
            
            # Restore our vertical scale and set up measurements in a batch
            oscilloscope.send_command(":CHANnel1:SCALe 50")
            
            # Setup all basic measurements at once
            oscilloscope.send_command(":MEASure:CLEar ALL")
            oscilloscope.send_command(":MEASure:ITEM FREQuency,CHANnel1;:MEASure:ITEM VPP,CHANnel1;:MEASure:ITEM VRMS,CHANnel1")
            
            # Force trigger and wait for stable signal
            oscilloscope.send_command(":TFORce")
            time.sleep(2)  # Reduced: Wait for stable signal (was 3s)
            
            # Get measurements with retries
            max_retries = 3
            freq_values = []
            vrms_values = []
            vpp_values = []
            
            for attempt in range(max_retries):
                # Get all measurements with a batch query when possible
                time.sleep(0.3)  # Short delay before measurements
                
                # Get measurements individually as batch queries might not be supported by all scopes
                freq = oscilloscope.query(":MEASure:ITEM? FREQuency,CHANnel1")
                vpp = oscilloscope.query(":MEASure:ITEM? VPP,CHANnel1")
                vrms = oscilloscope.query(":MEASure:ITEM? VRMS,CHANnel1")
                
                try:
                    freq_val = float(freq)
                    vpp_val = float(vpp)
                    vrms_val = float(vrms)
                    
                    # Check if values are valid (not 9.9e37)
                    if freq_val >= 9.9e37: freq_val = 0
                    if vpp_val >= 9.9e37: vpp_val = 0
                    if vrms_val >= 9.9e37: vrms_val = 0
                    
                    # Check if we have valid measurements
                    if freq_val > 0 and vrms_val > 0:
                        freq_values.append(freq_val)
                        vrms_values.append(vrms_val)
                        vpp_values.append(vpp_val)
                        logger.info(f"Attempt {attempt + 1}: Found signal - {freq_val:.1f} Hz, {vrms_val:.1f} Vrms")
                        
                        # Early exit: Once we have 2 good measurements, that's enough (was 3)
                        if len(freq_values) >= 2:
                            break
                    else:
                        logger.warning(f"Attempt {attempt + 1}: No valid measurements")
                        if attempt < max_retries - 1:
                            # Try forcing trigger again
                            oscilloscope.send_command(":TFORce")
                            time.sleep(1.5)  # Reduced wait time (was 3s)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Attempt {attempt + 1}: Error reading measurements - {str(e)}")
                    if attempt < max_retries - 1:
                        time.sleep(0.5)  # Reduced wait time (was 1s)
            
            # Check if we got any valid measurements
            if not freq_values or not vrms_values or should_simulate_failure(FailureCodes.MEASUREMENT_ERROR.value):
                return TestResult(
                    "Failed to get valid measurements",
                    FailureCodes.MEASUREMENT_ERROR
                )
            
            # Use range_check_list for frequency and voltage measurements
            # Check AC frequency
            rc = range_check_list(freq_values, "ac_frequency_range", cellConfig, prefix="ac_line")
            if rc.failure_code != BaseFailureCodes.NO_FAILURE:
                measurements = {
                    'frequency_hz': freq_values,
                    'vpp_volts': vpp_values,
                    'vrms_volts': vrms_values
                }
                context.record_values(measurements)
                write_measurements_csv(measurements, "relay_measurements.csv")
                return TestResult(
                    f"AC frequency out of range: {rc.message}",
                    FailureCodes.AC_FREQUENCY_ERROR,
                    return_value=measurements
                )
                
            # Check AC voltage
            rc = range_check_list(vrms_values, "ac_voltage_range", cellConfig, prefix="ac_line")
            if rc.failure_code != BaseFailureCodes.NO_FAILURE:
                measurements = {
                    'frequency_hz': freq_values,
                    'vpp_volts': vpp_values,
                    'vrms_volts': vrms_values
                }
                context.record_values(measurements)
                write_measurements_csv(measurements, "relay_measurements.csv")
                return TestResult(
                    f"AC voltage out of range: {rc.message}",
                    FailureCodes.AC_VOLTAGE_ERROR,
                    return_value=measurements
                )
                
            # Measuring power quality metrics
            logger.info("Measuring power quality metrics...")
            
            # Set up all power quality measurements in one batch
            oscilloscope.send_command(":MEASure:CLEar ALL;:MEASure:ITEM PERIOD,CHANnel1;:MEASure:ITEM PWIDTH,CHANnel1;:MEASure:ITEM NWIDTH,CHANnel1")
            
            # Force trigger and wait for stable measurements
            oscilloscope.send_command(":TFORce")
            time.sleep(1.5)  # Reduced: Wait for stable measurements (was 2s)
            
            # Get all measurements with a small delay
            time.sleep(0.2)
            period_response = oscilloscope.query(":MEASure:ITEM? PERIOD,CHANnel1").strip()
            pwidth_response = oscilloscope.query(":MEASure:ITEM? PWIDTH,CHANnel1").strip()
            nwidth_response = oscilloscope.query(":MEASure:ITEM? NWIDTH,CHANnel1").strip()
            
            # Check for invalid measurements
            if (not period_response or not pwidth_response or not nwidth_response or 
                should_simulate_failure(FailureCodes.MEASUREMENT_ERROR.value)):
                measurements = {
                    'frequency_hz': freq_values,
                    'vpp_volts': vpp_values,
                    'vrms_volts': vrms_values,
                    'error': 'Failed to get timing measurements'
                }
                context.record_values(measurements)
                write_measurements_csv(measurements, "relay_measurements.csv")
                return TestResult(
                    "Failed to get timing measurements",
                    FailureCodes.TIMING_MEASUREMENT_ERROR,
                    return_value=measurements
                )
            
            try:
                period = float(period_response)
                pos_width = float(pwidth_response)
                neg_width = float(nwidth_response)
                
                # Check for invalid values (9.9e37)
                if period >= 9.9e37 or pos_width >= 9.9e37 or neg_width >= 9.9e37:
                    measurements = {
                        'frequency_hz': freq_values,
                        'vpp_volts': vpp_values,
                        'vrms_volts': vrms_values,
                        'period': period,
                        'pos_width': pos_width,
                        'neg_width': neg_width,
                        'error': 'Invalid timing measurements'
                    }
                    context.record_values(measurements)
                    write_measurements_csv(measurements, "relay_measurements.csv")
                    return TestResult(
                        "Invalid timing measurements received",
                        FailureCodes.INVALID_TIMING_DATA,
                        return_value=measurements
                    )
                
                # Calculate duty cycle from positive and negative widths
                total_time = pos_width + neg_width
                duty_cycle = (pos_width / total_time) * 100 if total_time > 0 else 0
                
                # Calculate voltage stability
                voltage_stability = {
                    'mean': np.mean(vrms_values),
                    'std_dev': np.std(vrms_values),
                    'min': np.min(vrms_values),
                    'max': np.max(vrms_values),
                    'variation_coefficient': np.std(vrms_values) / np.mean(vrms_values) * 100
                }
                
                # Check required range configurations
                config_check = check_required_config(cellConfig, [
                    "duty_cycle_range",
                    "voltage_stability_range"
                ])
                if config_check:
                    return config_check
                
                # Record all measurements
                measurements = {
                    'frequency_hz': freq_values,
                    'vpp_volts': vpp_values,
                    'vrms_volts': vrms_values,
                    'duty_cycle': duty_cycle,
                    'period': period,
                    'pos_width': pos_width,
                    'neg_width': neg_width,
                    'voltage_stability': voltage_stability
                }
                context.record_values(measurements)
                
                # Check duty cycle
                rc = range_check(duty_cycle, "duty_cycle_range", cellConfig, prefix="power_quality")
                if rc.failure_code != BaseFailureCodes.NO_FAILURE:
                    write_measurements_csv(measurements, "relay_measurements.csv")
                    return TestResult(
                        f"Duty cycle out of range: {duty_cycle}%",
                        FailureCodes.DUTY_CYCLE_ERROR,
                        return_value=measurements
                    )
                
                # Check voltage stability
                rc = range_check(voltage_stability['variation_coefficient'], 
                               "voltage_stability_range", 
                               cellConfig, 
                               prefix="power_quality")
                if rc.failure_code != BaseFailureCodes.NO_FAILURE:
                    write_measurements_csv(measurements, "relay_measurements.csv")
                    return TestResult(
                        f"Voltage stability out of range: {voltage_stability['variation_coefficient']}% variation",
                        FailureCodes.VOLTAGE_STABILITY_ERROR,
                        return_value=measurements
                    )
                
                logger.info(f"Verified AC signal - Frequency: {sum(freq_values)/len(freq_values):.1f} Hz, "
                          f"Voltage: {sum(vrms_values)/len(vrms_values):.1f} Vrms")
                logger.info(f"Power Quality - Duty Cycle: {duty_cycle:.1f}%, Period: {period:.2e}s, "
                          f"Voltage Variation: {voltage_stability['variation_coefficient']:.2f}%")
                
                # Turn relay off to prepare for turn-on capture
                if not tasmota.set_power(False, relay_number) or should_simulate_failure(FailureCodes.RELAY_ERROR.value):
                    return TestResult(
                        f"Failed to turn off relay {relay_number}",
                        FailureCodes.RELAY_ERROR,
                        return_value=measurements
                    )
                time.sleep(0.5)  # Reduced: Let relay settle (was 1s)
                
                # Capture turn-on transition
                turn_on_waveform = capture_relay_transition(
                    oscilloscope, tasmota, relay_number, True, logger
                )
                if turn_on_waveform is None:
                    # If we got a timeout waiting for trigger, it's likely a relay actuation failure
                    return TestResult(
                        "Failed to capture relay turn-on transition - relay may have failed to actuate",
                        FailureCodes.RELAY_ERROR,
                        return_value=measurements
                    )
                
                # Save turn-on waveform data
                context.record_values({'turn_on_waveform': turn_on_waveform})
                
                # Save waveform to CSV for analysis
                saved_path = save_numpy_array(turn_on_waveform, 'relay_turn_on.csv', 
                                            delimiter=',', header='time_s,voltage_v')
                logger.info(f"Saved relay turn-on waveform to CSV: {saved_path}")
                
                # Return measurements
                return TestResult(
                    "Successfully captured relay turn-on transition",
                    FailureCodes.NO_FAILURE,
                    return_value=measurements
                )
                
            except Exception as e:
                measurements = {
                    'frequency_hz': freq_values,
                    'vpp_volts': vpp_values,
                    'vrms_volts': vrms_values,
                    'error': str(e)
                }
                context.record_values(measurements)
                write_measurements_csv(measurements, "relay_measurements.csv")
                logger.error(f"Error processing measurements: {str(e)}")
                return TestResult(
                    f"Error processing measurements: {str(e)}",
                    FailureCodes.MEASUREMENT_PROCESSING_ERROR,
                    return_value=measurements
                )
            
        finally:
            tasmota.disconnect()
        
    except Exception as e:
        logger.error(f"Error testing relay response: {str(e)}")
        return TestResult(
            f"Failed to test relay response: {str(e)}",
            FailureCodes.MEASUREMENT_ERROR
        ) 