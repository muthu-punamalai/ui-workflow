"""
Workflow capture system for converting browser-use agent actions to workflow.json
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from browser_use.agent.views import AgentHistoryList, AgentHistory
from workflow_use.schema.views import (
    WorkflowDefinitionSchema,
    WorkflowStep,
    NavigationStep,
    ClickStep,
    InputStep,
    KeyPressStep,
    ScrollStep,
    SelectChangeStep,
    WorkflowInputSchemaDefinition
)

logger = logging.getLogger(__name__)


class WorkflowCapture:
    """Captures browser-use agent actions and converts them to workflow.json format"""
    
    def __init__(self):
        self.captured_steps: List[WorkflowStep] = []
        self.inputs_schema: List[WorkflowInputSchemaDefinition] = []
        
    def capture_from_agent_history(
        self,
        agent_history,
        test_name: str,
        description: str = ""
    ) -> WorkflowDefinitionSchema:
        """
        Convert browser-use agent history to workflow definition

        Args:
            agent_history: Agent history from browser-use (AgentHistoryList or similar)
            test_name: Name for the workflow
            description: Description of the workflow

        Returns:
            WorkflowDefinitionSchema object
        """
        try:
            self.captured_steps = []
            self.inputs_schema = []

            # Handle AgentHistoryList
            if hasattr(agent_history, 'all_model_outputs'):
                # Process all model outputs from the agent history
                for model_output in agent_history.all_model_outputs:
                    step = self._convert_model_output_to_step(model_output)
                    if step:
                        self.captured_steps.append(step)
            elif isinstance(agent_history, list):
                # Handle as list of history items
                for history_item in agent_history:
                    workflow_steps = self._convert_history_item_to_steps(history_item)
                    self.captured_steps.extend(workflow_steps)
            else:
                # Try to process as single item
                workflow_steps = self._convert_history_item_to_steps(agent_history)
                self.captured_steps.extend(workflow_steps)

            # If no steps were captured, create a basic navigation step
            if not self.captured_steps:
                logger.warning("No workflow steps captured, creating basic navigation step")
                # Try to extract URL from agent history content
                url = self._extract_url_from_agent_history(agent_history)
                if url:
                    self.captured_steps.append(
                        NavigationStep(action="navigate", url=url, wait_for_load=True)
                    )

            # Create workflow definition
            workflow_def = WorkflowDefinitionSchema(
                name=test_name,
                description=description or f"Auto-generated workflow from {test_name}",
                version="1.0.0",
                steps=self.captured_steps,
                input_schema=self.inputs_schema,
                metadata={
                    "created_at": datetime.now().isoformat(),
                    "source": "browser-use-agent",
                    "capture_method": "agent_history",
                    "original_steps_count": len(self.captured_steps)
                }
            )

            logger.info(f"Successfully captured {len(self.captured_steps)} steps for workflow '{test_name}'")
            return workflow_def

        except Exception as e:
            logger.error(f"Error capturing workflow from agent history: {e}")
            raise

    def _extract_url_from_agent_history(self, agent_history) -> Optional[str]:
        """Extract URL from agent history for fallback navigation step"""
        try:
            if hasattr(agent_history, 'all_results'):
                for result in agent_history.all_results:
                    if hasattr(result, 'extracted_content'):
                        content = result.extracted_content
                        if 'navigated to' in content.lower():
                            url = self._extract_url_from_content(content)
                            if url:
                                return url
            return None
        except Exception as e:
            logger.warning(f"Error extracting URL from agent history: {e}")
            return None
    
    def _convert_history_item_to_steps(self, history_item) -> List[WorkflowStep]:
        """Convert a single agent history item to workflow steps"""
        steps = []

        try:
            # Handle different types of history items
            if hasattr(history_item, 'all_model_outputs') and history_item.all_model_outputs:
                # This is an AgentHistoryList, process all model outputs
                for model_output in history_item.all_model_outputs:
                    step = self._convert_model_output_to_step(model_output)
                    if step:
                        steps.append(step)
            elif isinstance(history_item, dict):
                # This is a single model output
                step = self._convert_model_output_to_step(history_item)
                if step:
                    steps.append(step)
            else:
                # Try to extract from individual result
                if hasattr(history_item, 'extracted_content'):
                    content = history_item.extracted_content
                    if 'navigated to' in content.lower():
                        url = self._extract_url_from_content(content)
                        if url:
                            step = NavigationStep(action="navigate", url=url, wait_for_load=True)
                            steps.append(step)

        except Exception as e:
            logger.warning(f"Error converting history item to step: {e}")

        return steps

    def _convert_model_output_to_step(self, model_output: Dict[str, Any]) -> Optional[WorkflowStep]:
        """Convert a model output dictionary to a workflow step"""
        try:
            # Extract the action from model output
            for action_name, action_data in model_output.items():
                if action_name == 'interacted_element':
                    continue  # Skip metadata

                if action_name == 'go_to_url':
                    return NavigationStep(
                        action="navigate",
                        url=action_data.get('url', ''),
                        wait_for_load=True
                    )
                elif action_name == 'click_element_by_index':
                    # Try to get selector from interacted_element
                    element = model_output.get('interacted_element')
                    selector = self._extract_selector_from_element(element)
                    if selector:
                        return ClickStep(
                            action="click",
                            selector=selector,
                            wait_for_element=True
                        )
                elif action_name == 'input_text':
                    element = model_output.get('interacted_element')
                    selector = self._extract_selector_from_element(element)
                    text = action_data.get('text', '')
                    if selector and text:
                        return InputStep(
                            action="input",
                            selector=selector,
                            text=text,
                            clear_first=True
                        )
                elif action_name == 'key_press':
                    key = action_data.get('key', '')
                    if key:
                        return KeyPressStep(
                            action="key_press",
                            key=key
                        )
                elif action_name == 'scroll':
                    return ScrollStep(
                        action="scroll",
                        direction=action_data.get('direction', 'down'),
                        amount=action_data.get('amount', 500)
                    )
                elif action_name == 'select_option':
                    element = model_output.get('interacted_element')
                    selector = self._extract_selector_from_element(element)
                    value = action_data.get('value', '')
                    if selector and value:
                        return SelectChangeStep(
                            action="select_change",
                            selector=selector,
                            value=value
                        )
                # Skip 'done', 'wait', 'extract_content' as they're not workflow actions

        except Exception as e:
            logger.warning(f"Error converting model output to step: {e}")

        return None
    
    def _create_navigation_step(self, action) -> Optional[NavigationStep]:
        """Create navigation step from action"""
        try:
            url = getattr(action, 'url', None) or getattr(action, 'target', None)
            if url:
                return NavigationStep(
                    action="navigate",
                    url=url,
                    wait_for_load=True
                )
        except Exception as e:
            logger.warning(f"Error creating navigation step: {e}")
        return None
    
    def _create_click_step(self, action) -> Optional[ClickStep]:
        """Create click step from action"""
        try:
            # Extract selector information
            selector = self._extract_selector(action)
            if selector:
                return ClickStep(
                    action="click",
                    selector=selector,
                    wait_for_element=True
                )
        except Exception as e:
            logger.warning(f"Error creating click step: {e}")
        return None
    
    def _create_input_step(self, action) -> Optional[InputStep]:
        """Create input step from action"""
        try:
            selector = self._extract_selector(action)
            text = getattr(action, 'text', None) or getattr(action, 'value', None)
            
            if selector and text:
                return InputStep(
                    action="input",
                    selector=selector,
                    text=text,
                    clear_first=True
                )
        except Exception as e:
            logger.warning(f"Error creating input step: {e}")
        return None
    
    def _create_key_press_step(self, action) -> Optional[KeyPressStep]:
        """Create key press step from action"""
        try:
            key = getattr(action, 'key', None)
            if key:
                return KeyPressStep(
                    action="key_press",
                    key=key
                )
        except Exception as e:
            logger.warning(f"Error creating key press step: {e}")
        return None
    
    def _create_scroll_step(self, action) -> Optional[ScrollStep]:
        """Create scroll step from action"""
        try:
            direction = getattr(action, 'direction', 'down')
            amount = getattr(action, 'amount', 500)
            
            return ScrollStep(
                action="scroll",
                direction=direction,
                amount=amount
            )
        except Exception as e:
            logger.warning(f"Error creating scroll step: {e}")
        return None
    
    def _create_select_step(self, action) -> Optional[SelectChangeStep]:
        """Create select step from action"""
        try:
            selector = self._extract_selector(action)
            value = getattr(action, 'value', None) or getattr(action, 'option', None)
            
            if selector and value:
                return SelectChangeStep(
                    action="select_change",
                    selector=selector,
                    value=value
                )
        except Exception as e:
            logger.warning(f"Error creating select step: {e}")
        return None
    
    def _extract_selector_from_element(self, element) -> Optional[str]:
        """Extract CSS selector from element object"""
        try:
            if not element:
                return None

            # Try different selector attributes
            if hasattr(element, 'css_selector') and element.css_selector:
                return element.css_selector
            elif hasattr(element, 'selector') and element.selector:
                return element.selector
            elif hasattr(element, 'xpath') and element.xpath:
                # Convert xpath to a simple selector if possible
                xpath = element.xpath
                if 'id=' in xpath:
                    # Extract ID from xpath
                    import re
                    id_match = re.search(r'id="([^"]+)"', xpath)
                    if id_match:
                        return f"#{id_match.group(1)}"
                return xpath
            elif hasattr(element, 'tag_name') and hasattr(element, 'attributes'):
                # Build selector from tag and attributes
                tag = element.tag_name
                attrs = element.attributes or {}

                if 'id' in attrs:
                    return f"#{attrs['id']}"
                elif 'class' in attrs:
                    classes = attrs['class'].replace(' ', '.')
                    return f"{tag}.{classes}"
                elif 'name' in attrs:
                    return f"{tag}[name='{attrs['name']}']"
                else:
                    return tag

            logger.warning("Could not extract selector from element")
            return None

        except Exception as e:
            logger.warning(f"Error extracting selector from element: {e}")
            return None

    def _extract_url_from_content(self, content: str) -> Optional[str]:
        """Extract URL from content string"""
        try:
            import re
            # Look for URLs in the content
            url_pattern = r'https?://[^\s]+'
            match = re.search(url_pattern, content)
            if match:
                return match.group(0)
            return None
        except Exception as e:
            logger.warning(f"Error extracting URL from content: {e}")
            return None

    def _extract_selector(self, action) -> Optional[str]:
        """Extract CSS selector from action (legacy method)"""
        try:
            # Try different possible selector attributes
            selector_attrs = ['selector', 'css_selector', 'xpath', 'element_selector']

            for attr in selector_attrs:
                if hasattr(action, attr):
                    selector = getattr(action, attr)
                    if selector:
                        return selector

            # Try to extract from element information
            if hasattr(action, 'element') and action.element:
                element = action.element
                if hasattr(element, 'selector'):
                    return element.selector
                elif hasattr(element, 'css_selector'):
                    return element.css_selector

            logger.warning("Could not extract selector from action")
            return None

        except Exception as e:
            logger.warning(f"Error extracting selector: {e}")
            return None
    
    def save_workflow(self, workflow_def: WorkflowDefinitionSchema, output_path: str) -> None:
        """Save workflow definition to JSON file"""
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(workflow_def.model_dump(), f, indent=2, ensure_ascii=False)
            
            logger.info(f"Workflow saved to: {output_file}")
            
        except Exception as e:
            logger.error(f"Error saving workflow to {output_path}: {e}")
            raise
