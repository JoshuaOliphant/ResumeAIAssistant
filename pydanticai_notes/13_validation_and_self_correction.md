# Validation and Self-Correction in PydanticAI

This document explores PydanticAI's validation and self-correction capabilities, which are crucial for building robust AI applications like our resume customization service.

## Output Validation

PydanticAI provides multiple layers of validation:

1. **Pydantic Model Validation**: Basic type checking and validation
2. **Output Validator Functions**: Custom validation logic
3. **Self-Correction**: Automated retry mechanisms

### Output Validator Functions

Output validator functions provide powerful custom validation capabilities:

```python
from pydantic_ai import Agent, ModelRetry
from pydantic_ai.run_context import RunContext
from typing import Dict, List

agent = Agent(
    model="anthropic:claude-3-7-sonnet-latest",
    output_type=ResumeEvaluation
)

@agent.output_validator()
async def validate_resume_evaluation(
    ctx: RunContext, 
    evaluation: ResumeEvaluation
) -> ResumeEvaluation:
    """Validate a resume evaluation output."""
    
    # Check overall score is within range
    if not (0 <= evaluation.match_score <= 100):
        raise ModelRetry(
            "The match score must be between 0 and 100. Please recalculate."
        )
    
    # Ensure there are at least 3 strengths identified
    if len(evaluation.strengths) < 3:
        raise ModelRetry(
            "Please identify at least 3 strengths in the resume."
        )
    
    # Ensure there are at least 2 gaps identified
    if len(evaluation.gaps) < 2:
        raise ModelRetry(
            "Please identify at least 2 areas for improvement in the resume."
        )
    
    # Validation passes, return the output
    return evaluation
```

Validators have access to the full output and run context, allowing for complex validation logic.

## Reflection and Self-Correction

PydanticAI supports self-correction through the `ModelRetry` mechanism:

```python
from pydantic_ai import Agent, ModelRetry
from pydantic_ai.run_context import RunContext
from typing import Dict, List

class TruthfulnessVerifier:
    """Verifies truthfulness of resume customizations."""
    
    @staticmethod
    async def check_truthfulness(
        ctx: RunContext,
        original_resume: str,
        customized_resume: str
    ) -> Dict[str, any]:
        """Check if customizations are truthful based on original resume."""
        # Implementation of truthfulness checking
        fabricated_items = find_fabricated_content(
            original_resume, 
            customized_resume
        )
        
        if fabricated_items:
            raise ModelRetry(
                f"The customized resume contains potentially fabricated information: "
                f"{', '.join(fabricated_items)}. Please revise to ensure all "
                f"content is supported by the original resume."
            )
        
        return {"is_truthful": True}
```

## Retry Handling

Customize retry behavior at different levels:

```python
# Agent-level retry configuration
agent = Agent(
    model="anthropic:claude-3-7-sonnet-latest",
    output_type=ResumeEvaluation,
    retry_count=2  # Default retry count for the agent
)

# Tool-specific retry configuration
@agent.tool(max_retries=3)
async def extract_requirements(
    ctx: RunContext,
    job_description: str
) -> List[str]:
    """Extract key requirements from a job description."""
    # Implementation
    requirements = parse_requirements(job_description)
    
    if not requirements:
        # If no requirements found, retry with more guidance
        raise ModelRetry(
            "No requirements identified. Look for skills, qualifications, "
            "and experience requirements in the job description."
        )
    
    return requirements

# Output validator with custom retry limit
@agent.output_validator(retries=2)
async def validate_improvement_plan(
    ctx: RunContext,
    plan: ImprovementPlan
) -> ImprovementPlan:
    """Validate an improvement plan."""
    # Validation logic
    if not plan.prioritized_changes:
        raise ModelRetry(
            "Improvement plan must include prioritized changes. "
            "Please add a list of prioritized improvements."
        )
    
    return plan
```

## Implementing Self-Correction in the Resume Customizer

For our resume customization service, implement self-correction at multiple stages:

### Evaluation Stage Validation

```python
@agent.output_validator()
async def validate_evaluation(
    ctx: RunContext,
    evaluation: ResumeEvaluation
) -> ResumeEvaluation:
    """Validate evaluation output and trigger retry if needed."""
    
    # Validate match score
    if not (0 <= evaluation.overall_match_score <= 100):
        raise ModelRetry(
            "Overall match score must be between 0 and 100. Please recalculate."
        )
    
    # Validate section evaluations
    if not evaluation.section_evaluations:
        raise ModelRetry(
            "Please evaluate at least the key sections of the resume "
            "(e.g., experience, education, skills)."
        )
    
    # Validate keyword matches
    if not evaluation.keyword_matches and not evaluation.missing_keywords:
        raise ModelRetry(
            "Please identify keyword matches and missing keywords "
            "between the resume and job description."
        )
    
    # Validate strengths and gaps
    if len(evaluation.top_strengths) < 2:
        raise ModelRetry(
            "Please identify at least 2 key strengths in the resume."
        )
    
    if len(evaluation.key_gaps) < 2:
        raise ModelRetry(
            "Please identify at least 2 key gaps between the resume "
            "and job requirements."
        )
    
    return evaluation
```

### Implementation Stage Validation

```python
async def implement_customizations(
    resume_content: str,
    job_description: str,
    improvement_plan: ImprovementPlan,
    evidence_tracker: EvidenceTracker
) -> str:
    """Implement the planned customizations to the resume."""
    
    # Create implementation agent with validation
    agent = Agent(
        model="anthropic:claude-3-7-sonnet-latest",
        output_type=str,  # Plain text output for the resume
        retry_count=2  # Allow up to 2 retries
    )
    
    @agent.output_validator()
    async def validate_customized_resume(
        ctx: RunContext,
        customized_resume: str
    ) -> str:
        """Validate the customized resume for truthfulness and completeness."""
        
        # Check for fabricated content
        try:
            verification_result = evidence_tracker.verify_customization(
                resume_content,
                customized_resume
            )
            
            if not verification_result["verified"]:
                issues = verification_result["issues"]
                raise ModelRetry(
                    f"The customized resume contains potential truthfulness issues: "
                    f"{', '.join(issues)}. Please revise to ensure all content "
                    f"is supported by the original resume."
                )
        except Exception as e:
            raise ModelRetry(f"Error during verification: {str(e)}")
        
        # Check for implementation of planned changes
        for section in improvement_plan.section_improvements:
            if section.priority >= 8:  # High priority changes
                if section.section_name not in customized_resume:
                    raise ModelRetry(
                        f"Missing high-priority improvement for section: "
                        f"{section.section_name}. Please implement the planned changes."
                    )
        
        # Check for keyword incorporation
        for keyword in improvement_plan.keyword_strategies:
            if keyword.keyword not in customized_resume:
                raise ModelRetry(
                    f"Missing keyword '{keyword.keyword}' that was planned for "
                    f"incorporation. Please add this keyword in a natural way."
                )
        
        return customized_resume
    
    # Run implementation with prompt
    prompt = f"""
    Customize this resume according to the improvement plan:
    
    ORIGINAL RESUME:
    {resume_content}
    
    JOB DESCRIPTION:
    {job_description}
    
    IMPROVEMENT PLAN:
    {improvement_plan.model_dump_json(indent=2)}
    
    Implement all the changes specified in the plan while maintaining:
    1. Truthfulness - don't invent experiences or skills
    2. Professional tone and formatting
    3. ATS compatibility
    4. Clarity and conciseness
    
    Return the complete customized resume in Markdown format.
    """
    
    return await agent.run(prompt)
```

## Progressive Validation

For complex outputs, implement progressive validation that builds on previous stages:

```python
class ResumeCustomizer:
    """Customizes resumes using a multi-stage approach with validation."""
    
    async def customize_resume(
        self,
        resume_content: str,
        job_description: str
    ):
        """Customize a resume through multiple validated stages."""
        
        # Stage 1: Evaluation with validation
        evaluation = await self._evaluate_with_validation(
            resume_content, 
            job_description
        )
        
        # Stage 2: Planning with validation based on evaluation
        improvement_plan = await self._plan_with_validation(
            resume_content,
            job_description,
            evaluation
        )
        
        # Extract evidence for truthfulness verification
        evidence = self.evidence_tracker.extract_evidence_from_resume(resume_content)
        
        # Stage 3: Implementation with validation using evidence
        customized_resume = await self._implement_with_validation(
            resume_content,
            job_description,
            improvement_plan,
            evidence
        )
        
        # Stage 4: Final verification with additional checks
        verification_result = await self._verify_with_validation(
            resume_content,
            customized_resume,
            job_description,
            evidence
        )
        
        return {
            "customized_resume": customized_resume,
            "evaluation": evaluation,
            "improvement_plan": improvement_plan,
            "verification_result": verification_result
        }
```

## Best Practices for Validation and Self-Correction

1. **Clear Error Messages**: Provide specific, actionable guidance in `ModelRetry` messages
2. **Appropriate Retry Limits**: Set retry counts based on task complexity
3. **Validation Hierarchy**: Implement validation at multiple levels (model, function, tool)
4. **Graceful Degradation**: Have fallbacks when retries are exhausted
5. **Contextual Validation**: Use context from previous stages to inform validation
6. **Progressive Complexity**: Start with simple validations, add complexity as needed
7. **Domain-Specific Rules**: Implement truthfulness checks specific to resume customization

By incorporating these validation and self-correction mechanisms, our resume customization service will produce more accurate, truthful, and high-quality results, even when the initial AI responses contain errors or issues.