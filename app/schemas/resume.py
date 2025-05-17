from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ResumeBase(BaseModel):
    """Base schema for resume data"""

    title: str


class ResumeCreate(ResumeBase):
    """Schema for creating a new resume"""

    content: str = Field(..., description="Resume content in Markdown format")


class ResumeVersionBase(BaseModel):
    """Base schema for resume version data"""

    content: str
    version_number: int
    is_customized: bool = False
    job_description_id: Optional[str] = None
    created_at: datetime


class ResumeVersionCreate(BaseModel):
    """Schema for creating a new resume version"""

    content: str
    is_customized: bool = False
    job_description_id: Optional[str] = None


class ResumeVersion(ResumeVersionBase):
    """Schema for a resume version"""

    id: str
    resume_id: str

    model_config = {
        "from_attributes": True
    }


class Resume(ResumeBase):
    """Schema for a resume with its most recent version"""

    id: str
    created_at: datetime
    updated_at: datetime
    current_version: Optional[ResumeVersion]

    model_config = {
        "from_attributes": True
    }


class ResumeDetail(Resume):
    """Schema for a resume with all its versions"""

    versions: List[ResumeVersion]

    model_config = {
        "from_attributes": True
    }


class SectionDiffInfo(BaseModel):
    """Schema for section-level diff information"""

    status: (
        str  # added, removed, unchanged, minor_changes, moderate_changes, major_changes
    )
    change_percentage: float
    content_length: int
    stats: Optional[dict] = None


class ResumeDiffResponse(BaseModel):
    """Schema for a resume diff view response"""

    id: str
    title: str
    original_content: str
    customized_content: str
    diff_content: str
    diff_statistics: dict
    section_analysis: Optional[dict[str, SectionDiffInfo]] = None
    is_diff_view: bool = True


class ResumeUpdate(BaseModel):
    """Schema for updating a resume"""

    title: Optional[str] = None
    content: Optional[str] = None
