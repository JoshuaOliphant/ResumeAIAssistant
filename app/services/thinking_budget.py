"""
Dynamic thinking budget management for PydanticAI models.

This module provides utilities for dynamically determining the appropriate thinking
budget for different AI tasks based on task complexity, model capabilities, and input context.

Key features:
1. Task complexity classification (SIMPLE, MODERATE, COMPLEX, VERY_COMPLEX, CRITICAL)
2. Content analysis to determine appropriate budget
3. Model-specific configuration formatting (Anthropic, Google)
4. Context-aware budget adjustment

Usage examples:
    
    # Get a thinking config for resume evaluation
    thinking_config = get_thinking_config_for_task(
        task_name="resume_evaluation",
        model_provider="anthropic",
        content=resume_content,
        job_description=job_description
    )
    
    # Apply to agent
    evaluator_agent.thinking_config = thinking_config
    
    # Manual calculation with custom metrics
    tokens, config = calculate_thinking_budget(
        task_complexity=TaskComplexity.COMPLEX,
        model_provider="google",
        input_metrics=InputMetrics(total_tokens=2000, section_count=5),
        context_factors={"importance": 1.5}
    )
"""

import logfire
from enum import Enum
from typing import Dict, Any, Optional, Tuple
import math

# Task complexity defines how much thinking a task requires
class TaskComplexity(str, Enum):
    """Enumeration of task complexity levels affecting thinking budget."""
    SIMPLE = "simple"            # Simple classification, keyword extraction
    MODERATE = "moderate"        # Basic analysis, summarization
    COMPLEX = "complex"          # Deep analysis, specialized tasks
    VERY_COMPLEX = "very_complex"  # Multi-stage reasoning, integrating diverse aspects
    CRITICAL = "critical"        # Mission-critical tasks requiring maximum capability

class InputMetrics:
    """Metrics about input content that affect thinking budget requirements."""
    def __init__(
        self,
        total_tokens: int,
        section_count: int = 0,
        keyword_count: int = 0,
        complexity_score: float = 0.0
    ):
        self.total_tokens = total_tokens
        self.section_count = section_count
        self.keyword_count = keyword_count
        self.complexity_score = complexity_score

# Define base thinking budget values for different task complexities
DEFAULT_THINKING_BUDGETS = {
    TaskComplexity.SIMPLE: 0,          # No thinking for simple tasks
    TaskComplexity.MODERATE: 2000,     # Basic thinking for moderate tasks
    TaskComplexity.COMPLEX: 5000,      # Substantial thinking for complex tasks
    TaskComplexity.VERY_COMPLEX: 10000, # Extensive thinking for very complex tasks
    TaskComplexity.CRITICAL: 15000,     # Maximum thinking for critical tasks
}

# Model provider needs different thinking configurations
MODEL_THINKING_CONFIGS = {
    "anthropic": {
        "config_key": "thinking_config",
        "format": {
            "type": "enabled",
            "budget_tokens": "{tokens}"
        }
    },
    "google": {
        "config_key": "thinking_config",
        "format": {
            "thinkingBudget": "{tokens}"
        }
    },
}

def calculate_thinking_budget(
    task_complexity: TaskComplexity,
    model_provider: str,
    input_metrics: Optional[InputMetrics] = None,
    context_factors: Optional[Dict[str, float]] = None,
    max_budget: int = 30000,
    min_budget: int = 0
) -> Tuple[int, Dict[str, Any]]:
    """
    Calculate the optimal thinking budget for a given task.
    
    Args:
        task_complexity: Complexity level of the task
        model_provider: Model provider (anthropic, google)
        input_metrics: Optional metrics about the input content
        context_factors: Optional dictionary of factors to adjust the budget
        max_budget: Maximum allowed thinking budget in tokens
        min_budget: Minimum thinking budget in tokens for non-simple tasks
        
    Returns:
        Tuple of (calculated_tokens, thinking_config_dict)
    """
    from app.core.config import settings
    
    # If thinking is disabled, return 0 budget and empty config
    if not settings.PYDANTICAI_ENABLE_THINKING:
        return 0, {}
    
    # Start with the base budget for the task complexity
    base_budget = DEFAULT_THINKING_BUDGETS[task_complexity]
    
    # Simple tasks always get 0 tokens regardless of other factors
    if task_complexity == TaskComplexity.SIMPLE:
        budget = 0
    else:
        # Start with the base budget
        budget = base_budget
        
        # Apply input metrics adjustments if provided
        if input_metrics:
            # Scale budget based on input size
            input_scale_factor = 1.0
            if input_metrics.total_tokens > 2000:
                # Increase budget for very large inputs, but with diminishing returns
                input_scale_factor = 1.0 + min(1.0, math.log(input_metrics.total_tokens / 2000, 10))
                
            # Scale based on section count (more sections = more complexity)
            section_factor = 1.0
            if input_metrics.section_count > 5:
                section_factor = 1.0 + min(0.5, (input_metrics.section_count - 5) * 0.05)
                
            # Scale based on explicit complexity score if provided
            complexity_factor = 1.0
            if input_metrics.complexity_score > 0:
                complexity_factor = max(0.5, min(2.0, input_metrics.complexity_score))
                
            # Apply all input metric factors
            combined_input_factor = input_scale_factor * section_factor * complexity_factor
            budget = int(budget * combined_input_factor)
        
        # Apply any additional context factors
        if context_factors:
            for factor_name, factor_value in context_factors.items():
                if factor_name == "importance":
                    # Important tasks get more budget
                    budget = int(budget * max(0.5, min(2.0, factor_value)))
                elif factor_name == "time_sensitive":
                    # More time-sensitive tasks might get less budget to complete faster
                    budget = int(budget * max(0.5, min(1.0, 2.0 - factor_value)))
                elif factor_name == "quality_critical":
                    # Quality-critical tasks get more budget
                    budget = int(budget * max(1.0, min(2.0, factor_value)))
    
    # Ensure the budget is within the allowed range
    budget = max(min_budget if task_complexity != TaskComplexity.SIMPLE else 0, 
                min(budget, max_budget))
    
    # Create the thinking config dict based on the model provider
    if model_provider not in MODEL_THINKING_CONFIGS:
        # Default to Anthropic format if provider not recognized
        logfire.warning(
            f"Unknown model provider: {model_provider}, using anthropic format",
            model_provider=model_provider,
            supported_providers=list(MODEL_THINKING_CONFIGS.keys())
        )
        model_provider = "anthropic"
    
    provider_config = MODEL_THINKING_CONFIGS[model_provider]
    config_key = provider_config["config_key"]
    
    # Format the budget value based on the provider's expected format
    format_dict = {}
    for k, v in provider_config["format"].items():
        format_dict[k] = v.format(tokens=budget)
    
    thinking_config = {
        config_key: format_dict
    }
    
    # Just return the inner dict for cleaner configuration
    thinking_config = format_dict
    
    logfire.info(
        "Calculated thinking budget",
        task_complexity=task_complexity.value,
        model_provider=model_provider,
        calculated_budget=budget,
        input_tokens=input_metrics.total_tokens if input_metrics else None,
        context_factors=context_factors
    )
    
    return budget, thinking_config

def get_task_complexity_from_content(
    content: str,
    job_description: Optional[str] = None,
    industry: Optional[str] = None
) -> Tuple[TaskComplexity, InputMetrics]:
    """
    Analyze content to determine task complexity and input metrics.
    
    Args:
        content: The main content to analyze (e.g., resume)
        job_description: Optional job description
        industry: Optional industry name
        
    Returns:
        Tuple of (task_complexity, input_metrics)
    """
    # Calculate basic token count (approximately 4 chars per token)
    content_tokens = len(content) // 4
    job_tokens = len(job_description or "") // 4
    total_tokens = content_tokens + job_tokens
    
    # Count sections (based on markdown headings)
    section_count = content.count('\n#') + content.count('\n##') + content.count('\n###')
    if section_count == 0:
        # Fallback counting - look for common section names at beginning of lines
        common_sections = ["experience", "education", "skills", "projects", "summary", 
                          "objective", "certifications", "awards", "publications"]
        # Look for section-like patterns (word at beginning of line or after newline)
        section_count = sum(1 for section in common_sections 
                          if f"\n{section.lower()}" in content.lower() 
                          or content.lower().startswith(section.lower()))
    
    # Count potential keywords
    # This is a very simple approximation - in a real implementation, 
    # you would use more sophisticated NLP techniques
    potential_keywords = set()
    
    # Add words that are emphasized (bold, italics) or within skill sections
    # Very basic approach for illustration
    for line in content.split('\n'):
        if '**' in line or '*' in line:
            emphasized_words = [w.strip('*') for w in line.split() if '*' in w]
            potential_keywords.update(emphasized_words)
            
        if 'skills' in line.lower() or 'technologies' in line.lower():
            skill_words = [w.strip(',:;') for w in line.split() 
                         if w.strip(',:;') and len(w.strip(',:;')) > 2]
            potential_keywords.update(skill_words)
    
    keyword_count = len(potential_keywords)
    
    # Calculate a complexity score based on multiple factors
    complexity_base = 1.0
    
    # Industry complexity factor
    industry_complexity = 1.0
    if industry:
        complex_industries = ["technology", "healthcare", "finance", "engineering", "legal"]
        if any(ind in industry.lower() for ind in complex_industries):
            industry_complexity = 1.3
    
    # Length complexity factor
    length_complexity = 0.7
    if total_tokens > 2000:
        length_complexity = 1.0
    if total_tokens > 4000:
        length_complexity = 1.3
    
    # Section complexity factor
    section_complexity = 0.8
    if section_count > 5:
        section_complexity = 1.0
    if section_count > 8:
        section_complexity = 1.2
    
    # Combined complexity score
    complexity_score = complexity_base * industry_complexity * length_complexity * section_complexity
    
    # Determine task complexity based on the combined score
    task_complexity = TaskComplexity.MODERATE  # Default
    
    if complexity_score < 0.8:
        task_complexity = TaskComplexity.SIMPLE
    elif complexity_score < 1.0:
        task_complexity = TaskComplexity.MODERATE
    elif complexity_score < 1.3:
        task_complexity = TaskComplexity.COMPLEX
    elif complexity_score < 1.6:
        task_complexity = TaskComplexity.VERY_COMPLEX
    else:
        task_complexity = TaskComplexity.CRITICAL
    
    # Create and return InputMetrics
    metrics = InputMetrics(
        total_tokens=total_tokens,
        section_count=section_count,
        keyword_count=keyword_count,
        complexity_score=complexity_score
    )
    
    logfire.info(
        "Content analysis for thinking budget",
        task_complexity=task_complexity.value,
        total_tokens=total_tokens,
        section_count=section_count,
        keyword_count=keyword_count,
        complexity_score=round(complexity_score, 2),
        industry=industry
    )
    
    return task_complexity, metrics

def get_thinking_config_for_task(
    task_name: str,
    model_provider: str,
    content: Optional[str] = None,
    job_description: Optional[str] = None,
    industry: Optional[str] = None,
    context_factors: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Get the appropriate thinking configuration for a specific task.
    
    Args:
        task_name: Name of the task (e.g., "resume_evaluation", "keyword_extraction")
        model_provider: Model provider (anthropic, google)
        content: Optional content to analyze for complexity
        job_description: Optional job description
        industry: Optional industry
        context_factors: Optional factors affecting the budget
        
    Returns:
        Thinking configuration dictionary for the specified model provider
    """
    # Map task names to complexity levels
    task_complexity_map = {
        # Simple tasks - classification, extraction, etc.
        "keyword_extraction": TaskComplexity.SIMPLE,
        "job_classifier": TaskComplexity.SIMPLE,
        "format_detection": TaskComplexity.SIMPLE,
        "ats_score": TaskComplexity.SIMPLE,
        
        # Moderate tasks - basic analysis
        "resume_summary": TaskComplexity.MODERATE,
        "job_requirements": TaskComplexity.MODERATE,
        "skill_matching": TaskComplexity.MODERATE,
        "formatting_suggestions": TaskComplexity.MODERATE,
        
        # Complex tasks - deeper analysis
        "resume_evaluation": TaskComplexity.COMPLEX,
        "keyword_analysis": TaskComplexity.COMPLEX,
        "section_optimization": TaskComplexity.COMPLEX,
        "experience_analysis": TaskComplexity.COMPLEX,
        
        # Very complex tasks - multi-step reasoning
        "optimization_plan": TaskComplexity.VERY_COMPLEX,
        "resume_implementation": TaskComplexity.VERY_COMPLEX,
        "job_strategy": TaskComplexity.VERY_COMPLEX,
        
        # Critical tasks - requires maximum capability
        "feedback_evaluation": TaskComplexity.CRITICAL,
        "resume_customization": TaskComplexity.CRITICAL,
        "cover_letter_generation": TaskComplexity.CRITICAL,
    }
    
    # Get the complexity level for the task
    if task_name in task_complexity_map:
        base_complexity = task_complexity_map[task_name]
        
        # If we have content, analyze it to potentially adjust complexity
        if content:
            content_complexity, metrics = get_task_complexity_from_content(
                content, job_description, industry
            )
            
            # Use the higher complexity between base and content-derived
            complexity_values = [c.value for c in TaskComplexity]
            task_complexity = base_complexity
            if complexity_values.index(content_complexity.value) > complexity_values.index(base_complexity.value):
                task_complexity = content_complexity
                logfire.info(
                    "Task complexity adjusted based on content analysis",
                    task_name=task_name,
                    base_complexity=base_complexity.value,
                    adjusted_complexity=task_complexity.value
                )
        else:
            # No content to analyze, use base complexity and estimate metrics
            task_complexity = base_complexity
            metrics = InputMetrics(
                total_tokens=1000,  # Default assumption
                section_count=5,    # Default assumption
                keyword_count=20,   # Default assumption
                complexity_score=1.0 # Default assumption
            )
    else:
        # Unknown task, use moderate complexity as default
        logfire.warning(
            f"Unknown task: {task_name}, using moderate complexity",
            task_name=task_name,
            known_tasks=list(task_complexity_map.keys())
        )
        task_complexity = TaskComplexity.MODERATE
        metrics = InputMetrics(
            total_tokens=1000,  # Default assumption
            section_count=5,    # Default assumption
            keyword_count=20,   # Default assumption
            complexity_score=1.0 # Default assumption
        )
    
    # Calculate the budget and get configuration
    _, thinking_config = calculate_thinking_budget(
        task_complexity=task_complexity,
        model_provider=model_provider,
        input_metrics=metrics,
        context_factors=context_factors
    )
    
    return thinking_config