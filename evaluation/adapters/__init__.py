# ABOUTME: Adapters for integrating with external evaluation frameworks
# ABOUTME: Includes PydanticAI and other evaluation framework adapters
"""
Evaluation Framework Adapters

This module contains adapters for integrating our evaluation framework with
external evaluation libraries and frameworks.
"""

from .pydantic_ai import PydanticAIAdapter, TestCaseToPydanticCase

__all__ = ['PydanticAIAdapter', 'TestCaseToPydanticCase']