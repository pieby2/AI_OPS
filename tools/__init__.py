"""
Tools module - Provides access to all available tools
"""
from typing import Dict
from .base import BaseTool
from .github_tool import GitHubTool
from .weather_tool import WeatherTool
from .news_tool import NewsTool


class ToolRegistry:
    """Registry for managing available tools"""
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._initialize_tools()
    
    def _initialize_tools(self):
        """Initialize and register all available tools"""
        try:
            github_tool = GitHubTool()
            self._tools[github_tool.name] = github_tool
        except Exception as e:
            print(f"Warning: Could not initialize GitHubTool: {e}")
        
        try:
            weather_tool = WeatherTool()
            self._tools[weather_tool.name] = weather_tool
        except Exception as e:
            print(f"Warning: Could not initialize WeatherTool: {e}")
        
        try:
            news_tool = NewsTool()
            self._tools[news_tool.name] = news_tool
        except Exception as e:
            print(f"Warning: Could not initialize NewsTool: {e}")
    
    def get_tool(self, name: str) -> BaseTool:
        """Get a tool by name"""
        if name not in self._tools:
            raise ValueError(f"Tool '{name}' not found. Available tools: {list(self._tools.keys())}")
        return self._tools[name]
    
    def get_all_tools(self) -> Dict[str, BaseTool]:
        """Get all registered tools"""
        return self._tools
    
    def get_tools_schema(self) -> list:
        """Get schema for all tools for LLM planning"""
        return [tool.get_schema() for tool in self._tools.values()]


# Singleton instance
_registry_instance = None

def get_tool_registry() -> ToolRegistry:
    """Get or create tool registry singleton"""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ToolRegistry()
    return _registry_instance


__all__ = ['BaseTool', 'GitHubTool', 'WeatherTool', 'NewsTool', 'ToolRegistry', 'get_tool_registry']

