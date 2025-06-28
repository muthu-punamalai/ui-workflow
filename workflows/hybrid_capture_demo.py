#!/usr/bin/env python3
"""
Demo: Hybrid approach - Browser-use execution + Playwright validation
"""

import asyncio
import json
from browser_use import Agent, Browser
from playwright.async_api import async_playwright

async def demo_hybrid_capture():
    """Combine browser-use execution with Playwright element validation"""
    
    print("🚀 Starting hybrid capture approach...")
    
    # Step 1: Run browser-use to get the workflow execution
    browser_use_steps = await capture_with_browser_use()
    
    # Step 2: Validate and enrich with Playwright
    enriched_steps = await enrich_with_playwright(browser_use_steps)
    
    # Step 3: Create production-ready workflow.json
    production_workflow = {
        "workflow_analysis": "Hybrid capture: browser-use execution + Playwright validation",
        "name": "google_search_hybrid",
        "description": "Production-ready workflow with validated element data",
        "version": "1.0.0",
        "steps": enriched_steps,
        "input_schema": [],
        "metadata": {
            "capture_method": "hybrid-browser-use-playwright",
            "validation": "playwright-element-inspector",
            "reliability": "high",
            "timestamp": "2025-06-28T23:30:00Z"
        }
    }
    
    # Save the production workflow
    with open('hybrid_google_search.workflow.json', 'w') as f:
        json.dump(production_workflow, f, indent=2)
    
    print(f"✅ Created production-ready workflow with {len(enriched_steps)} validated steps")
    print("📄 Saved to: hybrid_google_search.workflow.json")
    
    return production_workflow

async def capture_with_browser_use():
    """Step 1: Use browser-use to execute and capture basic workflow"""
    print("🔄 Step 1: Capturing workflow with browser-use...")
    
    # Simulate browser-use execution results
    # In real implementation, this would come from actual browser-use execution
    basic_steps = [
        {
            "type": "navigation",
            "url": "https://www.google.com",
            "description": "Navigate to Google homepage"
        },
        {
            "type": "input",
            "target_description": "search box",
            "value": "browser automation",
            "description": "Enter search term"
        },
        {
            "type": "click", 
            "target_description": "search button",
            "description": "Click search button"
        }
    ]
    
    print(f"✅ Captured {len(basic_steps)} basic steps from browser-use")
    return basic_steps

async def enrich_with_playwright(basic_steps):
    """Step 2: Use Playwright to validate and enrich element data"""
    print("🔄 Step 2: Enriching with Playwright element validation...")
    
    enriched_steps = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            for i, step in enumerate(basic_steps):
                print(f"  Enriching step {i+1}: {step['type']}")
                
                if step['type'] == 'navigation':
                    # Navigation steps don't need enrichment
                    enriched_steps.append(step)
                    await page.goto(step['url'])
                    
                elif step['type'] == 'input':
                    # Find and validate the input element
                    if 'search box' in step.get('target_description', ''):
                        try:
                            # Try multiple selectors for Google search box
                            selectors = [
                                "textarea[name='q']",
                                "input[name='q']", 
                                "[aria-label*='Search']",
                                "#APjFqb"
                            ]
                            
                            element_data = None
                            working_selector = None
                            
                            for selector in selectors:
                                try:
                                    element = await page.wait_for_selector(selector, timeout=2000)
                                    if element:
                                        working_selector = selector
                                        element_data = await page.evaluate(f"""
                                            () => {{
                                                const el = document.querySelector('{selector}');
                                                if (!el) return null;
                                                return {{
                                                    tagName: el.tagName.toLowerCase(),
                                                    id: el.id,
                                                    name: el.name,
                                                    className: el.className,
                                                    ariaLabel: el.getAttribute('aria-label'),
                                                    type: el.type,
                                                    xpath: getXPath(el),
                                                    attributes: Array.from(el.attributes).reduce((acc, attr) => {{
                                                        acc[attr.name] = attr.value;
                                                        return acc;
                                                    }}, {{}})
                                                }};
                                                
                                                function getXPath(element) {{
                                                    if (element.id) return `//*[@id="${{element.id}}"]`;
                                                    const parts = [];
                                                    while (element && element.nodeType === 1) {{
                                                        let index = 1;
                                                        let sibling = element.previousSibling;
                                                        while (sibling) {{
                                                            if (sibling.nodeType === 1 && sibling.nodeName === element.nodeName) index++;
                                                            sibling = sibling.previousSibling;
                                                        }}
                                                        parts.unshift(`${{element.nodeName.toLowerCase()}}[${{index}}]`);
                                                        element = element.parentNode;
                                                    }}
                                                    return '/' + parts.join('/');
                                                }}
                                            }}
                                        """)
                                        break
                                except:
                                    continue
                            
                            if element_data and working_selector:
                                enriched_step = {
                                    "type": "input",
                                    "cssSelector": working_selector,
                                    "xpath": element_data['xpath'],
                                    "value": step['value'],
                                    "elementTag": element_data['tagName'],
                                    "elementAttributes": element_data['attributes'],
                                    "fallbackSelectors": selectors,
                                    "waitConditions": {
                                        "timeout": 5000,
                                        "waitFor": "visible"
                                    },
                                    "description": step['description']
                                }
                                enriched_steps.append(enriched_step)
                                print(f"    ✅ Validated input element: {working_selector}")
                            else:
                                print(f"    ❌ Could not validate input element")
                                
                        except Exception as e:
                            print(f"    ❌ Error validating input: {e}")
                
                elif step['type'] == 'click':
                    # Find and validate the click element
                    if 'search button' in step.get('target_description', ''):
                        try:
                            selectors = [
                                "input[name='btnK']",
                                "button[aria-label*='Search']",
                                "[value='Google Search']"
                            ]
                            
                            element_data = None
                            working_selector = None
                            
                            for selector in selectors:
                                try:
                                    element = await page.wait_for_selector(selector, timeout=2000)
                                    if element:
                                        working_selector = selector
                                        element_data = await page.evaluate(f"""
                                            () => {{
                                                const el = document.querySelector('{selector}');
                                                if (!el) return null;
                                                return {{
                                                    tagName: el.tagName.toLowerCase(),
                                                    id: el.id,
                                                    name: el.name,
                                                    className: el.className,
                                                    value: el.value,
                                                    ariaLabel: el.getAttribute('aria-label'),
                                                    type: el.type,
                                                    attributes: Array.from(el.attributes).reduce((acc, attr) => {{
                                                        acc[attr.name] = attr.value;
                                                        return acc;
                                                    }}, {{}})
                                                }};
                                            }}
                                        """)
                                        break
                                except:
                                    continue
                            
                            if element_data and working_selector:
                                enriched_step = {
                                    "type": "click",
                                    "cssSelector": working_selector,
                                    "xpath": f"//input[@name='{element_data['name']}' and @type='{element_data['type']}']",
                                    "elementTag": element_data['tagName'],
                                    "elementAttributes": element_data['attributes'],
                                    "fallbackSelectors": selectors,
                                    "waitConditions": {
                                        "timeout": 5000,
                                        "waitFor": "visible"
                                    },
                                    "description": step['description']
                                }
                                enriched_steps.append(enriched_step)
                                print(f"    ✅ Validated click element: {working_selector}")
                            else:
                                print(f"    ❌ Could not validate click element")
                                
                        except Exception as e:
                            print(f"    ❌ Error validating click: {e}")
        
        finally:
            await browser.close()
    
    print(f"✅ Enriched {len(enriched_steps)} steps with Playwright validation")
    return enriched_steps

if __name__ == "__main__":
    asyncio.run(demo_hybrid_capture())
