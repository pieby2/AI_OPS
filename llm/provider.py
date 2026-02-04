"""
LLM Provider - Wrapper for Groq API with structured outputs
"""
import os
import json
from typing import Dict, Any, Optional
from groq import Groq
from metrics import get_metrics_tracker


class LLMProvider:
    """Wrapper for LLM API calls with structured JSON output support"""
    
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        
        self.client = Groq(api_key=self.api_key)
        self.model = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))
        self.metrics = get_metrics_tracker()
    
    def chat_completion(
        self, 
        messages: list[Dict[str, str]], 
        temperature: Optional[float] = None,
        json_mode: bool = False
    ) -> str:
        """
        Send chat completion request to LLM
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Override default temperature
            json_mode: Force JSON output format
            
        Returns:
            str: LLM response content
        """
        try:
            params = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature if temperature is not None else self.temperature,
            }
            
            if json_mode:
                params["response_format"] = {"type": "json_object"}
            
            response = self.client.chat.completions.create(**params)
            
            # Track token usage and cost
            usage = response.usage
            if usage:
                self.metrics.record_llm_call(
                    model=self.model,
                    tokens_in=usage.prompt_tokens,
                    tokens_out=usage.completion_tokens
                )
            
            return response.choices[0].message.content
            
        except Exception as e:
            raise Exception(f"LLM API error: {str(e)}")
    
    def get_structured_output(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        """
        Get structured JSON output from LLM
        
        Args:
            system_prompt: System instructions
            user_prompt: User request
            temperature: Lower temperature for more consistent outputs
            
        Returns:
            dict: Parsed JSON response
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = self.chat_completion(messages, temperature=temperature, json_mode=True)
        
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse LLM JSON response: {str(e)}\nResponse: {response}")


# Singleton instance
_llm_instance = None

def get_llm_provider() -> LLMProvider:
    """Get or create LLM provider singleton"""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = LLMProvider()
    return _llm_instance
