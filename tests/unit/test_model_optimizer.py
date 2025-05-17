"""
Tests for the model optimizer and tiered processing module.
"""

import os
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.services.model_optimizer import (
    TaskImportance,
    classify_task,
    select_optimized_model,
    track_token_usage,
    get_cost_report,
    reset_cost_tracking,
    optimize_prompt,
    TASK_COMPLEXITY_MAPPING,
    TASK_IMPORTANCE_MAPPING
)
from app.services.thinking_budget import TaskComplexity
from app.services.model_selector import ModelTier, ModelProvider, ModelCapability


def test_classify_task():
    """Test task classification logic."""
    # Basic classification based on task name
    complexity, importance = classify_task("resume_evaluation")
    assert complexity == TASK_COMPLEXITY_MAPPING["resume_evaluation"]
    assert importance == TASK_IMPORTANCE_MAPPING["resume_evaluation"]
    
    # Test with user override
    complexity, importance = classify_task(
        "resume_evaluation",
        user_override={
            "complexity": "simple",
            "importance": "low"
        }
    )
    assert complexity == TaskComplexity.SIMPLE
    assert importance == TaskImportance.LOW
    
    # Test with invalid user override (should use defaults)
    complexity, importance = classify_task(
        "resume_evaluation",
        user_override={
            "complexity": "invalid_value",
            "importance": "invalid_value"
        }
    )
    assert complexity == TASK_COMPLEXITY_MAPPING["resume_evaluation"]
    assert importance == TASK_IMPORTANCE_MAPPING["resume_evaluation"]
    
    # Test unknown task name (should default to MODERATE/MEDIUM)
    complexity, importance = classify_task("unknown_task_name")
    assert complexity == TaskComplexity.MODERATE
    assert importance == TaskImportance.MEDIUM


@patch('app.services.model_selector.get_model_config_for_task')
def test_select_optimized_model(mock_get_model_config):
    """Test optimized model selection based on task parameters."""
    # Mock the get_model_config_for_task function
    mock_get_model_config.return_value = {
        "model": "google:gemini-2.5-pro-preview-03-25",
        "temperature": 0.7,
        "max_tokens": 8000,
        "fallback_config": ["anthropic:claude-3-7-sonnet-latest", "openai:gpt-4.1"],
        "thinking_config": {"thinkingBudget": 15000}
    }
    
    # Test basic model selection
    model_config = select_optimized_model("resume_evaluation")
    assert "model" in model_config
    assert "optimization_metadata" in model_config
    assert model_config["optimization_metadata"]["task_complexity"] == TASK_COMPLEXITY_MAPPING["resume_evaluation"].value
    assert model_config["optimization_metadata"]["task_importance"] == TASK_IMPORTANCE_MAPPING["resume_evaluation"].value
    
    # Test selection with content
    resume_content = "Sample resume content"
    job_description = "Sample job description"
    
    model_config = select_optimized_model(
        "resume_evaluation",
        content=resume_content,
        job_description=job_description
    )
    assert "model" in model_config
    assert "optimization_metadata" in model_config
    assert "request_id" in model_config["optimization_metadata"]
    
    # Test with user override for tier
    model_config = select_optimized_model(
        "resume_evaluation",
        user_override={
            "tier": "economy",
            "cost_sensitivity": 2.0
        }
    )
    assert model_config["optimization_metadata"]["selected_tier"] == "economy"
    assert model_config["optimization_metadata"]["cost_sensitivity"] == 2.0
    
    # Test critical task (should use lower temperature)
    mock_get_model_config.return_value["temperature"] = 0.7
    model_config = select_optimized_model(
        "resume_customization",  # This is a CRITICAL task
    )
    assert model_config["temperature"] < 0.7  # Temperature should be reduced for critical tasks


@patch('app.services.model_optimizer.get_available_models')
def test_track_token_usage(mock_get_available_models):
    """Test token usage tracking and cost calculation."""
    # Mock the available models
    mock_get_available_models.return_value = {
        "google:gemini-2.5-pro-preview-03-25": {
            "provider": ModelProvider.GOOGLE,
            "tier": ModelTier.PREMIUM,
            "cost_per_1k_input": 0.000125,
            "cost_per_1k_output": 0.00375,
            "max_tokens": 1048576,
            "supports_thinking": True,
            "capabilities": [
                ModelCapability.THINKING,
                ModelCapability.STRUCTURED_OUTPUT,
                ModelCapability.DETAILED,
                ModelCapability.CREATIVE,
            ],
        }
    }
    
    # Reset tracking data before test
    reset_cost_tracking()
    
    # Track token usage
    result = track_token_usage(
        model="google:gemini-2.5-pro-preview-03-25",
        task_name="resume_evaluation",
        request_id="test_request_1",
        input_tokens=1000,
        output_tokens=500
    )
    
    # Verify result
    assert result["model"] == "google:gemini-2.5-pro-preview-03-25"
    assert result["input_tokens"] == 1000
    assert result["output_tokens"] == 500
    assert round(result["input_cost"], 6) == 0.000125  # 1000 tokens * $0.000125 per 1k
    assert round(result["output_cost"], 6) == 0.001875  # 500 tokens * $0.00375 per 1k
    assert round(result["total_cost"], 6) == 0.002  # 0.000125 + 0.001875
    
    # Get cost report
    report = get_cost_report()
    
    # Verify report contains our tracked usage
    assert report["total_tokens"] == 1500  # 1000 input + 500 output
    assert round(report["total_cost"], 4) == 0.002  # Same as calculated above
    assert "google:gemini-2.5-pro-preview-03-25" in report["models"]
    assert "resume_evaluation" in report["tasks"]
    assert len(report["recent_requests"]) == 1
    
    # Track another request
    track_token_usage(
        model="google:gemini-2.5-pro-preview-03-25",
        task_name="resume_evaluation",
        request_id="test_request_2",
        input_tokens=2000,
        output_tokens=1000
    )
    
    # Get updated cost report
    report = get_cost_report()
    
    # Verify total has been updated correctly
    assert report["total_tokens"] == 4500  # 1000 + 500 + 2000 + 1000
    assert round(report["total_cost"], 4) == 0.006  # 0.002 + 0.004
    assert report["models"]["google:gemini-2.5-pro-preview-03-25"]["request_count"] == 2
    assert report["tasks"]["resume_evaluation"]["request_count"] == 2
    assert len(report["recent_requests"]) == 2
    
    # Test reset
    reset_cost_tracking()
    report = get_cost_report()
    assert report["total_tokens"] == 0
    assert report["total_cost"] == 0.0
    assert len(report["models"]) == 0
    assert len(report["tasks"]) == 0
    assert len(report["recent_requests"]) == 0


def test_optimize_prompt():
    """Test prompt optimization logic."""
    # Test prompt with examples
    prompt = """
    You are an expert resume evaluator.
    
    Please evaluate this resume against the job description.
    
    This means you should compare skills and experience.
    
    <example>
    Example resume:
    - 5 years of Python experience
    - AWS certified
    
    Example job:
    - Requires Python
    - Requires cloud experience
    
    Evaluation: Good match because Python skills align
    </example>
    
    In other words, tell me if the resume is a good match.
    """
    
    # Test aggressive optimization for simple tasks
    optimized = optimize_prompt(prompt, TaskComplexity.SIMPLE, exclude_examples=True)
    assert "<example>" not in optimized
    assert "This means" not in optimized
    assert "In other words" not in optimized
    assert "expert resume evaluator" in optimized
    assert "evaluate this resume" in optimized
    
    # Test moderate optimization
    optimized = optimize_prompt(prompt, TaskComplexity.MODERATE, exclude_examples=True)
    assert "<example>" not in optimized
    assert "This means" in optimized  # Shouldn't remove explanations for moderate tasks
    assert "In other words" in optimized
    
    # Test minimal optimization for complex tasks
    optimized = optimize_prompt(prompt, TaskComplexity.COMPLEX, exclude_examples=False)
    assert "<example>" in optimized
    assert "This means" in optimized
    assert "In other words" in optimized
    
    # Test whitespace handling
    prompt_with_whitespace = "\n\n\nHello\n\n\nWorld\n\n\n"
    optimized = optimize_prompt(prompt_with_whitespace, TaskComplexity.SIMPLE)
    assert optimized == "Hello\nWorld"