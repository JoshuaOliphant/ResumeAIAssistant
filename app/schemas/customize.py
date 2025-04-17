from typing import Optional, List, Dict, Union
from enum import Enum
from pydantic import BaseModel, Field


class CustomizationLevel(int, Enum):
    """Enum for customization strength levels"""
    CONSERVATIVE = 1
    BALANCED = 2
    EXTENSIVE = 3


class ResumeCustomizationRequest(BaseModel):
    """Schema for requesting resume customization"""
    resume_id: str
    job_description_id: str
    customization_strength: CustomizationLevel = Field(
        default=CustomizationLevel.BALANCED, 
        description="Strength of customization: 1=conservative, 2=balanced, 3=extensive"
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


class RecommendationItem(BaseModel):
    """Schema for an individual customization recommendation"""
    section: str = Field(description="The resume section this recommendation applies to")
    what: str = Field(description="What specific change should be made")
    why: str = Field(description="Why this change will improve ATS performance")
    before_text: Optional[str] = Field(None, description="Original text to be modified")
    after_text: Optional[str] = Field(None, description="Suggested revised text")
    description: str = Field(description="Detailed explanation of the recommendation")


class CustomizationPlanRequest(BaseModel):
    """Schema for requesting a customization plan"""
    resume_id: str
    job_description_id: str
    customization_strength: CustomizationLevel = Field(
        default=CustomizationLevel.BALANCED, 
        description="Strength of customization: 1=conservative, 2=balanced, 3=extensive"
    )
    industry: Optional[str] = Field(
        default=None,
        description="Optional industry name for industry-specific optimization guidance"
    )
    ats_analysis: Optional[Dict] = Field(
        default=None,
        description="Optional ATS analysis results to use as input for the plan"
    )


class CustomizationPlan(BaseModel):
    """Schema for a resume customization plan"""
    summary: str = Field(description="Overall assessment of the resume's alignment with the job")
    job_analysis: str = Field(description="Analysis of the job description's key requirements")
    keywords_to_add: List[str] = Field(description="Important keywords to incorporate")
    formatting_suggestions: List[str] = Field(description="Suggestions for ATS-friendly formatting")
    recommendations: List[RecommendationItem] = Field(description="Detailed customization recommendations")