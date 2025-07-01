"""
Smart-Test StepTracker Implementation for Hybrid Testing Framework
Copied and adapted from smart-test framework for step-by-step assertion evaluation
"""

import re
import json
import logging
from typing import Dict, List, Any, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class StepTracker:
    """Tracks individual Gherkin step execution and results"""

    @staticmethod
    def extract_step_results(history_data: Dict[str, Any], gherkin_content: str) -> List[Dict[str, Any]]:
        """Extract step-by-step results from browser agent execution history"""
        step_results = []

        # Parse Gherkin steps
        gherkin_steps = StepTracker._parse_gherkin_steps(gherkin_content)

        # Extract step tracking from agent's extracted content and model actions
        all_content = []

        # Combine all sources of agent output
        if 'extracted_content' in history_data:
            all_content.extend(history_data['extracted_content'])

        if 'model_actions' in history_data:
            for action in history_data['model_actions']:
                if isinstance(action, dict) and 'content' in action:
                    all_content.append(action['content'])
                elif isinstance(action, str):
                    all_content.append(action)

        # Join all content for analysis
        content = '\n'.join(str(item) for item in all_content)

        # Look for explicit step tracking patterns
        step_starts = []
        step_results_found = []
        step_failures = []

        for content_item in all_content:
            if isinstance(content_item, str):
                # Look for STEP_START patterns
                step_start_matches = re.findall(r'STEP_START:\s*(.+?)(?=\n|$)', content_item, re.IGNORECASE)
                step_starts.extend(step_start_matches)

                # Look for STEP_RESULT patterns
                step_result_matches = re.findall(r'STEP_RESULT:\s*(PASSED|FAILED)\s*-\s*(.+?)(?=\n|$)', content_item, re.IGNORECASE)
                step_results_found.extend(step_result_matches)

                # Look for STEP_FAILED patterns
                step_failed_matches = re.findall(r'STEP_FAILED:\s*(.+?)(?=\n|$)', content_item, re.IGNORECASE)
                for match in step_failed_matches:
                    step_failures.append(('FAILED', match))

                # Also look for step tracking in memory and goal patterns
                memory_step_matches = re.findall(r'Steps? completed:.*?(\d+)\.(.*?)(?=\d+\.|Current|Next|$)', content_item, re.IGNORECASE | re.DOTALL)
                for match in memory_step_matches:
                    step_num, step_desc = match
                    step_results_found.append(('PASSED', f'Step {step_num}: {step_desc.strip()}'))

                # Look for goal patterns that indicate step completion
                goal_matches = re.findall(r'Next goal:\s*STEP_START:\s*(.+?)(?=\n|$)', content_item, re.IGNORECASE)
                step_starts.extend(goal_matches)

                # Look for evaluation success patterns
                eval_matches = re.findall(r'Eval:\s*Success\s*-\s*(.+?)(?=\n|$)', content_item, re.IGNORECASE)
                for eval_match in eval_matches:
                    step_results_found.append(('PASSED', eval_match.strip()))

        # Also extract error information from browser action results
        browser_errors = StepTracker._extract_browser_errors(history_data)

        # Extract parsing errors and agent failures
        parsing_errors = StepTracker._extract_parsing_errors(history_data)

        # Combine all types of failures
        all_failures = step_failures + browser_errors + parsing_errors

        # If we have explicit step tracking, use it
        if step_starts or step_results_found or all_failures:
            step_results = StepTracker._process_explicit_step_tracking(
                gherkin_steps, step_starts, step_results_found, all_failures
            )
        else:
            # Fallback: infer step results from actions and content
            step_results = StepTracker._infer_step_results_from_actions(
                gherkin_steps, history_data
            )

        logger.info(f"StepTracker extracted {len(step_results)} step results from {len(gherkin_steps)} Gherkin steps")
        return step_results

    @staticmethod
    def _parse_gherkin_steps(gherkin_content: str) -> List[str]:
        """Parse Gherkin content to extract individual steps"""
        steps = []
        lines = gherkin_content.split('\n')
        
        for line in lines:
            line = line.strip()
            # Look for Gherkin step keywords
            if re.match(r'^\s*(Given|When|Then|And|But)\s+', line, re.IGNORECASE):
                steps.append(line)
        
        return steps

    @staticmethod
    def _extract_browser_errors(history_data: Dict[str, Any]) -> List[Tuple[str, str]]:
        """Extract browser-specific errors from history data"""
        errors = []
        
        # Check for browser action failures
        if 'extracted_content' in history_data:
            for content in history_data['extracted_content']:
                if isinstance(content, str):
                    content_lower = content.lower()
                    if any(error_indicator in content_lower for error_indicator in [
                        'element not found', 'timeout', 'failed to click', 'failed to type',
                        'navigation failed', 'page load failed'
                    ]):
                        errors.append(('FAILED', f'Browser action failed: {content[:100]}...'))
        
        return errors

    @staticmethod
    def _extract_parsing_errors(history_data: Dict[str, Any]) -> List[Tuple[str, str]]:
        """Extract parsing and agent errors from history data"""
        errors = []
        
        # Check for parsing failures
        if 'errors' in history_data:
            for error in history_data['errors']:
                if isinstance(error, str):
                    error_lower = error.lower()
                    if 'failed to parse' in error_lower or 'could not parse' in error_lower:
                        errors.append(('FAILED', f'Parsing error: {error}'))
                    elif 'result failed' in error_lower:
                        errors.append(('FAILED', f'Agent execution failed: {error}'))
        
        return errors

    @staticmethod
    def _process_explicit_step_tracking(
        gherkin_steps: List[str],
        step_starts: List[str],
        step_results_found: List[Tuple[str, str]],
        all_failures: List[Tuple[str, str]]
    ) -> List[Dict[str, Any]]:
        """Process explicit step tracking information"""
        step_results = []

        # Check if there are any overall failure indicators
        has_overall_failure = any('task completed without success' in message.lower() or
                                'blocker encountered' in message.lower() or
                                'execution incomplete' in message.lower() or
                                'gherkin scenario execution incomplete' in message.lower()
                                for _, message in step_results_found + all_failures)

        for i, step in enumerate(gherkin_steps):
            # Default status depends on whether there's an overall failure
            default_status = 'FAILED' if has_overall_failure else 'PASSED'
            default_message = ('Step likely failed due to overall execution failure' if has_overall_failure
                             else 'Step executed successfully')

            step_info = {
                'step_number': i + 1,
                'step_text': step,
                'status': default_status,
                'message': default_message,
                'timestamp': datetime.now().isoformat(),
                'execution_order': i + 1
            }

            # Check if this step was explicitly tracked
            step_found = False

            # Look for matching step in results
            for j, (status, message) in enumerate(step_results_found):
                if StepTracker._steps_match(step, message) or i == j:
                    # If there's an overall failure, don't override with PASSED
                    if has_overall_failure and status.upper() == 'PASSED':
                        # Keep the default FAILED status but update the message
                        step_info['message'] = f"Step tracking shows PASSED but overall execution failed: {message.strip()}"
                    else:
                        step_info['status'] = status.upper()
                        step_info['message'] = message.strip()
                    step_found = True
                    break

            # Check for failures (these always override)
            for status, message in all_failures:
                if StepTracker._steps_match(step, message):
                    step_info['status'] = 'FAILED'
                    step_info['message'] = message.strip()
                    step_found = True
                    break

            step_results.append(step_info)

        return step_results

    @staticmethod
    def _steps_match(gherkin_step: str, tracked_message: str) -> bool:
        """Check if a Gherkin step matches a tracked message"""
        # Normalize both strings for comparison
        gherkin_normalized = re.sub(r'^\s*(Given|When|Then|And|But)\s+', '', gherkin_step, flags=re.IGNORECASE).lower()
        tracked_normalized = tracked_message.lower()

        # Remove common prefixes from tracked message
        tracked_normalized = re.sub(r'^(step \d+:?\s*)', '', tracked_normalized)

        # Check for substantial overlap
        return (gherkin_normalized in tracked_normalized or
                tracked_normalized in gherkin_normalized or
                StepTracker._calculate_similarity(gherkin_normalized, tracked_normalized) > 0.6)

    @staticmethod
    def _calculate_similarity(str1: str, str2: str) -> float:
        """Calculate similarity between two strings using simple word overlap"""
        words1 = set(str1.split())
        words2 = set(str2.split())

        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union)

    @staticmethod
    def _infer_step_results_from_actions(gherkin_steps: List[str], history_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Infer step results from browser actions and content when explicit tracking is not available"""
        step_results = []

        # Get overall execution status
        overall_status = 'PASSED'  # Default assumption

        # Check for final status indicators first
        final_status_indicators = history_data.get('final_status_indicators', [])
        if 'FAILED' in final_status_indicators:
            overall_status = 'FAILED'
            logger.info("Overall status set to FAILED based on final status indicators")

        # Check for errors in history
        errors = history_data.get('errors', [])
        parsing_failures = False
        agent_failures = False
        task_completion_failures = False

        for error in errors:
            if isinstance(error, str):
                error_lower = error.lower()
                if 'failed to parse' in error_lower or 'could not parse' in error_lower:
                    parsing_failures = True
                    overall_status = 'FAILED'
                elif 'result failed' in error_lower:
                    agent_failures = True
                    overall_status = 'FAILED'
                elif 'task completed without success' in error_lower or 'blocker encountered' in error_lower:
                    task_completion_failures = True
                    overall_status = 'FAILED'
                    logger.info(f"Task completion failure detected: {error[:100]}...")
                else:
                    overall_status = 'FAILED'

        # Extract actions and content
        actions = history_data.get('model_actions', [])
        extracted_content = history_data.get('extracted_content', [])

        # Create step results based on available information
        for i, step in enumerate(gherkin_steps):
            step_info = {
                'step_number': i + 1,
                'step_text': step,
                'status': 'INFERRED',  # Will be updated based on analysis
                'message': 'Step status inferred from execution',
                'timestamp': datetime.now().isoformat(),
                'execution_order': i + 1
            }

            # Try to match step with actions
            if i < len(actions):
                action_name = actions[i] if isinstance(actions[i], str) else str(actions[i])
                step_info['message'] = f'Executed action: {action_name}'

                # Check if there's corresponding content
                if i < len(extracted_content):
                    content = extracted_content[i]
                    if isinstance(content, str):
                        if 'error' in content.lower() or 'failed' in content.lower():
                            step_info['status'] = 'FAILED'
                            # Use the error categorization for better failure messages
                            step_info['message'] = StepTracker._categorize_error(content)
                        else:
                            step_info['status'] = 'PASSED'
                            step_info['message'] = f'Completed: {content[:100]}...'

            # If we couldn't determine status from actions, use overall status
            if step_info['status'] == 'INFERRED':
                if overall_status == 'FAILED':
                    if task_completion_failures:
                        step_info['status'] = 'FAILED'
                        step_info['message'] = 'Task execution blocked - unable to complete due to business logic constraints or data conflicts'
                    elif parsing_failures:
                        step_info['status'] = 'FAILED'
                        step_info['message'] = 'AI model parsing error - response could not be processed (possible token limit or format issue)'
                    elif agent_failures:
                        step_info['status'] = 'FAILED'
                        step_info['message'] = 'AI agent failed after multiple retry attempts - persistent execution issue'
                    elif i == len(gherkin_steps) - 1:
                        # Last step likely failed if overall failed
                        step_info['status'] = 'FAILED'
                        step_info['message'] = 'Step likely failed based on overall execution result'
                    else:
                        # Earlier steps might have passed before the failure
                        step_info['status'] = 'PASSED'
                        step_info['message'] = 'Step likely passed before failure occurred'
                else:
                    step_info['status'] = 'PASSED'
                    step_info['message'] = 'Step completed successfully (inferred from overall success)'

            step_results.append(step_info)

        return step_results

    @staticmethod
    def _categorize_error(error_content: str) -> str:
        """Categorize error content for better failure messages"""
        error_lower = error_content.lower()

        if 'blocker encountered' in error_lower or 'unable to proceed' in error_lower:
            return 'Business logic blocker - execution stopped due to data conflicts or validation errors'
        elif 'task completed without success' in error_lower:
            return 'Task execution failed - completed but did not achieve success criteria'
        elif 'email conflict' in error_lower or 'already has an ongoing contract' in error_lower:
            return 'Data conflict error - duplicate or conflicting data prevented operation completion'
        elif 'element not found' in error_lower or 'no such element' in error_lower:
            return 'Element location failed - target element not found on page'
        elif 'timeout' in error_lower:
            return 'Operation timeout - element or condition not met within time limit'
        elif 'click' in error_lower and 'failed' in error_lower:
            return 'Click action failed - element not clickable or interaction blocked'
        elif 'type' in error_lower and 'failed' in error_lower:
            return 'Text input failed - field not accessible or input rejected'
        elif 'navigation' in error_lower and 'failed' in error_lower:
            return 'Page navigation failed - URL unreachable or redirect issue'
        elif 'parse' in error_lower and 'failed' in error_lower:
            return 'AI model parsing error - response format issue or token limit exceeded'
        else:
            return f'Execution error: {error_content[:100]}...'
