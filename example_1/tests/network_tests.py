import requests
import time
from datetime import datetime
from onnyx.results import TestResult
from onnyx.decorators import test
from onnyx.context import gcc
from onnyx.mqtt import BannerState
from .failure_codes import FailureCodes
from .file_utils import append_csv, write_json


@test()
def check_internet_connection(
    category: str = None,
    test_name: str = None,
    url: str = "https://www.google.com",
    num_pings: int = 5,
    interval: float = 1.0,
):
    """Check if there's an active internet connection and log ping times.

    Args:
        category (str, optional): Test category. Used internally by the test framework.
        test_name (str, optional): Test name. Used internally by the test framework.
        url (str): The URL to test the connection against. Defaults to "https://www.google.com".
        num_pings (int): Number of pings to perform. Defaults to 5.
        interval (float): Time between pings in seconds. Defaults to 1.0.

    Returns:
        TestResult: Test result with possible outcomes:
            - Success (NO_FAILURE):
                "Internet connection successful. Average ping time: {avg_ping:.2f} ms"
                return_value: {
                    "ping_results": List of ping results,
                    "average_ping_ms": Average ping time in milliseconds
                }

            - Failure (INTERNET_CONNECTION_FAILED):
                "Internet connection failed"
                return_value: {
                    "ping_results": List of ping results up to failure
                }
                Condition: Connection error during ping attempts
    """
    context = gcc()  # Get current context
    ping_results = []
    successful_pings = []
    failed_pings = []

    # Only update banner at start and end of test
    context.set_banner("Starting internet connection test", "info", BannerState.SHOWING)

    for i in range(num_pings):
        try:
            start_time = time.time()
            response = requests.get(url, timeout=5)
            end_time = time.time()
            ping_time_ms = (end_time - start_time) * 1000  # Convert to milliseconds
            status = "success"

            result = {
                "ping_number": i + 1,
                "timestamp": datetime.now().isoformat(),
                "url": url,
                "ping_time_ms": round(ping_time_ms, 2),
                "status": status,
                "attempt": i + 1,
                "response_code": response.status_code,
            }

            # Append to CSV file
            append_csv(
                result,
                "ping_results",
                ["ping_number", "timestamp", "url", "ping_time_ms", "status", "attempt", "response_code"]
            )
            
            ping_results.append(result)
            successful_pings.append(ping_time_ms)

            if interval > 0 and i < num_pings - 1:  # Don't sleep after last ping
                time.sleep(interval)

        except requests.ConnectionError as e:
            context.set_banner(
                "Internet connection failed!", "error", BannerState.SHOWING
            )
            result = {
                "ping_number": i + 1,
                "timestamp": datetime.now().isoformat(),
                "url": url,
                "ping_time_ms": None,
                "status": "failed",
                "attempt": i + 1,
                "error": str(e),
            }
            
            # Append to CSV file
            append_csv(
                result,
                "ping_results",
                ["ping_number", "timestamp", "url", "ping_time_ms", "status", "attempt", "error"]
            )
            
            ping_results.append(result)
            failed_pings.append(result)

            # Write detailed failure info to JSON
            failure_details = {
                "test_name": "check_internet_connection",
                "url": url,
                "total_attempts": i + 1,
                "successful_pings": len(successful_pings),
                "failed_at_attempt": i + 1,
                "error": str(e),
                "all_results": ping_results
            }
            json_file = write_json(failure_details, "internet_connection_failure")

            return TestResult(
                "Internet connection failed",
                FailureCodes.INTERNET_CONNECTION_FAILED,
                return_value={
                    "success_count": len(successful_pings),
                    "failure_count": 1,
                    "details_file": json_file
                },
            )

    # Calculate average ping time from successful pings
    avg_ping = sum(successful_pings) / len(successful_pings) if successful_pings else 0

    # Write summary to JSON
    summary = {
        "test_name": "check_internet_connection",
        "url": url,
        "total_pings": num_pings,
        "successful_pings": len(successful_pings),
        "failed_pings": len(failed_pings),
        "average_ping_ms": round(avg_ping, 2),
        "min_ping_ms": round(min(successful_pings), 2) if successful_pings else None,
        "max_ping_ms": round(max(successful_pings), 2) if successful_pings else None,
        "test_duration_seconds": num_pings * interval + sum(successful_pings) / 1000,
        "all_results": ping_results
    }
    json_file = write_json(summary, "internet_connection_summary")

    # Clear the banner on success
    context.set_banner("", state=BannerState.HIDDEN)

    return TestResult(
        f"Internet connection successful. Average ping time: {avg_ping:.2f} ms",
        return_value={
            "average_ping_ms": round(avg_ping, 2),
            "success_rate": f"{len(successful_pings)}/{num_pings}",
            "details_file": json_file
        },
    )