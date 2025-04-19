from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.resume import Resume, ResumeVersion
from app.models.job import JobDescription
from app.schemas.cover_letter import CoverLetterRequest, CoverLetterResponse
from app.services.pydanticai_service import generate_cover_letter

router = APIRouter()


@router.post("/", response_model=CoverLetterResponse)
@router.post("/generate/", response_model=CoverLetterResponse)
async def generate_cover_letter_endpoint(
    cover_letter_request: CoverLetterRequest,
    db: Session = Depends(get_db)
):
    """
    Generate a cover letter based on a resume and job description using AI models.
    
    - **resume_id**: ID of the resume to base the cover letter on
    - **job_description_id**: ID of the job description for the application
    - **applicant_name**: Optional applicant name
    - **company_name**: Optional company name (will use job description company if available)
    - **hiring_manager_name**: Optional hiring manager name
    - **additional_context**: Optional additional context to include
    - **tone**: Tone of the cover letter (professional, enthusiastic, formal, etc.)
    """
    # Verify the resume exists
    resume = db.query(Resume).filter(Resume.id == cover_letter_request.resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    # Get the latest version of the resume
    resume_version = db.query(ResumeVersion).filter(
        ResumeVersion.resume_id == cover_letter_request.resume_id
    ).order_by(ResumeVersion.version_number.desc()).first()
    
    if not resume_version:
        raise HTTPException(status_code=404, detail="Resume content not found")
    
    # Verify the job description exists
    job = db.query(JobDescription).filter(JobDescription.id == cover_letter_request.job_description_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job description not found")
    
    # Use company name from job description if not provided
    company_name = cover_letter_request.company_name or job.company or "the company"
    
    # Call Claude to generate cover letter
    cover_letter_content = await generate_cover_letter(
        resume_content=resume_version.content,
        job_description=job.description,
        applicant_name=cover_letter_request.applicant_name,
        company_name=company_name,
        hiring_manager_name=cover_letter_request.hiring_manager_name,
        additional_context=cover_letter_request.additional_context,
        tone=cover_letter_request.tone
    )
    
    # Return the response
    response = CoverLetterResponse(
        resume_id=cover_letter_request.resume_id,
        job_description_id=cover_letter_request.job_description_id,
        cover_letter_content=cover_letter_content
    )
    
    return response
