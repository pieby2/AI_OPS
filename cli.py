#!/usr/bin/env python3
"""
AI Operations Assistant - Command Line Interface
Direct agent invocation without HTTP server
"""
import sys
import time
import argparse
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from agents import PlannerAgent, ExecutorAgent, VerifierAgent
from metrics import get_metrics_tracker
from cache import get_cache_manager


# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'


def print_header():
    """Print CLI header"""
    print(f"""
{Colors.CYAN}{Colors.BOLD}╔══════════════════════════════════════════════════════════════╗
║             AI Operations Assistant - CLI v2.0               ║
╚══════════════════════════════════════════════════════════════╝{Colors.ENDC}
    """)


def print_step(step_num: int, description: str, status: str = "running"):
    """Print step execution status"""
    if status == "running":
        icon = f"{Colors.YELLOW}⋯{Colors.ENDC}"
    elif status == "success":
        icon = f"{Colors.GREEN}✓{Colors.ENDC}"
    else:
        icon = f"{Colors.RED}✗{Colors.ENDC}"
    
    print(f"  {icon} Step {step_num}: {description}")


def print_section(title: str):
    """Print section header"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}▶ {title}{Colors.ENDC}")


def execute_task(task: str, show_details: bool = True) -> dict:
    """Execute a task using the multi-agent system"""
    start_time = time.time()
    
    # Initialize metrics tracking
    metrics = get_metrics_tracker()
    metrics.start_request()
    
    try:
        # Initialize agents
        print_section("Initializing Agents")
        planner = PlannerAgent()
        executor = ExecutorAgent()
        verifier = VerifierAgent()
        print(f"  {Colors.GREEN}✓{Colors.ENDC} Agents ready")
        
        # Step 1: Create plan
        print_section("Creating Execution Plan")
        plan = planner.create_plan(task)
        print(f"  {Colors.DIM}Steps: {len(plan['steps'])}{Colors.ENDC}")
        print(f"  {Colors.DIM}Tools: {', '.join(plan['tools_needed'])}{Colors.ENDC}")
        
        # Step 2: Execute plan
        print_section("Executing Steps")
        execution_results = []
        
        for step in plan.get("steps", []):
            step_num = step.get("step_number")
            desc = step.get("description", "")
            
            # Execute step
            result = executor._execute_step(step)
            execution_results.append(result)
            
            status = "success" if result.get("success") else "failed"
            print_step(step_num, desc, status)
            
            if show_details and result.get("success"):
                data = result.get("data", {})
                if isinstance(data, dict):
                    # Show brief data preview
                    if "_from_cache" in data:
                        print(f"      {Colors.DIM}(cached){Colors.ENDC}")
        
        # Step 3: Verify and format results
        print_section("Verifying & Formatting Results")
        final_answer = verifier.verify_and_format(task, plan, execution_results)
        
        execution_time = time.time() - start_time
        request_metrics = metrics.end_request()
        
        # Print final answer
        print(f"\n{Colors.CYAN}{'─'*60}{Colors.ENDC}")
        print(f"{Colors.BOLD}📋 Answer:{Colors.ENDC}\n")
        print(final_answer)
        print(f"\n{Colors.CYAN}{'─'*60}{Colors.ENDC}")
        
        # Print metrics
        print(f"\n{Colors.DIM}⏱  Time: {execution_time:.2f}s | "
              f"🔢 Tokens: {request_metrics['total_tokens']} | "
              f"💰 Cost: ${request_metrics['estimated_cost_usd']:.4f}{Colors.ENDC}\n")
        
        return {
            "success": True,
            "answer": final_answer,
            "metrics": request_metrics,
            "execution_time": execution_time
        }
        
    except Exception as e:
        metrics.end_request()
        print(f"\n{Colors.RED}❌ Error: {str(e)}{Colors.ENDC}\n")
        return {
            "success": False,
            "error": str(e)
        }


def interactive_mode():
    """Run in interactive mode"""
    print_header()
    print(f"{Colors.DIM}Enter tasks to execute. Type 'quit' or 'exit' to stop.{Colors.ENDC}")
    print(f"{Colors.DIM}Commands: /clear (clear cache), /stats (show stats), /help{Colors.ENDC}\n")
    
    while True:
        try:
            task = input(f"{Colors.BOLD}🤖 Task:{Colors.ENDC} ").strip()
            
            if not task:
                continue
            
            # Handle special commands
            if task.lower() in ['quit', 'exit', 'q']:
                print(f"\n{Colors.CYAN}👋 Goodbye!{Colors.ENDC}\n")
                break
            
            if task == '/clear':
                cache = get_cache_manager()
                count = cache.clear()
                print(f"{Colors.GREEN}✓ Cleared {count} cached entries{Colors.ENDC}\n")
                continue
            
            if task == '/stats':
                metrics = get_metrics_tracker()
                stats = metrics.get_total_metrics()
                cache = get_cache_manager()
                cache_stats = cache.get_stats()
                
                print(f"\n{Colors.BOLD}📊 Session Statistics:{Colors.ENDC}")
                print(f"  LLM Calls: {stats['total_calls']}")
                print(f"  Total Tokens: {stats['total_tokens']}")
                print(f"  Total Cost: ${stats['total_cost_usd']:.4f}")
                print(f"  Cache Entries: {cache_stats['active_entries']}\n")
                continue
            
            if task == '/help':
                print(f"\n{Colors.BOLD}Available Commands:{Colors.ENDC}")
                print("  /clear  - Clear the response cache")
                print("  /stats  - Show session statistics")
                print("  /help   - Show this help message")
                print("  quit    - Exit the CLI\n")
                continue
            
            # Execute the task
            print()  # Add spacing
            execute_task(task)
            
        except KeyboardInterrupt:
            print(f"\n\n{Colors.CYAN}👋 Goodbye!{Colors.ENDC}\n")
            break
        except EOFError:
            break


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="AI Operations Assistant - CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py "What's the weather in Tokyo?"
  python cli.py "Find popular Python repos on GitHub"
  python cli.py --interactive
  python cli.py -i
        """
    )
    
    parser.add_argument(
        "task",
        nargs="?",
        help="Task to execute (omit for interactive mode)"
    )
    
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Run in interactive mode"
    )
    
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Minimal output (only show final answer)"
    )
    
    args = parser.parse_args()
    
    # Determine mode
    if args.interactive or args.task is None:
        interactive_mode()
    else:
        print_header()
        print(f"{Colors.BOLD}Task:{Colors.ENDC} {args.task}\n")
        execute_task(args.task, show_details=not args.quiet)


if __name__ == "__main__":
    main()
