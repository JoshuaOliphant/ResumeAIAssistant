# PydanticAI Models for Resume Customization

This document provides Pydantic models designed specifically for the resume customization workflow, following the evaluator-optimizer pattern.

## Core Schema Models

### Resume Evaluation Models

```python
from pydantic import BaseModel, Field
from typing import List, Dict, Optional

class KeywordMatch(BaseModel):
    keyword: str = Field(description="The matched keyword from the job description")
    context: str = Field(description="Where and how it appears in the resume")
    strength: int = Field(description="Match strength on a scale of 1-10", ge=1, le=10)

class SectionEvaluation(BaseModel):
    section_name: str = Field(description="Name of the resume section")
    relevance_score: int = Field(description="Relevance to job description (1-10)", ge=1, le=10)
    strengths: List[str] = Field(description="Strengths of this section")
    weaknesses: List[str] = Field(description="Areas for improvement in this section")
    missing_elements: List[str] = Field(description="Job requirements not covered in this section")

class ResumeEvaluation(BaseModel):
    overall_match_score: int = Field(
        description="Overall match score between resume and job (0-100)",
        ge=0, 
        le=100
    )
    section_evaluations: List[SectionEvaluation] = Field(
        description="Evaluation of each resume section"
    )
    keyword_matches: List[KeywordMatch] = Field(
        description="Keywords from job found in resume"
    )
    missing_keywords: List[str] = Field(
        description="Important keywords from job missing in resume"
    )
    top_strengths: List[str] = Field(
        description="Top strengths of the resume for this job",
        min_items=1
    )
    key_gaps: List[str] = Field(
        description="Key gaps between resume and job requirements"
    )
    overall_assessment: str = Field(
        description="General assessment of the resume for this job"
    )
```

### Improvement Planning Models

```python
class SectionImprovement(BaseModel):
    section_name: str = Field(description="Name of the resume section to improve")
    current_content: str = Field(description="Current content of the section")
    suggested_changes: List[str] = Field(description="Specific changes to make")
    priority: int = Field(description="Priority of changes (1-10)", ge=1, le=10)
    rationale: str = Field(description="Reasoning behind the suggested changes")

class KeywordStrategy(BaseModel):
    keyword: str = Field(description="Keyword to incorporate")
    suggested_section: str = Field(description="Section where it should be added")
    context_suggestion: str = Field(description="How to naturally incorporate it")

class AchievementEnhancement(BaseModel):
    original_text: str = Field(description="Original achievement statement")
    enhanced_text: str = Field(description="Enhanced version of the statement")
    changes_made: List[str] = Field(description="Description of enhancements made")

class ImprovementPlan(BaseModel):
    section_improvements: List[SectionImprovement] = Field(
        description="Improvements for each section"
    )
    keyword_strategies: List[KeywordStrategy] = Field(
        description="How to incorporate missing keywords"
    )
    achievement_enhancements: List[AchievementEnhancement] = Field(
        description="Achievement statement enhancements"
    )
    format_improvements: List[str] = Field(
        description="Suggestions for format and structure"
    )
    prioritized_changes: List[str] = Field(
        description="All changes in priority order"
    )
    expected_outcome: str = Field(
        description="Expected improvement in match score"
    )
```

### Verification Models

```python
class TruthfulnessIssue(BaseModel):
    content: str = Field(description="The potentially untruthful content")
    section: str = Field(description="Section containing the content")
    severity: str = Field(description="Low, Medium, or High")
    explanation: str = Field(description="Why this might not be truthful")
    suggestion: str = Field(description="How to fix the issue")

class VerificationResult(BaseModel):
    is_truthful: bool = Field(description="Whether the resume is truthful overall")
    issues: List[TruthfulnessIssue] = Field(description="Any truthfulness issues found")
    verification_notes: str = Field(description="Additional notes on verification process")
```

## Implementation Example

```python
from pydantic_ai import Agent

async def evaluate_resume(resume_content, job_description):
    agent = Agent(
        model="anthropic:claude-3-7-sonnet-latest",
        output_type=ResumeEvaluation
    )
    
    prompt = f"""
    You are a professional resume evaluator. Carefully evaluate this resume against
    the job description, focusing on match quality, strengths, and areas for improvement.
    
    RESUME:
    {resume_content}
    
    JOB DESCRIPTION:
    {job_description}
    
    Provide a detailed evaluation of how well this resume matches the job requirements.
    Assess each section, identify keyword matches, gaps, strengths, and provide an overall assessment.
    """
    
    return await agent.run(prompt)

async def generate_improvement_plan(resume_content, job_description, evaluation):
    agent = Agent(
        model="anthropic:claude-3-7-sonnet-latest",
        output_type=ImprovementPlan
    )
    
    prompt = f"""
    You are a professional resume writer. Create a detailed plan to improve this resume
    for the specific job description, based on the evaluation provided.
    
    RESUME:
    {resume_content}
    
    JOB DESCRIPTION:
    {job_description}
    
    EVALUATION:
    {evaluation.model_dump_json(indent=2)}
    
    Create a comprehensive improvement plan focusing on:
    1. Section-specific improvements
    2. Keyword incorporation strategies
    3. Achievement enhancements
    4. Format improvements
    5. Prioritized list of changes
    
    IMPORTANT: All improvements must maintain truthfulness and must be based on
    information actually present in the original resume.
    """
    
    return await agent.run(prompt)

async def verify_customizations(original_resume, customized_resume):
    agent = Agent(
        model="anthropic:claude-3-7-sonnet-latest",
        output_type=VerificationResult
    )
    
    prompt = f"""
    You are a resume verification specialist. Compare the original and customized resumes
    to ensure that the customized version remains truthful and doesn't fabricate experience,
    skills, or achievements.
    
    ORIGINAL RESUME:
    {original_resume}
    
    CUSTOMIZED RESUME:
    {customized_resume}
    
    Carefully verify that all content in the customized resume is supported by evidence
    in the original resume. Flag any content that might be untruthful or exaggerated.
    """
    
    return await agent.run(prompt)
```

## Reusable Models Approach

For reusability, define these models in a dedicated module:

```python
# In app/schemas/pydanticai_models.py
from pydantic import BaseModel, Field
from typing import List, Dict, Optional

# Evaluation models
class KeywordMatch(BaseModel):
    # ... as defined above ...

class SectionEvaluation(BaseModel):
    # ... as defined above ...

class ResumeEvaluation(BaseModel):
    # ... as defined above ...

# Planning models
class SectionImprovement(BaseModel):
    # ... as defined above ...

class KeywordStrategy(BaseModel):
    # ... as defined above ...

class AchievementEnhancement(BaseModel):
    # ... as defined above ...

class ImprovementPlan(BaseModel):
    # ... as defined above ...

# Verification models
class TruthfulnessIssue(BaseModel):
    # ... as defined above ...

class VerificationResult(BaseModel):
    # ... as defined above ...
```

Then import and use these models throughout the application:

```python
from pydantic_ai import Agent
from app.schemas.pydanticai_models import ResumeEvaluation, ImprovementPlan, VerificationResult

class ResumeCustomizer:
    async def _evaluate_resume_job_match(self, resume_content, job_description):
        agent = await self.agent_factory.create_agent(
            output_schema=ResumeEvaluation,
            # ... other parameters ...
        )
        
        # ... implementation ...
        
    async def _generate_improvement_plan(self, resume_content, job_description, evaluation_result):
        agent = await self.agent_factory.create_agent(
            output_schema=ImprovementPlan,
            # ... other parameters ...
        )
        
        # ... implementation ...
        
    async def _verify_customization(self, original_resume, customized_resume, job_description):
        agent = await self.agent_factory.create_agent(
            output_schema=VerificationResult,
            # ... other parameters ...
        )
        
        # ... implementation ...
```

These schema models provide a structured foundation for the entire resume customization process, ensuring consistency, validation, and type safety.