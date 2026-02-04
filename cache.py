"""
Cache Manager - In-memory caching with TTL support for API responses
"""
import time
import hashlib
import json
import threading
from typing import Any, Optional, Dict
from functools import wraps


class CacheManager:
    """Thread-safe in-memory cache with TTL support"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._cache: Dict[str, Dict[str, Any]] = {}
                    cls._instance._cache_lock = threading.RLock()
        return cls._instance
    
    def _generate_key(self, tool_name: str, params: Dict[str, Any]) -> str:
        """Generate a unique cache key from tool name and parameters"""
        params_str = json.dumps(params, sort_keys=True)
        key_str = f"{tool_name}:{params_str}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache if exists and not expired
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        with self._cache_lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            if time.time() > entry["expires_at"]:
                # Entry has expired, remove it
                del self._cache[key]
                return None
            
            return entry["value"]
    
    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """
        Store value in cache with TTL
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (default: 5 minutes)
        """
        with self._cache_lock:
            self._cache[key] = {
                "value": value,
                "expires_at": time.time() + ttl,
                "created_at": time.time()
            }
    
    def invalidate(self, key: str) -> bool:
        """
        Remove a specific key from cache
        
        Args:
            key: Cache key to remove
            
        Returns:
            True if key was found and removed, False otherwise
        """
        with self._cache_lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self) -> int:
        """
        Clear all cached entries
        
        Returns:
            Number of entries cleared
        """
        with self._cache_lock:
            count = len(self._cache)
            self._cache.clear()
            return count
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired entries
        
        Returns:
            Number of entries removed
        """
        with self._cache_lock:
            now = time.time()
            expired_keys = [
                key for key, entry in self._cache.items()
                if now > entry["expires_at"]
            ]
            for key in expired_keys:
                del self._cache[key]
            return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._cache_lock:
            now = time.time()
            total = len(self._cache)
            expired = sum(1 for entry in self._cache.values() if now > entry["expires_at"])
            return {
                "total_entries": total,
                "active_entries": total - expired,
                "expired_entries": expired
            }


# Module-level cache instance
_cache_manager = None


def get_cache_manager() -> CacheManager:
    """Get or create the cache manager singleton"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


def cached(ttl: int = 300):
    """
    Decorator for caching tool execution results
    
    Args:
        ttl: Time-to-live in seconds (default: 5 minutes)
        
    Usage:
        @cached(ttl=600)
        def execute(self, **kwargs):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, **kwargs):
            cache = get_cache_manager()
            
            # Generate cache key from tool name and parameters
            tool_name = getattr(self, 'name', func.__name__)
            cache_key = cache._generate_key(tool_name, kwargs)
            
            # Check cache first
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                # Mark result as from cache for debugging
                if isinstance(cached_result, dict):
                    cached_result["_from_cache"] = True
                return cached_result
            
            # Execute and cache result
            result = func(self, **kwargs)
            
            # Only cache successful results
            if isinstance(result, dict) and result.get("success", False):
                cache.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator
