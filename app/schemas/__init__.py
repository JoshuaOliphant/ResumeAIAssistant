"""
Pydantic schemas for API request and response validation.
"""

from app.schemas.user import User, UserCreate, UserUpdate, UserInDB
from app.schemas.resume import Resume, ResumeCreate, ResumeUpdate, ResumeInDB
from app.schemas.job import Job, JobCreate, JobUpdate, JobInDB
from app.schemas.customize import (
    CustomizeResumeRequest, CustomizedResumeResponse, 
    CustomizationFilter, CustomizationCreate
)
from app.schemas.ats import ATSAnalysisRequest, ATSAnalysisResponse
from app.schemas.cover_letter import CoverLetterRequest, CoverLetterResponse
from app.schemas.requirements import ExtractRequirementsRequest, ExtractRequirementsResponse

# New schemas for claude_code implementation
from app.schemas.claude_code import QueuedTaskResponse, TaskStatusResponse

__all__ = [
    # User schemas
    "User", 
    "UserCreate", 
    "UserUpdate", 
    "UserInDB",
    
    # Resume schemas
    "Resume", 
    "ResumeCreate", 
    "ResumeUpdate", 
    "ResumeInDB",
    
    # Job schemas
    "Job", 
    "JobCreate", 
    "JobUpdate", 
    "JobInDB",
    
    # Customization schemas
    "CustomizeResumeRequest", 
    "CustomizedResumeResponse",
    "CustomizationFilter",
    "CustomizationCreate",
    
    # ATS schemas
    "ATSAnalysisRequest", 
    "ATSAnalysisResponse",
    
    # Cover letter schemas
    "CoverLetterRequest", 
    "CoverLetterResponse",
    
    # Requirements schemas
    "ExtractRequirementsRequest", 
    "ExtractRequirementsResponse",
    
    # Claude Code schemas
    "QueuedTaskResponse",
    "TaskStatusResponse"
]