import numpy as np
from typing import Dict, Any, Optional, Tuple
import csv

def analyze_waveform_file(filename: str) -> Dict[str, Any]:
    """Analyze a waveform CSV file to extract key measurements.
    
    Args:
        filename: Path to CSV file with Time (s), Voltage (V) columns
        
    Returns:
        Dict containing:
        - frequency_hz: Frequency in Hz
        - peak_to_peak_v: Peak-to-peak voltage in V
        - rms_v: RMS voltage in V
        - mean_v: Mean voltage in V
        - has_signal: True if AC signal detected
    """
    try:
        # Read CSV file
        time_data = []
        voltage_data = []
        with open(filename, 'r') as f:
            reader = csv.reader(f)
            # Skip header
            next(reader)
            for row in reader:
                time_data.append(float(row[0]))
                voltage_data.append(float(row[1]))
                
        time_array = np.array(time_data)
        voltage_array = np.array(voltage_data)
        
        # Calculate basic statistics
        peak_to_peak = np.ptp(voltage_array)
        mean = np.mean(voltage_array)
        rms = np.sqrt(np.mean(voltage_array**2))
        
        # Detect zero crossings to calculate frequency
        zero_crossings = np.where(np.diff(np.signbit(voltage_array - mean)))[0]
        if len(zero_crossings) >= 2:
            # Calculate periods between zero crossings
            periods = np.diff(time_array[zero_crossings])
            # Average period (two crossings = one period)
            avg_period = np.mean(periods) * 2
            frequency = 1.0 / avg_period
        else:
            frequency = 0.0
            
        # Determine if we have a valid AC signal
        # Criteria: 
        # 1. Frequency between 45-65 Hz (for 50/60 Hz AC)
        # 2. Peak-to-peak voltage > 20V
        # 3. RMS voltage > 10V
        has_signal = (
            45 <= frequency <= 65 and
            peak_to_peak > 20 and
            rms > 10
        )
        
        return {
            "frequency_hz": frequency,
            "peak_to_peak_v": peak_to_peak,
            "rms_v": rms,
            "mean_v": mean,
            "has_signal": has_signal,
            "num_samples": len(voltage_array),
            "duration_s": time_array[-1] - time_array[0]
        }
        
    except Exception as e:
        print(f"Error analyzing waveform file: {str(e)}")
        return {
            "frequency_hz": 0.0,
            "peak_to_peak_v": 0.0,
            "rms_v": 0.0,
            "mean_v": 0.0,
            "has_signal": False,
            "num_samples": 0,
            "duration_s": 0.0,
            "error": str(e)
        } 