from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class Requirement(BaseModel):
    """Schema for an individual job requirement"""
    text: str
    priority: int = Field(1, ge=1, le=5, description="Priority level 1-5, with 1 being highest")
    category: Optional[str] = None
    is_required: bool = True


class RequirementCategory(BaseModel):
    """Schema for a category of requirements"""
    category: str
    requirements: List[Requirement]
    weight: float = Field(1.0, ge=0.0, le=2.0, description="Category weight for scoring")


class KeyRequirements(BaseModel):
    """Schema for key requirements extracted from a job description"""
    job_id: Optional[str] = None
    job_title: Optional[str] = None
    company: Optional[str] = None
    job_type: str = Field("default", description="Job type categorization")
    categories: List[RequirementCategory]
    keywords: Dict[str, float] = Field(default_factory=dict, description="Keywords with importance weights")
    
    # Metadata
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confidence level of extraction")
    total_requirements_count: int = 0


class KeyRequirementsRequest(BaseModel):
    """Schema for requesting key requirements extraction"""
    job_description_id: str


class KeyRequirementsContentRequest(BaseModel):
    """Schema for requesting key requirements extraction from content"""
    job_description_content: str
    job_title: Optional[str] = None
    company: Optional[str] = None


class KeyRequirementsResponse(KeyRequirements):
    """Schema for key requirements extraction response"""
    job_description_id: str