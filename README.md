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

## Contributing

Contributions to this example repository are welcome! If you have a useful test flow that demonstrates Onnyx capabilities, please consider submitting it as a pull request.

When contributing:

1. Follow the existing structure for consistency
2. Include comprehensive documentation
3. Ensure your example is self-contained
4. Add your example to the list in this README
