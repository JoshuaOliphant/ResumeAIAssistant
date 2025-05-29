# ABOUTME: Validation script for test datasets
# ABOUTME: Ensures dataset structure, schema compliance, and data quality

"""
Dataset Validator

Validates YAML test datasets for schema compliance, data consistency,
and quality checks.
"""

import yaml
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from pydantic import ValidationError

import sys
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from evaluation.test_data.models import TestCase, TestDataset


class DatasetValidator:
    """Validates test dataset YAML files."""
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        
    def validate_dataset_file(self, file_path: Path) -> Tuple[bool, TestDataset]:
        """
        Validate a dataset YAML file.
        
        Args:
            file_path: Path to the YAML dataset file
            
        Returns:
            Tuple of (is_valid, dataset_object)
        """
        self.errors = []
        self.warnings = []
        
        # Check file exists
        if not file_path.exists():
            self.errors.append(f"Dataset file not found: {file_path}")
            return False, None
            
        # Check file extension
        if file_path.suffix not in ['.yaml', '.yml']:
            self.errors.append(f"Invalid file extension: {file_path.suffix}. Use .yaml or .yml")
            return False, None
            
        try:
            # Load YAML content
            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)
                
            # Validate top-level structure
            dataset = self._validate_structure(data)
            if not dataset:
                return False, None
                
            # Validate test cases
            self._validate_test_cases(dataset)
            
            # Cross-validation checks
            self._cross_validate_dataset(dataset)
            
            # Return validation result
            is_valid = len(self.errors) == 0
            return is_valid, dataset
            
        except yaml.YAMLError as e:
            self.errors.append(f"YAML parsing error: {str(e)}")
            return False, None
        except Exception as e:
            self.errors.append(f"Unexpected error: {str(e)}")
            return False, None
            
    def _validate_structure(self, data: Dict[str, Any]) -> Optional[TestDataset]:
        """Validate top-level dataset structure."""
        required_fields = ['name', 'version', 'test_cases']
        
        # Check required fields
        for field in required_fields:
            if field not in data:
                self.errors.append(f"Missing required field: {field}")
                
        if self.errors:
            return None
            
        # Create TestDataset object
        try:
            # Convert test cases to TestCase objects
            test_cases = []
            for idx, case_data in enumerate(data.get('test_cases', [])):
                try:
                    test_case = TestCase(**case_data)
                    test_cases.append(test_case)
                except ValidationError as e:
                    self.errors.append(f"Test case {idx} validation error: {str(e)}")
                    
            # Create dataset object
            dataset_data = {
                'name': data['name'],
                'version': data['version'],
                'description': data.get('description'),
                'author': data.get('author'),
                'test_cases': test_cases
            }
            
            dataset = TestDataset(**dataset_data)
            return dataset
            
        except ValidationError as e:
            self.errors.append(f"Dataset validation error: {str(e)}")
            return None
            
    def _validate_test_cases(self, dataset: TestDataset):
        """Validate individual test cases."""
        if not dataset.test_cases:
            self.errors.append("Dataset has no test cases")
            return
            
        # Check for duplicate IDs
        ids = [case.id for case in dataset.test_cases]
        if len(ids) != len(set(ids)):
            self.errors.append("Duplicate test case IDs found")
            
        # Validate each test case
        for idx, case in enumerate(dataset.test_cases):
            self._validate_single_test_case(case, idx)
            
    def _validate_single_test_case(self, case: TestCase, idx: int):
        """Validate a single test case."""
        prefix = f"Test case {idx} ({case.id})"
        
        # Validate content lengths
        if len(case.resume_content) < 100:
            self.warnings.append(f"{prefix}: Resume content seems too short")
            
        if len(case.job_description) < 50:
            self.warnings.append(f"{prefix}: Job description seems too short")
            
        # Validate expected match score
        if case.expected_match_score is not None:
            if case.expected_match_score < 0 or case.expected_match_score > 100:
                self.errors.append(f"{prefix}: Invalid match score {case.expected_match_score}")
                
        # Validate ground truth
        if case.ground_truth:
            self._validate_ground_truth(case.ground_truth, prefix)
            
        # Check for consistency between tags and difficulty
        if case.difficulty == "easy" and "hard" in case.tags:
            self.warnings.append(f"{prefix}: Inconsistent difficulty and tags")
            
    def _validate_ground_truth(self, ground_truth: Dict[str, Any], prefix: str):
        """Validate ground truth data."""
        expected_keys = ['match_rationale', 'strength_areas', 'gap_areas']
        
        for key in expected_keys:
            if key not in ground_truth:
                self.warnings.append(f"{prefix}: Missing ground truth key: {key}")
                
        # Validate rationale
        if 'match_rationale' in ground_truth:
            rationale = ground_truth['match_rationale']
            if len(rationale) < 20:
                self.warnings.append(f"{prefix}: Match rationale seems too short")
                
    def _cross_validate_dataset(self, dataset: TestDataset):
        """Perform cross-validation checks across the dataset."""
        # Check category distribution
        categories = [case.category for case in dataset.test_cases]
        category_counts = {cat: categories.count(cat) for cat in set(categories)}
        
        if len(category_counts) < 2:
            self.warnings.append("Dataset has limited category diversity")
            
        # Check difficulty distribution
        difficulties = [case.difficulty for case in dataset.test_cases]
        difficulty_counts = {diff: difficulties.count(diff) for diff in set(difficulties)}
        
        if len(difficulty_counts) < 2:
            self.warnings.append("Dataset has limited difficulty diversity")
            
        # Check score distribution
        scores = [case.expected_match_score for case in dataset.test_cases 
                 if case.expected_match_score is not None]
        
        if scores:
            avg_score = sum(scores) / len(scores)
            if avg_score > 80 or avg_score < 20:
                self.warnings.append(f"Dataset average score ({avg_score:.1f}) seems skewed")
                
    def print_validation_report(self):
        """Print validation results."""
        print("\n=== Dataset Validation Report ===")
        
        if self.errors:
            print(f"\n❌ Found {len(self.errors)} errors:")
            for error in self.errors:
                print(f"  - {error}")
        else:
            print("\n✅ No errors found")
            
        if self.warnings:
            print(f"\n⚠️  Found {len(self.warnings)} warnings:")
            for warning in self.warnings:
                print(f"  - {warning}")
        else:
            print("\n✅ No warnings found")
            
        print("\n" + "="*30 + "\n")


def main():
    """Main function to run validation from command line."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate test dataset YAML files")
    parser.add_argument("dataset_path", type=str, help="Path to dataset YAML file")
    parser.add_argument("--quiet", action="store_true", help="Only show errors")
    
    args = parser.parse_args()
    
    # Create validator
    validator = DatasetValidator()
    
    # Validate dataset
    dataset_path = Path(args.dataset_path)
    is_valid, dataset = validator.validate_dataset_file(dataset_path)
    
    # Print report
    if not args.quiet:
        validator.print_validation_report()
        
        if dataset:
            print(f"Dataset: {dataset.name} v{dataset.version}")
            print(f"Test cases: {len(dataset.test_cases)}")
            print(f"Categories: {len(set(case.category for case in dataset.test_cases))}")
            
    # Exit with appropriate code
    sys.exit(0 if is_valid else 1)


if __name__ == "__main__":
    main()