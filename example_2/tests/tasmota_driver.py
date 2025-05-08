import serial
import json
import time
import logging
from typing import Dict, Any, Optional, Union, List, Tuple


class TasmotaSerialDriver:
    """Driver for communicating with Tasmota firmware on Sonoff relays over serial port.

    This driver provides methods to control and query Sonoff relays running Tasmota firmware
    through a serial connection.
    """

    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 1.0):
        """Initialize the Tasmota serial driver.

        Args:
            port: Serial port name (e.g., 'COM3' on Windows, '/dev/ttyUSB0' on Linux)
            baudrate: Baud rate for serial communication (default: 115200)
            timeout: Serial read timeout in seconds (default: 1.0)
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None
        self.logger = logging.getLogger("TasmotaSerialDriver")

    def connect(self) -> bool:
        """Connect to the Tasmota device over serial.

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.logger.info(
                f"Attempting to connect to {self.port} at {self.baudrate} baud"
            )

            # Configure serial port with FTDI-friendly settings
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                xonxoff=False,  # Disable software flow control
                rtscts=False,  # Disable hardware (RTS/CTS) flow control
                dsrdtr=False,  # Disable hardware (DSR/DTR) flow control
                write_timeout=2.0,  # Add write timeout to prevent blocking
            )

            # Clear any pending data
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()

            # Wait for the device to stabilize after connection
            time.sleep(0.5)

            # Send a test command to verify connection
            self.logger.info("Sending test command (Status 0) to verify connection")
            response = self.send_command("Status 0", wait_time=1.0)

            if response:
                self.logger.info(f"Connected to Tasmota device on {self.port}")
                self.logger.debug(f"Response: {response}")
                return True
            else:
                self.logger.error(
                    f"Connected to {self.port} but no valid response from Tasmota"
                )
                self.disconnect()
                return False

        except serial.SerialException as e:
            self.logger.error(f"Failed to connect to {self.port}: {str(e)}")
            return False

    def disconnect(self) -> None:
        """Disconnect from the Tasmota device."""
        if self.serial and self.serial.is_open:
            self.logger.info(f"Disconnecting from {self.port}")
            self.serial.close()
            self.serial = None
            self.logger.info(f"Disconnected from {self.port}")

    def is_connected(self) -> bool:
        """Check if the driver is connected to the device.

        Returns:
            bool: True if connected, False otherwise
        """
        return self.serial is not None and self.serial.is_open

    def send_command(self, command: str, wait_time: float = 0.5) -> Dict[str, Any]:
        """Send a command to the Tasmota device and return the response.

        Args:
            command: Command to send
            wait_time: Time to wait for response in seconds

        Returns:
            Dict[str, Any]: Response from the device or empty dict if failed
        """
        if not self.is_connected():
            self.logger.error("Not connected to Tasmota device")
            return {}

        try:
            # Send the command
            self.logger.debug(f"Sending command: {command}")
            self.serial.write(f"{command}\r\n".encode('utf-8'))
            self.serial.flush()

            # Wait for response
            time.sleep(wait_time)

            # Read response
            response = ""
            while self.serial.in_waiting > 0:
                response += self.serial.read(self.serial.in_waiting).decode('utf-8')
                time.sleep(0.1)  # Small delay to allow more data to arrive

            self.logger.debug(f"Received response: {response}")

            # Try to parse JSON response
            try:
                # Look for JSON objects in the response
                json_start = response.find('{')
                if json_start >= 0:
                    json_str = response[json_start:]
                    result = json.loads(json_str)
                    return result
                else:
                    # No JSON found, return raw response
                    return {"raw_response": response}
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse JSON response: {str(e)}")
                # Return raw response if JSON parsing fails
                return {"raw_response": response}

        except Exception as e:
            self.logger.error(f"Error sending command: {str(e)}")
            return {}

    def send_raw_command(self, command: str, wait_time: float = 0.5) -> str:
        """Send a command to the Tasmota device and return the raw response without JSON parsing.

        Args:
            command: Command to send
            wait_time: Time to wait for response in seconds

        Returns:
            str: Raw response from the device or empty string if failed
        """
        if not self.is_connected():
            self.logger.error("Not connected to Tasmota device")
            return ""

        try:
            # Send the command
            self.logger.debug(f"Sending raw command: {command}")
            self.serial.write(f"{command}\r\n".encode('utf-8'))
            self.serial.flush()

            # Wait for response
            time.sleep(wait_time)

            # Read response
            response = ""
            while self.serial.in_waiting > 0:
                response += self.serial.read(self.serial.in_waiting).decode('utf-8')
                time.sleep(0.1)  # Small delay to allow more data to arrive

            self.logger.debug(f"Received raw response: {response}")
            return response

        except Exception as e:
            self.logger.error(f"Error sending raw command: {str(e)}")
            return ""

    def get_status(self) -> Optional[Dict[str, Any]]:
        """Get the status of the Tasmota device.

        Returns:
            Optional[Dict[str, Any]]: Status information or None if failed
        """
        self.logger.info("Getting device status")
        return self.send_command("Status 0")

    def get_power_state(self, relay_number: int = 1) -> Optional[bool]:
        """Get the power state of a specific relay.

        Args:
            relay_number: Relay number (1-8, default: 1)

        Returns:
            Optional[bool]: True if relay is ON, False if OFF, None if failed
        """
        self.logger.info(f"Getting power state for relay {relay_number}")

        # Define common patterns for ON state detection
        # For single relay devices (relay_number=1), we check both POWER and POWER1
        on_patterns = [
            f"POWER{relay_number} ON",
            f"POWER{relay_number}=ON",
            f"POWER{relay_number}: ON",
            f"RSL: POWER{relay_number} = ON",
            f'"POWER{relay_number}":"ON"',
        ]

        # Add patterns specific to single-relay devices
        if relay_number == 1:
            on_patterns.extend(
                [
                    "POWER ON",
                    "POWER=ON",
                    "POWER: ON",
                    "RSL: POWER = ON",
                    '"POWER":"ON"',
                ]
            )

        # Generate OFF patterns by replacing ON with OFF in all patterns
        off_patterns = [
            p.replace(" ON", " OFF")
            .replace("=ON", "=OFF")
            .replace(": ON", ": OFF")
            .replace('"ON"', '"OFF"')
            for p in on_patterns
        ]

        # Try multiple methods to determine the state, in order of reliability

        # Method 1: Status 11 command (most reliable)
        status_response = self.send_command("Status 11", wait_time=1.0)
        if status_response:
            # Try to parse JSON response
            if "StatusSTS" in status_response:
                status_sts = status_response["StatusSTS"]

                # Check for POWER field (single relay) or POWER1, POWER2, etc. (multiple relays)
                power_key = "POWER" if relay_number == 1 else f"POWER{relay_number}"
                if power_key in status_sts:
                    power_state = status_sts[power_key]
                    self.logger.info(
                        f"Found power state in Status 11: {power_key}={power_state}"
                    )

                    if power_state == "ON":
                        return True
                    elif power_state == "OFF":
                        return False

            # If JSON parsing didn't work, try pattern matching on raw response
            if "raw_response" in status_response:
                raw = status_response["raw_response"].upper()

                # Check for ON patterns
                for pattern in on_patterns:
                    if pattern.upper() in raw:
                        self.logger.info(
                            f"Relay {relay_number} is ON (matched pattern in Status 11)"
                        )
                        return True

                # Check for OFF patterns
                for pattern in off_patterns:
                    if pattern.upper() in raw:
                        self.logger.info(
                            f"Relay {relay_number} is OFF (matched pattern in Status 11)"
                        )
                        return False

        # Method 2: Direct Power query
        self.logger.info(f"Trying direct Power{relay_number} query")
        response = self.send_command(f"Power{relay_number}", wait_time=1.0)

        if response and "raw_response" in response:
            raw = response["raw_response"].upper()

            # Check for ON patterns
            for pattern in on_patterns:
                if pattern.upper() in raw:
                    self.logger.info(f"Relay {relay_number} is ON (direct query)")
                    return True

            # Check for OFF patterns
            for pattern in off_patterns:
                if pattern.upper() in raw:
                    self.logger.info(f"Relay {relay_number} is OFF (direct query)")
                    return False

        # Method 3: Status 0 command (fallback)
        self.logger.info("Trying to get power state from device status")
        status = self.send_command("Status 0", wait_time=1.0)

        if status:
            # Try to parse JSON response
            if "Status" in status:
                power_info = status["Status"].get("Power")
                if power_info is not None:
                    self.logger.info(f"Found power info in Status: {power_info}")
                    # Power might be a string "0" or "1", or a number, or "ON"/"OFF"
                    if power_info in ["0", "OFF", 0, "off", "Off"]:
                        return False
                    elif power_info in ["1", "ON", 1, "on", "On"]:
                        return True

            # If JSON parsing didn't work, try pattern matching on raw response
            if "raw_response" in status:
                raw = status["raw_response"].upper()

                # Check for ON patterns
                for pattern in on_patterns:
                    if pattern.upper() in raw:
                        self.logger.info(f"Relay {relay_number} is ON (from Status 0)")
                        return True

                # Check for OFF patterns
                for pattern in off_patterns:
                    if pattern.upper() in raw:
                        self.logger.info(f"Relay {relay_number} is OFF (from Status 0)")
                        return False

        # If we get here, we couldn't determine the state
        self.logger.warning(
            f"Could not determine power state for relay {relay_number} after trying all methods"
        )
        return None

    def set_power(self, state: bool, relay_number: int = 1) -> bool:
        """Set the power state of a specific relay.

        Args:
            state: True to turn ON, False to turn OFF
            relay_number: Relay number (1-8, default: 1)

        Returns:
            bool: True if command was successful, False otherwise
        """
        state_str = "ON" if state else "OFF"
        self.logger.info(f"Setting relay {relay_number} to {state_str}")

        # First check if the relay is already in the requested state
        current_state = self.get_power_state(relay_number)
        if current_state is not None and (
            (current_state and state) or (not current_state and not state)
        ):
            self.logger.info(
                f"Relay {relay_number} is already {state_str}, no action needed"
            )
            return True

        # Define success patterns for response validation
        success_patterns = [
            f"POWER{relay_number} {state_str}",
            f"POWER{relay_number}={state_str}",
            f"POWER{relay_number}: {state_str}",
            f"RSL: POWER{relay_number} = {state_str}",
            f"POWER{relay_number} SAME",  # "SAME" response indicates the relay was already in the requested state
        ]

        # Add patterns specific to single-relay devices
        if relay_number == 1:
            success_patterns.extend(
                [
                    f"POWER {state_str}",
                    f"POWER={state_str}",
                    f"POWER: {state_str}",
                    f"RSL: POWER = {state_str}",
                    "POWER SAME",
                ]
            )

        # Send the command to change the state
        cmd = f"Power{relay_number} {state_str}"
        response = self.send_command(cmd, wait_time=1.0)

        if response:
            # Check if the command was successful
            if "raw_response" in response:
                raw_response = response["raw_response"].upper()

                # Check if any success pattern is found in the response
                for pattern in success_patterns:
                    if pattern.upper() in raw_response:
                        self.logger.info(
                            f"Successfully set relay {relay_number} to {state_str}"
                        )
                        return True

                # If no success pattern was found, verify the state directly
                self.logger.warning(
                    f"No success pattern found in response, verifying state directly"
                )
                time.sleep(0.5)  # Wait a bit for the state to change
            else:
                self.logger.warning(
                    f"No raw_response in command result, verifying state directly"
                )

            # Verify the state directly as a fallback
            new_state = self.get_power_state(relay_number)
            if new_state is not None and (
                (new_state and state) or (not new_state and not state)
            ):
                self.logger.info(f"Verified relay {relay_number} is now {state_str}")
                return True

            # If we get here, the command likely failed
            self.logger.warning(f"Failed to set relay {relay_number} to {state_str}")
            return False

        self.logger.error(
            f"No valid response when setting relay {relay_number} to {state_str}"
        )
        return False

    def toggle_power(self, relay_number: int = 1) -> Optional[bool]:
        """Toggle the power state of a specific relay.

        Args:
            relay_number: Relay number (1-8, default: 1)

        Returns:
            Optional[bool]: New state (True=ON, False=OFF) or None if failed
        """
        self.logger.info(f"Toggling relay {relay_number}")
        response = self.send_command(f"Power{relay_number} TOGGLE")
        if response and "raw_response" in response:
            raw = response["raw_response"].upper()
            if f"POWER{relay_number} ON" in raw:
                self.logger.info(f"Relay {relay_number} toggled to ON")
                return True
            elif f"POWER{relay_number} OFF" in raw:
                self.logger.info(f"Relay {relay_number} toggled to OFF")
                return False
            else:
                self.logger.warning(f"Unexpected response format after toggle: {raw}")
        else:
            self.logger.warning(f"Failed to toggle relay {relay_number}")
        return None

    def get_firmware_version(self) -> Optional[str]:
        """Get the Tasmota firmware version.

        Returns:
            Optional[str]: Firmware version or None if failed
        """
        self.logger.info("Getting firmware version")
        response = self.send_command("Status 2")
        if response and "StatusFWR" in response:
            version = response["StatusFWR"].get("Version")
            self.logger.info(f"Firmware version: {version}")
            return version

        self.logger.warning("Failed to get firmware version")
        return None

    def get_device_info(self) -> Optional[Dict[str, Any]]:
        """Get the Tasmota device information.
        
        Returns:
            Optional[Dict[str, Any]]: Device information or None if failed
        """
        self.logger.info("Getting device information")
        
        # Collect information from multiple status commands
        device_info = {}
        
        # Status 1: Get device information
        response = self.send_command("Status 1")
        if response and "StatusPRM" in response:
            device_info.update({
                "module": response["StatusPRM"].get("Module", "Unknown"),
                "device_name": response["StatusPRM"].get("DeviceName", "Unknown"),
                "friendly_name": response["StatusPRM"].get("FriendlyName", ["Unknown"])[0],
                "topic": response["StatusPRM"].get("Topic", "Unknown"),
                "ota_url": response["StatusPRM"].get("OtaUrl", "")
            })
        
        # Status 2: Get firmware information
        response = self.send_command("Status 2")
        if response and "StatusFWR" in response:
            fwr = response["StatusFWR"]
            device_info.update({
                "version": fwr.get("Version", "Unknown"),
                "build_date": fwr.get("BuildDateTime", "Unknown"),
                "boot_count": fwr.get("BootCount", 0),
                "core": fwr.get("Core", "Unknown"),
                "sdk": fwr.get("SDK", "Unknown")
            })
        
        # Status 3: Get logging information
        response = self.send_command("Status 3")
        if response and "StatusLOG" in response:
            device_info["logging"] = response["StatusLOG"]
        
        # Status 4: Get memory information
        response = self.send_command("Status 4")
        if response and "StatusMEM" in response:
            device_info["memory"] = response["StatusMEM"]
        
        # Status 5: Get network information
        response = self.send_command("Status 5")
        if response and "StatusNET" in response:
            device_info["network"] = response["StatusNET"]
        
        if device_info:
            self.logger.info(f"Retrieved device info: {device_info}")
            return device_info
        
        self.logger.warning("Failed to get device information")
        return None

    def get_wifi_status(self) -> Optional[Dict[str, Any]]:
        """Get WiFi status information.

        Returns:
            Optional[Dict[str, Any]]: WiFi status or None if failed
        """
        self.logger.info("Getting WiFi status")
        response = self.send_command("Status 5")
        if response and "StatusSTS" in response:
            wifi_status = response["StatusSTS"].get("Wifi", {})
            self.logger.info(f"WiFi status: {wifi_status}")
            return wifi_status

        self.logger.warning("Failed to get WiFi status")
        return None

    def restart(self) -> bool:
        """Restart the Tasmota device.

        Returns:
            bool: True if restart command was sent successfully
        """
        self.logger.info("Restarting device")
        response = self.send_command("Restart 1")
        success = response is not None
        if success:
            self.logger.info("Restart command sent successfully")
        else:
            self.logger.warning("Failed to send restart command")
        return success

    def set_option(self, option: int, value: Union[int, bool]) -> bool:
        """Set a Tasmota option.

        Args:
            option: Option number
            value: Option value (0/1 or True/False)

        Returns:
            bool: True if command was successful
        """
        val = 1 if value else 0
        self.logger.info(f"Setting option {option} to {val}")
        response = self.send_command(f"SetOption{option} {val}")
        success = response is not None
        if success:
            self.logger.info(f"Successfully set option {option} to {val}")
        else:
            self.logger.warning(f"Failed to set option {option}")
        return success

    def execute_command(self, command: str) -> Optional[Dict[str, Any]]:
        """Execute a custom Tasmota command.

        Args:
            command: Custom Tasmota command

        Returns:
            Optional[Dict[str, Any]]: Command response or None if failed
        """
        self.logger.info(f"Executing custom command: {command}")
        return self.send_command(command)
