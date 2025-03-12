#!/usr/bin/env python3
"""
Utility script to analyze relay waveforms captured by the oscilloscope and save results to CSV.

Usage:
    python analyze_waveforms.py <waveform_file.csv>
    python analyze_waveforms.py --dir <waveform_directory>
"""

import os
import sys
import argparse
import numpy as np
import glob
import csv
from datetime import datetime

# Add the tests directory to the path to ensure imports work
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests"))

# Import the waveform utilities
try:
    from tests.waveform_utils import analyze_waveform_file, load_waveform_from_csv
except ImportError:
    try:
        import waveform_utils
        from waveform_utils import analyze_waveform_file, load_waveform_from_csv
    except ImportError:
        print("Error: waveform_utils module not found. Cannot proceed with analysis.")
        analyze_waveform_file = None
        load_waveform_from_csv = None


def analyze_and_save_waveform(filename, output_dir=None):
    """Analyze a waveform and save results to CSV.

    Args:
        filename: Path to CSV file containing waveform data
        output_dir: Directory to save results (defaults to same directory as input file)

    Returns:
        dict: Analysis results or None if analysis failed
    """
    if not analyze_waveform_file:
        print(f"Error: Cannot analyze {filename} - waveform_utils module not available")
        return None

    try:
        # Analyze the waveform
        analysis = analyze_waveform_file(filename)

        # Check if there was an error
        if "error" in analysis:
            print(f"Warning: {analysis['error']} in {filename}")
            return None

        # Determine output directory
        if output_dir is None:
            output_dir = os.path.dirname(os.path.abspath(filename))
        os.makedirs(output_dir, exist_ok=True)

        # Create output filename with static name based on the input file
        base_name = os.path.splitext(os.path.basename(filename))[0]
        output_file = os.path.join(output_dir, f"{base_name}_analysis.csv")

        # Save analysis results to CSV
        with open(output_file, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Parameter", "Value"])
            writer.writerow(["Source File", os.path.basename(filename)])
            writer.writerow(["Analysis Time", datetime.now().isoformat()])
            writer.writerow(["Transition Type", analysis["transition_type"]])
            writer.writerow(
                ["Transition Time (ms)", f"{analysis['transition_time_ms']:.6f}"]
            )
            writer.writerow(["Bounce Count", analysis["bounce_count"]])
            writer.writerow(
                ["Bounce Duration (ms)", f"{analysis['bounce_duration_ms']:.6f}"]
            )
            writer.writerow(["Start Voltage (V)", f"{analysis['start_voltage']:.6f}"])
            writer.writerow(["End Voltage (V)", f"{analysis['end_voltage']:.6f}"])

            # Add bounce region details if any
            if analysis["bounce_regions"]:
                writer.writerow([])
                writer.writerow(["Bounce Regions"])
                writer.writerow(["Start Index", "End Index", "Duration (ms)"])

                time, _ = load_waveform_from_csv(filename)
                for start_idx, end_idx in analysis["bounce_regions"]:
                    duration_ms = (time[end_idx] - time[start_idx]) * 1000
                    writer.writerow([start_idx, end_idx, f"{duration_ms:.6f}"])

        print(f"Analysis results saved to {output_file}")
        return analysis

    except Exception as e:
        print(f"Error analyzing {filename}: {str(e)}")
        return None


def analyze_directory(directory, output_dir=None):
    """Analyze all waveforms in a directory and save results.

    Args:
        directory: Directory containing waveform CSV files
        output_dir: Directory to save results (defaults to input directory)
    """
    # Find all CSV files
    csv_files = glob.glob(os.path.join(directory, "*.csv"))

    if not csv_files:
        print(f"No CSV files found in {directory}")
        return

    # Use the directory as output directory if not specified
    if output_dir is None:
        output_dir = os.path.join(directory, "analysis")

    os.makedirs(output_dir, exist_ok=True)

    # Group files by type
    rising_files = [f for f in csv_files if "rising" in f.lower()]
    falling_files = [f for f in csv_files if "falling" in f.lower()]
    other_files = [
        f for f in csv_files if "rising" not in f.lower() and "falling" not in f.lower()
    ]

    # Sort by timestamp (assuming filenames contain timestamps)
    rising_files.sort()
    falling_files.sort()
    other_files.sort()

    # Analyze each file
    all_results = []

    print(f"Analyzing {len(csv_files)} waveform files...")

    # Process rising edge files
    for filename in rising_files:
        result = analyze_and_save_waveform(filename, output_dir)
        if result:
            all_results.append(
                {
                    "filename": os.path.basename(filename),
                    "type": "rising",
                    "transition_time_ms": result["transition_time_ms"],
                    "bounce_count": result["bounce_count"],
                    "bounce_duration_ms": result["bounce_duration_ms"],
                }
            )

    # Process falling edge files
    for filename in falling_files:
        result = analyze_and_save_waveform(filename, output_dir)
        if result:
            all_results.append(
                {
                    "filename": os.path.basename(filename),
                    "type": "falling",
                    "transition_time_ms": result["transition_time_ms"],
                    "bounce_count": result["bounce_count"],
                    "bounce_duration_ms": result["bounce_duration_ms"],
                }
            )

    # Process other files
    for filename in other_files:
        result = analyze_and_save_waveform(filename, output_dir)
        if result:
            all_results.append(
                {
                    "filename": os.path.basename(filename),
                    "type": result["transition_type"],
                    "transition_time_ms": result["transition_time_ms"],
                    "bounce_count": result["bounce_count"],
                    "bounce_duration_ms": result["bounce_duration_ms"],
                }
            )

    # Save summary CSV
    if all_results:
        summary_file = os.path.join(output_dir, "waveform_analysis_summary.csv")
        with open(summary_file, "w", newline="") as csvfile:
            fieldnames = [
                "filename",
                "type",
                "transition_time_ms",
                "bounce_count",
                "bounce_duration_ms",
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for result in all_results:
                writer.writerow(result)

        print(f"Summary of all analyses saved to {summary_file}")
    else:
        print("No successful analyses to summarize")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze relay waveforms and save results to CSV"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("file", nargs="?", help="CSV file to analyze")
    group.add_argument("--dir", help="Directory containing waveform CSV files")
    parser.add_argument("--output", help="Directory to save analysis results")

    args = parser.parse_args()

    if not analyze_waveform_file:
        print(
            "Error: waveform_utils module not available. Cannot proceed with analysis."
        )
        return 1

    if args.file:
        if not os.path.exists(args.file):
            print(f"Error: File {args.file} not found")
            return 1

        analyze_and_save_waveform(args.file, args.output)

    elif args.dir:
        if not os.path.isdir(args.dir):
            print(f"Error: Directory {args.dir} not found")
            return 1

        analyze_directory(args.dir, args.output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
