"""
Job requirements extraction service.

This service extracts key requirements from job descriptions,
categorizes them, and returns structured data for use in resume customization.
"""

import logfire
from sqlalchemy.orm import Session

from app.models.job import JobDescription
from app.schemas.requirements import KeyRequirements


async def extract_key_requirements(job_description_id: str, db: Session) -> KeyRequirements:
    """
    Extract key requirements from a job description in the database.
    
    Args:
        job_description_id: ID of the job description to extract from
        db: Database session
        
    Returns:
        KeyRequirements object containing structured requirements
    """
    # Get the job description from the database
    job = db.query(JobDescription).filter(JobDescription.id == job_description_id).first()
    if not job:
        logfire.error(f"Job description with ID {job_description_id} not found")
        raise ValueError(f"Job description with ID {job_description_id} not found")
    
    # Extract requirements from the content
    return await extract_key_requirements_from_content(
        job_description_content=job.content,
        job_title=job.title,
        company=job.company
    )


async def extract_key_requirements_from_content(
    job_description_content: str,
    job_title: str = None,
    company: str = None
) -> KeyRequirements:
    """
    Extract key requirements from job description content.
    
    Args:
        job_description_content: Raw job description text
        job_title: Optional job title
        company: Optional company name
        
    Returns:
        KeyRequirements object containing structured requirements
    """
    # In a real implementation, this would use AI to extract requirements
    # For now, return a placeholder implementation
    
    # Extract job title if not provided
    if not job_title and "Title:" in job_description_content:
        job_title = "Software Developer"  # Placeholder
    
    # Placeholder categories and keywords
    categories = {
        "technical_skills": ["Python", "SQL", "React"],
        "soft_skills": ["Communication", "Teamwork"],
        "experience": ["3+ years experience"],
        "education": ["Bachelor's degree"]
    }
    
    # Simple keyword extraction (in a real implementation would be more sophisticated)
    keywords = ["Python", "SQL", "React", "Communication", "Teamwork", "Bachelor's degree"]
    
    logfire.info(
        "Extracted requirements",
        job_title=job_title,
        company=company,
        keyword_count=len(keywords)
    )
    
    # Return the structured requirements
    return KeyRequirements(
        job_title=job_title or "Unspecified Position",
        company=company or "Unspecified Company",
        job_type="Full-time",  # Default assumption
        categories=categories,
        keywords=keywords,
        confidence=0.85,  # Placeholder confidence score
        total_requirements_count=len(keywords)
    )