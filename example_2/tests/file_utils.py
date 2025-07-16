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


def write_measurements_csv(measurements: Dict[str, Any], filename: str) -> str:
    """Write measurements dictionary to CSV file (flattened format)."""
    try:
        # Flatten nested dictionaries
        flat_data = {}
        for key, value in measurements.items():
            if isinstance(value, dict):
                for subkey, subvalue in value.items():
                    flat_data[f"{key}_{subkey}"] = subvalue
            elif isinstance(value, list):
                for i, val in enumerate(value):
                    flat_data[f"{key}_{i+1}"] = val
            else:
                flat_data[key] = value
        
        # Write to CSV
        filepath = get_filepath(filename)
        with open(filepath, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=flat_data.keys())
            writer.writeheader()
            writer.writerow(flat_data)
        
        return filepath
            
    except Exception as e:
        try:
            context = gcc()
            context.logger.error(f"Error saving measurements to CSV: {str(e)}")
        except:
            print(f"Error saving measurements to CSV: {str(e)}")
        return ""


def save_numpy_array(data, filename: str, delimiter: str = ',', header: str = '') -> str:
    """Save numpy array to file in the appropriate output directory."""
    import numpy as np
    
    filepath = get_filepath(filename)
    np.savetxt(filepath, data, delimiter=delimiter, header=header, comments='')
    return filepath 