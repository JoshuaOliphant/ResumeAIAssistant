"""
API endpoints for resume customization.

This module provides endpoints for resume customization, redirecting to the
Claude Code implementation for improved customization.
"""

import os
import uuid
import tempfile
import logfire
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.job import JobDescription
from app.models.resume import Resume, ResumeVersion
from app.schemas.customize import (
    ResumeCustomizationRequest,
    ResumeCustomizationResponse,
)
from app.schemas.claude_code import (
    CustomizeResumeRequest as ClaudeCodeCustomizeRequest,
)

# Import the Claude Code service
from app.services.claude_code.executor import ClaudeCodeExecutor

router = APIRouter()

# Set up paths for Claude Code executor
PROMPT_TEMPLATE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    "new_prompt.md"
)
WORKING_DIR = os.environ.get("CLAUDE_CODE_WORKING_DIR", 
                            os.path.join(tempfile.gettempdir(), "claude_code_resume"))
os.makedirs(WORKING_DIR, exist_ok=True)

# Initialize the Claude Code executor with required parameters
claude_code_executor = ClaudeCodeExecutor(
    working_dir=WORKING_DIR,
    prompt_template_path=PROMPT_TEMPLATE_PATH,
    claude_cmd=os.environ.get("CLAUDE_CODE_CMD", "claude")
)


@router.post("/", response_model=ResumeCustomizationResponse)
async def customize_resume_endpoint(
    customization_request: ResumeCustomizationRequest,
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db)
):
    """
    Customize a resume for a specific job description using Claude Code.

    This endpoint is a wrapper that redirects to the Claude Code implementation
    for improved resume customization.

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
        "Starting resume customization with Claude Code",
        resume_id=customization_request.resume_id,
        job_id=customization_request.job_description_id,
        customization_level=customization_request.customization_strength.name,
    )

    # Redirect to Claude Code API
    from app.api.endpoints.claude_code import customize_resume_sync

    # Create a Claude Code request from the standard request
    claude_request = ClaudeCodeCustomizeRequest(
        resume_content=resume_version.content,
        job_description=job.description,
        user_id=customization_request.user_id if hasattr(customization_request, 'user_id') else None
    )

    # Call the Claude Code endpoint
    try:
        result = await customize_resume_sync(claude_request, db)
        
        # Return the standardized response
        response = ResumeCustomizationResponse(
            original_resume_id=customization_request.resume_id,
            customized_resume_id=customization_request.resume_id,
            job_description_id=customization_request.job_description_id,
        )
        
        return response
        
    except Exception as e:
        logfire.error(
            "Error during Claude Code customization",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Error during resume customization: {str(e)}"
        )


@router.post("/plan")
async def generate_customization_plan(
    plan_request: dict, db: Session = Depends(get_db)
):
    """
    This endpoint is deprecated and now redirects to the Claude Code implementation.
    
    Claude Code provides a complete customization solution that includes planning
    and implementation in a single workflow.
    
    Please use the /customize endpoint instead.
    """
    return JSONResponse(
        status_code=301,
        content={
            "message": "This endpoint is deprecated. Please use /api/v1/customize instead.",
            "redirect": "/api/v1/customize"
        }
    )


@router.post("/parallel")
async def generate_customization_plan_parallel(plan_request: dict, db: Session = Depends(get_db)):
    """
    This endpoint is deprecated and now redirects to the Claude Code implementation.
    
    Claude Code provides a complete customization solution that handles parallel
    processing internally for optimal performance.
    
    Please use the /customize endpoint instead.
    """
    return JSONResponse(
        status_code=301,
        content={
            "message": "This endpoint is deprecated. Please use /api/v1/customize instead.",
            "redirect": "/api/v1/customize"
        }
    )
