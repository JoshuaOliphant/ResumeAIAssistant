# ABOUTME: Helper utilities for common evaluation framework operations
# ABOUTME: Provides validation, sanitization, and utility functions
"""
Evaluation Framework Helpers

Common utility functions used across the evaluation framework for
validation, sanitization, and other shared operations.
"""

import re
import json
import logging
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

logger = logging.getLogger(__name__)


def validate_inputs(inputs: Dict[str, Any], required_fields: List[str]) -> bool:
    """
    Validate that required fields are present in inputs.
    
    Args:
        inputs: Input dictionary to validate
        required_fields: List of required field names
        
    Returns:
        True if all required fields are present
        
    Raises:
        ValueError: If required fields are missing
    """
    missing_fields = [field for field in required_fields if field not in inputs]
    
    if missing_fields:
        raise ValueError(f"Missing required fields: {missing_fields}")
    
    return True


def sanitize_outputs(outputs: Any, max_length: Optional[int] = None) -> Any:
    """
    Sanitize outputs for logging and storage.
    
    Args:
        outputs: Output data to sanitize
        max_length: Maximum length for string outputs
        
    Returns:
        Sanitized output data
    """
    if isinstance(outputs, str):
        # Remove potential sensitive information
        sanitized = re.sub(r'api[_-]?key[s]?[\s]*[:=]\s*[^\s]+', 'api_key=***', outputs, flags=re.IGNORECASE)
        sanitized = re.sub(r'token[s]?[\s]*[:=]\s*[^\s]+', 'token=***', sanitized, flags=re.IGNORECASE)
        
        # Truncate if necessary
        if max_length and len(sanitized) > max_length:
            sanitized = sanitized[:max_length] + "..."
            
        return sanitized
    
    elif isinstance(outputs, dict):
        return {k: sanitize_outputs(v, max_length) for k, v in outputs.items()}
    
    elif isinstance(outputs, list):
        return [sanitize_outputs(item, max_length) for item in outputs]
    
    else:
        return outputs


def safe_json_parse(text: str) -> Optional[Dict]:
    """
    Safely parse JSON text with fallback handling.
    
    Args:
        text: JSON text to parse
        
    Returns:
        Parsed dictionary or None if parsing fails
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.debug(f"Initial JSON parse failed: {e}")
        
        # Try to extract JSON from markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError as e:
                logger.debug(f"Markdown JSON extraction failed: {e}")
        
        # Try to find JSON-like content
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError as e:
                logger.debug(f"JSON-like content extraction failed: {e}")
    
    logger.warning(f"Failed to parse JSON from text (length: {len(text)})")
    return None


def ensure_directory(path: Union[str, Path]) -> Path:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        path: Directory path
        
    Returns:
        Path object for the directory
    """
    path_obj = Path(path)
    path_obj.mkdir(parents=True, exist_ok=True)
    return path_obj


def format_percentage(value: float, decimals: int = 1) -> str:
    """
    Format a decimal value as a percentage string.
    
    Args:
        value: Decimal value (0.0 to 1.0)
        decimals: Number of decimal places
        
    Returns:
        Formatted percentage string
    """
    return f"{value * 100:.{decimals}f}%"


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to specified length with suffix.
    
    Args:
        text: Text to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to add when truncating
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def normalize_score(score: Union[int, float], min_val: float = 0.0, max_val: float = 100.0) -> float:
    """
    Normalize a score to 0-1 range.
    
    Args:
        score: Score to normalize
        min_val: Minimum possible value
        max_val: Maximum possible value
        
    Returns:
        Normalized score between 0.0 and 1.0
    """
    if max_val <= min_val:
        # Handle edge case: if range is invalid or zero-width
        # Return 1.0 if score is at or above min_val, 0.0 otherwise
        return 1.0 if float(score) >= min_val else 0.0
    
    return max(0.0, min(1.0, (float(score) - min_val) / (max_val - min_val)))