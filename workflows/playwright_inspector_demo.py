#!/usr/bin/env python3
"""
Demo: Use Playwright's element inspector to capture rich element data
"""

import asyncio
import json
from playwright.async_api import async_playwright

async def demo_playwright_inspector():
    """Use Playwright to inspect and capture element details"""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        try:
            print("🔄 Navigating to Google...")
            await page.goto("https://www.google.com")
            
            # Wait for search box and inspect it
            search_box = await page.wait_for_selector("textarea[name='q']")
            
            # Extract comprehensive element data
            search_box_data = await page.evaluate("""
                (element) => {
                    const rect = element.getBoundingClientRect();
                    const computedStyle = window.getComputedStyle(element);
                    
                    return {
                        tagName: element.tagName.toLowerCase(),
                        id: element.id,
                        className: element.className,
                        name: element.name,
                        type: element.type,
                        placeholder: element.placeholder,
                        ariaLabel: element.getAttribute('aria-label'),
                        role: element.getAttribute('role'),
                        xpath: getXPath(element),
                        cssSelector: getCSSSelector(element),
                        attributes: Array.from(element.attributes).reduce((acc, attr) => {
                            acc[attr.name] = attr.value;
                            return acc;
                        }, {}),
                        position: {
                            x: rect.x,
                            y: rect.y,
                            width: rect.width,
                            height: rect.height
                        },
                        styles: {
                            display: computedStyle.display,
                            visibility: computedStyle.visibility,
                            opacity: computedStyle.opacity
                        }
                    };
                    
                    function getXPath(element) {
                        if (element.id) {
                            return `//*[@id="${element.id}"]`;
                        }
                        
                        const parts = [];
                        while (element && element.nodeType === Node.ELEMENT_NODE) {
                            let nbOfPreviousSiblings = 0;
                            let hasNextSiblings = false;
                            let sibling = element.previousSibling;
                            while (sibling) {
                                if (sibling.nodeType === Node.ELEMENT_NODE && sibling.nodeName === element.nodeName) {
                                    nbOfPreviousSiblings++;
                                }
                                sibling = sibling.previousSibling;
                            }
                            sibling = element.nextSibling;
                            while (sibling) {
                                if (sibling.nodeType === Node.ELEMENT_NODE && sibling.nodeName === element.nodeName) {
                                    hasNextSiblings = true;
                                    break;
                                }
                                sibling = sibling.nextSibling;
                            }
                            const prefix = element.nodeName.toLowerCase();
                            const nth = nbOfPreviousSiblings || hasNextSiblings ? `[${nbOfPreviousSiblings + 1}]` : '';
                            parts.push(prefix + nth);
                            element = element.parentNode;
                        }
                        return parts.length ? '/' + parts.reverse().join('/') : '';
                    }
                    
                    function getCSSSelector(element) {
                        if (element.id) {
                            return `#${element.id}`;
                        }
                        
                        const path = [];
                        while (element && element.nodeType === Node.ELEMENT_NODE) {
                            let selector = element.nodeName.toLowerCase();
                            if (element.className) {
                                selector += '.' + element.className.split(' ').join('.');
                            }
                            if (element.name) {
                                selector += `[name="${element.name}"]`;
                            }
                            path.unshift(selector);
                            element = element.parentNode;
                        }
                        return path.join(' > ');
                    }
                }
            """, search_box)
            
            print("🔍 Search box element data:")
            print(json.dumps(search_box_data, indent=2))
            
            # Type in search box
            await search_box.fill("browser automation")
            
            # Find and inspect search button
            search_button = await page.wait_for_selector("input[name='btnK']")
            
            search_button_data = await page.evaluate("""
                (element) => {
                    const rect = element.getBoundingClientRect();
                    return {
                        tagName: element.tagName.toLowerCase(),
                        id: element.id,
                        className: element.className,
                        name: element.name,
                        type: element.type,
                        value: element.value,
                        ariaLabel: element.getAttribute('aria-label'),
                        attributes: Array.from(element.attributes).reduce((acc, attr) => {
                            acc[attr.name] = attr.value;
                            return acc;
                        }, {}),
                        position: {
                            x: rect.x,
                            y: rect.y,
                            width: rect.width,
                            height: rect.height
                        }
                    };
                }
            """, search_button)
            
            print("\n🔍 Search button element data:")
            print(json.dumps(search_button_data, indent=2))
            
            # Create rich workflow from inspected elements
            rich_workflow = {
                "workflow_analysis": "Created using Playwright element inspector",
                "name": "google_search_playwright",
                "description": "Rich workflow with comprehensive element data",
                "version": "1.0.0",
                "steps": [
                    {
                        "type": "navigation",
                        "url": "https://www.google.com"
                    },
                    {
                        "type": "input",
                        "cssSelector": f"#{search_box_data['id']}" if search_box_data['id'] else f"textarea[name='{search_box_data['name']}']",
                        "xpath": search_box_data['xpath'],
                        "value": "browser automation",
                        "elementTag": search_box_data['tagName'],
                        "elementAttributes": search_box_data['attributes'],
                        "position": search_box_data['position'],
                        "waitConditions": {
                            "timeout": 5000,
                            "waitFor": "visible"
                        }
                    },
                    {
                        "type": "click",
                        "cssSelector": f"input[name='{search_button_data['name']}'][type='{search_button_data['type']}']",
                        "xpath": f"//input[@name='{search_button_data['name']}' and @type='{search_button_data['type']}']",
                        "elementTag": search_button_data['tagName'],
                        "elementAttributes": search_button_data['attributes'],
                        "position": search_button_data['position'],
                        "waitConditions": {
                            "timeout": 5000,
                            "waitFor": "visible"
                        }
                    }
                ],
                "input_schema": [],
                "metadata": {
                    "capture_method": "playwright-inspector",
                    "browser": "chromium",
                    "viewport": "1280x720",
                    "timestamp": "2025-06-28T23:30:00Z"
                }
            }
            
            # Save the rich workflow
            with open('playwright_google_search.workflow.json', 'w') as f:
                json.dump(rich_workflow, f, indent=2)
            
            print(f"\n✅ Created rich workflow with Playwright inspector")
            print("📄 Saved to: playwright_google_search.workflow.json")
            
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(demo_playwright_inspector())
