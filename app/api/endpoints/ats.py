from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logfire
import traceback

from app.db.session import get_db
from app.models.resume import Resume, ResumeVersion
from app.models.job import JobDescription
from app.schemas.ats import (
    ATSAnalysisRequest,
    ATSAnalysisResponse,
    ATSContentAnalysisRequest,
    ATSContentAnalysisResponse
)
from app.schemas.customize import (
    CustomizationPlanRequest,
    CustomizationPlan,
    CustomizationLevel
)

from app.services.ats_service import analyze_resume_for_ats
from app.services.pydanticai_optimizer import get_pydanticai_optimizer_service

router = APIRouter()


from app.services.smart_request_handler import smart_request, TaskComplexity, RequestPriority

@router.post("/analyze", response_model=ATSAnalysisResponse)
@smart_request(complexity=TaskComplexity.MODERATE, priority=RequestPriority.HIGH)
async def analyze_resume(
    analysis_request: ATSAnalysisRequest,
    db: Session = Depends(get_db),
    request_id: str = None  # Added for smart request handling
):
    """
    Analyze a resume against a job description for ATS compatibility.

    - **resume_id**: ID of the resume to analyze
    - **job_description_id**: ID of the job description to compare against
    """
    # Verify the resume exists
    resume = db.query(Resume).filter(Resume.id == analysis_request.resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    # Get the latest version of the resume
    resume_version = db.query(ResumeVersion).filter(
        ResumeVersion.resume_id == analysis_request.resume_id
    ).order_by(ResumeVersion.version_number.desc()).first()

    if not resume_version:
        raise HTTPException(status_code=404, detail="Resume content not found")

    # Verify the job description exists
    job = db.query(JobDescription).filter(JobDescription.id == analysis_request.job_description_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job description not found")

    # Log request with detailed information for monitoring
    logfire.info(
        "Starting ATS analysis with smart request handling",
        request_id=request_id,
        resume_id=analysis_request.resume_id,
        job_id=analysis_request.job_description_id,
        user_id=resume.user_id
    )

    # Perform ATS analysis
    analysis_result = await analyze_resume_for_ats(resume_version.content, job.description)

    # Structure the response
    response = ATSAnalysisResponse(
        resume_id=analysis_request.resume_id,
        job_description_id=analysis_request.job_description_id,
        match_score=analysis_result["match_score"],
        matching_keywords=analysis_result["matching_keywords"],
        missing_keywords=analysis_result["missing_keywords"],
        improvements=analysis_result["improvements"],
        job_type=analysis_result.get("job_type", "default"),
        section_scores=analysis_result.get("section_scores", []),
        confidence=analysis_result.get("confidence", "medium"),
        keyword_density=analysis_result.get("keyword_density", 0.0),
        request_id=request_id  # Include request ID in response for tracking
    )

    # Log completion for monitoring
    logfire.info(
        "ATS analysis completed successfully",
        request_id=request_id,
        resume_id=analysis_request.resume_id,
        job_id=analysis_request.job_description_id,
        match_score=analysis_result["match_score"],
        processing_time=f"{analysis_result.get('processing_time', 0):.2f}s"
    )

    return response


@router.post("/analyze-and-plan", response_model=CustomizationPlan)
async def analyze_and_generate_plan(
    request: ATSAnalysisRequest,
    customization_level: CustomizationLevel = CustomizationLevel.BALANCED,
    db: Session = Depends(get_db)
):
    """
    Analyze a resume against a job description and generate a customization plan in one step.
    This implements the evaluator-optimizer pattern described in the Anthropic blog.

    - **resume_id**: ID of the resume to analyze
    - **job_description_id**: ID of the job description to compare against
    - **customization_level**: Strength of customization (1=conservative, 2=balanced, 3=extensive)

    Returns a detailed customization plan with specific recommendations.
    """
    logfire.info(
        "Starting analyze-and-plan workflow",
        resume_id=request.resume_id,
        job_id=request.job_description_id,
        customization_level=customization_level.name
    )

    try:
        # Get the PydanticAI optimizer service
        customization_service = get_pydanticai_optimizer_service(db)

        # Create a plan request object
        plan_request = CustomizationPlanRequest(
            resume_id=request.resume_id,
            job_description_id=request.job_description_id,
            customization_strength=customization_level,
            ats_analysis=None  # Let the service perform the basic analysis
        )

        # Generate the plan using our service
        plan = await customization_service.generate_customization_plan(plan_request)

        logfire.info(
            "Analyze-and-plan completed successfully",
            resume_id=request.resume_id,
            job_id=request.job_description_id,
            recommendation_count=len(plan.recommendations)
        )

        return plan

    except ValueError as e:
        # Handle errors for missing resources
        error_message = str(e)
        logfire.error(
            "Error in analyze-and-plan",
            error=error_message,
            resume_id=request.resume_id,
            job_id=request.job_description_id
        )

        if "not found" in error_message.lower():
            raise HTTPException(status_code=404, detail=error_message)
        else:
            raise HTTPException(status_code=400, detail=error_message)

    except Exception as e:
        # Handle unexpected errors
        logfire.error(
            "Unexpected error in analyze-and-plan",
            error=str(e),
            error_type=type(e).__name__,
            traceback=traceback.format_exception(type(e), e, e.__traceback__),
            resume_id=request.resume_id,
            job_id=request.job_description_id
        )
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred during analyze-and-plan: {str(e)}"
        )


@router.post("/analyze-content", response_model=ATSContentAnalysisResponse)
async def analyze_resume_content(
    analysis_request: ATSContentAnalysisRequest
):
    """
    Analyze resume content against a job description for ATS compatibility.

    - **resume_content**: The content of the resume to analyze
    - **job_description_content**: The content of the job description to compare against

    Returns a detailed analysis of how well the resume matches the job description.
    """
    try:
        # Perform ATS analysis directly on the content
        analysis_result = await analyze_resume_for_ats(
            analysis_request.resume_content,
            analysis_request.job_description_content
        )

        # Structure the response
        response = ATSContentAnalysisResponse(
            match_score=analysis_result["match_score"],
            matching_keywords=analysis_result["matching_keywords"],
            missing_keywords=analysis_result["missing_keywords"],
            improvements=analysis_result["improvements"],
            job_type=analysis_result.get("job_type", "default"),
            section_scores=analysis_result.get("section_scores", []),
            confidence=analysis_result.get("confidence", "medium"),
            keyword_density=analysis_result.get("keyword_density", 0.0)
        )

        return response

    except Exception as e:
        # Handle unexpected errors
        logfire.error(
            "Error analyzing resume content",
            error=str(e),
            error_type=type(e).__name__,
            traceback=traceback.format_exception(type(e), e, e.__traceback__)
        )
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred during content analysis: {str(e)}"
        )


@router.post("/analyze-content-and-plan", response_model=CustomizationPlan)
async def analyze_content_and_generate_plan(
    analysis_request: ATSContentAnalysisRequest,
    customization_level: CustomizationLevel = CustomizationLevel.BALANCED,
    db: Session = Depends(get_db)
):
    """
    Analyze resume content against a job description and generate a customization plan in one step.
    This implements the evaluator-optimizer pattern described in the Anthropic blog.

    - **resume_content**: The content of the resume to analyze
    - **job_description_content**: The content of the job description to compare against
    - **customization_level**: Strength of customization (1=conservative, 2=balanced, 3=extensive)

    Returns a detailed customization plan with specific recommendations.
    """
    logfire.info(
        "Starting content-based analyze-and-plan workflow",
        resume_length=len(analysis_request.resume_content),
        job_description_length=len(analysis_request.job_description_content),
        customization_level=customization_level.name
    )

    try:
        # Get the PydanticAI optimizer service
        customization_service = get_pydanticai_optimizer_service(db)

        # First, perform the basic analysis
        basic_analysis = await analyze_resume_for_ats(
            analysis_request.resume_content,
            analysis_request.job_description_content
        )

        # Use the customization service's public method for content-based analysis and planning
        plan = await customization_service.analyze_content_and_create_plan(
            analysis_request.resume_content,
            analysis_request.job_description_content,
            basic_analysis,
            customization_level
        )

        logfire.info(
            "Content-based analyze-and-plan completed successfully",
            recommendation_count=len(plan.recommendations)
        )

        return plan

    except Exception as e:
        # Handle unexpected errors
        logfire.error(
            "Error in content-based analyze-and-plan",
            error=str(e),
            error_type=type(e).__name__,
            traceback=traceback.format_exception(type(e), e, e.__traceback__)
        )
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred during content-based analyze-and-plan: {str(e)}"
        )
