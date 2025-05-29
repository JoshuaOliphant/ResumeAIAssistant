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

try:
    from evaluation.test_data.models import TestCase, TestDataset
except ImportError:
    # Fallback for when running as script
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
            self.errors.append(f"Dataset file not found at path: {file_path}. Please verify the file path is correct.")
            return False, None
            
        # Check file extension
        if file_path.suffix not in ['.yaml', '.yml']:
            self.errors.append(f"Unsupported file extension '{file_path.suffix}' for file: {file_path.name}. Only .yaml and .yml files are supported.")
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
            self.errors.append(f"YAML parsing error in file {file_path.name}: {str(e)}. Please check YAML syntax.")
            return False, None
        except FileNotFoundError:
            self.errors.append(f"File {file_path.name} was deleted during processing.")
            return False, None
        except PermissionError:
            self.errors.append(f"Permission denied reading file {file_path.name}. Check file permissions.")
            return False, None
        except Exception as e:
            self.errors.append(f"Unexpected error processing file {file_path.name}: {str(e)}")
            return False, None
            
    def _validate_structure(self, data: Dict[str, Any]) -> Optional[TestDataset]:
        """Validate top-level dataset structure."""
        required_fields = ['name', 'version', 'test_cases']
        
        # Check required fields
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            self.errors.append(f"Missing required fields: {', '.join(missing_fields)}. Required fields are: {', '.join(required_fields)}")
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
            # Find duplicates
            duplicates = [id for id in set(ids) if ids.count(id) > 1]
            self.errors.append(f"Duplicate test case IDs found: {', '.join(duplicates)}. Each test case must have a unique ID.")
            
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
        required_keys = ['match_rationale', 'strength_areas', 'gap_areas']
        optional_keys = ['key_factors', 'interview_focus', 'recommendations']
        
        # Check for required keys
        missing_keys = [key for key in required_keys if key not in ground_truth]
        if missing_keys:
            self.warnings.append(f"{prefix}: Missing required ground truth keys: {', '.join(missing_keys)}")
        
        # Validate match rationale
        if 'match_rationale' in ground_truth:
            rationale = ground_truth['match_rationale']
            if isinstance(rationale, str):
                if len(rationale) < 30:
                    self.warnings.append(f"{prefix}: Match rationale is too short ({len(rationale)} chars). Should be at least 30 characters to provide meaningful explanation.")
                elif len(rationale) > 1000:
                    self.warnings.append(f"{prefix}: Match rationale is very long ({len(rationale)} chars). Consider being more concise.")
                
                # Check for key phrases that indicate good rationale
                good_phrases = ['experience', 'skills', 'requirement', 'background', 'match']
                if not any(phrase in rationale.lower() for phrase in good_phrases):
                    self.warnings.append(f"{prefix}: Match rationale should explain why the score was assigned based on requirements and candidate background.")
            else:
                self.errors.append(f"{prefix}: Match rationale must be a string, got {type(rationale).__name__}")
        
        # Validate strength areas
        if 'strength_areas' in ground_truth:
            strengths = ground_truth['strength_areas']
            if isinstance(strengths, list):
                if not strengths:
                    self.warnings.append(f"{prefix}: Strength areas list is empty. Should list candidate's advantages.")
                elif len(strengths) > 10:
                    self.warnings.append(f"{prefix}: Too many strength areas ({len(strengths)}). Consider grouping similar strengths.")
                    
                # Check for non-string items
                non_strings = [item for item in strengths if not isinstance(item, str)]
                if non_strings:
                    self.errors.append(f"{prefix}: All strength areas must be strings, found {len(non_strings)} non-string items")
            else:
                self.errors.append(f"{prefix}: Strength areas must be a list, got {type(strengths).__name__}")
        
        # Validate gap areas
        if 'gap_areas' in ground_truth:
            gaps = ground_truth['gap_areas']
            if isinstance(gaps, list):
                # Empty gaps list is acceptable for perfect matches
                if len(gaps) > 10:
                    self.warnings.append(f"{prefix}: Too many gap areas ({len(gaps)}). Consider grouping similar gaps.")
                    
                # Check for non-string items
                non_strings = [item for item in gaps if not isinstance(item, str)]
                if non_strings:
                    self.errors.append(f"{prefix}: All gap areas must be strings, found {len(non_strings)} non-string items")
            else:
                self.errors.append(f"{prefix}: Gap areas must be a list, got {type(gaps).__name__}")
        
        # Validate consistency between strengths/gaps and expected score
        # This requires access to the test case, so we'll add it as a parameter
        
        # Check for unexpected keys (not an error, but worth noting)
        all_expected_keys = set(required_keys + optional_keys)
        unexpected_keys = set(ground_truth.keys()) - all_expected_keys
        if unexpected_keys:
            self.warnings.append(f"{prefix}: Unexpected ground truth keys: {', '.join(unexpected_keys)}. Consider if these are necessary.")
                
    def _cross_validate_dataset(self, dataset: TestDataset):
        """Perform cross-validation checks across the dataset."""
        num_cases = len(dataset.test_cases)
        
        # Check category distribution
        categories = [case.category for case in dataset.test_cases]
        category_counts = {cat: categories.count(cat) for cat in set(categories)}
        
        if len(category_counts) < 2:
            self.warnings.append(f"Dataset has only {len(category_counts)} category: {list(category_counts.keys())}. Consider adding test cases from different categories (e.g., technical, management, operations).")
        elif num_cases >= 10:
            # For larger datasets, check if any category is over-represented
            max_count = max(category_counts.values())
            if max_count / num_cases > 0.8:
                dominant_cat = [cat for cat, count in category_counts.items() if count == max_count][0]
                self.warnings.append(f"Category '{dominant_cat}' dominates with {max_count}/{num_cases} cases ({max_count/num_cases*100:.0f}%). Consider balancing categories.")
            
        # Check difficulty distribution
        difficulties = [case.difficulty for case in dataset.test_cases]
        difficulty_counts = {diff: difficulties.count(diff) for diff in set(difficulties)}
        
        if len(difficulty_counts) < 2:
            self.warnings.append(f"Dataset has only '{list(difficulty_counts.keys())[0]}' difficulty. Consider adding test cases with varying difficulty levels (easy, medium, hard).")
        elif num_cases >= 6:
            # Check for missing difficulty levels
            expected_difficulties = {'easy', 'medium', 'hard'}
            missing_difficulties = expected_difficulties - set(difficulty_counts.keys())
            if missing_difficulties:
                self.warnings.append(f"Missing difficulty levels: {', '.join(missing_difficulties)}. Consider adding test cases with these difficulty levels.")
            
        # Check score distribution
        scores = [case.expected_match_score for case in dataset.test_cases 
                 if case.expected_match_score is not None]
        
        if scores:
            avg_score = sum(scores) / len(scores)
            min_score = min(scores)
            max_score = max(scores)
            
            # Check for score range coverage
            if max_score - min_score < 40:
                self.warnings.append(f"Limited score range: {min_score:.1f} to {max_score:.1f}. Consider adding test cases with more diverse match quality.")
            
            # Check for score skew
            if avg_score > 80:
                self.warnings.append(f"Dataset average score is high ({avg_score:.1f}). Consider adding more challenging test cases with lower match scores.")
            elif avg_score < 30:
                self.warnings.append(f"Dataset average score is low ({avg_score:.1f}). Consider adding some positive match examples.")
                
            # Check for score distribution
            score_ranges = {
                'Poor (0-39)': len([s for s in scores if s < 40]),
                'Partial (40-69)': len([s for s in scores if 40 <= s < 70]), 
                'Good (70-89)': len([s for s in scores if 70 <= s < 90]),
                'Excellent (90-100)': len([s for s in scores if s >= 90])
            }
            
            empty_ranges = [r for r, count in score_ranges.items() if count == 0]
            if len(empty_ranges) >= 2 and num_cases >= 8:
                self.warnings.append(f"Missing score ranges: {', '.join(empty_ranges)}. Consider adding test cases across different match quality levels.")
        
        # Check tag diversity
        all_tags = [tag for case in dataset.test_cases for tag in case.tags]
        unique_tags = set(all_tags)
        if len(unique_tags) < num_cases / 2:
            self.warnings.append(f"Limited tag diversity ({len(unique_tags)} unique tags for {num_cases} test cases). Consider using more descriptive and varied tags.")
                
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