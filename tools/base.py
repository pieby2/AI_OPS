"""
Base Tool Interface - Abstract class for all tools
"""
from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseTool(ABC):
    """Abstract base class for all tools"""
    
    # Override in subclasses to enable caching
    cache_ttl: int = 300  # Default TTL: 5 minutes
    enable_cache: bool = True  # Enable caching by default
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name identifier"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description for LLM to understand when to use it"""
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> Dict[str, str]:
        """Expected parameters with descriptions"""
        pass
    
    @abstractmethod
    def _execute_impl(self, **kwargs) -> Dict[str, Any]:
        """
        Internal implementation of tool execution
        Subclasses should implement this instead of execute()
        
        Returns:
            dict: Tool execution result with 'success', 'data', and optional 'error'
        """
        pass
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the tool with caching support
        
        Returns:
            dict: Tool execution result with 'success', 'data', and optional 'error'
        """
        if not self.enable_cache:
            return self._execute_impl(**kwargs)
        
        # Import here to avoid circular imports
        from cache import get_cache_manager
        
        cache = get_cache_manager()
        cache_key = cache._generate_key(self.name, kwargs)
        
        # Check cache first
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            if isinstance(cached_result, dict):
                cached_result = cached_result.copy()
                cached_result["_from_cache"] = True
            return cached_result
        
        # Execute and cache result
        result = self._execute_impl(**kwargs)
        
        # Only cache successful results
        if isinstance(result, dict) and result.get("success", False):
            cache.set(cache_key, result, self.cache_ttl)
        
        return result
    
    def get_schema(self) -> Dict[str, Any]:
        """Get tool schema for LLM planning"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }

