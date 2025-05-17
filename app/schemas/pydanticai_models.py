"""
Pydantic models for PydanticAI structured output and agent interactions.

This module centralizes all Pydantic models used with PydanticAI agents to ensure
consistency and proper serialization across the application.
"""
from enum import Enum
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


class ResumeAnalysis(BaseModel):
    """Analysis of resume alignment with a job description."""

    match_score: int = Field(
        ..., ge=0, le=100,
        description="Overall ATS match score 0-100",
        example=72,
    )
    key_matches: List[str] = Field(
        ...,
        description="Skills or experiences that strongly match the job",
        example=["Python", "REST APIs"],
    )
    missing_skills: List[str] = Field(
        ..., description="Important skills missing from the resume", example=["Docker"]
    )
    strengths: List[str] = Field(
        ...,
        description="Resume strengths relevant to the job",
        example=["5 years Python", "AWS certified"],
    )
    weaknesses: List[str] = Field(
        ...,
        description="Areas where the resume could be improved",
        example=["Limited leadership experience"],
    )
    section_analysis: Dict[str, str] = Field(
        ...,
        description="Analysis notes for each resume section",
        example={"Experience": "Relevant but lacks metrics"},
    )


class CustomizationPlan(BaseModel):
    """Detailed plan for improving a resume to reach a target score."""

    target_score: int = Field(
        ..., ge=0, le=100,
        description="Desired match score after customization",
        example=90,
    )
    section_changes: Dict[str, str] = Field(
        ...,
        description="Text changes proposed for each resume section",
        example={"Summary": "Add metrics around API development"},
    )
    keywords_to_add: List[str] = Field(
        ..., description="Keywords to incorporate", example=["Docker", "Kubernetes"]
    )
    format_improvements: List[str] = Field(
        ...,
        description="Formatting adjustments for better ATS readability",
        example=["Use bullet points for achievements"],
    )
    change_explanations: Dict[str, str] = Field(
        ...,
        description="Rationale for each major change",
        example={"Add Docker": "Job description emphasizes containerization"},
    )


class ImplementationResult(BaseModel):
    """Results produced after applying a customization plan."""

    updated_sections: Dict[str, str] = Field(
        ...,
        description="Final text for each updated section",
        example={"Skills": "Python, Docker, Kubernetes"},
    )
    final_score: int = Field(
        ..., ge=0, le=100,
        description="Score achieved after implementing changes",
        example=88,
    )
    applied_keywords: List[str] = Field(
        ..., description="Keywords that were actually added", example=["Docker"]
    )
    notes: Optional[str] = Field(
        None, description="Additional notes about the implementation"
    )


class EvidenceItem(BaseModel):
    """Evidence supporting the truthfulness of a resume claim."""

    claim: str = Field(..., description="Resume statement to verify", example="Led migration to AWS")
    evidence: str = Field(
        ..., description="Supporting proof or reference", example="Project documentation"
    )
    verified: bool = Field(..., description="Whether the evidence validates the claim", example=True)
    notes: Optional[str] = Field(None, description="Additional verification notes")


class VerificationResult(BaseModel):
    """Verification stage output after all changes are applied."""

    is_truthful: bool = Field(..., description="Whether modifications remain truthful", example=True)
    issues: List[str] = Field(
        default_factory=list,
        description="List of truthfulness or quality issues",
        example=["Unable to verify AWS certification"],
    )
    final_score: int = Field(
        ..., ge=0, le=100,
        description="Final ATS match score after verification",
        example=88,
    )
    improvement: int = Field(
        ..., ge=0, le=100,
        description="Score improvement from the original resume",
        example=16,
    )
    section_assessments: Dict[str, str] = Field(
        ...,
        description="Assessment notes for each section",
        example={"Summary": "Improved clarity"},
    )


class WorkflowStage(str, Enum):
    """Enumerates the stages of the resume customization workflow."""

    EVALUATION = "evaluation"
    PLANNING = "planning"
    IMPLEMENTATION = "implementation"
    VERIFICATION = "verification"


class WebSocketProgressUpdate(BaseModel):
    """Progress update payload for WebSocket clients."""

    stage: WorkflowStage = Field(
        ..., description="Current processing stage", example="planning"
    )
    percentage: int = Field(
        ..., ge=0, le=100,
        description="Percentage completion of the current stage",
        example=40,
    )
    message: Optional[str] = Field(
        None, description="Human-readable progress message", example="Analyzing experience section"
    )
    overall_progress: int = Field(
        ..., ge=0, le=100,
        description="Overall workflow progress percentage",
        example=25,
    )
