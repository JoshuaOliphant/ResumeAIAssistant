# Tracing and Observability with PydanticAI

This document explores how to implement tracing and observability for the resume customization service using PydanticAI and Logfire.

## Overview of Logfire Integration

PydanticAI integrates with Logfire, a specialized observability platform developed by the Pydantic team, specifically designed for generative AI applications. It provides:

1. **Detailed Traces**: Track agent runs, model requests, and tool calls
2. **Performance Monitoring**: Measure latency and resource usage
3. **Tool Execution Tracking**: Monitor tool calls and their outcomes
4. **Error Reporting**: Capture and analyze errors in AI workflows
5. **Usage Metrics**: Track token usage and API costs

## Basic Setup

Setting up Logfire for the resume customization service:

```python
import logfire
from pydantic_ai import Agent
from app.services.resume_customizer import ResumeCustomizer

# Configure Logfire
logfire.configure(
    app_name="resume-customizer",
    environment="development"
)

# Instrument PydanticAI
logfire.instrument_pydantic_ai()

# Instrument HTTP requests (for API calls)
logfire.instrument_httpx(capture_all=True)
```

## Advanced Tracing Configuration

For production deployment, implement more sophisticated tracing:

```python
import logfire
import os
from pydantic_ai import Agent
from opentelemetry.sdk.resources import Resource

# Configure resource attributes for better trace organization
resource = Resource.create({
    "service.name": "resume-customizer",
    "service.version": "1.0.0",
    "deployment.environment": os.environ.get("ENVIRONMENT", "development")
})

# Configure Logfire with custom settings
logfire.configure(
    app_name="resume-customizer",
    resource=resource,
    event_mode=logfire.EventMode.CONSOLE_AND_PLATFORM if os.environ.get("ENVIRONMENT") == "production" else logfire.EventMode.CONSOLE_ONLY,
    enable_recording=True
)

# Configure spans to capture
logfire.instrument_pydantic_ai(
    capture_run_steps=True,  # Track individual steps within an agent run
    capture_prompt_tokens=True,  # Track token usage
    capture_requests=True  # Track all HTTP requests
)
```

## Structured Logging

Implement structured logging throughout the resume customization service:

```python
class ResumeCustomizer:
    """Customizes resumes for job descriptions with tracing."""
    
    async def customize_resume(self, resume_content, job_description, customization_id):
        """Customize a resume with comprehensive tracing."""
        # Create a span for the entire customization process
        with logfire.span(
            "customize_resume",
            {
                "customization_id": customization_id,
                "resume_length": len(resume_content),
                "job_description_length": len(job_description)
            }
        ):
            try:
                # Log the start of customization
                logfire.info(
                    "Starting resume customization",
                    customization_id=customization_id
                )
                
                # Stage 1: Evaluation with tracing
                with logfire.span("evaluation_stage"):
                    evaluation_result = await self._evaluate_resume_job_match(
                        resume_content, 
                        job_description
                    )
                    
                    logfire.info(
                        "Completed evaluation stage",
                        match_score=evaluation_result.overall_match_score,
                        strengths_count=len(evaluation_result.top_strengths),
                        gaps_count=len(evaluation_result.key_gaps)
                    )
                
                # Stage 2: Planning with tracing
                with logfire.span("planning_stage"):
                    improvement_plan = await self._generate_improvement_plan(
                        resume_content,
                        job_description,
                        evaluation_result
                    )
                    
                    logfire.info(
                        "Completed planning stage",
                        section_improvements=len(improvement_plan.section_improvements),
                        keyword_strategies=len(improvement_plan.keyword_strategies)
                    )
                
                # Stage 3: Implementation with tracing
                with logfire.span("implementation_stage"):
                    customized_resume = await self._implement_customizations(
                        resume_content,
                        job_description,
                        improvement_plan
                    )
                    
                    logfire.info(
                        "Completed implementation stage",
                        original_length=len(resume_content),
                        customized_length=len(customized_resume)
                    )
                
                # Stage 4: Verification with tracing
                with logfire.span("verification_stage"):
                    verification_result = await self._verify_customization(
                        resume_content,
                        customized_resume,
                        job_description
                    )
                    
                    logfire.info(
                        "Completed verification stage",
                        is_truthful=verification_result["verified"],
                        issues_count=len(verification_result.get("issues", []))
                    )
                
                # Log successful completion
                logfire.info(
                    "Resume customization completed successfully",
                    customization_id=customization_id
                )
                
                return {
                    "customized_resume": customized_resume,
                    "evaluation": evaluation_result,
                    "improvement_plan": improvement_plan,
                    "verification_result": verification_result
                }
                
            except Exception as e:
                # Log failure with error details
                logfire.error(
                    "Resume customization failed",
                    customization_id=customization_id,
                    error=str(e),
                    exc_info=True
                )
                raise
```

## Tracing Agent Execution

Trace PydanticAI agent execution with detailed metadata:

```python
async def _evaluate_resume_job_match(self, resume_content, job_description):
    """Evaluate how well the resume matches the job description."""
    try:
        # Create evaluation agent
        agent = await self.agent_factory.create_agent(
            output_schema=ResumeEvaluation,
            system_prompt="You are an expert resume evaluator."
        )
        
        # Create span for agent execution
        with logfire.span(
            "agent_run",
            {
                "agent_type": "evaluation",
                "model": "anthropic:claude-3-7-sonnet-latest",
                "resume_length": len(resume_content),
                "job_description_length": len(job_description)
            }
        ):
            # Run evaluation
            evaluation_result = await self.agent_factory.run_agent(
                agent,
                f"""
                Evaluate how well this resume matches the job description:
                
                RESUME:
                {resume_content}
                
                JOB DESCRIPTION:
                {job_description}
                """
            )
            
            # Log evaluation metrics
            logfire.info(
                "Resume evaluation completed",
                match_score=evaluation_result.overall_match_score,
                strengths_count=len(evaluation_result.top_strengths),
                gaps_count=len(evaluation_result.key_gaps),
                missing_keywords_count=len(evaluation_result.missing_keywords)
            )
            
            return evaluation_result
    except Exception as e:
        # Log specific evaluation errors
        logfire.error(
            "Resume evaluation failed",
            error=str(e),
            exc_info=True
        )
        raise
```

## Tracing Tool Execution

For tools used in the resume customization process:

```python
async def extract_job_requirements(
    ctx: RunContext, 
    job_description: str
) -> List[str]:
    """Extract key requirements from a job description."""
    # Create span for tool execution
    with logfire.span(
        "tool_execution",
        {
            "tool_name": "extract_job_requirements",
            "job_description_length": len(job_description),
            "retry_count": ctx.retry
        }
    ):
        try:
            # Tool implementation
            requirements = []
            
            # Process job description to extract requirements
            sections = job_description.split("\n\n")
            for section in sections:
                if any(keyword in section.lower() for keyword in ["requirements", "qualifications", "skills"]):
                    # Process this section to extract requirements
                    section_requirements = extract_requirements_from_section(section)
                    requirements.extend(section_requirements)
            
            # Log extraction results
            logfire.info(
                "Extracted job requirements",
                requirements_count=len(requirements)
            )
            
            return requirements
        except Exception as e:
            # Log tool execution failure
            logfire.error(
                "Job requirements extraction failed",
                error=str(e),
                exc_info=True
            )
            raise
```

## Monitoring Error Cases and Retries

Track retries and error cases for better debugging:

```python
@agent.output_validator(retries=2)
async def validate_evaluation(ctx: RunContext, evaluation: ResumeEvaluation) -> ResumeEvaluation:
    """Validate evaluation output and track retries."""
    # Create span for validation
    with logfire.span(
        "validation",
        {
            "validator_type": "evaluation",
            "retry_count": ctx.retry
        }
    ):
        try:
            # Validation logic
            if not (0 <= evaluation.overall_match_score <= 100):
                error_message = "Overall match score must be between 0 and 100"
                logfire.warn(
                    "Validation failed, retrying",
                    error=error_message,
                    retry_count=ctx.retry
                )
                raise ModelRetry(error_message)
            
            # Additional validation checks...
            
            # Log successful validation
            logfire.info(
                "Validation passed",
                match_score=evaluation.overall_match_score,
                strengths_count=len(evaluation.top_strengths)
            )
            
            return evaluation
        except ModelRetry as e:
            # Re-raise ModelRetry errors for retry mechanism
            raise
        except Exception as e:
            # Log unexpected validation errors
            logfire.error(
                "Unexpected validation error",
                error=str(e),
                exc_info=True
            )
            raise
```

## API Endpoint Tracing

Trace FastAPI endpoints for the resume customization service:

```python
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
import logfire
import uuid
from datetime import datetime

router = APIRouter()

@router.post("/customize/", response_model=CustomizationResponse)
async def customize_resume(
    request: CustomizationRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Initiate resume customization process with tracing."""
    # Create span for API endpoint
    with logfire.span(
        "api_customize_resume",
        {
            "user_id": user.id,
            "resume_id": request.resume_id,
            "job_id": request.job_description_id
        }
    ):
        try:
            # Generate customization ID
            customization_id = uuid.uuid4().hex
            
            # Get resume and job description
            resume = await get_resume(request.resume_id, user.id, db)
            job_description = await get_job_description(request.job_description_id, user.id, db)
            
            if not resume or not job_description:
                logfire.warn(
                    "Resume or job description not found",
                    resume_found=resume is not None,
                    job_description_found=job_description is not None
                )
                raise HTTPException(status_code=404, detail="Resume or job description not found")
            
            # Log customization request details
            logfire.info(
                "Resume customization requested",
                customization_id=customization_id,
                resume_id=request.resume_id,
                job_id=request.job_description_id,
                customization_level=request.customization_level
            )
            
            # Create services for customization
            resume_customizer = create_resume_customizer(
                customization_id=customization_id,
                customization_level=request.customization_level
            )
            
            # Start customization in background
            background_tasks.add_task(
                run_customization_process,
                resume_customizer=resume_customizer,
                resume_content=resume.content,
                job_description=job_description.content,
                customization_id=customization_id,
                db=db
            )
            
            return CustomizationResponse(
                customization_id=customization_id,
                status="pending",
                message="Customization process started"
            )
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            # Log unexpected errors
            logfire.error(
                "Unexpected error in customize_resume endpoint",
                error=str(e),
                exc_info=True
            )
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
```

## Token Usage and Cost Tracking

Track token usage and estimated costs for model calls:

```python
class ModelUsageTracker:
    """Tracks model usage and costs for resume customization."""
    
    def __init__(self):
        # Cost per 1000 tokens for different models
        self.costs = {
            "anthropic:claude-3-7-sonnet-latest": {
                "input": 0.008,  # $0.008 per 1K input tokens
                "output": 0.024   # $0.024 per 1K output tokens
            }
        }
        
        # Usage counters
        self.usage = {
            "evaluation": {"input_tokens": 0, "output_tokens": 0},
            "planning": {"input_tokens": 0, "output_tokens": 0},
            "implementation": {"input_tokens": 0, "output_tokens": 0},
            "verification": {"input_tokens": 0, "output_tokens": 0}
        }
    
    def track_usage(self, stage, input_tokens, output_tokens):
        """Track token usage for a stage."""
        self.usage[stage]["input_tokens"] += input_tokens
        self.usage[stage]["output_tokens"] += output_tokens
        
        # Log token usage
        logfire.info(
            f"Token usage for {stage} stage",
            stage=stage,
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )
    
    def calculate_cost(self):
        """Calculate total cost based on token usage."""
        total_cost = 0
        model = "anthropic:claude-3-7-sonnet-latest"
        
        for stage, tokens in self.usage.items():
            input_cost = (tokens["input_tokens"] / 1000) * self.costs[model]["input"]
            output_cost = (tokens["output_tokens"] / 1000) * self.costs[model]["output"]
            stage_cost = input_cost + output_cost
            total_cost += stage_cost
            
            # Log stage cost
            logfire.info(
                f"Cost for {stage} stage",
                stage=stage,
                input_cost=input_cost,
                output_cost=output_cost,
                stage_cost=stage_cost
            )
        
        # Log total cost
        logfire.info(
            "Total customization cost",
            total_cost=total_cost
        )
        
        return total_cost
```

## WebSocket Connection Tracing

Trace WebSocket connections for progress reporting:

```python
@router.websocket("/ws/customize/{customization_id}")
async def websocket_customization_progress(
    websocket: WebSocket,
    customization_id: str,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    """WebSocket endpoint for progress updates with tracing."""
    # Create a span for the WebSocket connection
    with logfire.span(
        "websocket_connection",
        {
            "customization_id": customization_id
        }
    ):
        try:
            # Log WebSocket connection attempt
            logfire.info(
                "WebSocket connection attempt",
                customization_id=customization_id
            )
            
            # Authenticate user
            user = authenticate_token(token)
            if not user:
                logfire.warn(
                    "WebSocket authentication failed",
                    customization_id=customization_id
                )
                await websocket.close(code=1008)
                return
            
            # Log authenticated user
            logfire.info(
                "WebSocket authenticated",
                customization_id=customization_id,
                user_id=user.id
            )
            
            # Check customization exists and belongs to user
            customization = db.query(CustomizationModel).filter(
                CustomizationModel.id == customization_id,
                CustomizationModel.user_id == user.id
            ).first()
            
            if not customization:
                logfire.warn(
                    "Customization not found for WebSocket connection",
                    customization_id=customization_id,
                    user_id=user.id
                )
                await websocket.close(code=1008)
                return
            
            # Accept connection
            await websocket.accept()
            logfire.info(
                "WebSocket connection accepted",
                customization_id=customization_id
            )
            
            # Register connection
            websocket_manager = get_websocket_manager()
            websocket_manager.register(customization_id, websocket)
            
            # Count of messages received (for heartbeat tracking)
            message_count = 0
            
            try:
                # Keep connection open
                while True:
                    # Receive ping to keep connection alive
                    await websocket.receive_text()
                    message_count += 1
                    
                    # Log heartbeat periodically
                    if message_count % 10 == 0:
                        logfire.debug(
                            "WebSocket heartbeat",
                            customization_id=customization_id,
                            message_count=message_count
                        )
            except WebSocketDisconnect:
                # Log disconnection
                logfire.info(
                    "WebSocket disconnected",
                    customization_id=customization_id,
                    message_count=message_count
                )
                
                # Remove connection
                websocket_manager.remove(customization_id, websocket)
        except Exception as e:
            # Log unexpected errors
            logfire.error(
                "WebSocket error",
                customization_id=customization_id,
                error=str(e),
                exc_info=True
            )
            
            # Attempt to close connection
            try:
                await websocket.close(code=1011)
            except:
                pass
```

## Best Practices for Tracing in Production

1. **Sampling Strategy**: In high-volume production, use sampling to reduce trace volume
2. **Sensitive Data Handling**: Be careful about logging sensitive resume or job data
3. **Performance Considerations**: Balance tracing detail with performance impact
4. **Retention Policy**: Set appropriate retention periods for log data
5. **Error Alerting**: Configure alerts for critical errors
6. **Dashboard Creation**: Build dashboards for key metrics and error rates
7. **Cold Start Monitoring**: Track performance during cold starts
8. **Correlation IDs**: Use consistent customization_id across all traces

## Implementation in Our Project

To implement tracing in our resume customization service:

1. **Add Logfire Dependencies**:
   ```bash
   uv add "pydantic-ai[logfire]"
   ```

2. **Configure tracing in main.py**:
   ```python
   import logfire
   
   # Setup logging early in application startup
   logfire.configure(
       app_name="resume-customizer",
       environment=os.environ.get("ENVIRONMENT", "development")
   )
   
   # Instrument PydanticAI
   logfire.instrument_pydantic_ai()
   
   # Instrument HTTP client
   logfire.instrument_httpx()
   ```

3. **Add Tracing to Services**: Add spans and logging to all key services as shown above

4. **Dashboard Setup**: Create a dashboard to monitor:
   - Success/failure rates
   - Processing times per stage
   - Token usage and costs
   - Error frequency and types
   - Retry rates

By implementing comprehensive tracing and observability, we'll be able to:
- Debug issues more effectively
- Optimize performance of the customization process
- Monitor costs and resource usage
- Ensure reliability in production
- Identify patterns in failures and retries