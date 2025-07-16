# Onnyx Example Test Flow

This document explains the example test flow in a way that's easy to understand for non-programmers and developers alike.

## What This Test Does

This test is designed to verify that a device (like a laptop or computer) is functioning correctly by running a series of checks. Think of it like a health check-up for your computer that tests various components:

- System dependencies (required software)
- Internet connection reliability
- Storage drive presence and accessibility
- Disk write speed performance
- Camera functionality (optional)
- CPU performance under stress
- Screen resolution verification
- Battery status and health (if applicable)

## Test Flow Diagram

```mermaid
flowchart TD
    Start([Start Test]) --> Init[Initialize Test Context]
    Init --> SysDep[Check System Dependencies]

    SysDep -->|Success| Internet[Check Internet Connection]
    SysDep -->|Failure| Fail([Test Failed])

    Internet -->|Success| DriveCheck[Check Drive Presence]
    Internet -->|Failure| Fail

    DriveCheck -->|Success| DiskTest[Disk Write Speed Test]
    DriveCheck -->|Failure| Fail

    DiskTest -->|Success| CameraTest{Camera Test Enabled?}
    DiskTest -->|Failure| Fail

    CameraTest -->|Yes| Camera[Take Picture]
    CameraTest -->|No| CPUTest[CPU Stress Test]

    Camera -->|Success| CPUTest
    Camera -->|Failure| Fail

    CPUTest -->|Success| ScreenRes[Get Screen Resolution]
    CPUTest -->|Failure| Fail

    ScreenRes -->|Success| BatteryTest{Battery Test Enabled?}
    ScreenRes -->|Failure| Fail

    BatteryTest -->|Yes| Battery[Check Battery Status]
    BatteryTest -->|No| Success([Test Succeeded])

    Battery -->|Success| Success
    Battery -->|Failure| Fail
```

## Configuration Options Explained

The test uses a configuration object called `_cell_config_obj` that controls how the tests run. Here's what each setting does:

| Setting                   | Description                                  | Default Value                  |
| ------------------------- | -------------------------------------------- | ------------------------------ |
| `battery_test_enable`     | Whether to check the battery status          | `False`                        |
| `cpu_stress_duration`     | How long to stress test the CPU (in seconds) | `5`                            |
| `cpu_usage_range`         | Acceptable range for CPU usage (%)           | `{"min": 1, "max": 100}`       |
| `drive_letter`            | Which drive to check                         | `"C"` on Windows, `/` on Linux |
| `enable_camera_test`      | Whether to test the camera                   | `False`                        |
| `min_write_speed_mbps`    | Minimum acceptable disk write speed (MB/s)   | `10`                           |
| `num_test_files`          | Number of files to create during disk test   | `10`                           |
| `ping_url`                | Website to ping for internet test            | `"https://www.google.com"`     |
| `num_pings`               | Number of pings to perform                   | `5`                            |
| `ping_interval`           | Time between pings in seconds                | `1.0`                          |
| `write_speed_mbps`        | Acceptable range for disk write speed        | `{"min": 300, "max": 10000}`   |
| `skip_screen_resolution_check` | Skip screen resolution test for headless systems | `False`              |

## Configuration to Test Relationship

```mermaid
flowchart LR
    subgraph Config["Configuration Options"]
        ping_url["ping_url"]
        num_pings["num_pings"]
        ping_interval["ping_interval"]
        drive_letter["drive_letter"]
        min_write_speed["min_write_speed_mbps"]
        num_test_files["num_test_files"]
        write_speed_range["write_speed_mbps"]
        enable_camera["enable_camera_test"]
        cpu_duration["cpu_stress_duration"]
        cpu_range["cpu_usage_range"]
        battery_enable["battery_test_enable"]
        skip_screen["skip_screen_resolution_check"]
    end

    subgraph Tests["Test Functions"]
        internet["Internet Connection Test"]
        drive["Drive Presence Check"]
        disk["Disk Write Speed Test"]
        camera["Camera Test"]
        cpu["CPU Stress Test"]
        screen["Screen Resolution Check"]
        battery["Battery Status Check"]
    end

    ping_url --> internet
    num_pings --> internet
    ping_interval --> internet
    drive_letter --> drive
    min_write_speed --> disk
    num_test_files --> disk
    write_speed_range --> disk
    enable_camera --> camera
    cpu_duration --> cpu
    cpu_range --> cpu
    battery_enable --> battery
    skip_screen --> screen
```

## Test Components Diagram

```mermaid
classDiagram
    class TestFlow {
        +Initialize context
        +Run tests
        +Record results
        +Report failures
    }

    class SystemTests {
        +check_system_dependencies()
        +check_internet_connection()
        +is_drive_present()
    }

    class StorageTests {
        +disk_test()
    }

    class HardwareTests {
        +take_picture()
        +cpu_stress_test()
        +get_screen_resolution()
        +check_battery_status()
    }

    TestFlow --> SystemTests: runs
    TestFlow --> StorageTests: runs
    TestFlow --> HardwareTests: runs
```

## How Each Test Works

### System Dependencies Check

Verifies that all required software is installed on the computer. This ensures that the test environment has all necessary tools to run the subsequent tests.

### Internet Connection Test

Pings a website (default: Google) to check if the internet is working. The test measures response times and verifies connectivity by sending multiple ping requests.

### Drive Presence Check

Verifies that the specified drive (C: on Windows, / on Linux) exists and is accessible. This is a fundamental check to ensure storage is available.

### Disk Write Speed Test

Creates test files and measures how fast data can be written to disk. This test helps identify storage performance issues by writing multiple files and calculating the throughput.

### Camera Test

If enabled, takes a picture using the computer's camera and analyzes the image. This verifies that the camera hardware is functioning correctly and can capture images.

### CPU Stress Test

Runs intensive calculations to test CPU performance under load. This test helps identify potential thermal throttling or performance issues by pushing the CPU to high utilization.

### Screen Resolution Check

Gets the current screen resolution and verifies it meets minimum requirements. This ensures the display is functioning at the expected resolution.

### Battery Status Check

If enabled, checks the battery level and charging status. This test verifies that the battery is present, can hold a charge, and reports its status correctly.

## Test Results

Each test returns one of these results:

- **Success**: The test passed all checks
- **Failure**: The test failed with a specific error code (see Failure Codes section)
- **Exception**: An unexpected error occurred during test execution

## Test Output Files

The test framework creates detailed output files in the `test_outputs/` directory. These files contain comprehensive data about each test run:

### CSV Files (Data Logs)
- **`ping_results.csv`**: Network ping test results with response times
  - Format: `ping_number,timestamp,url,ping_time_ms,status,attempt,response_code`
- **`cpu_stress_samples.csv`**: CPU usage samples during stress testing
  - Format: `sample_number,timestamp,cpu_percent,test_phase`
- **`disk_test_results.csv`**: Disk write test results for each file
  - Format: `file,write_time_seconds,write_speed_mbps,file_size_mb,start_time,end_time`

### JSON Files (Test Summaries)
- **`system_dependencies_report.json`**: System dependency check results
- **`internet_connection_summary.json`**: Internet connection test summary with statistics
- **`internet_connection_failure.json`**: Internet connection failure details (if test fails)
- **`drive_check_success.json`**: Drive presence verification results
- **`drive_check_failure.json`**: Drive check failure details (if test fails)
- **`disk_test_summary.json`**: Disk performance test results and file write speeds
- **`disk_test_speed_failure.json`**: Disk speed failure details (if speed is out of range)
- **`disk_test_failure.json`**: Disk test failure details (if test fails)
- **`camera_test_results.json`**: Camera test results with image analysis metrics
- **`cpu_stress_summary.json`**: CPU stress test results and performance metrics
- **`cpu_stress_failure.json`**: CPU stress test failure details (if test fails)
- **`screen_resolution_results.json`**: Screen resolution detection results
- **`screen_resolution_headless.json`**: Screen resolution info for headless environments
- **`battery_status_results.json`**: Battery status and charging information

### File Structure Example
```
test_outputs/
├── ping_results.csv
├── cpu_stress_samples.csv
├── disk_test_results.csv
├── system_dependencies_report.json
├── internet_connection_summary.json
├── drive_check_success.json
├── disk_test_summary.json
├── camera_test_results.json
├── cpu_stress_summary.json
├── screen_resolution_results.json
└── battery_status_results.json
```

## How to Run the Test

The test is run by executing the `example_flow.py` script, which uses the configuration settings to determine which tests to run and what parameters to use.

```python
# Example of running the test
from example_flow import example_flow

# Create test document with configuration
test_document = {
    "_cell_config_obj": {
        "battery_test_enable": False,
        "cpu_stress_duration": 5,
        "cpu_usage_range": {"max": 100, "min": 1},
        "drive_letter": "C",
        "enable_camera_test": False,
        "num_test_files": 10,
        "ping_url": "https://www.google.com",
        "write_speed_mbps": {"max": 10000, "min": 300},
        "skip_screen_resolution_check": False,
    },
    "_cell_settings_obj": {
        "not_used_in_this_example": "This is not used in this example",
    }
}

# Run the test flow
example_flow(test_document, "DEV")
```

## Failure Codes

When a test fails, it returns a specific failure code that helps identify what went wrong:

```mermaid
classDiagram
    class FailureCodes {
        +NO_FAILURE: 0
        +EXCEPTION: -999
        +INTERNET_CONNECTION_FAILED: -1
        +DRIVE_NOT_PRESENT: -2
        +ERROR_CREATING_DATA: -3
        +ERROR_SAVING_DATA: -4
        +NO_BATTERY: -5
        +CAMERA_NOT_AVAILABLE: -6
        +IMAGE_CAPTURE_FAILED: -7
        +WRITE_SPEED_BELOW_MIN: -8
        +MISSING_DEPENDENCIES: -9
        +CPU_PERFORMANCE_FAILED: -10
    }
```

## Troubleshooting Common Issues

If tests fail, here are some common solutions:

| Failure Code               | Possible Solutions                                                 |
| -------------------------- | ------------------------------------------------------------------ |
| INTERNET_CONNECTION_FAILED | Check network cables, Wi-Fi connection, or try a different network |
| DRIVE_NOT_PRESENT          | Verify drive is properly connected and mounted                     |
| WRITE_SPEED_BELOW_MIN      | Check for disk fragmentation or hardware issues                    |
| MISSING_DEPENDENCIES       | Install required software packages                                 |
| CAMERA_NOT_AVAILABLE       | Check camera drivers or hardware connections                       |
| CPU_PERFORMANCE_FAILED     | Check for thermal throttling or background processes               |
| NO_BATTERY                 | Connect battery or run on a device with battery                    |
| ERROR_CREATING_DATA        | Check file system permissions and available disk space            |
| ERROR_SAVING_DATA          | Verify disk write permissions and available storage               |
| IMAGE_CAPTURE_FAILED       | Check camera connectivity and try restarting the camera driver    |

## Extending the Test Flow

To add new tests to the flow:

1. Create a new test function in `example_tests.py` using the `@test()` decorator
2. Add appropriate failure codes to the `FailureCodes` class
3. Update the `example_flow.py` to include your new test in the flow
4. Add any new configuration options to the `_cell_config_obj`
