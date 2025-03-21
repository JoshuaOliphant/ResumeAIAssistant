import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.resume import Resume, ResumeVersion
from app.models.job import JobDescription
from app.schemas.customize import ResumeCustomizationRequest, ResumeCustomizationResponse
from app.services.claude_service import customize_resume

router = APIRouter()


@router.post("/", response_model=ResumeCustomizationResponse)
async def customize_resume_endpoint(
    customization_request: ResumeCustomizationRequest,
    db: Session = Depends(get_db)
):
    """
    Customize a resume for a specific job description using Claude AI.
    
    - **resume_id**: ID of the resume to customize
    - **job_description_id**: ID of the job description to customize for
    - **customization_strength**: Strength of customization (1-3)
    - **focus_areas**: Optional comma-separated list of areas to focus on
    """
    # Verify the resume exists
    resume = db.query(Resume).filter(Resume.id == customization_request.resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    # Get the latest version of the resume
    resume_version = db.query(ResumeVersion).filter(
        ResumeVersion.resume_id == customization_request.resume_id
    ).order_by(ResumeVersion.version_number.desc()).first()
    
    if not resume_version:
        raise HTTPException(status_code=404, detail="Resume content not found")
    
    # Verify the job description exists
    job = db.query(JobDescription).filter(JobDescription.id == customization_request.job_description_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job description not found")
    
    # Call Claude to customize the resume
    customized_content = await customize_resume(
        resume_content=resume_version.content,
        job_description=job.description,
        customization_strength=customization_request.customization_strength,
        focus_areas=customization_request.focus_areas
    )
    
    # Create a new resume version for the customized content
    new_version_number = resume_version.version_number + 1
    
    # Create new customized version
    customized_version = ResumeVersion(
        id=str(uuid.uuid4()),
        resume_id=customization_request.resume_id,
        content=customized_content,
        version_number=new_version_number,
        is_customized=1,
        job_description_id=customization_request.job_description_id
    )
    db.add(customized_version)
    db.commit()
    db.refresh(customized_version)
    
    # Return the response
    response = ResumeCustomizationResponse(
        original_resume_id=customization_request.resume_id,
        customized_resume_id=customization_request.resume_id,  # Same ID, but different version
        job_description_id=customization_request.job_description_id
    )
    
    return response
