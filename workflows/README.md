# Workflow Use - AI Hybrid Testing Framework

A comprehensive hybrid testing framework that combines AI-powered automation with deterministic workflows for web application testing.

## Features

- **Hybrid Testing Approach**: Combines AI agents with traditional automation
- **Workflow Management**: Create, edit, and run deterministic workflows
- **Test Case Management**: Comprehensive test cases for various scenarios
- **Browser Automation**: Powered by browser-use and Playwright
- **AI Integration**: Uses AWS Bedrock for intelligent test execution
- **CLI Interface**: Easy-to-use command line interface

## Installation

```bash
# Install dependencies
uv sync

# Set up AWS credentials for Bedrock access
aws sso login --profile aws-bedrock-access-027283923462
```

## Usage

### Running Test Cases

```bash
# Run a specific test case
uv run python cli.py run-test testcases/pay_supplements.txt

# Run test cases from different categories
uv run python cli.py run-test testcases/iam/login.feature
uv run python cli.py run-test testcases/onboarding/contractor.txt
```

### Available Test Categories

- **IAM**: Identity and Access Management tests
- **Onboarding**: Employee and contractor onboarding workflows
- **Pay Supplements**: Payment-related functionality tests
- **Demo**: Sample test cases for demonstration

## Project Structure

```
workflows/
├── cli.py                 # Command line interface
├── testcases/            # Test case definitions
│   ├── iam/             # Authentication tests
│   ├── onboarding/      # Onboarding workflows
│   └── pay_supplements/ # Payment tests
├── workflow_use/        # Core framework code
├── backend/            # API backend
└── examples/           # Example workflows
```

## Development

This framework is built using:
- Python 3.11+
- FastAPI for backend services
- Browser-use for web automation
- AWS Bedrock for AI capabilities
- Typer for CLI interface

## License

Licensed under OSI Approved License.
