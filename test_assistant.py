#!/usr/bin/env python3
"""
Test Script for AI Operations Assistant
Tests the multi-agent system with various scenarios
"""
import requests
import json
import time
from typing import Dict, Any


BASE_URL = "http://localhost:8000"


def print_section(title: str):
    """Print formatted section header"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def test_health_check():
    """Test the health endpoint"""
    print_section("Health Check")
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False


def execute_task(task: str) -> Dict[str, Any]:
    """Execute a task and print results"""
    print_section(f"Task: {task}")
    
    try:
        start_time = time.time()
        
        response = requests.post(
            f"{BASE_URL}/task",
            json={"task": task},
            timeout=60
        )
        
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            
            print("✅ Task completed successfully!")
            print(f"\n📋 Plan:")
            print(f"  Steps: {len(result['plan']['steps'])}")
            print(f"  Tools: {', '.join(result['plan']['tools_needed'])}")
            
            print(f"\n⚙️  Execution:")
            for exec_result in result['execution_results']:
                status = "✓" if exec_result.get('success') else "✗"
                print(f"  {status} Step {exec_result['step_number']}: {exec_result['description']}")
            
            print(f"\n💬 Final Answer:")
            print(f"  {result['final_answer'][:500]}...")
            
            print(f"\n⏱️  Execution time: {elapsed:.2f}s")
            
            return result
        else:
            print(f"❌ Task failed with status {response.status_code}")
            print(f"Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error executing task: {e}")
        return None


def run_test_suite():
    """Run comprehensive test suite"""
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║     AI Operations Assistant - Test Suite                ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    # Test 1: Health check
    if not test_health_check():
        print("\n⚠️  Server is not healthy. Please check configuration.")
        return
    
    # Test 2: Simple weather query
    execute_task("What is the weather in Tokyo?")
    time.sleep(2)
    
    # Test 3: GitHub repository search
    execute_task("Find the top 3 most popular machine learning repositories on GitHub")
    time.sleep(2)
    
    # Test 4: Combined query
    execute_task("Get the weather in San Francisco and find popular Python web frameworks on GitHub")
    time.sleep(2)
    
    # Test 5: Multiple cities weather
    execute_task("What's the weather like in London, Paris, and New York?")
    time.sleep(2)
    
    # Test 6: Specific GitHub query
    execute_task("Search for TypeScript frameworks on GitHub sorted by stars, show me the top 5")
    
    print_section("Test Suite Completed")
    print("✅ All tests executed. Review results above.")


def interactive_mode():
    """Interactive mode for manual testing"""
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║     AI Operations Assistant - Interactive Mode          ║
    ╚══════════════════════════════════════════════════════════╝
    
    Enter tasks to execute them. Type 'quit' to exit.
    """)
    
    while True:
        try:
            task = input("\n🤖 Task: ").strip()
            
            if not task:
                continue
            
            if task.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            execute_task(task)
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        interactive_mode()
    else:
        run_test_suite()
