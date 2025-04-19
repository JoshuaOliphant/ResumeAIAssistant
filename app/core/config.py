import os
import secrets
from typing import Optional, Dict, Any, List, Union

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables
    """
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
    
    # CORS Configuration
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Claude API
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    # Using the latest Claude model with the -latest alias
    CLAUDE_MODEL: str = "claude-3-7-sonnet-latest"
    
    # OpenAI API
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    # Default to GPT-4.1 for strong reasoning capabilities
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4.1")
    # Use GPT-4.1 for evaluator and optimizer tasks too for consistent performance
    OPENAI_EVALUATOR_MODEL: str = os.getenv("OPENAI_EVALUATOR_MODEL", "gpt-4.1")
    OPENAI_OPTIMIZER_MODEL: str = os.getenv("OPENAI_OPTIMIZER_MODEL", "gpt-4.1")
    
    # Google Gemini API
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    
    # PydanticAI Configuration
    # Default provider based on available API keys
    PYDANTICAI_PRIMARY_PROVIDER: str = os.getenv("PYDANTICAI_PRIMARY_PROVIDER", "anthropic")
    # Default model setting - using Claude 3.7 Sonnet model by default with -latest alias
    PYDANTICAI_PRIMARY_MODEL: str = os.getenv(
        "PYDANTICAI_PRIMARY_MODEL", 
        "claude-3-7-sonnet-latest"
    )
    # Model for evaluation tasks - using Claude 3.7 Sonnet with extended thinking capability
    PYDANTICAI_EVALUATOR_MODEL: str = os.getenv(
        "PYDANTICAI_EVALUATOR_MODEL", 
        "anthropic:claude-3-7-sonnet-latest"
    )
    # Model for optimization tasks - also using Claude 3.7 Sonnet with extended thinking capability
    PYDANTICAI_OPTIMIZER_MODEL: str = os.getenv(
        "PYDANTICAI_OPTIMIZER_MODEL", 
        "anthropic:claude-3-7-sonnet-latest"
    )
    # Model for cover letter generation - using Claude 3.7 Sonnet for best quality
    PYDANTICAI_COVER_LETTER_MODEL: str = os.getenv(
        "PYDANTICAI_COVER_LETTER_MODEL",
        "anthropic:claude-3-7-sonnet-latest"  # Using latest Claude 3.7 Sonnet for cover letters
    )
    # Fallback models listed in order of preference
    PYDANTICAI_FALLBACK_MODELS: List[str] = [
        # Primary fallbacks - newer models with strong capabilities
        "anthropic:claude-3-7-sonnet-latest",       # Always use latest Claude 3.7 Sonnet
        "openai:gpt-4.1",                           # Latest GPT-4.1 model
        "google:gemini-2.5-pro-preview-03-25",      # Latest Gemini 2.5 Pro (Mar 2025)
        
        # Secondary fallbacks - more cost-effective models
        "openai:gpt-4o",                            # Older but still capable model
        "google:gemini-2.5-flash-preview-04-17",    # Latest Gemini 2.5 Flash (Apr 2025)
        "anthropic:claude-3-7-haiku-latest"         # Always use latest Claude 3.7 Haiku
    ]
    # Token budget for models with thinking capability
    PYDANTICAI_THINKING_BUDGET: int = os.getenv("PYDANTICAI_THINKING_BUDGET", 15000)
    # Temperature setting for agent outputs (0.0-1.0)
    PYDANTICAI_TEMPERATURE: float = os.getenv("PYDANTICAI_TEMPERATURE", 0.7)
    # Maximum tokens for responses
    PYDANTICAI_MAX_TOKENS: int = os.getenv("PYDANTICAI_MAX_TOKENS", 8000)
    
    # Database - SQLite only
    DATABASE_URL: str = "sqlite:///./resume_app.db"
    
    # File size limits
    MAX_UPLOAD_SIZE: int = 5 * 1024 * 1024  # 5MB

    class Config:
        case_sensitive = True


# Initialize settings
settings = Settings()

# Set up model provider configuration for PydanticAI
def get_pydanticai_model_config() -> Dict[str, Any]:
    """
    Get the configuration for PydanticAI model providers based on available API keys.
    
    Returns:
        Dictionary with model provider configuration for PydanticAI
    """
    config = {}
    
    # Configure Anthropic provider if API key is available
    if settings.ANTHROPIC_API_KEY:
        # Get the appropriate default model depending on provider preference
        anthropic_default = (
            settings.PYDANTICAI_PRIMARY_MODEL 
            if settings.PYDANTICAI_PRIMARY_PROVIDER == "anthropic" 
            else "claude-3-7-sonnet-20250219"
        )
        
        # Configure extended thinking capability for Claude 3.7 models
        thinking_config = None
        if "claude-3-7" in anthropic_default or "claude-3-7-sonnet-latest" in anthropic_default:
            thinking_config = {
                "type": "enabled",
                "budget_tokens": settings.PYDANTICAI_THINKING_BUDGET
            }
        
        config["anthropic"] = {
            "api_key": settings.ANTHROPIC_API_KEY,
            "default_model": anthropic_default,
            "temperature": settings.PYDANTICAI_TEMPERATURE,
            "max_tokens": settings.PYDANTICAI_MAX_TOKENS,
            "thinking_config": thinking_config
        }
    
    # Configure OpenAI provider if API key is available
    if settings.OPENAI_API_KEY:
        # Get the appropriate default model depending on provider preference
        openai_default = (
            settings.PYDANTICAI_PRIMARY_MODEL 
            if settings.PYDANTICAI_PRIMARY_PROVIDER == "openai" 
            else "gpt-4.1"
        )
        
        config["openai"] = {
            "api_key": settings.OPENAI_API_KEY,
            "default_model": openai_default,
            "temperature": settings.PYDANTICAI_TEMPERATURE,
            "max_tokens": settings.PYDANTICAI_MAX_TOKENS
        }
    
    # Configure Google Gemini provider if API key is available
    if settings.GEMINI_API_KEY:
        # Get the appropriate default model depending on provider preference
        gemini_default = (
            settings.PYDANTICAI_PRIMARY_MODEL 
            if settings.PYDANTICAI_PRIMARY_PROVIDER == "google" 
            else "gemini-2.5-pro-preview-03-25"  # Latest Gemini Pro model
        )
        
        # Configure thinking budget for Gemini models
        thinking_config = {
            "thinkingBudget": settings.PYDANTICAI_THINKING_BUDGET
        }
        
        config["gemini"] = {
            "api_key": settings.GEMINI_API_KEY,
            "default_model": gemini_default,
            "temperature": settings.PYDANTICAI_TEMPERATURE,
            "max_tokens": settings.PYDANTICAI_MAX_TOKENS,
            "thinking_config": thinking_config
        }
    
    # If no providers are configured, raise a warning
    if not config:
        import warnings
        warnings.warn(
            "No PydanticAI providers configured. Please set at least one of: "
            "ANTHROPIC_API_KEY, OPENAI_API_KEY, or GEMINI_API_KEY"
        )
    
    return config