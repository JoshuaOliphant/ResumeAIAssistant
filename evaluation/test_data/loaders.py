# ABOUTME: Data loading utilities for test datasets
# ABOUTME: Handles loading and saving test datasets in various formats
"""
Test Data Loaders

Utilities for loading and saving test datasets in various formats including
YAML, JSON, and custom formats.
"""

import json
import yaml
from pathlib import Path
from typing import Union, Dict, Any
from .models import TestDataset, TestCase, EvaluationResult


def load_test_dataset(file_path: Union[str, Path]) -> TestDataset:
    """
    Load a test dataset from file.
    
    Args:
        file_path: Path to the dataset file (YAML or JSON)
        
    Returns:
        TestDataset instance
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file format is not supported
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"Dataset file not found: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        if file_path.suffix.lower() in ['.yaml', '.yml']:
            data = yaml.safe_load(f)
        elif file_path.suffix.lower() == '.json':
            data = json.load(f)
        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")
    
    return TestDataset(**data)


def save_test_dataset(dataset: TestDataset, file_path: Union[str, Path]) -> None:
    """
    Save a test dataset to file.
    
    Args:
        dataset: TestDataset to save
        file_path: Path to save the dataset (format determined by extension)
    """
    file_path = Path(file_path)
    
    # Ensure directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert to dictionary with JSON serialization
    data = json.loads(dataset.model_dump_json())
    
    with open(file_path, 'w', encoding='utf-8') as f:
        if file_path.suffix.lower() in ['.yaml', '.yml']:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
        elif file_path.suffix.lower() == '.json':
            json.dump(data, f, indent=2, ensure_ascii=False)
        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")


def load_test_case(file_path: Union[str, Path]) -> TestCase:
    """
    Load a single test case from file.
    
    Args:
        file_path: Path to the test case file
        
    Returns:
        TestCase instance
    """
    file_path = Path(file_path)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        if file_path.suffix.lower() in ['.yaml', '.yml']:
            data = yaml.safe_load(f)
        elif file_path.suffix.lower() == '.json':
            data = json.load(f)
        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")
    
    return TestCase(**data)


def save_test_case(test_case: TestCase, file_path: Union[str, Path]) -> None:
    """
    Save a single test case to file.
    
    Args:
        test_case: TestCase to save
        file_path: Path to save the test case
    """
    file_path = Path(file_path)
    
    # Ensure directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    data = json.loads(test_case.model_dump_json())
    
    with open(file_path, 'w', encoding='utf-8') as f:
        if file_path.suffix.lower() in ['.yaml', '.yml']:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
        elif file_path.suffix.lower() == '.json':
            json.dump(data, f, indent=2, ensure_ascii=False)
        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")


def load_evaluation_results(file_path: Union[str, Path]) -> Dict[str, EvaluationResult]:
    """
    Load evaluation results from file.
    
    Args:
        file_path: Path to the results file
        
    Returns:
        Dictionary mapping result IDs to EvaluationResult instances
    """
    file_path = Path(file_path)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        if file_path.suffix.lower() in ['.yaml', '.yml']:
            data = yaml.safe_load(f)
        elif file_path.suffix.lower() == '.json':
            data = json.load(f)
        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")
    
    results = {}
    for result_id, result_data in data.items():
        results[result_id] = EvaluationResult(**result_data)
    
    return results


def save_evaluation_results(results: Dict[str, EvaluationResult], file_path: Union[str, Path]) -> None:
    """
    Save evaluation results to file.
    
    Args:
        results: Dictionary of EvaluationResult instances
        file_path: Path to save the results
    """
    file_path = Path(file_path)
    
    # Ensure directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert to dictionary with proper JSON serialization
    data = {result_id: json.loads(result.model_dump_json()) for result_id, result in results.items()}
    
    with open(file_path, 'w', encoding='utf-8') as f:
        if file_path.suffix.lower() in ['.yaml', '.yml']:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
        elif file_path.suffix.lower() == '.json':
            json.dump(data, f, indent=2, ensure_ascii=False)
        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")