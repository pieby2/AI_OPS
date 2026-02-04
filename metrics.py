"""
Metrics Tracker - Track LLM token usage and estimate costs
"""
import threading
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class LLMCallMetrics:
    """Metrics for a single LLM call"""
    model: str
    tokens_in: int
    tokens_out: int
    timestamp: datetime = field(default_factory=datetime.now)
    cost: float = 0.0


# Pricing per 1K tokens (as of 2024)
MODEL_PRICING = {
    # OpenAI models
    "gpt-4-turbo-preview": {"input": 0.01, "output": 0.03},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4-32k": {"input": 0.06, "output": 0.12},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    "gpt-3.5-turbo-16k": {"input": 0.003, "output": 0.004},
    # Groq models (free tier, but tracking for reference)
    "llama-3.3-70b-versatile": {"input": 0.00059, "output": 0.00079},
    "llama-3.1-70b-versatile": {"input": 0.00059, "output": 0.00079},
    "llama-3.1-8b-instant": {"input": 0.00005, "output": 0.00008},
    "mixtral-8x7b-32768": {"input": 0.00024, "output": 0.00024},
    "gemma2-9b-it": {"input": 0.0002, "output": 0.0002},
    # Default fallback
    "default": {"input": 0.01, "output": 0.03}
}


class MetricsTracker:
    """Thread-safe metrics tracker for LLM usage and costs"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._calls = []
                    cls._instance._calls_lock = threading.RLock()
                    cls._instance._request_metrics = None
        return cls._instance
    
    def start_request(self) -> None:
        """Start tracking a new request"""
        with self._calls_lock:
            self._request_metrics = {
                "calls": [],
                "start_time": datetime.now()
            }
    
    def record_llm_call(
        self, 
        model: str, 
        tokens_in: int, 
        tokens_out: int
    ) -> LLMCallMetrics:
        """
        Record an LLM API call
        
        Args:
            model: Model name (e.g., 'gpt-4-turbo-preview')
            tokens_in: Number of input tokens (prompt)
            tokens_out: Number of output tokens (completion)
            
        Returns:
            LLMCallMetrics with calculated cost
        """
        cost = self._calculate_cost(model, tokens_in, tokens_out)
        
        metrics = LLMCallMetrics(
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost=cost
        )
        
        with self._calls_lock:
            self._calls.append(metrics)
            if self._request_metrics is not None:
                self._request_metrics["calls"].append(metrics)
        
        return metrics
    
    def _calculate_cost(self, model: str, tokens_in: int, tokens_out: int) -> float:
        """Calculate cost based on model pricing"""
        pricing = MODEL_PRICING.get(model, MODEL_PRICING["default"])
        
        input_cost = (tokens_in / 1000) * pricing["input"]
        output_cost = (tokens_out / 1000) * pricing["output"]
        
        return round(input_cost + output_cost, 6)
    
    def get_request_metrics(self) -> Dict[str, Any]:
        """
        Get metrics for the current request
        
        Returns:
            dict with tokens used and estimated cost
        """
        with self._calls_lock:
            if self._request_metrics is None:
                return {
                    "total_tokens_in": 0,
                    "total_tokens_out": 0,
                    "total_tokens": 0,
                    "estimated_cost_usd": 0.0,
                    "llm_calls": 0
                }
            
            calls = self._request_metrics["calls"]
            
            total_in = sum(c.tokens_in for c in calls)
            total_out = sum(c.tokens_out for c in calls)
            total_cost = sum(c.cost for c in calls)
            
            return {
                "total_tokens_in": total_in,
                "total_tokens_out": total_out,
                "total_tokens": total_in + total_out,
                "estimated_cost_usd": round(total_cost, 6),
                "llm_calls": len(calls)
            }
    
    def end_request(self) -> Dict[str, Any]:
        """End request tracking and return final metrics"""
        metrics = self.get_request_metrics()
        with self._calls_lock:
            self._request_metrics = None
        return metrics
    
    def get_total_metrics(self) -> Dict[str, Any]:
        """Get cumulative metrics across all requests"""
        with self._calls_lock:
            if not self._calls:
                return {
                    "total_tokens_in": 0,
                    "total_tokens_out": 0,
                    "total_tokens": 0,
                    "total_cost_usd": 0.0,
                    "total_calls": 0
                }
            
            total_in = sum(c.tokens_in for c in self._calls)
            total_out = sum(c.tokens_out for c in self._calls)
            total_cost = sum(c.cost for c in self._calls)
            
            return {
                "total_tokens_in": total_in,
                "total_tokens_out": total_out,
                "total_tokens": total_in + total_out,
                "total_cost_usd": round(total_cost, 6),
                "total_calls": len(self._calls)
            }
    
    def reset(self) -> None:
        """Reset all metrics"""
        with self._calls_lock:
            self._calls.clear()
            self._request_metrics = None


# Module-level metrics instance
_metrics_tracker = None


def get_metrics_tracker() -> MetricsTracker:
    """Get or create the metrics tracker singleton"""
    global _metrics_tracker
    if _metrics_tracker is None:
        _metrics_tracker = MetricsTracker()
    return _metrics_tracker
