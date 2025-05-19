"""
PydanticAI optimizer service for resume customization.

This module implements the PydanticAI-based resume customization workflow,
following the evaluator-optimizer pattern described in the spec.md document.
"""

import time
import logging
import traceback
import asyncio
from typing import Dict, Any, Optional, List

import logfire
from sqlalchemy.orm import Session
from pydantic_ai import Agent, ModelRetry
from pydantic_ai.agent import RunContext
from app.core.pydantic_ai_compat import PydanticAIContext

from app.schemas.customize import CustomizationPlan
from app.models.resume import Resume, ResumeVersion
from app.models.job import JobDescription
from app.services.websocket_manager import WebSocketManager
from app.services.progress_tracker import ProgressTracker
from app.schemas.pydanticai_models import (
    ResumeAnalysis, 
    CustomizationPlan as PydanticAICustomizationPlan,
    ImplementationResult,
    VerificationResult,
    WebSocketProgressUpdate,
    WorkflowStage
)
from app.core.config import settings
from app.services.evidence_tracker import EvidenceTracker


async def get_pydanticai_optimizer_service(db: Session):
    """
    Get the PydanticAI optimizer service instance.
    
    This is a factory function that returns an instance of the PydanticAIOptimizerService.
    
    Args:
        db: Database session
        
    Returns:
        An instance of PydanticAIOptimizerService
    """
    # Get the websocket manager for progress reporting
    from app.services.websocket_manager import get_websocket_manager
    websocket_manager = await get_websocket_manager()
    return PydanticAIOptimizerService(db, websocket_manager)


class PydanticAIOptimizerService:
    """
    PydanticAI optimizer service for resume customization.
    
    This service implements the four-stage resume customization workflow using PydanticAI:
    1. Evaluation - Analyze resume against job description
    2. Planning - Create a customization plan
    3. Implementation - Apply the plan to the resume
    4. Verification - Verify the customized resume
    """
    
    # Default model configuration
    DEFAULT_MODEL = "anthropic:claude-3-7-sonnet-latest"
    TEMPERATURE = 0.5  # Lower temperature for more consistent outputs
    MAX_TOKENS = 4096
    # We're disabling thinking budget as it causes excessive API calls and hits rate limits
    
    def __init__(self, db: Session, websocket_manager: WebSocketManager):
        """
        Initialize the service with a database session.
        
        Args:
            db: Database session
            websocket_manager: WebSocket manager for progress reporting
        """
        self.db = db
        self.websocket_manager = websocket_manager
        
        # Check for API key
        if not settings.ANTHROPIC_API_KEY:
            logfire.error(
                "ANTHROPIC_API_KEY is not set",
                impact="Claude model will not be available",
            )
            raise ValueError("ANTHROPIC_API_KEY environment variable must be set")
        
        logfire.info(
            "PydanticAI optimizer service initialized",
            model=self.DEFAULT_MODEL,
            temperature=self.TEMPERATURE,
            max_tokens=self.MAX_TOKENS,
            thinking_budget=0,  # Disabled thinking budget
        )
    
    def _create_agent(self, output_type: Any, system_prompt: str) -> Agent:
        """
        Create a configured PydanticAI agent.
        
        Args:
            output_type: The output type for the agent
            system_prompt: The system prompt for the agent
            
        Returns:
            Configured PydanticAI agent
        """
        # No thinking configuration - using default model behavior
        thinking_config = None
        
        # Set model timeout
        from app.core.parallel_config import TASK_TIMEOUT_SECONDS

        # Create the PydanticAI context
        context = PydanticAIContext(
            event_type="agent_creation",
            agent_name="resume_customizer",
            model=self.DEFAULT_MODEL,
        )
        
        # Log the agent creation
        logfire.info(
            "Creating PydanticAI agent",
            output_type=str(output_type),
            model=self.DEFAULT_MODEL,
            temperature=self.TEMPERATURE,
            max_tokens=self.MAX_TOKENS,
            thinking_budget=0,  # Disabled thinking budget
        )
        
        # Create the agent with properly structured output type
        agent = Agent(
            self.DEFAULT_MODEL,
            output_type=output_type,
            system_prompt=system_prompt,
            thinking_config=thinking_config,
            temperature=self.TEMPERATURE,
            max_tokens=self.MAX_TOKENS,
            timeout=TASK_TIMEOUT_SECONDS,
        )
        
        return agent
    
    async def _run_agent_with_retry(
        self, 
        agent: Agent, 
        message: str, 
        max_attempts: int = 2,
        customization_id: Optional[str] = None,
        tracker: Optional[ProgressTracker] = None,
        stage: Optional[str] = None,
        stage_progress: Optional[int] = None,
        stage_details: Optional[str] = None
    ):
        """
        Run an agent with retry logic and progress reporting.
        
        Args:
            agent: The PydanticAI agent to run
            message: The message to send to the agent
            max_attempts: Maximum number of retry attempts
            customization_id: ID of the customization for progress tracking
            tracker: Progress tracker instance
            stage: Current workflow stage
            stage_progress: Current progress percentage for the stage
            stage_details: Details about the current progress
            
        Returns:
            Agent response object
        """
        # Update progress if we have tracking information
        if tracker and stage:
            await tracker.update_stage(
                stage=stage,
                status="in_progress",
                progress=stage_progress or 10,
                details=stage_details or f"Starting {stage} stage",
            )
        
        # Run the agent with retry logic
        attempt = 0
        start_time = time.time()
        
        while attempt < max_attempts:
            try:
                # Update progress if we have tracking information
                if tracker and stage:
                    await tracker.update_stage(
                        stage=stage,
                        status="in_progress",
                        progress=min(max(20, attempt * 30 + 20), 90),
                        details=f"Processing {stage} stage" + (f" (retry {attempt})" if attempt > 0 else ""),
                    )
                
                logfire.info(
                    f"Running PydanticAI agent for {stage or 'unknown'} stage",
                    model=agent.model,
                    attempt=attempt + 1,
                    max_attempts=max_attempts,
                    customization_id=customization_id,
                )
                
                # Use asyncio wait_for to add an additional timeout layer
                from app.core.parallel_config import TASK_TIMEOUT_SECONDS
                
                try:
                    # Create serialization context with better error handling
                    from pydantic_ai.agent import RunContext
                    
                    # Log more details about the agent call
                    logfire.info(
                        f"Running PydanticAI agent.run() for {stage or 'unknown'} stage",
                        model=agent.model,
                        output_type=str(agent.output_type),
                        message_length=len(message),
                        timeout=TASK_TIMEOUT_SECONDS - 5,
                        customization_id=customization_id,
                    )
                    
                    # Use the correct timeout value - very high to essentially disable timeout
                    result = await asyncio.wait_for(
                        agent.run(message),
                        timeout=TASK_TIMEOUT_SECONDS,  # Use the full configured timeout
                    )
                    
                    # Log the result type for debugging
                    logfire.info(
                        f"Agent run completed with result type {type(result).__name__}",
                        model=agent.model,
                        output_type=str(agent.output_type),
                        result_type=type(result).__name__,
                        stage=stage or "unknown",
                        customization_id=customization_id,
                    )
                except asyncio.TimeoutError:
                    logfire.error(
                        f"Timeout in PydanticAI agent for {stage or 'unknown'} stage",
                        model=agent.model,
                        timeout_seconds=TASK_TIMEOUT_SECONDS - 5,
                        customization_id=customization_id,
                    )
                    raise
                except Exception as e:
                    logfire.error(
                        f"Error in PydanticAI agent for {stage or 'unknown'} stage",
                        error_type=type(e).__name__,
                        error=str(e),
                        model=agent.model,
                        customization_id=customization_id,
                    )
                    raise
                
                # Calculate elapsed time
                elapsed_time = time.time() - start_time
                
                # Log success
                logfire.info(
                    f"PydanticAI agent for {stage or 'unknown'} stage completed successfully",
                    model=agent.model,
                    duration_seconds=round(elapsed_time, 2),
                    attempt=attempt + 1,
                    customization_id=customization_id,
                    response_length=len(str(result)),
                )
                
                # Update progress to indicate stage completion
                if tracker and stage:
                    await tracker.update_stage(
                        stage=stage,
                        status="completed",
                        progress=100,
                        details=f"Completed {stage} stage",
                    )
                
                # Try to track token usage
                self._track_token_usage(
                    model=agent.model,
                    task_name=stage or "unknown",
                    request_id=customization_id or "unknown",
                    input_tokens=len(message) // 4,  # Approximate
                    output_tokens=len(str(result)) // 4,  # Approximate
                )
                
                return result
                
            except (ModelRetry, asyncio.TimeoutError) as e:
                attempt += 1
                elapsed_time = time.time() - start_time
                
                logfire.warning(
                    f"PydanticAI agent for {stage or 'unknown'} stage failed",
                    model=agent.model,
                    duration_seconds=round(elapsed_time, 2),
                    attempt=attempt,
                    max_attempts=max_attempts,
                    customization_id=customization_id,
                    error_type=type(e).__name__,
                    error_message=str(e),
                )
                
                if attempt >= max_attempts:
                    if tracker and stage:
                        await tracker.update_stage(
                            stage=stage,
                            status="failed",
                            progress=0,
                            details=f"Failed {stage} stage after {attempt} attempts",
                        )
                    raise
                
                # Brief sleep before retry
                await asyncio.sleep(1)
                
                # Update progress to indicate retry
                if tracker and stage:
                    await tracker.update_stage(
                        stage=stage,
                        status="in_progress",
                        progress=min(20 + attempt * 20, 80),
                        details=f"Retrying {stage} stage (attempt {attempt + 1}/{max_attempts})",
                    )
    
    def _track_token_usage(
        self,
        model: Any,
        task_name: str,
        request_id: str,
        input_tokens: int,
        output_tokens: int,
    ):
        """
        Track token usage for the operation.
        
        Args:
            model: Model name or object
            task_name: Task name
            request_id: Request ID
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
        """
        try:
            from app.services.model_optimizer import track_token_usage
            
            # Convert model to string to handle AnthropicModel objects
            model_str = str(model)
            
            track_token_usage(
                model=model_str,
                task_name=task_name,
                request_id=request_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
            
            logfire.info(
                "Token usage tracked",
                model_str=model_str,
                task_name=task_name,
                request_id=request_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
        except (ImportError, Exception) as e:
            # Log but don't fail if token tracking has an error
            logfire.warning(
                "Error tracking token usage",
                error=str(e),
                error_type=type(e).__name__,
                model_type=type(model).__name__,
                task_name=task_name,
            )
            
    def _register_keyword_extraction_tool(self, agent, job_description):
        """
        Register the keyword extraction tool with a PydanticAI agent.
        
        Args:
            agent: The PydanticAI agent
            job_description: The job description text
            
        Returns:
            The registered function
        """
        @agent.tool
        def extract_keywords_for_job(
            context: RunContext[Any],
            job_description_text: str = job_description, 
            max_keywords: int = 20
        ) -> List[str]:
            """Extract important keywords from the job description."""
            import re
            from collections import Counter
            from nltk.corpus import stopwords
            
            try:
                words = re.findall(r"\b\w+\b", job_description_text.lower())
                stop_words = set(stopwords.words("english"))
                filtered_words = [
                    word for word in words if word not in stop_words and len(word) > 3
                ]
                word_counts = Counter(filtered_words)
                return [word for word, count in word_counts.most_common(max_keywords)]
            except Exception as e:
                logfire.error(f"Error extracting keywords: {str(e)}")
                return []
                
        return extract_keywords_for_job
        
    def _register_ats_simulation_tool(self, agent, resume_content, job_description, extract_keywords_fn):
        """
        Register the ATS simulation tool with a PydanticAI agent.
        
        Args:
            agent: The PydanticAI agent
            resume_content: The resume content text
            job_description: The job description text
            extract_keywords_fn: The keyword extraction function
            
        Returns:
            The registered function
        """
        @agent.tool
        def simulate_ats_scan(
            context: RunContext[Any],
            resume_text: str = resume_content, 
            job_description_text: str = job_description
        ) -> Dict[str, Any]:
            """Simulate how an ATS system would process this resume."""
            # We have to call extract_keywords_fn with the context parameter
            # that PydanticAI provides
            keywords = extract_keywords_fn(context, job_description_text)
            resume_lower = resume_text.lower()
            matches = [keyword for keyword in keywords if keyword in resume_lower]
            
            score = int(len(matches) / len(keywords) * 100) if keywords else 0
            return {
                "score": score,
                "matches": matches,
                "missing": [k for k in keywords if k not in matches],
                "passes": score >= 70,
            }
            
        return simulate_ats_scan
    
    async def customize_resume(
        self, 
        resume_id: str, 
        job_id: str, 
        customization_strength: Any = None,
        industry: str = None,
        iterations: int = 1,
        ats_analysis: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Customize a resume for a specific job description.
        
        This implements the complete four-stage workflow for resume customization.
        
        Args:
            resume_id: ID of the resume to customize
            job_id: ID of the job description to customize for
            customization_strength: Strength of customization (1-3)
            industry: Optional industry for specific guidance
            iterations: Number of improvement iterations
            ats_analysis: Optional existing ATS analysis results
            
        Returns:
            Dictionary with customized_content and metadata
        """
        # Initialize timing metrics
        start_time = time.time()
        stage_times = {}
        
        # Generate a unique customization ID
        customization_id = f"{resume_id}_{job_id}_{int(start_time)}"
        
        # Create a progress tracker
        tracker = ProgressTracker(customization_id, self.websocket_manager)
        await tracker.start()
        
        try:
            # Log the start of the customization process with detailed parameters
            logfire.info(
                "Starting PydanticAI resume customization workflow",
                resume_id=resume_id,
                job_id=job_id,
                customization_id=customization_id,
                customization_strength=str(customization_strength),
                industry=industry,
                iterations=iterations,
                has_ats_analysis=ats_analysis is not None,
            )
            
            # Fetch resume and job description data
            resume_data: Optional[ResumeVersion] = None
            job_data: Optional[JobDescription] = None
            
            try:
                # Get the latest version of the resume
                resume_data = (
                    self.db.query(ResumeVersion)
                    .filter(ResumeVersion.resume_id == resume_id)
                    .order_by(ResumeVersion.version_number.desc())
                    .first()
                )
                
                # Get the job description
                job_data = (
                    self.db.query(JobDescription)
                    .filter(JobDescription.id == job_id)
                    .first()
                )
                
                logfire.info(
                    "Retrieved resume and job data",
                    has_resume_data=resume_data is not None,
                    resume_version=resume_data.version_number if resume_data else None,
                    has_job_data=job_data is not None,
                    resume_length=len(resume_data.content) if resume_data else 0,
                    job_length=len(job_data.description) if job_data else 0,
                )
                
                if not resume_data or not job_data:
                    error_msg = "Resume or job data not found"
                    logfire.error(
                        error_msg,
                        resume_id=resume_id,
                        job_id=job_id,
                    )
                    await tracker.complete(success=False)
                    raise ValueError(error_msg)
                    
            except Exception as e:
                logfire.error(
                    "Error retrieving resume or job data",
                    error_type=type(e).__name__,
                    error_message=str(e),
                    resume_id=resume_id,
                    job_id=job_id,
                    traceback=traceback.format_exception(type(e), e, e.__traceback__),
                )
                await tracker.complete(success=False)
                raise
            
            # Get resume content and job description
            resume_content = resume_data.content
            job_description = job_data.description
            
            # Initialize the Evidence Tracker for truthfulness verification
            evidence_tracker = EvidenceTracker(resume_content)
            
            # Import prompts dynamically to avoid circular imports
            from app.services.prompts import (
                EVALUATOR_PROMPT,
                OPTIMIZER_PROMPT,
                IMPLEMENTATION_PROMPT,
                get_customization_level_instructions,
                get_industry_specific_guidance,
            )
            
            # Get customization level instructions
            from app.schemas.customize import CustomizationLevel
            customization_level = CustomizationLevel.BALANCED
            if customization_strength == 1:
                customization_level = CustomizationLevel.CONSERVATIVE
            elif customization_strength == 3:
                customization_level = CustomizationLevel.EXTENSIVE
                
            customization_instructions = get_customization_level_instructions(customization_level)
            
            # Get industry-specific guidance if industry is provided
            industry_guidance = ""
            if industry:
                industry_guidance = get_industry_specific_guidance(industry)
                if industry_guidance:
                    customization_instructions += f"\n\nINDUSTRY-SPECIFIC GUIDANCE ({industry.upper()}):\n{industry_guidance}"
            
            # Stage 1: Evaluation
            # Analyze the resume against the job description
            stage_start = time.time()
            logfire.info(
                "Starting Stage 1: Evaluation", 
                resume_id=resume_id, 
                job_id=job_id,
                customization_id=customization_id
            )
            
            try:
                # Prepare the prompt for the evaluation stage
                evaluator_prompt = EVALUATOR_PROMPT.replace(
                    "{{CUSTOMIZATION_LEVEL_INSTRUCTIONS}}", customization_instructions
                )
                
                # Create the evaluator agent
                evaluator_agent = self._create_agent(
                    output_type=ResumeAnalysis,
                    system_prompt=evaluator_prompt,
                )
                
                # Prepare the user message
                user_message = f"""
                Here's the resume content to evaluate:

                {resume_content}

                Here's the job description to match against:

                {job_description}
                """
                
                # Register tools for the evaluator agent
                extract_keywords_fn = self._register_keyword_extraction_tool(evaluator_agent, job_description)
                self._register_ats_simulation_tool(evaluator_agent, resume_content, job_description, extract_keywords_fn)
                
                # Run the evaluator agent with progress tracking
                evaluation_result = await self._run_agent_with_retry(
                    agent=evaluator_agent,
                    message=user_message,
                    customization_id=customization_id,
                    tracker=tracker,
                    stage="evaluation",
                    stage_progress=10,
                    stage_details="Analyzing resume against job description",
                )
                
                # Log success
                # Handle different result types from PydanticAI
                try:
                    # Try accessing match_score if it exists in the result
                    match_score = getattr(evaluation_result, "match_score", None)
                    if match_score is None and hasattr(evaluation_result, "dict"):
                        # Try to get it from dict() method if available
                        result_dict = evaluation_result.dict()
                        match_score = result_dict.get("match_score", 0)
                    
                    logfire.info(
                        "Evaluation stage completed", 
                        status="success",
                        match_score=match_score,
                        result_type=type(evaluation_result).__name__,
                        customization_id=customization_id,
                    )
                except Exception as access_error:
                    # Log but continue if we can't access the match_score
                    logfire.warning(
                        "Could not access match_score from evaluation result",
                        error=str(access_error),
                        error_type=type(access_error).__name__,
                        result_type=type(evaluation_result).__name__,
                        customization_id=customization_id,
                    )
                
                # Record the time taken for this stage
                stage_times["evaluation"] = time.time() - stage_start
            except Exception as e:
                logfire.error(
                    "Error during evaluation stage",
                    error_type=type(e).__name__,
                    error_message=str(e),
                    resume_id=resume_id,
                    job_id=job_id,
                    customization_id=customization_id,
                    traceback=traceback.format_exception(type(e), e, e.__traceback__),
                )
                await tracker.complete(success=False)
                raise
            
            # Stage 2: Planning
            # Create a customization plan
            stage_start = time.time()
            logfire.info(
                "Starting Stage 2: Planning", 
                resume_id=resume_id, 
                job_id=job_id,
                customization_id=customization_id
            )
            
            try:
                # Prepare the prompt for the planning stage
                optimizer_prompt = OPTIMIZER_PROMPT.replace(
                    "{{CUSTOMIZATION_LEVEL_INSTRUCTIONS}}", customization_instructions
                )
                
                # Create the optimizer agent
                optimizer_agent = self._create_agent(
                    output_type=PydanticAICustomizationPlan,
                    system_prompt=optimizer_prompt,
                )
                
                # Prepare the user message
                # Handle different result types, considering the output property
                try:
                    # First check if we have an AgentRunResult with an output property
                    if hasattr(evaluation_result, 'output'):
                        output = evaluation_result.output
                        # Try to get JSON from the output
                        if hasattr(output, 'json') and callable(output.json):
                            evaluation_json = output.json()
                        elif hasattr(output, 'model_dump_json') and callable(output.model_dump_json):
                            evaluation_json = output.model_dump_json()
                        elif hasattr(output, 'dict') and callable(output.dict):
                            import json
                            evaluation_json = json.dumps(output.dict())
                        else:
                            import json
                            evaluation_json = json.dumps({"result": str(output)})
                    # Fallback to direct access if no output property
                    elif hasattr(evaluation_result, 'json') and callable(evaluation_result.json):
                        evaluation_json = evaluation_result.json()
                    elif hasattr(evaluation_result, 'model_dump_json') and callable(evaluation_result.model_dump_json):
                        # Newer Pydantic versions use model_dump_json instead of json
                        evaluation_json = evaluation_result.model_dump_json()
                    elif hasattr(evaluation_result, 'dict') and callable(evaluation_result.dict):
                        # Fall back to dict and convert to JSON
                        import json
                        evaluation_json = json.dumps(evaluation_result.dict())
                    else:
                        # Last resort - just convert the string representation
                        import json
                        evaluation_json = json.dumps({"result": str(evaluation_result)})
                        
                    logfire.info(
                        "Successfully converted evaluation result to JSON",
                        result_type=type(evaluation_result).__name__,
                        json_length=len(evaluation_json),
                        customization_id=customization_id,
                    )
                except Exception as e:
                    # If all conversion attempts fail, provide a simplified structure
                    logfire.warning(
                        "Failed to convert evaluation result to JSON",
                        error=str(e),
                        error_type=type(e).__name__,
                        result_type=type(evaluation_result).__name__,
                        customization_id=customization_id,
                    )
                    import json
                    evaluation_json = json.dumps({
                        "match_score": 65, 
                        "strengths": ["Based on available information"],
                        "weaknesses": ["Some missing keywords"],
                        "summary": "Evaluation completed with technical issues"
                    })
                
                # Create the user message
                user_message = f"""
                Here's the resume content to optimize:

                {resume_content}

                Here's the job description to optimize for:

                {job_description}

                Here's the evaluation of how well the resume matches the job:

                {evaluation_json}
                """
                
                # Add tools to the agent using the helper methods
                extract_keywords_fn = self._register_keyword_extraction_tool(optimizer_agent, job_description)
                self._register_ats_simulation_tool(optimizer_agent, resume_content, job_description, extract_keywords_fn)
                
                # Run the optimizer agent with progress tracking
                customization_plan = await self._run_agent_with_retry(
                    agent=optimizer_agent,
                    message=user_message,
                    customization_id=customization_id,
                    tracker=tracker,
                    stage="planning",
                    stage_progress=10,
                    stage_details="Creating customization plan",
                )
                
                # Log success
                # Handle different result types from PydanticAI
                try:
                    # Try to access properties safely
                    target_score = getattr(customization_plan, "target_score", None)
                    if target_score is None and hasattr(customization_plan, "dict"):
                        result_dict = customization_plan.dict()
                        target_score = result_dict.get("target_score", 0)
                        
                    # Get recommendations count safely
                    recommendations_count = 0
                    if hasattr(customization_plan, "change_explanations"):
                        recommendations_count = len(customization_plan.change_explanations)
                    elif hasattr(customization_plan, "recommendations"):
                        recommendations_count = len(customization_plan.recommendations)
                    elif hasattr(customization_plan, "dict"):
                        result_dict = customization_plan.dict()
                        recommendations_count = len(result_dict.get("recommendations", []))
                    
                    logfire.info(
                        "Planning stage completed", 
                        status="success",
                        target_score=target_score,
                        recommendations_count=recommendations_count,
                        result_type=type(customization_plan).__name__,
                        customization_id=customization_id,
                    )
                except Exception as access_error:
                    # Log but continue if we can't access properties
                    logfire.warning(
                        "Could not access plan properties from result",
                        error=str(access_error),
                        error_type=type(access_error).__name__,
                        result_type=type(customization_plan).__name__, 
                        customization_id=customization_id,
                    )
                
                # Record the time taken for this stage
                stage_times["planning"] = time.time() - stage_start
            except Exception as e:
                logfire.error(
                    "Error during planning stage",
                    error_type=type(e).__name__,
                    error_message=str(e),
                    resume_id=resume_id,
                    job_id=job_id,
                    customization_id=customization_id,
                    traceback=traceback.format_exception(type(e), e, e.__traceback__),
                )
                await tracker.complete(success=False)
                raise
            
            # Stage 3: Implementation
            # Apply the plan to the resume
            stage_start = time.time()
            logfire.info(
                "Starting Stage 3: Implementation", 
                resume_id=resume_id, 
                job_id=job_id,
                customization_id=customization_id
            )
            
            try:
                # Prepare the prompt for the implementation stage
                implementation_prompt = IMPLEMENTATION_PROMPT.replace(
                    "{{CUSTOMIZATION_LEVEL_INSTRUCTIONS}}", customization_instructions
                )
                
                # Create the implementation agent (using text output format for the final resume)
                implementation_agent = Agent(
                    self.DEFAULT_MODEL,
                    output_format="text",  # Use text format for direct output
                    system_prompt=implementation_prompt,
                    # Disabled thinking config to avoid excessive API calls
                    thinking_config=None,
                    temperature=self.TEMPERATURE,
                    max_tokens=self.MAX_TOKENS,
                )
                
                # Get plan in JSON format safely
                plan_json = ""
                try:
                    if hasattr(customization_plan, 'output'):
                        output = customization_plan.output
                        if hasattr(output, 'json') and callable(output.json):
                            plan_json = output.json()
                        elif hasattr(output, 'model_dump_json') and callable(output.model_dump_json):
                            plan_json = output.model_dump_json()
                        elif hasattr(output, 'dict') and callable(output.dict):
                            import json
                            plan_json = json.dumps(output.dict())
                    elif hasattr(customization_plan, 'json') and callable(customization_plan.json):
                        plan_json = customization_plan.json()
                    elif hasattr(customization_plan, 'model_dump_json') and callable(customization_plan.model_dump_json):
                        plan_json = customization_plan.model_dump_json()
                    elif hasattr(customization_plan, 'dict') and callable(customization_plan.dict):
                        import json
                        plan_json = json.dumps(customization_plan.dict())
                    else:
                        import json
                        plan_json = json.dumps({"summary": "Plan summary unavailable"})
                except Exception as e:
                    logfire.warning(
                        "Error converting customization plan to JSON",
                        error=str(e),
                        error_type=type(e).__name__,
                        plan_type=type(customization_plan).__name__,
                        customization_id=customization_id
                    )
                    import json
                    plan_json = json.dumps({"summary": "Error converting plan to JSON"})
                
                # Prepare the user message
                user_message = f"""
                Here's the resume to customize:

                {resume_content}

                Here's the job description:

                {job_description}

                Here's the optimization plan:

                {plan_json}
                
                Please apply this plan to create a customized resume.
                """
                
                # Register tools for the implementation agent
                extract_keywords_fn = self._register_keyword_extraction_tool(implementation_agent, job_description)
                self._register_ats_simulation_tool(implementation_agent, resume_content, job_description, extract_keywords_fn)
                
                # Run the implementation agent with progress tracking
                customized_resume = await self._run_agent_with_retry(
                    agent=implementation_agent,
                    message=user_message,
                    customization_id=customization_id,
                    tracker=tracker,
                    stage="implementation",
                    stage_progress=10,
                    stage_details="Applying customization plan to resume",
                )
                
                # Get the actual text content from the result safely
                resume_text = ""
                if hasattr(customized_resume, 'output'):
                    # If it's an AgentRunResult, get the output text
                    resume_text = customized_resume.output
                else:
                    # Assume it's a string
                    resume_text = str(customized_resume)
                
                # Check for truthfulness using the Evidence Tracker
                truthfulness_issues = evidence_tracker.verify(resume_text)
                if truthfulness_issues:
                    # Log truthfulness issues
                    logfire.warning(
                        "Truthfulness issues detected in customized resume",
                        issues_count=len(truthfulness_issues),
                        issues=truthfulness_issues[:5],  # Log up to 5 issues
                        customization_id=customization_id,
                    )
                
                # Log success
                logfire.info(
                    "Implementation stage completed", 
                    status="success",
                    customized_content_length=len(resume_text),
                    truthfulness_issues_count=len(truthfulness_issues) if truthfulness_issues else 0,
                    customization_id=customization_id,
                    result_type=type(customized_resume).__name__,
                )
                
                # Record the time taken for this stage
                stage_times["implementation"] = time.time() - stage_start
            except Exception as e:
                logfire.error(
                    "Error during implementation stage",
                    error_type=type(e).__name__,
                    error_message=str(e),
                    resume_id=resume_id,
                    job_id=job_id,
                    customization_id=customization_id,
                    traceback=traceback.format_exception(type(e), e, e.__traceback__),
                )
                await tracker.complete(success=False)
                raise
            
            # Stage 4: Verification
            # Verify the customized resume
            stage_start = time.time()
            logfire.info(
                "Starting Stage 4: Verification", 
                resume_id=resume_id, 
                job_id=job_id,
                customization_id=customization_id
            )
            
            try:
                # Create verification agent to analyze the final resume
                verification_agent = self._create_agent(
                    output_type=VerificationResult,
                    system_prompt="""
                    You are an expert ATS (Applicant Tracking System) verification specialist. Your task is to verify that a customized resume is truthful and effectively optimized for a job description.
                    
                    Analyze the original resume, job description, and customized resume to determine if:
                    1. The customized resume is truthful (no fabricated experience)
                    2. All original experience is preserved
                    3. The resume is effectively optimized for the job description
                    4. The overall ATS score has improved
                    
                    Provide your verification results in a structured format.
                    """
                )
                
                # Prepare the user message
                user_message = f"""
                Here's the original resume:

                {resume_content}

                Here's the job description:

                {job_description}

                Here's the customized resume:

                {customized_resume}
                
                Please verify the customized resume for truthfulness and effectiveness.
                """
                
                # Register tools for the verification agent
                extract_keywords_fn = self._register_keyword_extraction_tool(verification_agent, job_description)
                self._register_ats_simulation_tool(verification_agent, resume_content, job_description, extract_keywords_fn)
                
                # Run the verification agent with progress tracking
                verification_result = await self._run_agent_with_retry(
                    agent=verification_agent,
                    message=user_message,
                    customization_id=customization_id,
                    tracker=tracker,
                    stage="verification",
                    stage_progress=10,
                    stage_details="Verifying customized resume",
                )
                
                # Log success
                # Handle different result types from PydanticAI
                try:
                    # Try to access properties safely
                    is_truthful = getattr(verification_result, "is_truthful", True)
                    final_score = getattr(verification_result, "final_score", 0)
                    improvement = getattr(verification_result, "improvement", 0)
                    issues = getattr(verification_result, "issues", [])
                    
                    # Try to access via dict if direct access failed
                    if hasattr(verification_result, "dict"):
                        result_dict = verification_result.dict()
                        if is_truthful is None:
                            is_truthful = result_dict.get("is_truthful", True)
                        if final_score is None:
                            final_score = result_dict.get("final_score", 0)
                        if improvement is None:
                            improvement = result_dict.get("improvement", 0)
                        if issues is None:
                            issues = result_dict.get("issues", [])
                    
                    # Handle AgentRunResult
                    if isinstance(issues, str):
                        issues = []
                    
                    logfire.info(
                        "Verification stage completed", 
                        status="success",
                        is_truthful=is_truthful,
                        final_score=final_score,
                        improvement=improvement,
                        issues_count=len(issues) if isinstance(issues, list) else 0,
                        result_type=type(verification_result).__name__,
                        customization_id=customization_id,
                    )
                except Exception as access_error:
                    # Log but continue if we can't access properties
                    logfire.warning(
                        "Could not access verification properties from result",
                        error=str(access_error),
                        error_type=type(access_error).__name__,
                        result_type=type(verification_result).__name__, 
                        customization_id=customization_id,
                    )
                
                # Record the time taken for this stage
                stage_times["verification"] = time.time() - stage_start
            except Exception as e:
                logfire.error(
                    "Error during verification stage",
                    error_type=type(e).__name__,
                    error_message=str(e),
                    resume_id=resume_id,
                    job_id=job_id,
                    customization_id=customization_id,
                    traceback=traceback.format_exception(type(e), e, e.__traceback__),
                )
                await tracker.complete(success=False)
                raise
            
            # Calculate total time and log completion with timing metrics
            total_time = time.time() - start_time
            
            # Safely extract values for logging
            final_score_value = None
            improvement_value = None
            
            # Try to access via output property first
            if hasattr(verification_result, 'output'):
                output = verification_result.output
                if hasattr(output, 'final_score'):
                    final_score_value = output.final_score
                if hasattr(output, 'improvement'):
                    improvement_value = output.improvement
            # Fallback to direct access
            else:
                if hasattr(verification_result, 'final_score'):
                    final_score_value = verification_result.final_score
                if hasattr(verification_result, 'improvement'):
                    improvement_value = verification_result.improvement
            
            logfire.info(
                "PydanticAI resume customization completed successfully",
                resume_id=resume_id,
                job_id=job_id,
                customization_id=customization_id,
                total_time_seconds=total_time,
                stage_times=stage_times,
                final_score=final_score_value,
                improvement=improvement_value,
            )
            
            # Mark tracking as complete
            await tracker.complete(success=True)
            
            # Extract the actual text content from the result
            customized_content = ""
            if hasattr(customized_resume, 'output'):
                # If it's an AgentRunResult, get the output text
                customized_content = customized_resume.output
            else:
                # Assume it's a string
                customized_content = str(customized_resume)
            
            # Create a result from the final customized resume
            # Safely extract properties from verification result
            improvement_score = 0
            final_score = 0
            is_truthful = True
            issues = []
            
            try:
                # Try to access properties with safe fallbacks
                improvement_score = getattr(verification_result, "improvement", 0)
                final_score = getattr(verification_result, "final_score", 0)
                is_truthful = getattr(verification_result, "is_truthful", True)
                issues = getattr(verification_result, "issues", [])
                
                # Try dict access if attributes don't exist
                if hasattr(verification_result, "dict"):
                    result_dict = verification_result.dict()
                    if improvement_score is None:
                        improvement_score = result_dict.get("improvement", 0)
                    if final_score is None:
                        final_score = result_dict.get("final_score", 0)
                    if is_truthful is None:
                        is_truthful = result_dict.get("is_truthful", True)
                    if issues is None or not isinstance(issues, list):
                        issues = result_dict.get("issues", [])
            except Exception as e:
                # Log the error but continue with default values
                logfire.warning(
                    "Error extracting verification result properties for final result",
                    error=str(e),
                    error_type=type(e).__name__,
                    customization_id=customization_id,
                )
                
            # Return the result with safe values
            return {
                "customized_content": customized_content,
                "customized_resume_id": resume_id,
                "job_id": job_id,
                "improvement_score": improvement_score,
                "final_score": final_score,
                "is_truthful": is_truthful,
                "timing_metrics": stage_times,
                "issues": issues if isinstance(issues, list) else [],
                "customization_id": customization_id,
            }
            
        except Exception as e:
            # Log any unexpected errors in the overall process
            total_time = time.time() - start_time
            logfire.error(
                "Error in PydanticAI resume customization process",
                error_type=type(e).__name__,
                error_message=str(e),
                resume_id=resume_id,
                job_id=job_id,
                customization_id=customization_id,
                total_time_seconds=total_time,
                stage_times=stage_times,
                traceback=traceback.format_exception(type(e), e, e.__traceback__),
            )
            
            # Determine the current stage based on what was attempted
            current_stage = "unknown"
            if "stage_times" in locals():
                # Get the last stage that was started based on stage_times
                if "verification" in stage_times:
                    current_stage = "verification"
                elif "implementation" in stage_times:
                    current_stage = "implementation"
                elif "planning" in stage_times:
                    current_stage = "planning"
                elif "evaluation" in stage_times:
                    current_stage = "evaluation"
            
            # Mark tracking as failed with error information
            await tracker.update_stage(
                stage=current_stage,
                status="failed",
                progress=0,
                details=f"Customization failed: {str(e)[:100]}..." if len(str(e)) > 100 else f"Customization failed: {str(e)}",
            )
            await tracker.complete(success=False)
            
            # Re-raise the exception to be handled by the caller
            raise
    
    async def implement_resume_customization(
        self,
        resume_id: str,
        job_id: str,
        plan: CustomizationPlan
    ) -> Dict[str, Any]:
        """
        Implement a customization plan for a resume.
        
        This is used by the enhanced customization service to implement a plan
        that was generated separately.
        
        Args:
            resume_id: ID of the resume to customize
            job_id: ID of the job description
            plan: Customization plan to implement
            
        Returns:
            Dictionary with customized_content and metadata
        """
        # Initialize timing
        start_time = time.time()
        
        # Generate a unique customization ID
        customization_id = f"{resume_id}_{job_id}_{int(start_time)}"
        
        # Create a progress tracker
        tracker = ProgressTracker(customization_id, self.websocket_manager)
        await tracker.start()
        
        try:
            logfire.info(
                "Implementing customization plan with PydanticAI",
                resume_id=resume_id,
                job_id=job_id,
                customization_id=customization_id,
                plan_summary=plan.summary
            )
            
            # Fetch resume and job description data
            resume_data = (
                self.db.query(ResumeVersion)
                .filter(ResumeVersion.resume_id == resume_id)
                .order_by(ResumeVersion.version_number.desc())
                .first()
            )
            
            job_data = (
                self.db.query(JobDescription)
                .filter(JobDescription.id == job_id)
                .first()
            )
            
            if not resume_data or not job_data:
                error_msg = "Resume or job data not found"
                logfire.error(
                    error_msg,
                    resume_id=resume_id,
                    job_id=job_id,
                    customization_id=customization_id,
                )
                await tracker.complete(success=False)
                raise ValueError(error_msg)
            
            # Get resume content and job description
            resume_content = resume_data.content
            job_description = job_data.description
            
            # Initialize the Evidence Tracker for truthfulness verification
            evidence_tracker = EvidenceTracker(resume_content)
            
            # Import prompts dynamically to avoid circular imports
            from app.services.prompts import IMPLEMENTATION_PROMPT
            
            # Create the implementation agent (using text output format for the final resume)
            implementation_agent = Agent(
                self.DEFAULT_MODEL,
                output_format="text",  # Use text format for direct output
                system_prompt=IMPLEMENTATION_PROMPT.replace(
                    "{{CUSTOMIZATION_LEVEL_INSTRUCTIONS}}", 
                    "Use a balanced approach to customization."
                ),
                # Disabled thinking config to avoid excessive API calls
                thinking_config=None,
                temperature=self.TEMPERATURE,
                max_tokens=self.MAX_TOKENS,
            )
            
            # Update progress
            await tracker.update_stage(
                stage="implementation",
                status="in_progress",
                progress=10,
                details="Applying customization plan to resume",
            )
            
            # Get plan in JSON format safely
            plan_json = ""
            try:
                if hasattr(plan, 'json') and callable(plan.json):
                    plan_json = plan.json()
                elif hasattr(plan, 'model_dump_json') and callable(plan.model_dump_json):
                    plan_json = plan.model_dump_json()
                elif hasattr(plan, 'dict') and callable(plan.dict):
                    import json
                    plan_json = json.dumps(plan.dict())
                else:
                    import json
                    plan_json = json.dumps({
                        "summary": plan.summary if hasattr(plan, "summary") else "Plan summary unavailable"
                    })
            except Exception as e:
                logfire.warning(
                    "Error converting plan to JSON in implement_resume_customization",
                    error=str(e),
                    error_type=type(e).__name__,
                    plan_type=type(plan).__name__,
                    customization_id=customization_id
                )
                import json
                plan_json = json.dumps({"summary": "Error converting plan to JSON"})
                
            # Prepare the user message
            user_message = f"""
            Here's the resume to customize:

            {resume_content}

            Here's the job description:

            {job_description}

            Here's the optimization plan:

            {plan_json}
            
            Please apply this plan to create a customized resume.
            """
            
            # Register any necessary tools for the agent
            extract_keywords_fn = self._register_keyword_extraction_tool(implementation_agent, job_description)
            self._register_ats_simulation_tool(implementation_agent, resume_content, job_description, extract_keywords_fn)
            
            # Run the implementation agent
            logfire.info(
                "Running implementation agent",
                customization_id=customization_id,
                resume_length=len(resume_content),
                job_description_length=len(job_description),
            )
            
            try:
                # Use a longer timeout for complex resume customization
                from app.core.parallel_config import TASK_TIMEOUT_SECONDS
                # No need to use a timeout for the implementation agent
                # Let it run as long as needed for complex customizations
                customized_resume = await implementation_agent.run(user_message)
            except asyncio.TimeoutError:
                logfire.error(
                    "Timeout in implementation agent",
                    customization_id=customization_id,
                    model=implementation_agent.model,
                    timeout_seconds=TASK_TIMEOUT_SECONDS,
                )
                raise
            
            # Get the actual text content from the result safely
            resume_text = ""
            if hasattr(customized_resume, 'output'):
                # If it's an AgentRunResult, get the output text
                resume_text = customized_resume.output
            else:
                # Assume it's a string
                resume_text = str(customized_resume)
            
            # Check for truthfulness using the Evidence Tracker
            truthfulness_issues = evidence_tracker.verify(resume_text)
            if truthfulness_issues:
                # Log truthfulness issues
                logfire.warning(
                    "Truthfulness issues detected in customized resume",
                    issues_count=len(truthfulness_issues),
                    issues=truthfulness_issues[:5],  # Log up to 5 issues
                    customization_id=customization_id,
                    result_type=type(customized_resume).__name__,
                )
            
            # Update progress
            await tracker.update_stage(
                stage="implementation",
                status="completed",
                progress=100,
                details="Customization plan applied successfully",
            )
            
            # Create a verification agent to check the final result
            verification_agent = self._create_agent(
                output_type=VerificationResult,
                system_prompt="""
                You are an expert ATS (Applicant Tracking System) verification specialist. Your task is to verify that a customized resume is truthful and effectively optimized for a job description.
                
                Analyze the original resume, job description, and customized resume to determine if:
                1. The customized resume is truthful (no fabricated experience)
                2. All original experience is preserved
                3. The resume is effectively optimized for the job description
                4. The overall ATS score has improved
                
                Provide your verification results in a structured format.
                """
            )
            
            # Update progress
            await tracker.update_stage(
                stage="verification",
                status="in_progress",
                progress=10,
                details="Verifying customized resume",
            )
            
            # Prepare the verification message
            verification_message = f"""
            Here's the original resume:

            {resume_content}

            Here's the job description:

            {job_description}

            Here's the customized resume:

            {customized_resume}
            
            Please verify the customized resume for truthfulness and effectiveness.
            """
            
            # Register any necessary tools for the verification agent
            extract_keywords_fn = self._register_keyword_extraction_tool(verification_agent, job_description)
            self._register_ats_simulation_tool(verification_agent, resume_content, job_description, extract_keywords_fn)
            
            # Run the verification agent
            try:
                from app.core.parallel_config import TASK_TIMEOUT_SECONDS
                # No need to use a timeout for the verification agent
                # Let it run as long as needed for complex verifications
                verification_result = await verification_agent.run(verification_message)
            except asyncio.TimeoutError:
                logfire.error(
                    "Timeout in verification agent",
                    customization_id=customization_id,
                    model=verification_agent.model,
                    timeout_seconds=TASK_TIMEOUT_SECONDS,
                )
                raise
            
            # Update progress
            await tracker.update_stage(
                stage="verification",
                status="completed",
                progress=100,
                details="Verification completed successfully",
            )
            
            # Mark tracking as complete
            await tracker.complete(success=True)
            
            # Calculate elapsed time
            elapsed_time = time.time() - start_time
            
            # Log completion
            # Safely extract values for logging
            final_score_value = None
            improvement_value = None
            is_truthful_value = True
            
            # Try to access via output property first
            if hasattr(verification_result, 'output'):
                output = verification_result.output
                if hasattr(output, 'final_score'):
                    final_score_value = output.final_score
                if hasattr(output, 'improvement'):
                    improvement_value = output.improvement
                if hasattr(output, 'is_truthful'):
                    is_truthful_value = output.is_truthful
            # Fallback to direct access
            else:
                if hasattr(verification_result, 'final_score'):
                    final_score_value = verification_result.final_score
                if hasattr(verification_result, 'improvement'):
                    improvement_value = verification_result.improvement
                if hasattr(verification_result, 'is_truthful'):
                    is_truthful_value = verification_result.is_truthful

            logfire.info(
                "Customization plan implementation completed",
                resume_id=resume_id,
                job_id=job_id,
                customization_id=customization_id,
                duration_seconds=round(elapsed_time, 2),
                is_truthful=is_truthful_value,
                final_score=final_score_value,
                improvement=improvement_value,
            )
            
            # Safely extract properties from verification result
            improvement_score = 0
            final_score = 0
            is_truthful = True
            issues = []
            
            try:
                # Try to access properties with safe fallbacks
                improvement_score = getattr(verification_result, "improvement", 0)
                final_score = getattr(verification_result, "final_score", 0)
                is_truthful = getattr(verification_result, "is_truthful", True)
                issues = getattr(verification_result, "issues", [])
                
                # Try dict access if attributes don't exist
                if hasattr(verification_result, "dict"):
                    result_dict = verification_result.dict()
                    if improvement_score is None:
                        improvement_score = result_dict.get("improvement", 0)
                    if final_score is None:
                        final_score = result_dict.get("final_score", 0)
                    if is_truthful is None:
                        is_truthful = result_dict.get("is_truthful", True)
                    if issues is None or not isinstance(issues, list):
                        issues = result_dict.get("issues", [])
            except Exception as e:
                # Log the error but continue with default values
                logfire.warning(
                    "Error extracting verification result properties for implement_resume_customization",
                    error=str(e),
                    error_type=type(e).__name__,
                    customization_id=customization_id,
                )
            
            # Extract the actual text content if needed
            customized_content = ""
            if hasattr(customized_resume, 'output'):
                # If it's an AgentRunResult, get the output text
                customized_content = customized_resume.output
            else:
                # Assume it's a string
                customized_content = str(customized_resume)
            
            # Return the result with safe values
            return {
                "customized_content": customized_content,
                "customized_resume_id": resume_id,
                "job_id": job_id,
                "improvement_score": improvement_score,
                "final_score": final_score,
                "is_truthful": is_truthful,
                "duration_seconds": round(elapsed_time, 2),
                "issues": issues if isinstance(issues, list) else [],
                "customization_id": customization_id,
            }
            
        except Exception as e:
            # Log error
            logfire.error(
                "Error implementing customization plan",
                error_type=type(e).__name__,
                error_message=str(e),
                resume_id=resume_id,
                job_id=job_id,
                customization_id=customization_id,
                traceback=traceback.format_exception(type(e), e, e.__traceback__),
            )
            
            # Mark tracking as failed with error information
            await tracker.update_stage(
                stage="implementation", 
                status="failed",
                progress=0,
                details=f"Implementation failed: {str(e)[:100]}..." if len(str(e)) > 100 else f"Implementation failed: {str(e)}",
            )
            await tracker.complete(success=False)
            
            # Re-raise the exception
            raise