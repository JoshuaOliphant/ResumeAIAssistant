from typing import Optional
from pydantic import BaseModel, Field


class CoverLetterRequest(BaseModel):
    """Schema for requesting cover letter generation"""
    resume_id: str
    job_description_id: str
    applicant_name: Optional[str] = None
    company_name: Optional[str] = None
    hiring_manager_name: Optional[str] = None
    additional_context: Optional[str] = None
    tone: str = Field(
        default="professional", 
        description="Tone of the cover letter (professional, enthusiastic, formal, etc.)"
    )


class CoverLetterResponse(BaseModel):
    """Schema for cover letter generation response"""
    resume_id: str
    job_description_id: str
    cover_letter_content: str
