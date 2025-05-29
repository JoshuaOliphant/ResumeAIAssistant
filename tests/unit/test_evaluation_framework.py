# ABOUTME: Unit tests for the evaluation framework components
# ABOUTME: Tests configuration, data models, and basic functionality
"""
Evaluation Framework Unit Tests

Comprehensive tests for the evaluation framework including configuration,
data models, evaluators, and utility functions.
"""

import pytest
import tempfile
import os
from pathlib import Path
from datetime import datetime

from evaluation.config import EvaluationConfig, get_config, update_config, reset_config
from evaluation.test_data.models import TestCase, EvaluationResult, TestDataset
from evaluation.test_data.loaders import load_test_dataset, save_test_dataset
from evaluation.evaluators.base import BaseEvaluator
from evaluation.evaluators.accuracy import JobParsingAccuracyEvaluator, MatchScoreEvaluator
from evaluation.evaluators.quality import TruthfulnessEvaluator, ContentQualityEvaluator, RelevanceImpactEvaluator
from evaluation.utils.helpers import validate_inputs, sanitize_outputs, safe_json_parse


class TestEvaluationConfig:
    """Test the evaluation configuration system."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = EvaluationConfig()
        
        assert config.default_model == "haiku"
        assert config.max_tokens == 4096
        assert config.temperature == 0.1
        assert config.parallel_evaluations is True
        
    def test_config_with_env_vars(self):
        """Test configuration with environment variables."""
        # Set environment variables
        os.environ["EVALUATION_MODEL"] = "sonnet"
        os.environ["EVALUATION_MAX_TOKENS"] = "8192"
        os.environ["EVALUATION_TEMPERATURE"] = "0.2"
        
        config = EvaluationConfig()
        config.update_from_env()
        
        assert config.default_model == "sonnet"
        assert config.max_tokens == 8192
        assert config.temperature == 0.2
        
        # Clean up
        del os.environ["EVALUATION_MODEL"]
        del os.environ["EVALUATION_MAX_TOKENS"]
        del os.environ["EVALUATION_TEMPERATURE"]
    
    def test_model_mapping(self):
        """Test model ID mapping."""
        config = EvaluationConfig()
        
        assert config.get_model_id("haiku") == "claude-3-5-haiku-20241022"
        assert config.get_model_id("sonnet") == "claude-3-5-sonnet-20241022"
        assert config.get_model_id("opus") == "claude-3-opus-20240229"
        assert config.get_model_id("custom-model") == "custom-model"
    
    def test_config_to_dict(self):
        """Test configuration serialization."""
        config = EvaluationConfig()
        config_dict = config.to_dict()
        
        assert "default_model" in config_dict
        assert "max_tokens" in config_dict
        assert config_dict["anthropic_api_key"] in ["", "***"]  # Should be masked


class TestTestDataModels:
    """Test the test data models."""
    
    def test_test_case_creation(self):
        """Test TestCase model creation."""
        test_case = TestCase(
            name="Test Case 1",
            resume_content="Sample resume content",
            job_description="Sample job description",
            expected_match_score=85.0
        )
        
        assert test_case.name == "Test Case 1"
        assert test_case.expected_match_score == 85.0
        assert test_case.category == "general"  # Default value
        assert isinstance(test_case.created_at, datetime)
    
    def test_test_case_validation(self):
        """Test TestCase validation."""
        # Test invalid match score
        with pytest.raises(ValueError):
            TestCase(
                name="Invalid Test",
                resume_content="Content",
                job_description="Description", 
                expected_match_score=150.0  # Invalid score > 100
            )
    
    def test_evaluation_result_creation(self):
        """Test EvaluationResult model creation."""
        result = EvaluationResult(
            test_case_id="test-123",
            evaluator_name="test_evaluator",
            overall_score=0.85,
            passed=True
        )
        
        assert result.test_case_id == "test-123"
        assert result.evaluator_name == "test_evaluator"
        assert result.overall_score == 0.85
        assert result.passed is True
        assert isinstance(result.evaluated_at, datetime)
    
    def test_test_dataset_operations(self):
        """Test TestDataset operations."""
        dataset = TestDataset(name="Test Dataset", description="Test description")
        
        # Test adding test cases
        test_case = TestCase(
            name="Test Case 1",
            resume_content="Content",
            job_description="Description"
        )
        
        dataset.add_test_case(test_case)
        assert dataset.total_cases == 1
        assert len(dataset.test_cases) == 1
        
        # Test retrieving test case
        retrieved = dataset.get_test_case(test_case.id)
        assert retrieved is not None
        assert retrieved.name == "Test Case 1"
        
        # Test filtering
        test_case.category = "technical"
        test_case.tags = ["python", "senior"]
        
        filtered_by_category = dataset.filter_by_category("technical")
        assert len(filtered_by_category) == 1
        
        filtered_by_tags = dataset.filter_by_tags(["python"])
        assert len(filtered_by_tags) == 1


class TestTestDataLoaders:
    """Test the test data loading functionality."""
    
    def test_save_and_load_dataset(self):
        """Test saving and loading datasets."""
        # Create test dataset
        dataset = TestDataset(name="Test Dataset")
        test_case = TestCase(
            name="Test Case 1",
            resume_content="Sample content",
            job_description="Sample description"
        )
        dataset.add_test_case(test_case)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test YAML format
            yaml_path = Path(temp_dir) / "test_dataset.yaml"
            save_test_dataset(dataset, yaml_path)
            assert yaml_path.exists()
            
            loaded_dataset = load_test_dataset(yaml_path)
            assert loaded_dataset.name == dataset.name
            assert len(loaded_dataset.test_cases) == 1
            assert loaded_dataset.test_cases[0].name == test_case.name
            
            # Test JSON format
            json_path = Path(temp_dir) / "test_dataset.json"
            save_test_dataset(dataset, json_path)
            assert json_path.exists()
            
            loaded_dataset_json = load_test_dataset(json_path)
            assert loaded_dataset_json.name == dataset.name


class TestBaseEvaluator:
    """Test the base evaluator functionality."""
    
    def test_base_evaluator_interface(self):
        """Test that BaseEvaluator cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseEvaluator("test")
    
    def test_evaluator_validation(self):
        """Test input validation in evaluators."""
        evaluator = JobParsingAccuracyEvaluator()
        
        # Test with valid inputs
        test_case = TestCase(
            name="Test",
            resume_content="Content",
            job_description="Description"
        )
        
        assert evaluator.validate_inputs(test_case, {"some": "output"}) is True
        
        # Test with invalid inputs
        with pytest.raises(ValueError):
            evaluator.validate_inputs("not_a_test_case", {"some": "output"})
        
        with pytest.raises(ValueError):
            evaluator.validate_inputs(test_case, None)


class TestEvaluators:
    """Test the evaluator implementations."""
    
    @pytest.mark.asyncio
    async def test_job_parsing_accuracy_evaluator(self):
        """Test JobParsingAccuracyEvaluator."""
        evaluator = JobParsingAccuracyEvaluator()
        
        test_case = TestCase(
            name="Job Parsing Test",
            resume_content="Sample resume",
            job_description="Sample job description"
        )
        
        actual_output = {
            "required_skills": [{"skill": "Python", "confidence": 0.9}],
            "technologies_mentioned": ["Python", "FastAPI"]
        }
        
        result = await evaluator.evaluate(test_case, actual_output)
        
        assert isinstance(result, EvaluationResult)
        assert result.evaluator_name == "job_parsing_accuracy"
        assert 0 <= result.overall_score <= 1
        # Check for the actual detailed scores from JobParsingAccuracyEvaluator
        assert "skill_precision" in result.detailed_scores
        assert "skill_recall" in result.detailed_scores
        assert "skill_f1" in result.detailed_scores
    
    @pytest.mark.asyncio
    async def test_match_score_evaluator(self):
        """Test MatchScoreEvaluator."""
        evaluator = MatchScoreEvaluator()
        
        test_case = TestCase(
            name="Match Score Test",
            resume_content="Sample resume",
            job_description="Sample job description",
            expected_match_score=80.0
        )
        
        actual_output = {
            "match_score": 82,
            "skills_match": {"score": 85, "strong_matches": ["Python"]},
            "experience_match": {"score": 80}
        }
        
        result = await evaluator.evaluate(test_case, actual_output)
        
        assert isinstance(result, EvaluationResult)
        assert result.evaluator_name == "match_score"
        assert 0 <= result.overall_score <= 1
    
    @pytest.mark.asyncio
    async def test_truthfulness_evaluator(self):
        """Test TruthfulnessEvaluator."""
        evaluator = TruthfulnessEvaluator()
        
        test_case = TestCase(
            name="Truthfulness Test",
            resume_content="Original content",
            job_description="Job description"
        )
        
        actual_output = {
            "original_content": "Original content",
            "optimized_content": "Enhanced original content",
            "is_truthful": True
        }
        
        result = await evaluator.evaluate(test_case, actual_output)
        
        assert isinstance(result, EvaluationResult)
        assert result.evaluator_name == "truthfulness"
        assert 0 <= result.overall_score <= 1


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_validate_inputs(self):
        """Test input validation helper."""
        inputs = {"field1": "value1", "field2": "value2"}
        required_fields = ["field1", "field2"]
        
        assert validate_inputs(inputs, required_fields) is True
        
        # Test missing fields
        with pytest.raises(ValueError, match="Missing required fields"):
            validate_inputs(inputs, ["field1", "field3"])
    
    def test_sanitize_outputs(self):
        """Test output sanitization."""
        # Test string sanitization
        sensitive_string = "API_KEY=secret123 and token=abc456"
        sanitized = sanitize_outputs(sensitive_string)
        
        assert "secret123" not in sanitized
        assert "abc456" not in sanitized
        assert "api_key=***" in sanitized.lower()
        
        # Test nested data sanitization
        nested_data = {
            "api_key": "secret",
            "data": ["item1", "item2"],
            "nested": {"token": "secret_token"}
        }
        
        sanitized_nested = sanitize_outputs(nested_data)
        assert isinstance(sanitized_nested, dict)
        assert "api_key" in sanitized_nested
    
    def test_safe_json_parse(self):
        """Test safe JSON parsing."""
        # Test valid JSON
        valid_json = '{"key": "value"}'
        result = safe_json_parse(valid_json)
        assert result == {"key": "value"}
        
        # Test JSON in markdown
        markdown_json = '```json\n{"key": "value"}\n```'
        result = safe_json_parse(markdown_json)
        assert result == {"key": "value"}
        
        # Test invalid JSON
        invalid_json = "not json"
        result = safe_json_parse(invalid_json)
        assert result is None


class TestGlobalConfig:
    """Test global configuration management."""
    
    def test_get_config_singleton(self):
        """Test that get_config returns singleton."""
        reset_config()  # Ensure clean state
        
        config1 = get_config()
        config2 = get_config()
        
        assert config1 is config2  # Same object
    
    def test_update_config(self):
        """Test updating global configuration."""
        reset_config()
        
        original_config = get_config()
        original_model = original_config.default_model
        
        update_config(default_model="sonnet")
        
        updated_config = get_config()
        assert updated_config.default_model == "sonnet"
        assert updated_config is original_config  # Same object
        
        # Test invalid parameter
        with pytest.raises(ValueError):
            update_config(invalid_parameter="value")


if __name__ == "__main__":
    pytest.main([__file__])