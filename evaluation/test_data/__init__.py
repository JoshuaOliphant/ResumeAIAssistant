# ABOUTME: Test data management for evaluation framework
# ABOUTME: Handles loading, validation, and storage of test datasets
"""
Test Data Management Module

Provides functionality for managing test datasets used in the evaluation framework.
Includes data models, loading utilities, and validation capabilities.
"""

from .models import TestCase, EvaluationResult, TestDataset
from .loaders import load_test_dataset, save_test_dataset

__all__ = [
    "TestCase",
    "EvaluationResult", 
    "TestDataset",
    "load_test_dataset",
    "save_test_dataset",
]