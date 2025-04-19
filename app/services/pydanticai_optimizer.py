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
import uuid
import json
import time
import asyncio
import logfire
from typing import Optional, Dict, Any, List, Tuple

# Import PydanticAI components - wrapped in try/except for graceful failure
# Since PydanticAI is a custom framework, we can use anthropic directly as fallback
try:
    # Try to import PydanticAI if available
    from pydanticai import Agent, tool
    PYDANTICAI_AVAILABLE = True
except ImportError:
    logfire.warning("PydanticAI not installed. Using Anthropic Claude directly instead.")
    PYDANTICAI_AVAILABLE = False
    
    # Import Anthropic SDK
    try:
        import anthropic
        from anthropic import Anthropic
        ANTHROPIC_AVAILABLE = True
    except ImportError:
        logfire.error("Neither PydanticAI nor Anthropic SDK installed. Please install with 'uv add anthropic'")
        ANTHROPIC_AVAILABLE = False
    
    # Create a placeholder Agent class that will use Anthropic directly
    class Agent:
        def __init__(self, model_name, output_type=None, system_prompt=None, thinking_config=None, 
                   temperature=0.7, max_tokens=4000):
            self.model_name = model_name
            self.system_prompt = system_prompt
            self.temperature = temperature
            self.max_tokens = max_tokens
            self.output_type = output_type
            self.thinking_config = thinking_config
            self.fallback_config = []
            
            # Try to get Anthropic client
            if ANTHROPIC_AVAILABLE:
                try:
                    self.client = Anthropic()
                except Exception as e:
                    logfire.error(f"Failed to initialize Anthropic client: {str(e)}")
                    self.client = None
            else:
                self.client = None
        
        async def run(self, prompt, deps=None):
            if not ANTHROPIC_AVAILABLE or not self.client:
                raise NotImplementedError("Anthropic SDK not installed or initialized")
            
            try:
                # Process model name to remove provider prefix if present
                model = self.model_name
                if ":" in model:
                    provider, model = model.split(":", 1)
                    if provider != "anthropic":
                        model = "claude-3-7-sonnet-20250211"  # Default fallback model
                
                # Configure Claude messages
                system_message = self.system_prompt or "You are a helpful AI assistant."
                messages = [
                    {"role": "user", "content": prompt}
                ]
                
                # Determine if thinking is enabled
                anthropic_params = {
                    "model": model,
                    "messages": messages,
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens,
                    "system": system_message
                }
                
                # Add thinking if applicable - but only if using PydanticAI 
                # which supports system_instructions (not the direct Anthropic API)
                # This section is commented out because it's causing errors with direct Anthropic API calls
                # if self.thinking_config and "claude-3-7" in model:
                #     anthropic_params["system_instructions"] = [
                #         {
                #             "type": "thinking",
                #             "thinking": {"enabled": True, "budget_tokens": self.thinking_config.get("budget_tokens", 15000)}
                #         }
                #     ]
                
                # Call Claude directly
                response = self.client.messages.create(**anthropic_params)
                
                # Process the response based on output_type
                result = response.content[0].text if response.content else ""
                
                # Convert to output_type if specified
                if self.output_type and hasattr(self.output_type, 'parse_raw'):
                    try:
                        # Try to parse as JSON if it's a Pydantic model
                        import json
                        import re
                        
                        # Extract JSON from the result if it's wrapped in code blocks
                        json_str = result
                        if "```json" in result:
                            json_str = result.split("```json")[1].split("```")[0].strip()
                        elif "```" in result:
                            code_blocks = re.findall(r'```(?:json)?(.*?)```', result, re.DOTALL)
                            if code_blocks:
                                # Try each code block until we find valid JSON
                                for block in code_blocks:
                                    try:
                                        json.loads(block.strip())
                                        json_str = block.strip()
                                        break
                                    except:
                                        continue
                        
                        # Handle potential JSON within markdown that isn't in code blocks
                        if '{' in json_str and '}' in json_str:
                            potential_json = json_str[json_str.find('{'):json_str.rfind('}')+1]
                            try:
                                json.loads(potential_json)
                                json_str = potential_json
                            except:
                                pass
                        
                        # Try to parse as JSON then as Pydantic model
                        data = json.loads(json_str)
                        return self.output_type.parse_obj(data)
                    except Exception as e:
                        logfire.error(f"Failed to parse response as {self.output_type.__name__}: {str(e)}")
                        
                        # Attempt to create a basic CustomizationPlan if that's what we're expecting
                        if self.output_type.__name__ == 'CustomizationPlan':
                            try:
                                from app.schemas.customize import CustomizationPlan, RecommendationItem
                                return CustomizationPlan(
                                    summary="Failed to parse JSON response, but created a basic plan.",
                                    job_analysis="The job requires skills and experience that could be better emphasized in your resume.",
                                    keywords_to_add=["skill", "experience", "qualification"],
                                    formatting_suggestions=["Use bullet points for achievements"],
                                    recommendations=[
                                        RecommendationItem(
                                            section="General",
                                            what="Improve content",
                                            why="Better job match",
                                            before_text=None,
                                            after_text=None,
                                            description="Enhance your resume to better match the job requirements."
                                        )
                                    ]
                                )
                            except Exception:
                                pass
                        
                        # Return the text directly if parsing fails
                        return result
                
                return result
                
            except Exception as e:
                logfire.error(f"Error calling Anthropic API: {str(e)}")
                
                # Try fallbacks if available
                for fallback_model in self.fallback_config:
                    try:
                        logfire.info(f"Trying fallback model: {fallback_model}")
                        original_model = self.model_name
                        self.model_name = fallback_model
                        result = await self.run(prompt, deps)
                        self.model_name = original_model
                        return result
                    except Exception as fallback_err:
                        logfire.error(f"Fallback to {fallback_model} failed: {str(fallback_err)}")
                
                # Re-raise the original error if all fallbacks fail
                raise e
        
        @staticmethod
        def tool(*args, **kwargs):
            def decorator(func):
                return func
            return decorator

# Import from project
from app.core.config import settings, get_pydanticai_model_config
from app.core.logging import log_function_call
from app.schemas.customize import (
    CustomizationLevel, 
    CustomizationPlan,
    RecommendationItem
)
from app.db.session import get_db
from sqlalchemy.orm import Session
from app.models.resume import Resume, ResumeVersion
from app.models.job import JobDescription

# Set up model provider configuration
MODEL_CONFIG = get_pydanticai_model_config()

# Define the output schema for the resume evaluation
class ResumeEvaluation:
    """Schema for resume evaluation results."""
    overall_assessment: str
    match_score: int
    job_key_requirements: List[str]
    strengths: List[str]
    gaps: List[str]
    term_mismatches: List[Dict[str, str]]
    section_evaluations: List[Dict[str, Any]]
    competitor_analysis: str
    reframing_opportunities: List[str]
    experience_preservation_check: str

class FeedbackEvaluation:
    """Schema for evaluation feedback on optimization."""
    requires_iteration: bool
    experience_preservation_issues: List[Dict[str, str]]
    keyword_alignment_feedback: List[Dict[str, str]]
    formatting_feedback: List[Dict[str, str]]
    authenticity_concerns: List[Dict[str, str]]
    missed_opportunities: List[Dict[str, str]]
    overall_feedback: str

# Log initialization
logfire.info(
    "PydanticAI optimizer initialized",
    providers=list(MODEL_CONFIG.keys()),
    primary_provider=settings.PYDANTICAI_PRIMARY_PROVIDER,
    evaluator_model=settings.PYDANTICAI_EVALUATOR_MODEL,
    optimizer_model=settings.PYDANTICAI_OPTIMIZER_MODEL
)

# Import prompts when needed to avoid circular imports
def _get_prompts():
    """Import prompts module dynamically to avoid circular imports"""
    from app.services.prompts import (
        get_customization_level_instructions,
        get_industry_specific_guidance,
        EVALUATOR_PROMPT,
        OPTIMIZER_PROMPT,
        EVALUATOR_FEEDBACK_PROMPT,
        OPTIMIZER_FEEDBACK_RESPONSE_PROMPT,
        IMPLEMENTATION_PROMPT,
        MAX_FEEDBACK_ITERATIONS
    )
    return {
        'get_customization_level_instructions': get_customization_level_instructions,
        'get_industry_specific_guidance': get_industry_specific_guidance,
        'EVALUATOR_PROMPT': EVALUATOR_PROMPT,
        'OPTIMIZER_PROMPT': OPTIMIZER_PROMPT,
        'EVALUATOR_FEEDBACK_PROMPT': EVALUATOR_FEEDBACK_PROMPT,
        'OPTIMIZER_FEEDBACK_RESPONSE_PROMPT': OPTIMIZER_FEEDBACK_RESPONSE_PROMPT,
        'IMPLEMENTATION_PROMPT': IMPLEMENTATION_PROMPT,
        'MAX_FEEDBACK_ITERATIONS': MAX_FEEDBACK_ITERATIONS
    }

# Utility function to create an evaluator agent
def create_evaluator_agent(
    customization_level: CustomizationLevel = CustomizationLevel.BALANCED,
    industry: Optional[str] = None,
    is_feedback_agent: bool = False
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
        prompt_template = prompts['EVALUATOR_FEEDBACK_PROMPT']
        output_type = FeedbackEvaluation
        
        # Add any industry-specific considerations if relevant
        if industry:
            industry_guidance = prompts['get_industry_specific_guidance'](industry)
            if industry_guidance:
                prompt_template += f"\n\nConsider this INDUSTRY-SPECIFIC GUIDANCE for {industry.upper()}:\n{industry_guidance}"
    else:
        # Standard evaluator agent
        # Get customization level specific instructions
        customization_instructions = prompts['get_customization_level_instructions'](customization_level)
        
        # Get industry-specific guidance if industry is provided
        if industry:
            industry_guidance = prompts['get_industry_specific_guidance'](industry)
            if industry_guidance:
                customization_instructions += f"\n\nINDUSTRY-SPECIFIC GUIDANCE ({industry.upper()}):\n{industry_guidance}"
        
        # Format the prompt with the customization level instructions
        prompt_template = prompts['EVALUATOR_PROMPT'].replace("{customization_level_instructions}", customization_instructions)
        output_type = ResumeEvaluation
    
    # Get the appropriate model config for thinking
    thinking_config = None
    if "claude-3-7" in settings.PYDANTICAI_EVALUATOR_MODEL:
        thinking_config = {
            "type": "enabled",
            "budget_tokens": settings.PYDANTICAI_THINKING_BUDGET
        }
    
    # Create the agent using PydanticAI
    try:
        evaluator_agent = Agent(
            settings.PYDANTICAI_EVALUATOR_MODEL,
            output_type=output_type,
            system_prompt=prompt_template,
            thinking_config=thinking_config,
            temperature=settings.PYDANTICAI_TEMPERATURE,
            max_tokens=settings.PYDANTICAI_MAX_TOKENS
        )
        
        # Add fallback configurations
        evaluator_agent.fallback_config = settings.PYDANTICAI_FALLBACK_MODELS
        
        logfire.info(
            "Resume Evaluator Agent created successfully",
            model=settings.PYDANTICAI_EVALUATOR_MODEL,
            is_feedback_agent=is_feedback_agent
        )
        
        return evaluator_agent
        
    except Exception as e:
        logfire.error(
            "Error creating Resume Evaluator Agent",
            error=str(e),
            error_type=type(e).__name__
        )
        raise e

# Utility function to create an optimizer agent
def create_optimizer_agent(
    customization_level: CustomizationLevel = CustomizationLevel.BALANCED,
    industry: Optional[str] = None,
    is_feedback_response: bool = False
) -> Agent:
    """
    Create a PydanticAI agent for generating resume optimization plans.
    
    Args:
        customization_level: Level of customization (affects optimization detail)
        industry: Optional industry name for industry-specific guidance
        is_feedback_response: Whether this agent is responding to evaluator feedback
        
    Returns:
        PydanticAI Agent configured for resume optimization
    """
    # Get prompts dynamically
    prompts = _get_prompts()
    
    # Select the appropriate base prompt based on whether this is a feedback response agent
    if is_feedback_response:
        prompt_template = prompts['OPTIMIZER_FEEDBACK_RESPONSE_PROMPT']
        
        # Add any industry-specific considerations if relevant
        if industry:
            industry_guidance = prompts['get_industry_specific_guidance'](industry)
            if industry_guidance:
                prompt_template += f"\n\nConsider this INDUSTRY-SPECIFIC GUIDANCE for {industry.upper()}:\n{industry_guidance}"
    else:
        # Standard optimizer agent
        # Get customization level specific instructions
        customization_instructions = prompts['get_customization_level_instructions'](customization_level)
        
        # Get industry-specific guidance if industry is provided
        if industry:
            industry_guidance = prompts['get_industry_specific_guidance'](industry)
            if industry_guidance:
                customization_instructions += f"\n\nINDUSTRY-SPECIFIC GUIDANCE ({industry.upper()}):\n{industry_guidance}"
        
        # Format the prompt with the customization level instructions
        prompt_template = prompts['OPTIMIZER_PROMPT'].replace("{customization_level_instructions}", customization_instructions)
    
    # Get the appropriate model config for thinking
    thinking_config = None
    if "claude-3-7" in settings.PYDANTICAI_OPTIMIZER_MODEL:
        thinking_config = {
            "type": "enabled",
            "budget_tokens": settings.PYDANTICAI_THINKING_BUDGET
        }
    
    # Create the agent using PydanticAI
    try:
        optimizer_agent = Agent(
            settings.PYDANTICAI_OPTIMIZER_MODEL,
            output_type=CustomizationPlan,
            system_prompt=prompt_template,
            thinking_config=thinking_config,
            temperature=settings.PYDANTICAI_TEMPERATURE,
            max_tokens=settings.PYDANTICAI_MAX_TOKENS
        )
        
        # Add fallback configurations
        optimizer_agent.fallback_config = settings.PYDANTICAI_FALLBACK_MODELS
        
        logfire.info(
            "Resume Optimizer Agent created successfully",
            model=settings.PYDANTICAI_OPTIMIZER_MODEL,
            is_feedback_response=is_feedback_response
        )
        
        return optimizer_agent
        
    except Exception as e:
        logfire.error(
            "Error creating Resume Optimizer Agent",
            error=str(e),
            error_type=type(e).__name__
        )
        raise e

# Utility function to create an implementation agent
def create_implementation_agent(
    customization_level: CustomizationLevel = CustomizationLevel.BALANCED,
    industry: Optional[str] = None
) -> Agent:
    """
    Create a PydanticAI agent for implementing resume optimizations.
    
    Args:
        customization_level: Level of customization (affects implementation detail)
        industry: Optional industry name for industry-specific guidance
        
    Returns:
        PydanticAI Agent configured for resume implementation
    """
    # Get prompts dynamically
    prompts = _get_prompts()
    
    # Get customization level specific instructions
    customization_instructions = prompts['get_customization_level_instructions'](customization_level)
    
    # Get industry-specific guidance if industry is provided
    if industry:
        industry_guidance = prompts['get_industry_specific_guidance'](industry)
        if industry_guidance:
            customization_instructions += f"\n\nINDUSTRY-SPECIFIC GUIDANCE ({industry.upper()}):\n{industry_guidance}"
    
    # Format the prompt with the customization level instructions
    prompt_template = prompts['IMPLEMENTATION_PROMPT'].replace("{customization_level_instructions}", customization_instructions)
    
    # Get the appropriate model - use a simpler model for implementation to reduce costs
    implementation_model = settings.PYDANTICAI_COVER_LETTER_MODEL
    
    # Create the agent using PydanticAI
    try:
        implementation_agent = Agent(
            implementation_model,
            output_type=None,  # Use None for plain text output
            system_prompt=prompt_template,
            temperature=settings.PYDANTICAI_TEMPERATURE,
            max_tokens=settings.PYDANTICAI_MAX_TOKENS
        )
        
        # Add fallback configurations
        implementation_agent.fallback_config = settings.PYDANTICAI_FALLBACK_MODELS
        
        logfire.info(
            "Resume Implementation Agent created successfully",
            model=implementation_model
        )
        
        return implementation_agent
        
    except Exception as e:
        logfire.error(
            "Error creating Resume Implementation Agent",
            error=str(e),
            error_type=type(e).__name__
        )
        raise e


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
        iterations: int = 1
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
        iterations = max(1, min(iterations, _get_prompts()['MAX_FEEDBACK_ITERATIONS']))
        
        # Gather the necessary data
        resume_content, job_description = await self._get_resume_and_job(
            resume_id, job_id
        )
        
        # Use provided analysis or perform basic analysis
        basic_analysis = ats_analysis
        if not basic_analysis:
            basic_analysis = await self._perform_basic_analysis(
                resume_id, job_id
            )
        
        # Evaluate the match (evaluator stage)
        start_time_evaluator = time.time()
        logfire.info(
            "Starting evaluator stage with PydanticAI",
            resume_id=resume_id,
            job_id=job_id,
            customization_level=customization_strength.name,
            industry=industry if industry else "not specified",
            using_extended_thinking="claude-3-7" in settings.PYDANTICAI_EVALUATOR_MODEL
        )
        evaluation = await self._evaluate_match(
            resume_content, 
            job_description, 
            basic_analysis,
            customization_strength,
            industry
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
            sections_evaluated=len(evaluation.get("section_evaluations", []))
        )
        
        # Generate the optimization plan (optimizer stage)
        start_time_optimizer = time.time()
        logfire.info(
            "Starting optimizer stage with PydanticAI",
            resume_id=resume_id,
            job_id=job_id,
            customization_level=customization_strength.name,
            industry=industry if industry else "not specified",
            using_extended_thinking="claude-3-7" in settings.PYDANTICAI_OPTIMIZER_MODEL
        )
        plan = await self._generate_optimization_plan(
            resume_content, 
            job_description, 
            evaluation,
            customization_strength,
            industry
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
            formatting_suggestions_count=len(plan.formatting_suggestions)
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
                max_iterations=iterations - 1  # We already did one iteration
            )
        
        # Store the plan for future reference
        await self._store_plan(
            resume_id,
            job_id,
            plan
        )
        
        return plan
    
    @log_function_call
    async def customize_resume(
        self, 
        resume_id: str, 
        job_id: str, 
        customization_strength: CustomizationLevel = CustomizationLevel.BALANCED,
        industry: Optional[str] = None,
        iterations: int = 2  # Default to 2 iterations for better results
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
            
        Returns:
            Dictionary with original and customized resume
        """
        # Gather the necessary data
        resume_content, job_description = await self._get_resume_and_job(
            resume_id, job_id
        )
        
        # Generate the customization plan with feedback iterations
        plan = await self.generate_customization_plan(
            resume_id=resume_id,
            job_id=job_id,
            customization_strength=customization_strength,
            industry=industry,
            iterations=iterations
        )
        
        # Implement the plan (apply changes to the resume)
        start_time_implementation = time.time()
        logfire.info(
            "Starting implementation stage with PydanticAI",
            resume_id=resume_id,
            job_id=job_id,
            customization_level=customization_strength.name,
            recommendation_count=len(plan.recommendations)
        )
        
        # Implement the optimization plan
        customized_resume = await self._implement_optimization_plan(
            resume_content=resume_content,
            job_description=job_description,
            plan=plan,
            customization_strength=customization_strength,
            industry=industry
        )
        
        # Log implementation results with metrics
        elapsed_time_implementation = time.time() - start_time_implementation
        logfire.info(
            "Implementation stage completed",
            resume_id=resume_id,
            job_id=job_id,
            duration_seconds=round(elapsed_time_implementation, 2),
            original_length=len(resume_content),
            customized_length=len(customized_resume)
        )
        
        # Save the customized resume as a new version
        new_resume_id = await self._save_customized_resume(
            resume_id=resume_id,
            job_id=job_id,
            customized_content=customized_resume
        )
        
        return {
            "original_resume_id": resume_id,
            "customized_resume_id": new_resume_id,
            "job_description_id": job_id,
            "original_content": resume_content,
            "customized_content": customized_resume
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
        # Get resume content
        resume_version = self.db.query(ResumeVersion).filter(
            ResumeVersion.resume_id == resume_id
        ).order_by(ResumeVersion.version_number.desc()).first()
        
        if not resume_version:
            logfire.error("Resume version not found", resume_id=resume_id)
            raise ValueError(f"Resume content not found for ID: {resume_id}")
        
        # Get job description
        job = self.db.query(JobDescription).filter(JobDescription.id == job_id).first()
        if not job:
            logfire.error("Job description not found", job_id=job_id)
            raise ValueError(f"Job description not found for ID: {job_id}")
        
        return resume_version.content, job.description
    
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
            "Performing basic ATS analysis",
            resume_id=resume_id,
            job_id=job_id
        )
        
        try:
            # Get resume content and job description
            resume_content, job_description = await self._get_resume_and_job(resume_id, job_id)
            
            # Import here to avoid circular imports
            from app.services.ats_service import analyze_resume_for_ats
            
            # Perform the analysis using the ATS service
            analysis_result = await analyze_resume_for_ats(
                resume_content=resume_content,
                job_description=job_description
            )
            
            # Add the IDs to the result
            analysis_result["resume_id"] = resume_id
            analysis_result["job_description_id"] = job_id
            
            logfire.info(
                "Basic ATS analysis completed successfully",
                resume_id=resume_id,
                job_id=job_id,
                match_score=analysis_result.get("match_score", 0)
            )
            
            return analysis_result
            
        except Exception as e:
            logfire.error(
                "Error performing basic ATS analysis",
                error=str(e),
                resume_id=resume_id,
                job_id=job_id
            )
            
            # Return a basic structure in case of error
            return {
                "resume_id": resume_id,
                "job_description_id": job_id,
                "match_score": 50,  # Default middle score
                "matching_keywords": [],
                "missing_keywords": [],
                "error": str(e)
            }
    
    async def _evaluate_match(
        self, 
        resume_content: str, 
        job_description: str, 
        basic_analysis: Dict, 
        customization_level: CustomizationLevel,
        industry: Optional[str] = None
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
            industry=industry if industry else "not specified"
        )
        
        # Create the evaluator agent
        evaluator_agent = create_evaluator_agent(
            customization_level=customization_level,
            industry=industry
        )
        
        # Build the input prompt
        prompt = f"""
        Resume:
        {resume_content}
        
        Job Description:
        {job_description}
        """
        
        if industry:
            prompt += f"\nIndustry: {industry}"
        
        if basic_analysis:
            # Convert complex objects to serializable format
            basic_analysis_copy = {}
            for key, value in basic_analysis.items():
                if isinstance(value, (str, int, float, bool, type(None))):
                    basic_analysis_copy[key] = value
                elif isinstance(value, list):
                    basic_analysis_copy[key] = []
                    for item in value:
                        if hasattr(item, '__dict__'):
                            basic_analysis_copy[key].append(item.__dict__)
                        else:
                            basic_analysis_copy[key].append(item)
                elif hasattr(value, '__dict__'):
                    basic_analysis_copy[key] = value.__dict__
            
            basic_analysis_str = json.dumps(basic_analysis_copy, indent=2)
            prompt += f"""
            
            Basic Analysis:
            {basic_analysis_str}
            """
        
        try:
            # Run the evaluator agent
            start_time = time.time()
            result = await evaluator_agent.run(prompt)
            elapsed_time = time.time() - start_time
            
            # Convert the result to dictionary
            if hasattr(result, 'dict'):
                evaluation_result = result.dict()
            else:
                # In case the agent returns a plain object, convert attributes to dict
                evaluation_result = {
                    attr: getattr(result, attr) 
                    for attr in dir(result) 
                    if not attr.startswith('_') and not callable(getattr(result, attr))
                }
            
            # Log success
            logfire.info(
                "Resume-job evaluation completed successfully with PydanticAI",
                duration_seconds=round(elapsed_time, 2),
                match_score=evaluation_result.get("match_score", 0)
            )
            
            return evaluation_result
            
        except Exception as e:
            logfire.error(
                "Error evaluating resume job match with PydanticAI",
                error=str(e),
                error_type=type(e).__name__
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
                "experience_preservation_check": "Could not verify experience preservation due to evaluation error."
            }
    
    async def _generate_optimization_plan(
        self, 
        resume_content: str, 
        job_description: str, 
        evaluation: Dict, 
        customization_level: CustomizationLevel,
        industry: Optional[str] = None
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
            industry=industry if industry else "not specified"
        )
        
        # Create the optimizer agent
        optimizer_agent = create_optimizer_agent(
            customization_level=customization_level,
            industry=industry
        )
        
        # Build the input prompt
        prompt = f"""
        Resume:
        {resume_content}
        
        Job Description:
        {job_description}
        
        Evaluation:
        - Overall Assessment: {evaluation.get('overall_assessment', '')}
        - Score: {evaluation.get('match_score', 0)}/100
        - Key Job Requirements: {', '.join(evaluation.get('job_key_requirements', []))}
        - Strengths: {', '.join(evaluation.get('strengths', []))}
        - Gaps: {', '.join(evaluation.get('gaps', []))}
        - Term Mismatches: {json.dumps(evaluation.get('term_mismatches', []), indent=2)}
        - Section Evaluations: {json.dumps(evaluation.get('section_evaluations', []), indent=2)}
        
        Customization Level: {customization_level.name.lower()}
        """
        
        if industry:
            prompt += f"\nIndustry: {industry}"
        
        try:
            # Run the optimizer agent
            start_time = time.time()
            result = await optimizer_agent.run(prompt)
            elapsed_time = time.time() - start_time
            
            # Log success
            logfire.info(
                "Optimization plan generation completed successfully with PydanticAI",
                duration_seconds=round(elapsed_time, 2),
                recommendation_count=len(result.recommendations)
            )
            
            return result
            
        except Exception as e:
            logfire.error(
                "Error generating optimization plan with PydanticAI",
                error=str(e),
                error_type=type(e).__name__
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
                    "Ensure consistent formatting"
                ],
                recommendations=[
                    RecommendationItem(
                        section="General",
                        what="Emphasize relevant keywords",
                        why="To improve ATS matching score",
                        before_text=None,
                        after_text=None,
                        description="Include more of the key terms from the job description in your resume."
                    )
                ]
            )
    
    async def _evaluate_optimization_plan(
        self, 
        original_resume: str,
        job_description: str,
        optimized_resume: str,
        customization_level: CustomizationLevel,
        industry: Optional[str] = None
    ) -> Dict:
        """
        Evaluate an optimization plan against the original resume and job description.
        This is the "feedback" step in the evaluator-optimizer iterative pattern.
        
        Args:
            original_resume: The original resume content in Markdown format
            job_description: The job description text
            optimized_resume: The optimized resume content to evaluate
            customization_level: Level of customization (affects evaluation detail)
            industry: Optional industry name for industry-specific guidance
            
        Returns:
            Dictionary containing evaluation feedback for the optimizer
        """
        # Start timer for performance tracking
        start_time = time.time()
        
        # Create a span in OpenTelemetry for tracing
        with logfire.span("evaluate_optimization_plan_operation") as span:
            span.set_attribute("original_resume_length", len(original_resume))
            span.set_attribute("job_description_length", len(job_description))
            span.set_attribute("optimized_resume_length", len(optimized_resume))
            span.set_attribute("customization_level", customization_level.value)
            span.set_attribute("industry", industry if industry else "not specified")
            
            # Log operation start
            logfire.info(
                "Starting optimization plan evaluation with PydanticAI",
                original_resume_length=len(original_resume),
                job_description_length=len(job_description),
                optimized_resume_length=len(optimized_resume),
                customization_level=customization_level.name,
                industry=industry if industry else "not specified"
            )
            
            # Create the evaluator agent specifically for feedback
            feedback_agent = create_evaluator_agent(
                customization_level=customization_level,
                industry=industry,
                is_feedback_agent=True
            )
            
            # Build the user message
            user_message = f"""
            Here's the ORIGINAL resume content:
            
            {original_resume}
            
            Here's the job description:
            
            {job_description}
            
            Here's the OPTIMIZED resume to evaluate:
            
            {optimized_resume}
            """
            
            try:
                # Run the agent
                result = await feedback_agent.run(user_message)
                
                # Calculate elapsed time
                elapsed_time = time.time() - start_time
                
                # Convert the result to dictionary
                if hasattr(result, 'dict'):
                    feedback_result = result.dict()
                else:
                    # In case the agent returns a plain object, convert attributes to dict
                    feedback_result = {
                        attr: getattr(result, attr) 
                        for attr in dir(result) 
                        if not attr.startswith('_') and not callable(getattr(result, attr))
                    }
                
                # Log success
                logfire.info(
                    "Optimization plan evaluation completed successfully with PydanticAI",
                    duration_seconds=round(elapsed_time, 2),
                    requires_iteration=feedback_result.get("requires_iteration", False)
                )
                
                return feedback_result
                
            except Exception as e:
                # Calculate elapsed time
                elapsed_time = time.time() - start_time
                
                # Log error
                logfire.error(
                    "Error evaluating optimization plan with PydanticAI",
                    error=str(e),
                    error_type=type(e).__name__,
                    duration_seconds=round(elapsed_time, 2)
                )
                
                # Return a basic structure as fallback with critical feedback about parsing failure
                return {
                    "requires_iteration": True,
                    "experience_preservation_issues": [],
                    "keyword_alignment_feedback": [],
                    "formatting_feedback": [],
                    "authenticity_concerns": [],
                    "missed_opportunities": [
                        {
                            "opportunity": "Unable to evaluate optimization properly",
                            "suggestion": "Please retry the optimization"
                        }
                    ],
                    "overall_feedback": f"Evaluation failed due to error: {str(e)}. Please ensure all output is in valid format."
                }
    
    async def _optimize_resume_with_feedback(
        self, 
        original_resume: str,
        job_description: str,
        evaluation: Dict,
        feedback: Dict,
        customization_level: CustomizationLevel,
        industry: Optional[str] = None
    ) -> CustomizationPlan:
        """
        Generate an improved optimization plan based on evaluator feedback.
        This continues the feedback loop in the evaluator-optimizer iterative pattern.
        
        Args:
            original_resume: The original resume content in Markdown format
            job_description: The job description text
            evaluation: The initial evaluation dictionary
            feedback: The feedback dictionary from the evaluator
            customization_level: Level of customization (affects optimization detail)
            industry: Optional industry name for industry-specific guidance
            
        Returns:
            Improved CustomizationPlan based on feedback
        """
        # Start timer for performance tracking
        start_time = time.time()
        
        # Create a span in OpenTelemetry for tracing
        with logfire.span("optimize_resume_with_feedback_operation") as span:
            span.set_attribute("resume_length", len(original_resume))
            span.set_attribute("job_description_length", len(job_description))
            span.set_attribute("customization_level", customization_level.value)
            span.set_attribute("industry", industry if industry else "not specified")
            
            # Log operation start
            logfire.info(
                "Starting resume optimization with feedback using PydanticAI",
                resume_length=len(original_resume),
                job_description_length=len(job_description),
                customization_level=customization_level.name,
                industry=industry if industry else "not specified"
            )
            
            # Create the optimizer agent specifically for feedback response
            optimizer_agent = create_optimizer_agent(
                customization_level=customization_level,
                industry=industry,
                is_feedback_response=True
            )
            
            # Build the user message
            user_message = f"""
            Here's the original resume content:
            
            {original_resume}
            
            Here's the job description to optimize for:
            
            {job_description}
            
            Here's the initial evaluation of how well the resume matches the job:
            
            {json.dumps(evaluation, indent=2)}
            
            Here's the feedback on your previous optimization plan:
            
            {json.dumps(feedback, indent=2)}
            
            Please create an improved optimization plan that addresses all feedback, especially ensuring that ALL original experience is preserved.
            """
            
            try:
                # Run the agent
                result = await optimizer_agent.run(user_message)
                
                # Calculate elapsed time
                elapsed_time = time.time() - start_time
                
                # Log success
                logfire.info(
                    "Resume optimization with feedback completed successfully using PydanticAI",
                    duration_seconds=round(elapsed_time, 2),
                    recommendation_count=len(result.recommendations)
                )
                
                return result
                
            except Exception as e:
                # Calculate elapsed time
                elapsed_time = time.time() - start_time
                
                # Log error
                logfire.error(
                    "Error generating optimization plan with feedback using PydanticAI",
                    error=str(e),
                    error_type=type(e).__name__,
                    duration_seconds=round(elapsed_time, 2)
                )
                
                # Create a fallback plan
                return CustomizationPlan(
                    summary="Failed to generate a complete optimization plan from feedback. Here is a basic updated plan.",
                    job_analysis="Please review the optimization suggestions carefully as they may not fully address all feedback.",
                    keywords_to_add=feedback.get("keyword_alignment_feedback", [])[:5],
                    formatting_suggestions=[
                        suggestion.get("suggestion", "Fix formatting issues") 
                        for suggestion in feedback.get("formatting_feedback", [])[:3]
                    ],
                    recommendations=[
                        RecommendationItem(
                            section="General",
                            what="Address feedback",
                            why="To improve optimization based on evaluator feedback",
                            before_text=None,
                            after_text=None,
                            description="Unable to fully parse the optimization improvements. Please review the feedback manually."
                        )
                    ]
                )
    
    async def _implement_optimization_plan(
        self, 
        resume_content: str, 
        job_description: str,
        plan: CustomizationPlan,
        customization_strength: CustomizationLevel,
        industry: Optional[str] = None
    ) -> str:
        """
        Implement an optimization plan by applying its recommendations to the resume.
        
        Args:
            resume_content: Original resume content
            job_description: The job description
            plan: Customization plan with recommendations
            customization_strength: Level of customization
            industry: Optional industry name for industry-specific guidance
            
        Returns:
            Optimized resume content with recommendations applied
        """
        logfire.info(
            "Implementing optimization plan with PydanticAI",
            resume_length=len(resume_content),
            recommendation_count=len(plan.recommendations),
            customization_level=customization_strength.name,
            industry=industry if industry else "not specified"
        )
        
        # Create the implementation agent
        implementation_agent = create_implementation_agent(
            customization_level=customization_strength,
            industry=industry
        )
        
        # Define the prompt for implementing the changes
        prompt = f"""
        I need to implement the following optimization plan to improve my resume for a specific job.
        
        # Original Resume
        
        {resume_content}
        
        # Job Description
        
        {job_description}
        
        # Optimization Plan Summary
        
        {plan.summary}
        
        # Job Analysis
        
        {plan.job_analysis}
        
        # Keywords to Add
        
        {', '.join(plan.keywords_to_add)}
        
        # Formatting Suggestions
        
        {', '.join(plan.formatting_suggestions)}
        
        # Recommendations to Apply
        
        """
        
        # Add each recommendation
        for i, rec in enumerate(plan.recommendations):
            prompt += f"""
            ## Recommendation {i+1}
            
            - Section: {rec.section}
            - What: {rec.what}
            - Why: {rec.why}
            """
            
            if rec.before_text:
                prompt += f"""
            - Before Text: 
            ```
            {rec.before_text}
            ```
                """
            
            if rec.after_text:
                prompt += f"""
            - After Text: 
            ```
            {rec.after_text}
            ```
                """
            
            prompt += f"""
            - Description: {rec.description}
            
            """
        
        try:
            # Run the implementation agent
            start_time = time.time()
            result = await implementation_agent.run(prompt)
            elapsed_time = time.time() - start_time
            
            # Get the optimized content from the result
            optimized_content = result
            
            logfire.info(
                "Optimization plan implementation completed successfully with PydanticAI",
                original_length=len(resume_content),
                optimized_length=len(optimized_content),
                duration_seconds=round(elapsed_time, 2)
            )
            
            return optimized_content
            
        except Exception as e:
            logfire.error(
                "Error implementing optimization plan with PydanticAI",
                error=str(e),
                error_type=type(e).__name__
            )
            # In case of error, return the original content to avoid breaking the workflow
            return resume_content
    
    async def _perform_feedback_iterations(
        self, 
        original_resume: str,
        job_description: str,
        evaluation: Dict,
        initial_plan: CustomizationPlan,
        customization_strength: CustomizationLevel,
        industry: Optional[str] = None,
        max_iterations: int = 1
    ) -> CustomizationPlan:
        """
        Perform multiple iterations of the feedback loop to progressively improve the plan.
        
        Args:
            original_resume: The original resume content
            job_description: The job description
            evaluation: The initial evaluation
            initial_plan: The initial optimization plan
            customization_strength: Level of customization
            industry: Optional industry name for industry-specific guidance
            max_iterations: Maximum number of iterations to perform
            
        Returns:
            The final improved CustomizationPlan
        """
        logfire.info(
            "Starting feedback iterations with PydanticAI",
            original_resume_length=len(original_resume),
            job_description_length=len(job_description),
            max_iterations=max_iterations
        )
        
        current_plan = initial_plan
        
        for i in range(max_iterations):
            # Implement the current plan to test it
            optimized_resume = await self._implement_optimization_plan(
                resume_content=original_resume,
                job_description=job_description,
                plan=current_plan,
                customization_strength=customization_strength,
                industry=industry
            )
            
            # Evaluate the implementation
            feedback = await self._evaluate_optimization_plan(
                original_resume=original_resume,
                job_description=job_description,
                optimized_resume=optimized_resume,
                customization_level=customization_strength,
                industry=industry
            )
            
            # Check if further iteration is needed
            if not feedback.get("requires_iteration", False):
                logfire.info(
                    "Feedback iteration complete - no further iterations needed",
                    iteration=i+1,
                    total_iterations=max_iterations
                )
                break
            
            # Generate improved plan based on feedback
            improved_plan = await self._optimize_resume_with_feedback(
                original_resume=original_resume,
                job_description=job_description,
                evaluation=evaluation,
                feedback=feedback,
                customization_level=customization_strength,
                industry=industry
            )
            
            # Update the current plan
            current_plan = improved_plan
            
            logfire.info(
                "Completed feedback iteration",
                iteration=i+1,
                total_iterations=max_iterations,
                recommendation_count=len(current_plan.recommendations)
            )
        
        return current_plan
    
    async def _store_plan(self, resume_id: str, job_id: str, plan: CustomizationPlan) -> None:
        """
        Store the customization plan for future reference.
        
        Args:
            resume_id: Resume ID
            job_id: Job description ID
            plan: The generated customization plan
        """
        try:
            # Import the database model
            from app.models.customization import CustomizationPlan as CustomizationPlanModel
            
            # Get the resume to find the user_id
            resume = self.db.query(Resume).filter(Resume.id == resume_id).first()
            user_id = resume.user_id if resume else None
            
            # Convert recommendations to a list of dicts for JSON storage
            recommendations_json = []
            for rec in plan.recommendations:
                recommendations_json.append({
                    "section": rec.section,
                    "what": rec.what,
                    "why": rec.why,
                    "before_text": rec.before_text,
                    "after_text": rec.after_text,
                    "description": rec.description
                })
            
            # Create a new plan record
            db_plan = CustomizationPlanModel(
                id=str(uuid.uuid4()),
                resume_id=resume_id,
                job_description_id=job_id,
                user_id=user_id,
                customization_strength=2,  # Default to balanced
                summary=plan.summary or "No summary provided",
                job_analysis=plan.job_analysis or "No job analysis provided",
                keywords_to_add=plan.keywords_to_add or [],
                formatting_suggestions=plan.formatting_suggestions or [],
                recommendations=recommendations_json or []
            )
            
            # Add and commit to database
            self.db.add(db_plan)
            self.db.commit()
            
            logfire.info(
                "Customization plan stored successfully",
                resume_id=resume_id,
                job_id=job_id,
                plan_id=db_plan.id,
                recommendation_count=len(plan.recommendations)
            )
            
            return db_plan.id
            
        except Exception as e:
            logfire.error(
                "Error storing customization plan",
                error=str(e),
                resume_id=resume_id,
                job_id=job_id
            )
            # Don't raise the exception since this is non-critical
            # We want the overall workflow to succeed even if storage fails
    
    async def _save_customized_resume(
        self, 
        resume_id: str, 
        job_id: str, 
        customized_content: str
    ) -> str:
        """
        Save a customized resume as a new version in the database.
        
        Args:
            resume_id: Original resume ID
            job_id: Job description ID used for customization
            customized_content: The customized resume content
            
        Returns:
            The new resume version ID
        """
        # Get the original resume to copy metadata
        resume = self.db.query(Resume).filter(Resume.id == resume_id).first()
        if not resume:
            raise ValueError(f"Original resume not found: {resume_id}")
        
        # Get the latest version number
        latest_version = self.db.query(ResumeVersion).filter(
            ResumeVersion.resume_id == resume_id
        ).order_by(ResumeVersion.version_number.desc()).first()
        
        version_number = 1
        if latest_version:
            version_number = latest_version.version_number + 1
        
        # Create a new customized resume
        customized_resume = Resume(
            id=str(uuid.uuid4()),
            user_id=resume.user_id,
            title=f"{resume.title} - Customized for Job {job_id}"
        )
        
        # Create the first version of the customized resume
        customized_version = ResumeVersion(
            id=str(uuid.uuid4()),
            resume_id=customized_resume.id,
            version_number=1,
            content=customized_content,
            is_customized=1,  # Mark as customized
            job_description_id=job_id  # Link to the job description
        )
        
        # Add and commit to database
        self.db.add(customized_resume)
        self.db.add(customized_version)
        self.db.commit()
        
        logfire.info(
            "Customized resume saved successfully",
            original_resume_id=resume_id,
            customized_resume_id=customized_resume.id,
            job_id=job_id
        )
        
        return customized_resume.id


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