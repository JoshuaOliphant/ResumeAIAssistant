# ABOUTME: Evaluation framework for resume optimization system
# ABOUTME: Provides systematic testing and improvement of prompt quality
"""
Resume Optimization Evaluation Framework

This package provides comprehensive evaluation capabilities for the resume optimization system,
enabling systematic testing, prompt improvement, and performance monitoring.

Modules:
- evaluators: Individual evaluation components for different quality dimensions
- test_data: Management and storage of test datasets
- results: Result processing and analysis tools
- utils: Shared utilities and configuration management
"""

__version__ = "0.1.0"
__author__ = "ResumeAI Assistant Team"

# Import main components for easy access
from .config import EvaluationConfig
from .utils.logger import get_evaluation_logger

__all__ = [
    "EvaluationConfig",
    "get_evaluation_logger",
]