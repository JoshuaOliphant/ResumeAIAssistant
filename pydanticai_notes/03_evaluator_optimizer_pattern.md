# The Evaluator-Optimizer Pattern with PydanticAI

The Evaluator-Optimizer pattern is a powerful approach for AI tasks that separates evaluation from optimization. This pattern is particularly relevant for the Resume Customization Service redesign.

## Core Concept

The pattern divides a complex task into two distinct phases:

1. **Evaluation**: Assess the current state, identify issues, and make judgments
2. **Optimization**: Generate improvements based on the evaluation

By separating these concerns, we create more focused AI tasks that are easier for models to perform correctly.

## Implementation with PydanticAI

PydanticAI makes it easy to implement this pattern by defining separate Pydantic models for evaluation and optimization:

```python
from pydantic_ai import Agent
from pydantic import BaseModel, Field
from typing import List, Dict

# Evaluation model
class ResumeEvaluation(BaseModel):
    match_score: int = Field(description="Overall match score between resume and job (0-100)")
    strengths: List[str] = Field(description="Key strengths in the resume relative to job requirements")
    gaps: List[str] = Field(description="Areas for improvement or missing skills")
    missing_keywords: List[str] = Field(description="Specific keywords from job description missing in resume")
    recommendations: List[str] = Field(description="Specific recommendations for improvement")

# Optimization model (could be a plan or direct changes)
class ImprovementPlan(BaseModel):
    sections_to_improve: Dict[str, str] = Field(description="Sections needing changes with action plans")
    keywords_to_add: List[str] = Field(description="Keywords to incorporate from job description")
    achievement_enhancements: List[Dict[str, str]] = Field(description="How to enhance specific achievements")
    format_changes: List[str] = Field(description="Suggested format and structure improvements")
    prioritized_changes: List[str] = Field(description="Prioritized list of changes to make")

# Implementation flow
async def customize_resume(resume_content, job_description):
    # Step 1: Evaluation
    evaluator = Agent(
        model="anthropic:claude-3-7-sonnet-latest",
        output_type=ResumeEvaluation
    )
    
    evaluation = await evaluator.run(
        f"""
        Evaluate how well this resume matches the job description:
        
        RESUME:
        {resume_content}
        
        JOB DESCRIPTION:
        {job_description}
        
        Provide a detailed evaluation focusing on match score, strengths, gaps, 
        missing keywords, and specific recommendations.
        """
    )
    
    # Step 2: Optimization (Planning)
    planner = Agent(
        model="anthropic:claude-3-7-sonnet-latest",
        output_type=ImprovementPlan
    )
    
    improvement_plan = await planner.run(
        f"""
        Based on this evaluation, create a detailed plan for improving the resume:
        
        RESUME:
        {resume_content}
        
        JOB DESCRIPTION:
        {job_description}
        
        EVALUATION:
        {evaluation.model_dump_json()}
        
        Create a comprehensive improvement plan that addresses the identified gaps
        and leverages the strengths. Focus on actionable steps.
        """
    )
    
    # Step 3: Implementation (could be another Agent call)
    # ...
    
    return {
        "evaluation": evaluation,
        "plan": improvement_plan,
        # Additional results...
    }
```

## Benefits in the Resume Customization Context

For resume customization, this pattern offers several advantages:

1. **Focused Assessment**: The evaluation phase can thoroughly analyze how well a resume matches a job description
2. **Structured Planning**: The planning phase can create a clear roadmap for improvements
3. **Truthfulness Control**: By separating planning from implementation, we can add safeguards to ensure truthfulness
4. **Reduced Complexity**: Each agent has a more focused task, reducing the chance of errors
5. **Better Progress Tracking**: The distinct phases make it easier to report progress to users

## Application to Our 4-Stage Workflow

Our redesigned Resume Customization Service extends this pattern to a 4-stage workflow:

1. **Evaluation Stage**: Assess resume-job match (evaluator)
2. **Planning Stage**: Create improvement plan (optimizer)
3. **Implementation Stage**: Apply changes to resume (implementer)
4. **Verification Stage**: Verify truthfulness of changes (validator)

This approach aligns with the principles outlined in [Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents), particularly workflow decomposition and validation gates.