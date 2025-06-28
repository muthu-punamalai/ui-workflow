#!/usr/bin/env python3
"""
Demo: Enhanced workflow capture with real element data
"""

import asyncio
import json
from browser_use import Agent, Browser
from browser_use.agent.views import AgentHistoryList

async def demo_enhanced_capture():
    """Demonstrate how to capture rich element data from browser-use"""
    
    # Create a simple browser-use agent
    browser = Browser()
    agent = Agent(
        task="Go to Google and search for 'browser automation'",
        browser=browser
    )
    
    try:
        # Run the agent to capture real element interactions
        print("🔄 Running browser-use agent to capture element data...")
        result = await agent.run()
        
        # Access the agent history with rich element data
        history: AgentHistoryList = agent.history
        
        print(f"✅ Agent completed. History has {len(history)} steps")
        
        # Extract rich workflow data
        workflow_steps = []
        
        # Method 1: Access action_results (contains detailed element info)
        action_results = history.action_results()
        print(f"📊 Found {len(action_results)} action results")
        
        for i, action_result in enumerate(action_results):
            print(f"\n🔍 Action Result {i+1}:")
            print(f"  Type: {type(action_result)}")
            
            # Extract the action details
            if hasattr(action_result, 'action'):
                action = action_result.action
                print(f"  Action: {action}")
                
                # Extract element details if available
                if hasattr(action_result, 'interacted_element') and action_result.interacted_element:
                    element = action_result.interacted_element
                    print(f"  Element tag: {getattr(element, 'tag_name', 'unknown')}")
                    print(f"  Element xpath: {getattr(element, 'xpath', 'none')}")
                    print(f"  Element css: {getattr(element, 'css_selector', 'none')}")
                    
                    if hasattr(element, 'attributes'):
                        attrs = element.attributes or {}
                        print(f"  Element attributes: {attrs}")
                        
                        # Create rich workflow step
                        if 'input' in str(action).lower():
                            step = {
                                "type": "input",
                                "cssSelector": build_css_selector(element, attrs),
                                "xpath": getattr(element, 'xpath', None),
                                "value": extract_input_value(action),
                                "elementTag": getattr(element, 'tag_name', 'input'),
                                "elementAttributes": attrs
                            }
                            workflow_steps.append(step)
                            
                        elif 'click' in str(action).lower():
                            step = {
                                "type": "click", 
                                "cssSelector": build_css_selector(element, attrs),
                                "xpath": getattr(element, 'xpath', None),
                                "elementTag": getattr(element, 'tag_name', 'button'),
                                "elementAttributes": attrs
                            }
                            workflow_steps.append(step)
        
        # Method 2: Access model_outputs (contains action details)
        model_outputs = history.model_outputs()
        print(f"\n📊 Found {len(model_outputs)} model outputs")
        
        for i, output in enumerate(model_outputs):
            print(f"\n🔍 Model Output {i+1}: {type(output)}")
            if hasattr(output, 'action'):
                print(f"  Action: {output.action}")
            if hasattr(output, 'interacted_element'):
                print(f"  Has interacted element: {output.interacted_element is not None}")
        
        # Create the rich workflow.json
        rich_workflow = {
            "workflow_analysis": "Enhanced capture with real browser-use element data",
            "name": "google_search_enhanced",
            "description": "Auto-generated workflow with rich element details",
            "version": "1.0.0",
            "steps": workflow_steps,
            "input_schema": [],
            "metadata": {
                "capture_method": "browser-use-enhanced",
                "total_actions": len(action_results),
                "total_outputs": len(model_outputs),
                "browser": "chromium",
                "success": True
            }
        }
        
        # Save the enhanced workflow
        with open('enhanced_google_search.workflow.json', 'w') as f:
            json.dump(rich_workflow, f, indent=2)
        
        print(f"\n✅ Created enhanced workflow with {len(workflow_steps)} rich steps")
        print("📄 Saved to: enhanced_google_search.workflow.json")
        
        return rich_workflow
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await browser.close()

def build_css_selector(element, attrs):
    """Build a robust CSS selector from element data"""
    # Priority: ID > Name > Class > Type
    if attrs.get('id'):
        return f"#{attrs['id']}"
    elif attrs.get('name'):
        tag = getattr(element, 'tag_name', 'input')
        return f"{tag}[name='{attrs['name']}']"
    elif attrs.get('class'):
        classes = attrs['class'].split()
        return f".{'.'.join(classes[:2])}"  # Use first 2 classes
    else:
        return getattr(element, 'tag_name', 'div')

def extract_input_value(action):
    """Extract input value from action"""
    action_str = str(action)
    if 'text' in action_str:
        # Try to extract text value
        import re
        match = re.search(r"text['\"]?\s*:\s*['\"]([^'\"]+)['\"]", action_str)
        if match:
            return match.group(1)
    return ""

if __name__ == "__main__":
    asyncio.run(demo_enhanced_capture())
