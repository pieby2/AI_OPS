"""
Planner Agent - Decomposes tasks into executable steps
"""
from typing import Dict, Any, List
from llm import get_llm_provider
from tools import get_tool_registry
from memory import get_memory_manager


class PlannerAgent:
    """Agent responsible for converting natural language tasks into structured plans"""
    
    def __init__(self):
        self.llm = get_llm_provider()
        self.tool_registry = get_tool_registry()
        self.memory = get_memory_manager()
    
    def create_plan(self, task: str) -> Dict[str, Any]:
        """
        Create a step-by-step execution plan for the given task
        
        Args:
            task: Natural language task description
            
        Returns:
            dict: Plan with steps and required tools
        """
        tools_schema = self.tool_registry.get_tools_schema()
        
        # Get relevant context from memory
        context = self._get_memory_context(task)
        
        system_prompt = self._build_system_prompt(tools_schema)
        user_prompt = self._build_user_prompt(task, context)
        
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

IMPORTANT: Before creating a plan, you must THINK step-by-step about WHY you are choosing this approach.

You must respond with a JSON object in this exact format:
{{
  "reasoning": "Explain your chain-of-thought here: What does the user want? Which tools are best suited? Why are you ordering the steps this way? What assumptions are you making?",
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
1. ALWAYS start with "reasoning" to explain your thought process
2. Break complex tasks into simple, sequential steps
3. Only use available tools listed above
4. Each step should have a clear purpose
5. Parameters must match the tool's expected parameters
6. If a task requires information from a previous step, make that dependency clear
7. If no tools are needed (e.g., simple information requests), create steps anyway with tool=null
8. Be specific about what information to extract from API responses

Examples:

Task: "What's the weather in London?"
{{
  "reasoning": "The user wants current weather information for London. I'll use the get_weather tool with 'London' as the city. Since no units were specified, I'll default to metric (Celsius). This is a single-step task.",
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
  "reasoning": "The user wants to discover Python web frameworks. I'll search GitHub with relevant keywords and sort by stars to find the most popular ones. Limiting to 5 results provides a good overview without overwhelming.",
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
  "reasoning": "This is a multi-part task with two independent requests: 1) weather in Paris, and 2) AI repositories on GitHub. Since these are independent, they can be executed in sequence. I'll get weather first (quick API call) then search GitHub.",
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
        required_keys = ["reasoning", "steps", "tools_needed", "expected_outcome"]
        
        if not all(key in plan for key in required_keys):
            return False
        
        if not isinstance(plan["reasoning"], str) or len(plan["reasoning"]) < 10:
            return False  # Reasoning should be substantive
        
        if not isinstance(plan["steps"], list) or len(plan["steps"]) == 0:
            return False
        
        for step in plan["steps"]:
            if not all(key in step for key in ["step_number", "description", "tool", "parameters"]):
                return False
        
        return True
    
    def _get_memory_context(self, task: str) -> List[Dict[str, Any]]:
        """Get relevant past interactions for context"""
        try:
            # Get user preferences
            preferences = self.memory.get_all_preferences()
            
            # Get similar past queries
            past_queries = self.memory.get_context_for_task(task, limit=2)
            
            return {
                "preferences": preferences,
                "past_queries": past_queries
            }
        except Exception:
            return {"preferences": {}, "past_queries": []}
    
    def _build_user_prompt(self, task: str, context: Dict[str, Any]) -> str:
        """Build user prompt with task and context"""
        prompt_parts = [f"Task: {task}"]
        
        # Add user preferences if available
        if context.get("preferences"):
            prefs_str = ", ".join([f"{k}: {v}" for k, v in context["preferences"].items()])
            prompt_parts.append(f"\nUser Preferences: {prefs_str}")
        
        # Add relevant past queries for context
        if context.get("past_queries"):
            prompt_parts.append("\nRelevant past queries (for context only):")
            for i, query in enumerate(context["past_queries"][:2], 1):
                prompt_parts.append(f"  {i}. \"{query['task'][:100]}\"")
        
        prompt_parts.append("\nCreate a detailed execution plan for this task.")
        
        return "\n".join(prompt_parts)

