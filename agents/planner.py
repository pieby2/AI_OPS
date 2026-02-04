"""
Planner Agent - Decomposes tasks into executable steps
"""
from typing import Dict, Any, List
from llm import get_llm_provider
from tools import get_tool_registry


class PlannerAgent:
    """Agent responsible for converting natural language tasks into structured plans"""
    
    def __init__(self):
        self.llm = get_llm_provider()
        self.tool_registry = get_tool_registry()
    
    def create_plan(self, task: str) -> Dict[str, Any]:
        """
        Create a step-by-step execution plan for the given task
        
        Args:
            task: Natural language task description
            
        Returns:
            dict: Plan with steps and required tools
        """
        tools_schema = self.tool_registry.get_tools_schema()
        
        system_prompt = self._build_system_prompt(tools_schema)
        user_prompt = f"Task: {task}\n\nCreate a detailed execution plan for this task."
        
        try:
            plan = self.llm.get_structured_output(system_prompt, user_prompt, temperature=0.3)
            
            # Validate plan structure
            if not self._validate_plan(plan):
                raise ValueError("Invalid plan structure returned by LLM")
            
            return plan
            
        except Exception as e:
            raise Exception(f"Failed to create plan: {str(e)}")
    
    def _build_system_prompt(self, tools_schema: List[Dict]) -> str:
        """Build system prompt with available tools"""
        tools_desc = "\n".join([
            f"- {tool['name']}: {tool['description']}\n  Parameters: {tool['parameters']}"
            for tool in tools_schema
        ])
        
        return f"""You are a task planning agent. Your job is to break down user tasks into executable steps.

Available Tools:
{tools_desc}

You must respond with a JSON object in this exact format:
{{
  "steps": [
    {{
      "step_number": 1,
      "description": "Clear description of what this step does",
      "tool": "tool_name or null if no tool needed",
      "parameters": {{"param1": "value1"}} or null
    }}
  ],
  "tools_needed": ["list", "of", "tool", "names"],
  "expected_outcome": "What the final result should contain"
}}

Rules:
1. Break complex tasks into simple, sequential steps
2. Only use available tools listed above
3. Each step should have a clear purpose
4. Parameters must match the tool's expected parameters
5. If a task requires information from a previous step, make that dependency clear
6. If no tools are needed (e.g., simple information requests), create steps anyway with tool=null
7. Be specific about what information to extract from API responses

Examples:

Task: "What's the weather in London?"
{{
  "steps": [
    {{
      "step_number": 1,
      "description": "Get current weather for London",
      "tool": "get_weather",
      "parameters": {{"city": "London", "units": "metric"}}
    }}
  ],
  "tools_needed": ["get_weather"],
  "expected_outcome": "Current weather conditions in London including temperature, humidity, and conditions"
}}

Task: "Find popular Python web frameworks on GitHub"
{{
  "steps": [
    {{
      "step_number": 1,
      "description": "Search GitHub for Python web framework repositories",
      "tool": "github_search",
      "parameters": {{"query": "python web framework", "sort": "stars", "limit": 5}}
    }}
  ],
  "tools_needed": ["github_search"],
  "expected_outcome": "List of top Python web frameworks with stars and descriptions"
}}

Task: "Get weather in Paris and find AI repositories"
{{
  "steps": [
    {{
      "step_number": 1,
      "description": "Get current weather for Paris",
      "tool": "get_weather",
      "parameters": {{"city": "Paris", "units": "metric"}}
    }},
    {{
      "step_number": 2,
      "description": "Search for popular AI repositories on GitHub",
      "tool": "github_search",
      "parameters": {{"query": "artificial intelligence", "sort": "stars", "limit": 5}}
    }}
  ],
  "tools_needed": ["get_weather", "github_search"],
  "expected_outcome": "Weather information for Paris and list of popular AI repositories"
}}

Now create a plan for the user's task."""
    
    def _validate_plan(self, plan: Dict[str, Any]) -> bool:
        """Validate that the plan has the required structure"""
        required_keys = ["steps", "tools_needed", "expected_outcome"]
        
        if not all(key in plan for key in required_keys):
            return False
        
        if not isinstance(plan["steps"], list) or len(plan["steps"]) == 0:
            return False
        
        for step in plan["steps"]:
            if not all(key in step for key in ["step_number", "description", "tool", "parameters"]):
                return False
        
        return True
