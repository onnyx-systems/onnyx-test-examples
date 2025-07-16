import time
import socket
import numpy as np
from typing import Dict, Any, Optional, List

from onnyx.context import gcc
from onnyx.decorators import test
from onnyx.results import TestResult
from onnyx.failure import BaseFailureCodes, FailureCode

from .rigol_driver import RigolOscilloscopeDriver
from .tasmota_driver import TasmotaSerialDriver
from .failure_codes import FailureCodes

def should_simulate_failure(failure_code: int) -> bool:
    """Helper function to determine if we should simulate a failure."""
    import random
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
        failure_chance = context.document.get("_cell_config_obj", {}).get("enable_intentional_fail")
        
        # Configure single trigger for relay test
        oscilloscope.send_command(":TRIGger:SWEep SINGle")
        
        # Arm trigger and wait for ready - no need for separate delay
        oscilloscope.send_command(":SINGle")
        time.sleep(0.5)  # Reduced from 1s
        
        # Toggle relay (unless simulating failure)
        action = "on" if turn_on else "off"
        logger.info(f"Turning relay {relay_number} {action}")
        
        if turn_on and failure_chance and random.random() < failure_chance:
            # Simulate mechanical failure by not actually turning on the relay
            logger.info("Simulating mechanical failure - relay did not actuate")
        else:
            if not tasmota.set_power(turn_on, relay_number):
                return None
        
        # Wait for trigger and capture with polling instead of fixed delay
        timeout = 4  # Reduced from 5 seconds
        poll_interval = 0.05  # Check status faster (was 0.1s)
        start_time = time.time()
        
        # Poll for trigger with shorter intervals
        while time.time() - start_time < timeout:
            status = oscilloscope.query(":TRIGger:STATus?")
            if status.strip() == "STOP":
                logger.info(f"Captured relay {action} transition")
                break
            time.sleep(poll_interval)
        else:
            logger.warning(f"Timeout waiting for relay {action} transition capture")
            return None
        
        # Get waveform data
        return oscilloscope.capture_waveform(channel=1)
        
    except Exception as e:
        logger.error(f"Error in capture_relay_transition: {str(e)}")
        return None
