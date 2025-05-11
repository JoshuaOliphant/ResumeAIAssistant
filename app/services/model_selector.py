"""
Task-based model selection utility for PydanticAI.

This module provides intelligent model selection for different AI tasks based on:
1. Task complexity and requirements
2. Cost efficiency considerations
3. Model capabilities and strengths
4. Fallback preferences for reliability

It works in conjunction with the thinking_budget module to provide comprehensive
model configuration for PydanticAI agents.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import logfire

from app.core.config import settings
from app.services.thinking_budget import get_thinking_config_for_task


class ModelTier(str, Enum):
    """Model tier classification based on capabilities and cost."""

    ECONOMY = "economy"  # Fast, cost-effective models with basic capabilities
    STANDARD = "standard"  # Balanced performance and cost
    PREMIUM = "premium"  # High-capability models with advanced reasoning
    SPECIALIZED = "specialized"  # Models optimized for specific tasks


class ModelProvider(str, Enum):
    """Available model providers."""

    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"
    ANY = "any"  # Any available provider is acceptable


class ModelCapability(str, Enum):
    """Specific capabilities required for tasks."""

    BASIC = "basic"  # Basic text generation
    STRUCTURED_OUTPUT = "structured_output"  # JSON/structured data generation
    THINKING = "thinking"  # Deep reasoning capability
    CREATIVE = "creative"  # Creative writing and ideation
    CODE_GENERATION = "code_generation"  # Code writing and analysis
    CONCISE = "concise"  # Brief, to-the-point responses
    DETAILED = "detailed"  # Comprehensive, thorough responses


# Model registry with details about each model
MODEL_REGISTRY = {
    # Anthropic models
    "anthropic:claude-3-7-sonnet-latest": {
        "provider": ModelProvider.ANTHROPIC,
        "tier": ModelTier.PREMIUM,
        "capabilities": [
            ModelCapability.THINKING,
            ModelCapability.STRUCTURED_OUTPUT,
            ModelCapability.DETAILED,
            ModelCapability.CREATIVE,
        ],
        "cost_per_1k_input": 0.003,
        "cost_per_1k_output": 0.015,
        "max_tokens": 200000,
        "supports_thinking": True,
        "recommended_for": [
            "resume_evaluation",
            "optimization_plan",
            "cover_letter_generation",
            "feedback_evaluation",
        ],
    },
    "anthropic:claude-3-7-haiku-latest": {
        "provider": ModelProvider.ANTHROPIC,
        "tier": ModelTier.STANDARD,
        "capabilities": [
            ModelCapability.STRUCTURED_OUTPUT,
            ModelCapability.CONCISE,
            ModelCapability.BASIC,
        ],
        "cost_per_1k_input": 0.00025,
        "cost_per_1k_output": 0.00125,
        "max_tokens": 200000,
        "supports_thinking": False,
        "recommended_for": ["keyword_extraction", "job_classifier", "skill_matching"],
    },
    # OpenAI models
    "openai:gpt-4.1": {
        "provider": ModelProvider.OPENAI,
        "tier": ModelTier.PREMIUM,
        "capabilities": [
            ModelCapability.STRUCTURED_OUTPUT,
            ModelCapability.DETAILED,
            ModelCapability.CREATIVE,
            ModelCapability.CODE_GENERATION,
        ],
        "cost_per_1k_input": 0.01,
        "cost_per_1k_output": 0.03,
        "max_tokens": 128000,
        "supports_thinking": False,
        "recommended_for": ["resume_evaluation", "optimization_plan"],
    },
    "openai:gpt-4o": {
        "provider": ModelProvider.OPENAI,
        "tier": ModelTier.STANDARD,
        "capabilities": [
            ModelCapability.STRUCTURED_OUTPUT,
            ModelCapability.CREATIVE,
            ModelCapability.CODE_GENERATION,
        ],
        "cost_per_1k_input": 0.005,
        "cost_per_1k_output": 0.015,
        "max_tokens": 128000,
        "supports_thinking": False,
        "recommended_for": ["resume_implementation", "skill_matching"],
    },
    # Google models
    "google:gemini-2.5-pro-preview-03-25": {
        "provider": ModelProvider.GOOGLE,
        "tier": ModelTier.PREMIUM,
        "capabilities": [
            ModelCapability.THINKING,
            ModelCapability.STRUCTURED_OUTPUT,
            ModelCapability.DETAILED,
            ModelCapability.CREATIVE,
        ],
        "cost_per_1k_input": 0.000125,
        "cost_per_1k_output": 0.00375,
        "max_tokens": 1048576,  # 1M tokens
        "supports_thinking": True,
        "recommended_for": ["resume_evaluation", "optimization_plan", "job_strategy"],
    },
    "google:gemini-2.5-flash-preview-04-17": {
        "provider": ModelProvider.GOOGLE,
        "tier": ModelTier.ECONOMY,
        "capabilities": [
            ModelCapability.STRUCTURED_OUTPUT,
            ModelCapability.CONCISE,
            ModelCapability.BASIC,
        ],
        "cost_per_1k_input": 0.0000625,
        "cost_per_1k_output": 0.00025,
        "max_tokens": 1048576,  # 1M tokens
        "supports_thinking": True,
        "recommended_for": ["keyword_extraction", "job_classifier", "format_detection"],
    },
}

# Task requirements mapping
TASK_REQUIREMENTS = {
    # Evaluation tasks
    "resume_evaluation": {
        "preferred_tier": ModelTier.PREMIUM,
        "required_capabilities": [
            ModelCapability.STRUCTURED_OUTPUT,
            ModelCapability.THINKING,
            ModelCapability.DETAILED,
        ],
        "fallback_tier": ModelTier.STANDARD,
        "budget_sensitivity": "low",  # Less sensitive to cost
        "token_requirements": "high",  # Needs larger context window
    },
    "feedback_evaluation": {
        "preferred_tier": ModelTier.PREMIUM,
        "required_capabilities": [
            ModelCapability.STRUCTURED_OUTPUT,
            ModelCapability.THINKING,
            ModelCapability.DETAILED,
        ],
        "fallback_tier": ModelTier.PREMIUM,  # Still need premium for feedback
        "budget_sensitivity": "low",
        "token_requirements": "high",
    },
    # Optimization tasks
    "optimization_plan": {
        "preferred_tier": ModelTier.PREMIUM,
        "required_capabilities": [
            ModelCapability.STRUCTURED_OUTPUT,
            ModelCapability.THINKING,
            ModelCapability.CREATIVE,
        ],
        "fallback_tier": ModelTier.STANDARD,
        "budget_sensitivity": "medium",
        "token_requirements": "high",
    },
    "optimization_plan_feedback": {
        "preferred_tier": ModelTier.PREMIUM,
        "required_capabilities": [
            ModelCapability.STRUCTURED_OUTPUT,
            ModelCapability.THINKING,
            ModelCapability.DETAILED,
        ],
        "fallback_tier": ModelTier.PREMIUM,
        "budget_sensitivity": "low",
        "token_requirements": "high",
    },
    "resume_implementation": {
        "preferred_tier": ModelTier.STANDARD,
        "required_capabilities": [ModelCapability.BASIC, ModelCapability.CREATIVE],
        "fallback_tier": ModelTier.ECONOMY,
        "budget_sensitivity": "medium",
        "token_requirements": "medium",
    },
    # Simple tasks
    "keyword_extraction": {
        "preferred_tier": ModelTier.ECONOMY,
        "required_capabilities": [
            ModelCapability.STRUCTURED_OUTPUT,
            ModelCapability.CONCISE,
        ],
        "fallback_tier": ModelTier.ECONOMY,
        "budget_sensitivity": "high",
        "token_requirements": "low",
    },
    "job_classifier": {
        "preferred_tier": ModelTier.ECONOMY,
        "required_capabilities": [
            ModelCapability.STRUCTURED_OUTPUT,
            ModelCapability.CONCISE,
        ],
        "fallback_tier": ModelTier.ECONOMY,
        "budget_sensitivity": "high",
        "token_requirements": "low",
    },
    "format_detection": {
        "preferred_tier": ModelTier.ECONOMY,
        "required_capabilities": [
            ModelCapability.STRUCTURED_OUTPUT,
            ModelCapability.CONCISE,
        ],
        "fallback_tier": ModelTier.ECONOMY,
        "budget_sensitivity": "high",
        "token_requirements": "low",
    },
    # Content generation
    "cover_letter_generation": {
        "preferred_tier": ModelTier.PREMIUM,
        "required_capabilities": [
            ModelCapability.CREATIVE,
            ModelCapability.DETAILED,
            ModelCapability.STRUCTURED_OUTPUT,
        ],
        "fallback_tier": ModelTier.STANDARD,
        "budget_sensitivity": "medium",
        "token_requirements": "medium",
    },
    "resume_summary": {
        "preferred_tier": ModelTier.STANDARD,
        "required_capabilities": [ModelCapability.CONCISE, ModelCapability.CREATIVE],
        "fallback_tier": ModelTier.ECONOMY,
        "budget_sensitivity": "medium",
        "token_requirements": "low",
    },
    # Analysis tasks
    "skill_matching": {
        "preferred_tier": ModelTier.STANDARD,
        "required_capabilities": [
            ModelCapability.STRUCTURED_OUTPUT,
            ModelCapability.CONCISE,
        ],
        "fallback_tier": ModelTier.ECONOMY,
        "budget_sensitivity": "medium",
        "token_requirements": "medium",
    },
    "job_strategy": {
        "preferred_tier": ModelTier.PREMIUM,
        "required_capabilities": [
            ModelCapability.THINKING,
            ModelCapability.DETAILED,
            ModelCapability.CREATIVE,
        ],
        "fallback_tier": ModelTier.STANDARD,
        "budget_sensitivity": "low",
        "token_requirements": "medium",
    },
}


def get_available_models() -> Dict[str, Dict]:
    """
    Get all available models based on environment configuration.

    Returns:
        Dictionary of available models and their configurations
    """
    available_models = {}

    # Check which providers are available based on API keys
    providers = []

    if settings.ANTHROPIC_API_KEY:
        providers.append(ModelProvider.ANTHROPIC)

    if settings.OPENAI_API_KEY:
        providers.append(ModelProvider.OPENAI)

    if settings.GEMINI_API_KEY:
        providers.append(ModelProvider.GOOGLE)

    # Filter models to only those from available providers
    for model_name, config in MODEL_REGISTRY.items():
        if config["provider"] in providers:
            available_models[model_name] = config

    logfire.info(
        "Available models determined",
        provider_count=len(providers),
        model_count=len(available_models),
        providers=[p.value for p in providers],
    )

    return available_models


def select_model_for_task(
    task_name: str,
    preferred_provider: Optional[ModelProvider] = None,
    cost_sensitivity: float = 1.0,  # 0.0 = cost no object, 1.0 = balanced, 2.0 = cost-focused
    content_length: Optional[int] = None,
    override_requirements: Optional[Dict[str, Any]] = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    Select the most appropriate model for a given task.

    Args:
        task_name: The name of the task to select a model for
        preferred_provider: Optional preference for a specific provider
        cost_sensitivity: How important cost optimization is (0.0-2.0)
        content_length: Optional estimate of input content length in tokens
        override_requirements: Optional override for task requirements

    Returns:
        Tuple of (selected_model_name, model_config)
    """
    # Get available models
    available_models = get_available_models()

    if not available_models:
        error_msg = "No models available - check API keys"
        logfire.error(error_msg)
        raise ValueError(error_msg)

    # Get task requirements
    if task_name in TASK_REQUIREMENTS:
        requirements = TASK_REQUIREMENTS[task_name].copy()
    else:
        # Default to premium tier with structured output if task not found
        print(f"WARNING: Task '{task_name}' not found in requirements registry")
        try:
            logfire.info(
                f"Task '{task_name}' not found in requirements registry",
                task_name=task_name,
                available_tasks=list(TASK_REQUIREMENTS.keys()),
                level="warning",
            )
        except Exception:
            pass
        requirements = {
            "preferred_tier": ModelTier.STANDARD,
            "required_capabilities": [ModelCapability.STRUCTURED_OUTPUT],
            "fallback_tier": ModelTier.ECONOMY,
            "budget_sensitivity": "medium",
            "token_requirements": "medium",
        }

    # Apply any requirement overrides
    if override_requirements:
        for key, value in override_requirements.items():
            requirements[key] = value

    # Filter models by required capabilities
    capable_models = {}
    for model_name, config in available_models.items():
        # Check if model has all required capabilities
        if all(
            cap in config["capabilities"]
            for cap in requirements["required_capabilities"]
        ):
            capable_models[model_name] = config

    # If no models meet capability requirements, log error and fall back to any available model
    if not capable_models:
        print(
            f"WARNING: No models meet all capability requirements for {task_name}, using any available"
        )
        try:
            logfire.info(
                "No models meet all capability requirements, using any available model",
                task_name=task_name,
                required_capabilities=[
                    cap.value for cap in requirements["required_capabilities"]
                ],
                level="warning",
            )
        except Exception:
            pass
        capable_models = available_models

    # Filter by provider preference if specified
    if preferred_provider and preferred_provider != ModelProvider.ANY:
        provider_models = {
            name: config
            for name, config in capable_models.items()
            if config["provider"] == preferred_provider
        }

        # Only apply provider filter if it doesn't eliminate all options
        if provider_models:
            capable_models = provider_models
        else:
            print(
                f"WARNING: Preferred provider {preferred_provider.value} has no suitable models, falling back to others"
            )
            try:
                logfire.info(
                    f"Preferred provider {preferred_provider.value} has no suitable models",
                    preferred_provider=preferred_provider.value,
                    falling_back_to_other_providers=True,
                    level="warning",
                )
            except Exception:
                pass

    # Check content length against model limits if specified
    if content_length:
        sufficient_models = {
            name: config
            for name, config in capable_models.items()
            if config["max_tokens"] >= content_length * 1.5  # Allow 50% buffer
        }

        # Only apply length filter if it doesn't eliminate all options
        if sufficient_models:
            capable_models = sufficient_models
        else:
            print(
                f"WARNING: No models have sufficient context length for content of {content_length} tokens, using available"
            )
            try:
                logfire.info(
                    "No models have sufficient context length, using available models",
                    required_length=content_length,
                    max_available=max(
                        config["max_tokens"] for config in capable_models.values()
                    ),
                    level="warning",
                )
            except Exception:
                pass

    # Score models based on tier match, capabilities, and cost
    model_scores = {}

    # Budget sensitivity factor
    budget_factor = 1.0
    if requirements["budget_sensitivity"] == "low":
        budget_factor = 0.5
    elif requirements["budget_sensitivity"] == "high":
        budget_factor = 2.0

    # Apply user's cost sensitivity adjustment
    budget_factor *= cost_sensitivity

    for model_name, config in capable_models.items():
        # Base score starts at 100
        score = 100.0

        # Tier matching
        if config["tier"] == requirements["preferred_tier"]:
            score += 50.0
        elif config["tier"] == requirements["fallback_tier"]:
            score += 25.0

        # Extra capabilities beyond requirements
        extra_capabilities = [
            cap
            for cap in config["capabilities"]
            if cap not in requirements["required_capabilities"]
        ]
        score += len(extra_capabilities) * 5.0

        # Special bonus for thinking capability if task benefits from it
        if ModelCapability.THINKING in config["capabilities"] and (
            task_name.startswith("resume_evaluation")
            or task_name.startswith("optimization")
            or task_name.startswith("feedback")
        ):
            score += 20.0

        # Cost factor - penalize higher cost models based on budget sensitivity
        cost_penalty = (
            (config["cost_per_1k_input"] + config["cost_per_1k_output"] * 3)
            * 1000
            * budget_factor
        )
        score -= cost_penalty

        # Provider preference bonus
        if preferred_provider and config["provider"] == preferred_provider:
            score += 30.0

        # Store the final score
        model_scores[model_name] = score

    # Get the highest scoring model
    if not model_scores:
        error_msg = f"No suitable models found for task: {task_name}"
        logfire.error(error_msg)
        raise ValueError(error_msg)

    selected_model = max(model_scores.items(), key=lambda x: x[1])[0]
    selected_config = available_models[selected_model]

    # Log the selection with detailed debugging information
    logfire.info(
        "Model selected for task",
        task=task_name,
        selected_model=selected_model,
        provider=selected_config["provider"].value,
        tier=selected_config["tier"].value,
        score=model_scores[selected_model],
        preferred_provider=preferred_provider.value if preferred_provider else "None",
        cost_sensitivity=cost_sensitivity,
        available_providers=[
            config["provider"].value for name, config in available_models.items()
        ],
        task_requirements=requirements,
        capabilities=selected_config["capabilities"],
        top_scores=dict(
            sorted(model_scores.items(), key=lambda x: x[1], reverse=True)[:3]
        ),
        all_scores=model_scores,
    )

    return selected_model, selected_config


def get_fallback_chain(
    primary_model: str, task_name: str, max_fallbacks: int = 3
) -> List[str]:
    """
    Generate a fallback chain for a given primary model and task.

    Args:
        primary_model: The primary model name
        task_name: The task name
        max_fallbacks: Maximum number of fallbacks to include

    Returns:
        List of fallback model names
    """
    # Get available models
    available_models = get_available_models()

    if primary_model not in available_models:
        error_msg = f"Primary model {primary_model} not in available models"
        logfire.error(error_msg)
        raise ValueError(error_msg)

    # Get the primary model's provider and tier
    primary_config = available_models[primary_model]
    primary_provider = primary_config["provider"]
    primary_tier = primary_config["tier"]

    # Get task requirements
    if task_name in TASK_REQUIREMENTS:
        requirements = TASK_REQUIREMENTS[task_name]
    else:
        # Default requirements if task not found
        requirements = {
            "preferred_tier": ModelTier.STANDARD,
            "required_capabilities": [ModelCapability.STRUCTURED_OUTPUT],
            "fallback_tier": ModelTier.ECONOMY,
            "budget_sensitivity": "medium",
        }

    # Strategy for fallbacks:
    # 1. Same provider, equivalent tier
    # 2. Different provider, equivalent tier
    # 3. Same provider, lower tier
    # 4. Different provider, lower tier

    fallbacks = []

    # Same provider, equivalent tier
    for model_name, config in available_models.items():
        if (
            model_name != primary_model
            and config["provider"] == primary_provider
            and config["tier"] == primary_tier
        ):
            fallbacks.append(model_name)

    # Different provider, equivalent tier
    for model_name, config in available_models.items():
        if (
            model_name != primary_model
            and config["provider"] != primary_provider
            and config["tier"] == primary_tier
            and model_name not in fallbacks
        ):
            fallbacks.append(model_name)

    # Same provider, fallback tier
    for model_name, config in available_models.items():
        if (
            model_name != primary_model
            and config["provider"] == primary_provider
            and config["tier"] == requirements["fallback_tier"]
            and model_name not in fallbacks
        ):
            fallbacks.append(model_name)

    # Different provider, fallback tier
    for model_name, config in available_models.items():
        if (
            model_name != primary_model
            and config["provider"] != primary_provider
            and config["tier"] == requirements["fallback_tier"]
            and model_name not in fallbacks
        ):
            fallbacks.append(model_name)

    # Any remaining models that have required capabilities
    for model_name, config in available_models.items():
        if (
            model_name != primary_model
            and model_name not in fallbacks
            and all(
                cap in config["capabilities"]
                for cap in requirements["required_capabilities"]
            )
        ):
            fallbacks.append(model_name)

    # Limit to max_fallbacks
    fallbacks = fallbacks[:max_fallbacks]

    logfire.info(
        "Generated fallback chain",
        primary_model=primary_model,
        fallbacks=fallbacks,
        task_name=task_name,
    )

    return fallbacks


def get_model_config_for_task(
    task_name: str,
    content: Optional[str] = None,
    job_description: Optional[str] = None,
    industry: Optional[str] = None,
    preferred_provider: Optional[str] = None,
    cost_sensitivity: float = 1.0,
) -> Dict[str, Any]:
    """
    Get complete model configuration for a task including model name and thinking budget.

    Args:
        task_name: Name of the task
        content: Optional content to analyze for complexity (e.g., resume)
        job_description: Optional job description
        industry: Optional industry
        preferred_provider: Optional preference for model provider
        cost_sensitivity: How important cost is (0.0-2.0)

    Returns:
        Complete configuration dictionary for PydanticAI agent
    """
    # Convert preferred provider string to enum if provided
    provider_enum = None
    if preferred_provider:
        try:
            provider_enum = ModelProvider(preferred_provider)
        except ValueError:
            logfire.warning(
                f"Unknown provider: {preferred_provider}, ignoring preference",
                preferred_provider=preferred_provider,
                valid_providers=[p.value for p in ModelProvider],
            )

    # Calculate content length if provided
    content_length = None
    if content:
        # Approximate tokens (4 chars per token)
        content_length = len(content) // 4
        if job_description:
            content_length += len(job_description) // 4

    # Select the best model for this task
    model_name, model_config = select_model_for_task(
        task_name=task_name,
        preferred_provider=provider_enum,
        cost_sensitivity=cost_sensitivity,
        content_length=content_length,
    )

    # Generate fallback chain
    fallbacks = get_fallback_chain(primary_model=model_name, task_name=task_name)

    # Get model provider
    model_provider = model_config["provider"].value

    # Generate thinking configuration if supported
    thinking_config = None
    if model_config["supports_thinking"]:
        thinking_config = get_thinking_config_for_task(
            task_name=task_name,
            model_provider=model_provider,
            content=content,
            job_description=job_description,
            industry=industry,
        )

    # Build the complete configuration
    complete_config = {
        "model": model_name,
        "temperature": settings.PYDANTICAI_TEMPERATURE,
        "max_tokens": settings.PYDANTICAI_MAX_TOKENS,
        "fallback_config": fallbacks,
    }

    # Add thinking configuration if available
    if thinking_config:
        complete_config["thinking_config"] = thinking_config
        
    # Try to use the model optimizer for more advanced tiered processing
    try:
        from app.services.model_optimizer import select_optimized_model
        
        # If model_optimizer is available, use it to get optimized settings
        optimized_config = select_optimized_model(
            task_name=task_name,
            content=content,
            job_description=job_description,
            industry=industry,
            preferred_provider=preferred_provider,
            user_override={
                "cost_sensitivity": cost_sensitivity
            }
        )
        
        # Use the optimized config instead, but retain fallbacks
        fallbacks_copy = complete_config["fallback_config"]
        complete_config = optimized_config
        
        # Ensure fallbacks are properly maintained
        if "fallback_config" not in complete_config or not complete_config["fallback_config"]:
            complete_config["fallback_config"] = fallbacks_copy
        
        logfire.info(
            "Using optimized model configuration",
            task=task_name,
            model=complete_config["model"],
            optimized=True,
            optimization_metadata=complete_config.get("optimization_metadata", {})
        )
    except (ImportError, Exception) as e:
        # model_optimizer might not be available or has an error,
        # continue with standard approach
        logfire.info(
            "Generated complete model configuration (standard)",
            task=task_name,
            model=model_name,
            provider=model_provider,
            has_thinking=thinking_config is not None,
            fallback_count=len(fallbacks),
            optimization_error=str(e) if isinstance(e, Exception) and not isinstance(e, ImportError) else None
        )

    return complete_config
