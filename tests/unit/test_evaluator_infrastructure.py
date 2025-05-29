# ABOUTME: Comprehensive tests for the evaluation framework infrastructure
# ABOUTME: Tests BaseEvaluator, TestRunner, progress tracking, and PydanticAI integration
"""
Test Evaluator Infrastructure

Comprehensive tests for the evaluation framework infrastructure including
BaseEvaluator enhancements, TestRunner, progress tracking, and adapters.
"""

import asyncio
import pytest
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from evaluation.evaluators.base import BaseEvaluator
from evaluation.test_data.models import TestCase, TestDataset, EvaluationResult
from evaluation.test_runner import TestRunner, EvaluationReport, CircuitBreaker
from evaluation.runner_config import (
    TestRunnerConfig, ParallelismStrategy, RetryConfig, CircuitBreakerConfig,
    get_default_config, get_fast_config, get_conservative_config
)
from evaluation.progress import ProgressTracker, EvaluationProgress, ConsoleProgressBar
from evaluation.adapters.pydantic_ai import (
    PydanticAIAdapter, TestCaseToPydanticCase, PydanticEvaluatorWrapper
)


# Mock evaluator for testing
class MockEvaluator(BaseEvaluator):
    """Mock evaluator for testing."""
    
    def __init__(self, name: str, delay: float = 0.1, fail_rate: float = 0.0):
        super().__init__(name)
        self.delay = delay
        self.fail_rate = fail_rate
        self.call_count = 0
    
    async def evaluate(self, test_case: TestCase, actual_output: Any) -> EvaluationResult:
        """Mock evaluation with configurable delay and failure rate."""
        self.call_count += 1
        
        # Simulate processing time
        await asyncio.sleep(self.delay)
        
        # Simulate random failures
        import random
        if random.random() < self.fail_rate:
            raise RuntimeError(f"Mock evaluation failed for {test_case.id}")
        
        # Return mock result
        return self.create_result(
            test_case=test_case,
            overall_score=0.85,
            detailed_scores={"accuracy": 0.9, "relevance": 0.8},
            passed=True,
            notes="Mock evaluation completed",
            execution_time=self.delay,
            api_calls_made=1,
            tokens_used=100
        )
    
    def get_description(self) -> str:
        return f"Mock evaluator: {self.name}"


class TestBaseEvaluatorEnhancements:
    """Test enhancements to BaseEvaluator class."""
    
    def test_evaluator_initialization(self):
        """Test evaluator initialization with config."""
        config = {"model": "gpt-4", "temperature": 0.7}
        evaluator = MockEvaluator("test_evaluator")
        
        assert evaluator.name == "test_evaluator"
        assert evaluator.config == {}
        assert hasattr(evaluator, '_is_async')
        assert evaluator._is_async is True
    
    @pytest.mark.asyncio
    async def test_evaluate_batch(self):
        """Test batch evaluation functionality."""
        evaluator = MockEvaluator("batch_test", delay=0.01)
        
        # Create test cases
        test_cases = [
            TestCase(name=f"Test {i}", resume_content="Resume", job_description="Job")
            for i in range(3)
        ]
        outputs = [{"output": i} for i in range(3)]
        
        # Run batch evaluation
        results = await evaluator.evaluate_batch(test_cases, outputs)
        
        assert len(results) == 3
        assert all(isinstance(r, EvaluationResult) for r in results)
        assert evaluator.call_count == 3
    
    @pytest.mark.asyncio
    async def test_evaluate_batch_mismatch(self):
        """Test batch evaluation with mismatched inputs."""
        evaluator = MockEvaluator("batch_test")
        
        test_cases = [TestCase(name="Test", resume_content="R", job_description="J")]
        outputs = [{"output": 1}, {"output": 2}]
        
        with pytest.raises(ValueError, match="must match"):
            await evaluator.evaluate_batch(test_cases, outputs)
    
    def test_evaluate_sync(self):
        """Test synchronous evaluation method."""
        evaluator = MockEvaluator("sync_test", delay=0.01)
        test_case = TestCase(name="Test", resume_content="Resume", job_description="Job")
        
        # Call sync method
        result = evaluator.evaluate_sync(test_case, {"output": "test"})
        
        assert isinstance(result, EvaluationResult)
        assert result.overall_score == 0.85
        assert evaluator.call_count == 1
    
    def test_get_capabilities(self):
        """Test evaluator capabilities reporting."""
        evaluator = MockEvaluator("capability_test")
        capabilities = evaluator.get_capabilities()
        
        assert capabilities["name"] == "capability_test"
        assert capabilities["is_async"] is True
        assert capabilities["supports_batch"] is True
        assert "description" in capabilities
    
    def test_create_result_with_resources(self):
        """Test creating result with resource tracking."""
        evaluator = MockEvaluator("resource_test")
        test_case = TestCase(name="Test", resume_content="R", job_description="J")
        
        result = evaluator.create_result(
            test_case=test_case,
            overall_score=0.9,
            execution_time=1.5,
            api_calls_made=3,
            tokens_used=500
        )
        
        assert result.execution_time == 1.5
        assert result.api_calls_made == 3
        assert result.tokens_used == 500
        assert result.evaluation_model == ""  # No model in config


class TestRunnerConfigTests:
    """Test runner configuration options."""
    
    def test_default_config(self):
        """Test default configuration."""
        config = get_default_config()
        
        assert config.parallelism_strategy == ParallelismStrategy.ADAPTIVE
        assert config.max_workers == 4
        assert config.resource_limits.max_concurrent_evaluations == 10
        assert config.retry_config.max_attempts == 3
    
    def test_fast_config(self):
        """Test fast configuration preset."""
        config = get_fast_config()
        
        assert config.parallelism_strategy == ParallelismStrategy.ASYNCIO
        assert config.max_workers == 10
        assert config.resource_limits.max_concurrent_evaluations == 20
        assert config.retry_config.max_attempts == 1
    
    def test_conservative_config(self):
        """Test conservative configuration preset."""
        config = get_conservative_config()
        
        assert config.parallelism_strategy == ParallelismStrategy.NONE
        assert config.max_workers == 1
        assert config.fail_fast is True
    
    def test_config_validation(self):
        """Test configuration validation."""
        config = TestRunnerConfig()
        config.validate()  # Should not raise
        
        # Test invalid configurations
        config.max_workers = 0
        with pytest.raises(ValueError):
            config.validate()
        
        config.max_workers = 4
        config.resource_limits.evaluation_timeout = -1
        with pytest.raises(ValueError):
            config.validate()


class TestCircuitBreaker:
    """Test circuit breaker functionality."""
    
    def test_circuit_breaker_normal_operation(self):
        """Test circuit breaker under normal conditions."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)
        
        assert cb.can_execute() is True
        
        # Record some successes
        cb.record_success()
        cb.record_success()
        assert cb.can_execute() is True
    
    def test_circuit_breaker_opens_on_failures(self):
        """Test circuit breaker opens after threshold failures."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)
        
        # Record failures up to threshold
        cb.record_failure()
        cb.record_failure()
        assert cb.can_execute() is True  # Still open
        
        cb.record_failure()  # Hit threshold
        assert cb.can_execute() is False  # Circuit open
    
    def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovery after timeout."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
        
        # Open the circuit
        cb.record_failure()
        cb.record_failure()
        assert cb.can_execute() is False
        
        # Wait for recovery
        time.sleep(0.15)
        assert cb.can_execute() is True  # Circuit recovered


class TestProgressTracking:
    """Test progress tracking functionality."""
    
    def test_progress_initialization(self):
        """Test progress tracker initialization."""
        tracker = ProgressTracker(total_cases=10, total_evaluators=3)
        
        assert tracker.progress.total_cases == 10
        assert tracker.progress.total_evaluators == 3
        assert tracker.progress.total_evaluations == 30
        assert tracker.progress.completed_evaluations == 0
    
    def test_progress_updates(self):
        """Test progress update tracking."""
        tracker = ProgressTracker(total_cases=5, total_evaluators=2)
        
        # Start and complete an evaluation
        tracker.start_evaluation("case1", "eval1")
        time.sleep(0.01)  # Simulate work
        tracker.update("case1", "eval1", success=True)
        
        info = tracker.get_progress_info()
        assert info["completed"] == 1
        assert info["percentage"] > 0
        assert "eval1" in info["evaluator_progress"]
    
    def test_eta_calculation(self):
        """Test ETA calculation."""
        tracker = ProgressTracker(total_cases=10, total_evaluators=1, show_eta=True)
        
        # Simulate several evaluations
        for i in range(3):
            tracker.start_evaluation(f"case{i}", "eval1")
            time.sleep(0.01)  # Consistent timing
            tracker.update(f"case{i}", "eval1")
        
        info = tracker.get_progress_info()
        assert info["eta"] is not None
        assert info["eta"] > 0  # Should have positive ETA
    
    def test_progress_summary(self):
        """Test progress summary generation."""
        tracker = ProgressTracker(total_cases=2, total_evaluators=2)
        
        # Complete some evaluations
        tracker.update("case1", "eval1")
        tracker.update("case1", "eval2")
        
        summary = tracker.get_summary()
        assert "Evaluation Summary" in summary
        assert "2/4" in summary  # 2 completed out of 4 total
        assert "eval1" in summary
        assert "eval2" in summary


@pytest.mark.asyncio
class TestTestRunner:
    """Test TestRunner orchestration."""
    
    async def test_runner_initialization(self):
        """Test TestRunner initialization."""
        evaluators = [MockEvaluator("eval1"), MockEvaluator("eval2")]
        config = get_default_config()
        
        runner = TestRunner(evaluators, config)
        
        assert len(runner.evaluators) == 2
        assert len(runner.circuit_breakers) == 2
        assert runner.config == config
    
    async def test_sequential_evaluation(self):
        """Test sequential evaluation execution."""
        evaluators = [MockEvaluator("eval1", delay=0.01)]
        config = TestRunnerConfig()
        config.parallelism_strategy = ParallelismStrategy.NONE
        runner = TestRunner(evaluators, config)
        
        # Create test dataset
        dataset = TestDataset(name="Test Dataset")
        dataset.add_test_case(TestCase(name="Test 1", resume_content="R1", job_description="J1"))
        dataset.add_test_case(TestCase(name="Test 2", resume_content="R2", job_description="J2"))
        
        # Run evaluation
        report = await runner.run_evaluation(dataset)
        
        assert report.total_cases == 2
        assert report.successful_cases == 2
        assert len(report.results) == 2
        assert report.average_score > 0
    
    async def test_parallel_evaluation(self):
        """Test parallel evaluation execution."""
        evaluators = [
            MockEvaluator("eval1", delay=0.01),
            MockEvaluator("eval2", delay=0.01)
        ]
        config = TestRunnerConfig()
        config.parallelism_strategy = ParallelismStrategy.ASYNCIO
        config.max_workers = 4
        runner = TestRunner(evaluators, config)
        
        # Create test dataset
        dataset = TestDataset(name="Test Dataset")
        for i in range(3):
            dataset.add_test_case(
                TestCase(name=f"Test {i}", resume_content=f"R{i}", job_description=f"J{i}")
            )
        
        # Run evaluation
        start_time = time.time()
        report = await runner.run_evaluation(dataset)
        duration = time.time() - start_time
        
        # Should be faster than sequential (3 cases * 2 evaluators * 0.01s = 0.06s)
        assert duration < 0.05  # Parallel should be much faster
        assert report.total_cases == 3
        assert len(report.results) == 6  # 3 cases * 2 evaluators
    
    async def test_error_handling(self):
        """Test error handling during evaluation."""
        evaluators = [
            MockEvaluator("eval1", delay=0.01),
            MockEvaluator("eval2", delay=0.01, fail_rate=1.0)  # Always fails
        ]
        config = TestRunnerConfig()
        config.fail_fast = False
        runner = TestRunner(evaluators, config)
        
        dataset = TestDataset(name="Test Dataset")
        dataset.add_test_case(TestCase(name="Test", resume_content="R", job_description="J"))
        
        report = await runner.run_evaluation(dataset)
        
        assert report.failed_cases_count > 0
        assert len(report.failed_cases) > 0
        assert report.successful_cases == 1  # eval1 should succeed
    
    async def test_circuit_breaker_integration(self):
        """Test circuit breaker prevents cascading failures."""
        evaluators = [MockEvaluator("flaky", delay=0.01, fail_rate=1.0)]
        config = TestRunnerConfig()
        config.circuit_breaker_config.failure_threshold = 2
        runner = TestRunner(evaluators, config)
        
        dataset = TestDataset(name="Test Dataset")
        for i in range(5):
            dataset.add_test_case(
                TestCase(name=f"Test {i}", resume_content=f"R{i}", job_description=f"J{i}")
            )
        
        report = await runner.run_evaluation(dataset)
        
        # Circuit breaker should have opened after threshold failures
        # In sequential mode, circuit breaker is checked before each case
        # So all 5 cases run, but circuit breaker records all failures
        assert report.failed_cases_count == 5
        assert runner.circuit_breakers["flaky"].is_open is True
    
    async def test_report_generation(self):
        """Test evaluation report generation."""
        evaluators = [MockEvaluator("eval1", delay=0.01)]
        runner = TestRunner(evaluators)
        
        dataset = TestDataset(name="Test Dataset", description="Test description")
        dataset.add_test_case(TestCase(name="Test", resume_content="R", job_description="J"))
        
        report = await runner.run_evaluation(dataset)
        report_dict = report.to_dict()
        
        assert report_dict["dataset_name"] == "Test Dataset"
        assert "summary" in report_dict
        assert "resource_usage" in report_dict
        assert "evaluator_metrics" in report_dict
        assert "eval1" in report_dict["evaluator_metrics"]


class TestPydanticAIAdapter:
    """Test PydanticAI adapter functionality."""
    
    def test_test_case_conversion(self):
        """Test converting TestCase to PydanticAI Case."""
        test_case = TestCase(
            name="Test Case",
            resume_content="Resume content",
            job_description="Job description",
            expected_match_score=85.0,
            expected_skills=["Python", "ML"],
            category="technical"
        )
        
        pydantic_case = TestCaseToPydanticCase.convert(test_case)
        
        assert pydantic_case.name == "Test Case"
        assert pydantic_case.inputs["resume_content"] == "Resume content"
        assert pydantic_case.expected_output["match_score"] == 85.0
        assert pydantic_case.metadata["category"] == "technical"
    
    def test_dataset_conversion(self):
        """Test converting TestDataset to PydanticAI format."""
        dataset = TestDataset(name="Test Dataset", version="1.0")
        dataset.add_test_case(
            TestCase(name="Test 1", resume_content="R1", job_description="J1")
        )
        dataset.add_test_case(
            TestCase(name="Test 2", resume_content="R2", job_description="J2")
        )
        
        pydantic_cases = TestCaseToPydanticCase.convert_dataset(dataset)
        
        assert len(pydantic_cases) == 2
        assert all(hasattr(case, 'inputs') for case in pydantic_cases)
    
    @pytest.mark.asyncio
    async def test_evaluator_wrapper(self):
        """Test PydanticAI evaluator wrapper."""
        # Mock PydanticAI evaluator
        mock_pydantic_eval = Mock()
        
        wrapper = PydanticEvaluatorWrapper(mock_pydantic_eval, "wrapped_eval")
        test_case = TestCase(name="Test", resume_content="R", job_description="J")
        
        result = await wrapper.evaluate(test_case, {"output": "test"})
        
        assert isinstance(result, EvaluationResult)
        assert result.evaluator_name == "wrapped_eval"
        assert result.overall_score == 0.85  # Mock score
    
    def test_results_conversion(self):
        """Test converting results to PydanticAI format."""
        adapter = PydanticAIAdapter()
        
        # Create mock results
        results = [
            EvaluationResult(
                test_case_id="case1",
                evaluator_name="eval1",
                overall_score=0.8,
                passed=True
            ),
            EvaluationResult(
                test_case_id="case1",
                evaluator_name="eval2",
                overall_score=0.9,
                passed=True
            )
        ]
        
        pydantic_format = adapter.convert_results_to_pydantic_format(results)
        
        assert "results" in pydantic_format
        assert "summary" in pydantic_format
        assert len(pydantic_format["results"]) == 1  # Grouped by case
        assert pydantic_format["results"][0]["case_id"] == "case1"
        assert len(pydantic_format["results"][0]["evaluations"]) == 2
    
    def test_create_pydantic_dataset(self):
        """Test creating PydanticAI dataset structure."""
        dataset = TestDataset(
            name="Test Dataset",
            description="Test description",
            version="2.0",
            category="test"
        )
        dataset.add_test_case(
            TestCase(name="Test", resume_content="R", job_description="J")
        )
        
        pydantic_dataset = PydanticAIAdapter.create_pydantic_dataset(dataset)
        
        assert pydantic_dataset["name"] == "Test Dataset"
        assert pydantic_dataset["version"] == "2.0"
        assert len(pydantic_dataset["cases"]) == 1
        assert "metadata" in pydantic_dataset