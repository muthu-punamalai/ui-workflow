"""
Browser prompts for executing Gherkin scenarios with browser-use
Copied from smart-test framework for compatibility
"""


def generate_browser_task(scenario: str, failure_behavior: str = "stop_on_assertion") -> str:
    """Generate the browser task prompt for executing Gherkin scenarios with assertion-aware execution"""

    failure_instructions = {
        "stop_on_first": "Stop execution immediately on any step failure (action or assertion)",
        "continue": "Continue execution even if steps fail, complete all steps",
        "stop_on_assertion": "Continue on action failures but stop immediately on assertion failures"
    }

    failure_instruction = failure_instructions.get(failure_behavior, failure_instructions["stop_on_assertion"])

    return f"""Execute this Gherkin scenario step-by-step with enhanced assertion validation:

**Gherkin Steps:**
```gherkin
{scenario}
```

**Execution Rules:**
1. **Given**: Set up initial state (navigate, verify elements exist)
2. **When**: Perform actions (click, type, select)
3. **Then**: Verify outcomes (check text, element presence, URL)
4. **And/But**: Continue previous step type
   - **And after Then**: Treat as additional assertion/verification steps
   - **And after When**: Treat as additional action steps
   - **And after Given**: Treat as additional setup steps

**CRITICAL EXECUTION RULES:**
- **USE EXACT URLS**: Navigate to the exact URLs specified in Gherkin steps. Do NOT modify or interpret URLs.
- **USE EXACT VALUES**: Use the exact text, emails, passwords, and values specified in Gherkin steps.
- **NO ASSUMPTIONS**: Do not assume or infer URLs, values, or actions not explicitly stated.

**Element Location Strategy:**
- Prioritize: ID > Name > CSS > Link Text > XPath
- Use contextual text from Gherkin steps
- Always capture detailed element info before interaction
- Wait for elements to be ready before acting

**Actions:**
- Click: Use "Perform element action" with action="click"
- Type: Use "Perform element action" with action="fill" and exact text
- Verify: Use "Get element property" to check content/state

**Step-by-Step Reporting with Assertion Tracking:**
- Before executing each Gherkin step, announce: "STEP_START: [step text]"
- For assertion steps (Then/And after Then), also announce: "ASSERTION_START: [assertion type] - [expected value]"
- After completing each step, report: "STEP_RESULT: [PASSED/FAILED] - [brief description]"
- For assertion steps, provide detailed results: "ASSERTION_RESULT: [PASSED/FAILED] - Expected: [value] | Actual: [value]"
- If a step fails, immediately report: "STEP_FAILED: [step text] - [detailed failure reason]"
- **IMPORTANT**: Treat "And" steps that follow "Then" steps as assertion steps requiring verification
- For assertion failures, include specific details like:
  * "Visibility assertion failed: Expected 'visible' but element was 'hidden'"
  * "Text assertion failed: Expected 'Welcome' but found 'Error'"
  * "State assertion failed: Expected 'enabled' but element was 'disabled'"
  * "Navigation assertion failed: Expected '/dashboard' but current URL is '/login'"
- For action failures, include details like:
  * "Element not found: [selector/description]"
  * "Click failed: [element] - [reason]"
  * "Field not visible: [field name]"
  * "Timeout waiting for: [element/condition]"
- Continue this pattern for every single Gherkin step

**Critical Rules:**
- For negative tests: Expected errors = TEST PASSED
- Always use "Get detailed element information" on interactive elements
- Final status must clearly state "PASSED" or "FAILED"
- **Failure Behavior**: {failure_instruction}
- Differentiate between action failures and assertion failures in reporting
- Log all actions and results with enhanced assertion details
- Report step-by-step progress as specified above
- If you encounter parsing errors or empty responses, retry with simpler actions
- Break complex steps into smaller, more manageable actions
- Always provide valid JSON responses - never return empty content
- For "Then" steps, focus on validation and provide detailed assertion results

**Negative Test Handling:**
If testing error conditions, seeing the expected error means TEST PASSED.

Execute each step methodically. Report step progress and final result clearly as PASSED or FAILED."""
