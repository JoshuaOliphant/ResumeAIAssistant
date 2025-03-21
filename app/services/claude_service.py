import os
import sys
from typing import Optional
import anthropic
from anthropic import Anthropic

from app.core.config import settings

# Initialize the Anthropic client
if not settings.ANTHROPIC_API_KEY:
    raise ValueError('ANTHROPIC_API_KEY environment variable must be set')

client = Anthropic(
    # Get your API key from https://console.anthropic.com/
    api_key=settings.ANTHROPIC_API_KEY,
)

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
        response = client.messages.create(
            model=settings.CLAUDE_MODEL,
            system=system_prompt,
            max_tokens=4000,
            messages=[
                {"role": "user", "content": user_message}
            ]
        )
        
        # Return the generated content
        return response.content[0].text
        
    except Exception as e:
        # Log the error (in a real app, use a proper logger)
        print(f"Error calling Claude API: {str(e)}")
        raise e


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
        response = client.messages.create(
            model=settings.CLAUDE_MODEL,
            system=system_prompt,
            max_tokens=4000,
            messages=[
                {"role": "user", "content": user_message}
            ]
        )
        
        # Return the generated content
        return response.content[0].text
        
    except Exception as e:
        # Log the error (in a real app, use a proper logger)
        print(f"Error calling Claude API: {str(e)}")
        raise e