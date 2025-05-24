"""
Pydantic schemas for API request and response validation.
"""

from app.schemas.user import User, UserCreate, UserUpdate, UserInDB
from app.schemas.resume import (
    Resume,
    ResumeCreate,
    ResumeUpdate,
    ResumeDetail,
    ResumeVersion,
    ResumeDiffResponse,
    SectionDiffInfo,
    HtmlDiffResponse,
)
from app.schemas.job import JobDescription, JobDescriptionCreate, JobDescriptionUpdate, JobDescriptionCreateFromUrl
from app.schemas.requirements import KeyRequirementsRequest, KeyRequirementsContentRequest, KeyRequirementsResponse, KeyRequirements, Requirement, RequirementCategory

# Claude Code schemas
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
    "HtmlDiffResponse",
    "SectionDiffInfo",
    
    # Job schemas
    "JobDescription", 
    "JobDescriptionCreate", 
    "JobDescriptionUpdate", 
    "JobDescriptionCreateFromUrl",
    
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
