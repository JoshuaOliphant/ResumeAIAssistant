"""
API endpoints for resume customization.
"""

import time
import traceback
import uuid

import logfire
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.job import JobDescription
from app.models.resume import Resume, ResumeVersion
from app.schemas.customize import (
    CustomizationPlan,
    ResumeCustomizationRequest,
    ResumeCustomizationResponse,
)
from app.services.parallel_customization_service import (
    get_parallel_customization_service,
)
from app.services.prompts import MAX_FEEDBACK_ITERATIONS
from app.services.pydanticai_optimizer import get_pydanticai_optimizer_service

router = APIRouter()


@router.post("/", response_model=ResumeCustomizationResponse)
async def customize_resume_endpoint(
    customization_request: ResumeCustomizationRequest, db: Session = Depends(get_db)
):
    """
    Customize a resume for a specific job description using PydanticAI.

    - **resume_id**: ID of the resume to customize
    - **job_description_id**: ID of the job description to customize for
    - **customization_strength**: Strength of customization (1-3)
    - **focus_areas**: Optional comma-separated list of areas to focus on or industry
    """
    # Verify the resume exists
    resume = (
        db.query(Resume).filter(Resume.id == customization_request.resume_id).first()
    )
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    # Get the latest version of the resume
    resume_version = (
        db.query(ResumeVersion)
        .filter(ResumeVersion.resume_id == customization_request.resume_id)
        .order_by(ResumeVersion.version_number.desc())
        .first()
    )

    if not resume_version:
        raise HTTPException(status_code=404, detail="Resume content not found")

    # Verify the job description exists
    job = (
        db.query(JobDescription)
        .filter(JobDescription.id == customization_request.job_description_id)
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job description not found")

    # Log operation start
    logfire.info(
        "Starting resume customization with PydanticAI",
        resume_id=customization_request.resume_id,
        job_id=customization_request.job_description_id,
        customization_level=customization_request.customization_strength.name,
    )

    # Use the PydanticAI optimizer service for the complete workflow
    pydanticai_service = get_pydanticai_optimizer_service(db)

    # Get the ATS analysis from the request
    ats_analysis = customization_request.ats_analysis

    # Perform the complete customization process
    result = await pydanticai_service.customize_resume(
        resume_id=customization_request.resume_id,
        job_id=customization_request.job_description_id,
        customization_strength=customization_request.customization_strength,
        industry=customization_request.focus_areas,
        iterations=MAX_FEEDBACK_ITERATIONS,
        ats_analysis=ats_analysis,  # Pass the ATS analysis to avoid redundant analysis
    )

    # Get the content from the result
    customized_content = result["customized_content"]

    logfire.info(
        "Resume customization completed successfully with PydanticAI",
        resume_id=customization_request.resume_id,
        job_id=customization_request.job_description_id,
        customized_resume_id=result["customized_resume_id"],
    )

    # Log the result of the customization process
    logfire.info(
        "Resume customization completed",
        resume_id=customization_request.resume_id,
        job_id=customization_request.job_description_id,
        final_content_length=len(customized_content),
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
        job_description_id=customization_request.job_description_id,
    )
    db.add(customized_version)
    db.commit()
    db.refresh(customized_version)

    # Return the response
    response = ResumeCustomizationResponse(
        original_resume_id=customization_request.resume_id,
        customized_resume_id=customization_request.resume_id,  # Same ID, but different version
        job_description_id=customization_request.job_description_id,
    )

    return response


# TODO: Remove this deprecated endpoint entirely in the next major version
@router.post("/plan", response_model=dict)
async def generate_customization_plan(request: dict, db: Session = Depends(get_db)):
    """
    [DEPRECATED] This endpoint is no longer in use.
    
    The application now uses the PydanticAI-based four-stage workflow with WebSocket 
    progress reporting for resume customization.
    
    This endpoint is kept for backward compatibility but returns a deprecation notice.
    """
    logfire.info("Deprecated /plan endpoint accessed")
    
    return {
        "detail": "This endpoint is deprecated. The application now uses the WebSocket-based four-stage workflow for resume customization."
    }


# TODO: Remove this deprecated endpoint entirely in the next major version
@router.post("/parallel", response_model=dict)
async def generate_customization_plan_parallel(request: dict, db: Session = Depends(get_db)):
    """
    [DEPRECATED] This endpoint is no longer in use.
    
    The application now uses the PydanticAI-based four-stage workflow with WebSocket 
    progress reporting for resume customization.
    
    This endpoint is kept for backward compatibility but returns a deprecation notice.
    """
    return await generate_customization_plan(request, db)
