from datetime import datetime
from typing import List, Optional, Any
from pydantic import BaseModel, Field, validator


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

    class Config:
        orm_mode = True


class Resume(ResumeBase):
    """Schema for a resume with its most recent version"""
    id: str
    created_at: datetime
    updated_at: datetime
    current_version: Optional[ResumeVersion]

    class Config:
        orm_mode = True


class ResumeDetail(Resume):
    """Schema for a resume with all its versions"""
    versions: List[ResumeVersion]

    class Config:
        orm_mode = True


class ResumeUpdate(BaseModel):
    """Schema for updating a resume"""
    title: Optional[str] = None
    content: Optional[str] = None
