import os
import csv
import json
import shutil
from typing import Any, Dict, List, Optional
from onnyx.context import gcc


def get_filepath(filename: str) -> str:
    """Get full file path for the given filename.
    
    In production mode, files should be created in the working directory
    so they can be properly uploaded via record_file().
    In development mode, files are created in test_outputs/ directory.
    """
    try:
        context = gcc()
        # Check if we're in local mode (development)
        if hasattr(context, '_is_local_mode') and context._is_local_mode:
            # Local development mode - use test_outputs directory
            output_dir = "test_outputs"
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            return os.path.join(output_dir, filename)
        else:
            # Production mode - create files in working directory for upload
            # Also check if onnyx_test_dir exists and copy there
            onnyx_dir = "onnyx_test_dir/files_to_upload"
            if os.path.exists(onnyx_dir):
                filepath = os.path.join(onnyx_dir, filename)
            else:
                filepath = filename
            return filepath
    except:
        # If no context available, assume development mode
        output_dir = "test_outputs"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
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
    
    # Record the file with onnyx agent
    try:
        gcc().record_file(filepath)
    except:
        pass  # Ignore if gcc() is not available
    
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
        
        # Record the file with onnyx agent
        try:
            gcc().record_file(filepath)
        except:
            pass  # Ignore if gcc() is not available
        
        return filepath
            
    except Exception as e:
        try:
            context = gcc()
            context.logger.error(f"Error saving measurements to CSV: {str(e)}")
        except:
            print(f"Error saving measurements to CSV: {str(e)}")
        return ""


def write_measurements_json(measurements: Dict[str, Any], filename: str) -> str:
    """Write measurements dictionary to JSON file."""
    try:
        filepath = get_filepath(filename)
        
        # Convert any numpy arrays or non-serializable types to lists
        def convert_to_serializable(obj):
            import numpy as np
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, (np.integer, np.floating)):
                return obj.item()
            elif isinstance(obj, dict):
                return {k: convert_to_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_to_serializable(item) for item in obj]
            return obj
        
        serializable_data = convert_to_serializable(measurements)
        
        # Write to JSON with pretty formatting
        with open(filepath, 'w') as jsonfile:
            json.dump(serializable_data, jsonfile, indent=2)
        
        # Record the file with onnyx agent
        try:
            gcc().record_file(filepath)
        except:
            pass  # Ignore if gcc() is not available
        
        return filepath
            
    except Exception as e:
        try:
            context = gcc()
            context.logger.error(f"Error saving measurements to JSON: {str(e)}")
        except:
            print(f"Error saving measurements to JSON: {str(e)}")
        return ""


def save_numpy_array(data, filename: str, delimiter: str = ',', header: str = '') -> str:
    """Save numpy array to file in the appropriate output directory."""
    import numpy as np
    
    filepath = get_filepath(filename)
    np.savetxt(filepath, data, delimiter=delimiter, header=header, comments='')
    
    # Record the file with onnyx agent
    try:
        gcc().record_file(filepath)
    except:
        pass  # Ignore if gcc() is not available
    
    return filepath