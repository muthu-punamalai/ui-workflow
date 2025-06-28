# UI Workflow - Hybrid Testing Framework

A next-generation hybrid testing framework that combines the speed of deterministic workflow execution with the intelligence of AI-powered browser automation.

## 🚀 Overview

The UI Workflow framework implements a **hybrid approach** that optimizes test execution by:

1. **First Run**: Converts plain text test cases to Gherkin scenarios, executes with browser-use AI, and captures rich element data
2. **Subsequent Runs**: Uses deterministic workflow execution for speed, with intelligent fallback to browser-use when needed
3. **Self-Healing**: Automatically adapts to page changes and maintains test reliability

## 🏗️ Architecture

```
📄 Plain Text Test Cases (.txt)
         ↓
🧠 Smart-Test Integration (txt → Gherkin)
         ↓
🔄 Hybrid Test Runner
         ↓
📊 Workflow.json exists?
         ↓                    ↓
       YES                   NO
         ↓                    ↓
   🚀 Workflow-Use        🤖 Browser-Use
   (Fast Execution)       (AI-Powered)
         ↓                    ↓
   ✅ Success? ❌ Failed      📄 Capture Rich Data
         ↓         ↓              ↓
   ✅ Continue   🤖 Fallback   📄 Create workflow.json
                    ↓
                ✅ Self-Healing
```

## 📁 Project Structure

```
workflows/
├── README.md                          # This documentation
├── cli.py                            # Command-line interface
├── test_timing.py                    # Performance analysis tool
├── testcases/                        # Test case files
│   ├── pay_supplements.txt           # Plain text test cases
│   ├── pay_supplements.workflow.json # Generated workflow files
│   └── google_search.txt
├── workflow_use/
│   ├── hybrid/                       # Hybrid system implementation
│   │   ├── test_runner.py           # Main test execution engine
│   │   ├── fallback_manager.py      # Intelligent fallback logic
│   │   └── simple_capture.py        # Workflow capture from browser-use
│   ├── llm/                         # LLM integration
│   │   └── providers.py             # AWS Bedrock & fallback providers
│   ├── workflow/                    # Workflow execution engine
│   │   └── service.py               # Deterministic workflow runner
│   ├── controller/                  # Browser interaction layer
│   │   ├── service.py               # Action implementations
│   │   └── utils.py                 # Element detection utilities
│   └── config/                      # Configuration management
       └── llm_config.py             # LLM configuration
```

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- UV package manager
- AWS credentials (for Bedrock LLM)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd workflows

# Install dependencies
uv sync

# Install Playwright browsers
uv run playwright install chromium
```

### Configuration

Create a `.env` file in the workflows directory:

```env
# AWS Configuration
AWS_PROFILE=your-aws-profile
AWS_REGION=us-east-1

# LLM Configuration
LLM_PROVIDER=bedrock
LLM_MODEL=anthropic.claude-3-5-sonnet-20241022-v2:0
```

### Running Tests

```bash
# Run a single test
uv run python cli.py run-test testcases/pay_supplements.txt

# Run with timing analysis
uv run python test_timing.py testcases/pay_supplements.txt

# Run test suite
uv run python cli.py run-suite testcases/
```

## 📝 Test Case Format

### Plain Text Format (.txt)

```
# Pay supplements Tests
Feature: Pay supplements

Scenario: Edit pay supplement under processing
    Go to https://release-app.usemultiplier.com
    Signin with email:tester+bullertest@usemultiplier.com password:Password@123
    Click on Administration button from the left nav bar
    Verify the Pay supplements option is visible under Adminstration
    Click to Pay supplements sections
    Verify Add pay supplement button is visible
    Close the browser
```

### Generated Workflow Format (.workflow.json)

```json
{
  "workflow_analysis": "Captured from browser-use execution",
  "name": "pay_supplements",
  "description": "Auto-generated workflow from pay_supplements",
  "version": "1.0.0",
  "steps": [
    {
      "description": "Navigate to Multiplier release app",
      "type": "navigation",
      "url": "https://release-app.usemultiplier.com",
      "timestamp": 0,
      "tabId": 0
    },
    {
      "description": "Enter email address",
      "type": "input",
      "cssSelector": "input[id=\"email\"][name=\"email\"][data-cy=\"email\"]",
      "xpath": "html/body/div[1]/div[2]/div[2]/div/div/form/div[1]/div/input",
      "value": "tester+bullertest@usemultiplier.com",
      "elementTag": "input",
      "timestamp": 0,
      "tabId": 0
    }
  ]
}
```

## 🔧 Core Components

### 1. Hybrid Test Runner

**File**: `workflow_use/hybrid/test_runner.py`

The main orchestrator that:
- Converts txt files to Gherkin scenarios
- Decides between workflow-use and browser-use execution
- Manages the complete test lifecycle
- Provides detailed timing and performance metrics

```python
from workflow_use.hybrid.test_runner import HybridTestRunner

runner = HybridTestRunner(llm, page_extraction_llm)
result = await runner.run_test('testcases/pay_supplements.txt')
```

### 2. Fallback Manager

**File**: `workflow_use/hybrid/fallback_manager.py`

Implements intelligent step-level fallback:
- Attempts workflow-use execution first
- Falls back to browser-use on failure
- Captures and updates workflow definitions
- Provides seamless error recovery

### 3. Workflow Capture

**File**: `workflow_use/hybrid/simple_capture.py`

Extracts rich element data from browser-use execution:
- Real CSS selectors and XPaths
- Element attributes and metadata
- Multiple fallback strategies
- Production-ready workflow definitions

### 4. Smart-Test Integration

Converts plain text test cases to structured Gherkin scenarios:
- Natural language processing
- URL and credential extraction
- Action identification and parameterization
- Maintains exact URLs and values

## 📊 Performance Analysis

### Execution Methods

1. **Workflow-Use** (Fast): 1-5 seconds per step
   - Direct CSS selector/XPath execution
   - No LLM reasoning required
   - Deterministic and reliable

2. **Browser-Use** (Intelligent): 10-30 seconds per step
   - AI-powered element detection
   - Visual page analysis
   - Adaptive to page changes

3. **Hybrid** (Optimal): Best of both worlds
   - Fast when selectors work
   - Intelligent when adaptation needed

### Performance Metrics

```bash
# Example timing output
📊 Results:
  Success: True
  Method: workflow-use-with-fallback
  Total time: 25.4 seconds

🔍 Step-by-step timing:
    Step 1: 1.2s (workflow-use)      ← Fast navigation
    Step 2: 2.1s (workflow-use)      ← Quick input
    Step 3: 18.7s (browser-use-fallback) ← Adapted to page change
    Step 4: 1.8s (workflow-use)      ← Back to fast execution

⚠️ Fallback analysis:
  Steps using browser-use fallback: 1
  Steps using pure workflow-use: 3
```

## 🔍 Method Detection

The framework automatically detects execution methods:

### Browser-Use Indicators
- `AgentHistoryList` in results
- `input_text` with index references
- `interacted_element` data
- Execution time > 15 seconds

### Workflow-Use Indicators
- CSS selector messages
- Direct element interaction logs
- Execution time < 10 seconds

## 🛠️ Configuration

### LLM Providers

**AWS Bedrock** (Primary):
```python
config = {
    "provider": "bedrock",
    "model": "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "region": "us-east-1"
}
```

**OpenAI** (Fallback):
```python
config = {
    "provider": "openai",
    "model": "gpt-4",
    "api_key": "your-api-key"
}
```

### Browser Configuration

```python
# Headless mode (CI/CD)
browser = Browser(headless=True)

# Development mode
browser = Browser(headless=False, user_data_dir="./browser-profile")
```

## 🚀 CI/CD Integration

### GitHub Actions Example

```yaml
name: UI Tests
on: [push, pull_request]

jobs:
  ui-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          cd workflows
          pip install uv
          uv sync
          uv run playwright install chromium --with-deps

      - name: Run UI Tests
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        run: |
          cd workflows
          uv run python cli.py run-suite testcases/

      - name: Upload test results
        uses: actions/upload-artifact@v3
        with:
          name: test-results
          path: workflows/testcases/*.workflow.json
```

### Docker Support

```dockerfile
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget gnupg && rm -rf /var/lib/apt/lists/*

# Install application
COPY workflows/ /app/workflows/
WORKDIR /app/workflows

RUN pip install uv
RUN uv sync
RUN uv run playwright install chromium --with-deps

# Run tests
CMD ["uv", "run", "python", "cli.py", "run-suite", "testcases/"]
```

## 🔧 Advanced Features

### Custom Element Selectors

The framework uses a stability-ranked selector strategy:

1. **ID selectors** (most stable): `#email`
2. **Name attributes**: `input[name="email"]`
3. **Data attributes**: `[data-cy="email"]`
4. **Class selectors**: `.email-input`
5. **XPath expressions** (fallback): `//input[@id="email"]`

### Intelligent Timeouts

- **Element detection**: 10 seconds maximum
- **Page navigation**: 30 seconds
- **Action execution**: 5 seconds
- **Smart waiting**: Exits immediately when element found

### Error Recovery

- **Automatic retry**: Up to 2 attempts per step
- **Selector fallback**: Multiple strategies per element
- **Method fallback**: Workflow-use → Browser-use
- **Graceful degradation**: Continues execution on non-critical failures

## 📈 Monitoring and Debugging

### Logging Levels

```python
import logging
logging.getLogger('workflow_use').setLevel(logging.INFO)
```

### Performance Monitoring

```bash
# Detailed timing analysis
uv run python test_timing.py testcases/your_test.txt

# Method breakdown
uv run python cli.py run-test testcases/your_test.txt --verbose
```

### Debug Mode

```bash
# Run with debug logging
PYTHONPATH=. python -m workflow_use.hybrid.test_runner --debug testcases/your_test.txt
```

## 🤝 Contributing

### Development Setup

```bash
# Install development dependencies
uv sync --dev

# Run tests
uv run pytest

# Format code
uv run black .
uv run isort .
```

### Adding New Actions

1. **Define action schema** in `workflow_use/workflow/models.py`
2. **Implement action logic** in `workflow_use/controller/service.py`
3. **Add capture logic** in `workflow_use/hybrid/simple_capture.py`
4. **Update tests** in `tests/`

### Adding New LLM Providers

1. **Implement provider** in `workflow_use/llm/providers.py`
2. **Add configuration** in `workflow_use/config/llm_config.py`
3. **Update documentation** in this README

## 📚 API Reference

### HybridTestRunner

```python
class HybridTestRunner:
    async def run_test(self, txt_file_path: str, force_browser_use: bool = False) -> Dict[str, Any]
    async def run_test_suite(self, testcases_dir: str) -> Dict[str, Any]
```

### FallbackManager

```python
class FallbackManager:
    async def execute_step_with_fallback(self, workflow, step_index, gherkin_scenario) -> Tuple[bool, Any, Optional[WorkflowStep]]
```

### SimpleWorkflowCapture

```python
class SimpleWorkflowCapture:
    def create_workflow_from_browser_use(self, agent_history, test_name: str, success: bool = True) -> Optional[WorkflowDefinitionSchema]
```

## 🐛 Troubleshooting

### Common Issues

**1. Element Not Found**
```
ERROR: Failed to input text. Original selector: input[id="email"]. Error: Timeout 10000ms exceeded
```
**Solution**: Check if element exists, verify selector, or let browser-use fallback handle it.

**2. LLM Connection Failed**
```
ERROR: Failed to initialize LLM with provider bedrock
```
**Solution**: Verify AWS credentials and region configuration.

**3. Workflow Validation Errors**
```
ERROR: 2 validation errors for ActionModel input.timestamp
```
**Solution**: Ensure workflow.json has valid schema with integer timestamps and tabIds.

### Performance Issues

**Slow Execution**: Check if browser-use fallback is being used excessively
**High Memory Usage**: Ensure browser sessions are properly closed
**Timeout Errors**: Increase timeout values in configuration

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **Browser-Use**: AI-powered browser automation
- **Playwright**: Reliable browser automation library
- **Smart-Test**: Natural language test case processing
- **AWS Bedrock**: Large language model infrastructure

---

**Built with ❤️ for reliable, intelligent, and fast UI testing**
