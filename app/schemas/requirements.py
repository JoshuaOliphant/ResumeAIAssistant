"""
Pydantic schemas for requirements extraction functionality.
"""

from typing import List, Optional
from pydantic import BaseModel
from enum import Enum


class RequirementCategory(str, Enum):
    """Categories for job requirements."""
    TECHNICAL_SKILLS = "technical_skills"
    SOFT_SKILLS = "soft_skills" 
    EXPERIENCE = "experience"
    EDUCATION = "education"
    CERTIFICATIONS = "certifications"
    TOOLS = "tools"
    DOMAIN_KNOWLEDGE = "domain_knowledge"


class Requirement(BaseModel):
    """Individual job requirement."""
    text: str
    category: RequirementCategory
    importance: str  # "required", "preferred", "nice_to_have"
    confidence: float = 1.0


class KeyRequirements(BaseModel):
    """Extracted key requirements from a job description."""
    requirements: List[Requirement]
    summary: Optional[str] = None


class KeyRequirementsRequest(BaseModel):
    """Request to extract requirements from a job description ID."""
    job_id: int


class KeyRequirementsContentRequest(BaseModel):
    """Request to extract requirements from job description content."""
    content: str


class KeyRequirementsResponse(BaseModel):
    """Response containing extracted requirements."""
    requirements: KeyRequirements
    job_id: Optional[int] = None