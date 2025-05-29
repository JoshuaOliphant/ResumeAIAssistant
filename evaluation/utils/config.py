# ABOUTME: Configuration utilities for easy access to evaluation settings
# ABOUTME: Provides helper functions for configuration management
"""
Configuration Utilities

Helper functions for accessing and managing evaluation framework configuration.
"""

from typing import Any, Dict
from ..config import get_config as _get_config, update_config as _update_config


def get_config() -> Dict[str, Any]:
    """Get current configuration as dictionary."""
    return _get_config().to_dict()


def update_config(**kwargs) -> None:
    """Update configuration with new values."""
    _update_config(**kwargs)