"""
API endpoints for model usage statistics and cost data.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel
from datetime import datetime

from app.core.security import get_current_user, get_current_active_superuser
from app.models.user import User

# Import model optimizer functions
try:
    from app.services.model_optimizer import (
        get_cost_report,
        reset_cost_tracking,
        BUDGET_LIMITS
    )
    MODEL_OPTIMIZER_AVAILABLE = True
except ImportError:
    MODEL_OPTIMIZER_AVAILABLE = False

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

# Endpoint to get usage statistics
@router.get("/usage", response_model=CostReportData)
async def get_usage_statistics(
    current_user: User = Depends(get_current_active_superuser)
) -> Dict[str, Any]:
    """
    Get detailed usage statistics and cost data.
    
    Only accessible to superusers.
    """
    if not MODEL_OPTIMIZER_AVAILABLE:
        raise HTTPException(
            status_code=501,
            detail="Model optimizer module is not available"
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
        "date": datetime.fromtimestamp(report["timestamp"]).isoformat() if "timestamp" in report else None,
        "budget_limits": report.get("budget_limits", BUDGET_LIMITS),
        "budget_status": report.get("budget_status", {
            "daily_cost": 0.0,
            "monthly_cost": 0.0,
            "daily_budget": BUDGET_LIMITS["daily"],
            "monthly_budget": BUDGET_LIMITS["monthly"],
            "daily_percent": 0.0,
            "monthly_percent": 0.0,
            "daily_status": "ok",
            "monthly_status": "ok",
            "overall_status": "ok"
        })
    }
    
    return response_data

# Endpoint to get budget status
@router.get("/budget", response_model=BudgetStatus)
async def get_budget_status(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get current budget status.
    
    This endpoint is accessible to all authenticated users.
    """
    if not MODEL_OPTIMIZER_AVAILABLE:
        raise HTTPException(
            status_code=501,
            detail="Model optimizer module is not available"
        )
    
    # Get cost report
    report = get_cost_report()
    
    # Return just the budget status
    return report.get("budget_status", {
        "daily_cost": 0.0,
        "monthly_cost": 0.0,
        "daily_budget": BUDGET_LIMITS["daily"],
        "monthly_budget": BUDGET_LIMITS["monthly"],
        "daily_percent": 0.0,
        "monthly_percent": 0.0,
        "daily_status": "ok",
        "monthly_status": "ok",
        "overall_status": "ok"
    })

# Endpoint to reset cost tracking data
@router.post("/reset-cost-tracking")
async def reset_cost_tracking_data(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_superuser)
) -> Dict[str, Any]:
    """
    Reset all cost tracking data.
    
    Only accessible to superusers.
    """
    if not MODEL_OPTIMIZER_AVAILABLE:
        raise HTTPException(
            status_code=501,
            detail="Model optimizer module is not available"
        )
    
    # Run reset in background task to avoid blocking the response
    background_tasks.add_task(reset_cost_tracking)
    
    return {
        "status": "success",
        "message": "Cost tracking data reset initiated",
        "timestamp": datetime.now().isoformat()
    }

# Endpoint to get model usage for a specific task
@router.get("/task/{task_name}", response_model=TaskUsageStats)
async def get_task_usage(
    task_name: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get usage statistics for a specific task.
    
    This endpoint is accessible to all authenticated users.
    """
    if not MODEL_OPTIMIZER_AVAILABLE:
        raise HTTPException(
            status_code=501,
            detail="Model optimizer module is not available"
        )
    
    # Get cost report
    report = get_cost_report()
    
    # Check if task exists in report
    if task_name not in report.get("tasks", {}):
        raise HTTPException(
            status_code=404,
            detail=f"No data found for task: {task_name}"
        )
    
    # Get task data
    task_data = report["tasks"][task_name]
    
    # Return task stats
    return {
        "task_name": task_name,
        "total_tokens": task_data.get("total_tokens", 0),
        "total_cost": task_data.get("total_cost", 0.0),
        "request_count": task_data.get("request_count", 0),
        "models_used": task_data.get("models_used", {})
    }

# Endpoint to get model usage statistics
@router.get("/models", response_model=List[ModelUsageStats])
async def get_model_usage(
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    Get usage statistics for all models.
    
    This endpoint is accessible to all authenticated users.
    """
    if not MODEL_OPTIMIZER_AVAILABLE:
        raise HTTPException(
            status_code=501,
            detail="Model optimizer module is not available"
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
            "tier": None  # We don't have this information in the tracking data
        }
        model_stats.append(model_stat)
    
    # Sort by cost (highest first)
    model_stats.sort(key=lambda x: x["total_cost"], reverse=True)
    
    return model_stats