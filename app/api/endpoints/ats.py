"""
API endpoints for ATS resume analysis.
"""

import logfire
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.job import JobDescription
from app.models.resume import Resume
from app.models.user import User
from app.core.security import get_optional_current_user
from app.schemas.ats import ATSAnalysisRequest, ATSAnalysisResponse

router = APIRouter()


@router.post("/analyze", response_model=ATSAnalysisResponse)
async def analyze_resume(
    request: ATSAnalysisRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_current_user),
):
    """
    Analyze a resume for ATS compatibility with a job description.
    
    Args:
        request: ATSAnalysisRequest with resume_id and job_description_id
        db: Database session
        current_user: Current user (optional)
        
    Returns:
        ATSAnalysisResponse with analysis results
    """
    try:
        # Check if resume exists
        resume = db.query(Resume).filter(Resume.id == request.resume_id).first()
        if not resume:
            logfire.warning(
                "Resume not found for ATS analysis",
                resume_id=request.resume_id,
                user_id=current_user.id if current_user else None
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found"
            )
            
        # Check if job description exists
        job = db.query(JobDescription).filter(JobDescription.id == request.job_description_id).first()
        if not job:
            logfire.warning(
                "Job description not found for ATS analysis",
                job_id=request.job_description_id,
                user_id=current_user.id if current_user else None
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job description not found"
            )
            
        # Check permissions
        if resume.user_id and current_user and resume.user_id != current_user.id:
            logfire.warning(
                "User not authorized to access resume for ATS analysis",
                resume_id=request.resume_id,
                user_id=current_user.id if current_user else None,
                resume_user_id=resume.user_id
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this resume"
            )
            
        if job.user_id and current_user and job.user_id != current_user.id:
            logfire.warning(
                "User not authorized to access job description for ATS analysis",
                job_id=request.job_description_id,
                user_id=current_user.id if current_user else None,
                job_user_id=job.user_id
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this job description"
            )
            
        # Log the analysis request
        logfire.info(
            "Starting ATS analysis",
            resume_id=request.resume_id,
            job_id=request.job_description_id,
            user_id=current_user.id if current_user else None
        )
        
        # Use the pydanticai_service to perform the analysis
        # This is a placeholder implementation
        # In a real implementation, this would use PydanticAI to analyze the resume
        from app.services.pydanticai_optimizer import get_pydanticai_optimizer_service
        
        # Get the PydanticAI service
        pydanticai_service = get_pydanticai_optimizer_service(db)
        
        # Run the analysis
        result = await pydanticai_service.analyze_resume_ats(
            resume_id=request.resume_id,
            job_id=request.job_description_id
        )
        
        # Return the response
        return ATSAnalysisResponse(
            resume_id=request.resume_id,
            job_description_id=request.job_description_id,
            match_score=result.get("match_score", 75),
            missing_keywords=result.get("missing_keywords", ["python", "react"]),
            keyword_matches=result.get("keyword_matches", {"python": True, "javascript": False}),
            section_scores=result.get("section_scores", {"experience": 85, "education": 90}),
            improvement_suggestions=result.get("improvement_suggestions", [
                "Add more specific technical skills",
                "Quantify your achievements"
            ])
        )
            
    except Exception as e:
        logfire.error(
            "Error performing ATS analysis",
            resume_id=request.resume_id,
            job_id=request.job_description_id,
            error=str(e),
            error_type=type(e).__name__,
            traceback=logfire.format_exception(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error performing ATS analysis: {str(e)}"
        )