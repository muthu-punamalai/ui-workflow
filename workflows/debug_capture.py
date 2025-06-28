#!/usr/bin/env python3
"""
Debug script to test workflow capture
"""

import sys
import os

# Add the workflow_use directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from workflow_use.hybrid.simple_capture import SimpleWorkflowCapture

def test_capture():
    """Test the workflow capture with mock data"""
    
    # Create a mock agent history similar to what we see in the output
    class MockAgentHistory:
        def __init__(self):
            self.all_model_outputs = [
                {
                    'go_to_url': {'url': 'https://www.google.com'}, 
                    'interacted_element': None
                },
                {
                    'input_text': {'index': 6, 'text': 'browser automation'}, 
                    'interacted_element': MockElement()
                },
                {
                    'click_element_by_index': {'index': 20}, 
                    'interacted_element': MockElement()
                }
            ]
    
    class MockElement:
        def __init__(self):
            self.tag_name = 'textarea'
            self.xpath = 'html/body/div[1]/div[3]/form/div[1]/div[1]/div[1]/div[1]/div[2]/textarea'
            self.css_selector = 'textarea.gLFyf[id="APjFqb"][name="q"]'
            self.attributes = {
                'class': 'gLFyf',
                'id': 'APjFqb',
                'name': 'q',
                'aria-label': 'Search'
            }
    
    # Test the capture
    capture = SimpleWorkflowCapture()
    mock_history = MockAgentHistory()
    
    print("Testing workflow capture...")
    workflow_def = capture.create_workflow_from_browser_use(
        mock_history,
        "test_google_search",
        success=True
    )
    
    if workflow_def:
        print(f"✅ Successfully created workflow with {len(workflow_def.steps)} steps")
        for i, step in enumerate(workflow_def.steps):
            print(f"  Step {i+1}: {step.type}")
            if hasattr(step, 'cssSelector'):
                print(f"    CSS: {step.cssSelector}")
            if hasattr(step, 'xpath'):
                print(f"    XPath: {step.xpath}")
        
        # Test saving
        saved = capture.save_workflow(workflow_def, "test_output.workflow.json")
        if saved:
            print("✅ Successfully saved workflow to test_output.workflow.json")
        else:
            print("❌ Failed to save workflow")
    else:
        print("❌ Failed to create workflow")

if __name__ == "__main__":
    test_capture()
