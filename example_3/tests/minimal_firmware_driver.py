"""
Driver for communicating with the minimal test firmware over serial.
"""

import serial
import serial.tools.list_ports
import time
import json
import re
import logging
from typing import Optional, Dict, Any, List, Tuple


class MinimalFirmwareDriver:
    """Driver for communicating with minimal test firmware."""
    
    def __init__(self, port: str = None, baudrate: int = 115200, timeout: float = 2.0):
        """
        Initialize the minimal firmware driver.
        
        Args:
            port: Serial port path (auto-detect if None)
            baudrate: Serial baudrate (fixed at 115200 for minimal firmware)
            timeout: Command timeout in seconds
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_connection = None
        self.logger = logging.getLogger(__name__)
        
    def find_ftdi_ports(self) -> List[str]:
        """
        Find FTDI USB-to-Serial devices.
        
        Returns:
            List of FTDI device port paths
        """
        ftdi_ports = []
        ports = serial.tools.list_ports.comports()
        
        for port in ports:
            # Check for FTDI VID/PID (0403:6001)
            if port.vid == 0x0403 and port.pid == 0x6001:
                ftdi_ports.append(port.device)
                self.logger.info(f"Found FTDI device: {port.device} - {port.description}")
        
        return ftdi_ports
    
    def find_available_ports(self) -> List[str]:
        """
        Find all available serial ports.
        
        Returns:
            List of available port paths
        """
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]
    
    def connect(self, port: str = None) -> bool:
        """
        Connect to the minimal firmware device.
        
        Args:
            port: Specific port to connect to (auto-detect if None)
            
        Returns:
            True if connection successful, False otherwise
        """
        if port:
            target_ports = [port]
        else:
            # Prefer FTDI devices, fallback to all ports
            ftdi_ports = self.find_ftdi_ports()
            if ftdi_ports:
                target_ports = ftdi_ports
                self.logger.info(f"Found {len(ftdi_ports)} FTDI device(s)")
            else:
                target_ports = self.find_available_ports()
                self.logger.info(f"No FTDI devices found, trying all {len(target_ports)} ports")
        
        for port_path in target_ports:
            try:
                self.logger.info(f"Attempting to connect to {port_path}")
                
                # Open serial connection
                self.serial_connection = serial.Serial(
                    port_path,
                    baudrate=self.baudrate,
                    timeout=self.timeout
                )
                
                # Wait for device to be ready
                time.sleep(1)
                
                # Test if this is the minimal firmware
                if self._test_minimal_firmware():
                    self.port = port_path
                    self.logger.info(f"Successfully connected to minimal firmware on {port_path}")
                    return True
                else:
                    self.logger.info(f"Device on {port_path} is not running minimal firmware")
                    self.serial_connection.close()
                    self.serial_connection = None
                    
            except Exception as e:
                self.logger.error(f"Failed to connect to {port_path}: {e}")
                if self.serial_connection:
                    self.serial_connection.close()
                    self.serial_connection = None
        
        self.logger.error("Failed to connect to any minimal firmware device")
        return False
    
    def _test_minimal_firmware(self) -> bool:
        """
        Test if the connected device is running minimal firmware.
        
        Returns:
            True if minimal firmware detected, False otherwise
        """
        try:
            # Clear any pending data
            self.serial_connection.reset_input_buffer()
            
            # Send VERSION command and check response
            response = self.send_command("VERSION", timeout=2.0)
            if response and "VERSION:" in response:
                return True
            
            # Try HELP command as fallback
            response = self.send_command("HELP", timeout=2.0)
            if response and ("=== COMMANDS ===" in response or "ON/OFF" in response):
                return True
                
            return False
            
        except Exception as e:
            self.logger.error(f"Error testing minimal firmware: {e}")
            return False
    
    def send_command(self, command: str, timeout: float = None) -> str:
        """
        Send a command to the device and get the response.
        
        Args:
            command: Command to send
            timeout: Response timeout (uses default if None)
            
        Returns:
            Response string or None if failed
        """
        if not self.serial_connection:
            self.logger.error("Not connected to device")
            return None
        
        if timeout is None:
            timeout = self.timeout
        
        try:
            # Clear input buffer
            self.serial_connection.reset_input_buffer()
            
            # Send command
            cmd_bytes = (command + '\r\n').encode('utf-8')
            self.serial_connection.write(cmd_bytes)
            self.logger.debug(f"Sent command: {command}")
            
            # Read response
            response = ""
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                if self.serial_connection.in_waiting > 0:
                    data = self.serial_connection.read(self.serial_connection.in_waiting)
                    response += data.decode('utf-8', errors='ignore')
                    
                    # Stop reading if we see a prompt or obvious end
                    if response.endswith('> ') or '\n> ' in response:
                        break
                
                time.sleep(0.01)
            
            self.logger.debug(f"Received response: {repr(response)}")
            return response.strip()
            
        except Exception as e:
            self.logger.error(f"Error sending command '{command}': {e}")
            return None
    
    def get_status_json(self) -> Optional[Dict[str, Any]]:
        """
        Get device status in JSON format.
        
        Returns:
            Status dictionary or None if failed
        """
        response = self.send_command("JSON")
        if not response:
            return None
        
        try:
            # Extract JSON from response (may contain other text)
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                return json.loads(json_str)
        except Exception as e:
            self.logger.error(f"Error parsing JSON status: {e}")
        
        return None
    
    def get_status_text(self) -> str:
        """
        Get device status in human-readable format.
        
        Returns:
            Status string or None if failed
        """
        return self.send_command("STATUS")
    
    def get_version(self) -> Optional[Dict[str, str]]:
        """
        Get firmware version information.
        
        Returns:
            Version dictionary or None if failed
        """
        response = self.send_command("VERSION")
        if not response:
            return None
        
        version_info = {}
        for line in response.split('\n'):
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                version_info[key.strip()] = value.strip()
        
        return version_info
    
    def set_relay(self, state: bool) -> bool:
        """
        Set relay state.
        
        Args:
            state: True for ON, False for OFF
            
        Returns:
            True if successful, False otherwise
        """
        command = "ON" if state else "OFF"
        response = self.send_command(command)
        
        if response:
            expected = f"OK:RELAY_{'ON' if state else 'OFF'}"
            return expected in response
        
        return False
    
    def toggle_relay(self) -> Optional[bool]:
        """
        Toggle relay state.
        
        Returns:
            New relay state (True/False) or None if failed
        """
        response = self.send_command("TOGGLE")
        if response:
            if "OK:RELAY_ON" in response:
                return True
            elif "OK:RELAY_OFF" in response:
                return False
        
        return None
    
    def get_relay_state(self) -> Optional[bool]:
        """
        Get current relay state.
        
        Returns:
            True if ON, False if OFF, None if failed
        """
        status = self.get_status_json()
        if status and 'relay' in status:
            return status['relay']
        
        return None
    
    def run_self_test(self) -> bool:
        """
        Run the built-in self-test.
        
        Returns:
            True if test passed, False otherwise
        """
        response = self.send_command("TEST", timeout=10.0)
        if response:
            return "SELF_TEST_COMPLETE" in response
        
        return False
    
    def start_burn_in(self, cycles: int, interval_ms: int) -> bool:
        """
        Start burn-in test.
        
        Args:
            cycles: Number of cycles to run
            interval_ms: Interval between cycles in milliseconds
            
        Returns:
            True if started successfully, False otherwise
        """
        command = f"BURN {cycles} {interval_ms}"
        response = self.send_command(command)
        
        if response:
            return "BURN_IN_START:" in response
        
        return False
    
    def stop_burn_in(self) -> bool:
        """
        Stop burn-in test.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        response = self.send_command("STOP")
        return response and "OK:TEST_STOPPED" in response
    
    def is_burn_in_active(self) -> bool:
        """
        Check if burn-in test is currently active.
        
        Returns:
            True if burn-in is active, False otherwise
        """
        status = self.get_status_text()
        if status:
            return "BURN_IN:" in status
        
        return False
    
    def get_burn_in_progress(self) -> Optional[Dict[str, int]]:
        """
        Get burn-in test progress.
        
        Returns:
            Dictionary with 'current' and 'total' cycles, or None
        """
        status = self.get_status_text()
        if status:
            # Look for BURN_IN: current/total pattern
            match = re.search(r'BURN_IN:\s*(\d+)/(\d+)', status)
            if match:
                return {
                    'current': int(match.group(1)),
                    'total': int(match.group(2))
                }
        
        return None
    
    def get_button_state(self) -> Optional[bool]:
        """
        Get current button state.
        
        Returns:
            True if pressed, False if released, None if failed
        """
        response = self.send_command("READ BUTTON")
        if response:
            if "BUTTON:PRESSED" in response:
                return True
            elif "BUTTON:RELEASED" in response:
                return False
        
        return None
    
    def reset_counters(self) -> bool:
        """
        Reset all counters.
        
        Returns:
            True if successful, False otherwise
        """
        response = self.send_command("RESET")
        return response and "OK:COUNTERS_RESET" in response
    
    def get_timing_measurement(self) -> Optional[Dict[str, float]]:
        """
        Get microsecond-precision timing measurements.
        
        Returns:
            Dictionary with timing measurements or None if failed
        """
        response = self.send_command("TIMING", timeout=5.0)
        if not response:
            return None
        
        measurements = {}
        for line in response.split('\n'):
            line = line.strip()
            if "RELAY_ON_TIME_US:" in line:
                try:
                    value = float(line.split(':')[1])
                    measurements['relay_on_time_us'] = value
                except:
                    pass
            elif "RELAY_OFF_TIME_US:" in line:
                try:
                    value = float(line.split(':')[1])
                    measurements['relay_off_time_us'] = value
                except:
                    pass
        
        return measurements if measurements else None
    
    def disconnect(self):
        """Disconnect from the device."""
        if self.serial_connection:
            self.serial_connection.close()
            self.serial_connection = None
            self.logger.info("Disconnected from device")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()