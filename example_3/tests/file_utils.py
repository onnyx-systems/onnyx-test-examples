"""
File and directory utilities for minimal firmware testing.
"""

import os
import csv
import json
from datetime import datetime


def ensure_directory_exists(directory_path):
    """
    Ensure that a directory exists, creating it if necessary.
    
    Args:
        directory_path (str): Path to the directory
        
    Returns:
        str: The directory path
    """
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)
    return directory_path


def write_csv_file(filename, data, headers=None):
    """
    Write data to a CSV file.
    
    Args:
        filename (str): Path to the CSV file
        data (list): List of rows (each row is a list or dict)
        headers (list, optional): Column headers
    """
    ensure_directory_exists(os.path.dirname(filename) or '.')
    
    with open(filename, 'w', newline='') as csvfile:
        if data and isinstance(data[0], dict):
            # Dictionary data
            fieldnames = headers or list(data[0].keys())
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        else:
            # List data
            writer = csv.writer(csvfile)
            if headers:
                writer.writerow(headers)
            writer.writerows(data)


def write_json_file(filename, data, indent=2):
    """
    Write data to a JSON file.
    
    Args:
        filename (str): Path to the JSON file
        data: Data to write (must be JSON serializable)
        indent (int): JSON indentation level
    """
    ensure_directory_exists(os.path.dirname(filename) or '.')
    
    with open(filename, 'w') as jsonfile:
        json.dump(data, jsonfile, indent=indent)


def read_csv_file(filename):
    """
    Read data from a CSV file.
    
    Args:
        filename (str): Path to the CSV file
        
    Returns:
        list: List of dictionaries (one per row)
    """
    data = []
    with open(filename, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            data.append(row)
    return data


def read_json_file(filename):
    """
    Read data from a JSON file.
    
    Args:
        filename (str): Path to the JSON file
        
    Returns:
        dict/list: The JSON data
    """
    with open(filename, 'r') as jsonfile:
        return json.load(jsonfile)


def get_timestamp_string():
    """
    Get a timestamp string suitable for filenames.
    
    Returns:
        str: Timestamp in YYYYMMDD_HHMMSS format
    """
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def create_output_filename(base_name, extension, output_dir=".", use_timestamp=False):
    """
    Create an output filename with optional timestamp.
    
    Args:
        base_name (str): Base filename without extension
        extension (str): File extension (with or without leading dot)
        output_dir (str): Output directory
        use_timestamp (bool): Whether to include timestamp
        
    Returns:
        str: Full file path
    """
    if not extension.startswith('.'):
        extension = '.' + extension
    
    if use_timestamp:
        timestamp = get_timestamp_string()
        filename = f"{base_name}_{timestamp}{extension}"
    else:
        filename = f"{base_name}{extension}"
    
    return os.path.join(output_dir, filename)