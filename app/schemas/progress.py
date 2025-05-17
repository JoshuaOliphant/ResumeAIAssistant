from __future__ import annotations

from typing import Dict, Optional

from pydantic import BaseModel, Field, validator


class StageProgress(BaseModel):
    """Progress information for a single stage."""

    status: str = Field("pending")
    progress: int = Field(0, ge=0, le=100)
    details: Optional[str] = None


class WebSocketProgressUpdate(BaseModel):
    """Payload sent over WebSocket to report progress."""

    overall_progress: int = Field(0, ge=0, le=100)
    status: str
    task_statuses: Dict[str, StageProgress]
    elapsed_seconds: int
    estimated_remaining_seconds: Optional[int] = None

    @validator("overall_progress", pre=True, always=True)
    def clamp_progress(cls, value: int) -> int:
        return max(0, min(100, value))


def calculate_overall_progress(
    stages: Dict[str, StageProgress], weights: Dict[str, float]
) -> int:
    """Calculate weighted progress for all stages."""
    total_weight = 0.0
    weighted = 0.0
    for name, stage in stages.items():
        weight = weights.get(name, 0.0)
        total_weight += weight
        weighted += stage.progress * weight
    return int(weighted / total_weight) if total_weight > 0 else 0
