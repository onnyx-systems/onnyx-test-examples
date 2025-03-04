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

This repository uses GitHub Actions for continuous integration and deployment of test flows to the Onnyx platform. The deployment process is automated through a workflow defined in `.github/workflows/deploy.yml`.

### How the CI/CD Pipeline Works

When changes are pushed to the `main` branch or a pull request is created targeting the `main` branch, the following automated process occurs:

1. **Checkout**: The repository code is checked out.
2. **Setup Deployer**: The workflow fetches the latest version of the Onnyx deployer tool from the Onnyx server and prepares it for use.
3. **Deploy to Onnyx**: The workflow updates the existing `deploy.yaml` file with server connection details and runs the deployment process.

The workflow is designed to fail explicitly if any step encounters an issue, making troubleshooting straightforward.

### Configuration

The deployment process uses the following configuration:

- **Server URL**: Configured via the `ONNYX_SERVER_URL` GitHub secret
- **API Key**: Configured via the `ONNYX_API_KEY` GitHub secret
- **Version**: Automatically set to the current commit SHA

The workflow preserves your existing `deploy.yaml` file configuration and only adds/updates the server connection details. This means you can maintain your test configuration in the repository while the sensitive server details are securely stored as GitHub secrets.

### Manual Deployment

You can also trigger the deployment workflow manually through the GitHub Actions interface by selecting the "Deploy Test Flow" workflow and clicking "Run workflow".

### Troubleshooting Deployment

If the deployment fails, check the GitHub Actions logs for detailed error messages. The workflow is designed to fail explicitly at any step that encounters an issue, with no fallback mechanisms. Common issues include:

- Invalid API credentials
- Network connectivity problems
- Missing deploy.yaml file (the workflow requires an existing deploy.yaml file)
- Incorrectly formatted deploy.yaml file
- Server-side issues with the Onnyx platform
- Missing or invalid deployer version metadata

### Local Deployment

To deploy from your local machine instead of using the CI/CD pipeline:

1. Download the latest deployer tool from the Onnyx server
2. Update your `deploy.yaml` file with your server URL and API key in the server section:
   ```yaml
   server:
     url: "your-onnyx-server-url"
     api_key: "your-api-key"
   ```
3. Run the deployer tool with the command: `./deploy_to_onnyx -config deploy.yaml`

## Contributing

Contributions to this example repository are welcome! If you have a useful test flow that demonstrates Onnyx capabilities, please consider submitting it as a pull request.

When contributing:

1. Follow the existing structure for consistency
2. Include comprehensive documentation
3. Ensure your example is self-contained
4. Add your example to the list in this README
