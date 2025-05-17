"""
Model optimization and tiered processing implementation.

This module implements a tiered processing approach that intelligently selects
models based on task complexity, reducing costs while maintaining quality.

Key features:
1. Task classification system based on complexity and importance
2. Tiered model selection based on task requirements
3. Token optimization techniques
4. Cost tracking and reporting system
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
import time
import logfire
from pathlib import Path
import threading
import functools

from app.core.config import settings
from app.services.model_selector import (
    ModelTier,
    ModelProvider,
    ModelCapability,
    select_model_for_task,
    get_model_config_for_task,
    get_fallback_chain,
    get_available_models,
)
from app.services.thinking_budget import TaskComplexity, get_task_complexity_from_content

# Define task importance levels
class TaskImportance(str, Enum):
    """Task importance classification based on impact on final output."""
    
    CRITICAL = "critical"     # Tasks that directly determine final output quality
    HIGH = "high"             # Tasks with significant impact on output
    MEDIUM = "medium"         # Tasks with moderate impact on output
    LOW = "low"               # Tasks with minimal impact on output
    BACKGROUND = "background" # Ancillary tasks with indirect impact on output

# Circuit breaker implementation for model provider health
class CircuitBreaker:
    """
    Implements a circuit breaker pattern to avoid making calls to failing model providers.
    
    This helps prevent waiting for timeouts when a service is down or degraded.
    """
    def __init__(self, failure_threshold=3, recovery_time_seconds=300):
        self.failure_counts = {}  # provider -> failure count
        self.circuit_open_until = {}  # provider -> datetime when circuit closes
        self.failure_threshold = failure_threshold
        self.recovery_time = timedelta(seconds=recovery_time_seconds)
    
    def record_failure(self, provider: str):
        """Record a failure for a provider and potentially open the circuit"""
        if provider not in self.failure_counts:
            self.failure_counts[provider] = 0
        
        self.failure_counts[provider] += 1
        
        if self.failure_counts[provider] >= self.failure_threshold:
            self.open_circuit(provider)
            logfire.warning(
                f"Circuit opened for provider {provider} due to repeated failures",
                provider=provider,
                failure_count=self.failure_counts[provider],
                open_until=self.circuit_open_until.get(provider)
            )
    
    def record_success(self, provider: str):
        """Record a success for a provider and reset failure count"""
        if provider in self.failure_counts:
            self.failure_counts[provider] = 0
        
        if provider in self.circuit_open_until:
            del self.circuit_open_until[provider]
    
    def open_circuit(self, provider: str):
        """Open the circuit for a provider for the recovery time"""
        self.circuit_open_until[provider] = datetime.now() + self.recovery_time
    
    def is_circuit_open(self, provider: str) -> bool:
        """Check if the circuit is open for a provider"""
        if provider not in self.circuit_open_until:
            return False
        
        # Check if recovery time has elapsed
        if datetime.now() > self.circuit_open_until[provider]:
            # Allow one request through to test if service has recovered
            del self.circuit_open_until[provider]
            return False
        
        return True

# Create circuit breaker instance with thread safety
optimizer_circuit_breaker = CircuitBreaker()
optimizer_circuit_breaker_lock = threading.Lock()

# Cost tracking data store
# Using a thread-safe dict for simplicity
_cost_data_lock = threading.Lock()
_cost_tracking_data = {
    "total_tokens": 0,
    "total_cost": 0.0,
    "models": {},
    "tasks": {},
    "requests": []
}

# Path to store cost reports
COST_REPORT_DIR = Path("./cost_reports")
# Create directory if it doesn't exist
COST_REPORT_DIR.mkdir(exist_ok=True, parents=True)

# Default budget limits for cost control
DEFAULT_BUDGET_LIMITS = {
    "daily": 50.0,     # $50 per day
    "monthly": 500.0,  # $500 per month
    "per_request": 0.50, # $0.50 per individual request (safeguard)
}

# Budget limits can be overridden with environment variables
BUDGET_LIMITS = {
    "daily": float(os.getenv("MAX_DAILY_BUDGET", DEFAULT_BUDGET_LIMITS["daily"])),
    "monthly": float(os.getenv("MAX_MONTHLY_BUDGET", DEFAULT_BUDGET_LIMITS["monthly"])),
    "per_request": float(os.getenv("MAX_REQUEST_BUDGET", DEFAULT_BUDGET_LIMITS["per_request"])),
}

# Task complexity and importance mappings
TASK_COMPLEXITY_MAPPING = {
    # Evaluation tasks
    "resume_evaluation": TaskComplexity.COMPLEX,
    "feedback_evaluation": TaskComplexity.CRITICAL,
    
    # Optimization tasks
    "optimization_plan": TaskComplexity.VERY_COMPLEX,
    "optimization_plan_feedback": TaskComplexity.CRITICAL,
    "resume_implementation": TaskComplexity.COMPLEX,
    
    # ATS-related tasks
    "ats_score": TaskComplexity.SIMPLE,
    "ats_improvement": TaskComplexity.MODERATE,
    
    # Analysis tasks
    "keyword_extraction": TaskComplexity.SIMPLE,
    "job_classifier": TaskComplexity.SIMPLE,
    "format_detection": TaskComplexity.SIMPLE,
    "job_requirements": TaskComplexity.MODERATE,
    "skill_matching": TaskComplexity.MODERATE,
    "formatting_suggestions": TaskComplexity.MODERATE,
    "keyword_analysis": TaskComplexity.COMPLEX,
    "section_optimization": TaskComplexity.COMPLEX,
    "experience_analysis": TaskComplexity.COMPLEX,
    "job_strategy": TaskComplexity.VERY_COMPLEX,
    
    # Content generation
    "cover_letter_generation": TaskComplexity.CRITICAL,
    "resume_summary": TaskComplexity.MODERATE,
    "resume_customization": TaskComplexity.CRITICAL,
}

TASK_IMPORTANCE_MAPPING = {
    # Evaluation tasks
    "resume_evaluation": TaskImportance.HIGH,
    "feedback_evaluation": TaskImportance.HIGH,
    
    # Optimization tasks
    "optimization_plan": TaskImportance.CRITICAL,
    "optimization_plan_feedback": TaskImportance.HIGH,
    "resume_implementation": TaskImportance.CRITICAL,
    
    # ATS-related tasks
    "ats_score": TaskImportance.MEDIUM,
    "ats_improvement": TaskImportance.HIGH,
    
    # Analysis tasks
    "keyword_extraction": TaskImportance.MEDIUM,
    "job_classifier": TaskImportance.LOW,
    "format_detection": TaskImportance.LOW,
    "job_requirements": TaskImportance.MEDIUM,
    "skill_matching": TaskImportance.MEDIUM,
    "formatting_suggestions": TaskImportance.MEDIUM,
    "keyword_analysis": TaskImportance.HIGH,
    "section_optimization": TaskImportance.HIGH,
    "experience_analysis": TaskImportance.HIGH,
    "job_strategy": TaskImportance.HIGH,
    
    # Content generation
    "cover_letter_generation": TaskImportance.CRITICAL,
    "resume_summary": TaskImportance.MEDIUM,
    "resume_customization": TaskImportance.CRITICAL,
}

# Token optimization configurations
TOKEN_OPTIMIZATION_STRATEGIES = {
    TaskComplexity.SIMPLE: {
        "context_compression": True,     # Compress context with semantic techniques
        "token_limit_multiplier": 0.6,   # Use only 60% of max tokens for simple tasks
        "exclude_examples": True,        # Don't include examples in prompts
        "reduce_thinking_budget": True,  # Reduce thinking budget for simple tasks
    },
    TaskComplexity.MODERATE: {
        "context_compression": True,
        "token_limit_multiplier": 0.8,
        "exclude_examples": True,
        "reduce_thinking_budget": False,
    },
    TaskComplexity.COMPLEX: {
        "context_compression": False,
        "token_limit_multiplier": 1.0,
        "exclude_examples": False,
        "reduce_thinking_budget": False,
    },
    TaskComplexity.VERY_COMPLEX: {
        "context_compression": False,
        "token_limit_multiplier": 1.0,
        "exclude_examples": False,
        "reduce_thinking_budget": False,
    },
    TaskComplexity.CRITICAL: {
        "context_compression": False,
        "token_limit_multiplier": 1.0,
        "exclude_examples": False,
        "reduce_thinking_budget": False,
    },
}

# Model tier selections based on task complexity and importance
MODEL_TIER_SELECTION = {
    # Format: (task_complexity, task_importance) -> ModelTier
    (TaskComplexity.SIMPLE, TaskImportance.LOW): ModelTier.ECONOMY,
    (TaskComplexity.SIMPLE, TaskImportance.MEDIUM): ModelTier.ECONOMY,
    (TaskComplexity.SIMPLE, TaskImportance.HIGH): ModelTier.ECONOMY,
    (TaskComplexity.SIMPLE, TaskImportance.CRITICAL): ModelTier.STANDARD,
    
    (TaskComplexity.MODERATE, TaskImportance.LOW): ModelTier.ECONOMY,
    (TaskComplexity.MODERATE, TaskImportance.MEDIUM): ModelTier.STANDARD,
    (TaskComplexity.MODERATE, TaskImportance.HIGH): ModelTier.STANDARD,
    (TaskComplexity.MODERATE, TaskImportance.CRITICAL): ModelTier.PREMIUM,
    
    (TaskComplexity.COMPLEX, TaskImportance.LOW): ModelTier.STANDARD,
    (TaskComplexity.COMPLEX, TaskImportance.MEDIUM): ModelTier.STANDARD,
    (TaskComplexity.COMPLEX, TaskImportance.HIGH): ModelTier.PREMIUM,
    (TaskComplexity.COMPLEX, TaskImportance.CRITICAL): ModelTier.PREMIUM,
    
    (TaskComplexity.VERY_COMPLEX, TaskImportance.LOW): ModelTier.STANDARD,
    (TaskComplexity.VERY_COMPLEX, TaskImportance.MEDIUM): ModelTier.PREMIUM,
    (TaskComplexity.VERY_COMPLEX, TaskImportance.HIGH): ModelTier.PREMIUM,
    (TaskComplexity.VERY_COMPLEX, TaskImportance.CRITICAL): ModelTier.PREMIUM,
    
    (TaskComplexity.CRITICAL, TaskImportance.LOW): ModelTier.PREMIUM,
    (TaskComplexity.CRITICAL, TaskImportance.MEDIUM): ModelTier.PREMIUM,
    (TaskComplexity.CRITICAL, TaskImportance.HIGH): ModelTier.PREMIUM,
    (TaskComplexity.CRITICAL, TaskImportance.CRITICAL): ModelTier.PREMIUM,
}

def classify_task(
    task_name: str,
    content: Optional[str] = None,
    job_description: Optional[str] = None,
    industry: Optional[str] = None,
    user_override: Optional[Dict[str, Any]] = None
) -> Tuple[TaskComplexity, TaskImportance]:
    """
    Classify a task based on its name, content, and context.
    
    Args:
        task_name: Name of the task
        content: Optional content to analyze (e.g. resume)
        job_description: Optional job description
        industry: Optional industry name
        user_override: Optional user-specified overrides
        
    Returns:
        Tuple of (task_complexity, task_importance)
    """
    # Start with predefined complexity and importance
    base_complexity = TASK_COMPLEXITY_MAPPING.get(
        task_name, TaskComplexity.MODERATE
    )
    base_importance = TASK_IMPORTANCE_MAPPING.get(
        task_name, TaskImportance.MEDIUM
    )
    
    # Apply user overrides if provided
    if user_override:
        if "complexity" in user_override:
            try:
                base_complexity = TaskComplexity(user_override["complexity"])
            except ValueError:
                logfire.warning(
                    f"Invalid complexity override: {user_override['complexity']}",
                    task_name=task_name,
                    valid_values=[c.value for c in TaskComplexity]
                )
                
        if "importance" in user_override:
            try:
                base_importance = TaskImportance(user_override["importance"])
            except ValueError:
                logfire.warning(
                    f"Invalid importance override: {user_override['importance']}",
                    task_name=task_name,
                    valid_values=[i.value for i in TaskImportance]
                )
    
    # If content is provided, analyze to potentially adjust complexity
    if content and task_name not in ["job_classifier", "format_detection"]:  
        # Skip content-based adjustment for tasks that don't need it
        content_complexity, metrics = get_task_complexity_from_content(
            content=content,
            job_description=job_description,
            industry=industry
        )
        
        # Use the higher complexity between base and content-derived
        complexity_values = [c.value for c in TaskComplexity]
        if complexity_values.index(content_complexity.value) > complexity_values.index(base_complexity.value):
            # Content suggests higher complexity than predefined mapping
            base_complexity = content_complexity
            logfire.info(
                "Task complexity adjusted based on content analysis",
                task_name=task_name,
                base_complexity=base_complexity.value,
                adjusted_complexity=content_complexity.value,
                content_length=metrics.total_tokens,
                section_count=metrics.section_count
            )
    
    # Special case: if job_description is very long or complex, increase complexity
    if job_description and len(job_description) > 4000:
        complexity_values = [c.value for c in TaskComplexity]
        current_index = complexity_values.index(base_complexity.value)
        if current_index < len(complexity_values) - 1:
            # Increase complexity by one level if not already at max
            higher_complexity = TaskComplexity(complexity_values[current_index + 1])
            logfire.info(
                "Task complexity increased due to long job description",
                task_name=task_name,
                original_complexity=base_complexity.value,
                new_complexity=higher_complexity.value,
                job_description_length=len(job_description)
            )
            base_complexity = higher_complexity
    
    # Special case: for critical tasks like optimization_plan, ensure high importance
    # This overrides even user settings for certain tasks that must be high quality
    if task_name in ["optimization_plan", "resume_customization", "cover_letter_generation"]:
        if base_importance.value in [TaskImportance.LOW.value, TaskImportance.MEDIUM.value]:
            logfire.info(
                f"Upgrading importance for critical task {task_name}",
                original_importance=base_importance.value,
                new_importance=TaskImportance.HIGH.value
            )
            base_importance = TaskImportance.HIGH
    
    # Log the classification
    logfire.info(
        "Task classified",
        task_name=task_name,
        complexity=base_complexity.value,
        importance=base_importance.value,
        has_content=content is not None,
        has_job_description=job_description is not None
    )
    
    return base_complexity, base_importance

def select_optimized_model(
    task_name: str,
    content: Optional[str] = None,
    job_description: Optional[str] = None,
    industry: Optional[str] = None,
    preferred_provider: Optional[str] = None,
    user_override: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Select an optimized model based on task complexity and importance.
    
    Args:
        task_name: Name of the task
        content: Optional content to analyze (e.g. resume)
        job_description: Optional job description
        industry: Optional industry name
        preferred_provider: Optional preferred provider
        user_override: Optional user-specified overrides
        
    Returns:
        Complete model configuration dictionary
    """
    # Start tracking this request for cost analysis
    request_id = f"{task_name}_{int(time.time())}"
    
    # Check budget limits before proceeding
    try:
        budget_status = _get_budget_status()
        
        # If we're approaching limits, return False to trigger cost saving measures
        if budget_status["overall_status"] in ["warning", "critical"]:
            logfire.warning(
                "Budget limit approaching, using economical model selection",
                task_name=task_name,
                budget_status="high_usage"
            )
            # Force economy tier selection
            if user_override is None:
                user_override = {}
            user_override["tier"] = ModelTier.ECONOMY.value
            user_override["cost_sensitivity"] = 2.0  # Highest cost sensitivity
    except Exception as e:
        logfire.error(
            "Error checking budget limits, defaulting to normal operation",
            error=str(e),
            error_type=type(e).__name__
        )
    
    # Classify the task
    task_complexity, task_importance = classify_task(
        task_name=task_name,
        content=content,
        job_description=job_description,
        industry=industry,
        user_override=user_override
    )
    
    # Determine appropriate model tier based on complexity and importance
    model_tier = MODEL_TIER_SELECTION.get(
        (task_complexity, task_importance),
        ModelTier.STANDARD  # Default to STANDARD if not explicitly mapped
    )
    
    # Apply user override for model tier if provided
    if user_override and "tier" in user_override:
        try:
            model_tier = ModelTier(user_override["tier"])
        except ValueError:
            logfire.warning(
                f"Invalid tier override: {user_override['tier']}",
                task_name=task_name,
                valid_values=[t.value for t in ModelTier]
            )
    
    # Determine cost sensitivity based on task importance
    cost_sensitivity = {
        TaskImportance.LOW: 1.8,        # Highly cost-sensitive
        TaskImportance.MEDIUM: 1.4,     # Moderately cost-sensitive
        TaskImportance.HIGH: 1.0,       # Standard cost sensitivity
        TaskImportance.CRITICAL: 0.7,   # Lower cost sensitivity for critical tasks
        TaskImportance.BACKGROUND: 2.0, # Maximum cost sensitivity for background tasks
    }.get(task_importance, 1.0)
    
    # Apply user override for cost sensitivity if provided
    if user_override and "cost_sensitivity" in user_override:
        try:
            cost_sensitivity = float(user_override["cost_sensitivity"])
            # Ensure it's within valid range
            cost_sensitivity = max(0.5, min(2.0, cost_sensitivity))
        except (ValueError, TypeError):
            logfire.warning(
                f"Invalid cost_sensitivity override: {user_override['cost_sensitivity']}",
                task_name=task_name,
                valid_range="0.5-2.0"
            )
    
    # Convert preferred provider to enum if provided
    provider_enum = None
    if preferred_provider:
        # Check if the preferred provider has an open circuit
        with optimizer_circuit_breaker_lock:
            provider_circuit_open = optimizer_circuit_breaker.is_circuit_open(preferred_provider)
        
        if provider_circuit_open:
            logfire.warning(
                f"Circuit open for provider {preferred_provider}, ignoring preference",
                preferred_provider=preferred_provider
            )
            preferred_provider = None
        else:
            try:
                from app.services.model_selector import ModelProvider
                provider_enum = ModelProvider(preferred_provider)
            except ValueError:
                logfire.warning(
                    f"Unknown provider: {preferred_provider}, ignoring preference",
                    preferred_provider=preferred_provider,
                    valid_providers=[p.value for p in ModelProvider]
                )
    
    # Apply token optimization strategies based on task complexity
    optimization_strategy = TOKEN_OPTIMIZATION_STRATEGIES.get(
        task_complexity, 
        TOKEN_OPTIMIZATION_STRATEGIES[TaskComplexity.MODERATE]  # Default to MODERATE if not found
    )
    
    # Calculate content length if provided
    content_length = None
    if content:
        # Approximate tokens (4 chars per token)
        content_length = len(content) // 4
        if job_description:
            content_length += len(job_description) // 4
    
    # Adjust max tokens based on optimization strategy
    max_tokens = settings.PYDANTICAI_MAX_TOKENS
    if optimization_strategy["token_limit_multiplier"] < 1.0:
        max_tokens = int(max_tokens * optimization_strategy["token_limit_multiplier"])
    
    # Adjust thinking budget based on complexity
    thinking_budget = settings.PYDANTICAI_THINKING_BUDGET
    if optimization_strategy["reduce_thinking_budget"]:
        thinking_budget = int(thinking_budget * 0.5)  # Reduce by 50% for simple tasks
    
    # Define required capabilities based on task
    required_capabilities = []
    
    # Add structured output capability for most tasks
    required_capabilities.append(ModelCapability.STRUCTURED_OUTPUT)
    
    # Add thinking capability for complex tasks
    if task_complexity in [TaskComplexity.COMPLEX, TaskComplexity.VERY_COMPLEX, TaskComplexity.CRITICAL]:
        required_capabilities.append(ModelCapability.THINKING)
    
    # Add detailed capability for tasks needing detailed analysis
    if task_complexity in [TaskComplexity.COMPLEX, TaskComplexity.VERY_COMPLEX, TaskComplexity.CRITICAL]:
        required_capabilities.append(ModelCapability.DETAILED)
    else:
        # For simpler tasks, prefer concise responses
        required_capabilities.append(ModelCapability.CONCISE)
    
    # Add creative capability for specific tasks
    if task_name in ["resume_customization", "cover_letter_generation", "optimization_plan"]:
        required_capabilities.append(ModelCapability.CREATIVE)
    
    # Override requirements dict for model selection
    override_requirements = {
        "preferred_tier": model_tier,
        "required_capabilities": required_capabilities,
        "budget_sensitivity": "high" if cost_sensitivity > 1.5 else (
            "low" if cost_sensitivity < 0.8 else "medium"
        ),
    }
    
    # Get model configuration
    model_config = get_model_config_for_task(
        task_name=task_name,
        content=content,
        job_description=job_description,
        industry=industry,
        preferred_provider=preferred_provider,
        cost_sensitivity=cost_sensitivity
    )
    
    # Add optimization metadata to the configuration
    model_config["optimization_metadata"] = {
        "task_complexity": task_complexity.value,
        "task_importance": task_importance.value,
        "selected_tier": model_tier.value,
        "cost_sensitivity": cost_sensitivity,
        "optimization_strategy": {k: v for k, v in optimization_strategy.items()},
        "request_id": request_id
    }
    
    # Additional optimizations for the temperature based on task
    if task_importance == TaskImportance.CRITICAL:
        # Use lower temperature for more deterministic results on critical tasks
        model_config["temperature"] = max(0.2, model_config.get("temperature", 0.7) - 0.3)
    elif task_importance == TaskImportance.LOW:
        # Can use higher temperature for less important tasks
        model_config["temperature"] = min(0.9, model_config.get("temperature", 0.7) + 0.2)
    
    # Apply max tokens adjustment from optimization strategy
    model_config["max_tokens"] = max_tokens
    
    # Register for cost tracking
    _register_model_usage(
        model_config["model"],
        task_name,
        request_id,
        {
            "complexity": task_complexity.value,
            "importance": task_importance.value,
            "cost_sensitivity": cost_sensitivity,
            "selected_tier": model_tier.value,
            "timestamp": time.time(),
        }
    )
    
    # Log the optimized model selection
    logfire.info(
        "Optimized model selected",
        task_name=task_name,
        model=model_config["model"],
        complexity=task_complexity.value,
        importance=task_importance.value,
        tier=model_tier.value,
        cost_sensitivity=cost_sensitivity,
        temperature=model_config.get("temperature"),
        max_tokens=model_config.get("max_tokens"),
        has_thinking_config="thinking_config" in model_config,
        request_id=request_id
    )
    
    return model_config

def track_token_usage(
    model: str,
    task_name: str,
    request_id: str,
    input_tokens: int,
    output_tokens: int
) -> Dict[str, Any]:
    """
    Track token usage and calculate costs.
    
    Args:
        model: Model name
        task_name: Task name
        request_id: Request ID for tracking
        input_tokens: Number of input tokens used
        output_tokens: Number of output tokens used
        
    Returns:
        Dictionary with cost details
    """
    # Get available models to lookup costs
    available_models = get_available_models()
    
    # Find the model in the registry
    if model not in available_models:
        logfire.warning(
            f"Model {model} not found in registry, cannot calculate costs",
            model=model,
            task_name=task_name,
            request_id=request_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )
        return {
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "input_cost": 0.0,
            "output_cost": 0.0,
            "total_cost": 0.0
        }
    
    # Get model costs from registry
    model_config = available_models[model]
    input_cost_per_1k = model_config.get("cost_per_1k_input", 0.0)
    output_cost_per_1k = model_config.get("cost_per_1k_output", 0.0)
    
    # Calculate costs
    input_cost = (input_tokens / 1000) * input_cost_per_1k
    output_cost = (output_tokens / 1000) * output_cost_per_1k
    total_cost = input_cost + output_cost
    
    # Create cost details
    cost_details = {
        "model": model,
        "tier": model_config.get("tier").value,
        "provider": model_config.get("provider").value,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "input_cost": input_cost,
        "output_cost": output_cost,
        "total_cost": total_cost,
        "timestamp": time.time()
    }
    
    # Update cost tracking data
    with _cost_data_lock:
        # Update global tokens and cost
        _cost_tracking_data["total_tokens"] += input_tokens + output_tokens
        _cost_tracking_data["total_cost"] += total_cost
        
        # Update model-specific tracking
        if model not in _cost_tracking_data["models"]:
            _cost_tracking_data["models"][model] = {
                "total_tokens": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_cost": 0.0,
                "request_count": 0
            }
        
        _cost_tracking_data["models"][model]["total_tokens"] += input_tokens + output_tokens
        _cost_tracking_data["models"][model]["input_tokens"] += input_tokens
        _cost_tracking_data["models"][model]["output_tokens"] += output_tokens
        _cost_tracking_data["models"][model]["total_cost"] += total_cost
        _cost_tracking_data["models"][model]["request_count"] += 1
        
        # Update task-specific tracking
        if task_name not in _cost_tracking_data["tasks"]:
            _cost_tracking_data["tasks"][task_name] = {
                "total_tokens": 0,
                "total_cost": 0.0,
                "request_count": 0,
                "models_used": {}
            }
        
        _cost_tracking_data["tasks"][task_name]["total_tokens"] += input_tokens + output_tokens
        _cost_tracking_data["tasks"][task_name]["total_cost"] += total_cost
        _cost_tracking_data["tasks"][task_name]["request_count"] += 1
        
        if model not in _cost_tracking_data["tasks"][task_name]["models_used"]:
            _cost_tracking_data["tasks"][task_name]["models_used"][model] = {
                "total_tokens": 0,
                "total_cost": 0.0,
                "request_count": 0
            }
        
        _cost_tracking_data["tasks"][task_name]["models_used"][model]["total_tokens"] += input_tokens + output_tokens
        _cost_tracking_data["tasks"][task_name]["models_used"][model]["total_cost"] += total_cost
        _cost_tracking_data["tasks"][task_name]["models_used"][model]["request_count"] += 1
        
        # Update request tracking
        for i, request in enumerate(_cost_tracking_data["requests"]):
            if request.get("request_id") == request_id:
                # Update existing request
                _cost_tracking_data["requests"][i]["input_tokens"] = input_tokens
                _cost_tracking_data["requests"][i]["output_tokens"] = output_tokens
                _cost_tracking_data["requests"][i]["input_cost"] = input_cost
                _cost_tracking_data["requests"][i]["output_cost"] = output_cost
                _cost_tracking_data["requests"][i]["total_cost"] = total_cost
                _cost_tracking_data["requests"][i]["timestamp_completed"] = time.time()
                break
        else:
            # If request not found, add it (shouldn't happen if _register_model_usage was called)
            _cost_tracking_data["requests"].append({
                "request_id": request_id,
                "model": model,
                "task_name": task_name,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "input_cost": input_cost,
                "output_cost": output_cost,
                "total_cost": total_cost,
                "timestamp_started": time.time() - 1,  # Approximate start time
                "timestamp_completed": time.time()
            })
    
    # Log the token usage and cost
    logfire.info(
        "Token usage tracked",
        model=model,
        task_name=task_name,
        request_id=request_id,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        input_cost=round(input_cost, 4),
        output_cost=round(output_cost, 4),
        total_cost=round(total_cost, 4)
    )
    
    # Record success in circuit breaker
    # Extract provider from model name (e.g., "anthropic" from "anthropic:claude-3-7-sonnet-latest")
    provider = model.split(':')[0] if ':' in model else model
    with optimizer_circuit_breaker_lock:
        optimizer_circuit_breaker.record_success(provider)
    
    # Check if we should save a cost report (do this periodically)
    _maybe_save_cost_report()
    
    return cost_details

def record_model_failure(
    provider: str, 
    error: Optional[str] = None, 
    error_type: Optional[str] = None
) -> None:
    """
    Record a model provider failure in the circuit breaker.
    
    Args:
        provider: Provider name (e.g., 'anthropic', 'google', 'openai')
        error: Optional error message
        error_type: Optional error type
    """
    # Log the failure
    logfire.error(
        f"Model provider failure recorded: {provider}",
        provider=provider,
        error=error,
        error_type=error_type
    )
    
    # Record in circuit breaker
    with optimizer_circuit_breaker_lock:
        optimizer_circuit_breaker.record_failure(provider)

def get_cost_report() -> Dict[str, Any]:
    """
    Get the current cost tracking report.
    
    Returns:
        Dictionary with detailed cost tracking data
    """
    with _cost_data_lock:
        # Create a copy of the data to avoid thread safety issues
        report = {
            "total_tokens": _cost_tracking_data["total_tokens"],
            "total_cost": _cost_tracking_data["total_cost"],
            "models": {k: v.copy() for k, v in _cost_tracking_data["models"].items()},
            "tasks": {k: v.copy() for k, v in _cost_tracking_data["tasks"].items()},
            # Only include the last 100 requests to keep the report size reasonable
            "recent_requests": _cost_tracking_data["requests"][-100:],
            "timestamp": time.time(),
            "budget_limits": BUDGET_LIMITS,
            "budget_status": _get_budget_status()
        }
    
    return report

def reset_cost_tracking() -> None:
    """Reset all cost tracking data."""
    with _cost_data_lock:
        # Save final report before resetting
        _save_cost_report()
        
        # Reset tracking data
        _cost_tracking_data["total_tokens"] = 0
        _cost_tracking_data["total_cost"] = 0.0
        _cost_tracking_data["models"] = {}
        _cost_tracking_data["tasks"] = {}
        _cost_tracking_data["requests"] = []
    
    logfire.info("Cost tracking data reset")

def optimize_prompt(
    prompt: str,
    task_complexity: TaskComplexity,
    exclude_examples: bool = False
) -> str:
    """
    Optimize a prompt to reduce token usage.
    
    Args:
        prompt: Original prompt text
        task_complexity: Complexity of the task
        exclude_examples: Whether to exclude examples
        
    Returns:
        Optimized prompt text
    """
    # For simple tasks, aggressively optimize
    if task_complexity == TaskComplexity.SIMPLE:
        # Remove any examples if requested
        if exclude_examples:
            # Look for common example patterns and remove them
            import re
            # Remove sections that look like examples (usually between <example> tags)
            prompt = re.sub(r'<example>.*?</example>', '', prompt, flags=re.DOTALL)
            # Remove lines that start with "Example:" and the content that follows
            prompt = re.sub(r'Example:.*?\n\n', '\n\n', prompt, flags=re.DOTALL)
        
        # Remove unnecessary whitespace
        prompt = '\n'.join(line.strip() for line in prompt.split('\n') if line.strip())
        
        # For simple tasks, we can remove detailed explanations
        # Look for explanation patterns like "This means..." or "In other words..."
        import re
        prompt = re.sub(r'This means.*?\n', '\n', prompt)
        prompt = re.sub(r'In other words.*?\n', '\n', prompt)
        
    # For moderate tasks, do moderate optimization
    elif task_complexity == TaskComplexity.MODERATE:
        # Remove examples if requested
        if exclude_examples:
            import re
            prompt = re.sub(r'<example>.*?</example>', '', prompt, flags=re.DOTALL)
        
        # Just clean up excessive whitespace
        prompt = '\n'.join(line for line in prompt.split('\n') if line.strip())
    
    # For complex tasks and above, do minimal or no optimization
    
    return prompt

def _register_model_usage(
    model: str,
    task_name: str,
    request_id: str,
    metadata: Dict[str, Any]
) -> None:
    """
    Register a model usage event for tracking.
    
    Args:
        model: Model name
        task_name: Task name
        request_id: Request ID for tracking
        metadata: Additional metadata
    """
    with _cost_data_lock:
        # Add request to tracking
        _cost_tracking_data["requests"].append({
            "request_id": request_id,
            "model": model,
            "task_name": task_name,
            "input_tokens": 0,  # Will be updated later
            "output_tokens": 0,  # Will be updated later
            "input_cost": 0.0,   # Will be updated later
            "output_cost": 0.0,  # Will be updated later
            "total_cost": 0.0,   # Will be updated later
            "timestamp_started": time.time(),
            "timestamp_completed": None,  # Will be updated later
            "metadata": metadata
        })
        
        # Keep only the last 1000 requests to avoid memory growth
        if len(_cost_tracking_data["requests"]) > 1000:
            _cost_tracking_data["requests"] = _cost_tracking_data["requests"][-1000:]

def _maybe_save_cost_report() -> None:
    """Periodically save the cost report to disk."""
    # Save every 50 requests or if total cost exceeds $1
    save_threshold_requests = 50
    save_threshold_cost = 1.0  # $1
    
    with _cost_data_lock:
        # Check if we have enough data to save
        request_count = len(_cost_tracking_data["requests"])
        last_save_request = getattr(_maybe_save_cost_report, 'last_save_request', 0)
        last_save_cost = getattr(_maybe_save_cost_report, 'last_save_cost', 0.0)
        
        if (request_count - last_save_request >= save_threshold_requests or
                _cost_tracking_data["total_cost"] - last_save_cost >= save_threshold_cost):
            # Save the report
            _save_cost_report()
            
            # Update last save metrics
            _maybe_save_cost_report.last_save_request = request_count
            _maybe_save_cost_report.last_save_cost = _cost_tracking_data["total_cost"]

def _save_cost_report() -> None:
    """Save the current cost report to disk."""
    # Create filename with current date and time
    filename = f"cost_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = COST_REPORT_DIR / filename
    
    # Prepare report data
    with _cost_data_lock:
        report_data = {
            "total_tokens": _cost_tracking_data["total_tokens"],
            "total_cost": _cost_tracking_data["total_cost"],
            "models": _cost_tracking_data["models"],
            "tasks": _cost_tracking_data["tasks"],
            "requests": _cost_tracking_data["requests"],
            "timestamp": time.time(),
            "date": datetime.now().isoformat(),
            "budget_limits": BUDGET_LIMITS,
            "budget_status": _get_budget_status()
        }
    
    # Save to file
    try:
        with open(filepath, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        logfire.info(
            "Cost report saved",
            filepath=str(filepath),
            total_cost=round(report_data["total_cost"], 2),
            total_tokens=report_data["total_tokens"],
            request_count=len(report_data["requests"])
        )
    except Exception as e:
        logfire.error(
            "Error saving cost report",
            error=str(e),
            filepath=str(filepath)
        )

def _get_budget_status() -> Dict[str, Any]:
    """
    Get the current budget status.
    
    Returns:
        Dictionary with budget status details
    """
    # Calculate daily and monthly costs
    today = datetime.now().date()
    this_month = today.replace(day=1)
    
    daily_cost = 0.0
    monthly_cost = 0.0
    
    with _cost_data_lock:
        for request in _cost_tracking_data["requests"]:
            if "timestamp_started" in request:
                request_time = datetime.fromtimestamp(request["timestamp_started"]).date()
                if request_time == today:
                    daily_cost += request.get("total_cost", 0.0)
                if request_time >= this_month:
                    monthly_cost += request.get("total_cost", 0.0)
    
    # Calculate usage percentages
    daily_percent = (daily_cost / BUDGET_LIMITS["daily"]) * 100 if BUDGET_LIMITS["daily"] > 0 else 0
    monthly_percent = (monthly_cost / BUDGET_LIMITS["monthly"]) * 100 if BUDGET_LIMITS["monthly"] > 0 else 0
    
    # Determine status levels
    daily_status = "ok"
    if daily_percent > 90:
        daily_status = "critical"
    elif daily_percent > 75:
        daily_status = "warning"
    
    monthly_status = "ok"
    if monthly_percent > 90:
        monthly_status = "critical"
    elif monthly_percent > 75:
        monthly_status = "warning"
    
    return {
        "daily_cost": daily_cost,
        "monthly_cost": monthly_cost,
        "daily_budget": BUDGET_LIMITS["daily"],
        "monthly_budget": BUDGET_LIMITS["monthly"],
        "daily_percent": daily_percent,
        "monthly_percent": monthly_percent,
        "daily_status": daily_status,
        "monthly_status": monthly_status,
        "overall_status": "critical" if daily_status == "critical" or monthly_status == "critical" else
                         "warning" if daily_status == "warning" or monthly_status == "warning" else "ok"
    }

def _check_budget_limits() -> bool:
    """
    Check if we are within budget limits.
    
    Returns:
        True if within limits, False if approaching or exceeding limits
    """
    try:
        budget_status = _get_budget_status()
        
        # If we're approaching limits, return False to trigger cost saving measures
        if budget_status["overall_status"] in ["warning", "critical"]:
            logfire.warning(
                "Approaching budget limits",
                daily_percent=round(budget_status["daily_percent"], 2),
                monthly_percent=round(budget_status["monthly_percent"], 2),
                status=budget_status["overall_status"]
            )
            return False
        
        return True
    except Exception as e:
        logfire.error(
            "Error checking budget limits, defaulting to normal operation",
            error=str(e),
            error_type=type(e).__name__
        )
        return True

# Decorator for tracking model usage in functions
def track_model_usage(task_name: str):
    """
    Decorator for tracking model usage in functions.
    
    Args:
        task_name: Name of the task
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract model config from kwargs if available
            model_config = kwargs.get("model_config")
            if not model_config:
                # Try to find it in the positional args by checking for dict types
                for arg in args:
                    if isinstance(arg, dict) and "model" in arg:
                        model_config = arg
                        break
            
            request_id = None
            if model_config and "optimization_metadata" in model_config:
                request_id = model_config["optimization_metadata"].get("request_id")
            else:
                # Generate a request ID if not found
                request_id = f"{task_name}_{int(time.time())}"
                # Register model usage with default values
                _register_model_usage(
                    model=model_config.get("model", "unknown") if model_config else "unknown",
                    task_name=task_name,
                    request_id=request_id,
                    metadata={
                        "timestamp": time.time(),
                    }
                )
            
            # Call the original function
            try:
                result = await func(*args, **kwargs)
                
                # Try to extract token usage from the result (if available)
                if hasattr(result, "_input_tokens") and hasattr(result, "_output_tokens"):
                    model_name = model_config.get("model", "unknown") if model_config else "unknown"
                    track_token_usage(
                        model=model_name,
                        task_name=task_name,
                        request_id=request_id,
                        input_tokens=getattr(result, "_input_tokens", 0),
                        output_tokens=getattr(result, "_output_tokens", 0)
                    )
                
                return result
            except Exception as e:
                # Record failure if possible
                if model_config and "model" in model_config:
                    model_name = model_config["model"]
                    provider = model_name.split(':')[0] if ':' in model_name else model_name
                    record_model_failure(
                        provider=provider, 
                        error=str(e),
                        error_type=type(e).__name__
                    )
                raise e  # Re-raise the exception
        
        return wrapper
    
    return decorator