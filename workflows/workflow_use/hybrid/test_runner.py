"""
Hybrid test runner that combines workflow-use and browser-use
Main entry point for the smart-test integration
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

from browser_use import Agent as BrowserAgent, Browser
from langchain_core.language_models.chat_models import BaseChatModel

from workflow_use.smart_test.gherkin_processor import process_txt_to_gherkin
from workflow_use.smart_test.browser_prompts import generate_browser_task
from workflow_use.workflow.service import Workflow
from workflow_use.hybrid.simple_capture import SimpleWorkflowCapture
from workflow_use.hybrid.fallback_manager import FallbackManager

logger = logging.getLogger(__name__)


class HybridTestRunner:
    """
    Hybrid test runner that intelligently chooses between workflow-use and browser-use
    
    Flow:
    1. First run: txt → Gherkin → browser-use → capture workflow.json
    2. Subsequent runs: Use workflow.json → fallback to browser-use on failures
    """
    
    def __init__(
        self,
        llm: BaseChatModel,
        page_extraction_llm: Optional[BaseChatModel] = None,
        browser: Optional[Browser] = None
    ):
        self.llm = llm
        self.page_extraction_llm = page_extraction_llm or llm
        self.browser = browser or Browser()
        self.workflow_capture = SimpleWorkflowCapture()
        self.fallback_manager = FallbackManager(llm, page_extraction_llm, self.browser)
    
    async def run_test(self, txt_file_path: str, force_browser_use: bool = False) -> Dict[str, Any]:
        """
        Run a test from .txt file using hybrid approach

        Args:
            txt_file_path: Path to the .txt test file
            force_browser_use: Force browser-use execution (skip workflow-use)

        Returns:
            Test execution results
        """
        import time
        start_time = time.time()

        try:
            txt_path = Path(txt_file_path)
            if not txt_path.exists():
                raise FileNotFoundError(f"Test file not found: {txt_file_path}")

            # Generate workflow file path
            workflow_path = txt_path.with_suffix('.workflow.json')

            logger.info(f"Starting hybrid test execution for: {txt_file_path}")

            # Check if workflow exists and not forcing browser-use
            if workflow_path.exists() and not force_browser_use:
                logger.info("Workflow file exists, attempting workflow-use execution")
                result = await self._run_with_workflow(txt_file_path, workflow_path)
            else:
                logger.info("No workflow file found or forced browser-use, running first-time execution")
                result = await self._run_first_time(txt_file_path, workflow_path)

            # Add timing information
            end_time = time.time()
            execution_time = end_time - start_time
            result["execution_time_seconds"] = round(execution_time, 2)

            logger.info(f"Test execution completed in {execution_time:.2f} seconds")
            return result
                
        except Exception as e:
            logger.error(f"Error in hybrid test execution: {e}")
            return {
                "success": False,
                "error": str(e),
                "execution_method": "error"
            }
    
    async def _run_first_time(self, txt_file_path: str, workflow_path: Path) -> Dict[str, Any]:
        """First-time execution: txt → Gherkin → browser-use → capture workflow"""
        try:
            # Step 1: Convert txt to Gherkin
            logger.info("Converting .txt file to Gherkin scenario")
            gherkin_scenario = process_txt_to_gherkin(txt_file_path, self.llm)

            # Step 2: Execute with browser-use
            logger.info("Executing Gherkin scenario with browser-use")
            browser_task = generate_browser_task(gherkin_scenario, "stop_on_assertion")

            browser_agent = BrowserAgent(
                task=browser_task,
                llm=self.llm,
                browser_session=self.browser,
                use_vision=True
            )

            agent_history = await browser_agent.run(max_steps=50)

            # Step 3: Analyze results
            success = self._analyze_browser_results(agent_history)

            if success:
                # Step 4: Create workflow from browser-use agent history
                logger.info("Creating workflow from successful browser-use execution")
                test_name = Path(txt_file_path).stem
                workflow_def = self.workflow_capture.create_workflow_from_browser_use(
                    agent_history,
                    test_name,
                    success=True
                )

                if workflow_def:
                    # Save workflow using existing ui-workflow format
                    saved = self.workflow_capture.save_workflow(workflow_def, str(workflow_path))

                    return {
                        "success": True,
                        "execution_method": "browser-use-first-time",
                        "gherkin_scenario": gherkin_scenario,
                        "workflow_captured": saved,
                        "workflow_path": str(workflow_path) if saved else None,
                        "steps_executed": len(workflow_def.steps),
                        "agent_history": agent_history
                    }
                else:
                    return {
                        "success": True,
                        "execution_method": "browser-use-first-time",
                        "gherkin_scenario": gherkin_scenario,
                        "workflow_captured": False,
                        "error": "Failed to create workflow from Gherkin",
                        "agent_history": agent_history
                    }
            else:
                return {
                    "success": False,
                    "execution_method": "browser-use-first-time",
                    "gherkin_scenario": gherkin_scenario,
                    "workflow_captured": False,
                    "error": "Browser-use execution failed",
                    "agent_history": agent_history
                }

        except Exception as e:
            logger.error(f"Error in first-time execution: {e}")
            return {
                "success": False,
                "execution_method": "browser-use-first-time",
                "error": str(e)
            }


    
    async def _run_with_workflow(self, txt_file_path: str, workflow_path: Path) -> Dict[str, Any]:
        """Subsequent execution: Use workflow-use with browser-use fallback"""
        try:
            # Load Gherkin scenario for fallback context
            gherkin_scenario = process_txt_to_gherkin(txt_file_path, self.llm)
            
            # Load and execute workflow
            logger.info(f"Loading workflow from: {workflow_path}")
            workflow = Workflow.load_from_file(
                str(workflow_path),
                browser=self.browser,
                llm=self.llm,
                page_extraction_llm=self.page_extraction_llm
            )
            
            # Execute workflow with step-by-step fallback
            results = await self._execute_workflow_with_fallback(
                workflow, gherkin_scenario, str(workflow_path)
            )
            
            return {
                "success": results["overall_success"],
                "execution_method": "workflow-use-with-fallback",
                "gherkin_scenario": gherkin_scenario,
                "workflow_path": str(workflow_path),
                "step_results": results["step_results"],
                "fallback_steps": results["fallback_steps"],
                "workflow_updated": results["workflow_updated"]
            }
            
        except Exception as e:
            logger.error(f"Error in workflow execution: {e}")
            # Fallback to full browser-use execution
            logger.info("Falling back to full browser-use execution")
            return await self._run_first_time(txt_file_path, workflow_path)
    
    async def _execute_workflow_with_fallback(
        self, 
        workflow: Workflow, 
        gherkin_scenario: str,
        workflow_path: str
    ) -> Dict[str, Any]:
        """Execute workflow with step-level fallback to browser-use"""
        step_results = []
        fallback_steps = []
        workflow_updated = False
        overall_success = True
        
        try:
            total_steps = len(workflow.steps)
            logger.info(f"Executing workflow with {total_steps} steps")
            
            for step_index in range(total_steps):
                logger.info(f"Executing step {step_index + 1}/{total_steps}")

                # Time each step
                import time
                step_start = time.time()

                # Execute step with fallback
                success, result, updated_step = await self.fallback_manager.execute_step_with_fallback(
                    workflow, step_index, gherkin_scenario
                )

                step_end = time.time()
                step_duration = step_end - step_start

                # Determine execution method based on result content and duration
                execution_method = self._determine_execution_method(result, step_duration, updated_step)

                step_results.append({
                    "step_index": step_index,
                    "success": success,
                    "method": execution_method,
                    "result": result,
                    "duration_seconds": round(step_duration, 2)
                })

                logger.info(f"Step {step_index + 1} completed in {step_duration:.2f}s via {execution_method}")
                
                if not success:
                    overall_success = False
                    logger.error(f"Step {step_index} failed completely")
                    break
                
                # If step was updated via browser-use fallback
                if updated_step:
                    fallback_steps.append(step_index)
                    
                    # Update workflow file
                    update_success = await self.fallback_manager.update_workflow_with_step(
                        workflow_path, step_index, updated_step
                    )
                    
                    if update_success:
                        workflow_updated = True
                        logger.info(f"Updated workflow step {step_index}")
            
            return {
                "overall_success": overall_success,
                "step_results": step_results,
                "fallback_steps": fallback_steps,
                "workflow_updated": workflow_updated
            }
            
        except Exception as e:
            logger.error(f"Error in workflow execution with fallback: {e}")
            return {
                "overall_success": False,
                "step_results": step_results,
                "fallback_steps": fallback_steps,
                "workflow_updated": workflow_updated,
                "error": str(e)
            }
    
    def _analyze_browser_results(self, agent_history) -> bool:
        """Analyze browser-use results to determine success"""
        try:
            if not agent_history:
                return False

            # Check if agent_history is a list or has all_results attribute
            if hasattr(agent_history, 'all_results'):
                results = agent_history.all_results
            elif isinstance(agent_history, list):
                results = agent_history
            else:
                # Try to access as AgentHistoryList directly
                try:
                    results = list(agent_history)
                except:
                    logger.warning(f"Could not extract results from agent_history type: {type(agent_history)}")
                    return False

            if not results:
                return False

            # Check the last result for success indicators
            last_result = results[-1]

            # Check success attribute first
            if hasattr(last_result, 'success') and last_result.success is not None:
                return last_result.success

            # Check extracted_content for success indicators
            if hasattr(last_result, 'extracted_content'):
                content = str(last_result.extracted_content).lower()

                # Look for explicit success/failure indicators
                if 'final status: passed' in content or 'task completed successfully' in content:
                    return True
                elif 'final status: failed' in content or 'execution failed' in content:
                    return False
                elif 'passed' in content and 'failed' not in content:
                    return True

            # If no explicit indicators, assume success if execution completed without errors
            return True

        except Exception as e:
            logger.warning(f"Error analyzing browser results: {e}")
            return False
    
    async def run_test_suite(self, test_directory: str) -> Dict[str, Any]:
        """Run all .txt test files in a directory"""
        try:
            test_dir = Path(test_directory)
            if not test_dir.exists():
                raise FileNotFoundError(f"Test directory not found: {test_directory}")
            
            # Find all .txt files
            txt_files = list(test_dir.glob("**/*.txt"))
            
            if not txt_files:
                logger.warning(f"No .txt test files found in {test_directory}")
                return {
                    "success": True,
                    "total_tests": 0,
                    "passed_tests": 0,
                    "failed_tests": 0,
                    "results": []
                }
            
            logger.info(f"Found {len(txt_files)} test files")
            
            results = []
            passed_count = 0
            failed_count = 0
            
            for txt_file in txt_files:
                logger.info(f"Running test: {txt_file}")
                
                try:
                    result = await self.run_test(str(txt_file))
                    results.append({
                        "test_file": str(txt_file),
                        "result": result
                    })
                    
                    if result.get("success", False):
                        passed_count += 1
                    else:
                        failed_count += 1
                        
                except Exception as e:
                    logger.error(f"Error running test {txt_file}: {e}")
                    results.append({
                        "test_file": str(txt_file),
                        "result": {
                            "success": False,
                            "error": str(e)
                        }
                    })
                    failed_count += 1
            
            return {
                "success": failed_count == 0,
                "total_tests": len(txt_files),
                "passed_tests": passed_count,
                "failed_tests": failed_count,
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Error running test suite: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _determine_execution_method(self, result, duration_seconds, updated_step):
        """
        Determine the actual execution method based on result content and timing
        """
        if result is None:
            return "unknown"

        result_str = str(result)

        # Check for browser-use indicators in the result
        browser_use_indicators = [
            "AgentHistoryList",
            "all_model_outputs",
            "input_text",
            "interacted_element",
            "DOMHistoryElement",
            "into index"
        ]

        # Check for workflow-use indicators
        workflow_use_indicators = [
            "🔗  Navigated to URL:",
            "⌨️  Input",
            "🖱️  Clicked element with CSS selector:",
            "with CSS selector:"
        ]

        # If result contains browser-use indicators, it's browser-use
        if any(indicator in result_str for indicator in browser_use_indicators):
            return "browser-use-fallback"

        # If result contains workflow-use indicators and duration is reasonable, it's workflow-use
        if any(indicator in result_str for indicator in workflow_use_indicators):
            # Fast execution (< 10s) is likely workflow-use
            if duration_seconds < 10:
                return "workflow-use"
            # Slow execution (> 15s) is likely browser-use fallback
            elif duration_seconds > 15:
                return "browser-use-fallback"
            else:
                return "workflow-use"  # Medium duration, assume workflow-use

        # Fallback to duration-based detection
        if duration_seconds < 5:
            return "workflow-use"
        elif duration_seconds > 20:
            return "browser-use-fallback"
        else:
            return "hybrid"
