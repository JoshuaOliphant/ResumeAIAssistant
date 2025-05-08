"""
API endpoints for resume customization.
"""
import uuid
import time
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logfire
import traceback
from app.services.prompts import MAX_FEEDBACK_ITERATIONS

from app.db.session import get_db
from app.models.resume import Resume, ResumeVersion
from app.models.job import JobDescription
from app.schemas.customize import (
    ResumeCustomizationRequest, 
    ResumeCustomizationResponse,
    CustomizationPlanRequest,
    CustomizationPlan
)
from app.services.customization_service import get_customization_service, CustomizationService
from app.services.pydanticai_optimizer import get_pydanticai_optimizer_service, PydanticAIOptimizerService
from app.services.parallel_customization_service import get_parallel_customization_service, ParallelCustomizationService

router = APIRouter()


@router.post("/", response_model=ResumeCustomizationResponse)
async def customize_resume_endpoint(
    customization_request: ResumeCustomizationRequest,
    db: Session = Depends(get_db)
):
    """
    Customize a resume for a specific job description using PydanticAI.
    
    - **resume_id**: ID of the resume to customize
    - **job_description_id**: ID of the job description to customize for
    - **customization_strength**: Strength of customization (1-3)
    - **focus_areas**: Optional comma-separated list of areas to focus on or industry
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
    
    # Log operation start
    logfire.info(
        "Starting resume customization with PydanticAI",
        resume_id=customization_request.resume_id,
        job_id=customization_request.job_description_id,
        customization_level=customization_request.customization_strength.name
    )
    
    # Use the PydanticAI optimizer service for the complete workflow
    pydanticai_service = get_pydanticai_optimizer_service(db)
    
    # Get the ATS analysis if it exists in the request
    ats_analysis = customization_request.ats_analysis if hasattr(customization_request, 'ats_analysis') else None
    
    # Perform the complete customization process
    result = await pydanticai_service.customize_resume(
        resume_id=customization_request.resume_id,
        job_id=customization_request.job_description_id,
        customization_strength=customization_request.customization_strength,
        industry=customization_request.focus_areas,
        iterations=MAX_FEEDBACK_ITERATIONS,
        ats_analysis=ats_analysis  # Pass the ATS analysis to avoid redundant analysis
    )
    
    # Get the content from the result
    customized_content = result["customized_content"]
    
    logfire.info(
        "Resume customization completed successfully with PydanticAI",
        resume_id=customization_request.resume_id,
        job_id=customization_request.job_description_id,
        customized_resume_id=result["customized_resume_id"]
    )
    
    # Log the result of the customization process
    logfire.info(
        "Resume customization completed",
        resume_id=customization_request.resume_id,
        job_id=customization_request.job_description_id,
        final_content_length=len(customized_content)
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


@router.post("/plan", response_model=CustomizationPlan)
async def generate_customization_plan(
    plan_request: CustomizationPlanRequest,
    db: Session = Depends(get_db)
):
    """
    Generate a detailed resume customization plan using the evaluator-optimizer pattern
    with parallel processing architecture.
    
    This endpoint implements a multi-stage AI workflow:
    1. Basic analysis (existing ATS analyzer)
    2. Parallel evaluation (AI models analyzing resume sections concurrently)
    3. Parallel optimization (AI models generating section-specific plans concurrently)
    4. Results aggregation (combining section analyses into unified plan)
    
    - **resume_id**: ID of the resume to analyze
    - **job_description_id**: ID of the job description to analyze against
    - **customization_strength**: Strength of customization (1=conservative, 2=balanced, 3=extensive)
    - **ats_analysis**: Optional results from prior ATS analysis
    
    Returns a detailed customization plan with specific recommendations.
    """
    start_time = time.time()
    logfire.info(
        "Generating customization plan with parallel architecture",
        resume_id=plan_request.resume_id,
        job_id=plan_request.job_description_id,
        customization_level=plan_request.customization_strength.name
    )
    
    try:
        # Use the parallel customization service for improved performance
        parallel_service = get_parallel_customization_service(db)
        
        # Generate the plan using parallel architecture
        plan = await parallel_service.generate_customization_plan(plan_request)
        
        # Calculate and log the total processing time
        total_duration = time.time() - start_time
        logfire.info(
            "Customization plan generated successfully with parallel architecture",
            resume_id=plan_request.resume_id,
            job_id=plan_request.job_description_id,
            recommendation_count=len(plan.recommendations),
            total_duration_seconds=round(total_duration, 2)
        )
        
        return plan
        
    except ValueError as e:
        # Handle errors for missing resources
        error_message = str(e)
        logfire.error(
            "Error generating customization plan",
            error=error_message,
            resume_id=plan_request.resume_id,
            job_id=plan_request.job_description_id
        )
        
        if "not found" in error_message.lower():
            raise HTTPException(status_code=404, detail=error_message)
        else:
            raise HTTPException(status_code=400, detail=error_message)
            
    except Exception as e:
        # Handle unexpected errors
        logfire.error(
            "Unexpected error generating customization plan",
            error=str(e),
            error_type=type(e).__name__,
            traceback=traceback.format_exception(type(e), e, e.__traceback__),
            resume_id=plan_request.resume_id,
            job_id=plan_request.job_description_id
        )
        raise HTTPException(
            status_code=500, 
            detail=f"An error occurred while generating the customization plan: {str(e)}"
        )

@router.post("/parallel", response_model=CustomizationPlan)
async def generate_customization_plan_parallel(
    plan_request: CustomizationPlanRequest,
    db: Session = Depends(get_db)
):
    """
    Generate a detailed resume customization plan using the parallel processing architecture.
    This is an alternative endpoint that explicitly uses the parallel architecture.
    
    This endpoint is identical to /plan but is provided separately for A/B testing and comparison.
    
    - **resume_id**: ID of the resume to analyze
    - **job_description_id**: ID of the job description to analyze against
    - **customization_strength**: Strength of customization (1=conservative, 2=balanced, 3=extensive)
    - **ats_analysis**: Optional results from prior ATS analysis
    
    Returns a detailed customization plan with specific recommendations.
    """
    # Simply call the main implementation
    return await generate_customization_plan(plan_request, db)