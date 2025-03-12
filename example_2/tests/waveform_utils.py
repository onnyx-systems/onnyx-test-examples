"""
Utility module for waveform analysis.

This module contains functions for analyzing relay transition waveforms,
including detecting transition types, calculating transition times, and
identifying contact bounce.
"""

import numpy as np
from typing import Dict, Any, List, Tuple, Optional, Union


def analyze_waveform(time: np.ndarray, voltage: np.ndarray) -> Dict[str, Any]:
    """Analyze a waveform to extract transition characteristics.

    Args:
        time: Array of time values (in seconds)
        voltage: Array of voltage values

    Returns:
        Dict containing analysis results:
            - transition_type: "rising" or "falling"
            - transition_time: Time in seconds from 10% to 90% of transition
            - bounce_count: Number of bounces detected
            - bounce_duration: Total duration of bounces in seconds
            - start_voltage: Average voltage at start of waveform
            - end_voltage: Average voltage at end of waveform
            - thresholds: Tuple of (low_threshold, high_threshold)
            - indices: Tuple of (start_idx, end_idx) for the main transition
            - bounce_regions: List of (start, end) indices for bounce regions
    """
    # Determine transition type (rising or falling)
    start_voltage = np.mean(voltage[:10])
    end_voltage = np.mean(voltage[-10:])
    is_rising = end_voltage > start_voltage

    # Set thresholds (10% and 90% of transition)
    v_min = min(start_voltage, end_voltage)
    v_max = max(start_voltage, end_voltage)
    v_range = v_max - v_min

    low_threshold = v_min + 0.1 * v_range
    high_threshold = v_min + 0.9 * v_range

    # Find crossing points
    try:
        if is_rising:
            start_idx = np.where(voltage > low_threshold)[0][0]
            end_idx = np.where(voltage > high_threshold)[0][0]
        else:
            start_idx = np.where(voltage < high_threshold)[0][0]
            end_idx = np.where(voltage < low_threshold)[0][0]
    except IndexError:
        # Could not find threshold crossings
        return {
            "error": "Could not find threshold crossings",
            "transition_type": "rising" if is_rising else "falling",
            "start_voltage": start_voltage,
            "end_voltage": end_voltage,
            "thresholds": (low_threshold, high_threshold),
        }

    # Calculate transition time
    transition_time = time[end_idx] - time[start_idx]

    # Detect bounce
    bounce_regions = detect_bounce(
        voltage, time, end_idx, high_threshold, low_threshold, is_rising
    )

    # Calculate total bounce duration
    bounce_duration = sum([time[end] - time[start] for start, end in bounce_regions])

    # Return results
    return {
        "transition_type": "rising" if is_rising else "falling",
        "transition_time": transition_time,
        "transition_time_ms": transition_time * 1000,  # For convenience
        "bounce_count": len(bounce_regions),
        "bounce_duration": bounce_duration,
        "bounce_duration_ms": bounce_duration * 1000,  # For convenience
        "start_voltage": start_voltage,
        "end_voltage": end_voltage,
        "thresholds": (low_threshold, high_threshold),
        "indices": (start_idx, end_idx),
        "bounce_regions": bounce_regions,
    }


def detect_bounce(
    voltage: np.ndarray,
    time: np.ndarray,
    end_idx: int,
    high_threshold: float,
    low_threshold: float,
    is_rising: bool,
) -> List[Tuple[int, int]]:
    """Detect bounce in a waveform after the main transition.

    Args:
        voltage: Array of voltage values
        time: Array of time values
        end_idx: Index where the main transition ends
        high_threshold: High threshold for bounce detection
        low_threshold: Low threshold for bounce detection
        is_rising: Whether the transition is rising or falling

    Returns:
        List of (start, end) index tuples for bounce regions
    """
    bounce_regions = []
    bounce_count = 0
    bounce_start = 0  # Initialize to avoid "used before assignment" error

    if is_rising:
        # Look for drops below high_threshold after end_idx
        for i in range(end_idx + 1, len(voltage) - 1):
            if voltage[i] < high_threshold and voltage[i - 1] >= high_threshold:
                bounce_count += 1
                bounce_start = i
            if (
                bounce_count > 0
                and voltage[i] >= high_threshold
                and voltage[i - 1] < high_threshold
            ):
                bounce_regions.append((bounce_start, i))
    else:
        # Look for rises above low_threshold after end_idx
        for i in range(end_idx + 1, len(voltage) - 1):
            if voltage[i] > low_threshold and voltage[i - 1] <= low_threshold:
                bounce_count += 1
                bounce_start = i
            if (
                bounce_count > 0
                and voltage[i] <= low_threshold
                and voltage[i - 1] > low_threshold
            ):
                bounce_regions.append((bounce_start, i))

    return bounce_regions


def load_waveform_from_csv(filename: str) -> Tuple[np.ndarray, np.ndarray]:
    """Load time and voltage data from a CSV file.

    Args:
        filename: Path to CSV file

    Returns:
        Tuple of (time, voltage) arrays
    """
    data = np.genfromtxt(filename, delimiter=",", skip_header=1)
    time = data[:, 0]
    voltage = data[:, 1]
    return time, voltage


def analyze_waveform_file(filename: str) -> Dict[str, Any]:
    """Analyze a waveform from a CSV file.

    Args:
        filename: Path to CSV file

    Returns:
        Dict containing analysis results
    """
    time, voltage = load_waveform_from_csv(filename)
    return analyze_waveform(time, voltage)
