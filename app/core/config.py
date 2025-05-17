import os
import secrets
from typing import Any, Dict, List, Optional, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables
    """

    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))

    # CORS Configuration - explicitly allow localhost:3000 (Next.js frontend)
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",  # Next.js frontend
        "http://127.0.0.1:3000",  # Alternative localhost
        "http://localhost:5001",  # Backend itself
        "http://127.0.0.1:5001"   # Alternative for backend
    ]

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

    # Claude Code settings
    CLAUDE_CODE_CMD: str = os.getenv("CLAUDE_CODE_CMD", "claude")
    CLAUDE_CODE_WORKING_DIR: Optional[str] = os.getenv("CLAUDE_CODE_WORKING_DIR")
    CLAUDE_CODE_TIMEOUT: int = int(os.getenv("CLAUDE_CODE_TIMEOUT", "900"))  # 15 minutes
    CLAUDE_CODE_MAX_TIMEOUT: int = int(os.getenv("CLAUDE_CODE_MAX_TIMEOUT", "1800"))  # 30 minutes max
    ENABLE_FALLBACK: bool = os.getenv("ENABLE_FALLBACK", "1") == "1"
    FALLBACK_THRESHOLD: int = int(os.getenv("FALLBACK_THRESHOLD", "3"))  # Number of failures before fallback

    # PydanticAI Configuration
    # Default provider based on available API keys
    PYDANTICAI_PRIMARY_PROVIDER: str = os.getenv(
        "PYDANTICAI_PRIMARY_PROVIDER", "google"
    )
    # Default model setting - using Gemini 2.5 Pro model by default
    PYDANTICAI_PRIMARY_MODEL: str = os.getenv(
        "PYDANTICAI_PRIMARY_MODEL", "gemini-2.5-pro-preview-03-25"
    )
    # Model for evaluation tasks - using Gemini 2.5 Pro with extended thinking capability
    PYDANTICAI_EVALUATOR_MODEL: str = os.getenv(
        "PYDANTICAI_EVALUATOR_MODEL", "google:gemini-2.5-pro-preview-03-25"
    )
    # Model for optimization tasks - also using Gemini 2.5 Pro with extended thinking capability
    PYDANTICAI_OPTIMIZER_MODEL: str = os.getenv(
        "PYDANTICAI_OPTIMIZER_MODEL", "google:gemini-2.5-pro-preview-03-25"
    )
    # Model for cover letter generation - using Gemini 2.5 Pro for best quality
    PYDANTICAI_COVER_LETTER_MODEL: str = os.getenv(
        "PYDANTICAI_COVER_LETTER_MODEL",
        "google:gemini-2.5-pro-preview-03-25",  # Using Gemini 2.5 Pro for cover letters
    )
    # Fallback models listed in order of preference
    PYDANTICAI_FALLBACK_MODELS: List[str] = [
        # Primary fallbacks - newer models with strong capabilities
        "anthropic:claude-3-7-sonnet-latest",  # Claude 3.7 Sonnet as first fallback
        "openai:gpt-4.1",  # Latest GPT-4.1 model
        "google:gemini-2.5-flash-preview-04-17",  # Latest Gemini 2.5 Flash (Apr 2025)
        # Secondary fallbacks - more cost-effective models
        "openai:gpt-4o",  # Older but still capable model
        "anthropic:claude-3-7-haiku-latest",  # Latest Claude 3.7 Haiku
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

    # WebSocket settings
    WS_PING_INTERVAL: int = int(os.getenv("WS_PING_INTERVAL", "30"))  # seconds

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

    # OVERRIDE: Always set google as the primary provider regardless of settings
    settings.PYDANTICAI_PRIMARY_PROVIDER = "google"

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
        if (
            "claude-3-7" in anthropic_default
            or "claude-3-7-sonnet-latest" in anthropic_default
        ):
            thinking_config = {
                "type": "enabled",
                "budget_tokens": settings.PYDANTICAI_THINKING_BUDGET,
            }

        config["anthropic"] = {
            "api_key": settings.ANTHROPIC_API_KEY,
            "default_model": anthropic_default,
            "temperature": settings.PYDANTICAI_TEMPERATURE,
            "max_tokens": settings.PYDANTICAI_MAX_TOKENS,
            "thinking_config": thinking_config,
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
            "max_tokens": settings.PYDANTICAI_MAX_TOKENS,
        }

    # Configure Google Gemini provider if API key is available
    if settings.GEMINI_API_KEY:
        # Get the appropriate default model depending on provider preference
        gemini_default = (
            settings.PYDANTICAI_PRIMARY_MODEL
            if settings.PYDANTICAI_PRIMARY_PROVIDER == "google"
            else "gemini-1.5-pro"  # Default Gemini Pro model
        )

        # Properly format for the API - gemini needs google-gla prefix
        if not gemini_default.startswith("google-gla:"):
            gemini_default = f"google-gla:{gemini_default}"

        # Configure thinking budget for Gemini models
        thinking_config = {"thinkingBudget": settings.PYDANTICAI_THINKING_BUDGET}

        config["gemini"] = {
            "api_key": settings.GEMINI_API_KEY,
            "default_model": gemini_default,
            "temperature": settings.PYDANTICAI_TEMPERATURE,
            "max_tokens": settings.PYDANTICAI_MAX_TOKENS,
            "thinking_config": thinking_config,
        }

    # If no providers are configured, raise a warning
    if not config:
        import warnings

        warnings.warn(
            "No PydanticAI providers configured. Please set at least one of: "
            "ANTHROPIC_API_KEY, OPENAI_API_KEY, or GEMINI_API_KEY"
        )

    return config