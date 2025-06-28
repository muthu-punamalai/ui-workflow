"""
Fallback manager for handling workflow-use failures and browser-use recovery
"""

import logging
from typing import Optional, Tuple, Any, Dict, List
from pathlib import Path

from browser_use import Agent as BrowserAgent, Browser
from langchain_core.language_models.chat_models import BaseChatModel

from workflow_use.workflow.service import Workflow
from workflow_use.smart_test.browser_prompts import generate_browser_task
from workflow_use.hybrid.simple_capture import SimpleWorkflowCapture
from workflow_use.schema.views import WorkflowStep

logger = logging.getLogger(__name__)


class FallbackManager:
    """Manages fallback between workflow-use and browser-use execution"""
    
    def __init__(
        self,
        llm: BaseChatModel,
        page_extraction_llm: Optional[BaseChatModel] = None,
        browser: Optional[Browser] = None
    ):
        self.llm = llm
        self.page_extraction_llm = page_extraction_llm or llm
        self.browser = browser
        self.workflow_capture = SimpleWorkflowCapture()
    
    async def execute_step_with_fallback(
        self,
        workflow: Workflow,
        step_index: int,
        gherkin_scenario: str,
        max_retries: int = 2
    ) -> Tuple[bool, Optional[Any], Optional[WorkflowStep]]:
        """
        Execute a single workflow step with browser-use fallback on failure
        
        Args:
            workflow: Workflow instance
            step_index: Index of the step to execute
            gherkin_scenario: Full Gherkin scenario for context
            max_retries: Maximum number of retry attempts
            
        Returns:
            Tuple of (success, result, updated_step)
        """
        try:
            # First attempt: Use workflow-use
            logger.info(f"Attempting workflow-use execution for step {step_index}")
            
            try:
                result = await workflow.run_step(step_index)
                logger.info(f"Workflow-use step {step_index} succeeded")
                return True, result, None
                
            except Exception as workflow_error:
                logger.warning(f"Workflow-use step {step_index} failed: {workflow_error}")
                
                # Fallback: Use browser-use
                return await self._fallback_to_browser_use(
                    workflow, step_index, gherkin_scenario, max_retries
                )
                
        except Exception as e:
            logger.error(f"Error in step execution with fallback: {e}")
            return False, None, None
    
    async def _fallback_to_browser_use(
        self,
        workflow: Workflow,
        step_index: int,
        gherkin_scenario: str,
        max_retries: int
    ) -> Tuple[bool, Optional[Any], Optional[WorkflowStep]]:
        """Execute step using browser-use agent"""
        try:
            logger.info(f"Falling back to browser-use for step {step_index}")
            
            # Extract the specific step from Gherkin scenario
            step_gherkin = self._extract_step_from_gherkin(gherkin_scenario, step_index)
            
            if not step_gherkin:
                logger.error(f"Could not extract step {step_index} from Gherkin scenario")
                return False, None, None
            
            # Create browser-use task for this specific step
            browser_task = generate_browser_task(step_gherkin, "stop_on_assertion")
            
            # Execute with browser-use agent
            browser_agent = BrowserAgent(
                task=browser_task,
                llm=self.llm,
                browser_session=self.browser or workflow.browser,
                use_vision=True
            )
            
            # Run the agent
            agent_history = await browser_agent.run(max_steps=5)
            
            if agent_history and len(agent_history) > 0:
                # Check if execution was successful
                last_result = agent_history[-1]
                if self._is_execution_successful(last_result):
                    logger.info(f"Browser-use step {step_index} succeeded")
                    
                    # Capture the successful action as a workflow step
                    updated_step = await self._capture_step_from_history(
                        agent_history, step_index
                    )
                    
                    return True, agent_history, updated_step
                else:
                    logger.error(f"Browser-use step {step_index} failed")
                    return False, None, None
            else:
                logger.error(f"Browser-use returned empty history for step {step_index}")
                return False, None, None
                
        except Exception as e:
            logger.error(f"Error in browser-use fallback: {e}")
            return False, None, None
    
    def _extract_step_from_gherkin(self, gherkin_scenario: str, step_index: int) -> Optional[str]:
        """Extract a specific step from Gherkin scenario"""
        try:
            lines = gherkin_scenario.strip().split('\n')
            step_lines = []
            current_step = 0
            
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Check if this is a step line
                    if any(line.startswith(keyword) for keyword in ['Given', 'When', 'Then', 'And', 'But']):
                        if current_step == step_index:
                            step_lines.append(line)
                            # Include any continuation lines
                            continue
                        elif current_step > step_index:
                            break
                        current_step += 1
                    elif step_lines:  # Continuation of current step
                        step_lines.append(line)
            
            if step_lines:
                # Create a minimal Gherkin scenario for this step
                feature_line = next((line for line in lines if line.strip().startswith('Feature:')), 'Feature: Test Step')
                scenario_line = next((line for line in lines if line.strip().startswith('Scenario:')), 'Scenario: Execute Step')
                
                return f"{feature_line}\n\n{scenario_line}\n    " + "\n    ".join(step_lines)
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting step from Gherkin: {e}")
            return None
    
    def _is_execution_successful(self, agent_result) -> bool:
        """Check if browser-use execution was successful"""
        try:
            # Check for success indicators in the result
            if hasattr(agent_result, 'success'):
                return agent_result.success
            
            # Check for failure keywords in the content
            if hasattr(agent_result, 'content'):
                content = str(agent_result.content).lower()
                failure_keywords = ['failed', 'error', 'timeout', 'not found', 'step_failed']
                success_keywords = ['passed', 'success', 'step_result: passed']
                
                # If we find success keywords, consider it successful
                if any(keyword in content for keyword in success_keywords):
                    return True
                
                # If we find failure keywords, consider it failed
                if any(keyword in content for keyword in failure_keywords):
                    return False
            
            # Default to success if no clear indicators
            return True
            
        except Exception as e:
            logger.warning(f"Error checking execution success: {e}")
            return False
    
    async def _capture_step_from_history(
        self, 
        agent_history, 
        step_index: int
    ) -> Optional[WorkflowStep]:
        """Capture workflow step from browser-use agent history"""
        try:
            if not agent_history:
                return None
            
            # Use workflow capture to convert agent history to workflow step
            workflow_def = self.workflow_capture.create_workflow_from_browser_use(
                agent_history,
                f"step_{step_index}",
                success=True
            )
            
            if workflow_def.steps:
                return workflow_def.steps[0]  # Return the first captured step
            
            return None
            
        except Exception as e:
            logger.error(f"Error capturing step from history: {e}")
            return None
    
    async def update_workflow_with_step(
        self,
        workflow_path: str,
        step_index: int,
        updated_step: WorkflowStep
    ) -> bool:
        """Update workflow file with new step definition"""
        try:
            # Load existing workflow
            workflow_file = Path(workflow_path)
            if not workflow_file.exists():
                logger.error(f"Workflow file not found: {workflow_path}")
                return False
            
            import json
            with open(workflow_file, 'r', encoding='utf-8') as f:
                workflow_data = json.load(f)
            
            # Update the specific step
            if 'steps' in workflow_data and step_index < len(workflow_data['steps']):
                workflow_data['steps'][step_index] = updated_step.model_dump()
                
                # Update version and metadata
                workflow_data['version'] = self._increment_version(workflow_data.get('version', '1.0.0'))
                if 'metadata' not in workflow_data:
                    workflow_data['metadata'] = {}
                workflow_data['metadata']['last_updated'] = self._get_current_timestamp()
                workflow_data['metadata']['updated_steps'] = workflow_data['metadata'].get('updated_steps', [])
                if step_index not in workflow_data['metadata']['updated_steps']:
                    workflow_data['metadata']['updated_steps'].append(step_index)
                
                # Save updated workflow
                with open(workflow_file, 'w', encoding='utf-8') as f:
                    json.dump(workflow_data, f, indent=2, ensure_ascii=False)
                
                logger.info(f"Updated workflow step {step_index} in {workflow_path}")
                return True
            else:
                logger.error(f"Invalid step index {step_index} for workflow")
                return False
                
        except Exception as e:
            logger.error(f"Error updating workflow with step: {e}")
            return False
    
    def _increment_version(self, version: str) -> str:
        """Increment workflow version"""
        try:
            parts = version.split('.')
            if len(parts) >= 3:
                patch = int(parts[2]) + 1
                return f"{parts[0]}.{parts[1]}.{patch}"
            else:
                return f"{version}.1"
        except:
            return "1.0.1"
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()
