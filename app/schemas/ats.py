from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ATSAnalysisRequest(BaseModel):
    """Schema for requesting ATS analysis"""
    resume_id: str
    job_description_id: str


class KeywordMatch(BaseModel):
    """Schema for keyword matching details"""
    keyword: str
    count_in_resume: int
    count_in_job: int
    is_match: bool


class ATSImprovement(BaseModel):
    """Schema for ATS improvement suggestion"""
    category: str
    suggestion: str
    priority: int = Field(..., ge=1, le=3, description="Priority level 1-3, with 1 being highest")


class SectionScore(BaseModel):
    """Schema for section score details"""
    section: str
    score: float
    weight: float


class ATSAnalysisResponse(BaseModel):
    """Schema for ATS analysis response"""
    resume_id: str
    job_description_id: str
    match_score: int = Field(..., ge=0, le=100, description="Overall match score 0-100")
    matching_keywords: List[KeywordMatch]
    missing_keywords: List[KeywordMatch]
    improvements: List[ATSImprovement]
    job_type: str = "default"
    section_scores: List[Dict[str, Any]] = []
    confidence: str = "medium"
    keyword_density: float = 0.0


class ATSContentAnalysisRequest(BaseModel):
    """Schema for requesting ATS analysis using direct content"""
    resume_content: str
    job_description_content: str


class ATSContentAnalysisResponse(BaseModel):
    """Schema for ATS analysis response based on content"""
    match_score: int = Field(..., ge=0, le=100, description="Overall match score 0-100")
    matching_keywords: List[KeywordMatch]
    missing_keywords: List[KeywordMatch]
    improvements: List[ATSImprovement]
    job_type: str = "default"
    section_scores: List[Dict[str, Any]] = []
    confidence: str = "medium"
    keyword_density: float = 0.0
