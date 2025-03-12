import socket
import time
import logging
import numpy as np
import csv
from typing import Dict, Any, Optional, Union, List, Tuple
import os
import datetime

# Import the waveform utilities
try:
    # Try relative import first (when running as a package)
    from .waveform_utils import analyze_waveform_file
except ImportError:
    try:
        # Try absolute import (when running directly)
        from tests.waveform_utils import analyze_waveform_file
    except ImportError:
        # Last resort: try importing from the current directory
        import sys

        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from waveform_utils import analyze_waveform_file


class RigolOscilloscopeDriver:
    """Driver for communicating with Rigol DS1054 oscilloscope over Ethernet.

    This driver provides methods to control and query the oscilloscope,
    capture waveform data, and save it to CSV files.
    """

    def __init__(self, ip_address: str, port: int = 5555, timeout: float = 5.0):
        """Initialize the Rigol oscilloscope driver.

        Args:
            ip_address: IP address of the oscilloscope
            port: SCPI port (default: 5555)
            timeout: Socket timeout in seconds (default: 5.0)
        """
        self.ip_address = ip_address
        self.port = port
        self.timeout = timeout
        self.socket = None
        self.logger = logging.getLogger("RigolOscilloscopeDriver")
        self.connected = False

    def connect(self) -> bool:
        """Connect to the oscilloscope over Ethernet.

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.logger.info(
                f"Connecting to Rigol oscilloscope at {self.ip_address}:{self.port}"
            )
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.ip_address, self.port))

            # Verify connection by querying the instrument ID
            idn = self.query("*IDN?")
            if idn and "RIGOL" in idn:
                self.logger.info(f"Connected to oscilloscope: {idn}")
                self.connected = True
                return True
            else:
                self.logger.error(
                    "Connected but device doesn't appear to be a Rigol oscilloscope"
                )
                self.disconnect()
                return False

        except Exception as e:
            self.logger.error(f"Failed to connect to oscilloscope: {str(e)}")
            self.socket = None
            return False

    def disconnect(self) -> None:
        """Disconnect from the oscilloscope."""
        if self.socket:
            self.logger.info(f"Disconnecting from oscilloscope at {self.ip_address}")
            self.socket.close()
            self.socket = None
            self.connected = False

    def is_connected(self) -> bool:
        """Check if the driver is connected to the oscilloscope.

        Returns:
            bool: True if connected, False otherwise
        """
        return self.connected and self.socket is not None

    def send_command(self, command: str) -> bool:
        """Send a command to the oscilloscope.

        Args:
            command: SCPI command to send

        Returns:
            bool: True if command was sent successfully, False otherwise
        """
        if not self.is_connected():
            self.logger.error("Not connected to oscilloscope")
            return False

        try:
            # Add newline if not present
            if not command.endswith("\n"):
                command += "\n"

            self.logger.debug(f"Sending command: {command.strip()}")
            self.socket.sendall(command.encode("utf-8"))
            return True
        except Exception as e:
            self.logger.error(f"Error sending command: {str(e)}")
            return False

    def query(self, query: str, max_size: int = 1024 * 1024) -> Optional[str]:
        """Send a query to the oscilloscope and return the response.

        Args:
            query: SCPI query to send
            max_size: Maximum size of response to read

        Returns:
            Optional[str]: Response from oscilloscope or None if failed
        """
        if not self.is_connected():
            self.logger.error("Not connected to oscilloscope")
            return None

        try:
            # Send the query
            if not self.send_command(query):
                return None

            # Read the response
            response = b""
            start_time = time.time()

            # Keep reading until we get a complete response or timeout
            while (time.time() - start_time) < self.timeout:
                try:
                    chunk = self.socket.recv(4096)
                    if not chunk:
                        break
                    response += chunk

                    # If we got a complete response, break
                    if response.endswith(b"\n"):
                        break
                except socket.timeout:
                    # Socket timeout, break the loop
                    break

            if response:
                decoded = response.decode("utf-8", errors="replace").strip()
                self.logger.debug(f"Received response: {decoded[:100]}...")
                return decoded
            else:
                self.logger.warning(f"No response received for query: {query}")
                return None

        except Exception as e:
            self.logger.error(f"Error querying oscilloscope: {str(e)}")
            return None

    def setup_for_relay_test(self, channel: int = 1, timebase: float = 0.001) -> bool:
        """Configure the oscilloscope for relay testing.

        Args:
            channel: Channel number to use (default: 1)
            timebase: Timebase setting in seconds/div (default: 1ms/div)

        Returns:
            bool: True if setup was successful, False otherwise
        """
        if not self.is_connected():
            return False

        try:
            # Reset the oscilloscope to default settings
            self.send_command("*RST")
            time.sleep(1)  # Wait for reset to complete

            # Configure the specified channel
            self.send_command(f":CHAN{channel}:DISP ON")  # Turn on the channel
            self.send_command(f":CHAN{channel}:COUP DC")  # DC coupling
            self.send_command(f":CHAN{channel}:SCAL 1")  # 1V/div
            self.send_command(f":CHAN{channel}:OFFS 0")  # 0V offset

            # Configure the timebase
            self.send_command(f":TIM:SCAL {timebase}")  # Set timebase
            self.send_command(":TIM:OFFS 0")  # Center the trigger

            # Configure the trigger
            self.send_command(
                f":TRIG:EDGE:SOUR CHAN{channel}"
            )  # Trigger on the specified channel
            self.send_command(":TRIG:EDGE:SLOP POS")  # Positive slope
            self.send_command(":TRIG:EDGE:LEV 2.5")  # Trigger at 2.5V (middle of 5V)

            # Configure acquisition
            self.send_command(":ACQ:TYPE NORM")  # Normal acquisition mode
            self.send_command(":ACQ:SRAT?")  # Query sample rate
            sample_rate = self.query(":ACQ:SRAT?")
            self.logger.info(f"Sample rate: {sample_rate}")

            return True
        except Exception as e:
            self.logger.error(f"Error setting up oscilloscope: {str(e)}")
            return False

    def capture_waveform(self, channel: int = 1) -> Optional[np.ndarray]:
        """Capture waveform data from the specified channel.

        Args:
            channel: Channel number to capture (default: 1)

        Returns:
            Optional[np.ndarray]: Waveform data as numpy array or None if failed
        """
        if not self.is_connected():
            return None

        try:
            # Stop acquisition to ensure we get a stable waveform
            self.send_command(":STOP")

            # Set waveform source
            self.send_command(f":WAV:SOUR CHAN{channel}")

            # Set waveform format to binary
            self.send_command(":WAV:FORM BYTE")

            # Get waveform preamble (contains scaling information)
            preamble_str = self.query(":WAV:PRE?")
            if not preamble_str:
                self.logger.error("Failed to get waveform preamble")
                return None

            # Parse preamble
            preamble = preamble_str.split(",")
            if len(preamble) < 10:
                self.logger.error(f"Invalid preamble format: {preamble_str}")
                return None

            # Extract scaling parameters
            format_type = int(preamble[0])  # 0=BYTE, 1=WORD
            points = int(preamble[2])  # Number of points
            x_increment = float(preamble[4])  # Time between points
            x_origin = float(preamble[5])  # First point time
            y_increment = float(preamble[7])  # Voltage per level
            y_origin = float(preamble[8])  # Reference level
            y_reference = float(preamble[9])  # Reference position

            self.logger.info(
                f"Capturing {points} points with time increment {x_increment}s"
            )

            # Get waveform data
            self.send_command(":WAV:DATA?")

            # Read response header and data
            response = b""
            header_read = False
            data_length = 0

            # Read the response in chunks
            while True:
                chunk = self.socket.recv(4096)
                if not chunk:
                    break

                response += chunk

                # Parse the header if we haven't already
                if not header_read and b"#" in response:
                    header_pos = response.find(b"#")
                    if header_pos >= 0 and len(response) > header_pos + 2:
                        try:
                            length_digits = int(
                                response[header_pos + 1 : header_pos + 2]
                            )
                            if len(response) >= header_pos + 2 + length_digits:
                                data_length = int(
                                    response[
                                        header_pos + 2 : header_pos + 2 + length_digits
                                    ]
                                )
                                header_read = True
                        except ValueError:
                            self.logger.error("Failed to parse waveform header")
                            return None

                # Check if we've read all the data
                if (
                    header_read and len(response) >= data_length + 11
                ):  # 11 = "#" + digit + length_digits + data
                    break

            # Extract the actual data
            if header_read:
                header_pos = response.find(b"#")
                length_digits = int(response[header_pos + 1 : header_pos + 2])
                data_start = header_pos + 2 + length_digits
                data_bytes = response[data_start : data_start + data_length]

                # Convert to numpy array
                waveform = np.frombuffer(data_bytes, dtype=np.uint8)

                # Scale the data
                time_axis = np.arange(0, len(waveform)) * x_increment + x_origin
                voltage_axis = (waveform - y_reference) * y_increment + y_origin

                return np.column_stack((time_axis, voltage_axis))
            else:
                self.logger.error("Failed to read waveform data")
                return None

        except Exception as e:
            self.logger.error(f"Error capturing waveform: {str(e)}")
            return None
        finally:
            # Restart acquisition
            self.send_command(":RUN")

    def save_waveform_to_csv(self, waveform: np.ndarray, filename: str) -> bool:
        """Save waveform data to a CSV file.

        Args:
            waveform: Waveform data as numpy array
            filename: Filename to save to

        Returns:
            bool: True if save was successful, False otherwise
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)

            # Save to CSV
            with open(filename, "w", newline="") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["Time (s)", "Voltage (V)"])
                writer.writerows(waveform)

            self.logger.info(f"Saved waveform to {filename}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving waveform to CSV: {str(e)}")
            return False

    def capture_relay_transition(
        self,
        channel: int = 1,
        transition_type: str = "rising",
        output_dir: str = "waveforms",
    ) -> Optional[str]:
        """Capture a relay transition (rising or falling edge).

        Args:
            channel: Channel number to capture (default: 1)
            transition_type: Type of transition to capture ("rising" or "falling")
            output_dir: Directory to save the waveform data

        Returns:
            Optional[str]: Path to saved CSV file or None if failed
        """
        if not self.is_connected():
            return None

        try:
            # Configure trigger based on transition type
            slope = "POS" if transition_type.lower() == "rising" else "NEG"
            self.send_command(f":TRIG:EDGE:SOUR CHAN{channel}")
            self.send_command(f":TRIG:EDGE:SLOP {slope}")
            self.send_command(":TRIG:EDGE:LEV 2.5")  # Trigger at 2.5V (middle of 5V)

            # Set single trigger mode
            self.send_command(":SING")
            self.logger.info(f"Waiting for {transition_type} edge trigger...")

            # Wait for trigger
            triggered = False
            start_time = time.time()
            while (time.time() - start_time) < 10:  # 10 second timeout
                status = self.query(":TRIG:STAT?")
                if status and "STOP" in status:
                    triggered = True
                    break
                time.sleep(0.1)

            if not triggered:
                self.logger.warning("Trigger timeout")
                return None

            # Capture the waveform
            self.logger.info("Triggered! Capturing waveform...")
            waveform = self.capture_waveform(channel)
            if waveform is None:
                return None

            # Save to CSV with static filename
            filename = os.path.join(output_dir, f"relay_{transition_type}.csv")
            if self.save_waveform_to_csv(waveform, filename):
                return filename
            return None

        except Exception as e:
            self.logger.error(f"Error capturing relay transition: {str(e)}")
            return None

    def analyze_relay_transition(self, waveform_file: str) -> Dict[str, float]:
        """Analyze a relay transition waveform to extract timing parameters.

        Args:
            waveform_file: Path to CSV file containing waveform data

        Returns:
            Dict[str, float]: Dictionary of timing parameters
        """
        try:
            # Use the shared utility function to analyze the waveform
            analysis = analyze_waveform_file(waveform_file)

            # Check if there was an error
            if "error" in analysis:
                self.logger.error(f"Error analyzing waveform: {analysis['error']}")
                return {"error": analysis["error"]}

            # Return the analysis results with additional metadata
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return {
                "transition_type": analysis["transition_type"],
                "transition_time_ms": analysis["transition_time_ms"],  # in ms
                "bounce_count": analysis["bounce_count"],
                "bounce_duration_ms": analysis["bounce_duration_ms"],  # in ms
                "start_voltage": analysis["start_voltage"],
                "end_voltage": analysis["end_voltage"],
                "low_threshold": analysis["thresholds"][0],
                "high_threshold": analysis["thresholds"][1],
                "waveform_file": waveform_file,
                "analysis_timestamp": timestamp,
                "sample_count": len(analysis.get("indices", (0, 0))),
            }

        except Exception as e:
            self.logger.error(f"Error analyzing waveform: {str(e)}")
            return {"error": str(e)}
