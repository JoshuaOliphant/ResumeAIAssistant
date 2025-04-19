# PydanticAI Integration Plan for ResumeAIAssistant

This document outlines a comprehensive plan to migrate the ResumeAIAssistant from Anthropic's Claude API to a model-agnostic architecture using PydanticAI, leveraging its flexibility, type safety, and structured output validation.

## Progress Tracking

### Overall Progress: ~70% Complete
- ✅ Set up PydanticAI implementation in pydanticai_optimizer.py
- ✅ Fix Anthropic API integration with proper system message format
- ✅ Update model names to use Claude 3.7 Sonnet models
- ✅ Fix error handling with proper fallbacks
- ✅ Update OPTIMIZER_PROMPT with improved instructions
- ✅ Add clear output format instructions to prevent commentary text
- ✅ Implement evaluator-optimizer pattern
- ✅ Configure model fallback chains
- ✅ Integrate with existing APIs

### Pending Items
- Implement enhanced logging with detailed metrics
- Add token counting and usage tracking
- Implement Gemini model integration
- Develop custom tools for keyword extraction and ATS simulation
- Implement model selection strategies
- Create comprehensive integration tests

## Table of Contents
1. [Current Architecture Analysis](#current-architecture-analysis)
2. [PydanticAI Features Overview](#pydanticai-features-overview)
3. [Migration Strategy](#migration-strategy)
4. [Implementation Plan](#implementation-plan)
5. [Evaluator-Optimizer Implementation with PydanticAI](#evaluator-optimizer-implementation-with-pydanticai)
6. [Code Generation Prompts](#code-generation-prompts)

## Current Architecture Analysis

The current architecture uses Claude for several AI-driven features:

1. **Resume Customization** (`customize_resume`): Tailors a resume to match a job description with different customization strengths.
2. **Resume-Job Match Evaluation** (`evaluate_resume_job_match`): Analyzes how well a resume matches a job description.
3. **Optimization Plan Generation** (`generate_optimization_plan`): Creates a detailed plan for improving a resume.
4. **Cover Letter Generation** (`generate_cover_letter`): Creates a personalized cover letter.

The application uses an "evaluator-optimizer" pattern where:
- The "evaluator" analyzes the resume-job match and provides structured feedback
- The "optimizer" then creates a detailed plan based on the evaluation
- This is a multi-step AI workflow with structured outputs

Key components include:
- `claude_service.py`: Core Claude API integration
- `openai_agents_service.py`: OpenAI Agents integration for the same features
- `prompts.py`: Detailed system prompts for different tasks
- `customization_service.py`: Business logic for the evaluator-optimizer pattern
- `ats.py` & `customize.py`: API endpoints

The application currently supports both Claude (via direct API) and OpenAI (via Agents SDK) as providers, with schema definitions for structured outputs already implemented using Pydantic.

## PydanticAI Features Overview

PydanticAI offers several advanced capabilities that can enhance the application:

### Key PydanticAI Features

1. **Model Agnosticism**:
   - Support for multiple LLM providers (OpenAI, Anthropic, Gemini, etc.)
   - Seamless switching between models with fallback mechanisms
   - Same code works across different LLM backends
   - Perfect for avoiding vendor lock-in and optimizing cost/performance

2. **Type-Safe Design**:
   - Built on Pydantic's robust type validation system
   - Early error detection through type checking
   - Clear error messages for invalid responses
   - Ensures consistent and predictable behavior

3. **Structured Outputs**:
   - Uses Pydantic models to define and validate response structures
   - Automatic conversion between JSON and Python objects
   - Support for complex nested models
   - Perfect for the structured evaluation and optimization plans in ResumeAIAssistant

4. **Dependency Injection**:
   - Flexible context passing to agents
   - Dynamic system prompts based on runtime data
   - Simplified testing through dependency substitution
   - Enables more modular and maintainable code

5. **Tool Integration**:
   - Python decorator-based function tools
   - Automatic schema generation from function signatures
   - Type-safe parameter validation
   - Enables extending agents with custom capabilities

6. **Agent Composition Patterns**:
   - Uses Python's native control flow for agent composition
   - Flexible error handling and retry logic
   - Natural integration with Python's async capabilities
   - Supports complex agent workflows through function composition

### Supported Models

1. **OpenAI Models**:
   - GPT-4o, GPT-4o-mini, GPT-4.1
   - Support for context windows up to 128K tokens
   - Function calling for structured outputs
   - Varying price points for cost optimization

2. **Anthropic Models**:
   - Claude 3.7 Sonnet (latest as of April 2025)
   - Claude 3.5 Sonnet (latest as of April 2025)
   - Claude 3.5 Haiku (latest as of April 2025)
   - Claude 3 Series (Opus, Sonnet, Haiku)
   - Extended thinking capability (Claude 3.7)
   - Large context windows
   - Strong reasoning capabilities

3. **Google Gemini Models**:
   - Gemini 2.5 Pro (most advanced reasoning, released March 2025)
   - Gemini 2.5 Flash (excellent price/performance, released April 2025)
   - Gemini 2.0 Flash (multimodal capabilities)
   - Long context support up to 1M tokens
   - Integrated thinking budget controls

4. **Additional Providers**:
   - Mistral, Cohere, Groq, Ollama
   - AWS Bedrock integration
   - Local model support
   - Open-source model compatibility

## Migration Strategy

The migration will follow these principles:

1. **Gradual Model Transition**: Start with Anthropic models for compatibility, then expand to other providers
2. **Backward Compatibility**: Maintain existing API contracts and function signatures
3. **Type Safety Enhancement**: Add Pydantic models for all structured inputs and outputs
4. **Model Flexibility**: Configure model selection based on task requirements
5. **Cost Optimization**: Implement model selection strategies to balance performance and cost
6. **Future-Proofing**: Create a flexible architecture that can adapt to new models and features

## Implementation Plan

The implementation plan builds on the existing codebase, which already has well-defined schemas and model integration patterns through `claude_service.py` and `openai_agents_service.py`.

### Phase 1: PydanticAI Core Integration
1. **Environment Setup**
   - ✅ Install PydanticAI and dependencies
   - ✅ Configure environment variables for API keys (reusing existing structure)
   - Set up enhanced logging with Pydantic Logfire integration
   - ✅ Create `pydanticai_optimizer.py` module leveraging existing patterns

2. **Schema Implementation**
   - ✅ Reuse existing Pydantic models from app.schemas:
     - `ResumeCustomizationRequest/Response` from customize.py
     - `RecommendationItem` and `CustomizationPlan` from customize.py
     - `ATSAnalysisResponse` from ats.py
   - ✅ Adapt/extend models as needed for PydanticAI compatibility
   - ✅ Ensure validation rules match existing schema definitions

3. **Basic Agent Implementation**
   - ✅ Create the base agent architecture based on current service implementations
   - ✅ Implement prompt templates reusing templates from prompts.py
   - ✅ Configure model providers (starting with Anthropic)
   - ✅ Set up error handling and retry logic matching existing patterns
   - Create utility functions for token counting and rate limiting

### Phase 2: Evaluator-Optimizer Implementation
1. **Evaluator Agent**
   - ✅ Define the `ResumeEvaluator` agent with structured output
   - ✅ Implement the existing evaluator prompts from prompts.py
   - Add custom tools for keyword extraction
   - ✅ Create validation logic for evaluation outputs
   - Implement comprehensive logging matching existing patterns
   - ✅ Support extended thinking for Claude 3.7 Sonnet

2. **Optimizer Agent**
   - ✅ Define the `ResumeOptimizer` agent with structured output
   - ✅ Implement the existing optimizer prompts from prompts.py (with improved instructions)
   - Add dependency injection for evaluation results
   - ✅ Create validation logic for optimization plans
   - Add tracing for optimization steps
   - ✅ Support extended thinking for complex optimization tasks

3. **Agent Workflow Integration**
   - ✅ Implement the evaluator-optimizer workflow based on customization_service.py
   - ✅ Define iteration mechanisms and stopping criteria (matching existing behavior)
   - ✅ Create error handling for the complete workflow
   - Implement performance metrics collection
   - Implement detailed logging for each step

### Phase 3: Extension and Optimization
1. **Model Provider Expansion**
   - ✅ Add optimal configuration for Claude 3.7 Sonnet with extended thinking
   - Implement Gemini 2.5 integration with thinking budgets
   - ✅ Add model fallback chains
   - Create model selection strategies
   - Implement A/B testing capabilities

2. **Tool Development**
   - Create keyword extraction tool
   - Implement ATS simulation tool
   - Add formatting analysis tool
   - Develop industry-specific guidance tools
   - Implement scoring and metrics tools

3. **Performance Optimization**
   - Implement caching mechanisms
   - Create token usage optimization
   - Add parallel processing where applicable
   - ✅ Implement model-specific prompt optimization
   - Create performance monitoring dashboards

## Evaluator-Optimizer Implementation with PydanticAI

The evaluator-optimizer pattern is perfect for implementation with PydanticAI's type-safe design and structured outputs. Here's a detailed implementation approach using the existing schema definitions:

### Schema Definition

```python
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal
from app.schemas.customize import CustomizationLevel, CustomizationPlan, RecommendationItem
from app.schemas.ats import KeywordMatch, ATSImprovement, SectionScore

class ResumeEvaluation(BaseModel):
    overall_assessment: str = Field(..., description="Detailed evaluation of resume-job match")
    match_score: int = Field(..., ge=0, le=100, description="Score from 0-100")
    job_key_requirements: List[str] = Field(..., description="Most important job requirements")
    strengths: List[str] = Field(..., description="Candidate strengths relative to job")
    gaps: List[str] = Field(..., description="Missing skills or experiences")
    term_mismatches: List[Dict[str, str]] = Field(..., description="Terminology equivalence")
    section_evaluations: List[Dict[str, Any]] = Field(..., description="Section-level evaluations")
    competitor_analysis: str = Field(..., description="Market comparison")
    reframing_opportunities: List[str] = Field(..., description="Experience reframing ideas")
    experience_preservation_check: str = Field(..., description="Verification of experience preservation")
```

### Agent Implementation

```python
from pydanticai import Agent, tool
from typing import Any, Dict
from app.core.config import settings
from app.core.logging import log_function_call
from app.schemas.customize import CustomizationLevel, CustomizationPlan, RecommendationItem

# Initialize the evaluator agent
evaluator_agent = Agent(
    # Support latest Claude model with extended thinking for better evaluation
    'anthropic:claude-3-7-sonnet-20250501',  # Can be configured based on settings
    output_type=ResumeEvaluation,
    system_prompt="""
    You are an expert resume evaluator and ATS specialist. Your job is to analyze how well a resume matches a job description.
    
    Provide detailed feedback on:
    1. Keyword matches and missing keywords
    2. Overall match score (0-100)
    3. Whether the resume would pass an ATS system
    4. Specific suggestions for improvement
    5. Strengths and weaknesses of the resume
    
    Be thorough in your analysis and provide actionable feedback.
    """,
    # Configure extended thinking for complex analysis
    thinking_config={"budget_tokens": 15000, "type": "enabled"}
)

# Define custom tools
@evaluator_agent.tool
def extract_keywords(job_description: str, max_keywords: int = 20) -> List[str]:
    """
    Extract important keywords from a job description.
    
    Args:
        job_description: The job description text
        max_keywords: Maximum number of keywords to extract
        
    Returns:
        List of important keywords
    """
    # Implementation would use NLP libraries
    # Placeholder for example
    return ["placeholder"]

@evaluator_agent.tool
def simulate_ats(resume: str, job_description: str) -> Dict[str, Any]:
    """
    Simulate how an ATS system would process this resume.
    
    Args:
        resume: The resume text
        job_description: The job description
        
    Returns:
        Dictionary with ATS simulation results
    """
    # Implementation would simulate ATS behavior
    # Placeholder for example
    return {"score": 85, "passes": True}

# Initialize the optimizer agent
optimizer_agent = Agent(
    # Also support latest Claude model with extended thinking
    'anthropic:claude-3-7-sonnet-20250501',  # Can be configured based on settings
    output_type=CustomizationPlan,
    system_prompt="""
    You are an expert resume optimizer. Your job is to create a detailed plan to improve a resume based on:
    
    1. The original resume
    2. The job description
    3. The evaluation feedback
    
    Create a section-by-section plan for improving the resume. For each section, provide:
    1. The original content
    2. The modified content
    3. A rationale for the changes
    
    Focus on addressing the missing keywords and suggestions from the evaluation.
    """,
    # Configure extended thinking for complex optimization
    thinking_config={"budget_tokens": 15000, "type": "enabled"}
)

# Add a model fallback configuration
evaluator_agent.fallback_config = [
    # First fallback to Claude 3.5 Sonnet
    'anthropic:claude-3-5-sonnet-20250501',
    # Then try Gemini 2.5 Flash
    'google:gemini-2.5-flash-preview-04-17',
    # Final fallback to OpenAI
    'openai:gpt-4.1'
]

optimizer_agent.fallback_config = [
    # First fallback to Claude 3.5 Sonnet
    'anthropic:claude-3-5-sonnet-20250501',
    # Then try Gemini 2.5 Pro for complex reasoning
    'google:gemini-2.5-pro-preview-03-25',
    # Final fallback to OpenAI
    'openai:gpt-4.1'
]
```

### Workflow Implementation

```python
@log_function_call
async def evaluate_resume_job_match(
    resume: str, 
    job_description: str,
    basic_analysis: Optional[Dict] = None,
    customization_level: CustomizationLevel = CustomizationLevel.BALANCED,
    industry: Optional[str] = None
) -> Dict:
    """
    Evaluate how well a resume matches a job description.
    
    Args:
        resume: The resume text
        job_description: The job description
        basic_analysis: Optional basic keyword analysis results
        customization_level: Level of customization
        industry: Optional industry context
        
    Returns:
        Structured evaluation of the resume-job match
    """
    # Import prompts dynamically to match existing behavior
    from app.services.prompts import get_customization_level_instructions, get_industry_specific_guidance
    
    # Start timer for performance tracking
    start_time = time.time()
    
    # Create a span in OpenTelemetry for tracing
    with logfire.span("evaluate_resume_job_match_operation") as span:
        span.set_attribute("resume_length", len(resume))
        span.set_attribute("job_description_length", len(job_description))
        span.set_attribute("customization_level", customization_level.value)
        span.set_attribute("industry", industry if industry else "not specified")
        
        # Log operation start
        logfire.info(
            "Starting resume-job match evaluation",
            resume_length=len(resume),
            job_description_length=len(job_description),
            customization_level=customization_level.name,
            industry=industry if industry else "not specified"
        )
        
        # Get customization level specific instructions
        customization_instructions = get_customization_level_instructions(customization_level)
        
        # Get industry-specific guidance if industry is provided
        industry_guidance = ""
        if industry:
            industry_guidance = get_industry_specific_guidance(industry)
            if industry_guidance:
                customization_instructions += f"\n\nINDUSTRY-SPECIFIC GUIDANCE ({industry.upper()}):\n{industry_guidance}"
        
        # Build the input prompt
        prompt = f"""
        Resume:
        {resume}
        
        Job Description:
        {job_description}
        """
        
        if industry:
            prompt += f"\nIndustry: {industry}"
        
        if basic_analysis:
            basic_analysis_str = json.dumps(basic_analysis, indent=2)
            prompt += f"\n\nBasic Analysis:\n{basic_analysis_str}"
        
        # Configure the agent with additional context (using dependency injection)
        # This ensures the tools have access to the necessary data
        context = {
            "extract_keywords_context": {"job_description": job_description},
            "simulate_ats_context": {"resume": resume, "job_description": job_description},
            "customization_level": customization_level.value,
            "industry": industry
        }
        
        try:
            # Run the evaluator agent
            result = await evaluator_agent.run(
                prompt,
                deps=context
            )
            
            # Convert to dict for API compatibility
            evaluation_result = result.dict()
            
            # Log success
            logfire.info(
                "Resume-job evaluation completed successfully",
                response_length=len(str(evaluation_result)),
                duration_seconds=round(time.time() - start_time, 2),
                match_score=evaluation_result.get("match_score")
            )
            
            return evaluation_result
            
        except Exception as e:
            # Log error
            logfire.error(
                "Error evaluating resume job match",
                error=str(e),
                error_type=type(e).__name__,
                duration_seconds=round(time.time() - start_time, 2)
            )
            
            # Re-raise the exception
            raise e

@log_function_call
async def generate_optimization_plan(
    resume: str,
    job_description: str,
    evaluation: Dict,
    customization_level: CustomizationLevel = CustomizationLevel.BALANCED,
    industry: Optional[str] = None
) -> CustomizationPlan:
    """
    Generate a plan to optimize the resume based on evaluation.
    
    Args:
        resume: The resume text
        job_description: The job description
        evaluation: The resume evaluation
        customization_level: How much to customize
        industry: Optional industry context
        
    Returns:
        Structured optimization plan
    """
    # Import prompts dynamically to match existing behavior
    from app.services.prompts import get_customization_level_instructions, get_industry_specific_guidance
    
    # Start timer for performance tracking
    start_time = time.time()
    
    # Create a span in OpenTelemetry for tracing
    with logfire.span("generate_optimization_plan_operation") as span:
        span.set_attribute("resume_length", len(resume))
        span.set_attribute("job_description_length", len(job_description))
        span.set_attribute("customization_level", customization_level.value)
        span.set_attribute("industry", industry if industry else "not specified")
        
        # Log operation start
        logfire.info(
            "Starting optimization plan generation",
            resume_length=len(resume),
            job_description_length=len(job_description),
            customization_level=customization_level.name,
            industry=industry if industry else "not specified"
        )
        
        # Get customization level specific instructions
        customization_instructions = get_customization_level_instructions(customization_level)
        
        # Get industry-specific guidance if industry is provided
        industry_guidance = ""
        if industry:
            industry_guidance = get_industry_specific_guidance(industry)
            if industry_guidance:
                customization_instructions += f"\n\nINDUSTRY-SPECIFIC GUIDANCE ({industry.upper()}):\n{industry_guidance}"
        
        # Build the input prompt
        prompt = f"""
        Resume:
        {resume}
        
        Job Description:
        {job_description}
        
        Evaluation:
        - Score: {evaluation.get('match_score', 0)}/100
        - Missing Keywords: {', '.join(evaluation.get('gaps', []))}
        - Strengths: {', '.join(evaluation.get('strengths', []))}
        - Overall Assessment: {evaluation.get('overall_assessment', '')}
        
        Customization Level: {customization_level.name.lower()}
        """
        
        if industry:
            prompt += f"\nIndustry: {industry}"
        
        try:
            # Run the optimizer agent
            result = await optimizer_agent.run(prompt)
            
            # Already a validated CustomizationPlan instance
            
            # Log success
            logfire.info(
                "Optimization plan generation completed successfully",
                duration_seconds=round(time.time() - start_time, 2),
                recommendation_count=len(result.recommendations)
            )
            
            return result
            
        except Exception as e:
            # Log error
            logfire.error(
                "Error generating optimization plan",
                error=str(e),
                error_type=type(e).__name__,
                duration_seconds=round(time.time() - start_time, 2)
            )
            
            # Re-raise the exception
            raise e

@log_function_call
async def customize_resume(
    resume_content: str,
    job_description: str,
    customization_strength: int = 2,
    focus_areas: Optional[str] = None,
    industry: Optional[str] = None,
    iterations: int = 1
) -> Dict[str, str]:
    """
    Customize a resume to better match a job description.
    
    Args:
        resume_content: The resume text
        job_description: The job description
        customization_strength: How much to customize (1-3)
        focus_areas: Optional areas to focus on
        industry: Optional industry context
        iterations: Number of improvement iterations
        
    Returns:
        Dictionary with original and customized resume
    """
    # Start timer for performance tracking
    start_time = time.time()
    
    # Create a span in OpenTelemetry for tracing
    with logfire.span("customize_resume_operation") as span:
        span.set_attribute("resume_length", len(resume_content))
        span.set_attribute("job_description_length", len(job_description))
        span.set_attribute("customization_strength", customization_strength)
        span.set_attribute("iterations", iterations)
        
        # Log operation start
        logfire.info(
            "Starting resume customization",
            resume_length=len(resume_content),
            job_description_length=len(job_description),
            customization_strength=customization_strength,
            focus_areas=focus_areas,
            iterations=iterations
        )
        
        # Map integer strength to CustomizationLevel enum
        customization_level = CustomizationLevel.BALANCED
        if customization_strength == 1:
            customization_level = CustomizationLevel.CONSERVATIVE
        elif customization_strength == 3:
            customization_level = CustomizationLevel.EXTENSIVE
        
        # Create a specialized customization agent
        customization_agent = Agent(
            # Use the lowest latency model for direct customization
            'anthropic:claude-3-5-haiku-20250501',  
            output_format="text",
            system_prompt=f"""
            You are a professional resume writer helping a job seeker customize their resume for a specific job posting.
            
            Your task is to optimize the resume to better match the job description while maintaining truthfulness.
            
            Guidelines:
            - Emphasize relevant skills and experience already present in the resume
            - Reorder or reword content for better impact and clarity
            - Highlight achievements, especially those with quantifiable results
            - Use industry-specific keywords from the job description
            - Ensure formatting is consistent in Markdown
            - NEVER fabricate experience, skills, or qualifications that aren't in the original resume
            - NEVER invent or add new sections unless explicitly derived from existing content
            
            {"Make minimal, subtle changes to better align the resume with the job description." if customization_strength == 1 else ""}
            {"Make moderate changes to highlight relevant experience and skills that match the job description." if customization_strength == 2 else ""}
            {"Make significant changes to strongly emphasize relevant experience and skills that match the job description." if customization_strength == 3 else ""}
            {f"Focus especially on these areas: {focus_areas}." if focus_areas else ""}
            
            Return ONLY the customized resume in Markdown format, maintaining proper formatting.
            """
        )
        
        current_resume = resume_content
        
        for i in range(iterations):
            # Build the user message
            user_message = f"""
            Here is my current resume in Markdown format:
            
            {current_resume}
            
            Here is the job description I'm applying for:
            
            {job_description}
            
            Please customize my resume for this specific job.
            """
            
            try:
                # Run the agent
                result = await customization_agent.run(user_message)
                
                # Update the current resume with the new version
                current_resume = result
                
                # If we have more iterations, first evaluate the current result
                if i < iterations - 1:
                    # Run evaluation to determine if more iterations needed
                    evaluation = await evaluate_resume_job_match(
                        current_resume, 
                        job_description,
                        customization_level=customization_level,
                        industry=industry
                    )
                    
                    # Check if score is already good enough
                    if evaluation.get("match_score", 0) >= 90:
                        logfire.info(
                            "Early stopping customization - good match score reached",
                            match_score=evaluation.get("match_score", 0),
                            iteration=i+1
                        )
                        break
            except Exception as e:
                # Log the error but return what we have so far
                logfire.error(
                    "Error during resume customization iteration",
                    error=str(e),
                    error_type=type(e).__name__,
                    iteration=i+1,
                    duration_seconds=round(time.time() - start_time, 2)
                )
                # Don't continue iterations if there was an error
                break
        
        # Create the final result
        result = {
            "original_resume": resume_content,
            "customized_resume": current_resume
        }
        
        # Log success
        logfire.info(
            "Resume customization completed successfully",
            duration_seconds=round(time.time() - start_time, 2),
            iterations_completed=i+1
        )
        
        return result
```

### Cover Letter Implementation

```python
class CoverLetter(BaseModel):
    content: str = Field(..., description="The full cover letter text")
    sections: Dict[str, str] = Field(..., description="The cover letter broken down by sections")
    personalization_elements: List[str] = Field(..., description="How the letter was personalized")
    formatting_notes: Optional[str] = Field(None, description="Notes about the formatting")

cover_letter_agent = Agent(
    'anthropic:claude-3-5-sonnet-20250501',  # Can be configured based on settings
    output_type=CoverLetter,
    system_prompt="""
    You are an expert cover letter writer. Your job is to create a compelling, personalized cover letter based on:
    
    1. The resume
    2. The job description
    3. Any personal details provided
    
    Create a professional cover letter that highlights relevant experience and skills,
    demonstrates enthusiasm for the role, and shows cultural fit with the company.
    
    The cover letter should have a clear structure with:
    - Introduction
    - 2-3 body paragraphs highlighting relevant experience
    - Closing paragraph
    
    Keep the tone professional but conversational, and limit to one page.
    """
)

@log_function_call
async def generate_cover_letter(
    resume: str,
    job_description: str,
    applicant_name: Optional[str] = None,
    company_name: str = "the company",
    hiring_manager_name: Optional[str] = None,
    additional_context: Optional[str] = None,
    tone: str = "professional"
) -> Dict:
    """
    Generate a personalized cover letter based on resume and job description.
    
    Args:
        resume: The resume text
        job_description: The job description
        applicant_name: Optional applicant name
        company_name: Company name
        hiring_manager_name: Optional hiring manager name
        additional_context: Optional additional context
        tone: Tone of the letter
        
    Returns:
        Structured cover letter response
    """
    # Start timer for performance tracking
    start_time = time.time()
    
    # Create a span in OpenTelemetry for tracing
    with logfire.span("generate_cover_letter_operation") as span:
        span.set_attribute("resume_length", len(resume))
        span.set_attribute("job_description_length", len(job_description))
        span.set_attribute("has_applicant_name", applicant_name is not None)
        span.set_attribute("company_name", company_name)
        span.set_attribute("has_hiring_manager", hiring_manager_name is not None)
        span.set_attribute("has_additional_context", additional_context is not None)
        span.set_attribute("tone", tone)
        
        # Log operation start
        logfire.info(
            "Starting cover letter generation",
            resume_length=len(resume),
            job_description_length=len(job_description),
            company_name=company_name,
            tone=tone
        )
        
        # Build the input prompt
        prompt = f"""
        Resume:
        {resume}
        
        Job Description:
        {job_description}
        
        Company: {company_name}
        Tone: {tone}
        """
        
        # Add personal details
        personal_details = {}
        if applicant_name:
            personal_details["Applicant Name"] = applicant_name
            prompt += f"\nApplicant Name: {applicant_name}"
            
        if hiring_manager_name:
            personal_details["Hiring Manager"] = hiring_manager_name
            prompt += f"\nHiring Manager: {hiring_manager_name}"
            
        if additional_context:
            personal_details["Additional Context"] = additional_context
            prompt += f"\nAdditional Context: {additional_context}"
        
        # Configure the agent with additional context
        context = {
            "personal_details": personal_details,
            "tone": tone,
            "company_name": company_name
        }
        
        try:
            # Run the cover letter agent
            result = await cover_letter_agent.run(
                prompt,
                deps=context
            )
            
            # Convert to dict for API compatibility
            cover_letter_result = result.dict()
            
            # Log success
            logfire.info(
                "Cover letter generation completed successfully",
                response_length=len(result.content),
                duration_seconds=round(time.time() - start_time, 2)
            )
            
            return cover_letter_result
            
        except Exception as e:
            # Log error
            logfire.error(
                "Error generating cover letter",
                error=str(e),
                error_type=type(e).__name__,
                duration_seconds=round(time.time() - start_time, 2)
            )
            
            # Re-raise the exception
            raise e
```

## Code Generation Prompts

The following section contains structured prompts for generating code for the PydanticAI implementation, aligned with the existing codebase structure.

### Prompt 1: Create PydanticAI Service Module ✅

```
Create a new Python module called pydanticai_service.py that will integrate with the existing services in the ResumeAIAssistant project.

The module should:
1. Import necessary dependencies:
   - PydanticAI (Agent, tool)
   - Pydantic for schema definition
   - Logging from app.core.logging
   - Configuration from app.core.config
   - Existing schemas from app.schemas package
2. Set up proper error handling for API key validation
3. Initialize logging similar to the Claude and OpenAI services
4. Utilize existing Pydantic schemas where possible:
   - ResumeCustomizationRequest/Response from customize.py
   - RecommendationItem and CustomizationPlan from customize.py
   - ATSAnalysisResponse from ats.py
5. Create the agent implementations:
   - Resume Evaluator Agent
   - Resume Optimizer Agent
   - Cover Letter Agent
6. Define the main API functions with the same signatures as claude_service.py:
   - evaluate_resume_job_match
   - generate_optimization_plan
   - customize_resume
   - generate_cover_letter

Include thorough documentation for the module and follow the proper project coding style. The implementation should maintain compatibility with existing services while adding model flexibility.
```
Note: Implemented as pydanticai_optimizer.py instead

### Prompt 2: Update Configuration Module ✅

```
Update the app.core.config.py module to add PydanticAI configuration.

The changes should:
1. Add the following settings:
   - PYDANTICAI_PRIMARY_PROVIDER: Default model provider (e.g., "anthropic")
   - PYDANTICAI_PRIMARY_MODEL: Default model setting (e.g., "claude-3-7-sonnet-20250501")
   - PYDANTICAI_EVALUATOR_MODEL: Model for evaluation tasks
   - PYDANTICAI_OPTIMIZER_MODEL: Model for optimization tasks
   - PYDANTICAI_FALLBACK_MODELS: List of models to try if primary fails
   - PYDANTICAI_THINKING_BUDGET: Token budget for models with thinking capability
   - PYDANTICAI_TEMPERATURE: Temperature setting for agent outputs
   - PYDANTICAI_MAX_TOKENS: Maximum tokens for responses
2. Add model configuration logic for different providers:
   - Anthropic configuration using existing ANTHROPIC_API_KEY
   - OpenAI configuration using existing OPENAI_API_KEY
   - Gemini configuration (new GEMINI_API_KEY)
3. Maintain complete backward compatibility with existing Claude and OpenAI configuration
4. Add proper documentation for all new settings
5. Include error checking for missing API keys

Follow the existing code style and structure in the config module.
```

### Prompt 3: Implement Evaluator-Optimizer Integration ✅

```
Implement the complete evaluator-optimizer pattern with PydanticAI based on the existing implementation in customization_service.py.

The implementation should:
1. Create a new module called pydanticai_optimizer.py in the services directory
2. Utilize the existing schemas in app.schemas
3. Create PydanticAI agents for evaluation and optimization
4. Implement the iterative workflow between evaluation and optimization
5. Add support for progressive enhancement through multiple iterations
6. Include proper logging and monitoring
7. Support fallback to alternative models
8. Maintain compatibility with the existing API
9. Add comprehensive error handling

Follow the existing code patterns in the project and ensure backward compatibility with current features.
```

### Prompt 4: Implement Cover Letter Generation

```
Implement the cover letter generation feature using PydanticAI.

The implementation should:
1. Create a PydanticAI agent for cover letter generation in pydanticai_service.py
2. Use Anthropic Claude 3.7 Sonnet (20250501) as the default model with fallbacks
3. Configure the agent with a system prompt based on existing claude_service.py prompt
4. Implement the generate_cover_letter function with the same signature
5. Add proper error handling and logging
6. Maintain compatibility with the existing API
7. Support all the current personalization options

Follow the existing code patterns in the project and ensure backward compatibility with current features.
```

### Prompt 5: Update API Endpoints ✅ (Partially complete)

```
Update the API endpoints to support the PydanticAI service module.

The implementation should:
1. Update the existing endpoints to use a provider selection mechanism
2. Add a new parameter to API endpoints for selecting the provider (claude, openai, pydanticai)
3. Use the appropriate service module based on the provider parameter
4. Maintain backward compatibility with existing clients
5. Add proper error handling for each provider
6. Add provider-specific logging and monitoring
7. Update the API documentation to include the new provider options

Follow the existing code patterns in the project and ensure backward compatibility with current features.
```

### Prompt 6: Implement Model Provider Management

```
Create a module for managing multiple model providers with PydanticAI called model_manager.py.

The implementation should:
1. Create a ModelManager class:
   - Configure multiple providers (Anthropic, OpenAI, Gemini)
   - Handle API key validation and error handling
   - Support fallback chains between providers
   - Track usage and performance metrics
2. Implement provider-specific configuration:
   - Anthropic provider setup with Claude 3.7 Sonnet (20250501) and extended thinking
   - OpenAI provider setup with GPT-4.1
   - Gemini provider setup with Gemini 2.5 models
   - Support for additional providers
3. Create model selection strategies:
   - Cost-based selection
   - Performance-based selection
   - Task-specific selection
   - Fallback handling
4. Implement token usage tracking:
   - Estimate token usage before requests
   - Track actual token usage
   - Calculate costs across providers
5. Add proper error handling and logging
6. Include comprehensive documentation
7. Add unit tests for provider management

Follow the project's modular architecture and provide thorough documentation.
```

### Prompt 7: Implement Integration Tests ✅ (Started)

```
Create comprehensive tests for the PydanticAI integration in tests/integration/test_pydanticai.py.

The implementation should include:
1. Unit tests for the PydanticAI service:
   - Test the evaluator agent with sample inputs
   - Test the optimizer agent with sample inputs
   - Test the cover letter agent with sample inputs
   - Verify structured output compliance
2. Integration tests for the evaluator-optimizer workflow:
   - Test the complete customization workflow
   - Verify proper handling of iterations
   - Test different customization levels
   - Validate integrated agent behavior
3. API endpoint tests:
   - Test the API endpoints with the pydanticai provider parameter
   - Verify backward compatibility with existing endpoints
   - Test error handling and fallbacks
4. Model fallback tests:
   - Test fallback behavior when a model is unavailable
   - Verify graceful degradation
5. Performance comparison tests:
   - Compare response quality across providers
   - Measure response times
   - Analyze token usage efficiency

Follow the project's testing conventions with pytest and provide comprehensive documentation.
```

## Next Steps and Considerations

### Completed ✅
- **Gradual Rollout**: Begun with Anthropic models for compatibility
- **Prompt Optimization**: Enhanced prompt templates for better response quality
- **System Message Format**: Fixed system message handling for Anthropic API
- **Fallback Implementation**: Added model fallback chains for reliability
- **Base Implementation**: Created core PydanticAI integration with evaluator-optimizer pattern
- **Output Format Control**: Added clear output format instructions to prevent commentary

### Next Priority Tasks
- **Token Tracking**: Implement token usage tracking and analytics
- **Enhanced Logging**: Add detailed logging with performance metrics
- **Gemini Integration**: Add support for Gemini models as fallback
- **Test Completion**: Finish implementation of comprehensive integration tests
- **Tool Development**: Create custom tools for keyword extraction and ATS simulation

### Future Enhancements
- **A/B Testing**: Implement comparison testing between Claude direct implementation, OpenAI Agents SDK, and PydanticAI
- **Cost Monitoring**: Track token usage and costs across different providers
- **Model Experimentation**: Test different models to find optimal price/performance balance
- **Schema Refinement**: Iterate on the Pydantic models based on user feedback
- **Documentation**: Provide comprehensive documentation for the new architecture
- **UI Integration**: Update the frontend to utilize new capabilities
- **Performance Tuning**: Optimize prompt templates and token usage for efficiency
- **Extended Thinking Optimization**: Fine-tune extended thinking budgets for Claude 3.7 Sonnet
- **Thinking Budget Control**: Experiment with Gemini thinking budgets for optimal performance