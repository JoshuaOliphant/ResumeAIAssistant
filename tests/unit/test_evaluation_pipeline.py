# ABOUTME: Comprehensive tests for EvaluationPipeline implementation  
# ABOUTME: Tests pipeline orchestration, result aggregation, and error recovery

"""
Test Evaluation Pipeline

Comprehensive tests for the EvaluationPipeline class including:
- Pipeline initialization and configuration
- Evaluator orchestration and execution
- Result aggregation and analysis
- Error recovery and failure handling
- Progress tracking and reporting
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from pathlib import Path

from evaluation.pipeline import (
    EvaluationPipeline,
    PipelineConfiguration,
    PipelineMode,
    PipelineResult,
    PipelineProgress,
    EvaluationStage
)
from evaluation.test_data.models import TestCase, EvaluationResult


class TestEvaluationPipeline:
    """Test EvaluationPipeline functionality."""
    
    @pytest.fixture
    def sample_test_case(self):
        """Create a sample test case."""
        return TestCase(
            id="test_001",
            name="Test Case",
            resume_content="Software Engineer with Python experience",
            job_description="Python developer position"
        )
    
    @pytest.fixture
    def sample_actual_output(self):
        """Create sample actual output."""
        return {
            "resume_content": "Software Engineer with Python experience",
            "job_description": "Python developer position"
        }
    
    @pytest.fixture
    def mock_evaluator_result(self):
        """Create a mock evaluator result."""
        return EvaluationResult(
            test_case_id="test_001",
            evaluator_name="test_evaluator",
            overall_score=0.8,
            passed=True,
            detailed_scores={"precision": 0.9, "recall": 0.7},
            execution_time=1.5,
            tokens_used=100,
            api_calls_made=1,
            notes="Test evaluation completed successfully"
        )
    
    def test_pipeline_initialization_default(self):
        """Test pipeline initialization with default configuration."""
        pipeline = EvaluationPipeline()
        
        assert pipeline.config.mode == PipelineMode.COMPREHENSIVE
        assert pipeline.config.parallel_execution is True
        assert len(pipeline.evaluators) == 5  # All evaluators for comprehensive mode
        assert pipeline.progress.total_evaluators == len(pipeline.evaluators)
    
    def test_pipeline_initialization_quick_mode(self):
        """Test pipeline initialization with quick mode."""
        config = PipelineConfiguration(mode=PipelineMode.QUICK)
        pipeline = EvaluationPipeline(config)
        
        assert pipeline.config.mode == PipelineMode.QUICK
        assert len(pipeline.evaluators) == 3  # Essential evaluators only
        expected_evaluators = {"job_parsing_accuracy", "match_score", "content_quality"}
        assert set(pipeline.evaluators.keys()) == expected_evaluators
    
    def test_pipeline_initialization_custom_mode(self):
        """Test pipeline initialization with custom evaluators."""
        config = PipelineConfiguration(
            mode=PipelineMode.CUSTOM,
            evaluators=["job_parsing_accuracy", "truthfulness"]
        )
        pipeline = EvaluationPipeline(config)
        
        assert pipeline.config.mode == PipelineMode.CUSTOM
        assert len(pipeline.evaluators) == 2
        assert "job_parsing_accuracy" in pipeline.evaluators
        assert "truthfulness" in pipeline.evaluators
    
    def test_pipeline_initialization_accuracy_focused(self):
        """Test pipeline initialization with accuracy-focused mode."""
        config = PipelineConfiguration(mode=PipelineMode.ACCURACY_FOCUSED)
        pipeline = EvaluationPipeline(config)
        
        assert len(pipeline.evaluators) == 2
        expected_evaluators = {"job_parsing_accuracy", "match_score"}
        assert set(pipeline.evaluators.keys()) == expected_evaluators
    
    def test_pipeline_initialization_quality_focused(self):
        """Test pipeline initialization with quality-focused mode."""
        config = PipelineConfiguration(mode=PipelineMode.QUALITY_FOCUSED)
        pipeline = EvaluationPipeline(config)
        
        assert len(pipeline.evaluators) == 3
        expected_evaluators = {"truthfulness", "content_quality", "relevance_impact"}
        assert set(pipeline.evaluators.keys()) == expected_evaluators
    
    @pytest.mark.asyncio
    async def test_evaluate_successful_pipeline(
        self,
        sample_test_case,
        sample_actual_output,
        mock_evaluator_result
    ):
        """Test successful pipeline evaluation."""
        config = PipelineConfiguration(mode=PipelineMode.QUICK)
        pipeline = EvaluationPipeline(config)
        
        # Mock all evaluators to return successful results
        with patch.object(pipeline, '_run_single_evaluator', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_evaluator_result
            
            result = await pipeline.evaluate(sample_test_case, sample_actual_output)
            
            assert isinstance(result, PipelineResult)
            assert result.test_case_id == sample_test_case.id
            assert result.mode == PipelineMode.QUICK
            assert result.overall_score > 0
            assert len(result.evaluator_results) == len(pipeline.evaluators)
            assert result.total_duration > 0
    
    @pytest.mark.asyncio
    async def test_evaluate_with_failed_evaluators(
        self,
        sample_test_case,
        sample_actual_output,
        mock_evaluator_result
    ):
        """Test pipeline evaluation with some failed evaluators."""
        config = PipelineConfiguration(
            mode=PipelineMode.QUICK,
            fail_fast=False
        )
        pipeline = EvaluationPipeline(config)
        
        # Mock evaluators to have one failure
        async def mock_evaluator_side_effect(name, evaluator, test_case, actual_output):
            if name == "job_parsing_accuracy":
                raise Exception("Test evaluator failure")
            return mock_evaluator_result
        
        with patch.object(pipeline, '_run_single_evaluator', new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = mock_evaluator_side_effect
            
            result = await pipeline.evaluate(sample_test_case, sample_actual_output)
            
            assert isinstance(result, PipelineResult)
            assert len(result.failed_evaluators) == 1
            assert "job_parsing_accuracy" in result.failed_evaluators
            assert len(result.evaluator_results) == len(pipeline.evaluators) - 1
    
    @pytest.mark.asyncio
    async def test_evaluate_fail_fast_mode(
        self,
        sample_test_case,
        sample_actual_output
    ):
        """Test pipeline evaluation with fail_fast enabled."""
        config = PipelineConfiguration(
            mode=PipelineMode.QUICK,
            fail_fast=True,
            parallel_execution=False,  # Use sequential for fail_fast to work properly
            retry_failed_evaluators=False  # Disable retries for fast failure
        )
        pipeline = EvaluationPipeline(config)
        
        # Mock evaluator to fail
        with patch.object(pipeline, '_run_single_evaluator', new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = Exception("Test failure")
            
            with pytest.raises(Exception, match="Test failure"):
                await pipeline.evaluate(sample_test_case, sample_actual_output)
    
    @pytest.mark.asyncio
    async def test_parallel_execution(
        self,
        sample_test_case,
        sample_actual_output,
        mock_evaluator_result
    ):
        """Test parallel execution of evaluators."""
        config = PipelineConfiguration(
            mode=PipelineMode.QUICK,
            parallel_execution=True,
            max_concurrent_evaluators=2
        )
        pipeline = EvaluationPipeline(config)
        
        with patch.object(pipeline, '_run_single_evaluator', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_evaluator_result
            
            result = await pipeline.evaluate(sample_test_case, sample_actual_output)
            
            # Verify all evaluators were called
            assert mock_run.call_count == len(pipeline.evaluators)
            assert len(result.evaluator_results) == len(pipeline.evaluators)
    
    @pytest.mark.asyncio
    async def test_sequential_execution(
        self,
        sample_test_case,
        sample_actual_output,
        mock_evaluator_result
    ):
        """Test sequential execution of evaluators."""
        config = PipelineConfiguration(
            mode=PipelineMode.QUICK,
            parallel_execution=False
        )
        pipeline = EvaluationPipeline(config)
        
        with patch.object(pipeline, '_run_single_evaluator', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = mock_evaluator_result
            
            result = await pipeline.evaluate(sample_test_case, sample_actual_output)
            
            # Verify all evaluators were called sequentially
            assert mock_run.call_count == len(pipeline.evaluators)
            assert len(result.evaluator_results) == len(pipeline.evaluators)
    
    @pytest.mark.asyncio
    async def test_retry_mechanism(
        self,
        sample_test_case,
        sample_actual_output,
        mock_evaluator_result
    ):
        """Test retry mechanism for failed evaluators."""
        config = PipelineConfiguration(
            mode=PipelineMode.QUICK,
            retry_failed_evaluators=True,
            max_retries=2
        )
        pipeline = EvaluationPipeline(config)
        
        # Mock evaluator to fail first time, succeed on retry
        call_count = 0
        async def mock_evaluator_side_effect(name, evaluator, test_case, actual_output):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("First attempt failure")
            return mock_evaluator_result
        
        with patch.object(pipeline, '_run_single_evaluator', new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = mock_evaluator_side_effect
            
            # Mock the retry method to test retry logic
            with patch.object(pipeline, '_retry_evaluator', new_callable=AsyncMock) as mock_retry:
                mock_retry.return_value = mock_evaluator_result
                
                result = await pipeline.evaluate(sample_test_case, sample_actual_output)
                
                # Verify retry was attempted
                assert mock_retry.called
    
    def test_result_aggregation_weights(self):
        """Test result aggregation with different weights."""
        config = PipelineConfiguration(
            weight_accuracy=0.5,
            weight_quality=0.3,
            weight_relevance=0.2
        )
        pipeline = EvaluationPipeline(config)
        
        # Test weight retrieval
        assert pipeline._get_evaluator_weight("job_parsing_accuracy") == 0.5
        assert pipeline._get_evaluator_weight("match_score") == 0.5
        assert pipeline._get_evaluator_weight("truthfulness") == 0.3
        assert pipeline._get_evaluator_weight("content_quality") == 0.3
        assert pipeline._get_evaluator_weight("relevance_impact") == 0.2
    
    def test_category_score_calculation(self, mock_evaluator_result):
        """Test category score calculation."""
        pipeline = EvaluationPipeline()
        
        evaluator_results = {
            "job_parsing_accuracy": mock_evaluator_result,
            "match_score": mock_evaluator_result,
            "truthfulness": mock_evaluator_result,
            "content_quality": mock_evaluator_result,
            "relevance_impact": mock_evaluator_result
        }
        
        category_scores = pipeline._calculate_category_scores(evaluator_results)
        
        assert "accuracy" in category_scores
        assert "quality" in category_scores
        assert "relevance" in category_scores
        assert category_scores["accuracy"] == mock_evaluator_result.overall_score
        assert category_scores["quality"] == mock_evaluator_result.overall_score
        assert category_scores["relevance"] == mock_evaluator_result.overall_score
    
    def test_confidence_score_calculation(self, mock_evaluator_result):
        """Test confidence score calculation."""
        pipeline = EvaluationPipeline()
        
        # Test with consistent scores (high confidence)
        consistent_results = {
            "eval1": mock_evaluator_result,
            "eval2": mock_evaluator_result,
            "eval3": mock_evaluator_result
        }
        confidence = pipeline._calculate_confidence_score(consistent_results)
        assert confidence > 0.8  # Should be high confidence
        
        # Test with inconsistent scores (low confidence)
        inconsistent_result = EvaluationResult(
            test_case_id="test_001",
            evaluator_name="test_evaluator_2",
            overall_score=0.2,  # Very different from 0.8
            passed=False,
            detailed_scores={},
            execution_time=1.0,
            tokens_used=50,
            api_calls_made=1,
            notes="Low score result"
        )
        
        inconsistent_results = {
            "eval1": mock_evaluator_result,  # 0.8
            "eval2": inconsistent_result     # 0.2
        }
        confidence = pipeline._calculate_confidence_score(inconsistent_results)
        assert confidence < 0.5  # Should be low confidence
    
    def test_strengths_identification(self, mock_evaluator_result):
        """Test identification of strengths."""
        pipeline = EvaluationPipeline()
        
        result = PipelineResult(
            pipeline_id="test",
            test_case_id="test_001",
            mode=PipelineMode.QUICK,
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_duration=10.0
        )
        
        # Add high-scoring evaluator result
        high_score_result = EvaluationResult(
            test_case_id="test_001",
            evaluator_name="high_scorer",
            overall_score=0.9,
            passed=True,
            detailed_scores={"precision": 0.95, "recall": 0.85},
            execution_time=1.0,
            tokens_used=100,
            api_calls_made=1,
            notes="Excellent performance"
        )
        
        result.evaluator_results = {"high_scorer": high_score_result}
        
        strengths = pipeline._identify_strengths(result)
        
        assert len(strengths) > 0
        assert any("high scorer" in strength.lower() for strength in strengths)
        assert any("precision" in strength.lower() for strength in strengths)
    
    def test_weaknesses_identification(self):
        """Test identification of weaknesses."""
        pipeline = EvaluationPipeline()
        
        result = PipelineResult(
            pipeline_id="test",
            test_case_id="test_001",
            mode=PipelineMode.QUICK,
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_duration=10.0
        )
        
        # Add low-scoring evaluator result
        low_score_result = EvaluationResult(
            test_case_id="test_001",
            evaluator_name="low_scorer",
            overall_score=0.3,
            passed=False,
            detailed_scores={"precision": 0.2, "recall": 0.4},
            execution_time=1.0,
            tokens_used=100,
            api_calls_made=1,
            notes="Poor performance"
        )
        
        result.evaluator_results = {"low_scorer": low_score_result}
        result.failed_evaluators = {"failed_evaluator": "Error message"}
        
        weaknesses = pipeline._identify_weaknesses(result)
        
        assert len(weaknesses) > 0
        assert any("low scorer" in weakness.lower() for weakness in weaknesses)
        assert any("failed" in weakness.lower() for weakness in weaknesses)
    
    def test_recommendations_generation(self):
        """Test generation of recommendations."""
        pipeline = EvaluationPipeline()
        
        result = PipelineResult(
            pipeline_id="test",
            test_case_id="test_001",
            mode=PipelineMode.QUICK,
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_duration=10.0,
            confidence_score=0.4  # Low confidence
        )
        
        # Set low category scores
        result.category_scores = {
            "accuracy": 0.5,
            "quality": 0.6,
            "relevance": 0.4
        }
        
        recommendations = pipeline._generate_recommendations(result)
        
        assert len(recommendations) > 0
        assert any("accuracy" in rec.lower() for rec in recommendations)
        assert any("relevance" in rec.lower() for rec in recommendations)
        assert any("confidence" in rec.lower() for rec in recommendations)
    
    @pytest.mark.asyncio
    async def test_save_pipeline_result(self, tmp_path):
        """Test saving pipeline results to file."""
        config = PipelineConfiguration(
            save_intermediate_results=True,
            output_directory=tmp_path
        )
        pipeline = EvaluationPipeline(config)
        
        result = PipelineResult(
            pipeline_id="test_save",
            test_case_id="test_001",
            mode=PipelineMode.QUICK,
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_duration=10.0
        )
        
        await pipeline._save_pipeline_result(result)
        
        # Check that file was created
        result_files = list(tmp_path.glob("pipeline_result_test_save_*.json"))
        assert len(result_files) == 1
        
        # Verify file contents
        import json
        with open(result_files[0]) as f:
            saved_data = json.load(f)
        
        assert saved_data["pipeline_id"] == "test_save"
        assert saved_data["test_case_id"] == "test_001"
    
    def test_get_available_evaluators(self):
        """Test getting available evaluators."""
        pipeline = EvaluationPipeline()
        
        evaluators = pipeline.get_available_evaluators()
        
        expected_evaluators = [
            "job_parsing_accuracy",
            "match_score",
            "truthfulness",
            "content_quality",
            "relevance_impact"
        ]
        
        assert evaluators == expected_evaluators
    
    def test_get_evaluator_descriptions(self):
        """Test getting evaluator descriptions."""
        pipeline = EvaluationPipeline()
        
        descriptions = pipeline.get_evaluator_descriptions()
        
        assert isinstance(descriptions, dict)
        assert len(descriptions) == 5
        assert "job_parsing_accuracy" in descriptions
        assert "precision and recall" in descriptions["job_parsing_accuracy"].lower()


class TestPipelineProgress:
    """Test PipelineProgress functionality."""
    
    def test_progress_initialization(self):
        """Test progress tracker initialization."""
        progress = PipelineProgress(total_evaluators=5)
        
        assert progress.current_stage == EvaluationStage.INITIALIZATION
        assert len(progress.stages_completed) == 0
        assert len(progress.evaluators_completed) == 0
        assert progress.total_evaluators == 5
    
    def test_stage_completion(self):
        """Test stage completion tracking."""
        progress = PipelineProgress()
        
        progress.complete_stage(EvaluationStage.INITIALIZATION)
        
        assert EvaluationStage.INITIALIZATION in progress.stages_completed
        assert progress.current_stage == EvaluationStage.PRE_PROCESSING
    
    def test_evaluator_completion(self):
        """Test evaluator completion tracking."""
        progress = PipelineProgress(total_evaluators=3)
        
        progress.complete_evaluator("evaluator1")
        progress.complete_evaluator("evaluator2")
        
        assert len(progress.evaluators_completed) == 2
        assert progress.get_completion_percentage() == 2/3 * 100
    
    def test_completion_percentage(self):
        """Test completion percentage calculation."""
        progress = PipelineProgress(total_evaluators=4)
        
        assert progress.get_completion_percentage() == 0.0
        
        progress.complete_evaluator("eval1")
        assert progress.get_completion_percentage() == 25.0
        
        progress.complete_evaluator("eval2")
        progress.complete_evaluator("eval3")
        progress.complete_evaluator("eval4")
        assert progress.get_completion_percentage() == 100.0


class TestPipelineConfiguration:
    """Test PipelineConfiguration functionality."""
    
    def test_default_configuration(self):
        """Test default configuration values."""
        config = PipelineConfiguration()
        
        assert config.mode == PipelineMode.COMPREHENSIVE
        assert config.parallel_execution is True
        assert config.max_concurrent_evaluators == 3
        assert config.fail_fast is False
        assert config.save_intermediate_results is True
        assert config.weight_accuracy == 0.3
        assert config.weight_quality == 0.4
        assert config.weight_relevance == 0.3
    
    def test_custom_configuration(self):
        """Test custom configuration values."""
        config = PipelineConfiguration(
            mode=PipelineMode.QUICK,
            parallel_execution=False,
            max_concurrent_evaluators=1,
            fail_fast=True,
            weight_accuracy=0.5
        )
        
        assert config.mode == PipelineMode.QUICK
        assert config.parallel_execution is False
        assert config.max_concurrent_evaluators == 1
        assert config.fail_fast is True
        assert config.weight_accuracy == 0.5


class TestPipelineResult:
    """Test PipelineResult functionality."""
    
    def test_result_initialization(self):
        """Test pipeline result initialization."""
        result = PipelineResult(
            pipeline_id="test_pipeline",
            test_case_id="test_001",
            mode=PipelineMode.QUICK,
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_duration=15.5
        )
        
        assert result.pipeline_id == "test_pipeline"
        assert result.test_case_id == "test_001"
        assert result.mode == PipelineMode.QUICK
        assert result.total_duration == 15.5
        assert len(result.evaluator_results) == 0
        assert len(result.failed_evaluators) == 0
    
    def test_result_to_dict(self):
        """Test converting result to dictionary."""
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=10)
        
        result = PipelineResult(
            pipeline_id="test_pipeline",
            test_case_id="test_001",
            mode=PipelineMode.QUICK,
            start_time=start_time,
            end_time=end_time,
            total_duration=10.0,
            overall_score=0.85,
            confidence_score=0.9
        )
        
        result_dict = result.to_dict()

        assert result_dict["pipeline_id"] == "test_pipeline"
        assert result_dict["test_case_id"] == "test_001"
        assert result_dict["mode"] == "quick"
        assert result_dict["aggregated_scores"]["overall_score"] == 0.85
        assert result_dict["aggregated_scores"]["confidence_score"] == 0.9
        assert "timing" in result_dict
        assert "resource_usage" in result_dict


@pytest.fixture
def sample_test_case():
    return TestCase(
        id="test_global",
        name="Test Case",
        resume_content="Software Engineer with Python experience",
        job_description="Python developer position",
    )


@pytest.fixture
def sample_actual_output():
    return {
        "resume_content": "Software Engineer with Python experience",
        "job_description": "Python developer position",
    }


@pytest.fixture
def mock_evaluator_result():
    return EvaluationResult(
        test_case_id="test_global",
        evaluator_name="test_evaluator",
        overall_score=0.8,
        passed=True,
        detailed_scores={"precision": 0.9, "recall": 0.7},
        execution_time=1.5,
        tokens_used=100,
        api_calls_made=1,
        notes="Test evaluation completed successfully",
    )


class TestPipelineCaching:
    """Tests for pipeline caching functionality."""

    @pytest.mark.asyncio
    async def test_caching_enabled(self, sample_test_case, sample_actual_output, mock_evaluator_result):
        config = PipelineConfiguration(mode=PipelineMode.QUICK, use_cache=True)
        pipeline = EvaluationPipeline(config)

        from contextlib import ExitStack

        with ExitStack() as stack:
            for ev in pipeline.evaluators.values():
                stack.enter_context(patch.object(ev, 'evaluate', return_value=mock_evaluator_result))

            result1 = await pipeline.evaluate(sample_test_case, sample_actual_output)
            result2 = await pipeline.evaluate(sample_test_case, sample_actual_output)

            for ev in pipeline.evaluators.values():
                assert ev.evaluate.call_count == 1

            assert result2.cache_hits >= len(pipeline.evaluators)
            assert result1.overall_score == result2.overall_score

    @pytest.mark.asyncio
    async def test_cache_with_custom_size_limit(self, sample_test_case, sample_actual_output, mock_evaluator_result):
        """Test cache with custom size limit."""
        config = PipelineConfiguration(
            mode=PipelineMode.QUICK, 
            use_cache=True, 
            cache_max_size=2  # Small size for testing
        )
        pipeline = EvaluationPipeline(config)
        
        # Verify cache was initialized with custom size
        assert pipeline.cache.max_size == 2
        
        # Add more items than cache size to test eviction
        pipeline.cache.set("key1", "value1")
        pipeline.cache.set("key2", "value2")
        pipeline.cache.set("key3", "value3")  # Should evict key1
        
        # key1 should be evicted, key2 and key3 should remain
        assert pipeline.cache.get("key1") is None
        assert pipeline.cache.get("key2") == "value2"
        assert pipeline.cache.get("key3") == "value3"

    @pytest.mark.asyncio
    async def test_cache_key_generation_consistency(self, sample_test_case, sample_actual_output):
        """Test that cache key generation is consistent."""
        config = PipelineConfiguration(mode=PipelineMode.QUICK, use_cache=True)
        pipeline = EvaluationPipeline(config)
        
        # Generate cache keys for same inputs multiple times
        key1 = pipeline._generate_cache_key("evaluator1", sample_test_case, sample_actual_output)
        key2 = pipeline._generate_cache_key("evaluator1", sample_test_case, sample_actual_output)
        
        # Keys should be identical
        assert key1 == key2
        
        # Different evaluator name should generate different key
        key3 = pipeline._generate_cache_key("evaluator2", sample_test_case, sample_actual_output)
        assert key1 != key3

    @pytest.mark.asyncio 
    async def test_cache_error_handling(self, sample_test_case):
        """Test cache error handling with problematic data."""
        config = PipelineConfiguration(mode=PipelineMode.QUICK, use_cache=True)
        pipeline = EvaluationPipeline(config)
        
        # Test cache key generation with non-serializable data
        class NonSerializable:
            def __str__(self):
                raise Exception("Cannot serialize")
        
        problematic_output = {"data": NonSerializable()}
        
        # Should not crash, should fallback to basic hash
        cache_key = pipeline._generate_cache_key("evaluator1", sample_test_case, problematic_output)
        assert isinstance(cache_key, str)
        assert len(cache_key) > 0

    def test_cache_thread_safety(self):
        """Test cache thread safety."""
        import threading
        import time
        
        config = PipelineConfiguration(mode=PipelineMode.QUICK, use_cache=True)
        pipeline = EvaluationPipeline(config)
        cache = pipeline.cache
        
        results = []
        errors = []
        
        def cache_worker(worker_id):
            try:
                for i in range(100):
                    key = f"worker_{worker_id}_key_{i}"
                    value = f"worker_{worker_id}_value_{i}"
                    cache.set(key, value)
                    retrieved = cache.get(key)
                    if retrieved != value:
                        errors.append(f"Worker {worker_id}: Expected {value}, got {retrieved}")
                    results.append((worker_id, i, retrieved == value))
            except Exception as e:
                errors.append(f"Worker {worker_id}: Exception {e}")
        
        # Start multiple threads accessing cache concurrently
        threads = []
        for i in range(5):
            thread = threading.Thread(target=cache_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check that there were no errors
        assert len(errors) == 0, f"Thread safety errors: {errors}"
        assert len(results) == 500  # 5 workers * 100 operations each

    def test_cache_stats_tracking(self):
        """Test cache statistics tracking."""
        config = PipelineConfiguration(mode=PipelineMode.QUICK, use_cache=True)
        pipeline = EvaluationPipeline(config)
        cache = pipeline.cache
        
        # Initial stats
        initial_stats = cache.stats()
        assert initial_stats["hits"] == 0
        assert initial_stats["misses"] == 0
        assert initial_stats["size"] == 0
        
        # Add some data and test hits/misses
        cache.set("key1", "value1")
        
        # Should be a miss first time
        result1 = cache.get("key1")
        assert result1 == "value1"
        
        # Should be a hit second time
        result2 = cache.get("key1")
        assert result2 == "value1"
        
        # Test miss
        result3 = cache.get("nonexistent")
        assert result3 is None
        
        # Check final stats
        final_stats = cache.stats()
        assert final_stats["hits"] == 2
        assert final_stats["misses"] == 1
        assert final_stats["size"] == 1
        assert final_stats["max_size"] == 1000  # Default max size


class TestPipelineConfigurationValidation:
    """Tests for pipeline configuration validation."""

    def test_valid_configuration(self):
        """Test that valid configuration passes validation."""
        config = PipelineConfiguration(
            max_concurrent_evaluators=5,
            cache_ttl=1800.0,
            cache_max_size=500,
            weight_accuracy=0.4,
            weight_quality=0.3,
            weight_relevance=0.3,
            confidence_threshold=0.8,
            max_retries=3,
            retry_delay=2.0
        )
        # Should not raise any exceptions
        assert config.max_concurrent_evaluators == 5

    def test_invalid_concurrent_evaluators(self):
        """Test validation of max_concurrent_evaluators."""
        with pytest.raises(ValueError, match="max_concurrent_evaluators must be positive"):
            PipelineConfiguration(max_concurrent_evaluators=0)
        
        with pytest.raises(ValueError, match="max_concurrent_evaluators must be positive"):
            PipelineConfiguration(max_concurrent_evaluators=-1)

    def test_invalid_cache_settings(self):
        """Test validation of cache settings."""
        with pytest.raises(ValueError, match="cache_ttl must be non-negative"):
            PipelineConfiguration(cache_ttl=-1.0)
        
        with pytest.raises(ValueError, match="cache_max_size must be positive"):
            PipelineConfiguration(cache_max_size=0)

    def test_invalid_weights(self):
        """Test validation of weight settings."""
        with pytest.raises(ValueError, match="weight_accuracy must be between 0 and 1"):
            PipelineConfiguration(weight_accuracy=-0.1)
        
        with pytest.raises(ValueError, match="weight_accuracy must be between 0 and 1"):
            PipelineConfiguration(weight_accuracy=1.1)
        
        with pytest.raises(ValueError, match="weight_quality must be between 0 and 1"):
            PipelineConfiguration(weight_quality=2.0)
        
        with pytest.raises(ValueError, match="weight_relevance must be between 0 and 1"):
            PipelineConfiguration(weight_relevance=-0.5)

    def test_weights_sum_validation(self):
        """Test that weights must sum to approximately 1.0."""
        # Weights sum to 0.5 (too low)
        with pytest.raises(ValueError, match="Weights must sum to 1.0"):
            PipelineConfiguration(
                weight_accuracy=0.1,
                weight_quality=0.2,
                weight_relevance=0.2
            )
        
        # Weights sum to 1.5 (too high) 
        with pytest.raises(ValueError, match="Weights must sum to 1.0"):
            PipelineConfiguration(
                weight_accuracy=0.5,
                weight_quality=0.5,
                weight_relevance=0.5
            )

    def test_confidence_threshold_validation(self):
        """Test validation of confidence threshold."""
        with pytest.raises(ValueError, match="confidence_threshold must be between 0 and 1"):
            PipelineConfiguration(confidence_threshold=-0.1)
        
        with pytest.raises(ValueError, match="confidence_threshold must be between 0 and 1"):
            PipelineConfiguration(confidence_threshold=1.1)

    def test_retry_settings_validation(self):
        """Test validation of retry settings."""
        with pytest.raises(ValueError, match="max_retries must be non-negative"):
            PipelineConfiguration(max_retries=-1)
        
        with pytest.raises(ValueError, match="retry_delay must be non-negative"):
            PipelineConfiguration(retry_delay=-1.0)

    def test_weights_sum_tolerance(self):
        """Test that small floating point errors in weight sums are tolerated."""
        # This should pass (sum is 1.001, within tolerance)
        config = PipelineConfiguration(
            weight_accuracy=0.334,
            weight_quality=0.333,
            weight_relevance=0.334  # Sum: 1.001
        )
        assert config.weight_accuracy == 0.334


class TestPerformanceMonitoringIntegration:
    """Tests for performance monitoring integration."""

    @pytest.mark.asyncio
    async def test_performance_monitoring_enabled(self, sample_test_case, sample_actual_output, mock_evaluator_result):
        """Test that performance monitoring works correctly."""
        config = PipelineConfiguration(mode=PipelineMode.QUICK)
        pipeline = EvaluationPipeline(config)
        
        with patch.object(pipeline.evaluators['match_score'], 'evaluate', return_value=mock_evaluator_result):
            result = await pipeline.evaluate(sample_test_case, sample_actual_output)
            
            # Check that performance summary is present
            assert "performance_summary" in result.metadata
            perf_summary = result.metadata["performance_summary"]
            
            # Verify performance metrics structure
            assert "count" in perf_summary
            assert "average_time" in perf_summary
            assert "average_memory" in perf_summary
            assert "total_time" in perf_summary
            assert "max_time" in perf_summary
            assert "min_time" in perf_summary
            assert "errors" in perf_summary
            
            # Performance count should match number of evaluators
            assert perf_summary["count"] >= 1
            assert perf_summary["errors"] == 0
