#!/usr/bin/env python3
"""
Debug script to understand browser-use AgentHistoryList structure
"""

import asyncio
import json
from browser_use import Agent, Browser
from browser_use.agent.views import AgentHistoryList

async def debug_browser_use_data():
    """Debug what data browser-use actually captures"""
    
    browser = Browser()
    agent = Agent(
        task="Go to https://www.google.com and search for 'test'",
        browser=browser
    )
    
    try:
        print("🔄 Running browser-use agent to capture data...")
        result = await agent.run()
        
        # Get the agent history
        history: AgentHistoryList = agent.history
        print(f"✅ Agent completed. History type: {type(history)}")
        print(f"📊 History length: {len(history)}")
        
        # Debug all available methods and attributes
        print(f"\n🔍 AgentHistoryList attributes:")
        for attr in dir(history):
            if not attr.startswith('_'):
                print(f"  - {attr}")
        
        # Check model_outputs method
        try:
            model_outputs = history.model_outputs()
            print(f"\n📊 model_outputs() returned {len(model_outputs)} items")
            
            for i, output in enumerate(model_outputs):
                print(f"\n🔍 Model Output {i+1}:")
                print(f"  Type: {type(output)}")
                print(f"  Attributes: {[attr for attr in dir(output) if not attr.startswith('_')]}")
                
                # Check if it has action and interacted_element
                if hasattr(output, 'action'):
                    print(f"  Action: {output.action}")
                    print(f"  Action type: {type(output.action)}")
                
                if hasattr(output, 'interacted_element'):
                    element = output.interacted_element
                    print(f"  Interacted Element: {element}")
                    print(f"  Element type: {type(element)}")
                    
                    if element:
                        print(f"  Element attributes: {[attr for attr in dir(element) if not attr.startswith('_')]}")
                        
                        # Check specific element properties
                        if hasattr(element, 'tag_name'):
                            print(f"    tag_name: {element.tag_name}")
                        if hasattr(element, 'xpath'):
                            print(f"    xpath: {element.xpath}")
                        if hasattr(element, 'css_selector'):
                            print(f"    css_selector: {element.css_selector}")
                        if hasattr(element, 'attributes'):
                            print(f"    attributes: {element.attributes}")
                
                # Print raw string representation
                print(f"  Raw string: {str(output)[:200]}...")
        
        except Exception as e:
            print(f"❌ Error accessing model_outputs(): {e}")
        
        # Check action_results method
        try:
            action_results = history.action_results()
            print(f"\n📊 action_results() returned {len(action_results)} items")
            
            for i, result in enumerate(action_results):
                print(f"\n🔍 Action Result {i+1}:")
                print(f"  Type: {type(result)}")
                print(f"  Attributes: {[attr for attr in dir(result) if not attr.startswith('_')]}")
                
                # Check extracted_content
                if hasattr(result, 'extracted_content'):
                    content = result.extracted_content
                    print(f"  Extracted content: {content[:100] if content else 'None'}...")
                
                # Check if it has action info
                if hasattr(result, 'action'):
                    print(f"  Action: {result.action}")
                
                # Print raw string
                print(f"  Raw string: {str(result)[:200]}...")
        
        except Exception as e:
            print(f"❌ Error accessing action_results(): {e}")
        
        # Try to access the raw history data
        try:
            print(f"\n🔍 Raw history data:")
            print(f"  History.__dict__.keys(): {list(history.__dict__.keys()) if hasattr(history, '__dict__') else 'No __dict__'}")
            
            # Try to access internal data
            if hasattr(history, 'history'):
                print(f"  history.history: {type(history.history)}")
            if hasattr(history, '_history'):
                print(f"  history._history: {type(history._history)}")
            if hasattr(history, 'data'):
                print(f"  history.data: {type(history.data)}")
        
        except Exception as e:
            print(f"❌ Error accessing raw history: {e}")
        
        print(f"\n✅ Debug complete. Check output above for element data structure.")
        
    except Exception as e:
        print(f"❌ Error running browser-use: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_browser_use_data())
