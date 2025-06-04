# ABOUTME: Service layer for evaluation pipeline integration with resume optimization
# ABOUTME: Provides API endpoints and business logic for running evaluation pipelines

"""
Evaluation Service

Service layer that integrates the evaluation pipeline with the existing
resume optimization workflow, providing API endpoints and business logic.
"""

import asyncio
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass

from fastapi import HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from evaluation.pipeline import EvaluationPipeline, PipelineConfiguration, PipelineMode, PipelineResult
from evaluation.test_data.models import TestCase
from app.core.logging import get_logger


class EvaluationRequest(BaseModel):
    """Request model for evaluation."""
    
    resume_content: str = Field(..., description="Resume content to evaluate")
    job_description: str = Field(..., description="Job description to match against")
    mode: PipelineMode = Field(PipelineMode.COMPREHENSIVE, description="Evaluation mode")
    custom_evaluators: Optional[List[str]] = Field(None, description="Custom evaluator list for CUSTOM mode")
    
    # Pipeline configuration options
    parallel_execution: bool = Field(True, description="Run evaluators in parallel")
    max_concurrent_evaluators: int = Field(3, description="Maximum concurrent evaluators")
    fail_fast: bool = Field(False, description="Stop on first evaluator failure")
    
    # Result options
    save_results: bool = Field(True, description="Save results to disk")
    include_detailed_scores: bool = Field(True, description="Include detailed evaluator scores")
    include_recommendations: bool = Field(True, description="Include analysis and recommendations")


class EvaluationResponse(BaseModel):
    """Response model for evaluation."""
    
    evaluation_id: str
    test_case_id: str
    mode: str
    status: str
    
    # Timing
    start_time: str
    end_time: Optional[str] = None
    duration_seconds: Optional[float] = None
    
    # Scores
    overall_score: float
    confidence_score: float
    category_scores: Dict[str, float]
    
    # Results
    evaluator_results: Optional[Dict[str, Dict[str, Any]]] = None
    failed_evaluators: Optional[Dict[str, str]] = None
    
    # Analysis
    strengths: Optional[List[str]] = None
    weaknesses: Optional[List[str]] = None
    recommendations: Optional[List[str]] = None
    
    # Resource usage
    total_tokens_used: int = 0
    total_api_calls: int = 0


class EvaluationStatus(BaseModel):
    """Status model for ongoing evaluations."""
    
    evaluation_id: str
    status: str  # "running", "completed", "failed"
    progress_percentage: float
    current_stage: str
    evaluators_completed: List[str]
    estimated_completion: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class ActiveEvaluation:
    """Tracks an active evaluation."""
    
    evaluation_id: str
    pipeline: EvaluationPipeline
    task: asyncio.Task
    start_time: datetime
    status: str = "running"
    result: Optional[PipelineResult] = None
    error: Optional[str] = None


class EvaluationService:
    """
    Service for managing evaluation pipelines and integration with resume optimization.
    """
    
    def __init__(self, output_directory: Optional[Path] = None, max_history_size: Optional[int] = None):
        """
        Initialize evaluation service.

        Args:
            output_directory: Directory to save evaluation results
            max_history_size: Maximum number of results to keep in memory
        """
        self.logger = get_logger("EvaluationService")
        self.output_directory = output_directory or Path("evaluation_results")
        self.output_directory.mkdir(parents=True, exist_ok=True)

        # Set history size limit
        env_size = os.getenv("EVALUATION_HISTORY_SIZE")
        self.max_history_size = (
            max_history_size if max_history_size is not None else int(env_size) if env_size else 1000
        )
        
        # Track active evaluations
        self.active_evaluations: Dict[str, ActiveEvaluation] = {}
        
        # Performance tracking
        self.evaluation_history: List[Dict[str, Any]] = []
    
    async def start_evaluation(
        self,
        request: EvaluationRequest,
        background_tasks: Optional[BackgroundTasks] = None
    ) -> str:
        """
        Start an evaluation pipeline.
        
        Args:
            request: Evaluation request
            background_tasks: FastAPI background tasks (for async execution)
            
        Returns:
            Evaluation ID for tracking
        """
        evaluation_id = str(uuid.uuid4())
        
        self.logger.info(f"Starting evaluation {evaluation_id} in {request.mode.value} mode")
        
        # Create pipeline configuration
        config = PipelineConfiguration(
            mode=request.mode,
            evaluators=request.custom_evaluators,
            parallel_execution=request.parallel_execution,
            max_concurrent_evaluators=request.max_concurrent_evaluators,
            fail_fast=request.fail_fast,
            save_intermediate_results=request.save_results,
            output_directory=self.output_directory if request.save_results else None
        )
        
        # Create pipeline
        pipeline = EvaluationPipeline(config)
        
        # Create test case from request
        test_case = TestCase(
            id=f"eval_{evaluation_id}",
            name=f"Evaluation {evaluation_id}",
            resume_content=request.resume_content,
            job_description=request.job_description
        )
        
        # Create actual output for evaluation
        # In a real system, this would come from the resume optimization process
        actual_output = {
            "resume_content": request.resume_content,
            "job_description": request.job_description,
            "optimization_applied": False  # Indicates this is raw evaluation
        }
        
        # Start evaluation as background task
        if background_tasks:
            # Asynchronous execution
            task = asyncio.create_task(
                self._run_evaluation_pipeline(evaluation_id, pipeline, test_case, actual_output)
            )
            
            # Track active evaluation
            self.active_evaluations[evaluation_id] = ActiveEvaluation(
                evaluation_id=evaluation_id,
                pipeline=pipeline,
                task=task,
                start_time=datetime.now()
            )
            
            # Add cleanup task
            background_tasks.add_task(self._cleanup_completed_evaluation, evaluation_id)
            
        else:
            # Synchronous execution
            try:
                result = await self._run_evaluation_pipeline(evaluation_id, pipeline, test_case, actual_output)
                self._record_evaluation_history(evaluation_id, result)
                
            except Exception as e:
                self.logger.error(f"Evaluation {evaluation_id} failed: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")
        
        return evaluation_id
    
    async def _run_evaluation_pipeline(
        self,
        evaluation_id: str,
        pipeline: EvaluationPipeline,
        test_case: TestCase,
        actual_output: Any
    ) -> PipelineResult:
        """Run the evaluation pipeline."""
        try:
            self.logger.info(f"Executing pipeline for evaluation {evaluation_id}")
            
            result = await pipeline.evaluate(test_case, actual_output, evaluation_id)
            
            # Update active evaluation if tracking
            if evaluation_id in self.active_evaluations:
                self.active_evaluations[evaluation_id].result = result
                self.active_evaluations[evaluation_id].status = "completed"
            
            self._record_evaluation_history(evaluation_id, result)
            
            self.logger.info(f"Evaluation {evaluation_id} completed successfully")
            return result
            
        except Exception as e:
            self.logger.error(f"Evaluation {evaluation_id} failed: {str(e)}")
            
            # Update active evaluation if tracking
            if evaluation_id in self.active_evaluations:
                self.active_evaluations[evaluation_id].status = "failed"
                self.active_evaluations[evaluation_id].error = str(e)
            
            raise
    
    async def get_evaluation_status(self, evaluation_id: str) -> EvaluationStatus:
        """
        Get status of an ongoing or completed evaluation.
        
        Args:
            evaluation_id: Evaluation identifier
            
        Returns:
            Current evaluation status
        """
        if evaluation_id not in self.active_evaluations:
            raise HTTPException(status_code=404, detail=f"Evaluation {evaluation_id} not found")
        
        active_eval = self.active_evaluations[evaluation_id]
        
        # Get progress from pipeline
        progress = active_eval.pipeline.progress
        
        status = EvaluationStatus(
            evaluation_id=evaluation_id,
            status=active_eval.status,
            progress_percentage=progress.get_completion_percentage(),
            current_stage=progress.current_stage.value,
            evaluators_completed=list(progress.evaluators_completed),
            error_message=active_eval.error
        )
        
        # Add estimated completion if available
        if progress.estimated_completion:
            status.estimated_completion = progress.estimated_completion.isoformat()
        
        return status
    
    async def get_evaluation_result(
        self,
        evaluation_id: str,
        include_detailed_scores: bool = True,
        include_recommendations: bool = True
    ) -> EvaluationResponse:
        """
        Get results of a completed evaluation.
        
        Args:
            evaluation_id: Evaluation identifier
            include_detailed_scores: Include detailed evaluator scores
            include_recommendations: Include analysis and recommendations
            
        Returns:
            Evaluation results
        """
        # Check if evaluation is active
        if evaluation_id in self.active_evaluations:
            active_eval = self.active_evaluations[evaluation_id]
            
            if active_eval.status != "completed":
                raise HTTPException(
                    status_code=400,
                    detail=f"Evaluation {evaluation_id} is not completed (status: {active_eval.status})"
                )
            
            if not active_eval.result:
                raise HTTPException(status_code=500, detail="Evaluation completed but no result available")
            
            return self._format_evaluation_response(
                active_eval.result,
                include_detailed_scores,
                include_recommendations
            )
        
        # Check evaluation history
        for history_entry in self.evaluation_history:
            if history_entry["evaluation_id"] == evaluation_id:
                # Try to load result from disk
                result_file = self.output_directory / f"pipeline_result_{evaluation_id}*.json"
                result_files = list(self.output_directory.glob(f"pipeline_result_{evaluation_id}_*.json"))
                
                if result_files:
                    import json
                    with open(result_files[0], 'r') as f:
                        result_data = json.load(f)
                    
                    # Convert back to PipelineResult object for formatting
                    # This is a simplified approach - in production, you might want more robust serialization
                    return self._format_response_from_dict(
                        result_data,
                        include_detailed_scores,
                        include_recommendations
                    )
        
        raise HTTPException(status_code=404, detail=f"Evaluation {evaluation_id} not found")
    
    def _format_evaluation_response(
        self,
        result: PipelineResult,
        include_detailed_scores: bool,
        include_recommendations: bool
    ) -> EvaluationResponse:
        """Format pipeline result as evaluation response."""
        response = EvaluationResponse(
            evaluation_id=result.pipeline_id,
            test_case_id=result.test_case_id,
            mode=result.mode.value,
            status="completed",
            start_time=result.start_time.isoformat(),
            end_time=result.end_time.isoformat(),
            duration_seconds=result.total_duration,
            overall_score=result.overall_score,
            confidence_score=result.confidence_score,
            category_scores=result.category_scores,
            total_tokens_used=result.total_tokens_used,
            total_api_calls=result.total_api_calls
        )
        
        if include_detailed_scores:
            response.evaluator_results = {
                name: {
                    "overall_score": eval_result.overall_score,
                    "passed": eval_result.passed,
                    "detailed_scores": eval_result.detailed_scores,
                    "execution_time": eval_result.execution_time,
                    "notes": eval_result.notes
                }
                for name, eval_result in result.evaluator_results.items()
            }
            response.failed_evaluators = result.failed_evaluators
        
        if include_recommendations:
            response.strengths = result.strengths
            response.weaknesses = result.weaknesses
            response.recommendations = result.recommendations
        
        return response
    
    def _format_response_from_dict(
        self,
        result_data: Dict[str, Any],
        include_detailed_scores: bool,
        include_recommendations: bool
    ) -> EvaluationResponse:
        """Format response from saved result dictionary."""
        response = EvaluationResponse(
            evaluation_id=result_data["pipeline_id"],
            test_case_id=result_data["test_case_id"],
            mode=result_data["mode"],
            status="completed",
            start_time=result_data["timing"]["start_time"],
            end_time=result_data["timing"]["end_time"],
            duration_seconds=result_data["timing"]["total_duration"],
            overall_score=result_data["aggregated_scores"]["overall_score"],
            confidence_score=result_data["aggregated_scores"]["confidence_score"],
            category_scores=result_data["aggregated_scores"]["category_scores"],
            total_tokens_used=result_data["resource_usage"]["total_tokens"],
            total_api_calls=result_data["resource_usage"]["total_api_calls"]
        )
        
        if include_detailed_scores:
            response.evaluator_results = result_data.get("evaluator_results", {})
            response.failed_evaluators = result_data.get("failed_evaluators", {})
        
        if include_recommendations:
            response.strengths = result_data["analysis"].get("strengths", [])
            response.weaknesses = result_data["analysis"].get("weaknesses", [])
            response.recommendations = result_data["analysis"].get("recommendations", [])
        
        return response
    
    async def evaluate_optimization_result(
        self,
        original_resume: str,
        optimized_resume: str,
        job_description: str,
        mode: PipelineMode = PipelineMode.COMPREHENSIVE
    ) -> EvaluationResponse:
        """
        Evaluate the result of resume optimization.
        
        This method is specifically designed to integrate with HaikuResumeOptimizer
        to evaluate the effectiveness of optimization.
        
        Args:
            original_resume: Original resume content
            optimized_resume: Optimized resume content
            job_description: Job description used for optimization
            mode: Evaluation mode
            
        Returns:
            Evaluation results comparing optimization effectiveness
        """
        evaluation_id = str(uuid.uuid4())
        
        self.logger.info(f"Evaluating optimization result {evaluation_id}")
        
        # Create pipeline configuration for optimization evaluation
        config = PipelineConfiguration(
            mode=mode,
            parallel_execution=True,
            save_intermediate_results=True,
            output_directory=self.output_directory
        )
        
        pipeline = EvaluationPipeline(config)
        
        # Create test case
        test_case = TestCase(
            id=f"optimization_eval_{evaluation_id}",
            name=f"Optimization Evaluation {evaluation_id}",
            resume_content=original_resume,
            job_description=job_description
        )
        
        # Create actual output that includes both original and optimized content
        actual_output = {
            "resume_before": original_resume,
            "resume_after": optimized_resume,
            "job_description": job_description,
            "optimization_applied": True
        }
        
        try:
            result = await pipeline.evaluate(test_case, actual_output, evaluation_id)
            self._record_evaluation_history(evaluation_id, result)
            
            return self._format_evaluation_response(result, True, True)
            
        except Exception as e:
            self.logger.error(f"Optimization evaluation {evaluation_id} failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")
    
    def _record_evaluation_history(self, evaluation_id: str, result: PipelineResult):
        """Record evaluation in history for analytics."""
        self.evaluation_history.append({
            "evaluation_id": evaluation_id,
            "timestamp": datetime.now().isoformat(),
            "mode": result.mode.value,
            "overall_score": result.overall_score,
            "confidence_score": result.confidence_score,
            "duration": result.total_duration,
            "evaluators_used": list(result.evaluator_results.keys()),
            "failed_evaluators": list(result.failed_evaluators.keys())
        })
        
        # Keep only the most recent evaluations in memory
        if len(self.evaluation_history) > self.max_history_size:
            del self.evaluation_history[:-self.max_history_size]
    
    async def _cleanup_completed_evaluation(self, evaluation_id: str):
        """Clean up completed evaluation from active tracking."""
        await asyncio.sleep(300)  # Keep active for 5 minutes after completion
        
        if evaluation_id in self.active_evaluations:
            active_eval = self.active_evaluations[evaluation_id]
            if active_eval.status in ["completed", "failed"]:
                del self.active_evaluations[evaluation_id]
                self.logger.debug(f"Cleaned up evaluation {evaluation_id}")
    
    def get_evaluation_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent evaluation history."""
        return self.evaluation_history[-limit:]
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for evaluations."""
        if not self.evaluation_history:
            return {"message": "No evaluation history available"}
        
        recent_evaluations = self.evaluation_history[-100:]  # Last 100 evaluations
        
        total_evaluations = len(recent_evaluations)
        avg_score = sum(e["overall_score"] for e in recent_evaluations) / total_evaluations
        avg_confidence = sum(e["confidence_score"] for e in recent_evaluations) / total_evaluations
        avg_duration = sum(e["duration"] for e in recent_evaluations) / total_evaluations
        
        mode_distribution = {}
        for eval_data in recent_evaluations:
            mode = eval_data["mode"]
            mode_distribution[mode] = mode_distribution.get(mode, 0) + 1
        
        return {
            "total_evaluations": total_evaluations,
            "average_overall_score": avg_score,
            "average_confidence_score": avg_confidence,
            "average_duration_seconds": avg_duration,
            "mode_distribution": mode_distribution,
            "active_evaluations": len(self.active_evaluations)
        }