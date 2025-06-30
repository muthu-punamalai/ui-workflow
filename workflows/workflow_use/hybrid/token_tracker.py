"""
Custom Token Tracking for Hybrid Testing Framework
Tracks LLM token usage and costs across both browser-use and workflow-use flows
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class TokenUsage:
    """Track token usage for a single LLM call"""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class ModelUsage:
    """Track cumulative usage for a specific model"""
    model_name: str = ""
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    call_count: int = 0

class TokenTracker:
    """Simple token tracking implementation for the hybrid testing framework"""
    
    def __init__(self):
        self.model_usage: Dict[str, ModelUsage] = {}
        self.session_start = datetime.now()
        
        # Token costs per 1K tokens (approximate AWS Bedrock pricing)
        self.token_costs = {
            "anthropic.claude-3-5-sonnet-20241022-v2:0": {
                "input": 0.003,   # $3 per 1M input tokens
                "output": 0.015   # $15 per 1M output tokens
            },
            "anthropic.claude-3-haiku-20240307-v1:0": {
                "input": 0.00025, # $0.25 per 1M input tokens
                "output": 0.00125 # $1.25 per 1M output tokens
            },
            "gpt-4": {
                "input": 0.03,    # $30 per 1M input tokens
                "output": 0.06    # $60 per 1M output tokens
            },
            "gpt-3.5-turbo": {
                "input": 0.0015,  # $1.50 per 1M input tokens
                "output": 0.002   # $2 per 1M output tokens
            }
        }
    
    def track_llm_call(self, model_name: str, input_tokens: int, output_tokens: int) -> TokenUsage:
        """Track a single LLM call"""
        total_tokens = input_tokens + output_tokens
        
        # Calculate cost
        cost = self._calculate_cost(model_name, input_tokens, output_tokens)
        
        # Create usage record
        usage = TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost=cost
        )
        
        # Update model usage
        if model_name not in self.model_usage:
            self.model_usage[model_name] = ModelUsage(model_name=model_name)
        
        model = self.model_usage[model_name]
        model.total_input_tokens += input_tokens
        model.total_output_tokens += output_tokens
        model.total_tokens += total_tokens
        model.total_cost += cost
        model.call_count += 1
        
        logger.debug(f"Tracked LLM call: {model_name} - {total_tokens} tokens, ${cost:.4f}")
        
        return usage
    
    def _calculate_cost(self, model_name: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for token usage"""
        if model_name not in self.token_costs:
            # Default pricing if model not found
            logger.warning(f"Unknown model for pricing: {model_name}, using default rates")
            input_cost = input_tokens * 0.003 / 1000  # $3 per 1M tokens
            output_cost = output_tokens * 0.015 / 1000  # $15 per 1M tokens
        else:
            rates = self.token_costs[model_name]
            input_cost = input_tokens * rates["input"] / 1000
            output_cost = output_tokens * rates["output"] / 1000
        
        return input_cost + output_cost
    
    def get_usage_summary(self) -> Dict[str, Any]:
        """Get comprehensive usage summary"""
        summary = {
            "session_start": self.session_start.isoformat(),
            "total_cost_usd": self.get_total_cost(),
            "total_tokens": self.get_total_tokens(),
            "total_input_tokens": sum(m.total_input_tokens for m in self.model_usage.values()),
            "total_output_tokens": sum(m.total_output_tokens for m in self.model_usage.values()),
            "model_breakdown": {},
            "call_count": sum(m.call_count for m in self.model_usage.values())
        }
        
        # Add per-model breakdown
        for model_name, usage in self.model_usage.items():
            summary["model_breakdown"][model_name] = {
                "input_tokens": usage.total_input_tokens,
                "output_tokens": usage.total_output_tokens,
                "total_tokens": usage.total_tokens,
                "cost": usage.total_cost,
                "call_count": usage.call_count
            }
        
        return summary
    
    def get_total_cost(self) -> float:
        """Get total cost across all models"""
        return sum(usage.total_cost for usage in self.model_usage.values())
    
    def get_total_tokens(self) -> int:
        """Get total tokens across all models"""
        return sum(usage.total_tokens for usage in self.model_usage.values())
    
    def reset(self):
        """Reset all tracking data"""
        self.model_usage.clear()
        self.session_start = datetime.now()
        logger.info("Token tracking reset")

# Global token tracker instance
_global_tracker = TokenTracker()

def get_token_tracker() -> TokenTracker:
    """Get the global token tracker instance"""
    return _global_tracker

def track_llm_call(model_name: str, input_tokens: int, output_tokens: int) -> TokenUsage:
    """Convenience function to track an LLM call"""
    return _global_tracker.track_llm_call(model_name, input_tokens, output_tokens)

def get_usage_summary() -> Dict[str, Any]:
    """Convenience function to get usage summary"""
    return _global_tracker.get_usage_summary()
