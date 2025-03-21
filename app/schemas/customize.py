from typing import Optional
from pydantic import BaseModel, Field


class ResumeCustomizationRequest(BaseModel):
    """Schema for requesting resume customization"""
    resume_id: str
    job_description_id: str
    customization_strength: int = Field(
        default=2, 
        ge=1, 
        le=3, 
        description="Strength of customization 1-3, with 3 being strongest"
    )
    focus_areas: Optional[str] = Field(
        default=None,
        description="Optional comma-separated list of areas to focus on during customization"
    )


class ResumeCustomizationResponse(BaseModel):
    """Schema for resume customization response"""
    original_resume_id: str
    customized_resume_id: str
    job_description_id: str
