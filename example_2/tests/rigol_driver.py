import time
import logging
import numpy as np
import os
from typing import Optional, Tuple
import pyvisa

class RigolOscilloscopeDriver:
    """Driver for communicating with Rigol oscilloscope using PyVISA."""

    def __init__(self, ip_address, port=5555, logger=None):
        self.ip_address = ip_address
        self.port = port
        
        # Setup logger if none provided
        if logger is None:
            self.logger = logging.getLogger("RigolDriver")
            if not self.logger.handlers:
                handler = logging.StreamHandler()
                formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)
                self.logger.setLevel(logging.INFO)
        else:
            self.logger = logger
            
        self._rm = None
        self._inst = None
        self.failed = False

    def connect(self) -> bool:
        """Connect to the oscilloscope using multiple resource string formats."""
        try:
            if self._inst is not None:
                return True

            self.logger.info("Creating PyVISA resource manager")
            self._rm = pyvisa.ResourceManager()

            # Try each of these resource strings in sequence
            resource_strings = [
                f"TCPIP::{self.ip_address}::INSTR",
                f"TCPIP0::{self.ip_address}::inst0::INSTR",
                f"TCPIP::{self.ip_address}::{self.port}::SOCKET",
                f"TCPIP0::{self.ip_address}::{self.port}::SOCKET"
            ]

            for resource in resource_strings:
                try:
                    self.logger.info(f"Trying to connect with resource string: {resource}")
                    self._inst = self._rm.open_resource(
                        resource,
                        write_termination='\n',
                        read_termination='\n'
                    )
                    self._inst.timeout = 5000  # 5 second timeout
                    self._inst.clear()  # Clear the device
                    
                    # Test communication
                    idn = self._inst.query("*IDN?")
                    if any(model in idn.upper() for model in ["RIGOL", "DS1", "DS2", "DS4", "DS6", "DS7", "MSO5", "MSO7"]):
                        self.logger.info(f"Successfully connected with: {resource}")
                        self.logger.info(f"Device ID: {idn}")
                        return True
                    else:
                        self.logger.warning(f"Connected but wrong device type: {idn}")
                        self._inst.close()
                        self._inst = None
                except Exception as e:
                    self.logger.debug(f"Failed with resource string {resource}: {e}")
                    if self._inst:
                        try:
                            self._inst.close()
                        except:
                            pass
                        self._inst = None
                    continue

            if self._inst is None:
                self.logger.error("Failed to connect with any resource string")
                self.failed = True
                return False

            return True

        except Exception as e:
            self.logger.error(f"Error connecting to oscilloscope: {e}")
            self.failed = True
            return False

    def disconnect(self):
        """Disconnect from the oscilloscope."""
        try:
            if self._inst:
                self._inst.close()
            self._inst = None
            if self._rm:
                self._rm.close()
            self._rm = None
        except Exception as e:
            self.logger.error(f"Error disconnecting: {e}")

    def send_command(self, command: str):
        """Send a command to the oscilloscope."""
        try:
            if not self._inst:
                self.logger.error("Not connected to oscilloscope")
                return False
            self._inst.write(command)
            return True
        except Exception as e:
            self.logger.error(f"Error sending command '{command}': {e}")
            return False

    def query(self, command: str) -> str:
        """Send a query and get the response."""
        try:
            if not self._inst:
                self.logger.error("Not connected to oscilloscope")
                return ""
            return self._inst.query(command)
        except Exception as e:
            self.logger.error(f"Error querying '{command}': {e}")
            return ""

    def get_idn(self) -> str:
        """Get the oscilloscope's identification string."""
        return self.query("*IDN?")

    def capture_waveform(self, channel: int = 1) -> Optional[np.ndarray]:
        """Capture waveform data from the specified channel."""
        try:
            if not self._inst:
                self.logger.error("Not connected to oscilloscope")
                return None

            # Stop acquisition first
            self.send_command(":STOP")
            time.sleep(0.5)  # Give scope time to stop

            # Set waveform parameters
            self.send_command(":WAV:SOUR CHAN" + str(channel))
            time.sleep(0.1)
            
            # Set memory depth to normal mode (auto)
            self.send_command(":ACQuire:MDEPth AUTO")
            time.sleep(0.1)
            
            # Use NORM mode first to get screen data
            self.send_command(":WAV:MODE NORM")
            time.sleep(0.1)
            self.send_command(":WAV:FORM BYTE")
            time.sleep(0.1)
            
            # Get preamble for scaling
            preamble_str = self.query(":WAV:PRE?")
            if not preamble_str:
                self.logger.error("Failed to get waveform preamble")
                return None

            # Parse preamble
            preamble = [float(x) for x in preamble_str.split(',')]
            if len(preamble) < 10:
                self.logger.error(f"Invalid preamble format: {preamble_str}")
                return None

            format_type = int(preamble[0])  # Should be 0 for BYTE
            points = int(preamble[2])
            xincrement = float(preamble[4])  # Time between points
            xorigin = float(preamble[5])     # Start time
            xreference = float(preamble[6])  # Reference time
            yincrement = float(preamble[7])  # Voltage increment per level
            yorigin = float(preamble[8])     # Voltage origin
            yreference = float(preamble[9])  # Reference level

            self.logger.info(f"Capturing {points} points from channel {channel}")

            # Set the waveform reading range
            self.send_command(":WAV:STAR 1")
            time.sleep(0.1)
            self.send_command(f":WAV:STOP {points}")
            time.sleep(0.1)

            # Read waveform data
            raw_data = self._inst.query_binary_values(
                ':WAV:DATA?',
                datatype='B',
                container=np.array,
                header_fmt='ieee',  # Use standard IEEE header format
                expect_termination=True
            )

            if len(raw_data) == 0:
                self.logger.error("No waveform data received")
                return None

            # Convert raw values to voltages using modified formula to handle vertical position:
            # voltage = (code - yreference) × yincrement + yorigin
            voltages = (raw_data - yreference) * yincrement

            # Calculate time array
            times = np.arange(len(raw_data)) * xincrement + xorigin

            # Return time-voltage pairs
            return np.column_stack((times, voltages))

        except Exception as e:
            self.logger.error(f"Error capturing waveform: {e}")
            return None

    def setup_for_relay_test(
        self, channel: int = 1, timebase: float = 0.01
    ) -> bool:
        """Setup the oscilloscope for relay testing."""
        if not self._inst:
            return False

        try:
            # Reset scope and stop acquisition
            self.send_command("*RST")
            time.sleep(2)  # Give scope time to reset
            self.send_command(":STOP")
            time.sleep(1)

            # Set timebase
            self.send_command(f":TIMebase:SCALe {timebase}")
            time.sleep(0.1)

            # Setup channel with explicit vertical positioning
            self.send_command(f":CHANnel{channel}:DISPlay ON")
            time.sleep(0.1)
            self.send_command(f":CHANnel{channel}:COUPling AC")
            time.sleep(0.1)
            self.send_command(f":CHANnel{channel}:SCALe 50")  # 50V/div
            time.sleep(0.1)
            
            # Zero out any vertical offset and center the position
            self.send_command(f":CHANnel{channel}:OFFSet 0")
            time.sleep(0.1)
            self.send_command(f":CHANnel{channel}:POSition 0")
            time.sleep(0.1)

            # Explicitly set probe ratio
            self.send_command(f":CHANnel{channel}:PROBe 10")  # 10X probe
            time.sleep(0.1)

            # Setup trigger
            self.send_command(":TRIGger:MODE EDGE")
            time.sleep(0.1)
            self.send_command(f":TRIGger:EDGE:SOURce CHANnel{channel}")
            time.sleep(0.1)
            self.send_command(":TRIGger:EDGE:SLOPe POSitive")
            time.sleep(0.1)
            self.send_command(":TRIGger:EDGE:LEVel 25")  # Trigger at 25V
            time.sleep(0.1)

            # Start acquisition
            self.send_command(":RUN")
            time.sleep(0.1)
            self.send_command(":TFORce")  # Force trigger
            time.sleep(1)

            return True

        except Exception as e:
            self.logger.error(f"Error setting up relay test: {e}")
            return False

    def get_screenshot(self) -> Optional[bytes]:
        """Get a screenshot from the oscilloscope."""
        if not self._inst:
            return None

        try:
            self.send_command(":DISP:DATA:FORM BMP")
            raw_data = self._inst.query_binary_values(":DISP:DATA?", datatype='B')
            return bytes(raw_data) if raw_data else None
        except Exception as e:
            self.logger.error(f"Error getting screenshot: {e}")
            return None
