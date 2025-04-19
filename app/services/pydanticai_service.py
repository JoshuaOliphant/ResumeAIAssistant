"""
PydanticAI Service Module for AI-driven resume customization features.
This module implements the model-agnostic approach using PydanticAI for structured outputs
and flexible model provider selection.
"""
import os
import time
import json
from typing import Optional, Dict, Any, List
import asyncio
import logfire

# Import from PydanticAI - wrapped in try/except to handle missing dependencies gracefully
try:
    from pydanticai import Agent, tool
    PYDANTICAI_AVAILABLE = True
except ImportError:
    logfire.error("PydanticAI not installed. Please install with 'uv add pydanticai'")
    # Create dummy classes to prevent import errors
    class Agent:
        def __init__(self, *args, **kwargs):
            pass
        
        async def run(self, *args, **kwargs):
            raise NotImplementedError("PydanticAI not installed")
            
    def tool(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
        
    PYDANTICAI_AVAILABLE = False

from pydantic import BaseModel, Field
from app.core.config import settings
from app.core.logging import log_function_call
from app.schemas.customize import CustomizationLevel, CustomizationPlan, RecommendationItem
from app.schemas.ats import KeywordMatch, ATSImprovement, SectionScore

# Check for API keys - at minimum, we need one of these to function
if not settings.ANTHROPIC_API_KEY and not settings.OPENAI_API_KEY:
    logfire.error(
        "Neither ANTHROPIC_API_KEY nor OPENAI_API_KEY is set",
        impact="Model providers will not be available"
    )
    raise ValueError('Either ANTHROPIC_API_KEY or OPENAI_API_KEY environment variable must be set')

# Set default models based on availability
DEFAULT_MODEL = None
if settings.ANTHROPIC_API_KEY:
    DEFAULT_MODEL = "anthropic:claude-3-7-sonnet-latest"  # Default to Claude 3.7 Sonnet
    logfire.info("Using Anthropic Claude as default model provider")
elif settings.OPENAI_API_KEY:
    DEFAULT_MODEL = "openai:gpt-4.1"  # Fallback to OpenAI if Anthropic not available
    logfire.info("Using OpenAI as default model provider")
else:
    # This should never happen due to the check above, but just in case
    logfire.warning("No default model provider available")

# Set environment variables for PydanticAI to use
if settings.ANTHROPIC_API_KEY:
    os.environ["ANTHROPIC_API_KEY"] = settings.ANTHROPIC_API_KEY
if settings.OPENAI_API_KEY:
    os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY
if settings.GEMINI_API_KEY:
    os.environ["GOOGLE_API_KEY"] = settings.GEMINI_API_KEY

# Import model config function
from app.core.config import get_pydanticai_model_config

# Define config for model providers using settings
EVALUATOR_MODEL = settings.PYDANTICAI_EVALUATOR_MODEL
OPTIMIZER_MODEL = settings.PYDANTICAI_OPTIMIZER_MODEL
COVER_LETTER_MODEL = settings.PYDANTICAI_COVER_LETTER_MODEL
THINKING_BUDGET = settings.PYDANTICAI_THINKING_BUDGET
TEMPERATURE = settings.PYDANTICAI_TEMPERATURE
MAX_TOKENS = settings.PYDANTICAI_MAX_TOKENS
FALLBACK_MODELS = settings.PYDANTICAI_FALLBACK_MODELS

# Get the complete model provider configuration
MODEL_CONFIG = get_pydanticai_model_config()

# Log initialization
logfire.info(
    "PydanticAI initialized",
    default_model=DEFAULT_MODEL,
    evaluator_model=EVALUATOR_MODEL,
    optimizer_model=OPTIMIZER_MODEL,
    cover_letter_model=COVER_LETTER_MODEL,
    thinking_budget=THINKING_BUDGET,
    temperature=TEMPERATURE,
    max_tokens=MAX_TOKENS,
    providers=list(MODEL_CONFIG.keys())
)

# Import prompts
# Import only when needed to avoid circular imports
def _get_prompts():
    """Import prompts module dynamically to avoid circular imports"""
    from app.services.prompts import (
        get_customization_level_instructions,
        get_industry_specific_guidance,
        EVALUATOR_PROMPT,
        OPTIMIZER_PROMPT,
    )
    return {
        'get_customization_level_instructions': get_customization_level_instructions,
        'get_industry_specific_guidance': get_industry_specific_guidance,
        'EVALUATOR_PROMPT': EVALUATOR_PROMPT,
        'OPTIMIZER_PROMPT': OPTIMIZER_PROMPT,
    }

# Schema definitions for PydanticAI
class ResumeEvaluation(BaseModel):
    """Schema for resume evaluation results"""
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

class CoverLetter(BaseModel):
    """Schema for generated cover letter"""
    content: str = Field(..., description="The full cover letter text")
    sections: Dict[str, str] = Field(..., description="The cover letter broken down by sections")
    personalization_elements: List[str] = Field(..., description="How the letter was personalized")
    formatting_notes: Optional[str] = Field(None, description="Notes about the formatting")
    address_block: Optional[str] = Field(None, description="Formatted address block if provided")
    closing: Optional[str] = Field(None, description="Closing section with signature")

# Define agent creation functions
def create_resume_evaluator_agent(customization_level: CustomizationLevel = CustomizationLevel.BALANCED, 
                                 industry: Optional[str] = None) -> Agent:
    """
    Create an agent for evaluating resume-job match.
    
    Args:
        customization_level: Level of customization
        industry: Optional industry name for industry-specific guidance
        
    Returns:
        PydanticAI Agent configured for resume evaluation
    """
    if not PYDANTICAI_AVAILABLE:
        raise ImportError("PydanticAI is not installed")
        
    # Get prompts dynamically
    prompts = _get_prompts()
    
    # Get customization level specific instructions
    customization_instructions = prompts['get_customization_level_instructions'](customization_level)
    
    # Get industry-specific guidance if industry is provided
    industry_guidance = ""
    if industry:
        industry_guidance = prompts['get_industry_specific_guidance'](industry)
        if industry_guidance:
            customization_instructions += f"\n\nINDUSTRY-SPECIFIC GUIDANCE ({industry.upper()}):\n{industry_guidance}"
    
    # Format the prompt with the customization level instructions
    prompt_template = prompts['EVALUATOR_PROMPT'].replace("{customization_level_instructions}", customization_instructions)
    
    # Add instructions to return structured output format
    json_instruction = """
    Your output must match the following structure:
    - overall_assessment: Detailed evaluation of how well the resume matches the job
    - match_score: A score from 0-100 representing how well the resume matches the job
    - job_key_requirements: A list of the most important job requirements
    - strengths: A list of candidate strengths relative to the job
    - gaps: A list of missing skills or experiences
    - term_mismatches: A list of terminology equivalence (job term vs resume term)
    - section_evaluations: A list of section-level evaluations
    - competitor_analysis: A brief market comparison
    - reframing_opportunities: A list of experience reframing ideas
    - experience_preservation_check: Verification that all original experience is preserved
    """
    
    prompt_template = f"{prompt_template}\n\n{json_instruction}"
    
    # Determine if the model supports thinking
    thinking_config = None
    if EVALUATOR_MODEL.startswith("anthropic:claude-3-7") or "claude-3-7-sonnet-latest" in EVALUATOR_MODEL:
        thinking_config = {"budget_tokens": THINKING_BUDGET, "type": "enabled"}
    elif EVALUATOR_MODEL.startswith("google:gemini-2.5"):
        # Gemini uses thinkingBudget
        thinking_config = {"thinkingBudget": THINKING_BUDGET}
    
    # Create the agent
    try:
        evaluator_agent = Agent(
            EVALUATOR_MODEL,
            output_type=ResumeEvaluation,
            system_prompt=prompt_template,
            thinking_config=thinking_config,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS
        )
        
        # Add fallback configurations
        evaluator_agent.fallback_config = FALLBACK_MODELS
        
        logfire.info(
            "Resume Evaluator Agent created successfully",
            model=EVALUATOR_MODEL,
            has_thinking=thinking_config is not None
        )
        
        return evaluator_agent
        
    except Exception as e:
        logfire.error(
            "Error creating Resume Evaluator Agent",
            error=str(e),
            error_type=type(e).__name__
        )
        raise e

def create_resume_optimizer_agent(customization_level: CustomizationLevel = CustomizationLevel.BALANCED, 
                                 industry: Optional[str] = None) -> Agent:
    """
    Create an agent for generating resume optimization plans.
    
    Args:
        customization_level: Level of customization
        industry: Optional industry name for industry-specific guidance
        
    Returns:
        PydanticAI Agent configured for resume optimization
    """
    if not PYDANTICAI_AVAILABLE:
        raise ImportError("PydanticAI is not installed")
        
    # Get prompts dynamically
    prompts = _get_prompts()
    
    # Get customization level specific instructions
    customization_instructions = prompts['get_customization_level_instructions'](customization_level)
    
    # Get industry-specific guidance if industry is provided
    industry_guidance = ""
    if industry:
        industry_guidance = prompts['get_industry_specific_guidance'](industry)
        if industry_guidance:
            customization_instructions += f"\n\nINDUSTRY-SPECIFIC GUIDANCE ({industry.upper()}):\n{industry_guidance}"
    
    # Format the prompt with the customization level instructions
    prompt_template = prompts['OPTIMIZER_PROMPT'].replace("{customization_level_instructions}", customization_instructions)
    
    # Determine if the model supports thinking
    thinking_config = None
    if OPTIMIZER_MODEL.startswith("anthropic:claude-3-7") or "claude-3-7-sonnet-latest" in OPTIMIZER_MODEL:
        thinking_config = {"budget_tokens": THINKING_BUDGET, "type": "enabled"}
    elif OPTIMIZER_MODEL.startswith("google:gemini-2.5"):
        # Gemini uses thinkingBudget
        thinking_config = {"thinkingBudget": THINKING_BUDGET}
    
    # Create the agent
    try:
        optimizer_agent = Agent(
            OPTIMIZER_MODEL,
            output_type=CustomizationPlan,
            system_prompt=prompt_template,
            thinking_config=thinking_config,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS
        )
        
        # Add fallback configurations
        optimizer_agent.fallback_config = FALLBACK_MODELS
        
        logfire.info(
            "Resume Optimizer Agent created successfully",
            model=OPTIMIZER_MODEL,
            has_thinking=thinking_config is not None
        )
        
        return optimizer_agent
        
    except Exception as e:
        logfire.error(
            "Error creating Resume Optimizer Agent",
            error=str(e),
            error_type=type(e).__name__
        )
        raise e

def create_cover_letter_agent(applicant_name: Optional[str] = None,
                         company_name: str = "the company",
                         hiring_manager_name: Optional[str] = None,
                         additional_context: Optional[str] = None,
                         tone: str = "professional") -> Agent:
    """
    Create an agent for generating cover letters.
    
    Args:
        applicant_name: Optional applicant name
        company_name: Optional company name
        hiring_manager_name: Optional hiring manager name
        additional_context: Optional additional context to include
        tone: Tone of the cover letter (professional, enthusiastic, formal, etc.)
        
    Returns:
        PydanticAI Agent configured for cover letter generation
    """
    if not PYDANTICAI_AVAILABLE:
        raise ImportError("PydanticAI is not installed")
        
    # Build the salutation based on available info
    salutation_instruction = ""
    if hiring_manager_name:
        salutation_instruction = f"Address the letter to {hiring_manager_name}."
    else:
        salutation_instruction = "Use an appropriate general salutation like 'Dear Hiring Manager'."
    
    # Add applicant name if provided
    applicant_instruction = ""
    if applicant_name:
        applicant_instruction = f"The letter should be signed by {applicant_name}."
    else:
        applicant_instruction = "End with an appropriate closing but without a specific name."
    
    # Add additional context if provided
    context_instruction = ""
    if additional_context:
        context_instruction = f"Also consider this additional context: {additional_context}"
        
    # Create system prompt for cover letter generation
    system_prompt = f"""
    You are a professional resume writer helping a job seeker create a compelling cover letter for a specific job posting.
    
    Your task is to write a personalized cover letter that highlights the applicant's qualifications for the position.
    
    Guidelines:
    - Use the provided resume to extract relevant experience, skills, and achievements
    - Match the applicant's qualifications to the job requirements
    - Keep the letter concise and focused (about 300-400 words)
    - Use a {tone} tone throughout the letter
    - Structure the letter with a clear introduction, body, and conclusion
    - Include specific examples from the resume that demonstrate the applicant's fit for the role
    - Mention the company name ({company_name}) naturally in the letter
    - {salutation_instruction}
    - {applicant_instruction}
    - Format the letter in professional Markdown with appropriate spacing
    
    {context_instruction}
    
    Your response MUST include:
    - The complete cover letter text in 'content' - this is the most important field
    - A breakdown of the letter by sections in 'sections' (e.g., introduction, body paragraphs, conclusion)
    - A list of how the letter was personalized for this specific job and company in 'personalization_elements'
    - Optional formatting notes in 'formatting_notes'
    - Optional address block in 'address_block' if appropriate
    - Optional closing in 'closing' if appropriate
    
    The letter should showcase the applicant's relevant qualifications while maintaining a professional and enthusiastic tone.
    Focus on demonstrating how the applicant's experience directly addresses the job requirements.
    """
    
    # Determine if the model supports thinking
    thinking_config = None
    if COVER_LETTER_MODEL.startswith("anthropic:claude-3-7") or "claude-3-7-sonnet-latest" in COVER_LETTER_MODEL:
        thinking_config = {"budget_tokens": THINKING_BUDGET, "type": "enabled"}
    elif COVER_LETTER_MODEL.startswith("google:gemini-2.5"):
        # Gemini uses thinkingBudget
        thinking_config = {"thinkingBudget": THINKING_BUDGET}
    
    # Create the agent
    try:
        # Cover letters benefit from a balance of creativity and consistency
        # Claude 3.5 Sonnet offers a good balance of quality and cost
        # For cover letters, we can use a slightly more creative temperature
        model = COVER_LETTER_MODEL
        
        # Adjust temperature based on tone
        # More creative for enthusiastic/casual tones, more conservative for formal/professional tones
        base_temperature = TEMPERATURE
        temperature_adjustment = 0.0
        
        if tone.lower() in ["enthusiastic", "casual", "conversational"]:
            temperature_adjustment = 0.1  # More creative for enthusiastic tones
        elif tone.lower() in ["formal", "academic", "technical"]:
            temperature_adjustment = -0.15  # More consistent for formal tones
        else:  # "professional" (default) or other tones
            temperature_adjustment = 0.0  # Default temperature is fine for professional tone
            
        temperature = max(0.3, min(0.9, base_temperature + temperature_adjustment))
        
        cover_letter_agent = Agent(
            model,
            output_type=CoverLetter,
            system_prompt=system_prompt,
            thinking_config=thinking_config,
            temperature=temperature,
            max_tokens=MAX_TOKENS
        )
        
        # For cover letters, we want fallback models that excel at creative writing
        # while still maintaining professionalism and structure
        fallbacks = [
            # Start with Claude 3.7 Sonnet which is excellent for writing tasks
            "anthropic:claude-3-7-sonnet-latest",
            # Next try OpenAI GPT-4.1 which has strong writing capabilities
            "openai:gpt-4.1",
            # Then try Gemini Pro which is good for creative text generation
            "google:gemini-2.5-pro-preview-03-25",
            # For faster/cheaper options if needed
            "anthropic:claude-3-7-haiku-latest",
            "openai:gpt-4o",
            "google:gemini-2.5-flash-preview-04-17"
        ]
        
        cover_letter_agent.fallback_config = fallbacks
        
        logfire.info(
            "Cover Letter Agent created successfully",
            model=model,
            temperature=temperature,
            tone=tone,
            has_thinking=thinking_config is not None,
            company_name=company_name,
            fallbacks=fallbacks[:3]  # Log only first 3 fallbacks to avoid verbose logs
        )
        
        return cover_letter_agent
        
    except Exception as e:
        logfire.error(
            "Error creating Cover Letter Agent",
            error=str(e),
            error_type=type(e).__name__
        )
        raise e

# Tools for agents
@tool
def extract_keywords(job_description: str, max_keywords: int = 20) -> List[str]:
    """
    Extract important keywords from a job description.
    
    Args:
        job_description: The job description text
        max_keywords: Maximum number of keywords to extract
        
    Returns:
        List of important keywords
    """
    # This would be implemented with proper NLP techniques
    # Basic implementation for now
    import re
    from collections import Counter
    import nltk
    from nltk.corpus import stopwords
    
    try:
        words = re.findall(r'\b\w+\b', job_description.lower())
        stop_words = set(stopwords.words('english'))
        filtered_words = [word for word in words if word not in stop_words and len(word) > 3]
        word_counts = Counter(filtered_words)
        return [word for word, count in word_counts.most_common(max_keywords)]
    except Exception as e:
        logfire.error(f"Error extracting keywords: {str(e)}")
        return []

@tool
def simulate_ats(resume: str, job_description: str) -> Dict[str, Any]:
    """
    Simulate how an ATS system would process this resume.
    
    Args:
        resume: The resume text
        job_description: The job description
        
    Returns:
        Dictionary with ATS simulation results
    """
    # Basic implementation - this would be more sophisticated in a real system
    keywords = extract_keywords(job_description)
    resume_lower = resume.lower()
    matches = [keyword for keyword in keywords if keyword in resume_lower]
    
    score = int(len(matches) / len(keywords) * 100) if keywords else 0
    return {
        "score": score,
        "matches": matches,
        "missing": [k for k in keywords if k not in matches],
        "passes": score >= 70
    }

# Main API functions
@log_function_call
async def evaluate_resume_job_match(
    resume_content: str,
    job_description: str,
    basic_analysis: Optional[Dict] = None,
    customization_level: CustomizationLevel = CustomizationLevel.BALANCED,
    industry: Optional[str] = None
) -> Dict:
    """
    Evaluate how well a resume matches a job description.
    
    Args:
        resume_content: The content of the resume in Markdown format
        job_description: The job description text
        basic_analysis: Optional basic keyword analysis results to enhance evaluation
        customization_level: Level of customization (affects evaluation detail)
        industry: Optional industry name for industry-specific guidance
        
    Returns:
        Dictionary containing evaluation of the resume-job match
    """
    if not PYDANTICAI_AVAILABLE:
        raise ImportError("PydanticAI is not installed")
        
    # Start timer for performance tracking
    start_time = time.time()
    
    # Create a span in OpenTelemetry for tracing
    with logfire.span("evaluate_resume_job_match_operation") as span:
        span.set_attribute("resume_length", len(resume_content))
        span.set_attribute("job_description_length", len(job_description))
        span.set_attribute("has_basic_analysis", basic_analysis is not None)
        span.set_attribute("customization_level", customization_level.value)
        span.set_attribute("industry", industry if industry else "not specified")
        
        # Log operation start
        logfire.info(
            "Starting resume-job match evaluation",
            resume_length=len(resume_content),
            job_description_length=len(job_description),
            has_basic_analysis=basic_analysis is not None,
            customization_level=customization_level.name,
            industry=industry if industry else "not specified"
        )
        
        # Create the evaluator agent with appropriate customization level and industry
        evaluator_agent = create_resume_evaluator_agent(
            customization_level=customization_level,
            industry=industry
        )
        
        # Build the user message
        user_message = f"""
        Here's the resume content to evaluate:
        
        {resume_content}
        
        Here's the job description to match against:
        
        {job_description}
        """
        
        # If we have basic analysis results, add them to the prompt
        if basic_analysis:
            basic_analysis_str = json.dumps(basic_analysis, indent=2)
            user_message += f"""
            
            Here are the results of a basic keyword analysis:
            
            {basic_analysis_str}
            """
            
        # If industry is specified, mention it in the user message
        if industry:
            user_message += f"""
            
            The target industry for this job is: {industry}
            """
        
        # Set up the dependencies for tools
        dependencies = {
            "extract_keywords_context": {"job_description": job_description},
            "simulate_ats_context": {"resume": resume_content, "job_description": job_description}
        }
        
        try:
            # Run the agent
            result = await evaluator_agent.run(
                user_message,
                deps=dependencies
            )
            
            # Calculate elapsed time
            elapsed_time = time.time() - start_time
            
            # Convert the result to a dictionary
            evaluation_result = result.dict()
            
            # Log success
            logfire.info(
                "Resume-job evaluation completed successfully",
                response_length=len(str(evaluation_result)),
                duration_seconds=round(elapsed_time, 2),
                match_score=evaluation_result.get("match_score")
            )
            
            return evaluation_result
            
        except Exception as e:
            # Calculate elapsed time
            elapsed_time = time.time() - start_time
            
            # Log error
            logfire.error(
                "Error evaluating resume-job match",
                error=str(e),
                error_type=type(e).__name__,
                duration_seconds=round(elapsed_time, 2)
            )
            
            # Re-raise the exception
            raise e

@log_function_call
async def generate_optimization_plan(
    resume_content: str,
    job_description: str,
    evaluation: Dict,
    customization_level: CustomizationLevel = CustomizationLevel.BALANCED,
    industry: Optional[str] = None
) -> CustomizationPlan:
    """
    Generate a detailed optimization plan based on an evaluation of resume-job match.
    
    Args:
        resume_content: The content of the resume in Markdown format
        job_description: The job description text
        evaluation: The evaluation dictionary from the evaluator stage
        customization_level: Level of customization (affects optimization detail)
        industry: Optional industry name for industry-specific guidance
        
    Returns:
        CustomizationPlan object with detailed recommendations
    """
    if not PYDANTICAI_AVAILABLE:
        raise ImportError("PydanticAI is not installed")
        
    # Start timer for performance tracking
    start_time = time.time()
    
    # Create a span in OpenTelemetry for tracing
    with logfire.span("generate_optimization_plan_operation") as span:
        span.set_attribute("resume_length", len(resume_content))
        span.set_attribute("job_description_length", len(job_description))
        span.set_attribute("customization_level", customization_level.value)
        span.set_attribute("industry", industry if industry else "not specified")
        
        # Log operation start
        logfire.info(
            "Starting optimization plan generation",
            resume_length=len(resume_content),
            job_description_length=len(job_description),
            customization_level=customization_level.name,
            industry=industry if industry else "not specified"
        )
        
        # Create the optimizer agent with appropriate customization level and industry
        optimizer_agent = create_resume_optimizer_agent(
            customization_level=customization_level,
            industry=industry
        )
        
        # Build the user message
        user_message = f"""
        Here's the resume content to optimize:
        
        {resume_content}
        
        Here's the job description to optimize for:
        
        {job_description}
        
        Here's the detailed evaluation of how well the resume matches the job:
        
        {json.dumps(evaluation, indent=2)}
        """
        
        # If industry is specified, mention it in the user message
        if industry:
            user_message += f"""
            
            The target industry for this job is: {industry}
            Please apply the industry-specific guidance for {industry.upper()} in your optimization plan.
            """
        
        try:
            # Run the agent
            result = await optimizer_agent.run(user_message)
            
            # Calculate elapsed time
            elapsed_time = time.time() - start_time
            
            # Result is already a validated CustomizationPlan instance
            
            # Log success
            logfire.info(
                "Optimization plan generation completed successfully",
                response_length=len(str(result)),
                duration_seconds=round(elapsed_time, 2),
                recommendation_count=len(result.recommendations)
            )
            
            return result
            
        except Exception as e:
            # Calculate elapsed time
            elapsed_time = time.time() - start_time
            
            # Log error
            logfire.error(
                "Error generating optimization plan",
                error=str(e),
                error_type=type(e).__name__,
                duration_seconds=round(elapsed_time, 2)
            )
            
            # Re-raise the exception
            raise e

@log_function_call
async def customize_resume(
    resume_content: str,
    job_description: str,
    customization_strength: int = 2,
    focus_areas: Optional[str] = None
) -> str:
    """
    Customize a resume for a specific job description.
    
    Args:
        resume_content: The content of the resume in Markdown format
        job_description: The job description text
        customization_strength: The strength of customization (1-3)
        focus_areas: Optional comma-separated list of areas to focus on
    
    Returns:
        Customized resume content in Markdown format
    """
    if not PYDANTICAI_AVAILABLE:
        raise ImportError("PydanticAI is not installed")
        
    # Start timer for performance tracking
    start_time = time.time()

    # Create a span in OpenTelemetry for tracing
    with logfire.span("customize_resume_operation") as span:
        span.set_attribute("resume_length", len(resume_content))
        span.set_attribute("job_description_length", len(job_description))
        span.set_attribute("customization_strength", customization_strength)
        span.set_attribute("has_focus_areas", focus_areas is not None)
        
        # Log operation start
        logfire.info(
            "Starting resume customization",
            resume_length=len(resume_content),
            job_description_length=len(job_description),
            customization_strength=customization_strength,
            focus_areas=focus_areas
        )
        
        # Prepare the instruction based on customization strength
        strength_instruction = ""
        if customization_strength == 1:
            strength_instruction = "Make minimal, subtle changes to better align the resume with the job description."
        elif customization_strength == 2:
            strength_instruction = "Make moderate changes to highlight relevant experience and skills that match the job description."
        elif customization_strength == 3:
            strength_instruction = "Make significant changes to strongly emphasize relevant experience and skills that match the job description."
        
        # Add focus areas if provided
        focus_instruction = ""
        if focus_areas:
            focus_instruction = f"Focus especially on these areas: {focus_areas}."
        
        # Build the full system prompt
        system_prompt = f"""
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
        
        {strength_instruction}
        {focus_instruction}
        
        Return ONLY the customized resume in Markdown format, maintaining proper formatting.
        """
        
        # Create a specialized agent for text generation
        customization_agent = Agent(
            DEFAULT_MODEL,
            output_format="text",  # Use text format for direct output
            system_prompt=system_prompt,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS
        )
        
        # Build the user message
        user_message = f"""
        Here is my current resume in Markdown format:
        
        {resume_content}
        
        Here is the job description I'm applying for:
        
        {job_description}
        
        Please customize my resume for this specific job.
        """
        
        try:
            # Run the agent
            result = await customization_agent.run(user_message)
            
            # Calculate elapsed time
            elapsed_time = time.time() - start_time
            
            # Log success
            logfire.info(
                "Resume customization completed successfully",
                response_length=len(result),
                duration_seconds=round(elapsed_time, 2)
            )
            
            # Return the customized resume
            return result
            
        except Exception as e:
            # Calculate elapsed time
            elapsed_time = time.time() - start_time
            
            # Log error
            logfire.error(
                "Error customizing resume",
                error=str(e),
                error_type=type(e).__name__,
                duration_seconds=round(elapsed_time, 2)
            )
            
            # Re-raise the exception
            raise e

@log_function_call
async def generate_cover_letter(
    resume_content: str,
    job_description: str,
    applicant_name: Optional[str] = None,
    company_name: str = "the company",
    hiring_manager_name: Optional[str] = None,
    additional_context: Optional[str] = None,
    tone: str = "professional"
) -> str:
    """
    Generate a cover letter based on a resume and job description using advanced AI.
    
    Args:
        resume_content: The content of the resume in Markdown format
        job_description: The job description text
        applicant_name: Optional applicant name
        company_name: Optional company name
        hiring_manager_name: Optional hiring manager name
        additional_context: Optional additional context to include
        tone: Tone of the cover letter (professional, enthusiastic, formal, etc.)
    
    Returns:
        Generated cover letter content in Markdown format
    """
    if not PYDANTICAI_AVAILABLE:
        raise ImportError("PydanticAI is not installed")
        
    # Start timer for performance tracking
    start_time = time.time()

    # Create a span in OpenTelemetry for tracing
    with logfire.span("generate_cover_letter_operation") as span:
        span.set_attribute("resume_length", len(resume_content))
        span.set_attribute("job_description_length", len(job_description))
        span.set_attribute("has_applicant_name", applicant_name is not None)
        span.set_attribute("company_name", company_name)
        span.set_attribute("has_hiring_manager", hiring_manager_name is not None)
        span.set_attribute("has_additional_context", additional_context is not None)
        span.set_attribute("tone", tone)
        span.set_attribute("model", COVER_LETTER_MODEL)
        
        # Log operation start
        logfire.info(
            "Starting cover letter generation",
            resume_length=len(resume_content),
            job_description_length=len(job_description),
            company_name=company_name,
            tone=tone,
            model=COVER_LETTER_MODEL
        )
        
        # Create the cover letter agent with all personalization options
        cover_letter_agent = create_cover_letter_agent(
            applicant_name=applicant_name,
            company_name=company_name,
            hiring_manager_name=hiring_manager_name,
            additional_context=additional_context,
            tone=tone
        )
        
        # Build the user message
        user_message = f"""
        Here is my resume in Markdown format:
        
        {resume_content}
        
        Here is the job description I'm applying for at {company_name}:
        
        {job_description}
        
        Please write a cover letter for this position that highlights my relevant qualifications.
        """
        
        # Add retry mechanism for improved resilience
        max_retries = 2
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                # Run the agent
                result = await cover_letter_agent.run(user_message)
                
                # Calculate elapsed time
                elapsed_time = time.time() - start_time
                
                # Extract metadata for logging
                sections_count = len(result.sections) if result.sections else 0
                personalization_count = len(result.personalization_elements) if result.personalization_elements else 0
                
                # Log success
                logfire.info(
                    "Cover letter generation completed successfully",
                    response_length=len(result.content),
                    sections_count=sections_count,
                    personalization_count=personalization_count,
                    duration_seconds=round(elapsed_time, 2),
                    attempt=retry_count + 1
                )
                
                # Return just the content for compatibility with existing APIs
                return result.content
                
            except Exception as e:
                retry_count += 1
                # Log error
                logfire.warning(
                    "Error generating cover letter, will retry" if retry_count <= max_retries else "Final error generating cover letter",
                    error=str(e),
                    error_type=type(e).__name__,
                    duration_seconds=round(time.time() - start_time, 2),
                    attempt=retry_count,
                    will_retry=retry_count <= max_retries
                )
                
                if retry_count > max_retries:
                    # Re-raise the exception on final failure
                    logfire.error(
                        "Failed to generate cover letter after all retries",
                        error=str(e),
                        error_type=type(e).__name__,
                        duration_seconds=round(time.time() - start_time, 2),
                        attempts=retry_count
                    )
                    raise e
                
                # If using fallback models, try to use the next one in the chain
                if retry_count == 1 and FALLBACK_MODELS:
                    fallback_model = FALLBACK_MODELS[0]
                    logfire.info(
                        f"Falling back to alternate model: {fallback_model}",
                        original_model=COVER_LETTER_MODEL,
                        fallback_model=fallback_model
                    )
                    
                    # Create a new agent with the fallback model
                    cover_letter_agent = Agent(
                        fallback_model,
                        output_type=CoverLetter,
                        system_prompt=cover_letter_agent.system_prompt,
                        temperature=TEMPERATURE,
                        max_tokens=MAX_TOKENS
                    )
                
                # Wait briefly before retrying
                await asyncio.sleep(1)