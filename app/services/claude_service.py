import os
import sys
import time
import json
from typing import Optional, Dict, Any, List, Union
import anthropic
from anthropic import Anthropic
import logfire

from app.core.config import settings
from app.core.logging import log_function_call, setup_anthropic_instrumentation
from app.schemas.customize import CustomizationLevel, CustomizationPlan, RecommendationItem

# Initialize the Anthropic client
if not settings.ANTHROPIC_API_KEY:
    logfire.error("ANTHROPIC_API_KEY not set", impact="Authentication will fail")
    raise ValueError('ANTHROPIC_API_KEY environment variable must be set')

# Create the Anthropic client
client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

# Setup instrumentation for this specific client
setup_anthropic_instrumentation(client)

logfire.info(
    "Anthropic client initialized and instrumented",
    model=settings.CLAUDE_MODEL
)

@log_function_call
async def customize_resume(
    resume_content: str,
    job_description: str,
    customization_strength: int = 2,
    focus_areas: Optional[str] = None
) -> str:
    """
    Customize a resume for a specific job description using Claude AI.
    
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
        
        # Build the user message
        user_message = f"""
        Here is my current resume in Markdown format:
        
        {resume_content}
        
        Here is the job description I'm applying for:
        
        {job_description}
        
        Please customize my resume for this specific job.
        """
        
        # Call Claude API
        try:
            # Log API call start
            logfire.info(
                "Calling Claude API for resume customization",
                model=settings.CLAUDE_MODEL,
                system_prompt_length=len(system_prompt),
                user_message_length=len(user_message),
                using_extended_thinking=True,
                thinking_tokens=12000
            )
            
            # The Logfire-wrapped Anthropic client will automatically log the request/response
            response = client.messages.create(
                model=settings.CLAUDE_MODEL,
                system=system_prompt,
                max_tokens=16000,
                temperature=1,  # Must be set to 1 when using extended thinking
                thinking={"type": "enabled", "budget_tokens": 12000},  # Extended thinking for deeper analysis
                messages=[
                    {"role": "user", "content": user_message}
                ]
            )
            
            # Calculate elapsed time
            elapsed_time = time.time() - start_time
            
            # Extract the content
            response_text = ""
            if response.content:
                for content_block in response.content:
                    # Handle different types of content blocks
                    if hasattr(content_block, 'text'):
                        response_text = content_block.text
                        break
                    elif hasattr(content_block, 'type') and content_block.type == 'text':
                        response_text = content_block.text
                        break
            
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
                "Error calling Claude API for resume customization",
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
    Evaluate how well a resume matches a job description using Claude's advanced reasoning.
    This is the "evaluator" stage of the evaluator-optimizer pattern.
    
    Args:
        resume_content: The content of the resume in Markdown format
        job_description: The job description text
        basic_analysis: Optional basic keyword analysis results to enhance evaluation
        customization_level: Level of customization (affects evaluation detail)
        industry: Optional industry name for industry-specific guidance
        
    Returns:
        Dictionary containing Claude's evaluation of the resume-job match
    """
    # Import here to avoid circular imports
    from app.services.prompts import EVALUATOR_PROMPT, get_customization_level_instructions, get_industry_specific_guidance
    
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
        
        # Get customization level specific instructions
        customization_instructions = get_customization_level_instructions(customization_level)
        
        # Get industry-specific guidance if industry is provided
        industry_guidance = ""
        if industry:
            industry_guidance = get_industry_specific_guidance(industry)
            if industry_guidance:
                customization_instructions += f"\n\nINDUSTRY-SPECIFIC GUIDANCE ({industry.upper()}):\n{industry_guidance}"
        
        # Format the prompt with the customization level instructions
        # Replace the raw string with proper escaped braces for f-string compatibility
        prompt_template = EVALUATOR_PROMPT.replace("{customization_level_instructions}", customization_instructions)
        formatted_prompt = prompt_template
        
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
        
        # Call Claude API
        try:
            # Log API call start
            logfire.info(
                "Calling Claude API for resume-job evaluation",
                model=settings.CLAUDE_MODEL,
                has_basic_analysis=basic_analysis is not None,
                using_extended_thinking=True,
                thinking_tokens=15000
            )
            
            # The Logfire-wrapped Anthropic client will automatically log the request/response
            response = client.messages.create(
                model=settings.CLAUDE_MODEL,
                system=formatted_prompt,
                max_tokens=20000,
                temperature=1,  # Must be set to 1 when using extended thinking
                thinking={"type": "enabled", "budget_tokens": 15000},  # Extended thinking for deeper analysis
                messages=[
                    {"role": "user", "content": user_message}
                ]
            )
            
            # Calculate elapsed time
            elapsed_time = time.time() - start_time
            
            # Extract the content and try to parse as JSON
            response_text = ""
            if response.content:
                for content_block in response.content:
                    # Handle different types of content blocks
                    if hasattr(content_block, 'text'):
                        response_text = content_block.text
                        break
                    elif hasattr(content_block, 'type') and content_block.type == 'text':
                        response_text = content_block.text
                        break
            
            try:
                # Extract JSON from the response text
                # Sometimes Claude wraps JSON in markdown code blocks
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
                    "Failed to parse Claude's evaluation as JSON",
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
                "Error calling Claude API for resume-job evaluation",
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
    # Import here to avoid circular imports
    from app.services.prompts import OPTIMIZER_PROMPT, get_customization_level_instructions, get_industry_specific_guidance
    
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
        
        # Get customization level specific instructions
        customization_instructions = get_customization_level_instructions(customization_level)
        
        # Get industry-specific guidance if industry is provided
        industry_guidance = ""
        if industry:
            industry_guidance = get_industry_specific_guidance(industry)
            if industry_guidance:
                customization_instructions += f"\n\nINDUSTRY-SPECIFIC GUIDANCE ({industry.upper()}):\n{industry_guidance}"
        
        # Format the prompt with the customization level instructions
        # Replace the raw string with proper escaped braces for f-string compatibility
        prompt_template = OPTIMIZER_PROMPT.replace("{customization_level_instructions}", customization_instructions)
        formatted_prompt = prompt_template
        
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
        
        # Call Claude API
        try:
            # Log API call start
            logfire.info(
                "Calling Claude API for optimization plan generation",
                model=settings.CLAUDE_MODEL,
                using_extended_thinking=True,
                thinking_tokens=15000
            )
            
            # The Logfire-wrapped Anthropic client will automatically log the request/response
            response = client.messages.create(
                model=settings.CLAUDE_MODEL,
                system=formatted_prompt,
                max_tokens=20000,
                temperature=1,  # Must be set to 1 when using extended thinking
                thinking={"type": "enabled", "budget_tokens": 15000},  # Extended thinking for deeper analysis
                messages=[
                    {"role": "user", "content": user_message}
                ]
            )
            
            # Calculate elapsed time
            elapsed_time = time.time() - start_time
            
            # Extract the content and try to parse as JSON
            response_text = ""
            if response.content:
                for content_block in response.content:
                    # Handle different types of content blocks
                    if hasattr(content_block, 'text'):
                        response_text = content_block.text
                        break
                    elif hasattr(content_block, 'type') and content_block.type == 'text':
                        response_text = content_block.text
                        break
            
            try:
                # Extract JSON from the response text
                # Sometimes Claude wraps JSON in markdown code blocks
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
                    "Failed to parse Claude's optimization plan as a valid CustomizationPlan",
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
                "Error calling Claude API for optimization plan generation",
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
    Generate a cover letter based on a resume and job description using Claude AI.
    
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
        
        # Build the user message
        user_message = f"""
        Here is my resume in Markdown format:
        
        {resume_content}
        
        Here is the job description I'm applying for at {company_name}:
        
        {job_description}
        
        Please write a cover letter for this position that highlights my relevant qualifications.
        """
        
        # Call Claude API
        try:
            # Log API call start
            logfire.info(
                "Calling Claude API for cover letter generation",
                model=settings.CLAUDE_MODEL,
                system_prompt_length=len(system_prompt),
                user_message_length=len(user_message),
                using_extended_thinking=True,
                thinking_tokens=12000
            )
            
            # The Logfire-wrapped Anthropic client will automatically log the request/response
            response = client.messages.create(
                model=settings.CLAUDE_MODEL,
                system=system_prompt,
                max_tokens=16000,
                temperature=1,  # Must be set to 1 when using extended thinking
                thinking={"type": "enabled", "budget_tokens": 12000},  # Extended thinking for deeper analysis
                messages=[
                    {"role": "user", "content": user_message}
                ]
            )
            
            # Calculate elapsed time
            elapsed_time = time.time() - start_time
            
            # Extract the content
            response_text = ""
            if response.content:
                for content_block in response.content:
                    # Handle different types of content blocks
                    if hasattr(content_block, 'text'):
                        response_text = content_block.text
                        break
                    elif hasattr(content_block, 'type') and content_block.type == 'text':
                        response_text = content_block.text
                        break
            
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
                "Error calling Claude API for cover letter generation",
                error=str(e),
                error_type=type(e).__name__,
                duration_seconds=round(elapsed_time, 2)
            )
            
            # Re-raise the exception
            raise e