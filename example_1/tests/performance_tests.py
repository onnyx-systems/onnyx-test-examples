import time
import psutil
from onnyx.results import TestResult
from onnyx.decorators import test
from onnyx.context import gcc
from onnyx.mqtt import BannerState
from onnyx.utils import range_check_list
from onnyx.failure import BaseFailureCodes
from .failure_codes import FailureCodes
from .file_utils import write_json, write_csv


@test()
def cpu_stress_test(
    category: str = None, test_name: str = None, duration_seconds: int = 5
):
    """Perform a CPU stress test for a specified duration.
    Uses a computationally intensive single-threaded operation to stress test the CPU.

    Args:
        category (str, optional): Test category. Used internally by the test framework.
        test_name (str, optional): Test name. Used internally by the test framework.
        duration_seconds (int): Duration of the stress test in seconds.

    Returns:
        TestResult: Test result with possible outcomes:
            - Success (NO_FAILURE):
                "CPU stress test completed successfully"
                return_value: {
                    "duration_seconds": Actual test duration,
                    "operations_completed": Number of operations performed,
                    "initial_cpu_percent": Initial CPU usage percentage,
                    "final_cpu_percent": Final CPU usage percentage,
                    "cpu_cores": Number of CPU cores,
                    "cpu_freq": CPU frequency information dictionary,
                    "cpu_percentages": List of CPU usage percentages
                }

            - Failure (CPU_PERFORMANCE_FAILED):
                "CPU usage out of expected range: {message}"
                return_value: Same as success
                Condition: CPU usage outside configured range

            - Failure (EXCEPTION):
                "Error during CPU stress test: {error}"
                Condition: Exception during test execution
    """
    try:
        context = gcc()
        start_time = time.time()
        end_time = start_time + duration_seconds
        operations_count = 0
        last_banner_update = start_time
        BANNER_UPDATE_INTERVAL = 0.5  # Update banner every 0.5 seconds
        cpu_percentages = []  # List to store CPU percentages for range check

        # Get initial CPU usage
        initial_cpu_percent = psutil.cpu_percent(interval=0.1)
        context.set_banner(
            f"Starting CPU stress test ({duration_seconds}s)",
            "info",
            BannerState.SHOWING,
        )

        # Run CPU-intensive calculations
        while time.time() < end_time:
            # Matrix operations and other CPU-intensive calculations
            for _ in range(10000):
                _ = sum(i * i for i in range(100))
            operations_count += 1

            # Update banner less frequently
            current_time = time.time()
            if current_time - last_banner_update >= BANNER_UPDATE_INTERVAL:
                elapsed = current_time - start_time
                remaining = max(0, duration_seconds - elapsed)
                current_cpu = psutil.cpu_percent(interval=0.1)
                if current_cpu > 0:  # Only store non-zero CPU percentages
                    cpu_percentages.append(current_cpu)
                context.set_banner(
                    f"CPU Test: {remaining:.1f}s remaining | CPU Usage: {current_cpu}%",
                    "warning" if current_cpu > 80 else "info",
                    BannerState.SHOWING,
                )
                last_banner_update = current_time

        actual_duration = time.time() - start_time

        # Get final CPU usage
        final_cpu_percent = psutil.cpu_percent(interval=0.1)
        if final_cpu_percent > 0:
            cpu_percentages.append(final_cpu_percent)

        # If no valid CPU measurements, try to get one more measurement
        if not cpu_percentages:
            context.logger.warning("No valid CPU measurements captured, attempting final measurement")
            final_measurement = psutil.cpu_percent(interval=0.5)
            if final_measurement > 0:
                cpu_percentages.append(final_measurement)
            else:
                # If still no valid measurement, use initial CPU percent
                if initial_cpu_percent > 0:
                    cpu_percentages.append(initial_cpu_percent)
                else:
                    # As last resort, add a minimal value to avoid empty list
                    cpu_percentages.append(1.0)
                    context.logger.warning("Unable to capture valid CPU usage, using minimum value")

        # Check CPU usage range
        cellConfig = context.document.get("_cell_config_obj", {})

        rc = range_check_list(
            cpu_percentages, "cpu_usage_range", cellConfig, prefix="cpu_stress"
        )

        # Prepare CPU performance data
        cpu_freq_info = psutil.cpu_freq()._asdict() if psutil.cpu_freq() else {}
        
        # Write detailed CPU metrics to CSV
        cpu_samples = []
        for i, cpu_pct in enumerate(cpu_percentages):
            cpu_samples.append({
                "sample_number": i + 1,
                "timestamp": time.time() - (len(cpu_percentages) - i - 1) * BANNER_UPDATE_INTERVAL,
                "cpu_percent": cpu_pct,
                "test_phase": "stress_test"
            })
        
        if cpu_samples:
            csv_file = write_csv(cpu_samples, "cpu_stress_samples")
        
        # Prepare comprehensive test summary
        test_summary = {
            "test_name": "cpu_stress_test",
            "status": "completed",
            "test_parameters": {
                "duration_requested_seconds": duration_seconds,
                "duration_actual_seconds": actual_duration,
                "sample_interval_seconds": BANNER_UPDATE_INTERVAL
            },
            "performance_metrics": {
                "operations_completed": operations_count,
                "operations_per_second": round(operations_count / actual_duration, 2),
                "initial_cpu_percent": initial_cpu_percent,
                "final_cpu_percent": final_cpu_percent,
                "average_cpu_percent": round(sum(cpu_percentages) / len(cpu_percentages), 2) if cpu_percentages else 0,
                "min_cpu_percent": min(cpu_percentages) if cpu_percentages else 0,
                "max_cpu_percent": max(cpu_percentages) if cpu_percentages else 0
            },
            "system_info": {
                "cpu_cores_logical": psutil.cpu_count(),
                "cpu_cores_physical": psutil.cpu_count(logical=False),
                "cpu_frequency_current_mhz": cpu_freq_info.get('current', 0),
                "cpu_frequency_min_mhz": cpu_freq_info.get('min', 0),
                "cpu_frequency_max_mhz": cpu_freq_info.get('max', 0)
            },
            "cpu_samples": cpu_samples,
            "timestamp": time.time()
        }

        if rc.failure_code != BaseFailureCodes.NO_FAILURE:
            test_summary["status"] = "failed"
            test_summary["failure_reason"] = f"CPU usage out of expected range: {rc.message}"
            test_summary["expected_range"] = cellConfig.get("cpu_usage_range")
            
            json_file = write_json(test_summary, "cpu_stress_failure")
            
            return TestResult(
                f"CPU usage out of expected range: {rc.message}",
                FailureCodes.CPU_PERFORMANCE_FAILED,
                return_value={
                    "test_failed": True,
                    "average_cpu": round(sum(cpu_percentages) / len(cpu_percentages), 2) if cpu_percentages else 0,
                    "details_file": json_file
                },
            )

        # Write success summary
        json_file = write_json(test_summary, "cpu_stress_summary")
        
        return TestResult(
            f"CPU stress test completed successfully",
            FailureCodes.NO_FAILURE,
            return_value={
                "average_cpu": round(sum(cpu_percentages) / len(cpu_percentages), 2) if cpu_percentages else 0,
                "operations_per_second": round(operations_count / actual_duration, 2),
                "details_file": json_file
            },
        )
    except Exception as e:
        if "context" in locals():
            context.set_banner(
                f"CPU test failed: {str(e)}", "error", BannerState.SHOWING
            )
        return TestResult(
            f"Error during CPU stress test: {e}",
            FailureCodes.EXCEPTION,
        )