"""
Claude Code Resume Customization API Endpoints

This module provides REST API endpoints for resume customization using Claude Code SDK,
supporting both synchronous and asynchronous operations.
"""

import logging
import os
import tempfile
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

# from app.api import deps
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.claude_code import (
    ClaudeCodeCustomizeRequest,
    ClaudeCodeCustomizeResponse,
    QueuedTaskResponse,
    TaskStatusResponse,
)
from app.services.claude_code.executor import (
    ClaudeCodeExecutionError,
    get_claude_code_executor,
)
from app.services.claude_code.progress_tracker import progress_tracker

# Configure logging
logger = logging.getLogger(__name__)

# Create the API router
router = APIRouter()


def save_temp_file(content: str) -> str:
    """Save content to a temporary file and return the path."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        f.write(content)
        return f.name


def create_temp_directory() -> str:
    """Create a temporary directory and return the path."""
    return tempfile.mkdtemp()


def read_file(file_path: str) -> str:
    """Read content from a file."""
    try:
        with open(file_path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return ""
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {str(e)}")
        return ""


@router.post("/customize-resume", response_model=ClaudeCodeCustomizeResponse)
async def customize_resume(
    request: ClaudeCodeCustomizeRequest,
    x_operation_timeout: Optional[int] = Header(None, ge=60, le=1800),  # 1-30 min range
    x_operation_id: Optional[str] = Header(None),  # Operation ID for tracking
    db: Session = Depends(get_db),
    # current_user: User = Depends(deps.get_current_user),
):
    """
    Synchronously customize a resume using Claude Code.

    This endpoint executes the customization synchronously and returns the result directly.
    For long-running operations, consider using the async endpoint instead.

    Args:
        request: Resume and job description for customization
        x_operation_timeout: Optional custom timeout in seconds (60-1800s, default: 900s)
        x_operation_id: Optional operation ID for tracking/logging
        db: Database session

    Returns:
        Customized resume and summary

    Note: This endpoint may timeout for complex resumes. Use the async version for reliability.
    """
    try:
        # Log request info
        logger.info("Starting Claude Code resume customization")
        logger.info(
            f"Request received - operation_timeout: {x_operation_timeout}, operation_id: {x_operation_id}"
        )

        # Create a simple request object with the expected fields
        from app.schemas.resume import CustomizeResumeRequest

        # Convert to the expected schema
        customize_request = CustomizeResumeRequest(
            resume_id=request.resume_id,
            job_id=request.job_id,
            user_id=request.user_id,
            resume_content=request.resume_content,
            job_description=request.job_description,
        )

        # Get timeout from header or use default from settings
        if x_operation_timeout:
            timeout_seconds = min(x_operation_timeout, settings.CLAUDE_CODE_MAX_TIMEOUT)
            logger.info(f"Using custom timeout: {timeout_seconds} seconds")
        else:
            timeout_seconds = 1800  # Use 30-minute default
            logger.info(f"Using default timeout: {timeout_seconds} seconds")

        # Check if we have an operation ID from the header parameter
        if x_operation_id:
            # Use the client-provided operation ID
            task_id = x_operation_id
            logger.info(f"Using client-provided operation ID: {task_id}")
        else:
            # Generate a new task ID for logging
            task_id = str(uuid.uuid4())
            logger.info(f"Generated new task ID: {task_id}")

        logger.info(f"Starting synchronous customization with task ID: {task_id}")

        # Save uploaded resume to temporary file
        resume_path = save_temp_file(request.resume_content)

        # Save job description to temporary file
        job_description_path = save_temp_file(request.job_description)

        # Create output directory
        output_dir = create_temp_directory()
        output_path = os.path.join(output_dir, "new_customized_resume.md")

        # Initialize the Claude Code executor
        executor = get_claude_code_executor()

        # Set up a progress tracker task for this operation
        # Get or create task using the task ID
        task = progress_tracker.get_task(task_id)
        if not task:
            # Create new task if it doesn't exist
            logger.info(f"Creating new progress tracker task with ID: {task_id}")
            task = progress_tracker.create_task()
            task.task_id = task_id  # Explicitly set the task ID

            # Log confirmation of task creation
            logger.info(f"Task created with ID: {task.task_id}")
            # Verify task is properly registered
            if not progress_tracker.get_task(task_id):
                logger.warning(
                    "Task verification failed - newly created task not found!"
                )
        else:
            logger.info(f"Using existing progress tracker task with ID: {task_id}")

        # Execute the customization with logs and timeout
        result = executor.customize_resume(
            resume_path=resume_path,
            job_description_path=job_description_path,
            output_path=output_path,
            task_id=task_id,
            timeout=timeout_seconds,
        )

        # Read the output files
        customized_resume = read_file(output_path)
        summary_path = os.path.join(output_dir, "customized_resume_output.md")
        customization_summary = read_file(summary_path)

        # Results are stored in the output directory for now
        # Future: Consider storing customization metadata in a simplified model
        customization_id = None

        # Mark task as completed
        task.status = "completed"
        task.result = {
            "customized_resume": customized_resume,
            "customization_summary": customization_summary,
            "customization_id": customization_id,
        }

        return {
            "customized_resume": customized_resume,
            "customization_summary": customization_summary,
            "customization_id": customization_id,
        }

    except ClaudeCodeExecutionError as e:
        logger.error(f"Claude Code customization error: {str(e)}")
        # Log to console for real-time visibility
        print(f"[ERROR] Claude Code customization failed: {str(e)}")

        # Check if this is a timeout error
        if "timeout" in str(e).lower():
            # Return a specific timeout error
            raise HTTPException(
                status_code=408, detail=f"Claude Code execution timed out: {str(e)}"
            )

        # Raise the error - no fallback available
        raise HTTPException(
            status_code=500, detail=f"Resume customization failed: {str(e)}"
        )

    except Exception as e:
        logger.error(f"Unexpected error in resume customization: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

    finally:
        # Clean up temporary files
        try:
            if "resume_path" in locals():
                os.unlink(resume_path)
            if "job_description_path" in locals():
                os.unlink(job_description_path)
        except Exception as e:
            logger.warning(f"Error cleaning up temporary files: {str(e)}")


@router.post("/customize-resume/async/", response_model=QueuedTaskResponse)
async def customize_resume_async(
    request: ClaudeCodeCustomizeRequest,
    x_operation_timeout: Optional[int] = Header(None, ge=60, le=1800),  # 1-30 min range
    x_operation_id: Optional[str] = Header(None),  # Operation ID for tracking
    db: Session = Depends(get_db),
):
    """
    Start an asynchronous resume customization task.

    This endpoint returns immediately with a task ID for tracking progress.
    Uses a default timeout of 900 seconds (15 minutes).

    Args:
        request: Resume customization request
        x_operation_timeout: Optional custom timeout in seconds (60-1800s, default: 900s)
        db: Database session

    Returns:
        Task ID for tracking progress
    """
    try:
        # Get timeout from header or use default
        timeout_seconds = x_operation_timeout or 1800  # 30-minute default
        logger.info(f"Starting async customization with timeout: {timeout_seconds}s")

        # Save uploaded resume to temporary file
        resume_path = save_temp_file(request.resume_content)

        # Save job description to temporary file
        job_description_path = save_temp_file(request.job_description)

        # Create output directory
        output_dir = create_temp_directory()
        output_path = os.path.join(output_dir, "new_customized_resume.md")

        # Create a task for tracking if ID provided
        task_id = x_operation_id
        if task_id:
            # Use existing task ID if provided
            task = progress_tracker.get_task(task_id)
            if not task:
                task = progress_tracker.create_task()
                task.task_id = task_id
                logger.info(f"Created task with provided ID: {task_id}")
        else:
            # Let executor create the task
            task_id = None
            logger.info("Will let executor create new task ID")

        # Initialize the Claude Code executor
        executor = get_claude_code_executor()
        
        # Use the executor's built-in async support
        result = executor.customize_resume_with_progress(
            resume_path=resume_path,
            job_description_path=job_description_path,
            output_path=output_path,
            timeout=timeout_seconds
        )
        
        # The executor handles everything in the background
        return {"task_id": result["task_id"], "status": "processing"}

    except Exception as e:
        logger.error(f"Error starting async customization: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error starting customization: {str(e)}"
        )


@router.get("/customize-resume/status/{task_id}", response_model=TaskStatusResponse)
async def get_customize_status(
    task_id: str,
    include_logs: bool = Query(True),
    max_logs: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """
    Get the status of an asynchronous customization task.

    Args:
        task_id: ID of the task to check
        include_logs: Whether to include logs in the response (default: True)
        max_logs: Maximum number of log lines to include (default: 50)
        db: Database session

    Returns:
        Current task status with log information
    """
    task = progress_tracker.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Get the basic task information
    status_data = task.to_dict()

    # Get logs from the log streamer
    from app.services.claude_code.log_streamer import get_log_streamer

    log_streamer = get_log_streamer()

    # Get logs if requested
    response_data = {
        "task_id": status_data["task_id"],
        "status": status_data["status"],
        "message": status_data["message"],
        "updated_at": status_data["updated_at"],
        "created_at": status_data["created_at"],
    }

    # Include error info if present
    if status_data.get("error"):
        response_data["error"] = status_data["error"]

    if include_logs:
        logs = log_streamer.get_logs(task_id, max_logs=max_logs)
        response_data["logs"] = logs

    # Include result info if task is completed
    if status_data["status"] == "completed" and status_data.get("result"):
        response_data["result"] = status_data["result"]

    return response_data


import threading


# Convenience wrapper for the sync endpoint to provide task-like response
@router.post("/customize-resume/", response_model=QueuedTaskResponse)
async def customize_resume_with_task(
    request: ClaudeCodeCustomizeRequest,
    x_operation_timeout: Optional[int] = Header(None, ge=60, le=1800),
    x_operation_id: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """
    Customize a resume with task tracking.

    This is a convenience endpoint that wraps the sync endpoint to provide
    consistent task-based responses. It immediately starts the customization
    and returns a task ID.

    Args:
        request: Resume customization request
        x_operation_timeout: Optional custom timeout in seconds
        x_operation_id: Optional operation ID for tracking
        db: Database session

    Returns:
        Task ID for tracking progress
    """
    # Simply delegate to the async endpoint which provides task tracking
    return await customize_resume_async(
        request=request,
        x_operation_timeout=x_operation_timeout,
        x_operation_id=x_operation_id,
        db=db,
    )
