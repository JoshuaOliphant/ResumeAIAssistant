# ABOUTME: Unit tests for dataset validator
# ABOUTME: Tests validation logic, error detection, and reporting

"""
Tests for Dataset Validator

Tests the dataset validation functionality including schema validation,
consistency checks, and error reporting.
"""

import pytest
import yaml
from pathlib import Path
from tempfile import NamedTemporaryFile
import sys

sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from evaluation.test_data.validation.dataset_validator import DatasetValidator
from evaluation.test_data.models import TestCase, TestDataset


class TestDatasetValidator:
    """Test cases for DatasetValidator."""
    
    @pytest.fixture
    def validator(self):
        """Create a validator instance."""
        return DatasetValidator()
    
    @pytest.fixture
    def valid_dataset_yaml(self):
        """Create a valid dataset YAML structure."""
        return {
            'name': 'Test Dataset',
            'version': '1.0',
            'description': 'A test dataset',
            'author': 'Test Author',
            'test_cases': [
                {
                    'id': 'test_001',
                    'name': 'Test Case 1',
                    'description': 'First test case',
                    'resume_content': 'A' * 200,  # Long enough content
                    'job_description': 'B' * 100,
                    'expected_match_score': 85.0,
                    'category': 'technical',
                    'difficulty': 'medium',
                    'tags': ['test'],
                    'ground_truth': {
                        'match_rationale': 'This is a good match because...',
                        'strength_areas': ['skill1', 'skill2'],
                        'gap_areas': ['skill3']
                    }
                }
            ]
        }
    
    def test_validate_valid_dataset(self, validator, valid_dataset_yaml, tmp_path):
        """Test validation of a valid dataset."""
        # Write valid dataset to file
        dataset_file = tmp_path / "valid_dataset.yaml"
        with open(dataset_file, 'w') as f:
            yaml.dump(valid_dataset_yaml, f)
        
        # Validate
        is_valid, dataset = validator.validate_dataset_file(dataset_file)
        
        assert is_valid is True
        assert dataset is not None
        assert dataset.name == 'Test Dataset'
        assert len(dataset.test_cases) == 1
        assert len(validator.errors) == 0
    
    def test_validate_missing_file(self, validator):
        """Test validation with missing file."""
        missing_file = Path("/tmp/nonexistent_dataset.yaml")
        is_valid, dataset = validator.validate_dataset_file(missing_file)
        
        assert is_valid is False
        assert dataset is None
        assert len(validator.errors) > 0
        assert "not found" in validator.errors[0]
    
    def test_validate_invalid_extension(self, validator, tmp_path):
        """Test validation with invalid file extension."""
        invalid_file = tmp_path / "dataset.json"
        invalid_file.write_text("{}")
        
        is_valid, dataset = validator.validate_dataset_file(invalid_file)
        
        assert is_valid is False
        assert "Unsupported file extension" in validator.errors[0]
    
    def test_validate_missing_required_fields(self, validator, tmp_path):
        """Test validation with missing required fields."""
        invalid_yaml = {
            'name': 'Test Dataset',
            # Missing 'version' and 'test_cases'
        }
        
        dataset_file = tmp_path / "invalid_dataset.yaml"
        with open(dataset_file, 'w') as f:
            yaml.dump(invalid_yaml, f)
        
        is_valid, dataset = validator.validate_dataset_file(dataset_file)
        
        assert is_valid is False
        assert any("version" in error for error in validator.errors)
        assert any("test_cases" in error for error in validator.errors)
    
    def test_validate_duplicate_test_case_ids(self, validator, valid_dataset_yaml, tmp_path):
        """Test validation catches duplicate test case IDs."""
        # Add duplicate test case
        valid_dataset_yaml['test_cases'].append({
            'id': 'test_001',  # Duplicate ID
            'name': 'Duplicate Test Case',
            'resume_content': 'X' * 200,
            'job_description': 'Y' * 100,
            'category': 'technical',
            'difficulty': 'easy'
        })
        
        dataset_file = tmp_path / "duplicate_ids.yaml"
        with open(dataset_file, 'w') as f:
            yaml.dump(valid_dataset_yaml, f)
        
        is_valid, dataset = validator.validate_dataset_file(dataset_file)
        
        assert is_valid is False
        assert any("Duplicate test case IDs" in error for error in validator.errors)
    
    def test_validate_short_content_warnings(self, validator, tmp_path):
        """Test validation generates warnings for short content."""
        dataset_yaml = {
            'name': 'Test Dataset',
            'version': '1.0',
            'test_cases': [
                {
                    'id': 'test_short',
                    'name': 'Short Content Test',
                    'resume_content': 'Too short',  # Less than 100 chars
                    'job_description': 'Also short',  # Less than 50 chars
                    'category': 'technical',
                    'difficulty': 'medium'
                }
            ]
        }
        
        dataset_file = tmp_path / "short_content.yaml"
        with open(dataset_file, 'w') as f:
            yaml.dump(dataset_yaml, f)
        
        is_valid, dataset = validator.validate_dataset_file(dataset_file)
        
        # Should be valid but with warnings
        assert is_valid is True
        assert len(validator.warnings) >= 2
        assert any("Resume content seems too short" in warning for warning in validator.warnings)
        assert any("Job description seems too short" in warning for warning in validator.warnings)
    
    def test_validate_invalid_match_score(self, validator, valid_dataset_yaml, tmp_path):
        """Test validation catches invalid match scores."""
        valid_dataset_yaml['test_cases'][0]['expected_match_score'] = 150.0  # Invalid
        
        dataset_file = tmp_path / "invalid_score.yaml"
        with open(dataset_file, 'w') as f:
            yaml.dump(valid_dataset_yaml, f)
        
        is_valid, dataset = validator.validate_dataset_file(dataset_file)
        
        assert is_valid is False
        # Pydantic validation error will be caught
        assert any("validation error" in error for error in validator.errors)
    
    def test_validate_ground_truth_warnings(self, validator, tmp_path):
        """Test validation generates warnings for incomplete ground truth."""
        dataset_yaml = {
            'name': 'Test Dataset',
            'version': '1.0',
            'test_cases': [
                {
                    'id': 'test_incomplete',
                    'name': 'Incomplete Ground Truth',
                    'resume_content': 'A' * 200,
                    'job_description': 'B' * 100,
                    'category': 'technical',
                    'difficulty': 'medium',
                    'ground_truth': {
                        'match_rationale': 'Short',  # Too short
                        # Missing strength_areas and gap_areas
                    }
                }
            ]
        }
        
        dataset_file = tmp_path / "incomplete_ground_truth.yaml"
        with open(dataset_file, 'w') as f:
            yaml.dump(dataset_yaml, f)
        
        is_valid, dataset = validator.validate_dataset_file(dataset_file)
        
        assert is_valid is True  # Warnings don't make it invalid
        assert any("Match rationale is too short" in warning for warning in validator.warnings)
        assert any("Missing required ground truth keys" in warning for warning in validator.warnings)
    
    def test_cross_validation_warnings(self, validator, tmp_path):
        """Test cross-validation generates appropriate warnings."""
        # Create dataset with limited diversity
        dataset_yaml = {
            'name': 'Limited Diversity Dataset',
            'version': '1.0',
            'test_cases': [
                {
                    'id': f'test_{i}',
                    'name': f'Test Case {i}',
                    'resume_content': 'A' * 200,
                    'job_description': 'B' * 100,
                    'category': 'technical',  # All same category
                    'difficulty': 'easy',  # All same difficulty
                    'expected_match_score': 90.0  # All high scores
                }
                for i in range(5)
            ]
        }
        
        dataset_file = tmp_path / "limited_diversity.yaml"
        with open(dataset_file, 'w') as f:
            yaml.dump(dataset_yaml, f)
        
        is_valid, dataset = validator.validate_dataset_file(dataset_file)
        
        assert is_valid is True
        assert any("only 1 category" in warning for warning in validator.warnings)
        assert any("only 'easy' difficulty" in warning for warning in validator.warnings)
        assert any("average score is high" in warning for warning in validator.warnings)
    
    def test_yaml_parsing_error(self, validator, tmp_path):
        """Test handling of YAML parsing errors."""
        dataset_file = tmp_path / "invalid_yaml.yaml"
        dataset_file.write_text("invalid: yaml: content: [")
        
        is_valid, dataset = validator.validate_dataset_file(dataset_file)
        
        assert is_valid is False
        assert any("YAML parsing error" in error for error in validator.errors)
    
    def test_print_validation_report(self, validator, capsys):
        """Test validation report printing."""
        validator.errors = ["Error 1", "Error 2"]
        validator.warnings = ["Warning 1"]
        
        validator.print_validation_report()
        
        captured = capsys.readouterr()
        assert "Found 2 errors" in captured.out
        assert "Error 1" in captured.out
        assert "Error 2" in captured.out
        assert "Found 1 warnings" in captured.out
        assert "Warning 1" in captured.out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])