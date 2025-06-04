# ABOUTME: API endpoints for evaluation pipeline integration
# ABOUTME: Provides REST endpoints for running evaluations and retrieving results

"""
Evaluation API Endpoints

REST API endpoints for the evaluation pipeline system, providing access to
quick and comprehensive evaluation suites with real-time progress tracking.
"""

from typing import List, Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query, status, Request
from fastapi.responses import JSONResponse

from app.services.evaluation_service import (
    EvaluationService,
    EvaluationRequest,
    EvaluationResponse,
    EvaluationStatus
)
from evaluation.pipeline import PipelineMode
from evaluation.suites.quick_suite import QuickEvaluationSuite
from evaluation.suites.comprehensive_suite import ComprehensiveEvaluationSuite
from app.core.logging import get_logger
from app.core.resilience import evaluation_rate_limiter, RateLimitExceeded

logger = get_logger("EvaluationAPI")

# Initialize router
router = APIRouter(prefix="/evaluation", tags=["evaluation"])

# Initialize services
evaluation_service = EvaluationService()
quick_suite = QuickEvaluationSuite()
comprehensive_suite = ComprehensiveEvaluationSuite()


async def rate_limit(request: Request) -> None:
    client_ip = request.client.host if request.client else "anonymous"
    if not await evaluation_rate_limiter.allow(client_ip):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")


def get_evaluation_service() -> EvaluationService:
    """Dependency to get evaluation service."""
    return evaluation_service


@router.post("/evaluate", response_model=EvaluationResponse)
async def start_evaluation(
    request: EvaluationRequest,
    background_tasks: BackgroundTasks,
    service: EvaluationService = Depends(get_evaluation_service),
    _: None = Depends(rate_limit),
):
    """
    Start a new evaluation pipeline.
    
    This endpoint starts an evaluation pipeline that can run in either
    synchronous or asynchronous mode based on the request parameters.
    """
    try:
        logger.info(f"Starting evaluation in {request.mode.value} mode")
        
        # Start evaluation (async by default)
        evaluation_id = await service.start_evaluation(request, background_tasks, http_request=request)
        
        # Return immediate response with evaluation ID
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "evaluation_id": evaluation_id,
                "status": "started",
                "message": f"Evaluation started in {request.mode.value} mode",
                "check_status_url": f"/evaluation/{evaluation_id}/status"
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to start evaluation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start evaluation: {str(e)}"
        )


@router.get("/{evaluation_id}/status", response_model=EvaluationStatus)
async def get_evaluation_status(
    evaluation_id: str,
    service: EvaluationService = Depends(get_evaluation_service)
):
    """
    Get the status of an ongoing evaluation.
    
    Returns current progress, stage information, and estimated completion time
    for evaluations that are still running.
    """
    try:
        status = await service.get_evaluation_status(evaluation_id)
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get evaluation status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get evaluation status: {str(e)}"
        )


@router.get("/{evaluation_id}/result", response_model=EvaluationResponse)
async def get_evaluation_result(
    evaluation_id: str,
    include_detailed_scores: bool = Query(True, description="Include detailed evaluator scores"),
    include_recommendations: bool = Query(True, description="Include analysis and recommendations"),
    service: EvaluationService = Depends(get_evaluation_service)
):
    """
    Get the results of a completed evaluation.
    
    Returns comprehensive evaluation results including scores, analysis,
    and recommendations based on the specified inclusion parameters.
    """
    try:
        result = await service.get_evaluation_result(
            evaluation_id,
            include_detailed_scores,
            include_recommendations
        )
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get evaluation result: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get evaluation result: {str(e)}"
        )


@router.post("/quick", response_model=dict)
async def quick_evaluation(
    resume_content: str,
    job_description: str,
    test_case_id: Optional[str] = None,
    _: None = Depends(rate_limit)
):
    """
    Run a quick evaluation for rapid feedback.
    
    Provides fast evaluation results using essential evaluators optimized
    for development workflows and rapid iteration.
    """
    try:
        logger.info("Starting quick evaluation")
        
        result = await quick_suite.evaluate_single(
            resume_content=resume_content,
            job_description=job_description,
            test_case_id=test_case_id
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Quick evaluation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Quick evaluation failed: {str(e)}"
        )


@router.post("/quick/batch", response_model=dict)
async def quick_batch_evaluation(
    resume_job_pairs: List[dict],
    batch_id: Optional[str] = None,
    _: None = Depends(rate_limit)
):
    """
    Run quick evaluation on a batch of resume-job pairs.
    
    Efficiently processes multiple resume-job combinations with
    aggregate metrics and batch-level analysis.
    """
    try:
        logger.info(f"Starting quick batch evaluation with {len(resume_job_pairs)} pairs")
        
        # Validate input format
        for i, pair in enumerate(resume_job_pairs):
            if "resume" not in pair or "job" not in pair:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Pair {i+1} missing required 'resume' or 'job' fields"
                )
        
        result = await quick_suite.evaluate_batch(
            resume_job_pairs=resume_job_pairs,
            batch_id=batch_id
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Quick batch evaluation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Quick batch evaluation failed: {str(e)}"
        )


@router.post("/comprehensive", response_model=dict)
async def comprehensive_evaluation(
    resume_content: str,
    job_description: str,
    test_case_id: Optional[str] = None,
    include_detailed_analysis: bool = Query(True, description="Include detailed analysis"),
    _: None = Depends(rate_limit)
):
    """
    Run a comprehensive evaluation with detailed analysis.
    
    Provides thorough evaluation using all available evaluators with
    extensive analysis, quality assurance, and detailed reporting.
    """
    try:
        logger.info("Starting comprehensive evaluation")
        
        result = await comprehensive_suite.evaluate_comprehensive(
            resume_content=resume_content,
            job_description=job_description,
            test_case_id=test_case_id,
            include_detailed_analysis=include_detailed_analysis
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Comprehensive evaluation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Comprehensive evaluation failed: {str(e)}"
        )


@router.post("/optimization-impact", response_model=dict)
async def evaluate_optimization_impact(
    original_resume: str,
    optimized_resume: str,
    job_description: str,
    optimization_metadata: Optional[dict] = None,
    _: None = Depends(rate_limit)
):
    """
    Evaluate the impact of resume optimization.
    
    Analyzes the effectiveness of resume optimization by comparing
    before and after versions with comprehensive impact metrics.
    """
    try:
        logger.info("Starting optimization impact evaluation")
        
        result = await comprehensive_suite.evaluate_optimization_impact(
            original_resume=original_resume,
            optimized_resume=optimized_resume,
            job_description=job_description,
            optimization_metadata=optimization_metadata
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Optimization impact evaluation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Optimization impact evaluation failed: {str(e)}"
        )


@router.post("/haiku-integration/evaluate")
async def evaluate_with_haiku_optimizer(
    original_resume: str,
    optimized_resume: str,
    job_description: str,
    mode: PipelineMode = PipelineMode.COMPREHENSIVE,
    _: None = Depends(rate_limit)
):
    """
    Integration endpoint for HaikuResumeOptimizer evaluation.
    
    This endpoint is specifically designed to integrate with the
    HaikuResumeOptimizer workflow for seamless evaluation.
    """
    try:
        logger.info("Starting HaikuResumeOptimizer integration evaluation")
        
        result = await evaluation_service.evaluate_optimization_result(
            original_resume=original_resume,
            optimized_resume=optimized_resume,
            job_description=job_description,
            mode=mode
        )
        
        return result
        
    except Exception as e:
        logger.error(f"HaikuResumeOptimizer integration evaluation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evaluation failed: {str(e)}"
        )


@router.get("/evaluators", response_model=dict)
async def get_available_evaluators():
    """
    Get information about available evaluators.
    
    Returns details about all available evaluators including their
    descriptions, capabilities, and typical use cases.
    """
    try:
        # Get evaluator information from different sources
        pipeline_evaluators = evaluation_service.active_evaluations  # Example - would get from pipeline
        quick_evaluators = quick_suite.get_evaluator_info()
        comprehensive_capabilities = comprehensive_suite.get_suite_capabilities()
        
        return {
            "available_evaluators": {
                "job_parsing_accuracy": "Evaluates precision and recall of job requirement extraction",
                "match_score": "Analyzes correlation and consistency of resume-job match scoring",
                "truthfulness": "Verifies content authenticity and detects fabrication",
                "content_quality": "Assesses readability, professionalism, and ATS compatibility",
                "relevance_impact": "Measures optimization effectiveness and targeting improvements"
            },
            "evaluation_modes": {
                "quick": {
                    "evaluators": list(quick_evaluators.keys()),
                    "description": "Fast evaluation for development feedback",
                    "typical_duration": "5-15 seconds"
                },
                "comprehensive": {
                    "evaluators": comprehensive_capabilities["evaluators"],
                    "description": "Thorough evaluation for production assessment",
                    "typical_duration": "30-120 seconds"
                },
                "accuracy_focused": {
                    "evaluators": ["job_parsing_accuracy", "match_score"],
                    "description": "Focus on accuracy metrics",
                    "typical_duration": "10-30 seconds"
                },
                "quality_focused": {
                    "evaluators": ["truthfulness", "content_quality", "relevance_impact"],
                    "description": "Focus on quality metrics",
                    "typical_duration": "20-60 seconds"
                }
            },
            "suite_capabilities": {
                "quick_suite": quick_suite.get_configuration_summary(),
                "comprehensive_suite": comprehensive_capabilities
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get evaluator information: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get evaluator information: {str(e)}"
        )


@router.get("/history", response_model=dict)
async def get_evaluation_history(
    limit: int = Query(50, ge=1, le=500, description="Number of recent evaluations to return"),
    service: EvaluationService = Depends(get_evaluation_service)
):
    """
    Get recent evaluation history.
    
    Returns a list of recent evaluations with basic metrics for
    analytics and performance tracking.
    """
    try:
        history = service.get_evaluation_history(limit)
        return {"evaluation_history": history}
        
    except Exception as e:
        logger.error(f"Failed to get evaluation history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get evaluation history: {str(e)}"
        )


@router.get("/metrics", response_model=dict)
async def get_performance_metrics(
    service: EvaluationService = Depends(get_evaluation_service)
):
    """
    Get performance metrics for the evaluation system.
    
    Returns aggregate metrics including average scores, duration statistics,
    and system performance indicators.
    """
    try:
        metrics = service.get_performance_metrics()
        return metrics
        
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get performance metrics: {str(e)}"
        )


@router.get("/health", response_model=dict)
async def health_check():
    """
    Health check endpoint for the evaluation system.
    
    Returns system status and availability of evaluation components.
    """
    try:
        # Check if evaluators can be initialized
        from evaluation.evaluators.accuracy import JobParsingAccuracyEvaluator
        from evaluation.evaluators.quality import ContentQualityEvaluator
        
        test_evaluator = JobParsingAccuracyEvaluator()
        
        health_status = {
            "status": "healthy",
            "timestamp": str(datetime.now()),
            "components": {
                "evaluation_service": "operational",
                "quick_suite": "operational",
                "comprehensive_suite": "operational",
                "evaluators": "operational"
            },
            "version": "1.0.0"
        }
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "timestamp": str(datetime.now()),
                "error": str(e)
            }
        )


# Import required for datetime
from datetime import datetime