"""
Gherkin processing functions for converting text files to Gherkin scenarios
Adapted from smart-test framework
"""

import re
import logging
from typing import Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)


def _extract_model_name(llm) -> str:
    """Extract the actual model name from LLM instance"""
    try:
        # Try different attributes where model name might be stored
        if hasattr(llm, 'model_id'):
            return llm.model_id
        elif hasattr(llm, 'model_name'):
            return llm.model_name
        elif hasattr(llm, 'model'):
            return llm.model
        elif hasattr(llm, '_model_id'):
            return llm._model_id
        elif hasattr(llm, 'model_kwargs') and 'model_id' in llm.model_kwargs:
            return llm.model_kwargs['model_id']
        elif hasattr(llm, 'model_kwargs') and 'model' in llm.model_kwargs:
            return llm.model_kwargs['model']
        else:
            # Fallback: try to extract from class name or string representation
            llm_str = str(llm)
            if 'claude-3-5-sonnet' in llm_str.lower():
                return 'anthropic.claude-3-5-sonnet-20241022-v2:0'
            elif 'claude-3-haiku' in llm_str.lower():
                return 'anthropic.claude-3-haiku-20240307-v1:0'
            elif 'gpt-4' in llm_str.lower():
                return 'gpt-4'
            elif 'gpt-3.5' in llm_str.lower():
                return 'gpt-3.5-turbo'
            else:
                logger.warning(f"Could not extract model name from LLM: {type(llm).__name__}")
                return f"{type(llm).__name__}-unknown"
    except Exception as e:
        logger.warning(f"Error extracting model name: {e}")
        return "unknown-model"


def extract_code_content(text: str) -> str:
    """Extract code from markdown code blocks if present"""
    # Look for content between triple backticks with optional language identifier
    code_block_pattern = re.compile(r"```(?:python|gherkin|javascript|java|robot|markdown)?\n(.*?)```", re.DOTALL)
    match = code_block_pattern.search(text)

    if match:
        return match.group(1).strip()
    return text.strip()


def generate_gherkin_scenarios(manual_test_cases_text: str, llm: BaseChatModel) -> str:
    """
    Generate Gherkin scenarios from manual test cases using LLM
    
    Args:
        manual_test_cases_text: Raw text content from .txt file
        llm: Language model instance for conversion
        
    Returns:
        Gherkin scenario text
    """
    try:
        # Create prompt for Gherkin conversion
        gherkin_prompt = f"""
You are an expert QA engineer specializing in converting manual test cases to Gherkin scenarios.

Convert the following manual test case to a proper Gherkin scenario format:

```
{manual_test_cases_text}
```

**CRITICAL REQUIREMENTS:**
1. **PRESERVE EXACT URLS**: Do NOT change any URLs. Keep them exactly as provided in the original text.
2. **PRESERVE EXACT VALUES**: Keep all specific values (emails, passwords, amounts, names) exactly as written.
3. **PRESERVE EXACT INSTRUCTIONS**: Keep the original wording and specific instructions intact.
4. **NO GENERIC REPLACEMENTS**: Do not replace specific URLs with generic descriptions.

**Gherkin Conversion Rules:**
1. Use proper Gherkin syntax (Feature, Scenario, Given, When, Then, And)
2. Convert action statements to appropriate Gherkin keywords:
   - "Go to [URL]" → "Given I navigate to [EXACT_URL]"
   - "Click on [element]" → "When I click on [EXACT_ELEMENT]"
   - "Enter [value]" → "When I enter [EXACT_VALUE]"
   - "Verify [condition]" → "Then I should see [EXACT_CONDITION]"
3. Break down complex steps into smaller, testable steps
4. Include proper assertions using "Then" and "And" statements
5. Use descriptive scenario names based on the original test intent

**EXAMPLES OF CORRECT CONVERSION:**
Original: "Go to https://release-app.usemultiplier.com"
Correct: "Given I navigate to https://release-app.usemultiplier.com"
WRONG: "Given I am on the Multiplier login page"

Original: "login with email:tester+bullertest@usemultiplier.com password:Password@123"
Correct: "When I enter email 'tester+bullertest@usemultiplier.com' and password 'Password@123'"
WRONG: "When I enter valid credentials"

**Output Format:**
Return only the Gherkin scenario without any additional explanation or markdown formatting.

Convert the provided test case following these rules, ensuring ALL specific values and URLs remain unchanged.
"""

        # Generate Gherkin using LLM
        response = llm.invoke([HumanMessage(content=gherkin_prompt)])
        gherkin_content = extract_code_content(response.content)

        # Track token usage if available
        try:
            from workflow_use.hybrid.token_tracker import track_llm_call
            # Estimate token usage (rough approximation)
            input_tokens = len(gherkin_prompt.split()) * 1.3  # Rough token estimation
            output_tokens = len(gherkin_content.split()) * 1.3

            # Extract proper model name from LLM instance
            model_name = _extract_model_name(llm)
            track_llm_call(model_name, int(input_tokens), int(output_tokens))
            logger.debug(f"Tracked Gherkin conversion: {model_name} - {int(input_tokens + output_tokens)} tokens")
        except Exception as e:
            logger.debug(f"Token tracking failed for Gherkin conversion: {e}")

        logger.info("Successfully converted text to Gherkin scenario")
        return gherkin_content
        
    except Exception as e:
        logger.error(f"Error generating Gherkin scenarios: {str(e)}")
        raise


def validate_gherkin_scenario(gherkin_text: str) -> bool:
    """
    Validate that the generated text is a proper Gherkin scenario
    
    Args:
        gherkin_text: Generated Gherkin text
        
    Returns:
        True if valid Gherkin format, False otherwise
    """
    try:
        # Check for required Gherkin keywords
        required_patterns = [
            r"Feature:\s*\w+",  # Feature declaration
            r"Scenario:\s*\w+",  # Scenario declaration
        ]
        
        for pattern in required_patterns:
            if not re.search(pattern, gherkin_text, re.IGNORECASE):
                logger.warning(f"Missing required Gherkin pattern: {pattern}")
                return False
        
        # Check for at least one step keyword
        step_keywords = ["Given", "When", "Then", "And", "But"]
        has_steps = any(keyword in gherkin_text for keyword in step_keywords)
        
        if not has_steps:
            logger.warning("No Gherkin step keywords found")
            return False
            
        logger.info("Gherkin scenario validation passed")
        return True
        
    except Exception as e:
        logger.error(f"Error validating Gherkin scenario: {e}")
        return False


def read_test_file(file_path: str) -> str:
    """
    Read test case content from .txt file
    
    Args:
        file_path: Path to the .txt test file
        
    Returns:
        File content as string
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read().strip()
        
        if not content:
            raise ValueError(f"Test file {file_path} is empty")
            
        logger.info(f"Successfully read test file: {file_path}")
        return content
        
    except FileNotFoundError:
        logger.error(f"Test file not found: {file_path}")
        raise
    except Exception as e:
        logger.error(f"Error reading test file {file_path}: {e}")
        raise


def process_txt_to_gherkin(txt_file_path: str, llm: BaseChatModel) -> str:
    """
    Complete pipeline to convert .txt test file to Gherkin scenario
    
    Args:
        txt_file_path: Path to the .txt test file
        llm: Language model instance
        
    Returns:
        Valid Gherkin scenario text
    """
    try:
        # Read the test file
        test_content = read_test_file(txt_file_path)
        
        # Convert to Gherkin
        gherkin_scenario = generate_gherkin_scenarios(test_content, llm)
        
        # Validate the result
        if not validate_gherkin_scenario(gherkin_scenario):
            raise ValueError("Generated Gherkin scenario failed validation")
        
        logger.info(f"Successfully processed {txt_file_path} to Gherkin")
        return gherkin_scenario
        
    except Exception as e:
        logger.error(f"Error processing txt to Gherkin: {e}")
        raise
