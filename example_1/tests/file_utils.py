import os
import csv
from typing import Any, Dict, List, Optional
from onnyx.context import gcc


def get_output_dir() -> str:
    """Get output directory - subdirectory in DEV mode, root level in agent mode."""
    try:
        context = gcc()
        if context._is_local_mode:  # DEV mode
            output_dir = "test_outputs"
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            return output_dir
        else:  # Agent mode
            return "."  # Root level for agent collection
    except:
        # Fallback if no context available
        return "."


def get_filepath(filename: str) -> str:
    """Get full file path in the appropriate output directory."""
    output_dir = get_output_dir()
    return os.path.join(output_dir, filename)


def write_csv(data: List[Dict[str, Any]], filename: str, fieldnames: Optional[List[str]] = None) -> str:
    """Write data to a CSV file and return the filepath."""
    if not data:
        return ""
    
    filepath = get_filepath(filename)
    
    if fieldnames is None:
        fieldnames = list(data[0].keys())
    
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    
    return filepath