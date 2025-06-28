"""
LLM Provider Factory for Workflow Use

This module provides a factory for creating different LLM providers
with proper configuration and error handling.
"""

import os
import logging
from typing import Optional, Tuple

from langchain_core.language_models.chat_models import BaseChatModel

from workflow_use.config.llm_config import LLMConfig

logger = logging.getLogger(__name__)


class LLMProviderError(Exception):
    """Exception raised when LLM provider initialization fails."""
    pass


def create_llm_from_config(config: LLMConfig) -> BaseChatModel:
    """
    Create an LLM instance from configuration.
    
    Args:
        config: LLM configuration object
        
    Returns:
        BaseChatModel instance
        
    Raises:
        LLMProviderError: If provider initialization fails
    """
    try:
        config.validate()
    except ValueError as e:
        raise LLMProviderError(f"Configuration validation failed: {e}")
    
    try:
        if config.provider == 'openai':
            return _create_openai_llm(config)
        elif config.provider == 'bedrock':
            return _create_bedrock_llm(config)
        elif config.provider == 'anthropic':
            return _create_anthropic_llm(config)
        elif config.provider == 'google':
            return _create_google_llm(config)
        else:
            raise LLMProviderError(f"Unsupported provider: {config.provider}")
    except Exception as e:
        raise LLMProviderError(f"Failed to initialize {config.provider} provider: {e}")


def _create_openai_llm(config: LLMConfig) -> BaseChatModel:
    """Create OpenAI LLM instance."""
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        raise LLMProviderError("langchain-openai is required for OpenAI provider. Install with: pip install langchain-openai")
    
    kwargs = config.get_openai_kwargs()
    logger.info(f"Initializing OpenAI LLM with model: {kwargs['model']}")
    return ChatOpenAI(**kwargs)


def _create_bedrock_llm(config: LLMConfig) -> BaseChatModel:
    """Create AWS Bedrock LLM instance."""
    try:
        from langchain_aws import ChatBedrock
        import boto3
    except ImportError:
        raise LLMProviderError("langchain-aws and boto3 are required for Bedrock provider. Install with: pip install langchain-aws boto3")
    
    # Verify AWS profile exists
    try:
        session = boto3.Session(profile_name=config.aws_profile, region_name=config.aws_region)
        # Test credentials by getting caller identity
        sts = session.client('sts')
        sts.get_caller_identity()
    except Exception as e:
        raise LLMProviderError(f"AWS profile '{config.aws_profile}' is not configured or accessible: {e}")
    
    kwargs = config.get_bedrock_kwargs()
    logger.info(f"Initializing Bedrock LLM with model: {kwargs['model_id']} using profile: {config.aws_profile}")
    return ChatBedrock(**kwargs)


def _create_anthropic_llm(config: LLMConfig) -> BaseChatModel:
    """Create Anthropic LLM instance."""
    try:
        from langchain_anthropic import ChatAnthropic
    except ImportError:
        raise LLMProviderError("langchain-anthropic is required for Anthropic provider. Install with: pip install langchain-anthropic")
    
    kwargs = config.get_anthropic_kwargs()
    logger.info(f"Initializing Anthropic LLM with model: {kwargs['model']}")
    return ChatAnthropic(**kwargs)


def _create_google_llm(config: LLMConfig) -> BaseChatModel:
    """Create Google LLM instance."""
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError:
        raise LLMProviderError("langchain-google-genai is required for Google provider. Install with: pip install langchain-google-genai")
    
    kwargs = config.get_google_kwargs()
    logger.info(f"Initializing Google LLM with model: {kwargs['model']}")
    return ChatGoogleGenerativeAI(**kwargs)


def create_llm_with_fallback(
    primary_config: Optional[LLMConfig] = None,
    interactive: bool = False
) -> Tuple[Optional[BaseChatModel], Optional[BaseChatModel]]:
    """
    Create LLM instances with fallback and interactive configuration.
    
    Args:
        primary_config: Primary LLM configuration. If None, loads from environment.
        interactive: Whether to prompt user for missing configuration
        
    Returns:
        Tuple of (main_llm, page_extraction_llm)
    """
    if primary_config is None:
        from workflow_use.config.llm_config import get_default_config
        primary_config = get_default_config()
    
    main_llm = None
    page_extraction_llm = None
    
    try:
        # Try to create main LLM
        main_llm = create_llm_from_config(primary_config)
        logger.info(f"Successfully initialized {primary_config.provider} LLM")
        
        # Create page extraction LLM (use smaller model if available)
        page_config = primary_config
        if primary_config.provider == 'openai':
            page_config = LLMConfig(
                provider=primary_config.provider,
                model='gpt-4o-mini',
                temperature=primary_config.temperature,
                openai_api_key=primary_config.openai_api_key
            )
        
        page_extraction_llm = create_llm_from_config(page_config)
        
    except LLMProviderError as e:
        logger.error(f"LLM initialization failed: {e}")

        if interactive:
            main_llm, page_extraction_llm = _interactive_llm_setup(str(e))
        else:
            # In non-interactive mode, just log the error and return None
            logger.warning(f"LLM initialization failed in non-interactive mode: {e}")
            return None, None
    
    return main_llm, page_extraction_llm


def _interactive_llm_setup(error_msg: str) -> Tuple[Optional[BaseChatModel], Optional[BaseChatModel]]:
    """Interactive LLM setup when automatic initialization fails."""
    import typer
    
    typer.secho(f'Error initializing LLM: {error_msg}', fg=typer.colors.RED)
    
    # Ask user what they want to do
    typer.echo("\nAvailable options:")
    typer.echo("1. Set OpenAI API key")
    typer.echo("2. Configure AWS Bedrock")
    typer.echo("3. Skip LLM initialization")
    
    choice = typer.prompt("Choose an option (1-3)", type=int)
    
    if choice == 1:
        return _setup_openai_interactive()
    elif choice == 2:
        return _setup_bedrock_interactive()
    else:
        typer.secho("Skipping LLM initialization. Some features may not work.", fg=typer.colors.YELLOW)
        return None, None


def _setup_openai_interactive() -> Tuple[Optional[BaseChatModel], Optional[BaseChatModel]]:
    """Interactive OpenAI setup."""
    import typer
    
    api_key = typer.prompt("Enter your OpenAI API key", hide_input=True)
    os.environ['OPENAI_API_KEY'] = api_key
    
    config = LLMConfig(
        provider='openai',
        model='gpt-4o',
        openai_api_key=api_key
    )
    
    try:
        main_llm = create_llm_from_config(config)
        
        page_config = LLMConfig(
            provider='openai',
            model='gpt-4o-mini',
            openai_api_key=api_key
        )
        page_extraction_llm = create_llm_from_config(page_config)
        
        typer.secho("OpenAI LLM initialized successfully!", fg=typer.colors.GREEN)
        return main_llm, page_extraction_llm
    except LLMProviderError as e:
        typer.secho(f"Failed to initialize OpenAI LLM: {e}", fg=typer.colors.RED)
        return None, None


def _setup_bedrock_interactive() -> Tuple[Optional[BaseChatModel], Optional[BaseChatModel]]:
    """Interactive Bedrock setup."""
    import typer
    
    aws_profile = typer.prompt("Enter your AWS profile name", default="default")
    model_id = typer.prompt(
        "Enter Bedrock model ID", 
        default="anthropic.claude-3-5-sonnet-20241022-v2:0"
    )
    
    config = LLMConfig(
        provider='bedrock',
        aws_profile=aws_profile,
        bedrock_model_id=model_id,
        model=model_id
    )
    
    try:
        main_llm = create_llm_from_config(config)
        page_extraction_llm = main_llm  # Use same model for page extraction
        
        typer.secho("Bedrock LLM initialized successfully!", fg=typer.colors.GREEN)
        return main_llm, page_extraction_llm
    except LLMProviderError as e:
        typer.secho(f"Failed to initialize Bedrock LLM: {e}", fg=typer.colors.RED)
        return None, None
