"""
PydanticAI Service Module for AI-driven resume customization features.
This module implements the model-agnostic approach using PydanticAI for structured outputs
and flexible model provider selection.
"""

import asyncio
import json
import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import logfire
from pydantic_ai import Agent, ModelRetry

from app.services.evidence_tracker import EvidenceTracker


# Import from PydanticAI directly - it's a core dependency

# Import from PydanticAI directly - it's a core dependency

logfire.info("PydanticAI imported successfully")

from app.core.config import settings
from app.core.logging import log_function_call
from app.schemas.customize import CustomizationLevel, CustomizationPlan
from app.schemas.pydanticai_models import CoverLetter, ResumeEvaluation

# Check for API keys - at minimum, we need one of these to function
if not settings.ANTHROPIC_API_KEY and not settings.OPENAI_API_KEY:
    logfire.error(
        "Neither ANTHROPIC_API_KEY nor OPENAI_API_KEY is set",
        impact="Model providers will not be available",
    )
    raise ValueError(
        "Either ANTHROPIC_API_KEY or OPENAI_API_KEY environment variable must be set"
    )

# Set default model based on availability
DEFAULT_MODEL = "anthropic:claude-3-7-sonnet-latest"  # Use Claude as the only model
logfire.info("Using Anthropic Claude as the model provider")

# Set environment variables for PydanticAI to use
if settings.ANTHROPIC_API_KEY:
    os.environ["ANTHROPIC_API_KEY"] = settings.ANTHROPIC_API_KEY
else:
    logfire.error(
        "ANTHROPIC_API_KEY is not set",
        impact="Claude model provider will not be available",
    )
    raise ValueError("ANTHROPIC_API_KEY environment variable must be set")

# Import model config function
from app.core.config import get_pydanticai_model_config

# Get configuration from the core config
model_config = get_pydanticai_model_config()

# Set model settings
EVALUATOR_MODEL = "anthropic:claude-3-7-sonnet-latest"  # Use Claude for evaluation
OPTIMIZER_MODEL = EVALUATOR_MODEL  # Use same model for optimizer
COVER_LETTER_MODEL = EVALUATOR_MODEL  # Use same model for cover letter generation
THINKING_BUDGET = settings.PYDANTICAI_THINKING_BUDGET
TEMPERATURE = settings.PYDANTICAI_TEMPERATURE
MAX_TOKENS = settings.PYDANTICAI_MAX_TOKENS

# No fallback models - we're only using Claude
FALLBACK_MODELS = []

# Log the configuration
logfire.info("No fallback models configured, using only anthropic:claude-3-7-sonnet-latest")

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
    providers=list(MODEL_CONFIG.keys()),
)


# Core service class implementing evaluator-optimizer workflow
class PydanticAIService:
    """High level interface for resume customization using PydanticAI."""

    def __init__(self) -> None:
        self.evaluator_model = EVALUATOR_MODEL
        self.optimizer_model = OPTIMIZER_MODEL
        self.fallback_models = FALLBACK_MODELS
        self.temperature = TEMPERATURE
        self.max_tokens = MAX_TOKENS
        self.thinking_budget = THINKING_BUDGET

    def _create_agent(self, model: str, system_prompt: str, output_type) -> Agent:
        """Create a configured agent with fallback and thinking config."""
        thinking = {"budget_tokens": self.thinking_budget, "type": "enabled"}
        agent = Agent(
            model,
            system_prompt=system_prompt,
            output_type=output_type,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            thinking_config=thinking,
        )
        # No fallback configuration is needed as we're only using Claude
        return agent

    async def _run_with_retry(self, agent: Agent, message: str):
        """Execute an agent with basic ModelRetry handling."""
        attempt = 0
        while True:
            try:
                return await agent.run(message)
            except ModelRetry as mr:
                attempt += 1
                logfire.warning("ModelRetry triggered", attempt=attempt, reason=str(mr))
                if attempt >= 2:
                    raise

    async def evaluate_resume(self, resume: str, job: str) -> ResumeEvaluation:
        """Run the evaluation stage."""
        prompts = _get_prompts()
        prompt = prompts["EVALUATOR_PROMPT"].replace(
            "{customization_level_instructions}", ""
        )
        agent = self._create_agent(self.evaluator_model, prompt, ResumeEvaluation)
        async with logfire.span("evaluate_resume"):
            return await self._run_with_retry(
                agent, f"Resume:\n{resume}\n\nJob:\n{job}"
            )

    async def customize_resume(self, resume: str, job: str) -> CustomizationPlan:
        """High level helper running evaluation then optimization."""
        evaluation = await self.evaluate_resume(resume, job)
        plan = await self.generate_plan(resume, job, evaluation)
        return plan

    def validate_evidence(self, original: str, updated: str) -> List[str]:
        """Check that updated resume remains truthful."""
        tracker = EvidenceTracker(original)
        return tracker.verify(updated)

    async def generate_plan(
        self, resume: str, job: str, evaluation: ResumeEvaluation
    ) -> CustomizationPlan:
        """Run the optimizer stage."""
        prompts = _get_prompts()
        prompt = prompts["OPTIMIZER_PROMPT"].replace(
            "{customization_level_instructions}", ""
        )
        agent = self._create_agent(self.optimizer_model, prompt, CustomizationPlan)
        async with logfire.span("generate_plan"):
            msg = (
                f"Resume:\n{resume}\n\nJob:\n{job}\n\nEvaluation:\n{evaluation.json()}"
            )
            return await self._run_with_retry(agent, msg)


# Import prompts
# Import only when needed to avoid circular imports
def _get_prompts():
    """Import prompts module dynamically to avoid circular imports"""
    from app.services.prompts import (
        EVALUATOR_PROMPT,
        OPTIMIZER_PROMPT,
        get_customization_level_instructions,
        get_industry_specific_guidance,
    )

    return {
        "get_customization_level_instructions": get_customization_level_instructions,
        "get_industry_specific_guidance": get_industry_specific_guidance,
        "EVALUATOR_PROMPT": EVALUATOR_PROMPT,
        "OPTIMIZER_PROMPT": OPTIMIZER_PROMPT,
    }


# Schema definitions for PydanticAI are now centralized in app.schemas.pydanticai_models

# Note: The helper functions for agent creation have been removed as they're no longer used.
# Agent creation now happens directly in the pydanticai_optimizer.py file with model selection.


def create_cover_letter_agent(
    applicant_name: Optional[str] = None,
    company_name: str = "the company",
    hiring_manager_name: Optional[str] = None,
    additional_context: Optional[str] = None,
    tone: str = "professional",
) -> Agent:
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
    # PydanticAI is a required dependency - no need to check

    # Build the salutation based on available info
    salutation_instruction = ""
    if hiring_manager_name:
        salutation_instruction = f"Address the letter to {hiring_manager_name}."
    else:
        salutation_instruction = (
            "Use an appropriate general salutation like 'Dear Hiring Manager'."
        )

    # Add applicant name if provided
    applicant_instruction = ""
    if applicant_name:
        applicant_instruction = f"The letter should be signed by {applicant_name}."
    else:
        applicant_instruction = (
            "End with an appropriate closing but without a specific name."
        )

    # Add additional context if provided
    context_instruction = ""
    if additional_context:
        context_instruction = (
            f"Also consider this additional context: {additional_context}"
        )

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
    if COVER_LETTER_MODEL.startswith(
        "anthropic:claude-3-7"
    ) or COVER_LETTER_MODEL.startswith("anthropic:claude-3-7-sonnet-latest"):
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
            temperature_adjustment = (
                0.0  # Default temperature is fine for professional tone
            )

        temperature = max(0.3, min(0.9, base_temperature + temperature_adjustment))

        from app.core.parallel_config import TASK_TIMEOUT_SECONDS

        cover_letter_agent = Agent(
            model,
            output_type=CoverLetter,
            system_prompt=system_prompt,
            thinking_config=thinking_config,
            temperature=temperature,
            max_tokens=MAX_TOKENS,
            timeout=TASK_TIMEOUT_SECONDS,
        )

        # No fallback configuration is needed as we're only using Claude

        logfire.info(
            "Cover Letter Agent created successfully",
            model=model,
            temperature=temperature,
            tone=tone,
            has_thinking=thinking_config is not None,
            company_name=company_name,
            fallbacks=fallbacks[:3],  # Log only first 3 fallbacks to avoid verbose logs
        )

        return cover_letter_agent

    except Exception as e:
        logfire.error(
            "Error creating Cover Letter Agent",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise e


# Tools for agents
# Function will need to be decorated with agent.tool in the specific agent creation
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

    from nltk.corpus import stopwords

    try:
        words = re.findall(r"\b\w+\b", job_description.lower())
        stop_words = set(stopwords.words("english"))
        filtered_words = [
            word for word in words if word not in stop_words and len(word) > 3
        ]
        word_counts = Counter(filtered_words)
        return [word for word, count in word_counts.most_common(max_keywords)]
    except Exception as e:
        logfire.error(f"Error extracting keywords: {str(e)}")
        return []


# Function will need to be decorated with agent.tool in the specific agent creation
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
        "passes": score >= 70,
    }


# Main API functions
@log_function_call
async def evaluate_resume_job_match(
    resume_content: str,
    job_description: str,
    basic_analysis: Optional[Dict] = None,
    customization_level: CustomizationLevel = CustomizationLevel.BALANCED,
    industry: Optional[str] = None,
    model_config: Optional[Dict[str, Any]] = None,
) -> Dict:
    """
    Evaluate how well a resume matches a job description.

    Args:
        resume_content: The content of the resume in Markdown format
        job_description: The job description text
        basic_analysis: Optional basic keyword analysis results to enhance evaluation
        customization_level: Level of customization (affects evaluation detail)
        industry: Optional industry name for industry-specific guidance
        model_config: Optional model configuration to override defaults

    Returns:
        Dictionary containing evaluation of the resume-job match
    """
    # PydanticAI is a required dependency - no need to check

    # Start timer for performance tracking
    start_time = time.time()

    # Create a span in OpenTelemetry for tracing
    with logfire.span("evaluate_resume_job_match_operation") as span:
        span.set_attribute("resume_length", len(resume_content))
        span.set_attribute("job_description_length", len(job_description))
        span.set_attribute("has_basic_analysis", basic_analysis is not None)
        span.set_attribute("customization_level", customization_level.value)
        span.set_attribute("industry", industry if industry else "not specified")
        span.set_attribute("has_model_config", model_config is not None)

        # Log operation start
        logfire.info(
            "Starting resume-job match evaluation",
            resume_length=len(resume_content),
            job_description_length=len(job_description),
            has_basic_analysis=basic_analysis is not None,
            customization_level=customization_level.name,
            industry=industry if industry else "not specified",
            has_custom_model_config=model_config is not None,
        )

        # Get prompts dynamically
        prompts = _get_prompts()

        # Get customization level specific instructions
        customization_instructions = prompts["get_customization_level_instructions"](
            customization_level
        )

        # Get industry-specific guidance if industry is provided
        industry_guidance = ""
        if industry:
            industry_guidance = prompts["get_industry_specific_guidance"](industry)
            if industry_guidance:
                customization_instructions += f"\n\nINDUSTRY-SPECIFIC GUIDANCE ({industry.upper()}):\n{industry_guidance}"

        # Format the prompt with the customization level instructions
        prompt_template = prompts["EVALUATOR_PROMPT"].replace(
            "{customization_level_instructions}", customization_instructions
        )

        # Use model configuration if provided, otherwise use defaults
        if model_config:
            # Extract model configuration
            model_name = model_config.get("model", EVALUATOR_MODEL)
            thinking_config = model_config.get(
                "thinking_config", {"thinkingBudget": THINKING_BUDGET}
            )
            temperature = model_config.get("temperature", TEMPERATURE)
            max_tokens = model_config.get("max_tokens", MAX_TOKENS)
            fallback_chain = model_config.get("fallback_config", FALLBACK_MODELS)

            logfire.info(
                "Using custom model configuration for resume evaluation",
                model=model_name,
                customization_level=customization_level.name,
                has_thinking_config=thinking_config is not None,
            )
        else:
            # Use default configuration
            model_name = EVALUATOR_MODEL
            thinking_config = {"thinkingBudget": THINKING_BUDGET}
            temperature = TEMPERATURE
            max_tokens = MAX_TOKENS
            fallback_chain = FALLBACK_MODELS

            logfire.info(
                "Using default model configuration for resume evaluation",
                model=model_name,
                customization_level=customization_level.name,
                has_thinking_config=thinking_config is not None,
            )

        # Create the agent with the selected configuration and timeout
        from app.core.parallel_config import TASK_TIMEOUT_SECONDS

        evaluator_agent = Agent(
            model_name,
            output_type=ResumeEvaluation,
            system_prompt=prompt_template,
            thinking_config=thinking_config,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=TASK_TIMEOUT_SECONDS,
        )

        # Apply fallback chain
        evaluator_agent.fallback_config = fallback_chain

        # Log the fallback configuration
        logfire.info(
            "Applied fallback chain for evaluator agent",
            fallback_models=fallback_chain[:2]
            if isinstance(fallback_chain, list)
            else "None",
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
            # Use string format instead of f-string
            analysis_template = """

            Here are the results of a basic keyword analysis:

            {analysis_str}
            """
            user_message += analysis_template.format(analysis_str=basic_analysis_str)

        # If industry is specified, mention it in the user message
        if industry:
            # Use string format instead of f-string
            industry_template = """

            The target industry for this job is: {industry_name}
            """
            user_message += industry_template.format(industry_name=industry)

        # Register tools on the agent instance
        @evaluator_agent.tool
        def extract_keywords_for_job(
            job_description: str = job_description, max_keywords: int = 20
        ) -> List[str]:
            """Extract important keywords from the job description."""
            return extract_keywords(job_description, max_keywords)

        @evaluator_agent.tool
        def simulate_ats_scan(
            resume: str = resume_content, job_desc: str = job_description
        ) -> Dict[str, Any]:
            """Simulate how an ATS system would process this resume."""
            return simulate_ats(resume, job_desc)

        try:
            # Run the agent with explicit timeout handling
            from app.core.parallel_config import TASK_TIMEOUT_SECONDS

            # Log the start time for better debugging
            api_start_time = time.time()
            logfire.info(
                "Starting evaluator API call with timeout",
                model=model_name,
                timeout_seconds=TASK_TIMEOUT_SECONDS,
                start_time=api_start_time,
            )

            # Use asyncio.wait_for to add an additional timeout layer
            try:
                result = await asyncio.wait_for(
                    evaluator_agent.run(user_message),
                    timeout=TASK_TIMEOUT_SECONDS
                    - 1,  # Set slightly lower to ensure it triggers before the model timeout
                )
                api_end_time = time.time()
                api_duration = api_end_time - api_start_time

                logfire.info(
                    "Evaluator API call completed successfully",
                    model=model_name,
                    duration_seconds=round(api_duration, 2),
                )
            except asyncio.TimeoutError:
                api_duration = time.time() - api_start_time
                logfire.error(
                    "Evaluator API call timed out",
                    model=model_name,
                    duration_seconds=round(api_duration, 2),
                    timeout_seconds=TASK_TIMEOUT_SECONDS,
                )
                raise asyncio.TimeoutError(
                    f"Evaluator API call to {model_name} timed out after {round(api_duration, 2)} seconds"
                )

            # Calculate elapsed time
            elapsed_time = time.time() - start_time

            # Convert the result to a dictionary
            evaluation_result = result.dict()

            # Try to track token usage via model_optimizer
            try:
                from app.services.model_optimizer import track_token_usage

                # Extract request_id if it's in the model config
                request_id = "unknown"
                if model_config and "optimization_metadata" in model_config:
                    request_id = model_config["optimization_metadata"].get(
                        "request_id", "unknown"
                    )

                # Try to extract token usage from the result
                # This implementation will depend on how PydanticAI reports token usage
                input_tokens = getattr(result, "_input_tokens", 0)
                output_tokens = getattr(result, "_output_tokens", 0)

                # If we can't get them directly, use approximation
                if input_tokens == 0:
                    # Approximate tokens (4 chars per token)
                    input_tokens = len(user_message) // 4
                if output_tokens == 0:
                    # Approximate tokens (4 chars per token)
                    output_tokens = len(str(evaluation_result)) // 4

                # Track the usage
                track_token_usage(
                    model=model_name,
                    task_name="resume_evaluation",
                    request_id=request_id,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )

                logfire.info(
                    "Token usage tracked for evaluation",
                    model=model_name,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    duration_seconds=round(elapsed_time, 2),
                )
            except ImportError:
                # model_optimizer might not be available
                pass
            except Exception as tracking_error:
                # Log but don't fail if token tracking has an error
                logfire.warning(
                    "Error tracking token usage for evaluation",
                    error=str(tracking_error),
                    model=model_name,
                )

            # Log success
            logfire.info(
                "Resume-job evaluation completed successfully",
                response_length=len(str(evaluation_result)),
                duration_seconds=round(elapsed_time, 2),
                match_score=evaluation_result.get("match_score"),
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
                duration_seconds=round(elapsed_time, 2),
            )

            # Re-raise the exception
            raise e


@log_function_call
async def generate_optimization_plan(
    resume_content: str,
    job_description: str,
    evaluation: Dict,
    customization_level: CustomizationLevel = CustomizationLevel.BALANCED,
    industry: Optional[str] = None,
    model_config: Optional[Dict[str, Any]] = None,
) -> CustomizationPlan:
    """
    Generate a detailed optimization plan based on an evaluation of resume-job match.

    Args:
        resume_content: The content of the resume in Markdown format
        job_description: The job description text
        evaluation: The evaluation dictionary from the evaluator stage
        customization_level: Level of customization (affects optimization detail)
        industry: Optional industry name for industry-specific guidance
        model_config: Optional model configuration to override defaults

    Returns:
        CustomizationPlan object with detailed recommendations
    """
    # PydanticAI is a required dependency - no need to check

    # Start timer for performance tracking
    start_time = time.time()

    # Create a span in OpenTelemetry for tracing
    with logfire.span("generate_optimization_plan_operation") as span:
        span.set_attribute("resume_length", len(resume_content))
        span.set_attribute("job_description_length", len(job_description))
        span.set_attribute("customization_level", customization_level.value)
        span.set_attribute("industry", industry if industry else "not specified")
        span.set_attribute("has_model_config", model_config is not None)

        # Log operation start
        logfire.info(
            "Starting optimization plan generation",
            resume_length=len(resume_content),
            job_description_length=len(job_description),
            customization_level=customization_level.name,
            industry=industry if industry else "not specified",
            has_custom_model_config=model_config is not None,
        )

        # Get prompts dynamically
        prompts = _get_prompts()

        # Get customization level specific instructions
        customization_instructions = prompts["get_customization_level_instructions"](
            customization_level
        )

        # Get industry-specific guidance if industry is provided
        industry_guidance = ""
        if industry:
            industry_guidance = prompts["get_industry_specific_guidance"](industry)
            if industry_guidance:
                customization_instructions += f"\n\nINDUSTRY-SPECIFIC GUIDANCE ({industry.upper()}):\n{industry_guidance}"

        # Format the prompt with the customization level instructions
        prompt_template = prompts["OPTIMIZER_PROMPT"].replace(
            "{customization_level_instructions}", customization_instructions
        )

        # Use model configuration if provided, otherwise use defaults
        if model_config:
            # Extract model configuration
            model_name = model_config.get("model", OPTIMIZER_MODEL)
            thinking_config = model_config.get(
                "thinking_config", {"thinkingBudget": THINKING_BUDGET}
            )
            temperature = model_config.get("temperature", TEMPERATURE)
            max_tokens = model_config.get("max_tokens", MAX_TOKENS)
            fallback_chain = model_config.get("fallback_config", FALLBACK_MODELS)

            logfire.info(
                "Using custom model configuration for optimization plan generation",
                model=model_name,
                customization_level=customization_level.name,
                has_thinking_config=thinking_config is not None,
            )
        else:
            # Use default configuration
            model_name = OPTIMIZER_MODEL
            thinking_config = {"thinkingBudget": THINKING_BUDGET}
            temperature = TEMPERATURE
            max_tokens = MAX_TOKENS
            fallback_chain = FALLBACK_MODELS

            logfire.info(
                "Using default model configuration for optimization plan generation",
                model=model_name,
                customization_level=customization_level.name,
                has_thinking_config=thinking_config is not None,
            )

        # Choose a more efficient model for the optimizer task if the primary model is Gemini
        from app.core.parallel_config import TASK_TIMEOUT_SECONDS

        # If Gemini is selected as the primary model, check if we have fallback models to prioritize
        # This helps avoid hanging with slow Gemini models and has better chance of success
        if model_name.startswith("google:gemini") and fallback_chain:
            # Find first non-Gemini model in fallback chain for better reliability
            for fallback in fallback_chain:
                if not fallback.startswith("google:gemini"):
                    logfire.info(
                        "Preemptively selecting non-Gemini model for optimizer due to known timeouts",
                        original_model=model_name,
                        selected_model=fallback,
                    )
                    model_name = fallback
                    # Adjust thinking config if switching provider
                    if model_name.startswith("anthropic:claude"):
                        thinking_config = {
                            "budget_tokens": THINKING_BUDGET,
                            "type": "enabled",
                        }
                    elif model_name.startswith("openai"):
                        # OpenAI doesn't support thinking budget in the same way
                        thinking_config = None
                    break

        # Create the agent with the selected configuration and timeout
        optimizer_agent = Agent(
            model_name,
            output_type=CustomizationPlan,
            system_prompt=prompt_template,
            thinking_config=thinking_config,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=TASK_TIMEOUT_SECONDS,
        )

        # Apply fallback chain
        optimizer_agent.fallback_config = fallback_chain

        # Log the fallback configuration
        logfire.info(
            "Applied fallback chain for optimizer agent",
            fallback_models=fallback_chain[:2]
            if isinstance(fallback_chain, list)
            else "None",
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

        # We're only using Claude, so there's no need for circuit breakers or fallbacks
        provider = "anthropic"

        try:
            # Register tools if needed (optimizer doesn't seem to need tools at the moment)
            @optimizer_agent.tool
            def extract_keywords_for_job(
                job_description: str = job_description, max_keywords: int = 20
            ) -> List[str]:
                """Extract important keywords from the job description."""
                return extract_keywords(job_description, max_keywords)

            # Run the agent with explicit timeout handling
            from app.core.parallel_config import TASK_TIMEOUT_SECONDS

            # Log the start time for better debugging
            api_start_time = time.time()
            logfire.info(
                "Starting optimizer API call with timeout",
                provider=provider,
                timeout_seconds=TASK_TIMEOUT_SECONDS,
                start_time=api_start_time,
            )

            # Use asyncio.wait_for to add an additional timeout layer
            try:
                result = await asyncio.wait_for(
                    optimizer_agent.run(user_message),
                    timeout=TASK_TIMEOUT_SECONDS
                    - 1,  # Set slightly lower to ensure it triggers before the model timeout
                )
                api_end_time = time.time()
                api_duration = api_end_time - api_start_time

                logfire.info(
                    "Optimizer API call completed successfully",
                    provider=provider,
                    duration_seconds=round(api_duration, 2),
                )

                # We're not using circuit breakers, so no need to record success
            except asyncio.TimeoutError:
                api_duration = time.time() - api_start_time
                logfire.error(
                    "Optimizer API call timed out",
                    provider=provider,
                    duration_seconds=round(api_duration, 2),
                    timeout_seconds=TASK_TIMEOUT_SECONDS,
                )
                # We're not using circuit breakers, so no need to record failure
                raise asyncio.TimeoutError(
                    f"Optimizer API call to {provider} timed out after {round(api_duration, 2)} seconds"
                )

            # Calculate elapsed time
            elapsed_time = time.time() - start_time

            # Result is already a validated CustomizationPlan instance

            # Try to track token usage via model_optimizer
            try:
                from app.services.model_optimizer import track_token_usage

                # Extract request_id if it's in the model config
                request_id = "unknown"
                if model_config and "optimization_metadata" in model_config:
                    request_id = model_config["optimization_metadata"].get(
                        "request_id", "unknown"
                    )
                else:
                    # Generate a unique request ID
                    request_id = f"optimize_{provider}_{int(time.time())}"

                # Try to extract token usage from the result
                # This implementation will depend on how PydanticAI reports token usage
                input_tokens = getattr(result, "_input_tokens", 0)
                output_tokens = getattr(result, "_output_tokens", 0)

                # If we can't get them directly, use approximation
                if input_tokens == 0:
                    # Approximate tokens (4 chars per token)
                    input_tokens = len(user_message) // 4
                if output_tokens == 0:
                    # Approximate tokens (4 chars per token)
                    output_tokens = len(str(result)) // 4

                # Track the usage
                track_token_usage(
                    model=optimizer_agent.model,
                    task_name="optimization_plan",
                    request_id=request_id,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )

                logfire.info(
                    "Token usage tracked for optimization plan",
                    model=optimizer_agent.model,
                    provider=provider,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    duration_seconds=round(elapsed_time, 2),
                )
            except ImportError:
                # model_optimizer might not be available
                pass
            except Exception as tracking_error:
                # Log but don't fail if token tracking has an error
                logfire.warning(
                    "Error tracking token usage for optimization",
                    error=str(tracking_error),
                    provider=provider,
                )

            # Log success
            logfire.info(
                "Optimization plan generation completed successfully",
                provider=provider,
                response_length=len(str(result)),
                duration_seconds=round(elapsed_time, 2),
                recommendation_count=len(result.recommendations),
            )

            return result

        except asyncio.TimeoutError as e:
            # Calculate elapsed time
            elapsed_time = time.time() - start_time

            # We're not using circuit breakers, so no need to record failure

            # Log error
            logfire.error(
                "Timeout generating optimization plan",
                provider=provider,
                error="Request timed out after {0} seconds".format(
                    TASK_TIMEOUT_SECONDS
                ),
                error_type="TimeoutError",
                duration_seconds=round(elapsed_time, 2),
            )

            # Re-raise the exception
            raise e

        except Exception as e:
            # Calculate elapsed time
            elapsed_time = time.time() - start_time

            # We're not using circuit breakers, so no need to record failure

            # Log error
            logfire.error(
                "Error generating optimization plan",
                provider=provider,
                error=str(e),
                error_type=type(e).__name__,
                duration_seconds=round(elapsed_time, 2),
            )

            # Re-raise the exception
            raise e


@log_function_call
async def customize_resume(
    resume_content: str,
    job_description: str,
    customization_strength: int = 2,
    focus_areas: Optional[str] = None,
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
    # PydanticAI is a required dependency - no need to check

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
            focus_areas=focus_areas,
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

        # Create a specialized agent for text generation with timeout
        from app.core.parallel_config import TASK_TIMEOUT_SECONDS

        customization_agent = Agent(
            DEFAULT_MODEL,
            output_format="text",  # Use text format for direct output
            system_prompt=system_prompt,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            timeout=TASK_TIMEOUT_SECONDS,
        )

        # Build the user message
        user_message = f"""
        Here is my current resume in Markdown format:

        {resume_content}

        Here is the job description I'm applying for:

        {job_description}

        Please customize my resume for this specific job.
        """

        # Register tools on the agent
        @customization_agent.tool
        def extract_keywords_for_job(
            job_description: str = job_description, max_keywords: int = 20
        ) -> List[str]:
            """Extract important keywords from the job description."""
            return extract_keywords(job_description, max_keywords)

        @customization_agent.tool
        def simulate_ats_scan(
            resume: str = resume_content, job_desc: str = job_description
        ) -> Dict[str, Any]:
            """Simulate how an ATS system would process this resume."""
            return simulate_ats(resume, job_desc)

        # Run the agent, tracking the start and end time
        try:
            start_time = time.time()
            result = await customization_agent.run(user_message)
            elapsed_time = time.time() - start_time

            # Log success
            logfire.info(
                "Resume customization completed successfully",
                response_length=len(result),
                duration_seconds=round(elapsed_time, 2),
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
                duration_seconds=round(elapsed_time, 2),
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
    tone: str = "professional",
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
    # PydanticAI is a required dependency - no need to check

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
            model=COVER_LETTER_MODEL,
        )

        # Create the cover letter agent with all personalization options
        cover_letter_agent = create_cover_letter_agent(
            applicant_name=applicant_name,
            company_name=company_name,
            hiring_manager_name=hiring_manager_name,
            additional_context=additional_context,
            tone=tone,
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
                personalization_count = (
                    len(result.personalization_elements)
                    if result.personalization_elements
                    else 0
                )

                # Log success
                logfire.info(
                    "Cover letter generation completed successfully",
                    response_length=len(result.content),
                    sections_count=sections_count,
                    personalization_count=personalization_count,
                    duration_seconds=round(elapsed_time, 2),
                    attempt=retry_count + 1,
                )

                # Return just the content for compatibility with existing APIs
                return result.content

            except Exception as e:
                retry_count += 1
                # Log error
                logfire.warning(
                    "Error generating cover letter, will retry"
                    if retry_count <= max_retries
                    else "Final error generating cover letter",
                    error=str(e),
                    error_type=type(e).__name__,
                    duration_seconds=round(time.time() - start_time, 2),
                    attempt=retry_count,
                    will_retry=retry_count <= max_retries,
                )

                if retry_count > max_retries:
                    # Re-raise the exception on final failure
                    logfire.error(
                        "Failed to generate cover letter after all retries",
                        error=str(e),
                        error_type=type(e).__name__,
                        duration_seconds=round(time.time() - start_time, 2),
                        attempts=retry_count,
                    )
                    raise e

                # We're not using fallback models, so just retry with the same model
                logfire.info(
                    "Retrying with Claude",
                    attempt=retry_count
                )

                # Wait briefly before retrying
                await asyncio.sleep(1)
