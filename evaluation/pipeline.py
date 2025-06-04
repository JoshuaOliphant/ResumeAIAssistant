# ABOUTME: EvaluationPipeline orchestrates all evaluators in a cohesive workflow
# ABOUTME: Provides integration with HaikuResumeOptimizer and comprehensive result aggregation

"""
Evaluation Pipeline

Main orchestrator for running complete evaluation workflows that combine all evaluators
into cohesive pipelines with result aggregation, progress tracking, and error recovery.
"""

import asyncio
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json

from .evaluators.base import BaseEvaluator
from .evaluators.accuracy import JobParsingAccuracyEvaluator, MatchScoreEvaluator
from .evaluators.quality import TruthfulnessEvaluator, ContentQualityEvaluator, RelevanceImpactEvaluator
from .test_data.models import TestCase, EvaluationResult
from .results.aggregator import ResultAggregator
from .results.analyzer import PerformanceAnalyzer
from .results.reporter import EvaluationReporter
# from .config import EvaluationConfig  # Will be used when config is needed
from .utils.logger import get_evaluation_logger
from app.core.resilience import evaluation_circuit_breaker


class PipelineMode(Enum):
    """Pipeline execution modes."""
    QUICK = "quick"              # Essential evaluators only
    COMPREHENSIVE = "comprehensive"  # All evaluators  
    CUSTOM = "custom"           # User-defined set
    ACCURACY_FOCUSED = "accuracy_focused"  # Accuracy evaluators only
    QUALITY_FOCUSED = "quality_focused"    # Quality evaluators only


class EvaluationStage(Enum):
    """Evaluation pipeline stages."""
    INITIALIZATION = "initialization"
    PRE_PROCESSING = "pre_processing"
    JOB_PARSING = "job_parsing"
    MATCH_SCORING = "match_scoring" 
    TRUTHFULNESS = "truthfulness"
    CONTENT_QUALITY = "content_quality"
    RELEVANCE_IMPACT = "relevance_impact"
    POST_PROCESSING = "post_processing"
    AGGREGATION = "aggregation"
    REPORTING = "reporting"
    COMPLETED = "completed"


@dataclass
class PipelineProgress:
    """Tracks progress through evaluation pipeline."""
    
    current_stage: EvaluationStage = EvaluationStage.INITIALIZATION
    stages_completed: Set[EvaluationStage] = field(default_factory=set)
    evaluators_completed: Set[str] = field(default_factory=set)
    total_evaluators: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    stage_start_time: datetime = field(default_factory=datetime.now)
    estimated_completion: Optional[datetime] = None
    
    def complete_stage(self, stage: EvaluationStage):
        """Mark a stage as completed."""
        self.stages_completed.add(stage)
        if stage == self.current_stage:
            self._advance_stage()
    
    def complete_evaluator(self, evaluator_name: str):
        """Mark an evaluator as completed."""
        self.evaluators_completed.add(evaluator_name)
    
    def _advance_stage(self):
        """Advance to next stage."""
        stages = list(EvaluationStage)
        current_index = stages.index(self.current_stage)
        if current_index < len(stages) - 1:
            self.current_stage = stages[current_index + 1]
            self.stage_start_time = datetime.now()
    
    def get_completion_percentage(self) -> float:
        """Get overall completion percentage."""
        if self.total_evaluators == 0:
            return 0.0
        return len(self.evaluators_completed) / self.total_evaluators * 100
    
    def estimate_completion_time(self) -> Optional[datetime]:
        """Estimate completion time based on current progress."""
        if len(self.evaluators_completed) == 0:
            return None
        
        elapsed = (datetime.now() - self.start_time).total_seconds()
        progress = self.get_completion_percentage() / 100
        
        if progress > 0:
            total_estimated = elapsed / progress
            remaining = total_estimated - elapsed
            return datetime.now() + timedelta(seconds=remaining)
        
        return None


@dataclass
class PipelineConfiguration:
    """Configuration for evaluation pipeline."""
    
    mode: PipelineMode = PipelineMode.COMPREHENSIVE
    evaluators: Optional[List[str]] = None  # Custom evaluator names for CUSTOM mode
    parallel_execution: bool = True
    max_concurrent_evaluators: int = 3
    fail_fast: bool = False
    save_intermediate_results: bool = True
    output_directory: Optional[Path] = None
    progress_callback: Optional[Callable[[PipelineProgress], None]] = None
    
    # Result aggregation settings
    weight_accuracy: float = 0.3
    weight_quality: float = 0.4
    weight_relevance: float = 0.3
    confidence_threshold: float = 0.7
    
    # Error recovery settings
    retry_failed_evaluators: bool = True
    max_retries: int = 2
    retry_delay: float = 1.0


@dataclass
class PipelineResult:
    """Complete result from evaluation pipeline."""
    
    pipeline_id: str
    test_case_id: str
    mode: PipelineMode
    start_time: datetime
    end_time: datetime
    total_duration: float = 0.0
    
    # Individual evaluator results
    evaluator_results: Dict[str, EvaluationResult] = field(default_factory=dict)
    failed_evaluators: Dict[str, str] = field(default_factory=dict)  # evaluator -> error
    
    # Aggregated metrics
    overall_score: float = 0.0
    confidence_score: float = 0.0
    category_scores: Dict[str, float] = field(default_factory=dict)
    
    # Detailed analysis
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    # Resource usage
    total_tokens_used: int = 0
    total_api_calls: int = 0
    total_execution_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "pipeline_id": self.pipeline_id,
            "test_case_id": self.test_case_id,
            "mode": self.mode.value,
            "timing": {
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat(),
                "total_duration": self.total_duration
            },
            "evaluator_results": {
                name: result.model_dump() for name, result in self.evaluator_results.items()
            },
            "failed_evaluators": self.failed_evaluators,
            "aggregated_scores": {
                "overall_score": self.overall_score,
                "confidence_score": self.confidence_score,
                "category_scores": self.category_scores
            },
            "analysis": {
                "strengths": self.strengths,
                "weaknesses": self.weaknesses,
                "recommendations": self.recommendations
            },
            "resource_usage": {
                "total_tokens": self.total_tokens_used,
                "total_api_calls": self.total_api_calls,
                "total_execution_time": self.total_execution_time
            }
        }


class EvaluationPipeline:
    """
    Orchestrates evaluation workflows combining all evaluators.
    
    Provides a high-level interface for running comprehensive evaluations
    with result aggregation, progress tracking, and error recovery.
    """
    
    def __init__(self, config: Optional[PipelineConfiguration] = None):
        """
        Initialize evaluation pipeline.
        
        Args:
            config: Pipeline configuration
        """
        self.config = config or PipelineConfiguration()
        self.logger = get_evaluation_logger("EvaluationPipeline")
        
        # Initialize evaluators based on mode
        self.evaluators = self._initialize_evaluators()
        
        # Initialize result processing components
        self.aggregator = ResultAggregator()
        self.analyzer = PerformanceAnalyzer([])
        self.reporter = EvaluationReporter([])
        
        # Progress tracking
        self.progress = PipelineProgress(total_evaluators=len(self.evaluators))
    
    def _initialize_evaluators(self) -> Dict[str, BaseEvaluator]:
        """Initialize evaluators based on configuration mode."""
        evaluators = {}
        
        if self.config.mode == PipelineMode.QUICK:
            # Essential evaluators for quick feedback
            evaluators["job_parsing_accuracy"] = JobParsingAccuracyEvaluator()
            evaluators["match_score"] = MatchScoreEvaluator()
            evaluators["content_quality"] = ContentQualityEvaluator()
            
        elif self.config.mode == PipelineMode.COMPREHENSIVE:
            # All available evaluators
            evaluators["job_parsing_accuracy"] = JobParsingAccuracyEvaluator()
            evaluators["match_score"] = MatchScoreEvaluator()
            evaluators["truthfulness"] = TruthfulnessEvaluator()
            evaluators["content_quality"] = ContentQualityEvaluator()
            evaluators["relevance_impact"] = RelevanceImpactEvaluator()
            
        elif self.config.mode == PipelineMode.ACCURACY_FOCUSED:
            # Focus on accuracy metrics
            evaluators["job_parsing_accuracy"] = JobParsingAccuracyEvaluator()
            evaluators["match_score"] = MatchScoreEvaluator()
            
        elif self.config.mode == PipelineMode.QUALITY_FOCUSED:
            # Focus on quality metrics
            evaluators["truthfulness"] = TruthfulnessEvaluator()
            evaluators["content_quality"] = ContentQualityEvaluator()
            evaluators["relevance_impact"] = RelevanceImpactEvaluator()
            
        elif self.config.mode == PipelineMode.CUSTOM:
            # User-defined evaluator set
            available_evaluators = {
                "job_parsing_accuracy": JobParsingAccuracyEvaluator,
                "match_score": MatchScoreEvaluator,
                "truthfulness": TruthfulnessEvaluator,
                "content_quality": ContentQualityEvaluator,
                "relevance_impact": RelevanceImpactEvaluator
            }
            
            for evaluator_name in (self.config.evaluators or []):
                if evaluator_name in available_evaluators:
                    evaluators[evaluator_name] = available_evaluators[evaluator_name]()
                else:
                    self.logger.warning(f"Unknown evaluator: {evaluator_name}")
        
        self.logger.info(f"Initialized {len(evaluators)} evaluators for {self.config.mode.value} mode")
        return evaluators
    
    async def evaluate(
        self,
        test_case: TestCase,
        actual_output: Any,
        pipeline_id: Optional[str] = None
    ) -> PipelineResult:
        """
        Run complete evaluation pipeline on a test case.
        
        Args:
            test_case: Test case to evaluate
            actual_output: Actual system output to evaluate
            pipeline_id: Optional pipeline identifier
            
        Returns:
            Complete pipeline result with aggregated metrics
        """
        pipeline_id = pipeline_id or f"pipeline_{int(time.time())}"
        start_time = datetime.now()
        
        self.logger.info(f"Starting pipeline {pipeline_id} for test case {test_case.id}")
        
        # Initialize progress tracking
        self.progress = PipelineProgress(total_evaluators=len(self.evaluators))
        self.progress.current_stage = EvaluationStage.INITIALIZATION
        
        # Initialize result
        result = PipelineResult(
            pipeline_id=pipeline_id,
            test_case_id=test_case.id,
            mode=self.config.mode,
            start_time=start_time,
            end_time=start_time  # Will be updated
        )
        
        try:
            # Stage 1: Pre-processing
            await self._run_preprocessing_stage(test_case, actual_output)
            
            # Stage 2: Run evaluators
            await self._run_evaluation_stage(test_case, actual_output, result)
            
            # Stage 3: Aggregate results
            await self._run_aggregation_stage(result)
            
            # Stage 4: Generate analysis and recommendations
            await self._run_analysis_stage(result)
            
            # Stage 5: Save results if configured
            if self.config.save_intermediate_results and self.config.output_directory:
                await self._save_pipeline_result(result)
            
            self.progress.complete_stage(EvaluationStage.COMPLETED)
            
        except Exception as e:
            self.logger.error(f"Pipeline {pipeline_id} failed: {str(e)}")
            if self.config.fail_fast:
                raise
        
        finally:
            # Finalize result
            result.end_time = datetime.now()
            result.total_duration = (result.end_time - result.start_time).total_seconds()
            
            # Update progress callback if provided
            if self.config.progress_callback:
                self.config.progress_callback(self.progress)
        
        self.logger.info(
            f"Pipeline {pipeline_id} completed in {result.total_duration:.2f}s. "
            f"Overall score: {result.overall_score:.3f}"
        )
        
        return result
    
    async def _run_preprocessing_stage(self, test_case: TestCase, actual_output: Any):
        """Run preprocessing stage."""
        self.progress.current_stage = EvaluationStage.PRE_PROCESSING
        
        # Validate inputs
        for evaluator in self.evaluators.values():
            try:
                evaluator.validate_inputs(test_case, actual_output)
            except Exception as e:
                self.logger.warning(f"Input validation failed for {evaluator.name}: {str(e)}")
                if self.config.fail_fast:
                    raise
        
        self.progress.complete_stage(EvaluationStage.PRE_PROCESSING)
    
    async def _run_evaluation_stage(
        self,
        test_case: TestCase,
        actual_output: Any,
        result: PipelineResult
    ):
        """Run all evaluators in parallel or sequential mode."""
        self.logger.info(f"Running {len(self.evaluators)} evaluators")
        
        if self.config.parallel_execution:
            await self._run_evaluators_parallel(test_case, actual_output, result)
        else:
            await self._run_evaluators_sequential(test_case, actual_output, result)
    
    async def _run_evaluators_parallel(
        self,
        test_case: TestCase,
        actual_output: Any,
        result: PipelineResult
    ):
        """Run evaluators in parallel with concurrency control."""
        semaphore = asyncio.Semaphore(self.config.max_concurrent_evaluators)
        
        async def run_evaluator_with_semaphore(name: str, evaluator: BaseEvaluator):
            async with semaphore:
                return await self._run_single_evaluator(name, evaluator, test_case, actual_output)
        
        # Create tasks for all evaluators
        tasks = [
            run_evaluator_with_semaphore(name, evaluator)
            for name, evaluator in self.evaluators.items()
        ]
        
        # Wait for all evaluators to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for i, (name, evaluator) in enumerate(self.evaluators.items()):
            eval_result = results[i]
            
            if isinstance(eval_result, Exception):
                error_msg = str(eval_result)
                self.logger.error(f"Evaluator {name} failed: {error_msg}")
                result.failed_evaluators[name] = error_msg
                
                # Retry if configured
                if self.config.retry_failed_evaluators:
                    eval_result = await self._retry_evaluator(name, evaluator, test_case, actual_output)
                    if eval_result and not isinstance(eval_result, Exception):
                        result.evaluator_results[name] = eval_result
                        self._update_result_metrics(result, eval_result)
            else:
                result.evaluator_results[name] = eval_result
                self._update_result_metrics(result, eval_result)
            
            self.progress.complete_evaluator(name)
    
    async def _run_evaluators_sequential(
        self,
        test_case: TestCase,
        actual_output: Any,
        result: PipelineResult
    ):
        """Run evaluators sequentially."""
        for name, evaluator in self.evaluators.items():
            try:
                eval_result = await self._run_single_evaluator(name, evaluator, test_case, actual_output)
                result.evaluator_results[name] = eval_result
                self._update_result_metrics(result, eval_result)
                
            except Exception as e:
                error_msg = str(e)
                self.logger.error(f"Evaluator {name} failed: {error_msg}")
                result.failed_evaluators[name] = error_msg
                
                if self.config.fail_fast:
                    raise
            
            self.progress.complete_evaluator(name)
    
    async def _run_single_evaluator(
        self,
        name: str,
        evaluator: BaseEvaluator,
        test_case: TestCase,
        actual_output: Any
    ) -> EvaluationResult:
        """Run a single evaluator with error handling."""
        self.logger.debug(f"Running evaluator: {name}")

        if await evaluation_circuit_breaker.is_open(name):
            raise RuntimeError(f"Circuit open for {name}")

        start_time = time.time()
        try:
            eval_result = await evaluator.evaluate(test_case, actual_output)
            await evaluation_circuit_breaker.record_success(name)
        except Exception:
            await evaluation_circuit_breaker.record_failure(name)
            raise
        execution_time = time.time() - start_time
        
        # Update execution time if not set
        if eval_result.execution_time == 0:
            eval_result.execution_time = execution_time
        
        self.logger.debug(f"Evaluator {name} completed in {execution_time:.2f}s")
        return eval_result
    
    async def _retry_evaluator(
        self,
        name: str,
        evaluator: BaseEvaluator,
        test_case: TestCase,
        actual_output: Any
    ) -> Optional[EvaluationResult]:
        """Retry a failed evaluator."""
        for attempt in range(self.config.max_retries):
            self.logger.info(f"Retrying evaluator {name}, attempt {attempt + 1}/{self.config.max_retries}")

            try:
                await asyncio.sleep(self.config.retry_delay * (2 ** attempt))
                return await self._run_single_evaluator(name, evaluator, test_case, actual_output)
                
            except Exception as e:
                self.logger.warning(f"Retry {attempt + 1} failed for {name}: {str(e)}")
                if attempt == self.config.max_retries - 1:
                    self.logger.error(f"All retries exhausted for evaluator {name}")
                    await evaluation_circuit_breaker.record_failure(name)
        
        return None
    
    def _update_result_metrics(self, result: PipelineResult, eval_result: EvaluationResult):
        """Update pipeline result with evaluator metrics."""
        result.total_tokens_used += eval_result.tokens_used
        result.total_api_calls += eval_result.api_calls_made
        result.total_execution_time += eval_result.execution_time
    
    async def _run_aggregation_stage(self, result: PipelineResult):
        """Aggregate results from all evaluators."""
        self.progress.current_stage = EvaluationStage.AGGREGATION
        
        if not result.evaluator_results:
            self.logger.warning("No evaluator results to aggregate")
            self.progress.complete_stage(EvaluationStage.AGGREGATION)
            return
        
        # Calculate weighted overall score
        total_weight = 0.0
        weighted_score = 0.0
        
        for name, eval_result in result.evaluator_results.items():
            weight = self._get_evaluator_weight(name)
            weighted_score += eval_result.overall_score * weight
            total_weight += weight
        
        if total_weight > 0:
            result.overall_score = weighted_score / total_weight
        
        # Calculate category scores
        result.category_scores = self._calculate_category_scores(result.evaluator_results)
        
        # Calculate confidence score based on agreement between evaluators
        result.confidence_score = self._calculate_confidence_score(result.evaluator_results)
        
        self.progress.complete_stage(EvaluationStage.AGGREGATION)
    
    def _get_evaluator_weight(self, evaluator_name: str) -> float:
        """Get weight for an evaluator based on configuration."""
        weights = {
            "job_parsing_accuracy": self.config.weight_accuracy,
            "match_score": self.config.weight_accuracy,
            "truthfulness": self.config.weight_quality,
            "content_quality": self.config.weight_quality,
            "relevance_impact": self.config.weight_relevance
        }
        return weights.get(evaluator_name, 1.0)
    
    def _calculate_category_scores(self, evaluator_results: Dict[str, EvaluationResult]) -> Dict[str, float]:
        """Calculate category-wise scores."""
        categories = {
            "accuracy": ["job_parsing_accuracy", "match_score"],
            "quality": ["truthfulness", "content_quality"],
            "relevance": ["relevance_impact"]
        }
        
        category_scores = {}
        
        for category, evaluator_names in categories.items():
            scores = []
            for name in evaluator_names:
                if name in evaluator_results:
                    scores.append(evaluator_results[name].overall_score)
            
            if scores:
                category_scores[category] = sum(scores) / len(scores)
            else:
                category_scores[category] = 0.0
        
        return category_scores
    
    def _calculate_confidence_score(self, evaluator_results: Dict[str, EvaluationResult]) -> float:
        """Calculate confidence score based on evaluator agreement."""
        if len(evaluator_results) < 2:
            return 1.0
        
        scores = [result.overall_score for result in evaluator_results.values()]
        
        # Calculate coefficient of variation (lower = higher confidence)
        mean_score = sum(scores) / len(scores)
        if mean_score == 0:
            return 0.0
        
        variance = sum((score - mean_score) ** 2 for score in scores) / len(scores)
        std_dev = variance ** 0.5
        coefficient_of_variation = std_dev / mean_score
        
        # Convert to confidence score (0-1, higher is better)
        confidence = max(0.0, 1.0 - coefficient_of_variation)
        return min(1.0, confidence)
    
    async def _run_analysis_stage(self, result: PipelineResult):
        """Generate analysis and recommendations."""
        self.progress.current_stage = EvaluationStage.POST_PROCESSING
        
        # Analyze strengths
        result.strengths = self._identify_strengths(result)
        
        # Analyze weaknesses
        result.weaknesses = self._identify_weaknesses(result)
        
        # Generate recommendations
        result.recommendations = self._generate_recommendations(result)
        
        self.progress.complete_stage(EvaluationStage.POST_PROCESSING)
    
    def _identify_strengths(self, result: PipelineResult) -> List[str]:
        """Identify strengths based on evaluator results."""
        strengths = []
        
        for name, eval_result in result.evaluator_results.items():
            if eval_result.overall_score >= 0.8:
                strengths.append(f"High {name.replace('_', ' ')} score ({eval_result.overall_score:.2f})")
                
                # Add specific strengths from detailed scores
                for metric, score in eval_result.detailed_scores.items():
                    if score >= 0.9:
                        strengths.append(f"Excellent {metric.replace('_', ' ')} ({score:.2f})")
        
        return strengths
    
    def _identify_weaknesses(self, result: PipelineResult) -> List[str]:
        """Identify weaknesses based on evaluator results."""
        weaknesses = []
        
        for name, eval_result in result.evaluator_results.items():
            if eval_result.overall_score < 0.6:
                weaknesses.append(f"Low {name.replace('_', ' ')} score ({eval_result.overall_score:.2f})")
                
                # Add specific weaknesses from detailed scores
                for metric, score in eval_result.detailed_scores.items():
                    if score < 0.5:
                        weaknesses.append(f"Poor {metric.replace('_', ' ')} ({score:.2f})")
        
        # Add failed evaluators as weaknesses
        for name, error in result.failed_evaluators.items():
            weaknesses.append(f"Failed {name.replace('_', ' ')} evaluation: {error}")
        
        return weaknesses
    
    def _generate_recommendations(self, result: PipelineResult) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        # Accuracy recommendations
        if "accuracy" in result.category_scores and result.category_scores["accuracy"] < 0.7:
            recommendations.append("Improve job requirement parsing accuracy")
            recommendations.append("Enhance skill extraction and normalization")
        
        # Quality recommendations
        if "quality" in result.category_scores and result.category_scores["quality"] < 0.7:
            recommendations.append("Review content for truthfulness and authenticity")
            recommendations.append("Improve professional language and ATS compatibility")
        
        # Relevance recommendations
        if "relevance" in result.category_scores and result.category_scores["relevance"] < 0.7:
            recommendations.append("Improve relevance by better aligning resume content with job requirements")
            recommendations.append("Enhance keyword optimization and targeting for better relevance")
        
        # Low confidence recommendations
        if result.confidence_score < self.config.confidence_threshold:
            recommendations.append("Results show low confidence - consider manual review")
            recommendations.append("Evaluator disagreement suggests edge case - investigate further")
        
        return recommendations
    
    async def _save_pipeline_result(self, result: PipelineResult):
        """Save pipeline result to file."""
        if not self.config.output_directory:
            return
        
        self.config.output_directory.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"pipeline_result_{result.pipeline_id}_{timestamp}.json"
        filepath = self.config.output_directory / filename
        
        with open(filepath, 'w') as f:
            json.dump(result.to_dict(), f, indent=2)
        
        self.logger.info(f"Pipeline result saved to: {filepath}")
    
    def get_available_evaluators(self) -> List[str]:
        """Get list of available evaluator names."""
        return [
            "job_parsing_accuracy",
            "match_score", 
            "truthfulness",
            "content_quality",
            "relevance_impact"
        ]
    
    def get_evaluator_descriptions(self) -> Dict[str, str]:
        """Get descriptions of all available evaluators."""
        return {
            "job_parsing_accuracy": "Evaluates precision and recall of job requirement extraction",
            "match_score": "Analyzes correlation and consistency of resume-job match scoring",
            "truthfulness": "Verifies content authenticity and detects fabrication",
            "content_quality": "Assesses readability, professionalism, and ATS compatibility",
            "relevance_impact": "Measures optimization effectiveness and targeting improvements"
        }


