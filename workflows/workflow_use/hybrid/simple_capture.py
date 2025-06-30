"""
Simple workflow capture that uses existing ui-workflow schema
but creates workflows from successful browser-use executions
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from workflow_use.schema.views import (
    WorkflowDefinitionSchema,
    NavigationStep,
    ClickStep,
    InputStep,
    KeyPressStep,
    ScrollStep,
    WorkflowInputSchemaDefinition
)

logger = logging.getLogger(__name__)


class SimpleWorkflowCapture:
    """Simple workflow capture using existing ui-workflow schema"""
    
    def create_workflow_from_browser_use(
        self,
        agent_history,
        test_name: str,
        success: bool = True
    ) -> Optional[WorkflowDefinitionSchema]:
        """
        Create workflow from browser-use agent history with actual element data
        """
        try:
            if not success:
                return None

            # Try multiple extraction methods
            steps = self._extract_steps_from_agent_history(agent_history)

            # If primary method fails, try extracting from action_results
            if not steps:
                logger.info("Primary extraction failed, trying action_results method")
                steps = self._extract_steps_from_action_results(agent_history)

            if not steps:
                logger.warning("No steps extracted from agent history using any method")
                return None

            workflow_def = WorkflowDefinitionSchema(
                name=test_name,
                description=f"Auto-generated workflow from {test_name}",
                version="1.0.0",
                steps=steps,
                input_schema=[],
                workflow_analysis=f"Captured from browser-use execution on {datetime.now().isoformat()}"
            )

            logger.info(f"Created workflow with {len(steps)} steps for '{test_name}'")
            return workflow_def

        except Exception as e:
            logger.error(f"Error creating workflow from browser-use: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    def create_workflow_from_gherkin(
        self,
        gherkin_scenario: str,
        test_name: str,
        success: bool = True
    ) -> Optional[WorkflowDefinitionSchema]:
        """
        Create a basic workflow from Gherkin scenario
        This creates a simple workflow that can be used by workflow execution
        """
        try:
            if not success:
                return None
            
            steps = self._parse_gherkin_to_steps(gherkin_scenario)
            
            if not steps:
                logger.warning("No steps extracted from Gherkin scenario")
                return None
            
            workflow_def = WorkflowDefinitionSchema(
                name=test_name,
                description=f"Auto-generated workflow from {test_name}",
                version="1.0.0",
                steps=steps,
                input_schema=[],
                workflow_analysis=f"Converted from Gherkin scenario on {datetime.now().isoformat()}"
            )
            
            logger.info(f"Created workflow with {len(steps)} steps for '{test_name}'")
            return workflow_def
            
        except Exception as e:
            logger.error(f"Error creating workflow from Gherkin: {e}")
            return None
    
    def _parse_gherkin_to_steps(self, gherkin_scenario: str) -> List:
        """Parse Gherkin scenario into basic workflow steps"""
        steps = []
        
        try:
            lines = gherkin_scenario.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#') or line.startswith('Feature:') or line.startswith('Scenario:'):
                    continue
                
                # Parse different Gherkin step types
                if line.startswith('Given I navigate to') or line.startswith('Go to'):
                    url = self._extract_url_from_line(line)
                    if url:
                        steps.append(NavigationStep(
                            type="navigation",
                            url=url,
                            description=f"Navigate to {url}",
                            timestamp=0,
                            tabId=0
                        ))
                
                elif 'click' in line.lower():
                    # Extract element to click
                    element_text = self._extract_element_text(line)
                    if element_text:
                        # Create a generic selector based on text
                        selector = f"text='{element_text}'"
                        steps.append(ClickStep(
                            type="click",
                            cssSelector=selector,
                            elementText=element_text,
                            description=f"Click {element_text}",
                            timestamp=0,
                            tabId=0
                        ))
                
                elif 'enter' in line.lower() or 'input' in line.lower():
                    # Extract input text and field
                    input_data = self._extract_input_data(line)
                    if input_data:
                        text, field = input_data
                        selector = f"[name='{field}']" if field else "input"
                        steps.append(InputStep(
                            type="input",
                            cssSelector=selector,
                            value=text,
                            description=f"Enter '{text}' in {field if field else 'input field'}",
                            timestamp=0,
                            tabId=0
                        ))
                
                elif 'scroll' in line.lower():
                    steps.append(ScrollStep(
                        type="scroll",
                        direction="down",
                        amount=500
                    ))

                elif 'press' in line.lower() and 'key' in line.lower():
                    key = self._extract_key_from_line(line)
                    if key:
                        steps.append(KeyPressStep(
                            type="key_press",
                            key=key
                        ))
            
        except Exception as e:
            logger.warning(f"Error parsing Gherkin to steps: {e}")
        
        return steps

    def _extract_steps_from_agent_history(self, agent_history) -> List:
        """Extract workflow steps from browser-use agent history"""
        steps = []

        try:
            # Get model outputs from agent history
            model_outputs = None

            # Access the model outputs from AgentHistoryList
            logger.info(f"Agent history type: {type(agent_history)}")

            # For AgentHistoryList, use model_actions method (includes interacted_element!)
            try:
                model_actions = agent_history.model_actions()  # This includes interacted_element!
                if model_actions and len(model_actions) > 0:
                    logger.info(f"Successfully accessed model_actions with {len(model_actions)} items")
                else:
                    logger.warning("model_actions exists but is empty")
                    return steps
            except AttributeError as e:
                logger.error(f"AgentHistoryList does not have model_actions method: {e}")
                return steps
            except Exception as e:
                logger.error(f"Unexpected error accessing model_actions: {e}")
                return steps

            for i, model_action in enumerate(model_actions):
                if not isinstance(model_action, dict):
                    logger.warning(f"Model action {i} is not a dict: {type(model_action)}")
                    continue

                logger.info(f"Processing model action {i}: {list(model_action.keys())}")

                # Extract the interacted_element (this is the key!)
                interacted_element = model_action.get('interacted_element')
                logger.info(f"Interacted element for action {i}: {interacted_element is not None}")

                # Process each action in the model action (excluding interacted_element)
                for action_name, action_data in model_action.items():
                    if action_name == 'interacted_element':
                        continue  # Skip the element data itself

                    # Create a model_output dict with the interacted_element
                    model_output_with_element = {
                        action_name: action_data,
                        'interacted_element': interacted_element
                    }

                    step = self._convert_browser_action_to_step(action_name, action_data, model_output_with_element)
                    if step:
                        steps.append(step)
                        logger.info(f"Created step from action: {action_name} with element data")

        except Exception as e:
            logger.error(f"Error extracting steps from agent history: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

        logger.info(f"Extracted {len(steps)} steps from agent history")
        return steps

    def _extract_steps_from_action_results(self, agent_history) -> List:
        """
        Alternative method: Extract workflow steps from AgentHistoryList action_results
        This method works with the actual browser-use AgentHistoryList structure
        """
        steps = []

        try:
            # Access action_results which contains the actual actions performed
            if hasattr(agent_history, 'action_results'):
                action_results = agent_history.action_results()  # Call the method
                logger.info(f"Found {len(action_results)} action results")

                for i, action_result in enumerate(action_results):
                    logger.info(f"Processing action result {i}: {type(action_result)}")

                    # Extract content from action result
                    if hasattr(action_result, 'extracted_content'):
                        content = action_result.extracted_content
                        logger.info(f"Action {i} content: {content[:100] if content else 'None'}...")

                        # Parse the content to determine action type
                        step = self._parse_action_content_to_step(content, i)
                        if step:
                            steps.append(step)
                            logger.info(f"Created step {i}: {step.type}")

            # Also try to access model_outputs if available
            elif hasattr(agent_history, 'model_outputs'):
                model_outputs = agent_history.model_outputs()  # Call the method
                logger.info(f"Found {len(model_outputs)} model outputs")

                for i, model_output in enumerate(model_outputs):
                    if isinstance(model_output, dict):
                        for action_name, action_data in model_output.items():
                            if action_name != 'interacted_element':
                                step = self._convert_browser_action_to_step(action_name, action_data, model_output)
                                if step:
                                    steps.append(step)
                                    logger.info(f"Created step from model output {i}: {action_name}")

            else:
                logger.warning("Agent history has neither action_results nor model_outputs")

        except Exception as e:
            logger.error(f"Error extracting steps from action results: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")

        logger.info(f"Extracted {len(steps)} steps from action results")
        return steps

    def _parse_action_content_to_step(self, content: str, step_index: int):
        """Parse action content string to create workflow step"""
        try:
            if not content:
                return None

            content_lower = content.lower()

            # Navigation action
            if 'navigated to' in content_lower and 'http' in content_lower:
                # Extract URL from content like "🔗  Navigated to https://www.google.com"
                import re
                url_match = re.search(r'https?://[^\s]+', content)
                if url_match:
                    return NavigationStep(
                        type="navigation",
                        url=url_match.group(0),
                        description=f"Navigate to {url_match.group(0)}",
                        timestamp=0,
                        tabId=0
                    )

            # Input action
            elif 'input' in content_lower and 'into index' in content_lower:
                # Extract text and index from content like "⌨️  Input browser automation into index 6"
                import re
                text_match = re.search(r'input\s+(.+?)\s+into\s+index\s+(\d+)', content_lower)
                if text_match:
                    text = text_match.group(1).strip()
                    index = text_match.group(2)
                    return InputStep(
                        type="input",
                        cssSelector=f"[data-index='{index}']",  # Generic selector
                        value=text,
                        elementTag="input",
                        description=f"Enter '{text}' in input field",
                        timestamp=0,
                        tabId=0
                    )

            # Click action
            elif 'clicked' in content_lower and 'index' in content_lower:
                # Extract index from content like "🖱️  Clicked button with index 20:"
                import re
                index_match = re.search(r'index\s+(\d+)', content_lower)
                if index_match:
                    index = index_match.group(1)
                    return ClickStep(
                        type="click",
                        cssSelector=f"[data-index='{index}']",  # Generic selector
                        elementTag="button",
                        description="Click button",
                        timestamp=0,
                        tabId=0
                    )

            # Extract content action (for assertions)
            elif 'extracted from page' in content_lower:
                # This represents a verification/assertion step
                return None  # Skip extraction steps for now

            return None

        except Exception as e:
            logger.warning(f"Error parsing action content: {e}")
            return None

    def _convert_browser_action_to_step(self, action_name: str, action_data: Dict, model_output: Dict):
        """Convert browser-use action to workflow step"""
        try:
            interacted_element = model_output.get('interacted_element')

            if action_name == 'go_to_url':
                url = action_data.get('url', '')
                return NavigationStep(
                    type="navigation",
                    url=url,
                    description=f"Navigate to {url}",
                    timestamp=0,
                    tabId=0
                )

            elif action_name == 'input_text':
                # Extract detailed element information
                css_selector = self._get_element_selector(interacted_element)
                text_value = action_data.get('text', '')
                # Generate multi-strategy selectors
                selectors = self._generate_multi_strategy_selectors(interacted_element)

                return InputStep(
                    type="input",
                    cssSelector=css_selector,
                    value=text_value,
                    xpath=self._get_element_xpath(interacted_element),
                    elementTag=self._get_element_tag(interacted_element),
                    description=f"Enter '{text_value}' in input field",
                    timestamp=0,
                    tabId=0,
                    primarySelector=selectors.get('primary'),
                    semanticSelector=selectors.get('semantic'),
                    fallbackSelectors=selectors.get('fallbacks'),
                    elementAttributes=selectors.get('attributes')
                )

            elif action_name == 'click_element_by_index':
                # Extract detailed element information
                css_selector = self._get_element_selector(interacted_element)
                element_text = self._get_element_text(interacted_element)
                # Generate multi-strategy selectors
                selectors = self._generate_multi_strategy_selectors(interacted_element)

                return ClickStep(
                    type="click",
                    cssSelector=css_selector,
                    xpath=self._get_element_xpath(interacted_element),
                    elementTag=self._get_element_tag(interacted_element),
                    elementText=element_text,
                    description=f"Click {element_text if element_text else 'element'}",
                    timestamp=0,
                    tabId=0,
                    primarySelector=selectors.get('primary'),
                    semanticSelector=selectors.get('semantic'),
                    fallbackSelectors=selectors.get('fallbacks'),
                    elementAttributes=selectors.get('attributes')
                )

            # Skip 'extract_content', 'done' as they're not workflow actions

        except Exception as e:
            logger.warning(f"Error converting browser action {action_name}: {e}")

        return None

    def _get_element_selector(self, element) -> str:
        """Get the best possible CSS selector from element with stability priority"""
        if not element:
            return ""

        # Get attributes for analysis
        attrs = getattr(element, 'attributes', {}) or {}
        tag = getattr(element, 'tag_name', 'div')

        # Priority 1: Test IDs (most stable)
        if attrs.get('data-testid'):
            return f"[data-testid='{attrs['data-testid']}']"
        if attrs.get('data-cy'):
            return f"[data-cy='{attrs['data-cy']}']"

        # Priority 2: Semantic attributes
        if hasattr(element, 'id') and element.id:
            return f"#{element.id}"
        if attrs.get('id'):
            return f"#{attrs['id']}"
        if hasattr(element, 'name') and element.name:
            return f"{tag}[name='{element.name}']"
        if attrs.get('name'):
            return f"{tag}[name='{attrs['name']}']"

        # Priority 3: Type + stable attributes for form elements
        if tag == 'input' and attrs.get('type'):
            type_attr = attrs['type']
            if attrs.get('placeholder'):
                return f"input[type='{type_attr}'][placeholder='{attrs['placeholder']}']"
            return f"input[type='{type_attr}']"

        # Priority 4: Role-based selectors
        if attrs.get('role'):
            return f"[role='{attrs['role']}']"

        # Priority 5: Aria labels
        if attrs.get('aria-label'):
            return f"[aria-label='{attrs['aria-label']}']"

        # Priority 6: Stable classes (avoid generated ones like css-xxxxx)
        if attrs.get('class'):
            classes = attrs['class'].split()
            stable_classes = [cls for cls in classes if not cls.startswith('css-') and len(cls) > 3]
            if stable_classes:
                return f"{tag}.{'.'.join(stable_classes[:2])}"

        # Priority 7: Use existing complex selector but log warning
        if hasattr(element, 'css_selector') and element.css_selector:
            complex_selector = element.css_selector
            logger.warning(f"Using complex selector as fallback: {complex_selector[:50]}...")
            return complex_selector

        # Final fallback: tag name
        if hasattr(element, 'tag_name'):
            return element.tag_name

        return ""

    def _get_element_xpath(self, element) -> Optional[str]:
        """Get XPath from element"""
        if element and hasattr(element, 'xpath'):
            return element.xpath
        return None

    def _get_element_tag(self, element) -> Optional[str]:
        """Get tag name from element"""
        if element and hasattr(element, 'tag_name'):
            return element.tag_name
        return None

    def _get_element_text(self, element) -> Optional[str]:
        """Get element text from element"""
        if element and hasattr(element, 'attributes'):
            attrs = element.attributes or {}
            return attrs.get('aria-label') or attrs.get('value') or attrs.get('title')
        return None

    def _generate_multi_strategy_selectors(self, element) -> Dict[str, Any]:
        """Generate multiple selector strategies for an element"""
        if not element:
            return {}

        attrs = getattr(element, 'attributes', {}) or {}
        tag = getattr(element, 'tag_name', 'div')

        selectors = {
            'primary': None,
            'semantic': None,
            'fallbacks': [],
            'attributes': attrs
        }

        # Primary selector (most stable)
        if attrs.get('data-testid'):
            selectors['primary'] = f"[data-testid='{attrs['data-testid']}']"
        elif attrs.get('data-cy'):
            selectors['primary'] = f"[data-cy='{attrs['data-cy']}']"
        elif attrs.get('id'):
            selectors['primary'] = f"#{attrs['id']}"

        # Semantic selector
        if attrs.get('name'):
            selectors['semantic'] = f"{tag}[name='{attrs['name']}']"
        elif tag == 'input' and attrs.get('type'):
            selectors['semantic'] = f"input[type='{attrs['type']}']"
        elif attrs.get('role'):
            selectors['semantic'] = f"[role='{attrs['role']}']"

        # Fallback selectors
        fallbacks = []

        # Add type-based selectors for inputs
        if tag == 'input' and attrs.get('type'):
            if attrs.get('placeholder'):
                fallbacks.append(f"input[type='{attrs['type']}'][placeholder='{attrs['placeholder']}']")
            fallbacks.append(f"input[type='{attrs['type']}']")

        # Add aria-label selectors
        if attrs.get('aria-label'):
            fallbacks.append(f"[aria-label='{attrs['aria-label']}']")

        # Add stable class selectors (avoid css-xxxxx)
        if attrs.get('class'):
            classes = attrs['class'].split()
            stable_classes = [cls for cls in classes if not cls.startswith('css-') and len(cls) > 3]
            if stable_classes:
                fallbacks.append(f"{tag}.{'.'.join(stable_classes[:2])}")

        # Add text-based selectors for clickable elements
        if tag in ['button', 'a'] and attrs.get('aria-label'):
            fallbacks.append(f"{tag}:has-text('{attrs['aria-label']}')")

        selectors['fallbacks'] = fallbacks
        return selectors

    def _extract_url_from_line(self, line: str) -> Optional[str]:
        """Extract URL from Gherkin line"""
        import re
        url_pattern = r'https?://[^\s]+'
        match = re.search(url_pattern, line)
        return match.group(0) if match else None
    
    def _extract_element_text(self, line: str) -> Optional[str]:
        """Extract element text to click from Gherkin line"""
        import re
        # Look for text in quotes
        quote_pattern = r'"([^"]+)"'
        match = re.search(quote_pattern, line)
        if match:
            return match.group(1)
        
        # Look for common button/link text patterns
        if 'login' in line.lower():
            return 'login'
        elif 'submit' in line.lower():
            return 'submit'
        elif 'button' in line.lower():
            return 'button'
        
        return None
    
    def _extract_input_data(self, line: str) -> Optional[tuple]:
        """Extract input text and field name from Gherkin line"""
        import re
        
        # Look for email and password patterns
        if 'email' in line.lower():
            email_pattern = r'"([^"]+@[^"]+)"'
            match = re.search(email_pattern, line)
            if match:
                return match.group(1), 'email'
        
        if 'password' in line.lower():
            password_pattern = r'password[:\s]+"([^"]+)"'
            match = re.search(password_pattern, line)
            if match:
                return match.group(1), 'password'
        
        # Generic text in quotes
        quote_pattern = r'"([^"]+)"'
        match = re.search(quote_pattern, line)
        if match:
            return match.group(1), None
        
        return None
    
    def _extract_key_from_line(self, line: str) -> Optional[str]:
        """Extract key name from Gherkin line"""
        if 'enter' in line.lower():
            return 'Enter'
        elif 'tab' in line.lower():
            return 'Tab'
        elif 'escape' in line.lower():
            return 'Escape'
        return None
    
    def save_workflow(self, workflow_def: WorkflowDefinitionSchema, output_path: str) -> bool:
        """Save workflow definition to JSON file"""
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(workflow_def.model_dump(), f, indent=2, ensure_ascii=False)
            
            logger.info(f"Workflow saved to: {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving workflow to {output_path}: {e}")
            return False

    def _convert_agent_output_to_step(self, agent_output, step_index: int):
        """Convert AgentOutput object to workflow step with rich element data"""
        try:
            # AgentOutput has action and interacted_element attributes
            if not hasattr(agent_output, 'action') or not agent_output.action:
                return None

            action = agent_output.action
            interacted_element = getattr(agent_output, 'interacted_element', None)

            # Extract action details
            action_str = str(action)
            logger.info(f"Processing action: {action_str[:100]}...")

            # Handle different action types with rich element data
            if 'go_to_url' in action_str.lower() or 'navigate' in action_str.lower():
                # Extract URL from action
                url = None
                if isinstance(action, dict) and 'url' in action:
                    url = action['url']
                else:
                    # Parse from string representation
                    import re
                    url_match = re.search(r'https?://[^\s\'"]+', action_str)
                    if url_match:
                        url = url_match.group(0)

                if url:
                    return NavigationStep(
                        type="navigation",
                        url=url,
                        description=f"Navigate to {url}",
                        timestamp=0,
                        tabId=0
                    )

            elif 'input_text' in action_str.lower():
                # Extract input details with element data
                text = None
                css_selector = None
                xpath = None
                element_tag = None

                if isinstance(action, dict) and 'text' in action:
                    text = action['text']
                else:
                    # Parse text from string
                    import re
                    text_match = re.search(r"text['\"]?\s*:\s*['\"]([^'\"]+)['\"]", action_str)
                    if text_match:
                        text = text_match.group(1)

                # Get element details if available
                if interacted_element:
                    css_selector = getattr(interacted_element, 'css_selector', None)
                    xpath = getattr(interacted_element, 'xpath', None)
                    element_tag = getattr(interacted_element, 'tag_name', None)

                if text:
                    return InputStep(
                        type="input",
                        cssSelector=css_selector or f"[data-step='{step_index}']",
                        value=text,
                        xpath=xpath,
                        elementTag=element_tag or "input",
                        description=f"Enter '{text}' in input field",
                        timestamp=0,
                        tabId=0
                    )

            elif 'click' in action_str.lower():
                # Extract click details with element data
                css_selector = None
                xpath = None
                element_tag = None
                element_text = None

                # Get element details if available
                if interacted_element:
                    css_selector = getattr(interacted_element, 'css_selector', None)
                    xpath = getattr(interacted_element, 'xpath', None)
                    element_tag = getattr(interacted_element, 'tag_name', None)

                    # Get element text from attributes
                    if hasattr(interacted_element, 'attributes'):
                        attrs = interacted_element.attributes or {}
                        element_text = attrs.get('aria-label') or attrs.get('value') or attrs.get('title')

                return ClickStep(
                    type="click",
                    cssSelector=css_selector or f"[data-step='{step_index}']",
                    xpath=xpath,
                    elementTag=element_tag or "button",
                    elementText=element_text,
                    description=f"Click {element_text if element_text else 'element'}",
                    timestamp=0,
                    tabId=0
                )

            return None

        except Exception as e:
            logger.warning(f"Error converting AgentOutput to step: {e}")
            return None
