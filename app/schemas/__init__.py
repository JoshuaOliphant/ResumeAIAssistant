"""
Pydantic schemas for API request and response validation.
"""

from app.schemas.user import User, UserCreate, UserUpdate, UserInDB
from app.schemas.resume import Resume, ResumeCreate, ResumeUpdate, ResumeDetail, ResumeVersion, ResumeDiffResponse, SectionDiffInfo
from app.schemas.job import JobDescription, JobDescriptionCreate, JobDescriptionUpdate, JobDescriptionCreateFromUrl
from app.schemas.customize import (
    ResumeCustomizationRequest, ResumeCustomizationResponse, 
    CustomizationPlan, CustomizationPlanRequest, CustomizationLevel, RecommendationItem
)
from app.schemas.ats import ATSAnalysisRequest, ATSAnalysisResponse
from app.schemas.requirements import KeyRequirementsRequest, KeyRequirementsContentRequest, KeyRequirementsResponse, KeyRequirements, Requirement, RequirementCategory

# New schemas for claude_code implementation
from app.schemas.claude_code import (
    CustomizeResumeRequest, CustomizedResumeResponse,
    QueuedTaskResponse, TaskStatusResponse, ClaudeCodeError
)

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
    "ResumeDetail",
    "ResumeVersion",
    "ResumeDiffResponse",
    "SectionDiffInfo",
    
    # Job schemas
    "JobDescription", 
    "JobDescriptionCreate", 
    "JobDescriptionUpdate", 
    "JobDescriptionCreateFromUrl",
    
    # Customization schemas
    "ResumeCustomizationRequest", 
    "ResumeCustomizationResponse",
    "CustomizationPlan",
    "CustomizationPlanRequest",
    "CustomizationLevel",
    "RecommendationItem",
    
    # ATS schemas
    "ATSAnalysisRequest", 
    "ATSAnalysisResponse",
    
    # Requirements schemas
    "KeyRequirementsRequest", 
    "KeyRequirementsContentRequest", 
    "KeyRequirementsResponse",
    "KeyRequirements",
    "Requirement",
    "RequirementCategory",
    
    # Claude Code schemas
    "CustomizeResumeRequest",
    "CustomizedResumeResponse",
    "QueuedTaskResponse",
    "TaskStatusResponse",
    "ClaudeCodeError"
]