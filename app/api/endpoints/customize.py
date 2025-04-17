import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logfire

from app.db.session import get_db
from app.models.resume import Resume, ResumeVersion
from app.models.job import JobDescription
from app.schemas.customize import (
    ResumeCustomizationRequest, 
    ResumeCustomizationResponse,
    CustomizationPlanRequest,
    CustomizationPlan
)
from app.services.claude_service import customize_resume
from app.services.customization_service import get_customization_service, CustomizationService

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


@router.post("/plan", response_model=CustomizationPlan)
async def generate_customization_plan(
    plan_request: CustomizationPlanRequest,
    customization_service: CustomizationService = Depends(get_customization_service)
):
    """
    Generate a detailed resume customization plan using the evaluator-optimizer pattern.
    
    This endpoint implements a multi-stage AI workflow:
    1. Basic analysis (existing ATS analyzer)
    2. Evaluation (Claude acting as ATS expert)
    3. Optimization (Claude generating a detailed plan)
    
    - **resume_id**: ID of the resume to analyze
    - **job_description_id**: ID of the job description to analyze against
    - **customization_strength**: Strength of customization (1=conservative, 2=balanced, 3=extensive)
    - **ats_analysis**: Optional results from prior ATS analysis
    
    Returns a detailed customization plan with specific recommendations.
    """
    logfire.info(
        "Generating customization plan",
        resume_id=plan_request.resume_id,
        job_id=plan_request.job_description_id,
        customization_level=plan_request.customization_strength.name
    )
    
    try:
        # Generate the plan using our service
        plan = await customization_service.generate_customization_plan(plan_request)
        
        logfire.info(
            "Customization plan generated successfully",
            resume_id=plan_request.resume_id,
            job_id=plan_request.job_description_id,
            recommendation_count=len(plan.recommendations)
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
        logfire.exception(
            "Unexpected error generating customization plan",
            error=str(e),
            resume_id=plan_request.resume_id,
            job_id=plan_request.job_description_id
        )
        raise HTTPException(
            status_code=500, 
            detail=f"An error occurred while generating the customization plan: {str(e)}"
        )
