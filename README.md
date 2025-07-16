# Onnyx Test Examples

This repository contains a collection of example test flows for the Onnyx testing framework. These examples demonstrate how to create, configure, and run various types of hardware and software tests using Onnyx.

## Available Examples

### [Example 1: Basic Device Health Check](./example_1/README.md)

A comprehensive device health check that tests various hardware and software components:

- System dependencies verification
- Internet connectivity testing
- Storage drive presence and performance
- Camera functionality
- CPU stress testing
- Screen resolution verification
- Battery status checking
- Interactive user tests

## Getting Started

Each example directory contains:

- A detailed README explaining the test flow
- The main test flow Python script
- Test modules with individual test functions
- Configuration examples

To run an example:

1. Navigate to the example directory
2. Review the README.md for details on the test flow
3. Run the example flow script with appropriate configuration

```bash
cd example_1
python -m example_flow
```

## Example Structure

Each example follows a similar structure:

```
example_X/
├── README.md           # Detailed documentation for the example
├── example_flow.py     # Main test flow implementation
└── tests/              # Directory containing test modules
    └── example_tests.py # Individual test functions
```

## Onnyx Framework Overview

Onnyx is a powerful testing framework designed for hardware and software validation. Key features include:

- **Test Context Management**: Centralized test state and configuration
- **Standardized Test Results**: Consistent reporting of test outcomes
- **Failure Code System**: Detailed error reporting with specific failure codes
- **Test Decorators**: Simplified test function creation with automatic logging
- **Configuration System**: Flexible test configuration via JSON objects
- **Interactive Testing**: Support for tests requiring user interaction
- **MQTT Integration**: Real-time test status reporting

## Creating Your Own Test Flows

To create your own test flow based on these examples:

1. Create a new directory for your test flow
2. Copy the basic structure from an existing example
3. Modify the test functions to suit your needs
4. Update the main flow script to include your test sequence
5. Document your test flow in a README.md file

## Continuous Integration and Deployment

This repository uses GitHub Actions for continuous integration and deployment of test flows to the Onnyx platform. The deployment workflow is defined in `.github/workflows/deploy.yml`.

### How the CI/CD Pipeline Works

When changes are pushed to the `main` branch, a pull request is created targeting the `main` branch, or the workflow is manually triggered, the following automated process occurs:

1. **Checkout**: The repository code is checked out using actions/checkout@v3.
2. **Setup Deployer**: The workflow fetches the latest version of the Onnyx deployer tool:
   - Retrieves metadata about the latest deployer version
   - Downloads the appropriate Linux version of the deployer
   - Makes the deployer executable
3. **Deploy to Onnyx**: The workflow:
   - Verifies that deploy.yaml exists in the repository
   - Updates the deploy.yaml with server configuration (URL, API key, and version)
   - Runs the deployment using the Onnyx deployer tool

The workflow provides detailed error messages at each step and will fail explicitly if any issues are encountered.

### Configuration

The deployment process relies on these GitHub secrets:

- **ONNYX_SERVER_URL**: The URL of the Onnyx server
- **ONNYX_API_KEY**: API key for authentication with the Onnyx server

The version is automatically set to the current commit SHA (`github.sha`).

The workflow preserves your existing `deploy.yaml` configuration and only adds/updates the server connection details.

### Required Files

Each test example must include a `deploy.yaml` file with configuration like:

```yaml
test_global:
  python_version: "3.11.7"
  base_path: "./"
  deploy:
    - files:
        - "requirements.txt"

tests:
  - name: "example_test"
    entry_point: "example_flow.py:example_flow"
    deploy:
      - files:
          - "example_flow.py"
      - folders:
          - "tests"
```

### Manual Deployment

You can trigger the deployment workflow manually through the GitHub Actions interface by selecting the "Deploy Test Flow" workflow and clicking "Run workflow".

### Troubleshooting Deployment

If deployment fails, check the GitHub Actions logs for detailed error messages. Common issues include:

- Invalid API credentials
- Network connectivity problems
- Missing or incorrectly formatted deploy.yaml file
- Server-side issues with the Onnyx platform

### Local Deployment

To deploy locally:

1. Download the latest deployer tool from the Onnyx server
2. Create or update your `deploy.yaml` file with server information:
   ```yaml
   server:
     url: "your-onnyx-server-url"
     api_key: "your-api-key"
   ```
3. Run the deployer: `./deploy_to_onnyx -config deploy.yaml`

## Contributing

Contributions to this example repository are welcome! If you have a useful test flow that demonstrates Onnyx capabilities, please consider submitting it as a pull request.

When contributing:

1. Follow the existing structure for consistency
2. Include comprehensive documentation
3. Ensure your example is self-contained
4. Add your example to the list in this README
