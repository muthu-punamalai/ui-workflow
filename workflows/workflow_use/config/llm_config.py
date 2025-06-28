"""
LLM Configuration Management for Workflow Use

This module provides configuration management for different LLM providers
including OpenAI, AWS Bedrock, and others.
"""

import os
from dataclasses import dataclass
from typing import Optional, Dict, Any
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional


@dataclass
class LLMConfig:
    """Configuration for LLM providers."""

    # Provider selection
    provider: str = "bedrock"  # Options: "openai", "bedrock", "anthropic", "google"

    # Model settings
    model: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"  # Default model
    temperature: float = 0.1  # Model creativity (0.0-1.0)
    max_tokens: Optional[int] = None  # Max response tokens
    
    # OpenAI specific
    openai_api_key: Optional[str] = None
    
    # AWS Bedrock specific
    aws_profile: Optional[str] = None
    aws_region: str = "us-west-2"
    bedrock_model_id: Optional[str] = None
    
    # Anthropic specific
    anthropic_api_key: Optional[str] = None
    
    # Google specific
    google_api_key: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> 'LLMConfig':
        """Create configuration from environment variables."""
        # Default to bedrock provider
        provider = os.getenv('AI_PROVIDER', os.getenv('LLM_PROVIDER', 'bedrock')).lower()

        # Support both AI_MODEL and LLM_MODEL for compatibility with smart-test
        model = os.getenv('AI_MODEL', os.getenv('LLM_MODEL'))

        # Support both AI_TEMPERATURE and LLM_TEMPERATURE
        temperature = float(os.getenv('AI_TEMPERATURE', os.getenv('LLM_TEMPERATURE', '0.1')))

        # Support both AI_MAX_TOKENS and LLM_MAX_TOKENS
        max_tokens_env = os.getenv('AI_MAX_TOKENS', os.getenv('LLM_MAX_TOKENS'))
        max_tokens = int(max_tokens_env) if max_tokens_env else None

        config = cls(
            provider=provider,
            model=model or 'anthropic.claude-3-5-sonnet-20241022-v2:0',
            temperature=temperature,
            max_tokens=max_tokens,

            # OpenAI
            openai_api_key=os.getenv('OPENAI_API_KEY'),

            # AWS Bedrock
            aws_profile=os.getenv('AWS_PROFILE', 'default'),
            aws_region=os.getenv('AWS_REGION', 'us-west-2'),
            bedrock_model_id=os.getenv('AI_MODEL', os.getenv('BEDROCK_MODEL_ID')),

            # Anthropic
            anthropic_api_key=os.getenv('ANTHROPIC_API_KEY'),

            # Google
            google_api_key=os.getenv('GOOGLE_API_KEY', os.getenv('GEMINI_API_KEY')),
        )

        # Set default models and configurations based on provider
        if provider == 'bedrock':
            if not config.bedrock_model_id:
                config.bedrock_model_id = 'anthropic.claude-3-5-sonnet-20241022-v2:0'
            config.model = config.bedrock_model_id
        elif provider == 'anthropic':
            if not model:
                config.model = 'claude-3-5-sonnet-20241022'
        elif provider == 'google' or provider == 'gemini':
            if not model:
                config.model = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash-exp')
        elif provider == 'openai':
            if not model:
                config.model = 'gpt-4o'

        return config
    
    def validate(self) -> None:
        """Validate configuration based on provider."""
        if self.provider == 'openai':
            if not self.openai_api_key:
                raise ValueError("OPENAI_API_KEY is required for OpenAI provider")
        elif self.provider == 'bedrock':
            if not self.aws_profile:
                raise ValueError("AWS_PROFILE is required for Bedrock provider")
            if not self.bedrock_model_id:
                raise ValueError("BEDROCK_MODEL_ID is required for Bedrock provider")
        elif self.provider == 'anthropic':
            if not self.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY is required for Anthropic provider")
        elif self.provider == 'google':
            if not self.google_api_key:
                raise ValueError("GOOGLE_API_KEY is required for Google provider")
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    def get_bedrock_kwargs(self) -> Dict[str, Any]:
        """Get kwargs for AWS Bedrock initialization."""
        return {
            'model_id': self.bedrock_model_id,
            'region_name': self.aws_region,
            'credentials_profile_name': self.aws_profile,
            'model_kwargs': {
                'temperature': self.temperature,
                'max_tokens': self.max_tokens or 4096,
            }
        }
    
    def get_openai_kwargs(self) -> Dict[str, Any]:
        """Get kwargs for OpenAI initialization."""
        kwargs = {
            'model': self.model,
            'temperature': self.temperature,
            'api_key': self.openai_api_key,
        }
        if self.max_tokens:
            kwargs['max_tokens'] = self.max_tokens
        return kwargs
    
    def get_anthropic_kwargs(self) -> Dict[str, Any]:
        """Get kwargs for Anthropic initialization."""
        kwargs = {
            'model': self.model,
            'temperature': self.temperature,
            'api_key': self.anthropic_api_key,
        }
        if self.max_tokens:
            kwargs['max_tokens'] = self.max_tokens
        return kwargs
    
    def get_google_kwargs(self) -> Dict[str, Any]:
        """Get kwargs for Google initialization."""
        kwargs = {
            'model': self.model,
            'temperature': self.temperature,
            'api_key': self.google_api_key,
        }
        if self.max_tokens:
            kwargs['max_tokens'] = self.max_tokens
        return kwargs


def get_default_config() -> LLMConfig:
    """Get default LLM configuration from environment."""
    return LLMConfig.from_env()
