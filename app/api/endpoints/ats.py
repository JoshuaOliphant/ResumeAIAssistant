from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.resume import Resume, ResumeVersion
from app.models.job import JobDescription
from app.schemas.ats import ATSAnalysisRequest, ATSAnalysisResponse
from app.services.ats_service import analyze_resume_for_ats

router = APIRouter()


@router.post("/analyze", response_model=ATSAnalysisResponse)
async def analyze_resume(
    analysis_request: ATSAnalysisRequest,
    db: Session = Depends(get_db)
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
        keyword_density=analysis_result.get("keyword_density", 0.0)
    )
    
    return response
