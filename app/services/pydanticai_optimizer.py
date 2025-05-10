"""
PydanticAI implementation of the evaluator-optimizer pattern for resume customization.

This module implements a multi-stage AI workflow using PydanticAI:
1. Evaluation (AI acting as ATS expert)
2. Optimization (AI generating a detailed plan)
3. Feedback loop for iterative refinement
4. Implementation (applying the optimizations)

The design follows the same structure as customization_service.py but leverages
PydanticAI's model-agnostic capabilities for provider flexibility.
"""

import json
import time
from typing import Dict, Optional, Tuple

import logfire
from pydantic_ai import Agent
from sqlalchemy.orm import Session

from app.core.config import get_pydanticai_model_config, settings
from app.core.logging import log_function_call
from app.models.job import JobDescription
from app.models.resume import ResumeVersion
from app.schemas.customize import (
    CustomizationLevel,
    CustomizationPlan,
    RecommendationItem,
)
from app.schemas.pydanticai_models import FeedbackEvaluation, ResumeEvaluation
from app.services.model_selector import get_model_config_for_task

# Set up model provider configuration
MODEL_CONFIG = get_pydanticai_model_config()

# Log initialization
logfire.info(
    "PydanticAI optimizer initialized",
    providers=list(MODEL_CONFIG.keys()),
    primary_provider=settings.PYDANTICAI_PRIMARY_PROVIDER,
    evaluator_model=settings.PYDANTICAI_EVALUATOR_MODEL,
    optimizer_model=settings.PYDANTICAI_OPTIMIZER_MODEL,
)


# Import prompts when needed to avoid circular imports
def _get_prompts():
    """Import prompts module dynamically to avoid circular imports"""
    from app.services.prompts import (
        EVALUATOR_FEEDBACK_PROMPT,
        EVALUATOR_PROMPT,
        IMPLEMENTATION_PROMPT,
        MAX_FEEDBACK_ITERATIONS,
        OPTIMIZER_FEEDBACK_RESPONSE_PROMPT,
        OPTIMIZER_PROMPT,
        get_customization_level_instructions,
        get_industry_specific_guidance,
    )

    return {
        "get_customization_level_instructions": get_customization_level_instructions,
        "get_industry_specific_guidance": get_industry_specific_guidance,
        "EVALUATOR_PROMPT": EVALUATOR_PROMPT,
        "OPTIMIZER_PROMPT": OPTIMIZER_PROMPT,
        "EVALUATOR_FEEDBACK_PROMPT": EVALUATOR_FEEDBACK_PROMPT,
        "OPTIMIZER_FEEDBACK_RESPONSE_PROMPT": OPTIMIZER_FEEDBACK_RESPONSE_PROMPT,
        "IMPLEMENTATION_PROMPT": IMPLEMENTATION_PROMPT,
        "MAX_FEEDBACK_ITERATIONS": MAX_FEEDBACK_ITERATIONS,
    }


# Utility function to create an evaluator agent
def create_evaluator_agent(
    customization_level: CustomizationLevel = CustomizationLevel.BALANCED,
    industry: Optional[str] = None,
    is_feedback_agent: bool = False,
) -> Agent:
    """
    Create a PydanticAI agent for evaluating resume-job match.

    Args:
        customization_level: Level of customization (affects evaluation detail)
        industry: Optional industry name for industry-specific guidance
        is_feedback_agent: Whether this agent is for providing feedback on optimization

    Returns:
        PydanticAI Agent configured for resume evaluation
    """
    # Get prompts dynamically
    prompts = _get_prompts()

    # Select the appropriate base prompt based on whether this is a feedback agent
    if is_feedback_agent:
        prompt_template = prompts["EVALUATOR_FEEDBACK_PROMPT"]
        output_type = FeedbackEvaluation

        # Add any industry-specific considerations if relevant
        if industry:
            industry_guidance = prompts["get_industry_specific_guidance"](industry)
            if industry_guidance:
                prompt_template += f"\n\nConsider this INDUSTRY-SPECIFIC GUIDANCE for {industry.upper()}:\n{industry_guidance}"
    else:
        # Standard evaluator agent
        # Get customization level specific instructions
        customization_instructions = prompts["get_customization_level_instructions"](
            customization_level
        )

        # Get industry-specific guidance if industry is provided
        if industry:
            industry_guidance = prompts["get_industry_specific_guidance"](industry)
            if industry_guidance:
                customization_instructions += f"\n\nINDUSTRY-SPECIFIC GUIDANCE ({industry.upper()}):\n{industry_guidance}"

        # Format the prompt with the customization level instructions
        prompt_template = prompts["EVALUATOR_PROMPT"].replace(
            "{customization_level_instructions}", customization_instructions
        )
        output_type = ResumeEvaluation

    # Get model configuration from the central config
    model_config = get_pydanticai_model_config()

    # Ensure we're using Google Gemini as the primary model
    # Get the model from the configuration if available, otherwise use default
    model = (
        model_config.get("gemini", {}).get("default_model", "google-gla:gemini-1.5-pro")
        if "gemini" in model_config
        else "google-gla:gemini-1.5-pro"
    )

    # Log the model override for debugging
    logfire.info("Using Google Gemini model for evaluation", model=model)

    # The thinking_config should be None for now - we'll set it after content is available
    thinking_config = None

    # Create the agent using PydanticAI
    try:
        # Determine ideal model based on task complexity
        # Evaluator requires deep understanding and analysis, especially for feedback
        # Use max capabilities for feedback agents due to complexity of evaluation
        temperature = settings.PYDANTICAI_TEMPERATURE

        # For feedback evaluation, we can use lower temperature for more consistent results
        if is_feedback_agent:
            temperature = max(
                0.3, temperature - 0.2
            )  # Reduce temperature but ensure it's not below 0.3

        evaluator_agent = Agent(
            model,
            output_type=output_type,
            system_prompt=prompt_template,
            thinking_config=thinking_config,
            temperature=temperature,
            max_tokens=settings.PYDANTICAI_MAX_TOKENS,
        )

        # Add fallback configurations - prioritize models that excel at evaluation
        # For evaluation tasks, we need models with strong reasoning capabilities
        # Get fallback models from the service module to ensure consistency
        from app.services.pydanticai_service import FALLBACK_MODELS

        # Use the centralized fallback models
        fallbacks = FALLBACK_MODELS

        # Add any other models from settings that aren't already in the list
        fallbacks += [
            m for m in settings.PYDANTICAI_FALLBACK_MODELS if m not in fallbacks
        ]

        evaluator_agent.fallback_config = fallbacks

        logfire.info(
            "Resume Evaluator Agent created successfully",
            model=model,
            temperature=temperature,
            is_feedback_agent=is_feedback_agent,
            fallbacks=fallbacks[:3],  # Log only first 3 fallbacks to avoid verbose logs
        )

        return evaluator_agent

    except Exception as e:
        logfire.error(
            "Error creating Resume Evaluator Agent",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise e


# Note: The previous helper functions for agent creation (create_optimizer_agent and create_implementation_agent)
# have been removed as they've been replaced with direct model selection in the main workflow functions.
# Agent creation now happens directly in the main functions with the dynamic model selection.


class PydanticAIOptimizerService:
    """
    Service for resume customization using PydanticAI's evaluator-optimizer pattern.
    This implements a multi-stage AI workflow:
    1. Evaluation (AI acting as ATS expert)
    2. Optimization (AI generating a detailed plan)
    3. Optional feedback loop for iterative refinement
    4. Implementation (applying the optimizations)
    """

    def __init__(self, db: Session):
        """
        Initialize the PydanticAI optimizer service with dependencies.

        Args:
            db: Database session
        """
        self.db = db

    @log_function_call
    async def generate_customization_plan(
        self,
        resume_id: str,
        job_id: str,
        customization_strength: CustomizationLevel = CustomizationLevel.BALANCED,
        industry: Optional[str] = None,
        ats_analysis: Optional[Dict] = None,
        iterations: int = 1,
    ) -> CustomizationPlan:
        """
        Generate a detailed customization plan for a resume based on a job description.
        This implements the evaluator-optimizer pattern.

        Args:
            resume_id: Resume ID
            job_id: Job description ID
            customization_strength: Level of customization
            industry: Optional industry name for industry-specific guidance
            ats_analysis: Optional existing ATS analysis to use
            iterations: Number of feedback iterations to perform

        Returns:
            A CustomizationPlan with detailed recommendations
        """
        # Ensure iterations is within reasonable limits
        iterations = max(1, min(iterations, _get_prompts()["MAX_FEEDBACK_ITERATIONS"]))

        # Gather the necessary data
        resume_content, job_description = await self._get_resume_and_job(
            resume_id, job_id
        )

        # Use provided analysis or perform basic analysis
        basic_analysis = ats_analysis
        if not basic_analysis:
            basic_analysis = await self._perform_basic_analysis(resume_id, job_id)

        # Evaluate the match (evaluator stage)
        start_time_evaluator = time.time()
        logfire.info(
            "Starting evaluator stage with PydanticAI",
            resume_id=resume_id,
            job_id=job_id,
            customization_level=customization_strength.name,
            industry=industry if industry else "not specified",
            using_extended_thinking="claude-3-7" in settings.PYDANTICAI_EVALUATOR_MODEL,
        )
        evaluation = await self.evaluate_match(
            resume_content,
            job_description,
            basic_analysis,
            customization_strength,
            industry,
        )

        # Log evaluation results with metrics
        elapsed_time_evaluator = time.time() - start_time_evaluator
        logfire.info(
            "Evaluator stage completed",
            resume_id=resume_id,
            job_id=job_id,
            duration_seconds=round(elapsed_time_evaluator, 2),
            match_score=evaluation.get("match_score", 0),
            term_mismatches_count=len(evaluation.get("term_mismatches", [])),
            sections_evaluated=len(evaluation.get("section_evaluations", [])),
        )

        # Generate the optimization plan (optimizer stage)
        start_time_optimizer = time.time()
        logfire.info(
            "Starting optimizer stage with PydanticAI",
            resume_id=resume_id,
            job_id=job_id,
            customization_level=customization_strength.name,
            industry=industry if industry else "not specified",
            using_extended_thinking="claude-3-7" in settings.PYDANTICAI_OPTIMIZER_MODEL,
        )
        plan = await self.generate_optimization_plan_from_evaluation(
            resume_content,
            job_description,
            evaluation,
            customization_strength,
            industry,
        )

        # Log optimizer results with metrics
        elapsed_time_optimizer = time.time() - start_time_optimizer
        logfire.info(
            "Optimizer stage completed",
            resume_id=resume_id,
            job_id=job_id,
            duration_seconds=round(elapsed_time_optimizer, 2),
            recommendations_count=len(plan.recommendations),
            keywords_added_count=len(plan.keywords_to_add),
            formatting_suggestions_count=len(plan.formatting_suggestions),
        )

        # Perform additional iterations if requested
        if iterations > 1:
            plan = await self._perform_feedback_iterations(
                original_resume=resume_content,
                job_description=job_description,
                evaluation=evaluation,
                initial_plan=plan,
                customization_strength=customization_strength,
                industry=industry,
                max_iterations=iterations - 1,  # We already did one iteration
            )

        # Store the plan for future reference
        await self._store_plan(resume_id, job_id, plan)

        return plan

    @log_function_call
    async def customize_resume(
        self,
        resume_id: str,
        job_id: str,
        customization_strength: CustomizationLevel = CustomizationLevel.BALANCED,
        industry: Optional[str] = None,
        iterations: int = 2,  # Default to 2 iterations for better results
        ats_analysis: Optional[Dict] = None,  # Added parameter to reuse ATS analysis
    ) -> Dict[str, str]:
        """
        Customize a resume for a specific job description.
        This implements the full evaluator-optimizer-implementation workflow.

        Args:
            resume_id: Resume ID
            job_id: Job description ID
            customization_strength: Level of customization
            industry: Optional industry name for industry-specific guidance
            iterations: Number of feedback iterations to perform
            ats_analysis: Optional existing ATS analysis to reuse (avoids duplicate analysis)

        Returns:
            Dictionary with original and customized resume
        """
        # Gather the necessary data
        resume_content, job_description = await self._get_resume_and_job(
            resume_id, job_id
        )

        # Generate the customization plan with feedback iterations
        # Pass the existing ATS analysis if provided
        plan = await self.generate_customization_plan(
            resume_id=resume_id,
            job_id=job_id,
            customization_strength=customization_strength,
            industry=industry,
            iterations=iterations,
            ats_analysis=ats_analysis,
        )

        # Implement the plan (apply changes to the resume)
        start_time_implementation = time.time()
        logfire.info(
            "Starting implementation stage with PydanticAI",
            resume_id=resume_id,
            job_id=job_id,
            customization_level=customization_strength.name,
            recommendation_count=len(plan.recommendations),
        )

        # Implement the optimization plan
        customized_resume = await self._implement_optimization_plan(
            resume_content=resume_content,
            job_description=job_description,
            plan=plan,
            customization_strength=customization_strength,
            industry=industry,
        )

        # Log implementation results with metrics
        elapsed_time_implementation = time.time() - start_time_implementation
        logfire.info(
            "Implementation stage completed",
            resume_id=resume_id,
            job_id=job_id,
            duration_seconds=round(elapsed_time_implementation, 2),
            original_length=len(resume_content),
            customized_length=len(customized_resume),
        )

        # Save the customized resume as a new version
        new_resume_id = await self._save_customized_resume(
            resume_id=resume_id, job_id=job_id, customized_content=customized_resume
        )

        return {
            "original_resume_id": resume_id,
            "customized_resume_id": new_resume_id,
            "job_description_id": job_id,
            "original_content": resume_content,
            "customized_content": customized_resume,
        }

    async def _get_resume_and_job(self, resume_id: str, job_id: str) -> Tuple[str, str]:
        """
        Retrieve resume content and job description from the database.

        Args:
            resume_id: Resume ID
            job_id: Job description ID

        Returns:
            Tuple of (resume_content, job_description)

        Raises:
            ValueError: If resume or job not found
        """
        # Use one database query to get both resume and job description by joining tables
        try:
            # Get resume content and job description in a single query
            resume_version = (
                self.db.query(ResumeVersion)
                .filter(ResumeVersion.resume_id == resume_id)
                .order_by(ResumeVersion.version_number.desc())
                .first()
            )

            if not resume_version:
                logfire.error("Resume version not found", resume_id=resume_id)
                raise ValueError(f"Resume content not found for ID: {resume_id}")

            # Check if we already have the job description linked in this resume version
            if (
                resume_version.job_description_id == job_id
                and hasattr(resume_version, "job_description")
                and resume_version.job_description
            ):
                # We have the job description already joined
                job_description = resume_version.job_description.description
            else:
                # Get job description separately
                job = (
                    self.db.query(JobDescription)
                    .filter(JobDescription.id == job_id)
                    .first()
                )
                if not job:
                    logfire.error("Job description not found", job_id=job_id)
                    raise ValueError(f"Job description not found for ID: {job_id}")
                job_description = job.description

            return resume_version.content, job_description

        except Exception as e:
            if not isinstance(e, ValueError):
                logfire.error(
                    "Error retrieving resume and job data",
                    error=str(e),
                    resume_id=resume_id,
                    job_id=job_id,
                )
            raise

    async def _perform_basic_analysis(self, resume_id: str, job_id: str) -> Dict:
        """
        Perform basic ATS analysis of resume vs job description.

        Args:
            resume_id: Resume ID
            job_id: Job description ID

        Returns:
            Dictionary containing basic analysis results
        """
        logfire.info(
            "Performing basic ATS analysis", resume_id=resume_id, job_id=job_id
        )

        try:
            # Get resume content and job description
            resume_content, job_description = await self._get_resume_and_job(
                resume_id, job_id
            )

            # Import here to avoid circular imports
            from app.services.ats_service import analyze_resume_for_ats

            # Perform the analysis using the ATS service
            analysis_result = await analyze_resume_for_ats(
                resume_content=resume_content, job_description=job_description
            )

            # Add the IDs to the result
            analysis_result["resume_id"] = resume_id
            analysis_result["job_description_id"] = job_id

            logfire.info(
                "Basic ATS analysis completed successfully",
                resume_id=resume_id,
                job_id=job_id,
                match_score=analysis_result.get("match_score", 0),
            )

            return analysis_result

        except Exception as e:
            logfire.error(
                "Error performing basic ATS analysis",
                error=str(e),
                resume_id=resume_id,
                job_id=job_id,
            )

            # Return a basic structure in case of error
            return {
                "resume_id": resume_id,
                "job_description_id": job_id,
                "match_score": 50,  # Default middle score
                "matching_keywords": [],
                "missing_keywords": [],
                "error": str(e),
            }

    async def analyze_content_and_create_plan(
        self,
        resume_content: str,
        job_description_content: str,
        basic_analysis: Dict,
        customization_level: CustomizationLevel,
        industry: Optional[str] = None,
    ) -> CustomizationPlan:
        """
        Public method that combines the evaluation and optimization steps for content-based analysis.
        This method should be used when you have the actual content rather than database IDs.

        Args:
            resume_content: The raw resume content as a string
            job_description_content: The raw job description content as a string
            basic_analysis: Results from the basic ATS analysis
            customization_level: The level of customization to apply
            industry: Optional industry context for better recommendations

        Returns:
            A detailed customization plan with recommendations
        """
        # First evaluate the match
        evaluation = await self.evaluate_match(
            resume_content,
            job_description_content,
            basic_analysis,
            customization_level,
            industry,
        )

        # Then generate an optimization plan based on the evaluation
        plan = await self.generate_optimization_plan_from_evaluation(
            resume_content,
            job_description_content,
            evaluation,
            customization_level,
            industry,
        )

        return plan

    async def evaluate_match(
        self,
        resume_content: str,
        job_description: str,
        basic_analysis: Dict,
        customization_level: CustomizationLevel,
        industry: Optional[str] = None,
    ) -> Dict:
        """
        Evaluate how well a resume matches a job description using PydanticAI.
        This is the "evaluator" stage of the evaluator-optimizer pattern.

        Args:
            resume_content: Resume content in Markdown format
            job_description: Job description text
            basic_analysis: Results from basic keyword analysis
            customization_level: Customization level (affects evaluation detail)
            industry: Optional industry name for industry-specific guidance

        Returns:
            Dictionary containing detailed evaluation
        """
        logfire.info(
            "Evaluating resume-job match with PydanticAI",
            resume_length=len(resume_content),
            job_description_length=len(job_description),
            customization_level=customization_level.name,
            industry=industry if industry else "not specified",
        )

        # Use model selector to get the best model configuration
        cost_sensitivity = (
            1.0
            if customization_level == CustomizationLevel.BALANCED
            else 0.5
            if customization_level == CustomizationLevel.EXTENSIVE
            else 1.5
        )

        # Force Google provider for testing
        model_config = get_model_config_for_task(
            task_name="resume_evaluation",
            content=resume_content,
            job_description=job_description,
            industry=industry,
            # Force Google as preferred provider
            preferred_provider="google",
            # Adjust cost sensitivity based on customization level
            cost_sensitivity=cost_sensitivity,
        )

        # Log the model selection in detail
        logfire.info(
            "Model selection for evaluator agent",
            selected_model=model_config.get("model", "unknown"),
            provider=model_config.get("model", "unknown").split(":")[0]
            if ":" in model_config.get("model", "unknown")
            else "unknown",
            customization_level=customization_level.value,
            cost_sensitivity=cost_sensitivity,
            thinking_config=model_config.get("thinking_config", None),
        )

        # SKIP the standard agent creation and create the agent directly with our model
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

        # Add structured output instructions
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

        # Get thinking configuration from model config
        thinking_config = model_config.get("thinking_config", None)

        # Direct agent creation with selected model
        # Get the Gemini model from the central configuration
        from app.services.pydanticai_service import (
            EVALUATOR_MODEL,
            ResumeEvaluation,
        )

        gemini_model = EVALUATOR_MODEL

        # Log the model override
        logfire.info(
            "Overriding model selection to use Google Gemini",
            original_model=model_config.get("model", "unknown"),
            override_model=gemini_model,
        )

        evaluator_agent = Agent(
            gemini_model,  # Force Google Gemini instead of using model_config["model"]
            output_type=ResumeEvaluation,
            system_prompt=prompt_template,
            thinking_config=thinking_config,
            temperature=model_config.get("temperature", 0.7),
            max_tokens=model_config.get("max_tokens", 8000),
        )

        # Use the centralized fallback models
        from app.services.pydanticai_service import FALLBACK_MODELS

        fallback_chain = FALLBACK_MODELS

        # Apply our custom fallback chain instead of using model_config
        evaluator_agent.fallback_config = fallback_chain

        # Log the fallback chain override
        logfire.info(
            "Applied custom fallback chain prioritizing Google models",
            fallback_models=fallback_chain[
                :2
            ],  # Log only first 2 fallbacks to reduce verbosity
        )

        logfire.info(
            "Created evaluator agent directly with selected model",
            model=gemini_model,
            provider=model_config["model"].split(":")[0]
            if ":" in model_config["model"]
            else "unknown",
            has_thinking=thinking_config is not None,
            fallback_count=len(model_config.get("fallback_config", [])),
        )

        logfire.info(
            "Applied model selection to evaluator agent",
            selected_model=model_config["model"],
            has_thinking_config="thinking_config" in model_config,
            fallback_count=len(model_config.get("fallback_config", [])),
            resume_length=len(resume_content),
            job_description_length=len(job_description),
        )

        # Prepare basic analysis data
        basic_analysis_str = ""
        if basic_analysis:
            # Convert complex objects to serializable format
            basic_analysis_copy = {}
            for key, value in basic_analysis.items():
                if isinstance(value, (str, int, float, bool, type(None))):
                    basic_analysis_copy[key] = value
                elif isinstance(value, list):
                    basic_analysis_copy[key] = []
                    for item in value:
                        if hasattr(item, "__dict__"):
                            basic_analysis_copy[key].append(item.__dict__)
                        else:
                            basic_analysis_copy[key].append(item)
                elif hasattr(value, "__dict__"):
                    basic_analysis_copy[key] = value.__dict__

            basic_analysis_str = json.dumps(basic_analysis_copy, indent=2)

        # Build the final prompt with the resume, job description, and analysis
        prompt = f"""
        Resume:
        {resume_content}

        Job Description:
        {job_description}

        {f"Industry: {industry}" if industry else ""}

        {f"Basic Analysis: {basic_analysis_str}" if basic_analysis else ""}

        CRITICALLY IMPORTANT: Use the provided evaluator system prompt to guide your analysis.
        """

        try:
            # Run the evaluator agent
            start_time = time.time()
            result = await evaluator_agent.run(prompt)
            elapsed_time = time.time() - start_time

            # Access the output property of AgentRunResult which contains the Pydantic model
            pydantic_result = result.output

            # Convert Pydantic model to dictionary using built-in methods
            if hasattr(pydantic_result, "model_dump"):
                # Pydantic v2
                evaluation_result = pydantic_result.model_dump()
            elif hasattr(pydantic_result, "dict"):
                # Pydantic v1
                evaluation_result = pydantic_result.dict()
            else:
                # Fallback (should not happen with properly configured output_type)
                evaluation_result = {
                    attr: getattr(pydantic_result, attr)
                    for attr in dir(pydantic_result)
                    if not attr.startswith("_")
                    and not callable(getattr(pydantic_result, attr))
                }

            # Log success
            logfire.info(
                "Resume-job evaluation completed successfully with PydanticAI",
                duration_seconds=round(elapsed_time, 2),
                match_score=evaluation_result.get("match_score", 0),
            )

            return evaluation_result

        except Exception as e:
            logfire.error(
                "Error evaluating resume job match with PydanticAI",
                error=str(e),
                error_type=type(e).__name__,
            )

            # Create a basic fallback evaluation to avoid breaking the pipeline
            return {
                "overall_assessment": f"Error during evaluation: {str(e)}. The resume appears to match some elements of the job description, but could be improved.",
                "match_score": 50,  # Default middle score
                "job_key_requirements": [],
                "strengths": [],
                "gaps": [],
                "term_mismatches": [],
                "section_evaluations": [],
                "competitor_analysis": "Unable to perform competitor analysis due to evaluation error.",
                "reframing_opportunities": [],
                "experience_preservation_check": "Could not verify experience preservation due to evaluation error.",
            }

    async def generate_optimization_plan_from_evaluation(
        self,
        resume_content: str,
        job_description: str,
        evaluation: Dict,
        customization_level: CustomizationLevel,
        industry: Optional[str] = None,
    ) -> CustomizationPlan:
        """
        Generate an optimization plan based on the evaluation.
        This is the "optimizer" stage of the evaluator-optimizer pattern.

        Args:
            resume_content: Resume content in Markdown format
            job_description: Job description text
            evaluation: Evaluation dictionary from evaluator stage
            customization_level: Customization level (affects optimization detail)
            industry: Optional industry name for industry-specific guidance

        Returns:
            CustomizationPlan with detailed recommendations
        """
        logfire.info(
            "Generating optimization plan with PydanticAI",
            resume_length=len(resume_content),
            job_description_length=len(job_description),
            customization_level=customization_level.name,
            industry=industry if industry else "not specified",
        )

        # Use model selector to get the best model configuration
        cost_sensitivity = (
            1.0
            if customization_level == CustomizationLevel.BALANCED
            else 0.5
            if customization_level == CustomizationLevel.EXTENSIVE
            else 1.5
        )

        # Force Google provider for testing
        model_config = get_model_config_for_task(
            task_name="optimization_plan",
            content=resume_content,
            job_description=job_description,
            industry=industry,
            # Force Google as preferred provider
            preferred_provider="google",
            # Adjust cost sensitivity based on customization level
            cost_sensitivity=cost_sensitivity,
        )

        # Log the model selection in detail
        logfire.info(
            "Model selection for optimizer agent",
            selected_model=model_config.get("model", "unknown"),
            provider=model_config.get("model", "unknown").split(":")[0]
            if ":" in model_config.get("model", "unknown")
            else "unknown",
            customization_level=customization_level.value,
            cost_sensitivity=cost_sensitivity,
            thinking_config=model_config.get("thinking_config", None),
        )

        # SKIP the standard agent creation and create the agent directly with our model
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

        # Get thinking configuration from model config
        thinking_config = model_config.get("thinking_config", None)

        # Get the Gemini model from the central configuration
        from app.services.pydanticai_service import EVALUATOR_MODEL

        gemini_model = EVALUATOR_MODEL

        # Log the model override
        logfire.info(
            "Overriding model selection to use Google Gemini for optimizer",
            original_model=model_config.get("model", "unknown"),
            override_model=gemini_model,
        )

        # Direct agent creation with selected model
        from app.schemas.customize import CustomizationPlan

        optimizer_agent = Agent(
            gemini_model,  # Force Google Gemini instead of using model_config["model"]
            output_type=CustomizationPlan,
            system_prompt=prompt_template,
            thinking_config=thinking_config,
            temperature=model_config.get("temperature", 0.7),
            max_tokens=model_config.get("max_tokens", 8000),
        )

        # Use the centralized fallback models
        from app.services.pydanticai_service import FALLBACK_MODELS

        fallback_chain = FALLBACK_MODELS

        # Apply our custom fallback chain instead of using model_config
        optimizer_agent.fallback_config = fallback_chain

        # Log the fallback chain override
        logfire.info(
            "Applied custom fallback chain prioritizing Google models for optimizer",
            fallback_models=fallback_chain[
                :2
            ],  # Log only first 2 fallbacks to reduce verbosity
        )

        logfire.info(
            "Created optimizer agent directly with selected model",
            model=gemini_model,
            provider="google",
            has_thinking=thinking_config is not None,
            fallback_count=len(model_config.get("fallback_config", [])),
        )

        logfire.info(
            "Applied model selection to optimizer agent",
            selected_model=gemini_model,
            has_thinking_config="thinking_config" in model_config,
            fallback_count=len(model_config.get("fallback_config", [])),
            resume_length=len(resume_content),
            job_description_length=len(job_description),
        )

        # Build the input prompt - adapt for new OPTIMIZER_PROMPT format
        # Get the prompts module
        prompts = _get_prompts()

        # Get optimizer prompt template
        optimizer_prompt_template = prompts.get("OPTIMIZER_PROMPT")

        # Replace placeholders in the optimizer prompt template
        prompt = optimizer_prompt_template
        prompt = prompt.replace("{{resume}}", resume_content)
        prompt = prompt.replace("{{job_description}}", job_description)

        # Create customization level instructions
        customization_instructions = ""
        if customization_level == CustomizationLevel.CONSERVATIVE:
            customization_instructions = "Conservative customization - make minimal changes focused only on the most critical improvements."
        elif customization_level == CustomizationLevel.BALANCED:
            customization_instructions = "Balanced customization - make a moderate number of high-impact changes."
        elif customization_level == CustomizationLevel.EXTENSIVE:
            customization_instructions = "Extensive customization - be comprehensive in optimizing the resume while maintaining truthfulness."

        # Add evaluation data as additional context
        # We should already have a dictionary from _evaluate_match
        # But ensure it's serializable before adding to the prompt
        try:
            evaluation_json = json.dumps(evaluation, indent=2)
            customization_instructions += f"\n\nEvaluation data:\n{evaluation_json}"
        except TypeError as e:
            # In the unlikely case evaluation still contains non-serializable objects
            logfire.warning(
                "Could not directly serialize evaluation, attempting conversion",
                error=str(e),
            )
            # Try to convert it first if needed
            evaluation_dict = (
                evaluation.model_dump()
                if hasattr(evaluation, "model_dump")
                else evaluation.dict()
                if hasattr(evaluation, "dict")
                else evaluation
            )
            evaluation_json = json.dumps(evaluation_dict, indent=2)
            customization_instructions += f"\n\nEvaluation data:\n{evaluation_json}"

        # Add industry information if available
        if industry:
            industry_guidance = prompts.get("get_industry_specific_guidance")(industry)
            if industry_guidance:
                customization_instructions += f"\n\nIndustry-specific guidance for {industry.upper()}:\n{industry_guidance}"

        # Replace the placeholder for customization level instructions
        prompt = prompt.replace(
            "{{CUSTOMIZATION_LEVEL_INSTRUCTIONS}}", customization_instructions
        )

        if industry:
            prompt += f"\nIndustry: {industry}"

        try:
            # Run the optimizer agent
            start_time = time.time()
            result = await optimizer_agent.run(prompt)
            elapsed_time = time.time() - start_time

            # Access the output property of AgentRunResult which contains the Pydantic model
            plan = result.output

            # Log success
            logfire.info(
                "Optimization plan generation completed successfully with PydanticAI",
                duration_seconds=round(elapsed_time, 2),
                recommendation_count=len(plan.recommendations),
            )

            return plan

        except Exception as e:
            logfire.error(
                "Error generating optimization plan with PydanticAI",
                error=str(e),
                error_type=type(e).__name__,
            )

            # Create a basic fallback plan to avoid breaking the pipeline
            keywords = []
            if isinstance(evaluation.get("gaps"), list):
                keywords = evaluation.get("gaps", [])[:10]

            return CustomizationPlan(
                summary="Failed to generate a complete optimization plan. Here is a basic plan based on the evaluation.",
                job_analysis="The job requires skills and experience that could be better emphasized in your resume.",
                keywords_to_add=keywords,
                formatting_suggestions=[
                    "Use bullet points for achievements",
                    "Include more quantifiable results",
                    "Ensure consistent formatting",
                ],
                authenticity_statement="All recommendations maintain complete truthfulness while optimizing presentation.",
                experience_preservation_statement="All experience from the original resume is preserved in these recommendations.",
                recommendations=[
                    RecommendationItem(
                        section="General",
                        what="Update resume format and keywords",
                        why="Improves ATS compatibility and readability",
                        description="Apply consistent formatting and include relevant keywords throughout the resume to improve ATS scoring.",
                    )
                ],
            )


# Factory function to create a PydanticAI optimizer service
def get_pydanticai_optimizer_service(db: Session) -> PydanticAIOptimizerService:
    """
    Create a PydanticAI optimizer service with all required dependencies.

    Args:
        db: Database session

    Returns:
        Initialized PydanticAIOptimizerService
    """
    return PydanticAIOptimizerService(db)
