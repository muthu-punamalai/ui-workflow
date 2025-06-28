#!/usr/bin/env python3
"""
Test timing comparison between browser-use and workflow-use
"""

import asyncio
import time
from pathlib import Path
from workflow_use.hybrid.test_runner import HybridTestRunner
from workflow_use.llm.providers import create_llm_with_fallback
from workflow_use.config.llm_config import get_default_config

async def test_timing_comparison(test_file_path=None):
    """Compare execution times between browser-use and workflow-use"""

    config = get_default_config()
    llm, page_extraction_llm = create_llm_with_fallback(config, interactive=False)
    runner = HybridTestRunner(llm, page_extraction_llm)

    # Use provided test file or default to pay_supplements
    if test_file_path is None:
        test_file = "testcases/pay_supplements.txt"
    else:
        test_file = test_file_path

    # Generate workflow file path from test file
    test_path = Path(test_file)
    workflow_file = test_path.with_suffix('.workflow.json')

    print("🚀 Testing execution timing comparison...")
    print(f"📄 Test file: {test_file}")
    print(f"📄 Workflow file exists: {workflow_file.exists()}")
    
    if workflow_file.exists():
        print("\n🔄 Running with existing workflow.json (should use workflow-use)...")
        start_time = time.time()
        
        result = await runner.run_test(test_file)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        print(f"\n📊 Results:")
        print(f"  Success: {result.get('success')}")
        print(f"  Method: {result.get('execution_method')}")
        print(f"  Total time: {total_time:.2f} seconds")
        print(f"  Reported time: {result.get('execution_time_seconds', 'N/A')} seconds")
        
        # Show step-by-step timing if available
        step_results = result.get('step_results', [])
        if step_results:
            print(f"\n🔍 Step-by-step timing:")
            total_step_time = 0
            for step in step_results:
                step_time = step.get('duration_seconds', 0)
                total_step_time += step_time
                method = step.get('method', 'unknown')
                print(f"    Step {step.get('step_index', 0) + 1}: {step_time:.2f}s ({method})")
            print(f"  Total step time: {total_step_time:.2f}s")
        
        # Show fallback analysis
        fallback_steps = result.get('fallback_steps', [])
        if fallback_steps:
            print(f"\n⚠️  Fallback analysis:")
            print(f"  Steps using browser-use fallback: {len(fallback_steps)}")
            print(f"  Steps using pure workflow-use: {len(step_results) - len(fallback_steps)}")
        else:
            print(f"\n✅ All steps used pure workflow-use execution!")
            
    else:
        print("\n❌ No workflow.json file found. Run the test once to create it:")
        print(f"   uv run python cli.py run-test {test_file}")

if __name__ == "__main__":
    import sys

    # Check if test file is provided as command line argument
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
        print(f"📝 Using test file from command line: {test_file}")
        asyncio.run(test_timing_comparison(test_file))
    else:
        print("📝 No test file specified, using default: testcases/pay_supplements.txt")
        print("💡 Usage: python test_timing.py <test_file_path>")
        print("💡 Example: python test_timing.py testcases/google_search.txt")
        asyncio.run(test_timing_comparison())
