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
    CLAUDE_CODE_TIMEOUT: int = int(os.getenv("CLAUDE_CODE_TIMEOUT", "1800"))  # 30 minutes
    CLAUDE_CODE_MAX_TIMEOUT: int = int(os.getenv("CLAUDE_CODE_MAX_TIMEOUT", "3600"))  # 60 minutes max
    ENABLE_FALLBACK: bool = False  # Disable fallback to legacy customization
    FALLBACK_THRESHOLD: int = int(os.getenv("FALLBACK_THRESHOLD", "3"))  # Number of failures before fallback

    # MCP (Model Context Protocol) settings
    CLAUDE_USE_MCP: bool = os.getenv("CLAUDE_USE_MCP", "false").lower() == "true"
    BRAVE_SEARCH_API_KEY: Optional[str] = os.getenv("BRAVE_SEARCH_API_KEY")
    CLAUDE_SYSTEM_PROMPT: Optional[str] = os.getenv("CLAUDE_SYSTEM_PROMPT")

    # No legacy configuration is needed anymore as PydanticAI has been completely removed

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


# Configuration is now simplified with complete removal of PydanticAI