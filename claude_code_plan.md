# Claude Code Integration Plan for ResumeAI Assistant

## Overview

This document outlines a comprehensive plan to replace the existing AI model workflow in the ResumeAI Assistant application with Claude Code, leveraging its command-line capabilities to implement the advanced resume customization system defined in `new_prompt.md`.

## Current Challenges

- Complex workflows with multiple LLMs are difficult to manage
- PydanticAI implementation is not working effectively
- Parallel processing logic is complicated
- Truthfulness verification is challenging

## Proposed Solution Architecture

The solution will use Claude Code as a subprocess-driven agent that implements the evaluator-optimizer workflow pattern from `new_prompt.md` while leveraging Claude Code's command-line capabilities, thinking tools, and structured approach.

### High-Level Architecture

```
┌─────────────────┐     ┌───────────────────┐     ┌───────────────────┐
│  Web/API Layer  │────►│  Resume Manager   │────►│  Claude Code      │
│  (FastAPI)      │     │  (Python Service) │     │  Agent Executor   │
└─────────────────┘     └───────────────────┘     └───────────────────┘
                                                         │
                                                         ▼
                                                ┌───────────────────┐
                                                │  Output Processor │
                                                │  & File Manager   │
                                                └───────────────────┘
```

## Implementation Details

### 1. Claude Code Executor Service

Create a Python service that manages Claude Code executions as subprocesses:

```python
class ClaudeCodeExecutor:
    def __init__(self, working_dir, prompt_template_path, claude_cmd="claude"):
        self.working_dir = working_dir
        self.prompt_template = self._load_prompt_template(prompt_template_path)
        self.claude_cmd = claude_cmd
        
    def _load_prompt_template(self, path):
        with open(path, 'r') as f:
            return f.read()
            
    def customize_resume(self, resume_path, job_description_path, output_path):
        # Prepare files and context
        temp_dir = self._create_temp_workspace()
        
        # Build the complete prompt with template and inputs
        prompt = self._build_prompt(resume_path, job_description_path)
        
        # Execute Claude Code as subprocess with our prompt
        command = [
            self.claude_cmd, 
            "--print", prompt,
            "--output-format", "json",
        ]
        
        result = subprocess.run(
            command,
            cwd=temp_dir,
            capture_output=True,
            text=True
        )
        
        # Process the output and extract results
        parsed_results = self._process_output(result.stdout)
        
        # Save and return customized resume
        return self._save_results(parsed_results, output_path)
```

### 2. Prompt Building Module

```python
def _build_prompt(self, resume_path, job_description_path):
    # Load the resume and job description contents
    with open(resume_path, 'r') as f:
        resume_content = f.read()
        
    with open(job_description_path, 'r') as f:
        job_description_content = f.read()
    
    # Create a structured prompt based on new_prompt.md
    complete_prompt = f"""
# Resume Customization Task

## Input Files
- Resume: {resume_content}
- Job Description: {job_description_content}

## Execution Instructions
{self.prompt_template}

## Expected Outputs
1. Generate customized resume in markdown format (new_customized_resume.md)
2. Create a detailed change summary (customized_resume_output.md)
3. Save all intermediate files for verification
    """
    
    return complete_prompt
```

### 3. Integration with FastAPI Backend

Update the existing API endpoint to use the Claude Code executor:

```python
@router.post("/customize-resume/", response_model=schemas.CustomizedResumeResponse)
async def customize_resume(
    request: schemas.CustomizeResumeRequest,
    db: Session = Depends(get_db)
):
    # Save uploaded resume to temporary file
    resume_path = save_temp_file(request.resume_content)
    
    # Save job description to temporary file
    job_description_path = save_temp_file(request.job_description)
    
    # Create output directory
    output_dir = create_temp_directory()
    
    # Initialize the Claude Code executor
    executor = ClaudeCodeExecutor(
        working_dir=output_dir,
        prompt_template_path="app/prompts/new_prompt.md"
    )
    
    # Execute the customization
    result = executor.customize_resume(
        resume_path=resume_path,
        job_description_path=job_description_path,
        output_path=f"{output_dir}/new_customized_resume.md"
    )
    
    # Read the output files
    customized_resume = read_file(f"{output_dir}/new_customized_resume.md")
    customization_summary = read_file(f"{output_dir}/customized_resume_output.md")
    
    # Store results in database
    db_customization = models.Customization(
        original_resume=request.resume_content,
        job_description=request.job_description,
        customized_resume=customized_resume,
        customization_summary=customization_summary,
        user_id=request.user_id
    )
    db.add(db_customization)
    db.commit()
    
    return {
        "customized_resume": customized_resume,
        "customization_summary": customization_summary,
        "customization_id": db_customization.id
    }
```

### 4. Progress Tracking System

Since Claude Code execution may take time, implement a progress tracking system:

```python
def customize_resume_with_progress(self, resume_path, job_description_path, output_path, progress_callback=None):
    # Set up progress tracking
    progress_status = {
        "status": "initializing",
        "progress": 0,
        "message": "Preparing customization process"
    }
    
    if progress_callback:
        progress_callback(progress_status)
    
    # Start Claude Code in background thread
    thread = threading.Thread(
        target=self._run_customization,
        args=(resume_path, job_description_path, output_path, progress_callback)
    )
    thread.start()
    
    return {"task_id": str(uuid.uuid4())}

def _run_customization(self, resume_path, job_description_path, output_path, progress_callback):
    try:
        # Phase 1: Research & Analysis
        progress_update(progress_callback, "analyzing", 10, "Analyzing resume and job description")
        # ... execute Phase 1 with Claude Code
        
        # Phase 2: Enhancement Planning
        progress_update(progress_callback, "planning", 30, "Planning enhancements")
        # ... execute Phase 2
        
        # Phase 3-5: Implementation, Verification, Finalization
        progress_update(progress_callback, "implementing", 50, "Generating customized content")
        # ... execute remaining phases
        
        # Complete
        progress_update(progress_callback, "completed", 100, "Customization complete")
    
    except Exception as e:
        progress_update(progress_callback, "error", 0, f"Error: {str(e)}")
        raise
```

### 5. CLAUDE.md Configuration

Create a `CLAUDE.md` file that defines specific guidelines for Claude Code when customizing resumes:

```markdown
# CLAUDE.md - Guidelines for Resume Customization

## Workflow
1. Always follow the evaluator-optimizer workflow from new_prompt.md
2. Create JSON intermediate files for analysis and verification
3. Document all changes with evidence sources
4. Write final output to new_customized_resume.md and customized_resume_output.md

## Verification Rules
1. Never fabricate experiences, skills, or achievements
2. Only reorganize and reframe existing content
3. Track all changes with evidence from original resume
4. Maintain strict truth tracking in evidence_tracker.json

## Output Format
1. Customized resume must be valid Markdown
2. Change summary must include match score and improvements
3. All intermediate files should be searchable JSON
```

### 6. Implementation of WebSocket Progress Updates

To provide real-time progress updates to the frontend:

```python
@app.websocket("/ws/customize/{task_id}")
async def websocket_customize_progress(websocket: WebSocket, task_id: str):
    await websocket.accept()
    
    # Retrieve task from progress tracker
    task = progress_tracker.get_task(task_id)
    
    if not task:
        await websocket.send_json({"error": "Task not found"})
        await websocket.close()
        return
    
    # Subscribe to task progress updates
    queue = asyncio.Queue()
    task.add_subscriber(queue)
    
    try:
        while True:
            # Wait for progress updates
            progress = await queue.get()
            
            # Send progress to client
            await websocket.send_json(progress)
            
            # If task is complete or errored, close connection
            if progress["status"] in ["completed", "error"]:
                break
                
    except WebSocketDisconnect:
        task.remove_subscriber(queue)
```

## Deployment Considerations

### 1. Claude Code Installation

Ensure Claude Code is installed on the server:

```bash
npm install -g @anthropic-ai/claude-code
```

### 2. Environment Configuration

Set up the necessary environment variables:

```bash
# Authentication
export ANTHROPIC_API_KEY="your_api_key_here"

# Claude Code settings
export CLAUDE_MODEL="claude-3-7-sonnet-20250219"
export CLAUDE_MAX_TOKENS=200000

# Application settings
export CLAUDE_CODE_TIMEOUT=300  # 5-minute timeout
```

### 3. Error Handling and Fallbacks

Implement robust error handling:

```python
try:
    result = executor.customize_resume(
        resume_path=resume_path,
        job_description_path=job_description_path,
        output_path=output_path
    )
except ClaudeCodeExecutionError as e:
    # Log the error
    logger.error(f"Claude Code execution failed: {str(e)}")
    
    # Fall back to previous implementation if needed
    if config.ENABLE_FALLBACK:
        logger.info("Falling back to previous implementation")
        result = legacy_customizer.customize_resume(
            resume_content=request.resume_content,
            job_description=request.job_description
        )
    else:
        raise HTTPException(status_code=500, detail="Resume customization failed")
```

## Migration Strategy

### 1. Side-by-Side Implementation

Initially implement Claude Code as an alternative path:

```python
@router.post("/customize-resume/", response_model=schemas.CustomizedResumeResponse)
async def customize_resume(
    request: schemas.CustomizeResumeRequest,
    use_claude_code: bool = Query(False, description="Use Claude Code for customization"),
    db: Session = Depends(get_db)
):
    if use_claude_code:
        # New Claude Code path
        return await customize_with_claude_code(request, db)
    else:
        # Existing implementation
        return await customize_with_existing_implementation(request, db)
```

### 2. Phase-out Plan

1. A/B test Claude Code with a subset of users (10%)
2. Monitor performance, accuracy, and user satisfaction metrics
3. Gradually increase Claude Code usage to 25%, 50%, 75%, 100%
4. Remove the legacy implementation once Claude Code is proven stable

## Performance Considerations

### 1. Caching Strategy

```python
# Cache customized resumes for the same job description
@cached(ttl=86400)  # 24-hour cache
def get_cached_customization(resume_hash, job_description_hash):
    """Check if we've already customized this resume for this job"""
    cache_key = f"{resume_hash}:{job_description_hash}"
    return customization_cache.get(cache_key)
```

### 2. Batch Processing

For high-traffic scenarios, implement a queue system:

```python
# Add customization request to queue
@router.post("/customize-resume/queue", response_model=schemas.QueuedTaskResponse)
async def queue_customize_resume(request: schemas.CustomizeResumeRequest):
    task_id = str(uuid.uuid4())
    
    # Add to background tasks queue
    background_tasks.add_task(
        process_customization_request,
        task_id=task_id,
        request=request
    )
    
    return {"task_id": task_id, "status": "queued"}

# Check status of queued task
@router.get("/customize-resume/status/{task_id}", response_model=schemas.TaskStatusResponse)
async def get_customize_status(task_id: str):
    return task_manager.get_task_status(task_id)
```

## Security Considerations

1. Use temporary directories with appropriate permissions
2. Sanitize all inputs before passing to Claude Code
3. Limit execution time and resource usage
4. Implement rate limiting for API endpoints
5. Set up monitoring and alerting for abnormal usage patterns

## Testing Strategy

1. Unit tests for the ClaudeCodeExecutor class
2. Integration tests with sample resumes and job descriptions
3. End-to-end tests of the entire workflow
4. Performance benchmarks compared to current implementation
5. A/B testing with real users

## Next Steps

1. ✅ Set up development environment with Claude Code
2. ✅ Create prototype implementation of executor service
3. ✅ Integrate with existing FastAPI backend:
   - ✅ Created `ClaudeCodeService` in frontend client.ts
   - ✅ Updated customize-resume.tsx component to use Claude Code
   - ✅ Implemented backend endpoint for Claude Code with progress tracking
   - ✅ Added fallback mechanism for resilience
4. ✅ Implement progress tracking with WebSockets
5. ✅ Update documentation:
   - ✅ Documented new architecture in README.md
   - ✅ Added Claude Code integration section with workflow details
   - ✅ Updated prerequisites and installation instructions
6. 🔄 Run preliminary testing with sample data
7. Refine prompt template based on output quality
8. Deploy for A/B testing with small user group
9. Gather metrics and refine implementation
10. Roll out to all users

## Implementation Progress

### Frontend Updates

1. ✅ Created a new `ClaudeCodeService` in client.ts with:
   - Methods for both ID-based and content-based customization
   - Clear interface definitions for requests and responses
   - Proper error handling and progress tracking

2. ✅ Simplified the component workflow in customize-resume.tsx:
   - Reduced stages from 'analysis' → 'plan' → 'implementation' → 'complete' to just 'preparation' → 'implementation' → 'complete'
   - Removed all complex plan generation code
   - Added customizationSummary state to display Claude Code's summary of changes

3. ✅ Updated UI to reflect the Claude Code workflow:
   - Modified progress steps to match the simplified stages
   - Updated loading state messages to reference Claude Code
   - Added a section to display the customization summary when available

### Backend Updates

1. ✅ Created `/claude-code/customize` endpoints:
   - Implemented synchronous endpoint for resume customization
   - Added asynchronous endpoint with progress tracking
   - Integrated with WebSockets for real-time updates
   - Set up cleanup process for completed tasks
   
2. ✅ Implemented `ClaudeCodeExecutor` service with:
   - Subprocess execution of Claude Code CLI
   - Prompt building from template and input files
   - Output parsing and processing
   - Temporary workspace management
   
3. ✅ Added error handling and fallback mechanism:
   - Set up fallback to legacy customization service
   - Added detailed error reporting and logging
   - Implemented timeout handling for long-running processes

By following this plan, we'll replace the complex PydanticAI implementation with a streamlined Claude Code approach that leverages the evaluator-optimizer workflow from `new_prompt.md` while maintaining all the functionality of the current system.