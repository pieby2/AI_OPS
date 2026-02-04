"""
Executor Agent - Executes planned steps and calls tools
Supports parallel execution for independent steps
"""
import asyncio
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor
from tools import get_tool_registry


class ExecutorAgent:
    """Agent responsible for executing planned steps with parallel support"""
    
    def __init__(self):
        self.tool_registry = get_tool_registry()
        self._executor = ThreadPoolExecutor(max_workers=5)
    
    def execute_plan(self, plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Execute all steps in the plan with parallel execution for independent steps
        
        Args:
            plan: Plan from PlannerAgent containing steps
            
        Returns:
            list: Results from each step execution
        """
        steps = plan.get("steps", [])
        
        if not steps:
            return []
        
        # Group steps by independence (steps that can run in parallel)
        step_groups = self._group_independent_steps(steps)
        
        results = []
        
        for group in step_groups:
            if len(group) == 1:
                # Single step, execute normally
                result = self._execute_step(group[0])
                results.append(result)
            else:
                # Multiple independent steps, execute in parallel
                group_results = self._execute_parallel(group)
                results.extend(group_results)
        
        # Sort results by step number to maintain order
        results.sort(key=lambda x: x.get("step_number", 0))
        
        return results
    
    def _group_independent_steps(self, steps: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        Group steps that can be executed in parallel
        
        Steps are considered independent if:
        - They don't reference results from other steps
        - They use different tools (to avoid rate limiting issues)
        
        Returns:
            List of step groups, where each group can be executed in parallel
        """
        groups = []
        current_group = []
        used_tools = set()
        
        for step in steps:
            tool = step.get("tool")
            description = step.get("description", "").lower()
            
            # Check if step depends on previous results
            # Simple heuristic: if description mentions "previous", "above", "result"
            depends_on_previous = any(
                keyword in description 
                for keyword in ["previous", "above", "result from", "using the"]
            )
            
            # Check if tool is already in current group (avoid rate limits)
            tool_conflict = tool in used_tools if tool else False
            
            if depends_on_previous or tool_conflict:
                # Start new group
                if current_group:
                    groups.append(current_group)
                current_group = [step]
                used_tools = {tool} if tool else set()
            else:
                # Add to current group
                current_group.append(step)
                if tool:
                    used_tools.add(tool)
        
        # Don't forget the last group
        if current_group:
            groups.append(current_group)
        
        return groups
    
    def _execute_parallel(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute multiple steps in parallel using ThreadPoolExecutor"""
        with ThreadPoolExecutor(max_workers=len(steps)) as executor:
            futures = [executor.submit(self._execute_step, step) for step in steps]
            results = [future.result() for future in futures]
        return results
    
    def _execute_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a single step
        
        Args:
            step: Step definition with tool and parameters
            
        Returns:
            dict: Step execution result
        """
        step_number = step.get("step_number")
        description = step.get("description")
        tool_name = step.get("tool")
        parameters = step.get("parameters")
        
        result = {
            "step_number": step_number,
            "description": description,
            "tool_used": tool_name
        }
        
        # If no tool is needed, just acknowledge the step
        if not tool_name or tool_name == "null":
            result["success"] = True
            result["data"] = {"message": "No tool execution needed for this step"}
            return result
        
        # Execute the tool
        try:
            tool = self.tool_registry.get_tool(tool_name)
            
            # Execute with parameters
            params = parameters if parameters else {}
            execution_result = tool.execute(**params)
            
            result["success"] = execution_result.get("success", False)
            result["data"] = execution_result.get("data")
            
            # Track if result came from cache
            if execution_result.get("_from_cache"):
                result["from_cache"] = True
            
            if not result["success"]:
                result["error"] = execution_result.get("error", "Unknown error")
            
        except ValueError as e:
            # Tool not found
            result["success"] = False
            result["error"] = str(e)
        except Exception as e:
            # Tool execution failed
            result["success"] = False
            result["error"] = f"Tool execution error: {str(e)}"
        
        return result

