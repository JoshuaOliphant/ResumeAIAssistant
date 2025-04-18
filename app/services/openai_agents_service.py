"""
OpenAI Agents Service Module for AI-driven resume customization features.
This module implements the evaluator-optimizer pattern using the OpenAI Agents SDK.
"""
import os
import time
import json
import asyncio
from typing import Optional, Dict, Any, List, Tuple
import logfire
from pydantic import BaseModel, Field

# Import from Agents SDK - wrapped in try/except to handle missing dependencies gracefully
try:
    from agents import Agent, Runner
except ImportError:
    logfire.error("Agents SDK not installed. Please install with 'pip install openai-agents'")
    # Create dummy classes to prevent import errors
    class Agent:
        def __init__(self, *args, **kwargs):
            pass
    class Runner:
        @staticmethod
        async def run(*args, **kwargs):
            raise NotImplementedError("Agents SDK not installed")

from app.core.config import settings
from app.core.logging import log_function_call
from app.schemas.customize import CustomizationLevel, CustomizationPlan, RecommendationItem

# Check for OpenAI API key
if not settings.OPENAI_API_KEY:
    logfire.error("OPENAI_API_KEY not set", impact="Authentication will fail")
    raise ValueError('OPENAI_API_KEY environment variable must be set')

# Set environment variable for Agents SDK to use
os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY

# Log initialization
logfire.info(
    "OpenAI Agents SDK initialized",
    model=settings.OPENAI_MODEL,
    evaluator_model=settings.OPENAI_EVALUATOR_MODEL,
    optimizer_model=settings.OPENAI_OPTIMIZER_MODEL
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
        EVALUATOR_FEEDBACK_PROMPT,
        OPTIMIZER_FEEDBACK_RESPONSE_PROMPT,
        MAX_FEEDBACK_ITERATIONS
    )
    return {
        'get_customization_level_instructions': get_customization_level_instructions,
        'get_industry_specific_guidance': get_industry_specific_guidance,
        'EVALUATOR_PROMPT': EVALUATOR_PROMPT,
        'OPTIMIZER_PROMPT': OPTIMIZER_PROMPT,
        'EVALUATOR_FEEDBACK_PROMPT': EVALUATOR_FEEDBACK_PROMPT,
        'OPTIMIZER_FEEDBACK_RESPONSE_PROMPT': OPTIMIZER_FEEDBACK_RESPONSE_PROMPT,
        'MAX_FEEDBACK_ITERATIONS': MAX_FEEDBACK_ITERATIONS
    }

# Define agent creation functions
def create_resume_evaluator_agent(customization_level: CustomizationLevel = CustomizationLevel.BALANCED, 
                                 industry: Optional[str] = None, 
                                 is_feedback_agent: bool = False) -> Agent:
    """
    Create an agent for evaluating resume-job match.
    
    Args:
        customization_level: Level of customization
        industry: Optional industry name for industry-specific guidance
        is_feedback_agent: Whether this agent is for providing feedback on optimization
        
    Returns:
        OpenAI Agent configured for resume evaluation
    """
    # Get prompts dynamically
    prompts = _get_prompts()
    
    # Select the appropriate base prompt based on whether this is a feedback agent
    if is_feedback_agent:
        prompt_template = prompts['EVALUATOR_FEEDBACK_PROMPT']
        
        # No need for customization instructions for feedback agent - it uses a simpler format
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
        industry_guidance = ""
        if industry:
            industry_guidance = prompts['get_industry_specific_guidance'](industry)
            if industry_guidance:
                customization_instructions += f"\n\nINDUSTRY-SPECIFIC GUIDANCE ({industry.upper()}):\n{industry_guidance}"
        
        # Format the prompt with the customization level instructions
        prompt_template = prompts['EVALUATOR_PROMPT'].replace("{customization_level_instructions}", customization_instructions)
        
        # Add instructions to return JSON format for standard evaluator
        json_instruction = """
        Your output must be in JSON format with these fields:
        {
            "overall_assessment": "Detailed evaluation of how well the resume matches the job",
            "match_score": 85, // A score from 0-100 representing how well the resume matches the job
            "job_key_requirements": ["list", "of", "most", "important", "job", "requirements"],
            "strengths": ["list", "of", "candidate", "strengths", "relative", "to", "job"],
            "gaps": ["list", "of", "missing", "skills", "or", "experiences"],
            "term_mismatches": [
                {
                    "job_term": "required term from job description",
                    "resume_term": "equivalent term used in resume",
                    "context": "brief explanation of the equivalence"
                }
            ],
            "section_evaluations": [
                {
                    "section": "section name (e.g., Summary, Experience, Skills)",
                    "assessment": "detailed evaluation of how well this section matches job requirements",
                    "improvement_potential": "high/medium/low",
                    "key_issues": ["specific", "issues", "to", "address"],
                    "priority": "high/medium/low"
                }
            ],
            "competitor_analysis": "Brief assessment of how this resume might compare to other candidates based on job market trends",
            "reframing_opportunities": ["list", "of", "experience", "that", "could", "be", "reframed", "using", "job", "description", "terminology"],
            "experience_preservation_check": "Confirmation that ALL original experience is preserved in the optimized resume, or specific details of any missing items"
        }
        """
        prompt_template = f"{prompt_template}\n\n{json_instruction}"
    
    # Create the agent using the Agents SDK
    try:
        evaluator_agent = Agent(
            name="ResumeEvaluator",
            instructions=prompt_template,
            model=settings.OPENAI_EVALUATOR_MODEL
        )
        
        logfire.info(
            "Resume Evaluator Agent created successfully",
            model=settings.OPENAI_EVALUATOR_MODEL
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
                                 industry: Optional[str] = None,
                                 is_feedback_response: bool = False) -> Agent:
    """
    Create an agent for generating resume optimization plans.
    
    Args:
        customization_level: Level of customization
        industry: Optional industry name for industry-specific guidance
        is_feedback_response: Whether this agent is responding to evaluator feedback
        
    Returns:
        OpenAI Agent configured for resume optimization
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
        industry_guidance = ""
        if industry:
            industry_guidance = prompts['get_industry_specific_guidance'](industry)
            if industry_guidance:
                customization_instructions += f"\n\nINDUSTRY-SPECIFIC GUIDANCE ({industry.upper()}):\n{industry_guidance}"
        
        # Format the prompt with the customization level instructions
        prompt_template = prompts['OPTIMIZER_PROMPT'].replace("{customization_level_instructions}", customization_instructions)
        
        # Add instructions to return JSON format
        json_instruction = """
        Your output must be in JSON format with these fields:
        {
            "summary": "Brief overall assessment of the resume's current alignment with the job",
            "job_analysis": "Brief analysis of the job description's key requirements and priorities",
            "keywords_to_add": ["list", "of", "important", "keywords", "to", "incorporate", "based", "on", "existing", "experience"],
            "formatting_suggestions": ["suggestions", "for", "better", "ATS", "friendly", "formatting"],
            "authenticity_statement": "Statement confirming that all recommendations maintain complete truthfulness while optimizing presentation",
            "experience_preservation_statement": "Confirmation that ALL experience from the original resume is preserved in the recommendations",
            "recommendations": [
                {
                    "section": "Section name",
                    "what": "Specific change to make",
                    "why": "Why this change improves ATS performance",
                    "before_text": "Original text to be replaced",
                    "after_text": "Suggested new text",
                    "description": "Detailed explanation of this change",
                    "priority": "high/medium/low",
                    "authenticity_check": "Explanation of how this change maintains truthfulness while optimizing presentation",
                    "preservation_check": "Confirmation that this change preserves all original experience content"
                }
            ]
        }
        """
        
        prompt_template = f"{prompt_template}\n\n{json_instruction}"
    
    # Create the agent using the Agents SDK
    try:
        optimizer_agent = Agent(
            name="ResumeOptimizer",
            instructions=prompt_template,
            model=settings.OPENAI_OPTIMIZER_MODEL
        )
        
        logfire.info(
            "Resume Optimizer Agent created successfully",
            model=settings.OPENAI_OPTIMIZER_MODEL
        )
        
        return optimizer_agent
        
    except Exception as e:
        logfire.error(
            "Error creating Resume Optimizer Agent",
            error=str(e),
            error_type=type(e).__name__
        )
        raise e

def create_cover_letter_agent() -> Agent:
    """
    Create an agent for generating cover letters.
    
    Returns:
        OpenAI Agent configured for cover letter generation
    """
    # Create system prompt for cover letter generation
    system_prompt = """
    You are a professional resume writer helping a job seeker create a compelling cover letter for a specific job posting.
    
    Your task is to write a personalized cover letter that highlights the applicant's qualifications for the position.
    
    Guidelines:
    - Use the provided resume to extract relevant experience, skills, and achievements
    - Match the applicant's qualifications to the job requirements
    - Keep the letter concise and focused (about 300-400 words)
    - Use a professional and enthusiastic tone throughout the letter
    - Structure the letter with a clear introduction, body, and conclusion
    - Include specific examples from the resume that demonstrate the applicant's fit for the role
    - Mention the company name naturally in the letter
    - Format the letter in professional Markdown with appropriate spacing
    
    Return ONLY the cover letter in Markdown format with proper formatting.
    """
    
    # Create the agent using the Agents SDK
    try:
        cover_letter_agent = Agent(
            name="CoverLetterAgent",
            instructions=system_prompt,
            model=settings.OPENAI_MODEL
        )
        
        logfire.info(
            "Cover Letter Agent created successfully",
            model=settings.OPENAI_MODEL
        )
        
        return cover_letter_agent
        
    except Exception as e:
        logfire.error(
            "Error creating Cover Letter Agent",
            error=str(e),
            error_type=type(e).__name__
        )
        raise e

# Helper function to run an agent and wait for completion
async def _run_agent(agent: Agent, message: str) -> str:
    """
    Run an agent with a given message and wait for completion.
    
    Args:
        agent: The Agents SDK Agent to run
        message: The message content to send to the agent
    
    Returns:
        Response text from the agent
    """
    start_time = time.time()
    
    try:
        # Run the agent with the message
        try:
            result = await Runner.run(
                starting_agent=agent,
                input=message
            )
            
            # Log success
            elapsed_time = time.time() - start_time
            logfire.info(
                "Agent run completed successfully",
                agent_name=getattr(agent, 'name', 'unknown'),
                response_length=len(result.final_output) if hasattr(result, 'final_output') and result.final_output else 0,
                duration_seconds=round(elapsed_time, 2)
            )
            
            # Return the final output
            return result.final_output if hasattr(result, 'final_output') else ""
            
        except (AttributeError, NotImplementedError) as e:
            # Handle the case where Agents SDK is not available - fallback to a basic response
            logfire.warning(
                "Agents SDK not available, using fallback response",
                error=str(e)
            )
            # Return a basic response
            return "Unable to process request - Agents SDK not available"
        
    except Exception as e:
        # Calculate elapsed time
        elapsed_time = time.time() - start_time
        
        # Log error
        logfire.error(
            "Error running agent",
            error=str(e),
            error_type=type(e).__name__,
            agent_name=getattr(agent, 'name', 'unknown'),
            duration_seconds=round(elapsed_time, 2)
        )
        
        # Re-raise the exception
        raise e

# Helper for the async functions defined below

@log_function_call
async def evaluate_optimization_plan(
    original_resume: str,
    job_description: str,
    optimized_resume: str,
    customization_level: CustomizationLevel = CustomizationLevel.BALANCED,
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
            "Starting optimization plan evaluation",
            original_resume_length=len(original_resume),
            job_description_length=len(job_description),
            optimized_resume_length=len(optimized_resume),
            customization_level=customization_level.name,
            industry=industry if industry else "not specified"
        )
        
        # Create the evaluator agent specifically for feedback
        evaluator_agent = create_resume_evaluator_agent(
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
            response_text = await _run_agent(
                agent=evaluator_agent,
                message=user_message
            )
            
            # Calculate elapsed time
            elapsed_time = time.time() - start_time
            
            try:
                # Extract JSON from the response text
                # Sometimes the model wraps JSON in markdown code blocks
                if "```json" in response_text:
                    json_str = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    json_str = response_text.split("```")[1].split("```")[0].strip()
                else:
                    json_str = response_text.strip()
                
                feedback_result = json.loads(json_str)
                
                # Log success
                logfire.info(
                    "Optimization plan evaluation completed successfully",
                    response_length=len(response_text),
                    duration_seconds=round(elapsed_time, 2),
                    requires_iteration=feedback_result.get("requires_iteration", False)
                )
                
                return feedback_result
                
            except json.JSONDecodeError as json_err:
                # Log parsing error but continue with a fallback
                logfire.warning(
                    "Failed to parse feedback evaluation as JSON",
                    error=str(json_err),
                    response_text=response_text[:500] + ("..." if len(response_text) > 500 else "")
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
                            "opportunity": "Unable to parse feedback properly",
                            "suggestion": "Please retry the optimization with clearer JSON formatting"
                        }
                    ],
                    "overall_feedback": "Failed to parse structured feedback, please ensure all output is in valid JSON format.",
                    "parsing_error": True
                }
                
        except Exception as e:
            # Calculate elapsed time
            elapsed_time = time.time() - start_time
            
            # Log error
            logfire.error(
                "Error evaluating optimization plan",
                error=str(e),
                error_type=type(e).__name__,
                duration_seconds=round(elapsed_time, 2)
            )
            
            # Re-raise the exception
            raise e

@log_function_call
async def optimize_resume_with_feedback(
    original_resume: str,
    job_description: str,
    evaluation: Dict,
    feedback: Dict,
    customization_level: CustomizationLevel = CustomizationLevel.BALANCED,
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
            "Starting resume optimization with feedback",
            resume_length=len(original_resume),
            job_description_length=len(job_description),
            customization_level=customization_level.name,
            industry=industry if industry else "not specified"
        )
        
        # Create the optimizer agent specifically for feedback response
        optimizer_agent = create_resume_optimizer_agent(
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
            response_text = await _run_agent(
                agent=optimizer_agent,
                message=user_message
            )
            
            # Calculate elapsed time
            elapsed_time = time.time() - start_time
            
            try:
                # Extract JSON from the response text
                # Sometimes the model wraps JSON in markdown code blocks
                if "```json" in response_text:
                    json_str = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    json_str = response_text.split("```")[1].split("```")[0].strip()
                else:
                    json_str = response_text.strip()
                
                optimization_result = json.loads(json_str)
                
                # Convert to Pydantic model for validation and consistency
                plan = CustomizationPlan(
                    summary=optimization_result.get("summary", "Plan summary not provided"),
                    job_analysis=optimization_result.get("job_analysis", "Job analysis not provided"),
                    keywords_to_add=optimization_result.get("keywords_to_add", []),
                    formatting_suggestions=optimization_result.get("formatting_suggestions", []),
                    recommendations=[
                        RecommendationItem(
                            section=rec.get("section", "Unknown"),
                            what=rec.get("what", ""),
                            why=rec.get("why", ""),
                            before_text=rec.get("before_text"),
                            after_text=rec.get("after_text"),
                            description=rec.get("description", "") + (
                                f"\n\nAuthenticity check: {rec.get('authenticity_check', 'Verified')}" 
                                if rec.get('authenticity_check') else ""
                            ) + (
                                f"\n\nPreservation check: {rec.get('preservation_check', 'Verified')}" 
                                if rec.get('preservation_check') else ""
                            )
                        )
                        for rec in optimization_result.get("recommendations", [])
                    ]
                )
                
                # Add authenticity statement if available
                if optimization_result.get("authenticity_statement"):
                    plan.summary = f"{plan.summary}\n\n**Authenticity Statement**: {optimization_result.get('authenticity_statement')}"
                
                # Add experience preservation statement if available
                if optimization_result.get("experience_preservation_statement"):
                    plan.summary = f"{plan.summary}\n\n**Experience Preservation**: {optimization_result.get('experience_preservation_statement')}"
                
                # Add feedback addressed statement if available
                if optimization_result.get("feedback_addressed"):
                    plan.summary = f"{plan.summary}\n\n**Feedback Addressed**: {optimization_result.get('feedback_addressed')}"
                
                # Log success
                logfire.info(
                    "Resume optimization with feedback completed successfully",
                    response_length=len(response_text),
                    duration_seconds=round(elapsed_time, 2),
                    recommendation_count=len(plan.recommendations)
                )
                
                return plan
                
            except (json.JSONDecodeError, ValueError) as err:
                # Log parsing error but continue with a fallback
                logfire.warning(
                    "Failed to parse optimization with feedback response as a valid CustomizationPlan",
                    error=str(err),
                    response_text=response_text[:500] + ("..." if len(response_text) > 500 else "")
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
                
        except Exception as e:
            # Calculate elapsed time
            elapsed_time = time.time() - start_time
            
            # Log error
            logfire.error(
                "Error generating optimization plan with feedback",
                error=str(e),
                error_type=type(e).__name__,
                duration_seconds=round(elapsed_time, 2)
            )
            
            # Re-raise the exception
            raise e

@log_function_call
async def evaluate_resume_job_match(
    resume_content: str,
    job_description: str,
    basic_analysis: Optional[Dict] = None,
    customization_level: CustomizationLevel = CustomizationLevel.BALANCED,
    industry: Optional[str] = None
) -> Dict:
    """
    Evaluate how well a resume matches a job description using OpenAI's advanced reasoning.
    This is the "evaluator" stage of the evaluator-optimizer pattern.
    
    Args:
        resume_content: The content of the resume in Markdown format
        job_description: The job description text
        basic_analysis: Optional basic keyword analysis results to enhance evaluation
        customization_level: Level of customization (affects evaluation detail)
        industry: Optional industry name for industry-specific guidance
        
    Returns:
        Dictionary containing OpenAI's evaluation of the resume-job match
    """
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
            # Convert to dict for JSON serialization
            basic_analysis_dict = {}
            
            # Copy regular fields
            for key, value in basic_analysis.items():
                if key in ["resume_id", "job_description_id", "match_score", "job_type", "confidence", "keyword_density"]:
                    basic_analysis_dict[key] = value
                    
            # Handle complex objects
            if "matching_keywords" in basic_analysis:
                basic_analysis_dict["matching_keywords"] = [
                    {"keyword": k.keyword, "count_in_resume": k.count_in_resume, "count_in_job": k.count_in_job, "is_match": k.is_match}
                    for k in basic_analysis.get("matching_keywords", [])
                ]
                
            if "missing_keywords" in basic_analysis:
                basic_analysis_dict["missing_keywords"] = [
                    {"keyword": k.keyword, "count_in_resume": k.count_in_resume, "count_in_job": k.count_in_job, "is_match": k.is_match}
                    for k in basic_analysis.get("missing_keywords", [])
                ]
                
            if "improvements" in basic_analysis:
                basic_analysis_dict["improvements"] = [
                    {"category": imp.category, "suggestion": imp.suggestion, "priority": imp.priority}
                    for imp in basic_analysis.get("improvements", [])
                ]
                
            if "section_scores" in basic_analysis:
                basic_analysis_dict["section_scores"] = basic_analysis.get("section_scores", [])
            
            # Serialize to string
            basic_analysis_str = json.dumps(basic_analysis_dict, indent=2)
            user_message += f"""
            
            Here are the results of a basic keyword analysis:
            
            {basic_analysis_str}
            """
            
        # If industry is specified, mention it in the user message
        if industry:
            user_message += f"""
            
            The target industry for this job is: {industry}
            """
        
        try:
            # Run the agent
            response_text = await _run_agent(
                agent=evaluator_agent,
                message=user_message
            )
            
            # Calculate elapsed time
            elapsed_time = time.time() - start_time
            
            try:
                # Extract JSON from the response text
                # Sometimes the model wraps JSON in markdown code blocks
                if "```json" in response_text:
                    json_str = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    json_str = response_text.split("```")[1].split("```")[0].strip()
                else:
                    json_str = response_text.strip()
                
                evaluation_result = json.loads(json_str)
                
                # Log success
                logfire.info(
                    "Resume-job evaluation completed successfully",
                    response_length=len(response_text),
                    duration_seconds=round(elapsed_time, 2)
                )
                
                return evaluation_result
                
            except json.JSONDecodeError as json_err:
                # Log parsing error but continue with a fallback
                logfire.warning(
                    "Failed to parse OpenAI's evaluation as JSON",
                    error=str(json_err),
                    response_text=response_text[:500] + ("..." if len(response_text) > 500 else "")
                )
                
                # Return a basic structure as fallback
                return {
                    "overall_assessment": "Failed to parse structured evaluation. The resume appears to match some elements of the job description, but could be improved.",
                    "match_score": 50,  # Default middle score
                    "job_key_requirements": [],
                    "strengths": [],
                    "gaps": [],
                    "term_mismatches": [],
                    "section_evaluations": [],
                    "parsing_error": True,
                    "raw_response": response_text[:1000] + ("..." if len(response_text) > 1000 else "")
                }
                
        except Exception as e:
            # Calculate elapsed time
            elapsed_time = time.time() - start_time
            
            # Log error
            logfire.error(
                "Error calling OpenAI API for resume-job evaluation",
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
    This is the "optimizer" stage of the evaluator-optimizer pattern.
    
    Args:
        resume_content: The content of the resume in Markdown format
        job_description: The job description text
        evaluation: The evaluation dictionary from the evaluator stage
        customization_level: Level of customization (affects optimization detail)
        industry: Optional industry name for industry-specific guidance
        
    Returns:
        CustomizationPlan object with detailed recommendations
    """
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
            response_text = await _run_agent(
                agent=optimizer_agent,
                message=user_message
            )
            
            # Calculate elapsed time
            elapsed_time = time.time() - start_time
            
            try:
                # Extract JSON from the response text
                # Sometimes the model wraps JSON in markdown code blocks
                if "```json" in response_text:
                    json_str = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    json_str = response_text.split("```")[1].split("```")[0].strip()
                else:
                    json_str = response_text.strip()
                
                optimization_result = json.loads(json_str)
                
                # Convert to Pydantic model for validation
                plan = CustomizationPlan(
                    summary=optimization_result.get("summary", "Plan summary not provided"),
                    job_analysis=optimization_result.get("job_analysis", "Job analysis not provided"),
                    keywords_to_add=optimization_result.get("keywords_to_add", []),
                    formatting_suggestions=optimization_result.get("formatting_suggestions", []),
                    recommendations=[
                        RecommendationItem(
                            section=rec.get("section", "Unknown"),
                            what=rec.get("what", ""),
                            why=rec.get("why", ""),
                            before_text=rec.get("before_text"),
                            after_text=rec.get("after_text"),
                            description=rec.get("description", "") + (
                                f"\n\nAuthenticity check: {rec.get('authenticity_check', 'Verified')}" 
                                if rec.get('authenticity_check') else ""
                            )
                        )
                        for rec in optimization_result.get("recommendations", [])
                    ]
                )
                
                # Add authenticity statement if available
                if optimization_result.get("authenticity_statement"):
                    plan.summary = f"{plan.summary}\n\n**Authenticity Statement**: {optimization_result.get('authenticity_statement')}"
                
                # Log success
                logfire.info(
                    "Optimization plan generation completed successfully",
                    response_length=len(response_text),
                    duration_seconds=round(elapsed_time, 2),
                    recommendation_count=len(plan.recommendations)
                )
                
                return plan
                
            except (json.JSONDecodeError, ValueError) as err:
                # Log parsing error but continue with a fallback
                logfire.warning(
                    "Failed to parse OpenAI's optimization plan as a valid CustomizationPlan",
                    error=str(err),
                    response_text=response_text[:500] + ("..." if len(response_text) > 500 else "")
                )
                
                # Create a fallback plan
                keywords = []
                if isinstance(evaluation.get("gaps"), list):
                    keywords = evaluation.get("gaps", [])[:10]
                
                # Return a basic fallback plan
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
                
        except Exception as e:
            # Calculate elapsed time
            elapsed_time = time.time() - start_time
            
            # Log error
            logfire.error(
                "Error calling OpenAI API for optimization plan generation",
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
    Customize a resume for a specific job description using OpenAI Agents.
    
    Args:
        resume_content: The content of the resume in Markdown format
        job_description: The job description text
        customization_strength: The strength of customization (1-3)
        focus_areas: Optional comma-separated list of areas to focus on
    
    Returns:
        Customized resume content in Markdown format
    """
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
        
        # Create a custom agent for resume customization
        try:
            customization_agent = Agent(
                name="ResumeCustomizationAgent",
                instructions=system_prompt,
                model=settings.OPENAI_MODEL
            )
            
            # Build the user message
            user_message = f"""
            Here is my current resume in Markdown format:
            
            {resume_content}
            
            Here is the job description I'm applying for:
            
            {job_description}
            
            Please customize my resume for this specific job.
            """
            
            # Run the agent
            response_text = await _run_agent(
                agent=customization_agent,
                message=user_message
            )
            
            # Calculate elapsed time
            elapsed_time = time.time() - start_time
            
            # Log success
            logfire.info(
                "Resume customization completed successfully",
                response_length=len(response_text),
                duration_seconds=round(elapsed_time, 2)
            )
            
            # Return the generated content
            return response_text
            
        except Exception as e:
            # Calculate elapsed time
            elapsed_time = time.time() - start_time
            
            # Log error
            logfire.error(
                "Error calling OpenAI API for resume customization",
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
    Generate a cover letter based on a resume and job description using OpenAI Agents.
    
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
        
        # Log operation start
        logfire.info(
            "Starting cover letter generation",
            resume_length=len(resume_content),
            job_description_length=len(job_description),
            company_name=company_name,
            tone=tone
        )
        
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
        
        # Build the full system prompt
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
        
        Return ONLY the cover letter in Markdown format with proper formatting.
        """
        
        # Create or get the cover letter agent
        cover_letter_agent = create_cover_letter_agent()
        
        # Build the user message
        user_message = f"""
        Here is my resume in Markdown format:
        
        {resume_content}
        
        Here is the job description I'm applying for at {company_name}:
        
        {job_description}
        
        Please write a cover letter for this position that highlights my relevant qualifications.
        """
        
        try:
            # Run the agent
            response_text = await _run_agent(
                agent=cover_letter_agent,
                message=user_message
            )
            
            # Calculate elapsed time
            elapsed_time = time.time() - start_time
            
            # Log success
            logfire.info(
                "Cover letter generation completed successfully",
                response_length=len(response_text),
                duration_seconds=round(elapsed_time, 2)
            )
            
            # Return the generated content
            return response_text
            
        except Exception as e:
            # Calculate elapsed time
            elapsed_time = time.time() - start_time
            
            # Log error
            logfire.error(
                "Error calling OpenAI API for cover letter generation",
                error=str(e),
                error_type=type(e).__name__,
                duration_seconds=round(elapsed_time, 2)
            )
            
            # Re-raise the exception
            raise e