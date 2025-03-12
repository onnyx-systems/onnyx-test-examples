import re
from typing import Optional


def extract_version_numbers(version_str: str) -> str:
    """Extract the numeric part of a version string.

    Args:
        version_str: The version string to parse (e.g., "14.5.0(release-tasmota)")

    Returns:
        The numeric part of the version string (e.g., "14.5.0")
    """
    numeric_part = re.match(r"(\d+(\.\d+)*)", version_str)
    if numeric_part:
        return numeric_part.group(1)
    return version_str


def compare_versions(current_version: str, min_version: str) -> bool:
    """Compare two version strings to determine if current_version meets or exceeds min_version.

    Args:
        current_version: The current version string
        min_version: The minimum required version string

    Returns:
        True if current_version meets or exceeds min_version, False otherwise
    """
    # Clean up version strings to get just the numeric parts
    clean_current = extract_version_numbers(current_version)
    clean_min = extract_version_numbers(min_version)

    # Split version strings into components and convert to integers
    try:
        current_parts = [int(p) for p in clean_current.split(".")]
        min_parts = [int(p) for p in clean_min.split(".")]

        # Pad with zeros if needed
        while len(current_parts) < len(min_parts):
            current_parts.append(0)
        while len(min_parts) < len(current_parts):
            min_parts.append(0)

        # Compare version components
        for i in range(len(current_parts)):
            if current_parts[i] > min_parts[i]:
                return True
            elif current_parts[i] < min_parts[i]:
                return False
            # If equal, continue to next component

        # All components are equal
        return True
    except Exception:
        # If version comparison fails, return False to be safe
        return False
