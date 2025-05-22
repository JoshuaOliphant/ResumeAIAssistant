"""
Compatibility module to bridge differences between pydantic_ai versions.
"""
from typing import Any, Dict, Optional, List
from dataclasses import dataclass


@dataclass
class PydanticAIContext:
    """
    Compatibility class for PydanticAI instrumentation across different versions.
    This class provides the expected interface for the logging instrumentation.
    """
    event_type: str
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None
    agent_type: Optional[str] = None
    model: Optional[str] = None
    prompt: Optional[str] = None
    response: Optional[str] = None
    duration_ms: Optional[float] = None
    completion: Optional[str] = None
    error: Optional[Exception] = None
    
    # Add any additional attributes used in the codebase


def adapt_run_context_to_pydanticai_context(run_context: Any) -> PydanticAIContext:
    """
    Adapts a RunContext from newer pydantic_ai versions to the PydanticAIContext 
    format expected by the instrumentation.
    
    Args:
        run_context: A RunContext from pydantic_ai
        
    Returns:
        PydanticAIContext with values mapped from the run_context
    """
    # Extract information from run_context and return a PydanticAIContext
    # This is a placeholder implementation
    event_type = getattr(run_context, "event_type", "unknown")
    
    return PydanticAIContext(
        event_type=event_type,
        agent_id=getattr(run_context, "agent_id", None),
        model=str(getattr(run_context, "model", None)),
        prompt=getattr(run_context, "prompt", None),
        response=getattr(run_context, "response", None),
    )