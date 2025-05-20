"""
Claude Code Resume Customization API Endpoints

This module provides API endpoints for using Claude Code to customize
resumes based on job descriptions.
"""

import os
import uuid
import json
import tempfile
import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException, Query, Header
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse, StreamingResponse
import asyncio
import queue

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
from app.core.config import settings

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
    x_operation_timeout: Optional[int] = Header(None, ge=60, le=1800),  # 1-30 min range
    x_operation_id: Optional[str] = Header(None),  # Operation ID for tracking
    db: Session = Depends(get_db)
):
    """
    Customize a resume using Claude Code (synchronous version).
    
    This endpoint blocks until the customization is complete.
    Uses a default timeout of 900 seconds (15 minutes).
    
    Args:
        request: Resume customization request
        x_operation_timeout: Optional custom timeout in seconds (60-1800s, default: 900s)
        db: Database session
        
    Returns:
        Customized resume data
    """
    try:
        # Import settings to get configured timeout values
        from app.core.config import settings
        
        # Get timeout from header or use default from settings
        # If no header specified, use default from settings
        # If header specified, validate against max allowed timeout
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
                logger.warning(f"Task verification failed - newly created task not found!")
        else:
            logger.info(f"Using existing progress tracker task with ID: {task_id}")
        
        # Execute the customization with logs and timeout
        result = executor.customize_resume(
            resume_path=resume_path,
            job_description_path=job_description_path,
            output_path=output_path,
            task_id=task_id,
            timeout=timeout_seconds
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
        
        # Mark task as completed
        task.status = "completed"
        task.result = {
            "customized_resume": customized_resume,
            "customization_summary": customization_summary,
            "customization_id": customization_id
        }
        
        return {
            "customized_resume": customized_resume,
            "customization_summary": customization_summary,
            "customization_id": customization_id
        }
    
    except ClaudeCodeExecutionError as e:
        logger.error(f"Claude Code customization error: {str(e)}")
        # Log to console for real-time visibility
        print(f"[ERROR] Claude Code customization failed: {str(e)}")
        
        # Check if this is a timeout error
        if "timeout" in str(e).lower():
            # Return a specific timeout error
            raise HTTPException(status_code=408, detail=f"Claude Code execution timed out: {str(e)}")
        
        # Check if fallback is enabled
        if settings.ENABLE_FALLBACK:
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
    x_operation_timeout: Optional[int] = Header(None, ge=60, le=1800),  # 1-30 min range
    x_operation_id: Optional[str] = Header(None),  # Operation ID for tracking
    db: Session = Depends(get_db)
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
        # Import settings to get configured timeout values
        from app.core.config import settings
        
        # Get timeout from header or use default from settings
        if x_operation_timeout:
            timeout_seconds = min(x_operation_timeout, settings.CLAUDE_CODE_MAX_TIMEOUT)
            logger.info(f"Using custom timeout: {timeout_seconds} seconds")
        else:
            timeout_seconds = 1800  # Use 30-minute default
            logger.info(f"Using default timeout: {timeout_seconds} seconds")
            
        # Use operation ID if provided
        task_id = None
        if x_operation_id:
            task_id = x_operation_id
            logger.info(f"Using client-provided operation ID: {task_id}")
            
        # Log request info
        logger.info(f"Starting async customization with timeout: {timeout_seconds}s")
        
        # Save uploaded resume to temporary file
        resume_path = save_temp_file(request.resume_content)
        
        # Save job description to temporary file
        job_description_path = save_temp_file(request.job_description)
        
        # Create output directory
        output_dir = create_temp_directory()
        output_path = os.path.join(output_dir, "new_customized_resume.md")
        
        # Create a task for tracking
        if task_id:
            # Use existing task ID if provided
            task = progress_tracker.get_task(task_id)
            if not task:
                logger.info(f"Creating new progress tracker task with provided ID: {task_id}")
                task = progress_tracker.create_task()
                task.task_id = task_id
                
                # Log confirmation of task creation
                logger.info(f"Task created with provided ID: {task.task_id}")
                # Verify task is properly registered
                if not progress_tracker.get_task(task_id):
                    logger.warning(f"Task verification failed - newly created task not found!")
            else:
                logger.info(f"Using existing progress tracker task with ID: {task_id}")
        else:
            # Create a new task with a generated ID
            task = progress_tracker.create_task()
            logger.info(f"Created new task with generated ID: {task.task_id}")
        
        # Initialize the Claude Code executor
        executor = get_claude_code_executor()
        
        # Start the customization in the background
        callback = progress_update_callback(task.task_id)
        result = executor.customize_resume_with_progress(
            resume_path=resume_path,
            job_description_path=job_description_path,
            output_path=output_path,
            progress_callback=callback,
            timeout=timeout_seconds
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
    include_logs: bool = Query(False),
    db: Session = Depends(get_db)
):
    """
    Get the status of an asynchronous customization task.
    
    Args:
        task_id: ID of the task to check
        include_logs: Whether to include logs in the response
        db: Database session
        
    Returns:
        Current task status
    """
    task = progress_tracker.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    status_data = task.to_dict()
    
    # If logs are requested, add them to the response
    if include_logs:
        # Import the log streamer to get logs
        from app.services.claude_code.log_streamer import get_log_streamer
        log_streamer = get_log_streamer()
        logs = log_streamer.get_logs(task_id)
        
        # Add logs to the response
        status_data["logs"] = logs
    
    # If task is completed, include the results
    if task.status == "completed" and task.result:
        return status_data
        
    # If task failed, include the error
    if task.status == "error":
        return status_data
    
    # Otherwise, just return the status
    response_data = {
        "task_id": status_data["task_id"],
        "status": status_data["status"],
        "progress": status_data["progress"],
        "message": status_data["message"]
    }
    
    # Include logs if requested
    if include_logs and "logs" in status_data:
        response_data["logs"] = status_data["logs"]
    
    return response_data

@router.get("/customize-resume/logs/{task_id}")
async def get_customize_logs(
    task_id: str,
    db: Session = Depends(get_db)
):
    """
    Get the execution logs for a customization task.
    
    Args:
        task_id: ID of the task to get logs for
        db: Database session
        
    Returns:
        List of log entries for the task
    """
    # Check if the task exists
    task = progress_tracker.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Import the log streamer
    from app.services.claude_code.log_streamer import get_log_streamer
    log_streamer = get_log_streamer()
    
    # Get logs for the task
    logs = log_streamer.get_logs(task_id)
    
    # Return the logs
    return {"task_id": task_id, "logs": logs}

@router.get("/customize-resume/logs/{task_id}/stream")
async def stream_customize_logs(
    task_id: str,
    max_duration: Optional[int] = Query(3600, ge=10, le=86400, description="Maximum stream duration in seconds"),
    format: Optional[str] = Query("sse", description="Output format: 'sse' for Server-Sent Events or 'json' for direct JSON streaming"),
    db: Session = Depends(get_db)
):
    """
    Stream logs for a customization task as they arrive in real-time.
    
    Args:
        task_id: ID of the task to stream logs for
        max_duration: Maximum duration to stream logs (10s to 24h, default: 1h)
        format: Output format, either 'sse' (default) or 'json'
        db: Database session
        
    Returns:
        Streaming response with logs as they arrive
    """
    # Check if the task exists
    task = progress_tracker.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Import the log streamer
    from app.services.claude_code.log_streamer import get_log_streamer
    log_streamer = get_log_streamer()
    
    # Set up streaming response based on format
    if format.lower() == "sse":
        # Server-Sent Events format
        async def sse_generator():
            # Yield initial logs
            logs = log_streamer.get_logs(task_id)
            yield "data: " + json.dumps({"task_id": task_id, "logs": logs, "status": task.status}) + "\n\n"
            
            # Stream logs as they arrive using the enhanced streamer
            try:
                async for log in log_streamer.stream_logs(task_id, timeout=max_duration):
                    # If log is a dict, it's a structured log
                    if isinstance(log, dict):
                        yield "data: " + json.dumps({
                            "task_id": task_id, 
                            "new_log": log.get("formatted_message", str(log)),
                            "log_data": log
                        }) + "\n\n"
                    else:
                        # Plain text log
                        yield "data: " + json.dumps({"task_id": task_id, "new_log": log}) + "\n\n"
                    
                    # Add heartbeat comment every 10 logs to keep connection alive
                    yield ": heartbeat\n\n"
                
                # At end of stream, yield final state
                logs = log_streamer.get_logs(task_id)
                yield "data: " + json.dumps({
                    "task_id": task_id, 
                    "logs": logs, 
                    "status": task.status,
                    "completed": True
                }) + "\n\n"
                
            except Exception as e:
                logger.error(f"Error in SSE log stream for task {task_id}: {str(e)}")
                yield "data: " + json.dumps({"error": str(e)}) + "\n\n"
        
        # Return SSE streaming response
        return StreamingResponse(
            sse_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Disable proxy buffering
            }
        )
        
    else:
        # Direct JSON streaming
        async def json_generator():
            # Stream logs as they arrive using the enhanced streamer
            try:
                # Start with task info and existing logs
                yield json.dumps({
                    "task_id": task_id,
                    "status": task.status,
                    "logs": log_streamer.get_logs(task_id),
                    "type": "init"
                })
                
                # Stream new logs as they arrive
                async for log in log_streamer.stream_logs(task_id, timeout=max_duration):
                    # If log is a dict, it's a structured log
                    if isinstance(log, dict):
                        yield json.dumps({
                            "task_id": task_id,
                            "log": log,
                            "type": "log"
                        })
                    else:
                        # Plain text log
                        yield json.dumps({
                            "task_id": task_id,
                            "log": log,
                            "type": "log"
                        })
                
                # Final state
                yield json.dumps({
                    "task_id": task_id,
                    "status": task.status,
                    "type": "complete"
                })
                
            except Exception as e:
                logger.error(f"Error in JSON log stream for task {task_id}: {str(e)}")
                yield json.dumps({"error": str(e), "type": "error"})
        
        # Return JSON lines streaming response
        return StreamingResponse(
            json_generator(),
            media_type="application/json-seq",
            headers={"Cache-Control": "no-cache"}
        )


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


@router.post("/customize-resume/content", response_model=CustomizedResumeResponse)
async def customize_content(
    request: CustomizeResumeRequest,
    x_operation_timeout: Optional[int] = Header(None, ge=60, le=1800),  # 1-30 min range
    x_operation_id: Optional[str] = Header(None),  # Operation ID for tracking
    db: Session = Depends(get_db)
):
    """
    Customize a resume using Claude Code with direct content (no storage).
    
    This endpoint accepts resume and job description content directly,
    without requiring them to be stored in the database first.
    Uses a default timeout of 900 seconds (15 minutes).
    
    Args:
        request: Resume customization request with content
        x_operation_timeout: Optional custom timeout in seconds (60-1800s, default: 900s)
        db: Database session
        
    Returns:
        Customized resume data
    """
    try:
        # Import settings to get configured timeout values
        from app.core.config import settings
        
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
            
        logger.info(f"Starting content customization with task ID: {task_id}")
        
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
        task = progress_tracker.get_task(task_id)
        if not task:
            # Create new task if it doesn't exist
            task = progress_tracker.create_task()
            task.task_id = task_id
        
        # Execute the customization
        result = executor.customize_resume(
            resume_path=resume_path,
            job_description_path=job_description_path,
            output_path=output_path,
            task_id=task_id,
            timeout=timeout_seconds
        )
        
        # Read the output files
        customized_resume = read_file(output_path)
        summary_path = os.path.join(output_dir, "customized_resume_output.md")
        customization_summary = read_file(summary_path)
        
        # Return the results without storing in the database
        return {
            "customized_resume": customized_resume,
            "customization_summary": customization_summary,
            "customization_id": None,
            "is_fallback": False
        }
    
    except ClaudeCodeExecutionError as e:
        logger.error(f"Claude Code customization error: {str(e)}")
        # Log to console for real-time visibility
        print(f"[ERROR] Claude Code content customization failed: {str(e)}")
        
        # Check if this is a timeout error
        if "timeout" in str(e).lower():
            # Return a specific timeout error
            raise HTTPException(status_code=408, detail=f"Claude Code execution timed out: {str(e)}")
            
        # Check if fallback is enabled
        if settings.ENABLE_FALLBACK:
            logger.info("Falling back to legacy customization service")
            return await fallback_customize_resume(request, db)
        
        # Otherwise, raise the error
        raise HTTPException(status_code=500, detail=f"Resume customization failed: {str(e)}")
    
    except Exception as e:
        logger.error(f"Unexpected error in content customization: {str(e)}")
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