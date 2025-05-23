"""
Configuration settings for the parallel processing architecture.

This module provides configuration settings for the parallel processing
architecture, including concurrency limits, section weights, and timeouts.
"""

from typing import Dict, Any
from app.core.config import settings

# Maximum number of concurrent tasks to run
# This should be tuned based on available resources and API rate limits
MAX_CONCURRENT_TASKS = getattr(settings, 'MAX_CONCURRENT_TASKS', 5)

# Maximum timeout for parallel tasks in seconds
# Tasks that exceed this timeout will be considered failed
# Increased to 180 seconds to account for Claude 3.7 Sonnet processing time
TASK_TIMEOUT_SECONDS = getattr(settings, 'PARALLEL_TASK_TIMEOUT', 180)

# Default weights for different resume sections
# Used to calculate the importance of each section for optimization
SECTION_WEIGHTS = {
    "summary": 0.7,
    "experience": 1.5,
    "education": 0.8,
    "skills": 1.8,
    "projects": 1.0,
    "certifications": 0.9,
    "other": 0.5
}

# Job type specific weights
JOB_TYPE_WEIGHTS = {
    "technical": {
        "skills": 2.0,
        "experience": 1.6,
        "projects": 1.5,
        "education": 0.9,
        "certifications": 1.0
    },
    "management": {
        "experience": 2.0,
        "skills": 1.2,
        "summary": 1.3,
        "certifications": 1.0
    },
    "entry_level": {
        "education": 1.8,
        "skills": 1.5,
        "projects": 1.5,
        "experience": 1.0
    }
}

# Model selection preferences for different section types
SECTION_MODEL_PREFERENCES = {
    "summary": {
        "preferred_provider": "anthropic",
        "model_capabilities": ["creative", "detailed"],
        "cost_sensitivity": 0.8  # Lower means less cost-sensitive
    },
    "experience": {
        "preferred_provider": "google",
        "model_capabilities": ["structured_output", "thinking"],
        "cost_sensitivity": 1.0
    },
    "education": {
        "preferred_provider": "google",
        "model_capabilities": ["structured_output"],
        "cost_sensitivity": 1.2
    },
    "skills": {
        "preferred_provider": "google",
        "model_capabilities": ["structured_output", "thinking"],
        "cost_sensitivity": 0.9
    },
    "projects": {
        "preferred_provider": "google",
        "model_capabilities": ["structured_output"],
        "cost_sensitivity": 1.1
    },
    "certifications": {
        "preferred_provider": "google",
        "model_capabilities": ["structured_output"],
        "cost_sensitivity": 1.2
    },
    "other": {
        "preferred_provider": "google",
        "model_capabilities": ["basic"],
        "cost_sensitivity": 1.5  # Higher means more cost-sensitive
    }
}

# Retry configuration for parallel tasks
RETRY_CONFIG = {
    "max_retries": 2,
    "initial_backoff_seconds": 0.5,
    "max_backoff_seconds": 5
}

def get_section_model_preferences(section_name: str) -> Dict[str, Any]:
    """
    Get model preferences for a specific resume section.
    
    Args:
        section_name: The name of the section
        
    Returns:
        Dictionary with model preferences
    """
    lower_name = section_name.lower()
    
    # Return preferences for the specific section if available
    for section, prefs in SECTION_MODEL_PREFERENCES.items():
        if section in lower_name or lower_name in section:
            return prefs
    
    # Return default preferences if no match found
    return SECTION_MODEL_PREFERENCES.get("other", {
        "preferred_provider": "google",
        "model_capabilities": ["basic"],
        "cost_sensitivity": 1.2
    })
