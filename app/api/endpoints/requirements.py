from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import logfire
from app.core.security import get_optional_current_user
from app.db.session import get_db
from app.models.job import JobDescription
from app.models.user import User
from app.schemas.requirements import (
    KeyRequirementsRequest,
    KeyRequirementsContentRequest,
    KeyRequirementsResponse,
    KeyRequirements
)
from app.services.requirements_extractor import (
    extract_key_requirements, 
    extract_key_requirements_from_content
)

router = APIRouter()


@router.post(
    "/extract", 
    response_model=KeyRequirementsResponse, 
    status_code=status.HTTP_200_OK
)
async def extract_requirements(
    request: KeyRequirementsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_current_user),
):
    """
    Extract key requirements from a job description.
    
    Args:
        request: KeyRequirementsRequest with job_description_id
        db: Database session
        current_user: Optional current user
        
    Returns:
        KeyRequirementsResponse with extracted requirements
    """
    try:
        # Check if job description exists and user has access
        job = db.query(JobDescription).filter(JobDescription.id == request.job_description_id).first()
        if not job:
            logfire.warning(
                "Job description not found", 
                job_id=request.job_description_id,
                user_id=current_user.id if current_user else None
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job description not found"
            )
        
        # Check if user has access to job description
        if job.user_id:
            if not current_user or job.user_id != current_user.id:
                logfire.warning(
                    "User not authorized to access job description",
                    job_id=request.job_description_id,
                    user_id=current_user.id if current_user else None,
                    job_user_id=job.user_id
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to access this job description"
                )
        
        # Log extraction request
        logfire.info(
            "Extracting key requirements",
            job_id=request.job_description_id,
            user_id=current_user.id if current_user else None
        )
        
        # Extract key requirements using the service
        requirements = await extract_key_requirements(
            job_description_id=request.job_description_id,
            db=db
        )
        
        # Create response
        response = KeyRequirementsResponse(
            job_description_id=request.job_description_id,
            job_title=requirements.job_title,
            company=requirements.company,
            job_type=requirements.job_type,
            categories=requirements.categories,
            keywords=requirements.keywords,
            confidence=requirements.confidence,
            total_requirements_count=requirements.total_requirements_count
        )
        
        logfire.info(
            "Key requirements extraction completed",
            job_id=request.job_description_id,
            requirement_count=requirements.total_requirements_count,
            confidence=requirements.confidence
        )
        
        return response
        
    except Exception as e:
        logfire.error(
            "Error extracting key requirements",
            job_id=request.job_description_id,
            error=str(e),
            error_type=type(e).__name__,
            traceback=logfire.format_exception(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error extracting key requirements: {str(e)}"
        )


@router.post(
    "/extract-from-content",
    response_model=KeyRequirementsResponse,
    status_code=status.HTTP_200_OK
)
async def extract_requirements_from_content(
    request: KeyRequirementsContentRequest,
    current_user: User = Depends(get_optional_current_user),
):
    """
    Extract key requirements from job description content.
    
    Args:
        request: KeyRequirementsContentRequest with content
        
    Returns:
        KeyRequirements with extracted requirements
    """
    try:
        logfire.info(
            "Extracting key requirements from content",
            content_length=len(request.job_description_content)
        )
        
        # Extract key requirements using the service
        requirements = await extract_key_requirements_from_content(
            job_description_content=request.job_description_content,
            job_title=request.job_title,
            company=request.company
        )
        
        # Create response with specified job_description_id (use a placeholder)
        response = KeyRequirementsResponse(
            job_description_id="from_content",
            job_title=requirements.job_title,
            company=requirements.company,
            job_type=requirements.job_type,
            categories=requirements.categories,
            keywords=requirements.keywords,
            confidence=requirements.confidence,
            total_requirements_count=requirements.total_requirements_count
        )
        
        logfire.info(
            "Key requirements extraction from content completed",
            requirement_count=requirements.total_requirements_count,
            confidence=requirements.confidence
        )
        
        return response
        
    except Exception as e:
        logfire.error(
            "Error extracting key requirements from content",
            content_length=len(request.job_description_content) if request.job_description_content else 0,
            error=str(e),
            error_type=type(e).__name__,
            traceback=logfire.format_exception(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error extracting key requirements from content: {str(e)}"
        )