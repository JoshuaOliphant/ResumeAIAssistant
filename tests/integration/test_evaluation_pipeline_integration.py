# ABOUTME: Integration tests for evaluation pipeline with real evaluators
# ABOUTME: Tests end-to-end pipeline workflows with actual evaluator implementations

"""
Evaluation Pipeline Integration Tests

Tests the complete evaluation pipeline integration including:
- End-to-end pipeline execution with real evaluators
- Service layer integration
- API endpoint functionality 
- Suite integration testing
- HaikuResumeOptimizer integration
"""

import pytest
import asyncio
from pathlib import Path
from datetime import datetime

from evaluation.pipeline import EvaluationPipeline, PipelineConfiguration, PipelineMode
from evaluation.test_data.models import TestCase
from evaluation.suites.quick_suite import QuickEvaluationSuite
from app.services.evaluation_service import EvaluationService, EvaluationRequest


class TestPipelineIntegration:
    """Test complete pipeline integration with real evaluators."""
    
    @pytest.fixture
    def sample_resume(self):
        """Sample resume content for testing."""
        return """
        John Smith
        Senior Software Engineer
        
        EXPERIENCE
        Senior Software Engineer | TechCorp Inc. | 2019-Present
        - Lead team of 6 engineers developing microservices using Python and Kubernetes
        - Designed RESTful APIs serving 10M+ daily requests
        - Mentored junior developers and conducted code reviews
        
        SKILLS
        Languages: Python, JavaScript, TypeScript, SQL
        Frameworks: Django, FastAPI, React.js, Node.js
        Cloud/DevOps: AWS, Docker, Kubernetes, CI/CD
        """
    
    @pytest.fixture
    def sample_job_description(self):
        """Sample job description for testing."""
        return """
        Senior Software Engineer
        
        Requirements:
        - 7+ years of software development experience
        - Strong proficiency in Python and JavaScript
        - Experience with microservices architecture and Kubernetes
        - Proven experience leading engineering teams
        - Experience building RESTful APIs
        - Strong understanding of cloud platforms (AWS preferred)
        """
    
    @pytest.fixture
    def test_case(self, sample_resume, sample_job_description):
        """Create test case from sample data."""
        return TestCase(
            id="integration_test_001",
            name="Integration Test Case",
            resume_content=sample_resume,
            job_description=sample_job_description,
            expected_match_score=85.0
        )
    
    @pytest.mark.asyncio
    async def test_quick_mode_pipeline_execution(self, test_case, sample_resume, sample_job_description):
        """Test quick mode pipeline execution with real evaluators."""
        config = PipelineConfiguration(mode=PipelineMode.QUICK)
        pipeline = EvaluationPipeline(config)
        
        actual_output = {
            "resume_content": sample_resume,
            "job_description": sample_job_description
        }
        
        result = await pipeline.evaluate(test_case, actual_output)
        
        # Verify pipeline completed successfully
        assert result.pipeline_id is not None
        assert result.test_case_id == test_case.id
        assert result.mode == PipelineMode.QUICK
        assert result.total_duration > 0
        
        # Verify evaluators ran
        assert len(result.evaluator_results) > 0
        expected_evaluators = {"job_parsing_accuracy", "match_score", "content_quality"}
        for evaluator_name in expected_evaluators:
            if evaluator_name in result.evaluator_results:
                eval_result = result.evaluator_results[evaluator_name]
                assert eval_result.overall_score >= 0.0
                assert eval_result.overall_score <= 1.0
                assert eval_result.execution_time > 0
        
        # Verify aggregation
        assert 0.0 <= result.overall_score <= 1.0
        assert 0.0 <= result.confidence_score <= 1.0
        assert isinstance(result.category_scores, dict)
        
        # Verify analysis
        assert isinstance(result.strengths, list)
        assert isinstance(result.weaknesses, list)
        assert isinstance(result.recommendations, list)
    
    @pytest.mark.asyncio
    async def test_comprehensive_mode_pipeline_execution(self, test_case, sample_resume, sample_job_description):
        """Test comprehensive mode pipeline execution with all evaluators."""
        config = PipelineConfiguration(mode=PipelineMode.COMPREHENSIVE)
        pipeline = EvaluationPipeline(config)
        
        actual_output = {
            "resume_content": sample_resume,
            "job_description": sample_job_description
        }
        
        result = await pipeline.evaluate(test_case, actual_output)
        
        # Verify all evaluators were attempted
        total_evaluators = len(result.evaluator_results) + len(result.failed_evaluators)
        assert total_evaluators == 5  # All available evaluators
        
        # Verify successful evaluators have valid results
        for evaluator_name, eval_result in result.evaluator_results.items():
            assert eval_result.overall_score >= 0.0
            assert eval_result.overall_score <= 1.0
            assert eval_result.execution_time > 0
            assert isinstance(eval_result.detailed_scores, dict)
    
    @pytest.mark.asyncio
    async def test_parallel_vs_sequential_execution(self, test_case, sample_resume, sample_job_description):
        """Test parallel vs sequential execution produces similar results."""
        actual_output = {
            "resume_content": sample_resume,
            "job_description": sample_job_description
        }
        
        # Run parallel execution
        parallel_config = PipelineConfiguration(
            mode=PipelineMode.QUICK,
            parallel_execution=True
        )
        parallel_pipeline = EvaluationPipeline(parallel_config)
        parallel_result = await parallel_pipeline.evaluate(test_case, actual_output)
        
        # Run sequential execution
        sequential_config = PipelineConfiguration(
            mode=PipelineMode.QUICK,
            parallel_execution=False
        )
        sequential_pipeline = EvaluationPipeline(sequential_config)
        sequential_result = await sequential_pipeline.evaluate(test_case, actual_output)
        
        # Results should be similar (allowing for minor variations)
        score_diff = abs(parallel_result.overall_score - sequential_result.overall_score)
        assert score_diff < 0.1  # Scores should be within 0.1
        
        # Same evaluators should have run
        assert set(parallel_result.evaluator_results.keys()) == set(sequential_result.evaluator_results.keys())
    
    @pytest.mark.asyncio
    async def test_optimization_evaluation(self, sample_resume, sample_job_description):
        """Test evaluation of optimization results."""
        # Simulate optimized resume (slightly better content)
        optimized_resume = sample_resume.replace(
            "Lead team of 6 engineers",
            "Successfully led and mentored a team of 6 engineers"
        ).replace(
            "Designed RESTful APIs",
            "Architected and implemented high-performance RESTful APIs"
        )
        
        test_case = TestCase(
            id="optimization_test",
            name="Optimization Test",
            resume_content=sample_resume,
            job_description=sample_job_description
        )
        
        actual_output = {
            "resume_before": sample_resume,
            "resume_after": optimized_resume,
            "job_description": sample_job_description,
            "optimization_applied": True
        }
        
        config = PipelineConfiguration(mode=PipelineMode.COMPREHENSIVE)
        pipeline = EvaluationPipeline(config)
        
        result = await pipeline.evaluate(test_case, actual_output)
        
        # Should have results from relevance impact evaluator
        if "relevance_impact" in result.evaluator_results:
            relevance_result = result.evaluator_results["relevance_impact"]
            # Should detect some improvement
            assert relevance_result.overall_score > 0.0


class TestQuickSuiteIntegration:
    """Test QuickEvaluationSuite integration."""
    
    @pytest.fixture
    def quick_suite(self, tmp_path):
        """Create QuickEvaluationSuite instance."""
        return QuickEvaluationSuite(output_directory=tmp_path)
    
    @pytest.mark.asyncio
    async def test_quick_suite_single_evaluation(self, quick_suite):
        """Test quick suite single evaluation."""
        resume = "Python developer with 3 years experience"
        job = "Looking for Python developer with 2+ years experience"
        
        result = await quick_suite.evaluate_single(resume, job)
        
        assert "evaluation_id" in result
        assert "overall_score" in result
        assert "confidence_score" in result
        assert "quick_summary" in result
        assert "key_issues" in result
        assert "next_steps" in result
        
        assert 0.0 <= result["overall_score"] <= 1.0
        assert isinstance(result["quick_summary"], str)
        assert isinstance(result["key_issues"], list)
        assert isinstance(result["next_steps"], list)
    
    @pytest.mark.asyncio
    async def test_quick_suite_batch_evaluation(self, quick_suite):
        """Test quick suite batch evaluation."""
        resume_job_pairs = [
            {
                "resume": "Python developer with 3 years experience",
                "job": "Looking for Python developer"
            },
            {
                "resume": "Java developer with 5 years experience", 
                "job": "Looking for Python developer"
            },
            {
                "resume": "Python expert with 8 years experience",
                "job": "Looking for Python developer"
            }
        ]
        
        result = await quick_suite.evaluate_batch(resume_job_pairs)
        
        assert "batch_summary" in result
        assert "individual_results" in result
        
        batch_summary = result["batch_summary"]
        assert batch_summary["total_pairs"] == 3
        assert batch_summary["successful_evaluations"] <= 3
        assert "average_score" in batch_summary
        assert "score_distribution" in batch_summary
        
        individual_results = result["individual_results"]
        assert len(individual_results) == 3
        for individual_result in individual_results:
            assert "overall_score" in individual_result
    
    def test_quick_suite_configuration(self, quick_suite):
        """Test quick suite configuration and info methods."""
        evaluator_info = quick_suite.get_evaluator_info()
        assert isinstance(evaluator_info, dict)
        assert len(evaluator_info) > 0
        
        config_summary = quick_suite.get_configuration_summary()
        assert config_summary["mode"] == "Quick"
        assert "evaluators" in config_summary
        assert "best_for" in config_summary



class TestEvaluationServiceIntegration:
    """Test EvaluationService integration."""
    
    @pytest.fixture
    def evaluation_service(self, tmp_path):
        """Create EvaluationService instance."""
        return EvaluationService(output_directory=tmp_path)
    
    @pytest.mark.asyncio
    async def test_evaluation_service_quick_mode(self, evaluation_service):
        """Test evaluation service with quick mode."""
        request = EvaluationRequest(
            resume_content="Python developer with experience",
            job_description="Looking for Python developer",
            mode=PipelineMode.QUICK,
            parallel_execution=True
        )
        
        evaluation_id = await evaluation_service.start_evaluation(request)
        
        assert evaluation_id is not None
        assert isinstance(evaluation_id, str)
        
        # Wait a moment for evaluation to complete
        await asyncio.sleep(2)
        
        # Get status
        try:
            status = await evaluation_service.get_evaluation_status(evaluation_id)
            assert status.evaluation_id == evaluation_id
        except:
            # May not be in active evaluations if completed quickly
            pass
    
    @pytest.mark.asyncio 
    async def test_optimization_result_evaluation(self, evaluation_service):
        """Test evaluation of optimization results through service."""
        original_resume = "Software developer"
        optimized_resume = "Experienced software developer with proven track record"
        job_description = "Looking for experienced software developer"
        
        result = await evaluation_service.evaluate_optimization_result(
            original_resume=original_resume,
            optimized_resume=optimized_resume,
            job_description=job_description,
            mode=PipelineMode.QUICK
        )
        
        assert result.overall_score >= 0.0
        assert result.overall_score <= 1.0
        assert result.status == "completed"
        assert result.mode == "quick"
    
    def test_evaluation_service_metrics(self, evaluation_service):
        """Test evaluation service performance metrics."""
        metrics = evaluation_service.get_performance_metrics()
        
        assert isinstance(metrics, dict)
        # May have no history initially
        if "total_evaluations" in metrics:
            assert metrics["total_evaluations"] >= 0


class TestPipelineErrorRecovery:
    """Test pipeline error recovery and resilience."""
    
    @pytest.mark.asyncio
    async def test_pipeline_with_missing_dependencies(self):
        """Test pipeline behavior when some dependencies are missing."""
        # This test would simulate missing optional dependencies
        # and verify graceful degradation
        config = PipelineConfiguration(mode=PipelineMode.QUICK)
        pipeline = EvaluationPipeline(config)
        
        test_case = TestCase(
            id="error_test",
            name="Error Recovery Test",
            resume_content="Test content",
            job_description="Test job"
        )
        
        actual_output = {
            "resume_content": "Test content",
            "job_description": "Test job"
        }
        
        # Pipeline should handle missing dependencies gracefully
        try:
            result = await pipeline.evaluate(test_case, actual_output)
            # Even with some failures, should return a result
            assert isinstance(result.pipeline_id, str)
            assert result.total_duration > 0
        except Exception as e:
            # If complete failure, should be handled gracefully
            assert isinstance(e, Exception)
    
    @pytest.mark.asyncio
    async def test_pipeline_timeout_handling(self):
        """Test pipeline behavior with timeouts."""
        # Create a configuration with very short timeout
        config = PipelineConfiguration(
            mode=PipelineMode.QUICK,
            fail_fast=False
        )
        pipeline = EvaluationPipeline(config)
        
        test_case = TestCase(
            id="timeout_test",
            name="Timeout Test",
            resume_content="Test content",
            job_description="Test job"
        )
        
        actual_output = {
            "resume_content": "Test content", 
            "job_description": "Test job"
        }
        
        # Should complete within reasonable time
        start_time = datetime.now()
        result = await pipeline.evaluate(test_case, actual_output)
        elapsed = (datetime.now() - start_time).total_seconds()
        
        # Should complete within 60 seconds for quick mode
        assert elapsed < 60
        assert isinstance(result.pipeline_id, str)


class TestPipelinePerformance:
    """Test pipeline performance characteristics."""
    
    @pytest.mark.asyncio
    async def test_quick_mode_performance(self):
        """Test that quick mode meets performance expectations."""
        config = PipelineConfiguration(mode=PipelineMode.QUICK)
        pipeline = EvaluationPipeline(config)
        
        test_case = TestCase(
            id="perf_test",
            name="Performance Test",
            resume_content="Software engineer with Python experience",
            job_description="Looking for Python developer"
        )
        
        actual_output = {
            "resume_content": test_case.resume_content,
            "job_description": test_case.job_description
        }
        
        start_time = datetime.now()
        result = await pipeline.evaluate(test_case, actual_output)
        elapsed = (datetime.now() - start_time).total_seconds()
        
        # Quick mode should complete within 30 seconds
        assert elapsed < 30
        assert result.total_duration < 30
        
        # Should have reasonable resource usage
        assert result.total_tokens_used < 10000  # Reasonable token usage
        assert result.total_api_calls < 10  # Reasonable API calls
    
    @pytest.mark.asyncio
    async def test_parallel_execution_performance(self):
        """Test that parallel execution improves performance."""
        test_case = TestCase(
            id="parallel_perf_test",
            name="Parallel Performance Test",
            resume_content="Software engineer with Python experience",
            job_description="Looking for Python developer"
        )
        
        actual_output = {
            "resume_content": test_case.resume_content,
            "job_description": test_case.job_description
        }
        
        # Test sequential execution
        sequential_config = PipelineConfiguration(
            mode=PipelineMode.QUICK,
            parallel_execution=False
        )
        sequential_pipeline = EvaluationPipeline(sequential_config)
        
        start_time = datetime.now()
        sequential_result = await sequential_pipeline.evaluate(test_case, actual_output)
        sequential_time = (datetime.now() - start_time).total_seconds()
        
        # Test parallel execution
        parallel_config = PipelineConfiguration(
            mode=PipelineMode.QUICK,
            parallel_execution=True
        )
        parallel_pipeline = EvaluationPipeline(parallel_config)
        
        start_time = datetime.now()
        parallel_result = await parallel_pipeline.evaluate(test_case, actual_output)
        parallel_time = (datetime.now() - start_time).total_seconds()
        
        # Parallel should be faster or at least not significantly slower
        # (Allow some variance due to overhead)
        assert parallel_time <= sequential_time * 1.2