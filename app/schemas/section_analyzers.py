"""
Pydantic models for section analyzers and their results.
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from app.services.section_analyzers.base import SectionType


class KeywordMatch(BaseModel):
    """Schema for a keyword match between resume and job description."""
    term: str = Field(..., description="The matched term")
    context_in_resume: str = Field(..., description="Context of the term in the resume")
    context_in_job: str = Field(..., description="Context of the term in the job description")
    importance: int = Field(..., ge=1, le=10, description="Importance of this term (1-10 scale)")


class KeywordGap(BaseModel):
    """Schema for a keyword gap between resume and job description."""
    term: str = Field(..., description="The missing term")
    context_in_job: str = Field(..., description="Context of the term in the job description")
    importance: int = Field(..., ge=1, le=10, description="Importance of this term (1-10 scale)")
    suggested_alternatives: List[str] = Field(..., description="Suggested alternative phrases that could be used")


class SectionRecommendation(BaseModel):
    """Schema for a detailed section improvement recommendation."""
    what: str = Field(..., description="What to improve")
    why: str = Field(..., description="Why this improvement is needed")
    how: str = Field(..., description="How to implement the improvement")
    priority: int = Field(..., ge=1, le=10, description="Priority level (1-10 scale)")
    before_text: Optional[str] = Field(None, description="Original text if replacement is needed")
    after_text: Optional[str] = Field(None, description="Suggested new text")


class SectionIssue(BaseModel):
    """Schema for an issue identified in a resume section."""
    issue_type: str = Field(..., description="Type of issue (format, content, alignment, etc.)")
    description: str = Field(..., description="Description of the issue")
    severity: int = Field(..., ge=1, le=10, description="Severity of the issue (1-10 scale)")
    fix_suggestion: str = Field(..., description="Suggestion for fixing the issue")


# Specialized schemas for each analyzer type

class SkillsAnalysisResult(BaseModel):
    """Schema for skills and qualifications analysis."""
    section_type: SectionType = SectionType.SKILLS
    score: int = Field(..., ge=0, le=100, description="Match score (0-100)")
    job_required_skills: List[str] = Field(..., description="Skills required by the job")
    matching_skills: List[KeywordMatch] = Field(..., description="Skills found in the resume")
    missing_skills: List[KeywordGap] = Field(..., description="Skills missing from the resume")
    skill_categorization: Dict[str, List[str]] = Field(..., description="Categorization of skills (technical, soft, etc.)")
    recommendations: List[SectionRecommendation] = Field(..., description="Recommendations for improving skills section")
    issues: List[SectionIssue] = Field(..., description="Issues identified in the skills section")
    strengths: List[str] = Field(..., description="Strengths of the skills section")
    improvement_suggestions: List[Dict[str, Any]] = Field(..., description="Suggestions for improving skills section")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ExperienceAnalysisResult(BaseModel):
    """Schema for experience alignment analysis."""
    section_type: SectionType = SectionType.EXPERIENCE
    score: int = Field(..., ge=0, le=100, description="Match score (0-100)")
    relevant_experiences: List[Dict[str, Any]] = Field(..., description="Experiences relevant to the job")
    missing_experiences: List[Dict[str, Any]] = Field(..., description="Experience types missing for the job")
    experience_alignment: Dict[str, float] = Field(..., description="Alignment of experiences with job requirements")
    role_specific_keywords: List[str] = Field(..., description="Role-specific keywords found in experiences")
    recommendations: List[SectionRecommendation] = Field(..., description="Recommendations for improving experience section")
    issues: List[SectionIssue] = Field(..., description="Issues identified in the experience section")
    strengths: List[str] = Field(..., description="Strengths of the experience section")
    improvement_suggestions: List[Dict[str, Any]] = Field(..., description="Suggestions for improving experience section")
    keyword_alignment_opportunities: List[Dict[str, Any]] = Field(..., description="Opportunities to align keywords in experiences")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class EducationAnalysisResult(BaseModel):
    """Schema for education and certification analysis."""
    section_type: SectionType = SectionType.EDUCATION
    score: int = Field(..., ge=0, le=100, description="Match score (0-100)")
    education_matches: List[Dict[str, Any]] = Field(..., description="Education credentials matching job requirements")
    education_gaps: List[Dict[str, Any]] = Field(..., description="Education gaps compared to job requirements")
    certification_matches: List[Dict[str, Any]] = Field(..., description="Certifications matching job requirements")
    certification_gaps: List[Dict[str, Any]] = Field(..., description="Certification gaps compared to job requirements")
    recommendations: List[SectionRecommendation] = Field(..., description="Recommendations for improving education section")
    issues: List[SectionIssue] = Field(..., description="Issues identified in the education section")
    strengths: List[str] = Field(..., description="Strengths of the education section")
    improvement_suggestions: List[Dict[str, Any]] = Field(..., description="Suggestions for improving education section")
    relevant_coursework_opportunities: List[str] = Field(..., description="Opportunities to highlight relevant coursework")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class AchievementAnalysisResult(BaseModel):
    """Schema for achievement quantification analysis."""
    section_type: SectionType = SectionType.ACHIEVEMENTS
    score: int = Field(..., ge=0, le=100, description="Match score (0-100)")
    quantified_achievements: List[Dict[str, Any]] = Field(..., description="Achievements with metrics")
    unquantified_achievements: List[Dict[str, Any]] = Field(..., description="Achievements lacking metrics")
    impact_assessment: Dict[str, Any] = Field(..., description="Assessment of achievement impact")
    recommendations: List[SectionRecommendation] = Field(..., description="Recommendations for improving achievements")
    issues: List[SectionIssue] = Field(..., description="Issues identified in achievements")
    strengths: List[str] = Field(..., description="Strengths of the achievements")
    improvement_suggestions: List[Dict[str, Any]] = Field(..., description="Suggestions for improving achievements")
    quantification_opportunities: List[Dict[str, Any]] = Field(..., description="Opportunities to add metrics")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class LanguageToneAnalysisResult(BaseModel):
    """Schema for language and tone optimization analysis."""
    section_type: SectionType = SectionType.ALL
    score: int = Field(..., ge=0, le=100, description="Match score (0-100)")
    tone_assessment: Dict[str, Any] = Field(..., description="Assessment of resume tone")
    language_style_match: Dict[str, Any] = Field(..., description="Match between resume and job language style")
    action_verb_usage: Dict[str, Any] = Field(..., description="Analysis of action verb usage")
    industry_terminology_alignment: Dict[str, Any] = Field(..., description="Alignment with industry terminology")
    recommendations: List[SectionRecommendation] = Field(..., description="Recommendations for improving language/tone")
    issues: List[SectionIssue] = Field(..., description="Issues identified in language/tone")
    strengths: List[str] = Field(..., description="Strengths of the language/tone")
    improvement_suggestions: List[Dict[str, Any]] = Field(..., description="Suggestions for improving language/tone")
    tone_improvement_opportunities: List[Dict[str, Any]] = Field(..., description="Opportunities to improve tone")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class CombinedAnalysisResult(BaseModel):
    """Schema for combined results from all section analyzers."""
    overall_score: int = Field(..., ge=0, le=100, description="Overall match score (0-100)")
    skills_analysis: Optional[SkillsAnalysisResult] = Field(None, description="Skills analysis results")
    experience_analysis: Optional[ExperienceAnalysisResult] = Field(None, description="Experience analysis results")
    education_analysis: Optional[EducationAnalysisResult] = Field(None, description="Education analysis results")
    achievement_analysis: Optional[AchievementAnalysisResult] = Field(None, description="Achievement analysis results")
    language_tone_analysis: Optional[LanguageToneAnalysisResult] = Field(None, description="Language/tone analysis results")
    integrated_recommendations: List[SectionRecommendation] = Field(..., description="Integrated recommendations from all analyzers")
    priority_improvements: List[Dict[str, Any]] = Field(..., description="Prioritized improvements across sections")
    improvement_plan: Dict[str, Any] = Field(..., description="Structured improvement plan")