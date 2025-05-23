"""
API endpoints for model usage statistics, cost data, and request monitoring.

This module provides endpoints for accessing:
- Model usage and cost data
- Request statistics and performance metrics
- Server health and monitoring data
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from pydantic import BaseModel

from app.core.security import get_current_active_superuser, get_current_user
from app.models.user import User

# Import model optimizer functions
try:
    from app.services.model_optimizer import (
        BUDGET_LIMITS,
        get_circuit_breaker_status,
        get_cost_report,
        reset_circuit_breaker,
        reset_cost_tracking,
    )

    MODEL_OPTIMIZER_AVAILABLE = True
except ImportError:
    MODEL_OPTIMIZER_AVAILABLE = False

# Import smart request handler functions
try:
    from app.services.smart_request_handler import (
        get_request_statistics,
        get_request_status,
        request_tracker,
    )

    SMART_REQUEST_AVAILABLE = True
except ImportError:
    SMART_REQUEST_AVAILABLE = False

# Define router
router = APIRouter()


# Define response models
class ModelUsageStats(BaseModel):
    """Statistics for a specific model's usage."""

    model: str
    total_tokens: int
    input_tokens: int = 0
    output_tokens: int = 0
    total_cost: float
    request_count: int = 0
    provider: Optional[str] = None
    tier: Optional[str] = None


class TaskUsageStats(BaseModel):
    """Statistics for a specific task type."""

    task_name: str
    total_tokens: int
    total_cost: float
    request_count: int
    models_used: Dict[str, Dict[str, Any]]


class BudgetStatus(BaseModel):
    """Budget status information."""

    daily_cost: float
    monthly_cost: float
    daily_budget: float
    monthly_budget: float
    daily_percent: float
    monthly_percent: float
    daily_status: str
    monthly_status: str
    overall_status: str


class CostReportData(BaseModel):
    """Complete cost report data."""

    total_tokens: int
    total_cost: float
    models: Dict[str, Dict[str, Any]]
    tasks: Dict[str, Dict[str, Any]]
    recent_requests: List[Dict[str, Any]]
    timestamp: float
    date: Optional[str] = None
    budget_limits: Dict[str, float]
    budget_status: BudgetStatus


class CircuitBreakerStatus(BaseModel):
    """Circuit breaker status information."""

    failure_counts: Dict[str, int]
    circuit_open_until: Dict[str, str]
    open_circuits: Dict[str, bool]
    failure_threshold: int
    recovery_time_seconds: float
    timestamp: str


class CircuitBreakerResetRequest(BaseModel):
    """Request to reset a circuit breaker."""

    provider: Optional[str] = None


class CircuitBreakerResetResponse(BaseModel):
    """Response for circuit breaker reset."""

    status: str
    message: str
    provider: Optional[str] = None


# Endpoint to get usage statistics
@router.get("/usage", response_model=CostReportData)
async def get_usage_statistics(
    current_user: User = Depends(get_current_active_superuser),
) -> Dict[str, Any]:
    """
    Get detailed usage statistics and cost data.

    Only accessible to superusers.
    """
    if not MODEL_OPTIMIZER_AVAILABLE:
        raise HTTPException(
            status_code=501, detail="Model optimizer module is not available"
        )

    # Get cost report
    report = get_cost_report()

    # Convert to response model format
    response_data = {
        "total_tokens": report["total_tokens"],
        "total_cost": report["total_cost"],
        "models": report["models"],
        "tasks": report["tasks"],
        "recent_requests": report.get("recent_requests", []),
        "timestamp": report["timestamp"],
        "date": datetime.fromtimestamp(report["timestamp"]).isoformat()
        if "timestamp" in report
        else None,
        "budget_limits": report.get("budget_limits", BUDGET_LIMITS),
        "budget_status": report.get(
            "budget_status",
            {
                "daily_cost": 0.0,
                "monthly_cost": 0.0,
                "daily_budget": BUDGET_LIMITS["daily"],
                "monthly_budget": BUDGET_LIMITS["monthly"],
                "daily_percent": 0.0,
                "monthly_percent": 0.0,
                "daily_status": "ok",
                "monthly_status": "ok",
                "overall_status": "ok",
            },
        ),
    }

    return response_data


# Endpoint to get budget status
@router.get("/budget", response_model=BudgetStatus)
async def get_budget_status(
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get current budget status.

    This endpoint is accessible to all authenticated users.
    """
    if not MODEL_OPTIMIZER_AVAILABLE:
        raise HTTPException(
            status_code=501, detail="Model optimizer module is not available"
        )

    # Get cost report
    report = get_cost_report()

    # Return just the budget status
    return report.get(
        "budget_status",
        {
            "daily_cost": 0.0,
            "monthly_cost": 0.0,
            "daily_budget": BUDGET_LIMITS["daily"],
            "monthly_budget": BUDGET_LIMITS["monthly"],
            "daily_percent": 0.0,
            "monthly_percent": 0.0,
            "daily_status": "ok",
            "monthly_status": "ok",
            "overall_status": "ok",
        },
    )


# Endpoint to reset cost tracking data
@router.post("/reset-cost-tracking")
async def reset_cost_tracking_data(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_superuser),
) -> Dict[str, Any]:
    """
    Reset all cost tracking data.

    Only accessible to superusers.
    """
    if not MODEL_OPTIMIZER_AVAILABLE:
        raise HTTPException(
            status_code=501, detail="Model optimizer module is not available"
        )

    # Run reset in background task to avoid blocking the response
    background_tasks.add_task(reset_cost_tracking)

    return {
        "status": "success",
        "message": "Cost tracking data reset initiated",
        "timestamp": datetime.now().isoformat(),
    }


# New endpoint to get circuit breaker status
@router.get("/circuit-breaker", response_model=CircuitBreakerStatus)
async def get_circuit_breaker_stats(
    current_user: User = Depends(get_current_active_superuser),
) -> Dict[str, Any]:
    """
    Get current circuit breaker status for all model providers.

    Only accessible to superusers.
    """
    if not MODEL_OPTIMIZER_AVAILABLE:
        raise HTTPException(
            status_code=501, detail="Model optimizer module is not available"
        )

    try:
        # Get circuit breaker status
        status = get_circuit_breaker_status()
        return status
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving circuit breaker status: {str(e)}"
        )


# New endpoint to reset circuit breaker
@router.post("/reset-circuit-breaker", response_model=CircuitBreakerResetResponse)
async def reset_circuit_breaker_endpoint(
    request: CircuitBreakerResetRequest,
    current_user: User = Depends(get_current_active_superuser),
) -> Dict[str, Any]:
    """
    Reset the circuit breaker for a specific provider or all providers.

    Only accessible to superusers.

    Args:
        provider: Optional provider name to reset. If not provided, all circuit breakers will be reset.
    """
    if not MODEL_OPTIMIZER_AVAILABLE:
        raise HTTPException(
            status_code=501, detail="Model optimizer module is not available"
        )

    try:
        # Reset circuit breaker
        result = reset_circuit_breaker(request.provider)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error resetting circuit breaker: {str(e)}"
        )


# Endpoint to get model usage for a specific task
@router.get("/task/{task_name}", response_model=TaskUsageStats)
async def get_task_usage(
    task_name: str, current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get usage statistics for a specific task.

    This endpoint is accessible to all authenticated users.
    """
    if not MODEL_OPTIMIZER_AVAILABLE:
        raise HTTPException(
            status_code=501, detail="Model optimizer module is not available"
        )

    # Get cost report
    report = get_cost_report()

    # Check if task exists in report
    if task_name not in report.get("tasks", {}):
        raise HTTPException(
            status_code=404, detail=f"No data found for task: {task_name}"
        )

    # Get task data
    task_data = report["tasks"][task_name]

    # Return task stats
    return {
        "task_name": task_name,
        "total_tokens": task_data.get("total_tokens", 0),
        "total_cost": task_data.get("total_cost", 0.0),
        "request_count": task_data.get("request_count", 0),
        "models_used": task_data.get("models_used", {}),
    }


# Endpoint to get model usage statistics
@router.get("/models", response_model=List[ModelUsageStats])
async def get_model_usage(
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """
    Get usage statistics for all models.

    This endpoint is accessible to all authenticated users.
    """
    if not MODEL_OPTIMIZER_AVAILABLE:
        raise HTTPException(
            status_code=501, detail="Model optimizer module is not available"
        )

    # Get cost report
    report = get_cost_report()

    # Extract model statistics
    model_stats = []
    for model_name, model_data in report.get("models", {}).items():
        model_stat = {
            "model": model_name,
            "total_tokens": model_data.get("total_tokens", 0),
            "input_tokens": model_data.get("input_tokens", 0),
            "output_tokens": model_data.get("output_tokens", 0),
            "total_cost": model_data.get("total_cost", 0.0),
            "request_count": model_data.get("request_count", 0),
            "provider": model_name.split(":")[0] if ":" in model_name else None,
            "tier": None,  # We don't have this information in the tracking data
        }
        model_stats.append(model_stat)

    # Sort by cost (highest first)
    model_stats.sort(key=lambda x: x["total_cost"], reverse=True)

    return model_stats


# Smart request handling endpoints
class RequestStats(BaseModel):
    """Statistics for API request monitoring."""

    total_requests: int
    completed_requests: int
    failed_requests: int
    active_requests: int
    success_rate: float
    endpoints: Optional[Dict[str, Any]] = None
    response_times: Optional[Dict[str, float]] = None


class EndpointStats(BaseModel):
    """Statistics for a specific endpoint."""

    endpoint: str
    total_requests: int
    completed_requests: int
    failed_requests: int
    active_requests: int
    avg_duration: float
    failure_count: int
    success_rate: float


class RequestDetails(BaseModel):
    """Detailed information about a specific request."""

    endpoint: str
    start_time: float
    status: str
    priority: int
    complexity: str
    timeout: int
    end_time: Optional[float] = None
    duration: Optional[float] = None
    error: Optional[str] = None


@router.get("/requests", response_model=RequestStats)
async def get_requests_statistics(
    endpoint: Optional[str] = None,
    current_user: User = Depends(get_current_active_superuser),
) -> Dict[str, Any]:
    """
    Get statistics about API requests processing.

    Only accessible to superusers.

    Args:
        endpoint: Optional endpoint to filter statistics for
    """
    if not SMART_REQUEST_AVAILABLE:
        raise HTTPException(
            status_code=501, detail="Smart request handler module is not available"
        )

    try:
        if endpoint:
            # Get statistics for specific endpoint
            return request_tracker.get_endpoint_statistics(endpoint)
        else:
            # Get overall statistics
            return await get_request_statistics()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving request statistics: {str(e)}"
        )


@router.get("/request/{request_id}", response_model=RequestDetails)
async def get_request_details(
    request_id: str, current_user: User = Depends(get_current_active_superuser)
) -> Dict[str, Any]:
    """
    Get status and details of a specific request.

    Only accessible to superusers.

    Args:
        request_id: ID of the request to check
    """
    if not SMART_REQUEST_AVAILABLE:
        raise HTTPException(
            status_code=501, detail="Smart request handler module is not available"
        )

    try:
        return await get_request_status(request_id)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving request status: {str(e)}"
        )


@router.post("/cleanup-requests", status_code=204)
async def cleanup_old_requests(
    max_age_hours: int = 24, current_user: User = Depends(get_current_active_superuser)
) -> Response:
    """
    Clean up old request tracking data.

    Only accessible to superusers.

    Args:
        max_age_hours: Maximum age in hours for requests to keep
    """
    if not SMART_REQUEST_AVAILABLE:
        raise HTTPException(
            status_code=501, detail="Smart request handler module is not available"
        )

    try:
        # Clean up old requests
        cleared = request_tracker.clear_old_requests(max_age_hours)

        return Response(content=f"Cleared {cleared} old requests", status_code=204)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error cleaning up old requests: {str(e)}"
        )


@router.get("/health", response_model=Dict[str, Any])
async def get_health_metrics() -> Dict[str, Any]:
    """
    Get health and performance metrics for the server.

    This endpoint is publicly accessible.
    """
    import time

    import psutil

    try:
        # Get system metrics
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        # Get request metrics if available
        request_stats = {}
        if SMART_REQUEST_AVAILABLE:
            try:
                stats = await get_request_statistics()
                request_stats = {
                    "active": stats.get("active_requests", 0),
                    "success_rate": stats.get("success_rate", 100),
                }
            except Exception:
                request_stats = {"status": "unavailable"}

        return {
            "status": "healthy",
            "timestamp": time.time(),
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": disk.percent,
            },
            "requests": request_stats,
        }
    except Exception as e:
        return {"status": "degraded", "error": str(e), "timestamp": time.time()}
