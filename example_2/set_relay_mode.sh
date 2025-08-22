#!/bin/bash

# Relay Mode Control Script
# Usage: ./set_relay_mode.sh [mode]
# Modes: normal, stuck-on, stuck-off, status

SERIAL_PORT="/dev/ttyUSB0"
BAUD_RATE=115200

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to send command to relay using Python
send_command() {
    local cmd="$1"
    echo -e "${YELLOW}Sending: $cmd${NC}"
    
    # Use Python for more reliable serial communication
    python3 -c "
import serial
import time

try:
    ser = serial.Serial('$SERIAL_PORT', $BAUD_RATE, timeout=1)
    time.sleep(0.1)  # Wait for connection
    
    # Send command
    ser.write(b'$cmd\n')
    time.sleep(0.3)
    
    # Read response
    response = ser.read(100).decode('utf-8', errors='ignore').strip()
    if response:
        print('Response:', response)
    else:
        print('No response received')
    
    ser.close()
except Exception as e:
    print(f'Error: {e}')
" | while IFS= read -r line; do
    if [[ $line == Response:* ]]; then
        echo -e "${GREEN}${line}${NC}"
    elif [[ $line == Error:* ]]; then
        echo -e "${RED}${line}${NC}"
    else
        echo "$line"
    fi
done
}

# Check if serial port exists
if [ ! -e "$SERIAL_PORT" ]; then
    echo -e "${RED}Error: Serial port $SERIAL_PORT not found${NC}"
    exit 1
fi

# Check if Python and pyserial are available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python3 is required${NC}"
    exit 1
fi

if ! python3 -c "import serial" 2>/dev/null; then
    echo -e "${RED}Error: Python serial module not found${NC}"
    echo "Install with: pip install pyserial"
    exit 1
fi

# Parse command line argument
case "${1,,}" in
    normal|clear)
        echo -e "${BLUE}Setting relay to NORMAL mode (clearing simulations)${NC}"
        send_command "FAIL CLEAR"
        ;;
    stuck-on|stuckon|on)
        echo -e "${BLUE}Setting relay to STUCK ON mode${NC}"
        send_command "SIMULATE STUCK ON"
        ;;
    stuck-off|stuckoff|off)
        echo -e "${BLUE}Setting relay to STUCK OFF mode${NC}"
        send_command "SIMULATE STUCK OFF"
        ;;
    status|info)
        echo -e "${BLUE}Getting relay status${NC}"
        send_command "STATUS"
        ;;
    relay-on|1on)
        echo -e "${BLUE}Turning relay ON${NC}"
        send_command "1ON"
        ;;
    relay-off|1off)
        echo -e "${BLUE}Turning relay OFF${NC}"
        send_command "1OFF"
        ;;
    version)
        echo -e "${BLUE}Getting firmware version${NC}"
        send_command "VERSION"
        ;;
    help|--help|-h|"")
        echo "Relay Mode Control Script"
        echo "Usage: $0 [mode]"
        echo ""
        echo "Available modes:"
        echo "  normal       - Set relay to normal operation"
        echo "  stuck-on     - Simulate relay stuck ON"
        echo "  stuck-off    - Simulate relay stuck OFF"
        echo "  status       - Get current relay status"
        echo "  relay-on     - Turn relay ON"
        echo "  relay-off    - Turn relay OFF"
        echo "  version      - Get firmware version"
        echo "  help         - Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0 normal"
        echo "  $0 stuck-on"
        echo "  $0 status"
        ;;
    *)
        echo -e "${RED}Error: Unknown mode '$1'${NC}"
        echo "Use '$0 help' for available options"
        exit 1
        ;;
esac