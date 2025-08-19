import os
import csv
import json
from typing import Any, Dict, List, Optional
from onnyx.context import gcc


def get_filepath(filename: str) -> str:
    """Get full file path in the test_outputs directory."""
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


def append_csv(data: List[Dict[str, Any]], filename: str, fieldnames: Optional[List[str]] = None) -> str:
    """Append data to a CSV file and return the filepath. Creates file with header if it doesn't exist."""
    if not data:
        return ""
    
    filepath = get_filepath(filename)
    
    if fieldnames is None:
        fieldnames = list(data[0].keys())
    
    # Check if file exists to determine if we need to write header
    file_exists = os.path.exists(filepath)
    
    with open(filepath, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerows(data)
    
    # Record the file with onnyx agent
    try:
        gcc().record_file(filepath)
    except:
        pass  # Ignore if gcc() is not available
    
    return filepath


def write_json(data: Dict[str, Any], filename_prefix: str) -> str:
    """Write data to a JSON file and return the filepath."""
    filename = f"{filename_prefix}.json"
    filepath = get_filepath(filename)
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    
    # Record the file with onnyx agent
    try:
        gcc().record_file(filepath)
    except:
        pass  # Ignore if gcc() is not available
    
    return filepath