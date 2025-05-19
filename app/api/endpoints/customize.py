"""
API endpoints for resume customization.
"""

import sys
import uuid
import traceback
import time
import asyncio

import logfire
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.job import JobDescription
from app.models.resume import Resume, ResumeVersion
from app.schemas.customize import (
    ResumeCustomizationRequest,
    ResumeCustomizationResponse,
)
from app.services.prompts import MAX_FEEDBACK_ITERATIONS
from app.services.pydanticai_optimizer import get_pydanticai_optimizer_service

router = APIRouter()


@router.post("/", response_model=ResumeCustomizationResponse)
async def customize_resume_endpoint(
    request: Request,
    customization_request: ResumeCustomizationRequest, 
    db: Session = Depends(get_db)
):
    # Debug log the raw request URL and body content
    request_body = await request.body()
    logfire.debug(
        "Customize endpoint accessed - raw request details",
        url=str(request.url),
        method=request.method,
        path=request.url.path,
        query_params=str(request.query_params),
        body_content=request_body.decode('utf-8', errors='replace'),
        content_type=request.headers.get("content-type"),
    )
    # Track request processing time
    start_time = time.time()
    
    # Log detailed request information
    logfire.info(
        "Received resume customization request",
        client_host=request.client.host if request.client else None,
        client_port=request.client.port if request.client else None,
        resume_id=customization_request.resume_id,
        job_description_id=customization_request.job_description_id,
        customization_strength=customization_request.customization_strength,
        has_ats_analysis=customization_request.ats_analysis is not None,
        request_path=request.url.path,
        request_method=request.method,
        request_time=time.time(),
        headers=dict(request.headers),
    )
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

    # Log operation start with more detail
    logfire.info(
        "Starting resume customization with PydanticAI",
        resume_id=customization_request.resume_id,
        job_id=customization_request.job_description_id,
        customization_level=customization_request.customization_strength.name,
        resume_title=resume.title if resume else None,
        resume_version=resume_version.version_number if resume_version else None,
        job_title=job.title if job else None,
        focus_areas=customization_request.focus_areas,
    )

    # Report memory usage
    logfire.debug(
        "Memory usage before customization",
        python_version=sys.version,
        process_time=time.process_time(),
    )
    
    # Use the PydanticAI optimizer service for the complete workflow
    try:
        pydanticai_service = await get_pydanticai_optimizer_service(db)
        logfire.info("PydanticAI optimizer service initialized")

        # Get the ATS analysis from the request
        ats_analysis = customization_request.ats_analysis

        # Record pre-customization metrics
        resume_length = len(resume_version.content) if resume_version else 0
        job_length = len(job.description) if job else 0
        logfire.info(
            "Pre-customization metrics",
            resume_length=resume_length,
            job_description_length=job_length,
            max_iterations=MAX_FEEDBACK_ITERATIONS,
        )
        
        # Track when we start the actual customization process
        customization_start = time.time()
        logfire.info("Starting PydanticAI optimize_resume call")
        
        # Perform the complete customization process
        result = await pydanticai_service.customize_resume(
            resume_id=customization_request.resume_id,
            job_id=customization_request.job_description_id,
            customization_strength=customization_request.customization_strength,
            industry=customization_request.focus_areas,
            iterations=MAX_FEEDBACK_ITERATIONS,
            ats_analysis=ats_analysis,  # Pass the ATS analysis to avoid redundant analysis
        )
        
        # Track when the customization process is complete
        customization_end = time.time()
        customization_duration = customization_end - customization_start
        logfire.info(
            "PydanticAI customization completed",
            duration_seconds=customization_duration,
            result_keys=list(result.keys()) if result else None,
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
        
        # Log total request processing time
        end_time = time.time()
        processing_time = end_time - start_time
        logfire.info(
            "Resume customization request completed",
            total_processing_time=processing_time,
            status="success",
        )

        return response
        
    except asyncio.TimeoutError as e:
        # Handle timeout errors specifically
        error_time = time.time()
        processing_time = error_time - start_time
        
        logfire.error(
            "Timeout during resume customization",
            resume_id=customization_request.resume_id,
            job_id=customization_request.job_description_id,
            error_type="TimeoutError",
            error_message="The resume customization process took too long to complete. This may be due to high server load or complexity of the customization.",
            processing_time=processing_time,
            traceback=traceback.format_exception(type(e), e, e.__traceback__),
        )
        
        # Return a specific HTTP error for timeouts
        raise HTTPException(
            status_code=504,  # Gateway Timeout
            detail="The resume customization process timed out. Please try again with a less complex optimization or try again later."
        )
        
    except Exception as e:
        # Log detailed error information for other errors
        error_time = time.time()
        processing_time = error_time - start_time
        
        logfire.error(
            "Error during resume customization",
            resume_id=customization_request.resume_id,
            job_id=customization_request.job_description_id,
            error_type=type(e).__name__,
            error_message=str(e),
            processing_time=processing_time,
            traceback=traceback.format_exception(type(e), e, e.__traceback__),
        )
        
        # Return an appropriate HTTP exception
        if isinstance(e, HTTPException):
            raise
        else:
            # Convert general exceptions to HTTP exceptions
            raise HTTPException(
                status_code=500,
                detail=f"An error occurred during resume customization: {str(e)}"
            )
