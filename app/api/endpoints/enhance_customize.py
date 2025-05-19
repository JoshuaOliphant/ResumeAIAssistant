"""
Enhanced API endpoints for resume customization with advanced parallel processing.
"""

import uuid
from typing import Dict, Any

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
from app.services.enhanced_customization_service import (
    get_enhanced_customization_service,
)
from app.services.prompts import MAX_FEEDBACK_ITERATIONS
from app.services.pydanticai_optimizer import get_pydanticai_optimizer_service

router = APIRouter()


@router.post("/", response_model=ResumeCustomizationResponse)
async def customize_resume_enhanced(
    customization_request: ResumeCustomizationRequest, db: Session = Depends(get_db)
):
    """
    Customize a resume for a specific job description using the enhanced parallel
    processing architecture with advanced features.

    This endpoint provides significant improvements in performance, reliability, and
    result quality through:
    1. Advanced task scheduling with adaptive prioritization
    2. Request batching for similar tasks
    3. Circuit breaker pattern for API failure handling
    4. Caching layer for improved performance
    5. Sequential consistency pass for better results

    - **resume_id**: ID of the resume to customize
    - **job_description_id**: ID of the job description to customize for
    - **customization_strength**: Strength of customization (1-3)
    - **industry**: Optional industry for industry-specific guidance
    - **focus_areas**: Optional comma-separated list of areas to focus on
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
        "Starting enhanced resume customization",
        resume_id=customization_request.resume_id,
        job_id=customization_request.job_description_id,
        customization_level=customization_request.customization_strength.name,
    )

    # Use the PydanticAI optimizer service for the complete workflow
    pydanticai_service = await get_pydanticai_optimizer_service(db)

    # Get the ATS analysis from the request
    ats_analysis = customization_request.ats_analysis

    # Perform the complete customization process with enhanced services
    # First, generate the plan using the enhanced service
    enhanced_service = get_enhanced_customization_service(db)
    
    # Create a plan data structure (using dict instead of the deprecated CustomizationPlanRequest)
    plan_data = {
        "resume_id": customization_request.resume_id,
        "job_description_id": customization_request.job_description_id,
        "customization_strength": customization_request.customization_strength,
        "industry": customization_request.focus_areas,
        "ats_analysis": ats_analysis
    }
    
    # Generate the plan using enhanced parallel architecture
    plan = await enhanced_service.generate_customization_plan(plan_data)
    
    # Then implement the plan with the existing optimizer
    result = await pydanticai_service.implement_resume_customization(
        resume_id=customization_request.resume_id,
        job_id=customization_request.job_description_id,
        plan=plan
    )

    # Get the content from the result
    customized_content = result["customized_content"]

    logfire.info(
        "Enhanced resume customization completed successfully",
        resume_id=customization_request.resume_id,
        job_id=customization_request.job_description_id,
        customized_resume_id=result["customized_resume_id"],
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