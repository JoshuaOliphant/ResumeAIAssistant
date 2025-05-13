"""
Claude Code Resume Customization API Endpoints

This module provides API endpoints for using Claude Code to customize
resumes based on job descriptions.
"""

import os
import tempfile
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException, Query
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse

from app.db.session import get_db
from app.models import Customization
from app.schemas import (
    CustomizeResumeRequest,
    CustomizedResumeResponse,
    QueuedTaskResponse,
    TaskStatusResponse
)
from app.services.claude_code.executor import ClaudeCodeExecutor, ClaudeCodeExecutionError
from app.services.claude_code.progress_tracker import progress_tracker, progress_update_callback
from app.core import config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/claude-code", tags=["Claude Code Customization"])

# Set up the Claude Code executor with configuration
PROMPT_TEMPLATE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "new_prompt.md"
)
WORKING_DIR = os.environ.get("CLAUDE_CODE_WORKING_DIR", 
                            os.path.join(tempfile.gettempdir(), "claude_code_resume"))
os.makedirs(WORKING_DIR, exist_ok=True)


def get_claude_code_executor() -> ClaudeCodeExecutor:
    """
    Get a configured Claude Code executor instance.
    
    Returns:
        Configured ClaudeCodeExecutor
    """
    return ClaudeCodeExecutor(
        working_dir=WORKING_DIR,
        prompt_template_path=PROMPT_TEMPLATE_PATH,
        claude_cmd=os.environ.get("CLAUDE_CODE_CMD", "claude")
    )


def save_temp_file(content: str) -> str:
    """
    Save content to a temporary file.
    
    Args:
        content: Text content to save
        
    Returns:
        Path to the temporary file
    """
    fd, path = tempfile.mkstemp(dir=WORKING_DIR)
    try:
        with os.fdopen(fd, 'w') as file:
            file.write(content)
        return path
    except Exception as e:
        logger.error(f"Error saving temporary file: {str(e)}")
        raise HTTPException(status_code=500, detail="Error saving uploaded content")


def create_temp_directory() -> str:
    """
    Create a temporary directory for output files.
    
    Returns:
        Path to the temporary directory
    """
    return tempfile.mkdtemp(dir=WORKING_DIR)


def read_file(file_path: str) -> str:
    """
    Read content from a file.
    
    Args:
        file_path: Path to the file to read
        
    Returns:
        File contents as string
    """
    try:
        with open(file_path, 'r') as file:
            return file.read()
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error reading output file: {str(e)}")


@router.post("/customize-resume/", response_model=CustomizedResumeResponse)
async def customize_resume_sync(
    request: CustomizeResumeRequest,
    db: Session = Depends(get_db)
):
    """
    Customize a resume using Claude Code (synchronous version).
    
    This endpoint blocks until the customization is complete.
    
    Args:
        request: Resume customization request
        db: Database session
        
    Returns:
        Customized resume data
    """
    try:
        # Save uploaded resume to temporary file
        resume_path = save_temp_file(request.resume_content)
        
        # Save job description to temporary file
        job_description_path = save_temp_file(request.job_description)
        
        # Create output directory
        output_dir = create_temp_directory()
        output_path = os.path.join(output_dir, "new_customized_resume.md")
        
        # Initialize the Claude Code executor
        executor = get_claude_code_executor()
        
        # Execute the customization
        result = executor.customize_resume(
            resume_path=resume_path,
            job_description_path=job_description_path,
            output_path=output_path
        )
        
        # Read the output files
        customized_resume = read_file(output_path)
        summary_path = os.path.join(output_dir, "customized_resume_output.md")
        customization_summary = read_file(summary_path)
        
        # Store results in database if user is authenticated
        if request.user_id:
            db_customization = Customization(
                original_resume=request.resume_content,
                job_description=request.job_description,
                customized_resume=customized_resume,
                customization_summary=customization_summary,
                user_id=request.user_id
            )
            db.add(db_customization)
            db.commit()
            db.refresh(db_customization)
            customization_id = db_customization.id
        else:
            customization_id = None
        
        return {
            "customized_resume": customized_resume,
            "customization_summary": customization_summary,
            "customization_id": customization_id
        }
    
    except ClaudeCodeExecutionError as e:
        logger.error(f"Claude Code customization error: {str(e)}")
        
        # Check if fallback is enabled
        if config.ENABLE_FALLBACK:
            logger.info("Falling back to legacy customization service")
            return await fallback_customize_resume(request, db)
        
        # Otherwise, raise the error
        raise HTTPException(status_code=500, detail=f"Resume customization failed: {str(e)}")
    
    except Exception as e:
        logger.error(f"Unexpected error in resume customization: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
    
    finally:
        # Clean up temporary files
        try:
            if 'resume_path' in locals():
                os.unlink(resume_path)
            if 'job_description_path' in locals():
                os.unlink(job_description_path)
        except Exception as e:
            logger.warning(f"Error cleaning up temporary files: {str(e)}")


@router.post("/customize-resume/async/", response_model=QueuedTaskResponse)
async def customize_resume_async(
    request: CustomizeResumeRequest,
    db: Session = Depends(get_db)
):
    """
    Start an asynchronous resume customization task.
    
    This endpoint returns immediately with a task ID for tracking progress.
    
    Args:
        request: Resume customization request
        db: Database session
        
    Returns:
        Task ID for tracking progress
    """
    try:
        # Save uploaded resume to temporary file
        resume_path = save_temp_file(request.resume_content)
        
        # Save job description to temporary file
        job_description_path = save_temp_file(request.job_description)
        
        # Create output directory
        output_dir = create_temp_directory()
        output_path = os.path.join(output_dir, "new_customized_resume.md")
        
        # Create a task for tracking
        task = progress_tracker.create_task()
        
        # Initialize the Claude Code executor
        executor = get_claude_code_executor()
        
        # Start the customization in the background
        callback = progress_update_callback(task.task_id)
        result = executor.customize_resume_with_progress(
            resume_path=resume_path,
            job_description_path=job_description_path,
            output_path=output_path,
            progress_callback=callback
        )
        
        # Store task info in the task object for later use
        task.context = {
            "resume_path": resume_path,
            "job_description_path": job_description_path,
            "output_path": output_path,
            "output_dir": output_dir,
            "user_id": request.user_id
        }
        
        return {"task_id": task.task_id, "status": "queued"}
    
    except Exception as e:
        logger.error(f"Error starting async customization: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error starting customization: {str(e)}")


@router.get("/customize-resume/status/{task_id}", response_model=TaskStatusResponse)
async def get_customize_status(
    task_id: str,
    db: Session = Depends(get_db)
):
    """
    Get the status of an asynchronous customization task.
    
    Args:
        task_id: ID of the task to check
        db: Database session
        
    Returns:
        Current task status
    """
    task = progress_tracker.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    status_data = task.to_dict()
    
    # If task is completed, include the results
    if task.status == "completed" and task.result:
        return status_data
        
    # If task failed, include the error
    if task.status == "error":
        return status_data
    
    # Otherwise, just return the status
    return {
        "task_id": status_data["task_id"],
        "status": status_data["status"],
        "progress": status_data["progress"],
        "message": status_data["message"]
    }


@router.get("/customize-resume/result/{task_id}", response_model=CustomizedResumeResponse)
async def get_customize_result(
    task_id: str,
    db: Session = Depends(get_db)
):
    """
    Get the result of a completed customization task.
    
    Args:
        task_id: ID of the completed task
        db: Database session
        
    Returns:
        Customization results if task is complete
    """
    task = progress_tracker.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status != "completed":
        raise HTTPException(
            status_code=400, 
            detail=f"Task is not completed. Current status: {task.status}"
        )
    
    if not task.result:
        # Task completed but no result available, try to load it
        try:
            context = getattr(task, "context", {})
            output_path = context.get("output_path")
            output_dir = context.get("output_dir")
            user_id = context.get("user_id")
            
            if not output_path or not os.path.exists(output_path):
                raise HTTPException(status_code=404, detail="Result files not found")
            
            # Read the output files
            customized_resume = read_file(output_path)
            summary_path = os.path.join(output_dir, "customized_resume_output.md")
            customization_summary = read_file(summary_path)
            
            # Store in database if user is authenticated
            customization_id = None
            if user_id:
                resume_path = context.get("resume_path")
                job_description_path = context.get("job_description_path")
                
                original_resume = read_file(resume_path)
                job_description = read_file(job_description_path)
                
                db_customization = Customization(
                    original_resume=original_resume,
                    job_description=job_description,
                    customized_resume=customized_resume,
                    customization_summary=customization_summary,
                    user_id=user_id
                )
                db.add(db_customization)
                db.commit()
                db.refresh(db_customization)
                customization_id = db_customization.id
            
            task.result = {
                "customized_resume": customized_resume,
                "customization_summary": customization_summary,
                "customization_id": customization_id
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving task result for {task_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error retrieving result: {str(e)}")
    
    return task.result


async def fallback_customize_resume(
    request: CustomizeResumeRequest,
    db: Session
) -> CustomizedResumeResponse:
    """
    Fallback to the legacy customization service if Claude Code fails.
    
    Args:
        request: Resume customization request
        db: Database session
        
    Returns:
        Customized resume data from legacy service
    """
    # Import the legacy service only when needed to avoid circular imports
    from app.services.customization_service import customize_resume as legacy_customize
    
    # Call the legacy service
    result = await legacy_customize(request.resume_content, request.job_description)
    
    # Store in database if user is authenticated
    customization_id = None
    if request.user_id:
        db_customization = Customization(
            original_resume=request.resume_content,
            job_description=request.job_description,
            customized_resume=result["customized_resume"],
            customization_summary=result["customization_summary"],
            user_id=request.user_id
        )
        db.add(db_customization)
        db.commit()
        db.refresh(db_customization)
        customization_id = db_customization.id
    
    return {
        "customized_resume": result["customized_resume"],
        "customization_summary": result["customization_summary"],
        "customization_id": customization_id,
        "is_fallback": True
    }