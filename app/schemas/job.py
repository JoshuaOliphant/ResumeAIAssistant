from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class JobDescriptionBase(BaseModel):
    """Base schema for job description data"""

    title: str
    company: Optional[str] = None
    description: str


class JobDescriptionCreate(JobDescriptionBase):
    """Schema for creating a new job description from text"""

    pass


class JobDescriptionCreateFromUrl(BaseModel):
    """Schema for creating a new job description from URL"""

    url: str = Field(..., description="URL to fetch job description from")
    title: Optional[str] = None
    company: Optional[str] = None


class JobDescription(JobDescriptionBase):
    """Schema for a job description"""

    id: str
    source_url: Optional[str] = None
    is_from_url: Optional[bool] = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class JobDescriptionUpdate(BaseModel):
    """Schema for updating a job description"""

    title: Optional[str] = None
    company: Optional[str] = None
    description: Optional[str] = None
