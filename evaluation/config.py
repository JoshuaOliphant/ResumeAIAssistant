# ABOUTME: Configuration management for the evaluation framework
# ABOUTME: Centralizes settings, API keys, and runtime parameters
"""
Evaluation Framework Configuration

Provides centralized configuration management for the evaluation framework.
Handles environment variables, API keys, model settings, and runtime parameters.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class EvaluationConfig:
    """Configuration class for the evaluation framework."""
    
    # API Configuration
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    
    # Model Configuration  
    default_model: str = "haiku"
    model_mapping: Dict[str, str] = field(default_factory=lambda: {
        "haiku": "claude-3-5-haiku-20241022",
        "sonnet": "claude-3-5-sonnet-20241022", 
        "opus": "claude-3-opus-20240229"
    })
    
    # Evaluation Settings
    max_tokens: int = 4096
    temperature: float = 0.1
    parallel_evaluations: bool = True
    max_parallel_workers: int = 5
    
    # Paths
    project_root: Path = field(default_factory=lambda: Path(__file__).parent.parent)
    test_data_dir: Path = field(default_factory=lambda: Path(__file__).parent / "test_data")
    results_dir: Path = field(default_factory=lambda: Path(__file__).parent / "results")
    
    # Logging
    log_level: str = "INFO"
    log_to_file: bool = True
    log_file_path: Optional[Path] = field(default_factory=lambda: Path(__file__).parent / "evaluation.log")
    
    # Performance
    api_retry_attempts: int = 3
    api_retry_delay: float = 1.0
    request_timeout: float = 60.0
    
    # Testing
    test_mode: bool = field(default_factory=lambda: os.getenv("EVALUATION_TEST_MODE", "false").lower() == "true")
    mock_api_calls: bool = field(default_factory=lambda: os.getenv("MOCK_API_CALLS", "false").lower() == "true")
    
    def __post_init__(self):
        """Post-initialization validation and setup."""
        # Ensure required directories exist
        self.test_data_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Validate API key
        if not self.anthropic_api_key and not self.mock_api_calls:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")
        
        # Convert relative paths to absolute
        if not self.project_root.is_absolute():
            self.project_root = self.project_root.resolve()
        if not self.test_data_dir.is_absolute():
            self.test_data_dir = self.project_root / self.test_data_dir
        if not self.results_dir.is_absolute():
            self.results_dir = self.project_root / self.results_dir
    
    def get_model_id(self, model_name: str) -> str:
        """Get the full model ID for a given model name."""
        return self.model_mapping.get(model_name, model_name)
    
    def update_from_env(self) -> None:
        """Update configuration from environment variables."""
        env_mappings = {
            "EVALUATION_MODEL": "default_model",
            "EVALUATION_MAX_TOKENS": ("max_tokens", int),
            "EVALUATION_TEMPERATURE": ("temperature", float), 
            "EVALUATION_LOG_LEVEL": "log_level",
            "EVALUATION_PARALLEL": ("parallel_evaluations", lambda x: x.lower() == "true"),
            "EVALUATION_MAX_WORKERS": ("max_parallel_workers", int),
        }
        
        for env_var, attr_info in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value:
                if isinstance(attr_info, tuple):
                    attr_name, converter = attr_info
                    setattr(self, attr_name, converter(env_value))
                else:
                    setattr(self, attr_info, env_value)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary (excluding sensitive data)."""
        config_dict = {}
        for key, value in self.__dict__.items():
            if key == "anthropic_api_key":
                config_dict[key] = "***" if value else ""
            elif isinstance(value, Path):
                config_dict[key] = str(value)
            else:
                config_dict[key] = value
        return config_dict


# Global configuration instance
_config: Optional[EvaluationConfig] = None


def get_config() -> EvaluationConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = EvaluationConfig()
        _config.update_from_env()
    return _config


def update_config(**kwargs) -> None:
    """Update the global configuration with new values."""
    global _config
    if _config is None:
        _config = EvaluationConfig()
    
    for key, value in kwargs.items():
        if hasattr(_config, key):
            setattr(_config, key, value)
        else:
            raise ValueError(f"Unknown configuration parameter: {key}")


def reset_config() -> None:
    """Reset configuration to default values."""
    global _config
    _config = None