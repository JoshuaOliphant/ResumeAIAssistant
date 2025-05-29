# ABOUTME: TestRunner orchestrates evaluation execution with parallel processing
# ABOUTME: Manages test case execution, progress tracking, and result aggregation
"""
Test Runner

Orchestrates the execution of evaluations across test datasets with support for
parallel processing, progress tracking, and comprehensive error handling.
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import traceback
from pathlib import Path

from .evaluators.base import BaseEvaluator
from .test_data.models import TestCase, TestDataset, EvaluationResult
from .runner_config import TestRunnerConfig, ParallelismStrategy
from .utils.logger import get_evaluation_logger
from .progress import ProgressTracker, EvaluationProgress


@dataclass
class EvaluationReport:
    """Comprehensive report of an evaluation run."""
    
    dataset_id: str
    dataset_name: str
    start_time: datetime
    end_time: datetime
    total_duration: float  # seconds
    
    # Results
    results: List[EvaluationResult] = field(default_factory=list)
    failed_cases: List[Tuple[TestCase, str]] = field(default_factory=list)  # (case, error_msg)
    
    # Aggregate metrics
    total_cases: int = 0
    successful_cases: int = 0
    failed_cases_count: int = 0
    average_score: float = 0.0
    
    # Resource usage
    total_tokens_used: int = 0
    total_api_calls: int = 0
    
    # Per-evaluator metrics
    evaluator_metrics: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary format."""
        return {
            "dataset_id": self.dataset_id,
            "dataset_name": self.dataset_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "total_duration": self.total_duration,
            "summary": {
                "total_cases": self.total_cases,
                "successful_cases": self.successful_cases,
                "failed_cases": self.failed_cases_count,
                "average_score": self.average_score,
                "success_rate": self.successful_cases / self.total_cases if self.total_cases > 0 else 0
            },
            "resource_usage": {
                "total_tokens": self.total_tokens_used,
                "total_api_calls": self.total_api_calls
            },
            "evaluator_metrics": self.evaluator_metrics,
            "results": [r.model_dump() for r in self.results],
            "failures": [
                {"case_id": case.id, "case_name": case.name, "error": error}
                for case, error in self.failed_cases
            ]
        }


class CircuitBreaker:
    """Circuit breaker for handling failing evaluators."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.is_open = False
    
    def record_success(self):
        """Record a successful evaluation."""
        self.failure_count = 0
        self.is_open = False
    
    def record_failure(self):
        """Record a failed evaluation."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.is_open = True
    
    def can_execute(self) -> bool:
        """Check if circuit breaker allows execution."""
        if not self.is_open:
            return True
        
        # Check if recovery timeout has passed
        if self.last_failure_time and \
           (time.time() - self.last_failure_time) > self.recovery_timeout:
            self.is_open = False
            self.failure_count = 0
            return True
        
        return False


class TestRunner:
    """Orchestrates evaluation execution across test datasets."""
    
    def __init__(
        self,
        evaluators: List[BaseEvaluator],
        config: Optional[TestRunnerConfig] = None
    ):
        """
        Initialize TestRunner.
        
        Args:
            evaluators: List of evaluators to run
            config: Runner configuration
        """
        self.evaluators = evaluators
        self.config = config or TestRunnerConfig()
        self.config.validate()
        
        self.logger = get_evaluation_logger("TestRunner")
        self.progress_tracker = None
        
        # Circuit breakers for each evaluator
        self.circuit_breakers = {
            evaluator.name: CircuitBreaker(
                self.config.circuit_breaker_config.failure_threshold,
                self.config.circuit_breaker_config.recovery_timeout
            )
            for evaluator in evaluators
        }
        
        # Thread pool for CPU-bound evaluators
        self._thread_pool = None
        if self.config.parallelism_strategy in [ParallelismStrategy.THREAD_POOL, ParallelismStrategy.ADAPTIVE]:
            self._thread_pool = ThreadPoolExecutor(max_workers=self.config.max_workers)
    
    async def run_evaluation(
        self,
        dataset: TestDataset,
        output_dir: Optional[Path] = None
    ) -> EvaluationReport:
        """
        Run evaluation on a test dataset.
        
        Args:
            dataset: Test dataset to evaluate
            output_dir: Optional directory to save intermediate results
            
        Returns:
            Comprehensive evaluation report
        """
        self.logger.info(f"Starting evaluation run for dataset: {dataset.name}")
        start_time = datetime.now()
        
        # Initialize progress tracking
        if self.config.progress_config.enabled:
            self.progress_tracker = ProgressTracker(
                total_cases=len(dataset.test_cases),
                total_evaluators=len(self.evaluators),
                show_eta=self.config.progress_config.show_eta
            )
        
        # Initialize report
        report = EvaluationReport(
            dataset_id=dataset.id,
            dataset_name=dataset.name,
            start_time=start_time,
            end_time=start_time,  # Will be updated
            total_duration=0.0,
            total_cases=len(dataset.test_cases)
        )
        
        try:
            # Run evaluations based on parallelism strategy
            if self.config.parallelism_strategy == ParallelismStrategy.NONE:
                await self._run_sequential(dataset, report)
            else:
                await self._run_parallel(dataset, report)
            
            # Calculate aggregate metrics
            self._calculate_aggregate_metrics(report)
            
        except Exception as e:
            self.logger.error(f"Evaluation run failed: {str(e)}")
            if self.config.fail_fast:
                raise
        
        finally:
            # Finalize report
            report.end_time = datetime.now()
            report.total_duration = (report.end_time - report.start_time).total_seconds()
            
            # Clean up thread pool
            if self._thread_pool:
                self._thread_pool.shutdown(wait=True)
            
            # Save report if output directory specified
            if output_dir:
                await self._save_report(report, output_dir)
        
        self.logger.info(
            f"Evaluation completed in {report.total_duration:.2f}s. "
            f"Success rate: {report.successful_cases}/{report.total_cases}"
        )
        
        return report
    
    async def _run_sequential(self, dataset: TestDataset, report: EvaluationReport):
        """Run evaluations sequentially."""
        for case in dataset.test_cases:
            for evaluator in self.evaluators:
                if not self.circuit_breakers[evaluator.name].can_execute():
                    self.logger.warning(f"Skipping evaluator {evaluator.name} due to circuit breaker")
                    continue
                
                try:
                    result = await self._evaluate_single(evaluator, case)
                    report.results.append(result)
                    report.successful_cases += 1
                    self.circuit_breakers[evaluator.name].record_success()
                    
                except Exception as e:
                    self._handle_evaluation_error(evaluator, case, e, report)
                    if self.config.fail_fast:
                        raise
                
                if self.progress_tracker:
                    self.progress_tracker.update(case.id, evaluator.name)
    
    async def _run_parallel(self, dataset: TestDataset, report: EvaluationReport):
        """Run evaluations in parallel."""
        # Create evaluation tasks
        tasks = []
        for case in dataset.test_cases:
            for evaluator in self.evaluators:
                if not self.circuit_breakers[evaluator.name].can_execute():
                    continue
                
                task = asyncio.create_task(
                    self._evaluate_with_tracking(evaluator, case, report)
                )
                tasks.append(task)
        
        # Use semaphore to limit concurrent evaluations
        semaphore = asyncio.Semaphore(self.config.resource_limits.max_concurrent_evaluations)
        
        async def limited_task(task):
            async with semaphore:
                return await task
        
        # Wait for all tasks with proper error handling
        results = await asyncio.gather(*[limited_task(task) for task in tasks], return_exceptions=True)
        
        # Process results
        for result in results:
            if isinstance(result, Exception):
                self.logger.error(f"Task failed with exception: {str(result)}")
                if self.config.fail_fast:
                    raise result
    
    async def _evaluate_single(
        self,
        evaluator: BaseEvaluator,
        test_case: TestCase
    ) -> EvaluationResult:
        """
        Evaluate a single test case with an evaluator.
        
        Args:
            evaluator: Evaluator to use
            test_case: Test case to evaluate
            
        Returns:
            Evaluation result
        """
        start_time = time.time()
        
        # For now, use the test case content as the actual output
        # In real usage, this would come from the system being tested
        actual_output = {
            "resume": test_case.resume_content,
            "job": test_case.job_description
        }
        
        # Validate inputs
        evaluator.validate_inputs(test_case, actual_output)
        
        # Run evaluation with timeout
        try:
            result = await asyncio.wait_for(
                evaluator.evaluate(test_case, actual_output),
                timeout=self.config.resource_limits.evaluation_timeout
            )
            
            # Update execution time if not set
            if result.execution_time == 0:
                result.execution_time = time.time() - start_time
            
            return result
            
        except asyncio.TimeoutError:
            raise TimeoutError(
                f"Evaluation timed out after {self.config.resource_limits.evaluation_timeout}s"
            )
    
    async def _evaluate_with_tracking(
        self,
        evaluator: BaseEvaluator,
        test_case: TestCase,
        report: EvaluationReport
    ):
        """Evaluate with progress tracking and error handling."""
        try:
            result = await self._evaluate_single(evaluator, test_case)
            report.results.append(result)
            report.successful_cases += 1
            self.circuit_breakers[evaluator.name].record_success()
            
            # Update resource usage
            report.total_tokens_used += result.tokens_used
            report.total_api_calls += result.api_calls_made
            
        except Exception as e:
            self._handle_evaluation_error(evaluator, test_case, e, report)
            if self.config.fail_fast:
                raise
        
        finally:
            if self.progress_tracker:
                self.progress_tracker.update(test_case.id, evaluator.name)
    
    def _handle_evaluation_error(
        self,
        evaluator: BaseEvaluator,
        test_case: TestCase,
        error: Exception,
        report: EvaluationReport
    ):
        """Handle evaluation errors."""
        error_msg = f"{evaluator.name}: {str(error)}"
        self.logger.error(f"Evaluation failed for case {test_case.id}: {error_msg}")
        
        if self.config.log_failed_cases:
            self.logger.debug(f"Stack trace: {traceback.format_exc()}")
        
        report.failed_cases.append((test_case, error_msg))
        report.failed_cases_count += 1
        
        # Update circuit breaker
        self.circuit_breakers[evaluator.name].record_failure()
    
    def _calculate_aggregate_metrics(self, report: EvaluationReport):
        """Calculate aggregate metrics for the report."""
        if not report.results:
            return
        
        # Calculate average score
        total_score = sum(r.overall_score for r in report.results)
        report.average_score = total_score / len(report.results)
        
        # Calculate per-evaluator metrics
        evaluator_results = {}
        for result in report.results:
            if result.evaluator_name not in evaluator_results:
                evaluator_results[result.evaluator_name] = []
            evaluator_results[result.evaluator_name].append(result)
        
        for evaluator_name, results in evaluator_results.items():
            avg_score = sum(r.overall_score for r in results) / len(results)
            avg_time = sum(r.execution_time for r in results) / len(results)
            total_tokens = sum(r.tokens_used for r in results)
            
            report.evaluator_metrics[evaluator_name] = {
                "total_evaluations": len(results),
                "average_score": avg_score,
                "average_execution_time": avg_time,
                "total_tokens_used": total_tokens,
                "success_rate": len(results) / report.total_cases
            }
    
    async def _save_report(self, report: EvaluationReport, output_dir: Path):
        """Save evaluation report to file."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"evaluation_report_{timestamp}.json"
        filepath = output_dir / filename
        
        import json
        with open(filepath, 'w') as f:
            json.dump(report.to_dict(), f, indent=2)
        
        self.logger.info(f"Report saved to: {filepath}")