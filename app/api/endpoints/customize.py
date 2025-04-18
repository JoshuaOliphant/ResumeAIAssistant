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
from app.services import openai_agents_service
from app.services.customization_service import get_customization_service, CustomizationService

router = APIRouter()


@router.post("/", response_model=ResumeCustomizationResponse)
async def customize_resume_endpoint(
    customization_request: ResumeCustomizationRequest,
    db: Session = Depends(get_db)
):
    """
    Customize a resume for a specific job description using OpenAI's AI models.
    
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
    
    # Get the customization plan first
    plan_request = CustomizationPlanRequest(
        resume_id=customization_request.resume_id,
        job_description_id=customization_request.job_description_id,
        customization_strength=customization_request.customization_strength,
        industry=customization_request.focus_areas
    )
    
    # Get the customization service
    customization_service = get_customization_service(db)
    
    # Generate the plan
    plan = await customization_service.generate_customization_plan(plan_request)
    
    # Now, implement the plan to get the initial optimized resume
    try:
        optimized_resume = await customization_service._implement_optimization_plan(
            resume_version.content, 
            plan
        )
    except Exception as e:
        logfire.error(
            "Error implementing optimization plan",
            error=str(e),
            error_type=type(e).__name__,
            traceback=traceback.format_exception(type(e), e, e.__traceback__),
            resume_id=customization_request.resume_id,
            job_id=customization_request.job_description_id
        )
        # In case of error, use the original content
        optimized_resume = resume_version.content
    
    # Implement the iterative feedback loop for up to MAX_FEEDBACK_ITERATIONS iterations
    iterations = 0
    while iterations < MAX_FEEDBACK_ITERATIONS:
        # Log the iteration count
        logfire.info(
            f"Starting feedback iteration {iterations + 1}/{MAX_FEEDBACK_ITERATIONS}",
            resume_id=customization_request.resume_id,
            job_id=customization_request.job_description_id,
            iteration=iterations + 1
        )
        
        # Get feedback from the evaluator on the optimized resume
        
        start_time_feedback = time.time()
        feedback = await openai_agents_service.evaluate_optimization_plan(
            original_resume=resume_version.content,
            job_description=job.description,
            optimized_resume=optimized_resume,
            customization_level=customization_request.customization_strength,
            industry=customization_request.focus_areas
        )
        
        # Log feedback metrics
        elapsed_time_feedback = time.time() - start_time_feedback
        logfire.info(
            f"Feedback iteration {iterations + 1} evaluation completed",
            resume_id=customization_request.resume_id,
            job_id=customization_request.job_description_id,
            duration_seconds=round(elapsed_time_feedback, 2),
            requires_iteration=feedback.get("requires_iteration", False),
            experience_issues_count=len(feedback.get("experience_preservation_issues", [])),
            keyword_feedback_count=len(feedback.get("keyword_alignment_feedback", []))
        )
        
        # If no further iteration is required, break out of the loop
        if not feedback.get("requires_iteration", False):
            logfire.info(
                f"No further iterations required after iteration {iterations + 1}",
                resume_id=customization_request.resume_id,
                job_id=customization_request.job_description_id
            )
            break
            
        # If we have experience preservation issues, these are critical to fix
        if feedback.get("experience_preservation_issues"):
            logfire.warning(
                f"Experience preservation issues found in iteration {iterations + 1}",
                resume_id=customization_request.resume_id,
                job_id=customization_request.job_description_id,
                issues_count=len(feedback.get("experience_preservation_issues", []))
            )
        
        # Generate an improved plan based on the feedback
        start_time_improved = time.time()
        improved_plan = await openai_agents_service.optimize_resume_with_feedback(
            original_resume=resume_version.content,
            job_description=job.description,
            evaluation={},  # We don't need the full evaluation for feedback response
            feedback=feedback,
            customization_level=customization_request.customization_strength,
            industry=customization_request.focus_areas
        )
        
        # Log improved plan metrics
        elapsed_time_improved = time.time() - start_time_improved
        logfire.info(
            f"Improved plan generated for iteration {iterations + 1}",
            resume_id=customization_request.resume_id,
            job_id=customization_request.job_description_id,
            duration_seconds=round(elapsed_time_improved, 2),
            recommendations_count=len(improved_plan.recommendations)
        )
        
        # Update the plan with the improved one
        plan = improved_plan
        
        # Implement the improved plan
        try:
            optimized_resume = await customization_service._implement_optimization_plan(
                resume_version.content, 
                plan
            )
        except Exception as e:
            logfire.error(
                f"Error implementing improved plan in iteration {iterations + 1}",
                error=str(e),
                error_type=type(e).__name__,
                traceback=traceback.format_exception(type(e), e, e.__traceback__),
                resume_id=customization_request.resume_id,
                job_id=customization_request.job_description_id,
                iteration=iterations + 1
            )
            # In case of error, use the previous optimized resume
            # (This avoids breaking the loop if implementation fails)
            # optimized_resume remains unchanged
        
        # Increment iteration counter
        iterations += 1
    
    # If we reached the maximum iterations, log this
    if iterations == MAX_FEEDBACK_ITERATIONS:
        logfire.info(
            f"Reached maximum feedback iterations ({MAX_FEEDBACK_ITERATIONS})",
            resume_id=customization_request.resume_id,
            job_id=customization_request.job_description_id
        )
    
    # The final optimized resume is our customized content
    customized_content = optimized_resume
    
    # Log the result of the customization process
    logfire.info(
        "Resume customization completed with feedback loop",
        resume_id=customization_request.resume_id,
        job_id=customization_request.job_description_id,
        iterations_completed=iterations,
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
