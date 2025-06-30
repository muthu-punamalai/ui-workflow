"""
Smart-Test Assertion Evaluator for Hybrid Testing Framework
Integrates smart-test assertion logic for reliable success/failure detection
"""

import re
import logging
from typing import Dict, List, Tuple, Any, Optional

logger = logging.getLogger(__name__)

class AssertionEvaluator:
    """Evaluates test assertions using smart-test patterns for reliable success detection"""
    
    def __init__(self):
        self.assertion_patterns = {
            'passed': [
                r'ASSERTION PASSED',
                r'STEP_RESULT: PASSED',
                r'Successfully (navigated|logged in|clicked|verified)',
                r'option verified visible',
                r'button verified visible',
                # Browser-use success patterns
                r'All assertions passed',
                r'Task completed successfully',
                r'Scenario completed',
                r'actions were completed successfully',
                r'✅ Task completed successfully',
                r'All steps completed successfully'
            ],
            'failed': [
                r'ASSERTION FAILED',
                r'STEP_RESULT: FAILED',
                r'Assertion failed at step',
                r'not found',
                r'Login attempt failed',
                r'Authentication Error',
                r'Execution stopped.*due to.*failure',
                r'❌.*failed',
                r'Task failed'
            ]
        }
    
    def evaluate_browser_use_results(self, agent_history) -> Tuple[bool, Dict[str, Any]]:
        """
        Evaluate browser-use execution results using smart-test assertion patterns
        
        Returns:
            Tuple[bool, Dict]: (success, detailed_results)
        """
        try:
            if not agent_history:
                return False, {"error": "No agent history available"}
            
            # Extract all result content
            all_content = self._extract_all_content(agent_history)
            
            # Analyze step-by-step results
            step_results = self._analyze_step_results(all_content)
            
            # Check for assertion results
            assertion_results = self._analyze_assertions(all_content)
            
            # Determine overall success
            overall_success = self._determine_overall_success(step_results, assertion_results, all_content)
            
            detailed_results = {
                "overall_success": overall_success,
                "step_results": step_results,
                "assertion_results": assertion_results,
                "failure_details": self._extract_failure_details(all_content) if not overall_success else None,
                "evaluation_method": "smart-test-assertions"
            }
            
            logger.info(f"Assertion evaluation complete: {'PASSED' if overall_success else 'FAILED'}")
            if not overall_success and detailed_results["failure_details"]:
                logger.info(f"Failure details: {detailed_results['failure_details'][:200]}...")
            
            return overall_success, detailed_results
            
        except Exception as e:
            logger.error(f"Error evaluating assertions: {e}")
            return False, {"error": str(e), "evaluation_method": "error"}
    
    def _extract_all_content(self, agent_history) -> str:
        """Extract all content from agent history for analysis"""
        all_content = []
        
        try:
            # Handle different agent history formats
            if hasattr(agent_history, 'all_results'):
                results = agent_history.all_results
            elif isinstance(agent_history, list):
                results = agent_history
            else:
                results = list(agent_history)
            
            for result in results:
                if hasattr(result, 'extracted_content') and result.extracted_content:
                    all_content.append(str(result.extracted_content))
                    
        except Exception as e:
            logger.warning(f"Error extracting content: {e}")
        
        return "\n".join(all_content)
    
    def _analyze_step_results(self, content: str) -> List[Dict[str, Any]]:
        """Analyze step-by-step results using smart-test patterns"""
        step_results = []

        # Debug: Log content length and sample
        logger.info(f"Analyzing content length: {len(content)} characters")
        logger.info(f"Content sample: {content[:500]}...")

        # Look for STEP_RESULT patterns
        step_pattern = r'STEP_RESULT: (PASSED|FAILED) - (.+?)(?=\n|$)'
        matches = re.finditer(step_pattern, content, re.IGNORECASE | re.MULTILINE)

        match_count = 0
        for i, match in enumerate(matches):
            match_count += 1
            status = match.group(1).upper()
            description = match.group(2).strip()

            step_results.append({
                "step_number": i + 1,
                "status": status,
                "description": description,
                "passed": status == "PASSED"
            })

        logger.info(f"Found {match_count} STEP_RESULT patterns")
        
        # Also look for numbered step patterns
        numbered_pattern = r'(\d+)\.\s+(Given|When|And|Then).*?-\s+(PASSED|FAILED)'
        numbered_matches = re.finditer(numbered_pattern, content, re.IGNORECASE | re.MULTILINE)
        
        for match in numbered_matches:
            step_num = int(match.group(1))
            step_type = match.group(2)
            status = match.group(3).upper()
            
            # Avoid duplicates
            if not any(sr["step_number"] == step_num for sr in step_results):
                step_results.append({
                    "step_number": step_num,
                    "step_type": step_type,
                    "status": status,
                    "passed": status == "PASSED"
                })
        
        return sorted(step_results, key=lambda x: x["step_number"])
    
    def _analyze_assertions(self, content: str) -> List[Dict[str, Any]]:
        """Analyze assertion results using smart-test patterns"""
        assertion_results = []
        
        # Look for ASSERTION PASSED/FAILED patterns
        assertion_pattern = r'ASSERTION (PASSED|FAILED)[:\s-]*(.+?)(?=\n|$)'
        matches = re.finditer(assertion_pattern, content, re.IGNORECASE | re.MULTILINE)
        
        for i, match in enumerate(matches):
            status = match.group(1).upper()
            description = match.group(2).strip()
            
            assertion_results.append({
                "assertion_number": i + 1,
                "status": status,
                "description": description,
                "passed": status == "PASSED"
            })
        
        # Look for "Then" step assertions
        then_pattern = r'Then.*?(ASSERTION PASSED|ASSERTION FAILED|verified visible|not found)'
        then_matches = re.finditer(then_pattern, content, re.IGNORECASE | re.MULTILINE)
        
        for match in then_matches:
            assertion_text = match.group(0)
            if "PASSED" in assertion_text or "verified visible" in assertion_text:
                status = "PASSED"
            else:
                status = "FAILED"
            
            # Avoid duplicates
            if not any(ar["description"] in assertion_text for ar in assertion_results):
                assertion_results.append({
                    "assertion_number": len(assertion_results) + 1,
                    "status": status,
                    "description": assertion_text,
                    "passed": status == "PASSED"
                })
        
        return assertion_results
    
    def _determine_overall_success(self, step_results: List[Dict], assertion_results: List[Dict], content: str) -> bool:
        """Determine overall test success based on smart-test criteria"""
        
        # Check for explicit failure indicators
        failure_indicators = [
            "Execution stopped.*due to.*failure",
            "Authentication Error",
            "critical.*failure",
            "Unable to proceed"
        ]
        
        for indicator in failure_indicators:
            if re.search(indicator, content, re.IGNORECASE):
                logger.info(f"Found critical failure indicator: {indicator}")
                return False
        
        # Check step results
        if step_results:
            failed_steps = [sr for sr in step_results if not sr["passed"]]
            if failed_steps:
                logger.info(f"Found {len(failed_steps)} failed steps")
                return False
        
        # Check assertion results
        if assertion_results:
            failed_assertions = [ar for ar in assertion_results if not ar["passed"]]
            if failed_assertions:
                logger.info(f"Found {len(failed_assertions)} failed assertions")
                return False
        
        # If we have step or assertion results, and none failed, it's a success
        if step_results or assertion_results:
            logger.info("All steps and assertions passed")
            return True
        
        # Fallback: look for general success indicators (expanded for browser-use)
        success_indicators = [
            "Successfully completed",
            "All steps completed",
            "Task completed successfully",
            "All assertions passed",
            "Scenario completed",
            "actions were completed successfully",
            "✅ Task completed successfully",
            "ready to close browser",
            "All steps executed successfully",
            "STEP_RESULT: PASSED"
        ]

        for indicator in success_indicators:
            if re.search(indicator, content, re.IGNORECASE):
                logger.info(f"Found success indicator: {indicator}")
                return True

        # Check for browser-use specific success patterns
        browser_success_patterns = [
            r'all assertions passed.*successfully',
            r'task completed successfully',
            r'scenario completed.*ready to close',
            r'✅.*task completed successfully',
            r'\d+\.\s+.*completed.*successfully'
        ]

        for pattern in browser_success_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                logger.info(f"Found browser-use success pattern: {pattern}")
                return True

        # If no clear indicators, be conservative and return False for workflow creation
        logger.info("No clear success/failure indicators found - defaulting to failed for workflow creation")
        return False
    
    def _extract_failure_details(self, content: str) -> Optional[str]:
        """Extract detailed failure information for debugging"""
        failure_details = []
        
        # Look for "Failure Details:" sections
        failure_section_pattern = r'Failure Details?:(.*?)(?=\n\n|\n[A-Z]|$)'
        matches = re.finditer(failure_section_pattern, content, re.IGNORECASE | re.DOTALL)
        
        for match in matches:
            failure_details.append(match.group(1).strip())
        
        # Look for specific error messages
        error_patterns = [
            r'Authentication Error: (.+)',
            r'Assertion failed at step \d+: (.+)',
            r'Login attempt failed: (.+)',
            r'not found.*Available options include (.+)'
        ]
        
        for pattern in error_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                failure_details.append(match.group(1).strip())
        
        return "; ".join(failure_details) if failure_details else None
