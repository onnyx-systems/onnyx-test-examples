import time
import socket
import random
import numpy as np
from typing import Dict, Any, Optional, List

from onnyx.context import gcc
from onnyx.decorators import test
from onnyx.results import TestResult
from onnyx.failure import BaseFailureCodes, FailureCode

from .rigol_driver import RigolOscilloscopeDriver
# Removed tasmota_driver import - using minimal firmware instead
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


def detect_oscilloscope() -> Optional[str]:
    """Auto-detect a Rigol oscilloscope on the network.
    
    Returns:
        IP address of oscilloscope if found, None otherwise
    """
    # For now, return None since auto-detection requires network scanning
    # which is complex. Users should specify oscilloscope IP manually.
    return None

def connect_oscilloscope(
    ip_address: str,
    port: int = 5555,
    timebase: float = 0.005  # Default to 5ms/div for 60Hz AC
) -> Optional[RigolOscilloscopeDriver]:
    """Connect to and configure the oscilloscope for AC line measurements.
    
    Args:
        ip_address: IP address of the oscilloscope
        port: SCPI port (default: 5555)
        timebase: Timebase in seconds/div (default: 0.005 = 5ms/div)
        
    Returns:
        RigolOscilloscopeDriver instance if successful, None otherwise
    """
    try:
        # Connect to oscilloscope
        scope = RigolOscilloscopeDriver(ip_address, port)
        if not scope.connect():
            return None
            
        # Basic configuration
        scope.send_command("*RST")
        time.sleep(1)
        scope.send_command(f":TIMebase:SCALe {timebase}")
        time.sleep(0.1)
        scope.send_command(":CHANnel1:DISPlay ON")
        time.sleep(0.1)
        
        return scope
        
    except Exception as e:
        print(f"Error connecting to oscilloscope: {e}")
        return None

def capture_relay_transition(
    oscilloscope: RigolOscilloscopeDriver,
    minimal_driver,
    turn_on: bool,
    logger
) -> Optional[np.ndarray]:
    """Capture relay transition waveform using minimal firmware.
    
    Args:
        oscilloscope: Configured oscilloscope instance
        minimal_driver: Connected minimal firmware device
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
        
        # Arm trigger and wait for ready
        oscilloscope.send_command(":SINGle")
        time.sleep(0.5)
        
        # Toggle relay (unless simulating failure)
        action = "on" if turn_on else "off"
        logger.info(f"Turning relay {action}")
        
        if turn_on and failure_chance and random.random() < failure_chance:
            # Simulate mechanical failure by not actually turning on the relay
            logger.info("Simulating mechanical failure - relay did not actuate")
        else:
            if not minimal_driver.set_relay(turn_on):
                return None
        
        # Wait for trigger and capture with polling
        timeout = 4
        poll_interval = 0.05
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
