from enum import IntEnum
import time
import serial.tools.list_ports
import os
import socket
import re
import concurrent.futures
from typing import Dict, Any, Optional, List, Tuple, Set
import ipaddress
import numpy as np
import csv
import random

from onnyx.context import gcc
from onnyx.decorators import test
from onnyx.failure import BaseFailureCodes, FailureCode
from onnyx.results import TestResult
from onnyx.utils import range_check_list, range_check

from .tasmota_driver import TasmotaSerialDriver
from .rigol_driver import RigolOscilloscopeDriver
from .waveform_utils import analyze_waveform_file

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
    failure_chance = context.document.get("_cell_config_obj", {}).get("randomly_fail", 0.0)
    
    # If failure_chance is 0 or not set, never simulate failures
    if not failure_chance:
        return False

    fail = random.random() < failure_chance
    if fail:
        context.logger.warning(f"Simulating failure: {failure_code}")
    return fail

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

def scan_ip(ip: str, ports: List[int], timeout: float = 0.1) -> Optional[Dict[str, Any]]:
    """Scan a single IP address for Rigol oscilloscopes.
    
    Args:
        ip: IP address to scan
        ports: List of ports to try
        timeout: Socket timeout in seconds
        
    Returns:
        Dict with device info if found, None otherwise
    """
    context = gcc()
    context.logger.debug(f"Scanning {ip}")
    
    for port in ports:
        # First check if port is open
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect((ip, port))
            s.close()
            
            # Port is open, try to connect as oscilloscope
            scope = RigolOscilloscopeDriver(ip, port, logger=context.logger)
            if scope.connect():
                try:
                    idn = scope.get_idn()
                    if any(model in idn.upper() for model in [
                        "RIGOL", "DS1", "DS2", "DS4", "DS6", "DS7", "MSO5", "MSO7"
                    ]):
                        return {
                            "ip": ip,
                            "port": port,
                            "idn": idn
                        }
                finally:
                    scope.disconnect()
        except (socket.timeout, socket.error, OSError):
            continue
        except Exception as e:
            context.logger.debug(f"Error scanning {ip}:{port} - {str(e)}")
            continue
            
    return None

@test()
def detect_oscilloscope(
    category: str,
    test_name: str,
    ip_address: str = None,
    port: int = 5555,
    timeout: float = 1.0
) -> TestResult:
    """Check if a Rigol oscilloscope is available at the specified IP.
    
    Args:
        category: Test category for reporting and organization
        test_name: Name of this specific test instance
        ip_address: Oscilloscope IP address
        port: SCPI port (default: 5555)
        timeout: Connection timeout in seconds
        
    Returns:
        TestResult with oscilloscope info
    """
    context = gcc()
    
    # Require IP address
    if not ip_address:
        return TestResult(
            "No oscilloscope IP address provided",
            FailureCodes.OSCILLOSCOPE_ERROR
        )
    
    # Try to connect to oscilloscope
    try:
        # First check if port is open
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        
        try:
            s.connect((ip_address, port))
            s.close()
        except (socket.timeout, socket.error, OSError):
            return TestResult(
                f"Could not connect to {ip_address}:{port}",
                FailureCodes.OSCILLOSCOPE_ERROR
            )
            
        # Port is open, try to connect as oscilloscope
        scope = RigolOscilloscopeDriver(ip_address, port, logger=context.logger)
        if not scope.connect() or should_simulate_failure(FailureCodes.OSCILLOSCOPE_ERROR.value):
            return TestResult(
                f"Failed to connect to oscilloscope at {ip_address}",
                FailureCodes.OSCILLOSCOPE_ERROR
            )
            
        try:
            # Get device ID
            idn = scope.get_idn()
            
            # Check if it's a Rigol scope
            if any(model in idn.upper() for model in [
                "RIGOL", "DS1", "DS2", "DS4", "DS6", "DS7", "MSO5", "MSO7"
            ]) and not should_simulate_failure(FailureCodes.OSCILLOSCOPE_ERROR.value):
                context.logger.info(f"Found oscilloscope at {ip_address}: {idn}")
                return TestResult(
                    f"Found Rigol oscilloscope at {ip_address}",
                    FailureCodes.NO_FAILURE,
                    return_value={
                        "oscilloscope_ip": ip_address,
                        "oscilloscope_port": port,
                        "oscilloscope_idn": idn
                    }
                )
            else:
                context.logger.error(f"Device at {ip_address} is not a Rigol oscilloscope")
                context.logger.error(f"Device ID: {idn}")
                return TestResult(
                    f"Device at {ip_address} is not a Rigol oscilloscope",
                    FailureCodes.OSCILLOSCOPE_ERROR
                )
                
        finally:
            scope.disconnect()
            
    except Exception as e:
        context.logger.error(f"Error checking oscilloscope at {ip_address}: {str(e)}")
        return TestResult(
            f"Error checking oscilloscope at {ip_address}: {str(e)}",
            FailureCodes.OSCILLOSCOPE_ERROR
        )
        
    return TestResult(
        f"No Rigol oscilloscope found at {ip_address}",
        FailureCodes.OSCILLOSCOPE_ERROR
    )

@test()
def connect_oscilloscope(
    category: str,
    test_name: str,
    ip_address: str,
    port: int = 5555,
    timebase: float = 0.005  # Default to 5ms/div for 60Hz AC
) -> TestResult:
    """Connect to and configure the oscilloscope for AC line measurements.
    
    Args:
        category: Test category for reporting and organization
        test_name: Name of this specific test instance
        ip_address: IP address of the oscilloscope
        port: SCPI port (default: 5555)
        timebase: Timebase in seconds/div (default: 0.005 = 5ms/div)
        
    Returns:
        TestResult: Test result with oscilloscope settings
    """
    context = gcc()
    logger = context.logger
    logger.info(f"Starting {test_name}")
    
    try:
        # Connect to oscilloscope
        scope = RigolOscilloscopeDriver(ip_address, port, logger=logger)
        if not scope.connect():
            return TestResult(
                "Failed to connect to oscilloscope",
                FailureCodes.OSCILLOSCOPE_ERROR
            )
            
        # Get scope ID for verification
        scope_id = scope.get_idn()
        logger.info(f"Connected to oscilloscope: {scope_id}")
        
        # Store scope in context for other tests to use
        context.document["_oscilloscope"] = scope
        
        # Reset scope and stop acquisition
        scope.send_command("*RST")
        time.sleep(2)  # Give scope time to reset
        scope.send_command(":STOP")
        time.sleep(1)
        
        # Set timebase first (5ms/div shows ~3 cycles of 60Hz)
        logger.info("Setting timebase...")
        max_retries = 3
        for attempt in range(max_retries):
            scope.send_command(f":TIMebase:SCALe {timebase}")
            time.sleep(0.2)
            
            # Verify timebase
            actual_timebase = scope.query(":TIMebase:SCALe?")
            time.sleep(0.1)
            
            try:
                actual_value = float(actual_timebase)
                if abs(actual_value - timebase) <= timebase * 0.01:  # 1% tolerance
                    logger.info(f"Timebase set to {actual_value} s/div")
                    break
                else:
                    logger.warning(f"Timebase verification failed: wanted {timebase}, got {actual_value}")
                    if attempt < max_retries - 1:
                        time.sleep(0.5)
            except (ValueError, TypeError):
                if attempt < max_retries - 1:
                    time.sleep(0.5)
                    
        # Setup channel for AC line measurement
        logger.info("Setting up channel...")
        scope.send_command(":CHANnel1:DISPlay ON")
        time.sleep(0.1)
        scope.send_command(":CHANnel1:COUPling AC")
        time.sleep(0.1)
        
        # Configure probe settings
        scope.send_command(":CHANnel1:IMPedance ONEMeg")  # 1MΩ for voltage probe
        time.sleep(0.1)
        scope.send_command(":CHANnel1:PROBe 10")  # 10X probe
        time.sleep(0.1)
        scope.send_command(":CHANnel1:PROBe:BIAS 0")  # No DC bias
        time.sleep(0.1)
        
        # Set vertical scale (50V/div * 10X probe = 500V full scale)
        scope.send_command(":CHANnel1:SCALe 50")
        time.sleep(0.1)
        
        # Setup trigger for AC line
        logger.info("Setting up trigger...")
        scope.send_command(":TRIGger:MODE EDGE")
        time.sleep(0.1)
        scope.send_command(":TRIGger:EDGE:SOURce CHANnel1")
        time.sleep(0.1)
        scope.send_command(":TRIGger:EDGE:SLOPe POSitive")
        time.sleep(0.1)
        scope.send_command(":TRIGger:EDGE:LEVel 25")  # ~25V for 120VAC
        time.sleep(0.1)
        scope.send_command(":TRIGger:COUPling AC")
        time.sleep(0.1)
        scope.send_command(":TRIGger:SWEep NORMal")
        time.sleep(0.1)
        
        # Setup measurements
        logger.info("Setting up measurements...")
        scope.send_command(":MEASure:CLEar ALL")
        time.sleep(0.1)
        scope.send_command(":MEASure:ITEM FREQuency,CHANnel1")
        time.sleep(0.1)
        scope.send_command(":MEASure:ITEM VPP,CHANnel1")
        time.sleep(0.1)
        scope.send_command(":MEASure:ITEM VRMS,CHANnel1")
        time.sleep(0.1)
        
        # Start acquisition with force trigger
        logger.info("Starting acquisition...")
        scope.send_command(":RUN")
        time.sleep(0.1)
        scope.send_command(":TFORce")
        time.sleep(3)  # Wait for acquisition
        
        # Verify settings
        vscale = scope.query(":CHANnel1:SCALe?")
        tscale = scope.query(":TIMebase:SCALe?")
        logger.info(f"Final settings - Vertical: {float(vscale)}V/div, Timebase: {float(tscale)}s/div")
        
        # Return success with scope settings (not the scope object)
        return TestResult(
            "Successfully connected and configured oscilloscope",
            FailureCodes.NO_FAILURE,
            return_value={
                "scope_id": scope_id,
                "vertical_scale": float(vscale),
                "timebase": float(tscale)
            }
        )
        
    except Exception as e:
        logger.error(f"Error configuring oscilloscope: {str(e)}")
        if 'scope' in locals():
            scope.disconnect()
        return TestResult(
            f"Failed to configure oscilloscope: {str(e)}",
            FailureCodes.OSCILLOSCOPE_ERROR
        )

def capture_relay_transition(
    oscilloscope: RigolOscilloscopeDriver,
    tasmota: TasmotaSerialDriver,
    relay_number: int,
    turn_on: bool,
    logger
) -> Optional[np.ndarray]:
    """Capture relay transition waveform.
    
    Args:
        oscilloscope: Configured oscilloscope instance
        tasmota: Connected Tasmota device
        relay_number: Relay number to test
        turn_on: True to capture turn-on, False for turn-off
        logger: Logger instance
        
    Returns:
        Optional[np.ndarray]: Waveform data if captured successfully
    """
    try:
        # Get context to access config
        context = gcc()
        failure_chance = context.document.get("_cell_config_obj", {}).get("randomly_fail", 0.0)
        
        # Configure single trigger for relay test
        oscilloscope.send_command(":TRIGger:SWEep SINGle")
        time.sleep(0.1)
        
        # Arm trigger and wait for ready
        oscilloscope.send_command(":SINGle")
        time.sleep(1)
        
        # Toggle relay (unless simulating failure)
        action = "on" if turn_on else "off"
        logger.info(f"Turning relay {relay_number} {action}")
        
        if turn_on and failure_chance and random.random() < failure_chance:
            # Simulate mechanical failure by not actually turning on the relay
            logger.info("Simulating mechanical failure - relay did not actuate")
            time.sleep(0.1)
        else:
            if not tasmota.set_power(turn_on, relay_number):
                return None
            time.sleep(0.1)
        
        # Wait for trigger and capture
        timeout = 5  # seconds
        start_time = time.time()
        while time.time() - start_time < timeout:
            status = oscilloscope.query(":TRIGger:STATus?")
            if status.strip() == "STOP":
                logger.info(f"Captured relay {action} transition")
                break
            time.sleep(0.1)
        else:
            logger.warning(f"Timeout waiting for relay {action} transition capture")
            return None
        
        # Get waveform data
        return oscilloscope.capture_waveform(channel=1)
        
    except Exception as e:
        logger.error(f"Error in capture_relay_transition: {str(e)}")
        return None

def save_measurements_to_csv(measurements: dict, filename: str):
    """Save measurements to CSV file.
    
    Args:
        measurements: Dictionary of measurements
        filename: Output CSV filename
    """
    try:
        # Flatten nested dictionaries
        flat_data = {}
        for key, value in measurements.items():
            if isinstance(value, dict):
                for subkey, subvalue in value.items():
                    flat_data[f"{key}_{subkey}"] = subvalue
            elif isinstance(value, list):
                for i, val in enumerate(value):
                    flat_data[f"{key}_{i+1}"] = val
            else:
                flat_data[key] = value
        
        # Write to CSV
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=flat_data.keys())
            writer.writeheader()
            writer.writerow(flat_data)

        # Save the csv file for uploading to Onnyx
        gcc().record_file(filename)
            
    except Exception as e:
        gcc().logger.error(f"Error saving measurements to CSV: {str(e)}")

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
        cellConfig = context.document.get("_cell_config_obj", {})
        
        # Set default ranges if not in config
        if not "ac_frequency_range" in cellConfig:
            cellConfig["ac_frequency_range"] = {"min": 55.0, "max": 65.0}  # 60Hz ±5Hz
        if not "ac_voltage_range" in cellConfig:
            cellConfig["ac_voltage_range"] = {"min": 100.0, "max": 130.0}  # 120V ±10%
        
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
            time.sleep(1)  # Let relay settle
            
            # Try to find AC signal with auto-scale
            logger.info("Auto-scaling to find AC signal...")
            oscilloscope.send_command(":AUToscale")
            time.sleep(5)  # Give auto-scale time to work
            
            # Restore our vertical scale
            oscilloscope.send_command(":CHANnel1:SCALe 50")
            time.sleep(0.1)
            
            # Force trigger and wait for stable signal
            oscilloscope.send_command(":TFORce")
            time.sleep(3)
            
            # Get measurements with retries
            max_retries = 3
            freq_values = []
            vrms_values = []
            vpp_values = []
            
            for attempt in range(max_retries):
                # Get measurements
                freq = oscilloscope.query(":MEASure:ITEM? FREQuency,CHANnel1")
                time.sleep(0.2)  # Longer delay between measurements
                vpp = oscilloscope.query(":MEASure:ITEM? VPP,CHANnel1")
                time.sleep(0.2)
                vrms = oscilloscope.query(":MEASure:ITEM? VRMS,CHANnel1")
                time.sleep(0.2)
                
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
                        if len(freq_values) >= 3:  # Get at least 3 good measurements
                            break
                    else:
                        logger.warning(f"Attempt {attempt + 1}: No valid measurements")
                        if attempt < max_retries - 1:
                            # Try forcing trigger again
                            oscilloscope.send_command(":TFORce")
                            time.sleep(3)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Attempt {attempt + 1}: Error reading measurements - {str(e)}")
                    if attempt < max_retries - 1:
                        time.sleep(1)
            
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
                save_measurements_to_csv(measurements, "relay_measurements.csv")
                return TestResult(
                    f"AC frequency out of range: {rc.message}",
                    FailureCodes.MEASUREMENT_ERROR,
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
                save_measurements_to_csv(measurements, "relay_measurements.csv")
                return TestResult(
                    f"AC voltage out of range: {rc.message}",
                    FailureCodes.MEASUREMENT_ERROR,
                    return_value=measurements
                )
                
            # Measuring power quality metrics
            logger.info("Measuring power quality metrics...")
            
            # Clear existing measurements
            oscilloscope.send_command(":MEASure:CLEar ALL")
            time.sleep(0.2)
            
            # Set up period and width measurements
            oscilloscope.send_command(":MEASure:ITEM PERIOD,CHANnel1")  # Period
            time.sleep(0.2)
            oscilloscope.send_command(":MEASure:ITEM PWIDTH,CHANnel1")  # Positive pulse width
            time.sleep(0.2)
            oscilloscope.send_command(":MEASure:ITEM NWIDTH,CHANnel1")  # Negative pulse width
            time.sleep(0.2)
            
            # Force trigger and wait for stable measurements
            oscilloscope.send_command(":TFORce")
            time.sleep(2)
            
            # Get measurements
            period_response = oscilloscope.query(":MEASure:ITEM? PERIOD,CHANnel1").strip()
            time.sleep(0.2)
            pwidth_response = oscilloscope.query(":MEASure:ITEM? PWIDTH,CHANnel1").strip()
            time.sleep(0.2)
            nwidth_response = oscilloscope.query(":MEASure:ITEM? NWIDTH,CHANnel1").strip()
            time.sleep(0.2)
            
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
                return TestResult(
                    "Failed to get timing measurements",
                    FailureCodes.MEASUREMENT_ERROR,
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
                    return TestResult(
                        "Invalid timing measurements received",
                        FailureCodes.MEASUREMENT_ERROR,
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
                
                # Set default ranges if not in config
                if not "duty_cycle_range" in cellConfig:
                    cellConfig["duty_cycle_range"] = {"min": 45.0, "max": 55.0}  # 50% ±5% for AC sine wave
                if not "voltage_stability_range" in cellConfig:
                    cellConfig["voltage_stability_range"] = {"min": 0.0, "max": 2.0}  # Max 2% variation
                
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
                    return TestResult(
                        f"Duty cycle out of range: {duty_cycle}%",
                        FailureCodes.MEASUREMENT_ERROR,
                        return_value=measurements
                    )
                
                # Check voltage stability
                rc = range_check(voltage_stability['variation_coefficient'], 
                               "voltage_stability_range", 
                               cellConfig, 
                               prefix="power_quality")
                if rc.failure_code != BaseFailureCodes.NO_FAILURE:
                    return TestResult(
                        f"Voltage stability out of range: {voltage_stability['variation_coefficient']}% variation",
                        FailureCodes.MEASUREMENT_ERROR,
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
                time.sleep(1)  # Let relay settle
                
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
                np.savetxt('relay_turn_on.csv', turn_on_waveform, delimiter=',', 
                         header='time_s,voltage_v', comments='')
                # Save the csv file for uploading to Onnyx
                gcc().record_file('relay_turn_on.csv')
                logger.info("Saved relay turn-on waveform to CSV")
                
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
                logger.error(f"Error processing measurements: {str(e)}")
                return TestResult(
                    f"Error processing measurements: {str(e)}",
                    FailureCodes.MEASUREMENT_ERROR,
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