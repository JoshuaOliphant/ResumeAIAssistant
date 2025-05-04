"""
Pydantic models for PydanticAI structured output and agent interactions.

This module centralizes all Pydantic models used with PydanticAI agents to ensure
consistency and proper serialization across the application.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class TermMismatch(BaseModel):
    """A single term mismatch between resume and job description"""
    resume_term: str = Field(..., description="Term used in the resume")
    job_term: str = Field(..., description="Equivalent term used in the job description")

class SectionEvaluation(BaseModel):
    """Evaluation of a single resume section"""
    section_name: str = Field(..., description="Name of the resume section")
    score: int = Field(..., ge=0, le=100, description="Match score for this section")
    comments: str = Field(..., description="Evaluation comments for this section")

class ResumeEvaluation(BaseModel):
    """Schema for resume evaluation results"""
    overall_assessment: str = Field(..., description="Detailed evaluation of resume-job match")
    match_score: int = Field(..., ge=0, le=100, description="Score from 0-100")
    job_key_requirements: List[str] = Field(..., description="Most important job requirements")
    strengths: List[str] = Field(..., description="Candidate strengths relative to job")
    gaps: List[str] = Field(..., description="Missing skills or experiences")
    term_mismatches: List[TermMismatch] = Field(..., description="Terminology equivalence")
    section_evaluations: List[SectionEvaluation] = Field(..., description="Section-level evaluations")
    competitor_analysis: str = Field(..., description="Market comparison")
    reframing_opportunities: List[str] = Field(..., description="Experience reframing ideas")
    experience_preservation_check: str = Field(..., description="Verification of experience preservation")

class PreservationIssue(BaseModel):
    """Experience preservation issue"""
    item: str = Field(..., description="Experience item that has an issue")
    description: str = Field(..., description="Description of the preservation issue")

class KeywordFeedback(BaseModel):
    """Keyword alignment feedback"""
    keyword: str = Field(..., description="Keyword that needs better alignment")
    suggestion: str = Field(..., description="Suggestion for better keyword alignment")

class FormatFeedback(BaseModel):
    """Formatting feedback item"""
    section: str = Field(..., description="Resume section needing format improvements")
    improvement: str = Field(..., description="Specific formatting improvement suggestion")

class AuthenticityItem(BaseModel):
    """Authenticity concern item"""
    concern: str = Field(..., description="Specific authenticity concern")
    explanation: str = Field(..., description="Explanation of why this is a concern")

class OpportunityItem(BaseModel):
    """Missed opportunity item"""
    opportunity: str = Field(..., description="Missed opportunity in the optimization")
    potential_benefit: str = Field(..., description="Potential benefit of addressing this opportunity")

class FeedbackEvaluation(BaseModel):
    """Schema for evaluation feedback on optimization"""
    requires_iteration: bool = Field(..., description="Whether another iteration is needed")
    experience_preservation_issues: List[PreservationIssue] = Field(..., description="Issues with experience preservation")
    keyword_alignment_feedback: List[KeywordFeedback] = Field(..., description="Feedback on keyword alignment")
    formatting_feedback: List[FormatFeedback] = Field(..., description="Feedback on formatting issues")
    authenticity_concerns: List[AuthenticityItem] = Field(..., description="Concerns about authenticity")
    missed_opportunities: List[OpportunityItem] = Field(..., description="Missed optimization opportunities")
    overall_feedback: str = Field(..., description="Overall feedback assessment")

class CoverLetter(BaseModel):
    """Schema for generated cover letter"""
    content: str = Field(..., description="The full cover letter text")
    sections: Dict[str, str] = Field(..., description="The cover letter broken down by sections")
    personalization_elements: List[str] = Field(..., description="Elements personalized for the applicant/company")
    address_block: Optional[str] = Field(None, description="Formatted address block if provided")
    closing: Optional[str] = Field(None, description="Closing section with signature")
