"""
Test functions for minimal test firmware devices.
"""

import time
import serial.tools.list_ports
import random

from onnyx.context import gcc
from onnyx.decorators import test
from onnyx.results import TestResult

from .minimal_firmware_driver import MinimalFirmwareDriver
from .failure_codes import FailureCodes


def should_simulate_failure(failure_code: int) -> bool:
    """Helper function to determine if we should simulate a failure."""
    context = gcc()
    failure_chance = context.document.get("_cell_config_obj", {}).get("enable_intentional_fail")
    
    # If failure_chance is 0 or not set, never simulate failures
    if not failure_chance:
        return False

    fail = random.random() < failure_chance
    if fail:
        context.logger.warning(f"Simulating failure: {failure_code}")
    return fail


@test()
def detect_minimal_firmware_serial_port(
    category: str,
    test_name: str,
    port: str = None,
    baudrate: int = 115200
) -> TestResult:
    """Detect and connect to minimal firmware device.
    
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
            driver = MinimalFirmwareDriver(test_port, baudrate)
            if not driver.connect() or should_simulate_failure(FailureCodes.CONNECTION_ERROR.value):
                continue
                
            # Get device info to verify it's a minimal firmware device
            device_info = driver.get_status_json()
            if device_info and not should_simulate_failure(FailureCodes.CONNECTION_ERROR.value):
                return TestResult(
                    f"Connected to minimal firmware device on {test_port}",
                    FailureCodes.NO_FAILURE,
                    return_value={
                        "port": test_port,
                        "device_info": device_info
                    }
                )
            driver.disconnect()
                
        return TestResult(
            "No minimal firmware devices found on FTDI ports",
            FailureCodes.DEVICE_NOT_FOUND
        )
    
    # Try specified port
    driver = MinimalFirmwareDriver(port, baudrate)
    if not driver.connect() or should_simulate_failure(FailureCodes.CONNECTION_ERROR.value):
        return TestResult(
            f"Failed to connect to {port}",
            FailureCodes.CONNECTION_ERROR
        )
        
    device_info = driver.get_status_json()
    if device_info and not should_simulate_failure(FailureCodes.CONNECTION_ERROR.value):
        return TestResult(
            f"Connected to minimal firmware device on {port}",
            FailureCodes.NO_FAILURE,
            return_value={
                "port": port,
                "device_info": device_info
            }
        )
    
    driver.disconnect()
    return TestResult(
        f"Device on {port} is not a minimal firmware device",
        FailureCodes.DEVICE_NOT_FOUND
    )


@test()
def check_firmware_version(
    category: str,
    test_name: str,
    port: str,
    min_version: str
) -> TestResult:
    """Check minimal firmware version.
    
    Args:
        category: Test category for reporting and organization
        test_name: Name of this specific test instance
        port: Serial port
        min_version: Minimum required version
        
    Returns:
        TestResult with firmware version
    """
    driver = MinimalFirmwareDriver(port)
    if not driver.connect() or should_simulate_failure(FailureCodes.CONNECTION_ERROR.value):
        return TestResult(
            f"Failed to connect to {port}",
            FailureCodes.CONNECTION_ERROR
        )
        
    try:
        version_info = driver.get_version()
        if not version_info or should_simulate_failure(FailureCodes.FIRMWARE_ERROR.value):
            return TestResult(
                "Failed to get firmware version",
                FailureCodes.FIRMWARE_ERROR
            )
            
        # Extract version info
        version = version_info.get('VERSION', 'Unknown')
        build = version_info.get('BUILD', 'Unknown')
        chip_id = version_info.get('CHIP_ID', 'Unknown')
        
        # For now, just check that we got version info
        # More sophisticated version checking could be added here
        if version != 'Unknown' and not should_simulate_failure(FailureCodes.FIRMWARE_ERROR.value):
            return TestResult(
                f"Firmware version {version} detected",
                FailureCodes.NO_FAILURE,
                return_value={
                    "firmware_version": version,
                    "build": build,
                    "chip_id": chip_id
                }
            )
        else:
            return TestResult(
                f"Unable to determine firmware version",
                FailureCodes.FIRMWARE_ERROR
            )
            
    finally:
        driver.disconnect()


@test()
def test_basic_relay_control(
    category: str,
    test_name: str,
    port: str,
    test_cycles: int = 5
) -> TestResult:
    """Test basic relay control functionality.
    
    Args:
        category: Test category for reporting and organization
        test_name: Name of this specific test instance
        port: Serial port
        test_cycles: Number of test cycles to run
        
    Returns:
        TestResult with relay control measurements
    """
    logger = gcc().logger
    logger.info(f"Starting {test_name}")
    
    driver = MinimalFirmwareDriver(port)
    if not driver.connect() or should_simulate_failure(FailureCodes.CONNECTION_ERROR.value):
        return TestResult(
            f"Failed to connect to {port}",
            FailureCodes.CONNECTION_ERROR
        )
        
    try:
        # Reset counters before test
        if not driver.reset_counters():
            logger.warning("Failed to reset counters")
        
        # Get initial state
        initial_state = driver.get_relay_state()
        logger.info(f"Initial relay state: {initial_state}")
        
        # Test relay cycles
        for cycle in range(test_cycles):
            logger.info(f"Cycle {cycle + 1}/{test_cycles}")
            
            # Turn ON
            if not driver.set_relay(True) or should_simulate_failure(FailureCodes.RELAY_ERROR.value):
                return TestResult(
                    f"Failed to turn relay ON in cycle {cycle + 1}",
                    FailureCodes.RELAY_ERROR
                )
            
            time.sleep(0.5)
            
            # Verify ON state
            state = driver.get_relay_state()
            if state is not True:
                return TestResult(
                    f"Relay state mismatch: expected ON, got {state}",
                    FailureCodes.RELAY_ERROR
                )
            
            # Turn OFF
            if not driver.set_relay(False) or should_simulate_failure(FailureCodes.RELAY_ERROR.value):
                return TestResult(
                    f"Failed to turn relay OFF in cycle {cycle + 1}",
                    FailureCodes.RELAY_ERROR
                )
            
            time.sleep(0.5)
            
            # Verify OFF state
            state = driver.get_relay_state()
            if state is not False:
                return TestResult(
                    f"Relay state mismatch: expected OFF, got {state}",
                    FailureCodes.RELAY_ERROR
                )
            
            logger.info(f"Cycle {cycle + 1} completed successfully")
        
        # Get final status
        status = driver.get_status_json()
        measurements = {
            "test_cycles": test_cycles,
            "initial_state": initial_state,
            "final_status": status
        }
        
        logger.info("Basic relay control test completed successfully")
        return TestResult(
            f"Successfully completed {test_cycles} relay control cycles",
            FailureCodes.NO_FAILURE,
            return_value=measurements
        )
        
    except Exception as e:
        logger.error(f"Error in basic relay control test: {e}")
        return TestResult(
            f"Error in basic relay control test: {e}",
            FailureCodes.RELAY_ERROR
        )
    finally:
        driver.disconnect()


@test()
def test_relay_reliability(
    category: str,
    test_name: str,
    port: str,
    reliability_cycles: int = 50
) -> TestResult:
    """Test relay reliability to catch race conditions and timing bugs.
    
    This test performs rapid relay cycling to expose stability issues
    that an intermediate programmer might introduce, such as:
    - Race conditions in relay control
    - Inconsistent state tracking
    - Timing-dependent failures
    
    Args:
        category: Test category for reporting and organization
        test_name: Name of this specific test instance
        port: Serial port
        reliability_cycles: Number of rapid test cycles to run
        
    Returns:
        TestResult with reliability measurements
    """
    logger = gcc().logger
    logger.info(f"Starting {test_name} with {reliability_cycles} cycles")
    
    driver = MinimalFirmwareDriver(port)
    if not driver.connect() or should_simulate_failure(FailureCodes.CONNECTION_ERROR.value):
        return TestResult(
            f"Failed to connect to {port}",
            FailureCodes.CONNECTION_ERROR
        )
        
    try:
        # Reset counters before test
        if not driver.reset_counters():
            logger.warning("Failed to reset counters")
        
        failures = 0
        inconsistencies = 0
        timing_failures = 0
        
        # Rapid reliability testing
        for cycle in range(reliability_cycles):
            if cycle % 10 == 0:
                logger.info(f"Reliability cycle {cycle + 1}/{reliability_cycles}")
            
            # Test rapid ON/OFF cycling (expose race conditions)
            expected_state = True
            if not driver.set_relay(expected_state):
                failures += 1
                continue
                
            # Short delay to expose timing bugs
            time.sleep(0.05)  # 50ms - faster than typical delays
            
            # Verify state consistency
            actual_state = driver.get_relay_state()
            if actual_state != expected_state:
                inconsistencies += 1
                logger.warning(f"State inconsistency at cycle {cycle}: expected {expected_state}, got {actual_state}")
            
            # Test OFF
            expected_state = False  
            if not driver.set_relay(expected_state):
                failures += 1
                continue
                
            time.sleep(0.05)  # Another short delay
            
            # Verify state consistency again
            actual_state = driver.get_relay_state()
            if actual_state != expected_state:
                inconsistencies += 1
                logger.warning(f"State inconsistency at cycle {cycle}: expected {expected_state}, got {actual_state}")
            
            # Test timing consistency (buggy firmware may have variable timing)
            start_time = time.time()
            driver.set_relay(True)
            time.sleep(0.02)  # Very short timing window
            driver.set_relay(False) 
            end_time = time.time()
            
            # Should complete in reasonable time (< 100ms)
            if (end_time - start_time) > 0.1:
                timing_failures += 1
        
        # Calculate reliability metrics
        total_operations = reliability_cycles * 4  # 2 states × 2 verifications per cycle
        success_rate = ((total_operations - failures - inconsistencies) / total_operations) * 100
        
        # Get final status for analysis
        final_status = driver.get_status_json()
        
        measurements = {
            "reliability_cycles": reliability_cycles,
            "total_operations": total_operations,
            "failures": failures,
            "state_inconsistencies": inconsistencies,
            "timing_failures": timing_failures,
            "success_rate_percent": success_rate,
            "final_status": final_status
        }
        
        # Determine pass/fail criteria
        # A good firmware should have > 99% reliability
        # Buggy firmware will likely have < 95% due to race conditions
        if success_rate >= 99.0 and inconsistencies == 0 and timing_failures < 3:
            logger.info(f"Reliability test passed: {success_rate:.1f}% success rate")
            return TestResult(
                f"Relay reliability test passed with {success_rate:.1f}% success rate",
                FailureCodes.NO_FAILURE,
                return_value=measurements
            )
        else:
            logger.error(f"Reliability test failed: {success_rate:.1f}% success rate, {inconsistencies} inconsistencies, {timing_failures} timing failures")
            return TestResult(
                f"Relay reliability test failed: {success_rate:.1f}% success rate, {inconsistencies} state inconsistencies detected",
                FailureCodes.RELAY_ERROR,
                return_value=measurements
            )
        
    except Exception as e:
        logger.error(f"Error in reliability test: {e}")
        return TestResult(
            f"Error in reliability test: {e}",
            FailureCodes.RELAY_ERROR
        )
    finally:
        driver.disconnect()
