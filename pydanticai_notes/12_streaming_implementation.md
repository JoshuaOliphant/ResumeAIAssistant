# Streaming Implementation with PydanticAI

Based on the available examples and documentation, this document explains how to implement streaming responses in PydanticAI and how it can be applied to the resume customization service for real-time progress tracking.

## Basic Streaming Concepts

PydanticAI supports two forms of streaming:

1. **Text Streaming**: Streams raw text output incrementally
2. **Structured Streaming**: Streams partially completed structured data (like Pydantic models)

Both are valuable for our resume customization service to provide real-time progress updates to users.

## Text Streaming

The simplest form of streaming returns incremental text:

```python
from pydantic_ai import Agent
import asyncio

async def stream_text_example():
    agent = Agent(
        model="anthropic:claude-3-7-sonnet-latest",
        output_type=str
    )
    
    prompt = "Write a paragraph about resume customization."
    
    # Stream the response
    async for chunk in agent.run_stream(prompt):
        # Each chunk is a string containing new content
        print(chunk, end="", flush=True)
        await asyncio.sleep(0.01)  # Simulate network delay
```

## Structured Streaming

More powerful is structured streaming, which returns partially completed structured data:

```python
from pydantic_ai import Agent
from pydantic import BaseModel, Field
from typing import List, Optional

class ResumeEvaluation(BaseModel):
    match_score: Optional[int] = Field(None, description="Overall match score (0-100)")
    strengths: List[str] = Field(default_factory=list, description="Resume strengths")
    gaps: List[str] = Field(default_factory=list, description="Areas for improvement")
    overall_assessment: Optional[str] = Field(None, description="Overall assessment")

async def stream_structured_example():
    agent = Agent(
        model="anthropic:claude-3-7-sonnet-latest",
        output_type=ResumeEvaluation
    )
    
    prompt = """
    Evaluate this resume for a software engineering position:
    [Resume content here]
    """
    
    # Use context manager for structured streaming
    async with agent.run_stream(prompt) as result:
        # Stream partial ResumeEvaluation objects
        async for partial_evaluation in result.stream():
            # partial_evaluation is a partially complete ResumeEvaluation
            print_progress_update(partial_evaluation)
```

## Stream Processing with WebSockets

For our resume customization service, we'll combine structured streaming with WebSockets:

```python
import asyncio
from fastapi import WebSocket
from pydantic_ai import Agent

async def stream_customization_progress(
    websocket: WebSocket,
    resume_content: str,
    job_description: str
):
    """Stream customization progress via WebSocket."""
    # Accept the WebSocket connection
    await websocket.accept()
    
    # Create agent
    agent = Agent(
        model="anthropic:claude-3-7-sonnet-latest",
        output_type=ResumeEvaluation
    )
    
    # Prepare prompt
    prompt = f"""
    Evaluate how well this resume matches the job description:
    
    RESUME:
    {resume_content}
    
    JOB DESCRIPTION:
    {job_description}
    """
    
    # Initialize progress tracking
    progress = 0
    last_update_time = asyncio.get_event_loop().time()
    update_interval = 0.5  # Update at most every 0.5 seconds
    
    try:
        # Stream the evaluation
        async with agent.run_stream(prompt) as result:
            async for partial_evaluation in result.stream():
                # Calculate progress based on fields completed
                new_progress = calculate_progress(partial_evaluation)
                
                # Check if it's time to send an update
                current_time = asyncio.get_event_loop().time()
                if (new_progress != progress and 
                    current_time - last_update_time >= update_interval):
                    
                    # Update progress
                    progress = new_progress
                    last_update_time = current_time
                    
                    # Send progress update via WebSocket
                    await websocket.send_json({
                        "progress": progress,
                        "stage": "evaluation",
                        "data": partial_evaluation.dict(exclude_none=True)
                    })
                    
        # Send final complete result
        await websocket.send_json({
            "progress": 100,
            "stage": "evaluation",
            "data": partial_evaluation.dict(),
            "complete": True
        })
    
    except Exception as e:
        # Send error message
        await websocket.send_json({
            "error": str(e)
        })
    finally:
        # Close connection
        await websocket.close()

def calculate_progress(partial_evaluation: ResumeEvaluation) -> int:
    """Calculate progress percentage based on completed fields."""
    # Track which fields are completed
    completed_fields = 0
    total_fields = 4  # match_score, strengths, gaps, overall_assessment
    
    if partial_evaluation.match_score is not None:
        completed_fields += 1
    
    if partial_evaluation.strengths:
        completed_fields += 1
    
    if partial_evaluation.gaps:
        completed_fields += 1
    
    if partial_evaluation.overall_assessment:
        completed_fields += 1
    
    # Calculate percentage
    return int((completed_fields / total_fields) * 100)
```

## Multi-Stage Streaming with Progress Tracking

For our 4-stage resume customization workflow, we need more sophisticated progress tracking:

```python
class CustomizationProgress:
    """Tracks progress across multiple stages of resume customization."""
    
    def __init__(self, websocket):
        self.websocket = websocket
        self.stages = [
            {"name": "evaluation", "weight": 0.25, "progress": 0},
            {"name": "planning", "weight": 0.25, "progress": 0},
            {"name": "implementation", "weight": 0.4, "progress": 0},
            {"name": "verification", "weight": 0.1, "progress": 0}
        ]
        self.current_stage_index = 0
        self.overall_progress = 0
    
    def update_stage_progress(self, progress: int):
        """Update progress for the current stage."""
        self.stages[self.current_stage_index]["progress"] = progress
        self._recalculate_overall_progress()
    
    def advance_stage(self):
        """Move to the next stage."""
        if self.current_stage_index < len(self.stages) - 1:
            self.current_stage_index += 1
    
    def _recalculate_overall_progress(self):
        """Recalculate overall progress based on weighted stage progress."""
        self.overall_progress = sum(
            stage["weight"] * stage["progress"] 
            for stage in self.stages
        )
    
    async def send_update(self, details=None):
        """Send progress update via WebSocket."""
        current_stage = self.stages[self.current_stage_index]
        
        await self.websocket.send_json({
            "overall_progress": round(self.overall_progress),
            "current_stage": current_stage["name"],
            "stage_progress": current_stage["progress"],
            "details": details
        })
```

## Full Implementation with 4-Stage Streaming

Here's how to implement streaming for the entire 4-stage workflow:

```python
async def stream_resume_customization(
    websocket: WebSocket,
    resume_content: str,
    job_description: str
):
    """Stream the full 4-stage resume customization process."""
    # Accept connection
    await websocket.accept()
    
    # Initialize progress tracker
    progress = CustomizationProgress(websocket)
    
    try:
        # Stage 1: Evaluation
        evaluation_result = await stream_evaluation(
            resume_content, 
            job_description, 
            progress
        )
        
        # Advance to next stage
        progress.advance_stage()
        await progress.send_update({"message": "Starting improvement planning"})
        
        # Stage 2: Planning
        improvement_plan = await stream_planning(
            resume_content,
            job_description,
            evaluation_result,
            progress
        )
        
        # Advance to next stage
        progress.advance_stage()
        await progress.send_update({"message": "Implementing customizations"})
        
        # Stage 3: Implementation
        customized_resume = await stream_implementation(
            resume_content,
            job_description,
            improvement_plan,
            progress
        )
        
        # Advance to next stage
        progress.advance_stage()
        await progress.send_update({"message": "Verifying customizations"})
        
        # Stage 4: Verification
        verification_result = await stream_verification(
            resume_content,
            customized_resume,
            progress
        )
        
        # Send final result
        await websocket.send_json({
            "overall_progress": 100,
            "complete": True,
            "result": {
                "customized_resume": customized_resume,
                "evaluation": evaluation_result.dict(),
                "improvement_plan": improvement_plan.dict(),
                "verification": verification_result.dict()
            }
        })
    
    except Exception as e:
        # Send error
        await websocket.send_json({
            "error": str(e)
        })
    finally:
        # Close connection
        await websocket.close()
```

## Individual Stage Streaming Implementation

Here's an example of how to implement streaming for one stage (evaluation):

```python
async def stream_evaluation(
    resume_content: str,
    job_description: str,
    progress: CustomizationProgress
) -> ResumeEvaluation:
    """Stream the evaluation stage and report progress."""
    # Create evaluation agent
    agent = Agent(
        model="anthropic:claude-3-7-sonnet-latest",
        output_type=ResumeEvaluation
    )
    
    # Prepare prompt
    prompt = f"""
    Evaluate how well this resume matches the job description:
    
    RESUME:
    {resume_content}
    
    JOB DESCRIPTION:
    {job_description}
    """
    
    # Initialize tracking
    field_progress = {
        "match_score": 0.25,
        "strengths": 0.25,
        "gaps": 0.25,
        "overall_assessment": 0.25
    }
    completed_fields = set()
    
    # Stream evaluation
    async with agent.run_stream(prompt) as result:
        async for partial_evaluation in result.stream():
            # Track newly completed fields
            stage_progress = 0
            
            for field, weight in field_progress.items():
                field_value = getattr(partial_evaluation, field)
                
                # Check if field is now complete
                is_complete = False
                if field == "match_score" and field_value is not None:
                    is_complete = True
                elif field in ["strengths", "gaps"] and field_value:
                    is_complete = True
                elif field == "overall_assessment" and field_value:
                    is_complete = True
                
                # Update progress if field is newly completed
                if is_complete and field not in completed_fields:
                    completed_fields.add(field)
                
                # Add field's contribution to progress
                if field in completed_fields:
                    stage_progress += weight * 100
            
            # Update and send progress
            progress.update_stage_progress(round(stage_progress))
            await progress.send_update({
                "partial_evaluation": partial_evaluation.dict(exclude_none=True)
            })
    
    # Return the final result
    return partial_evaluation
```

## Integration with Frontend

On the frontend, we can use WebSockets to display real-time progress:

```typescript
// In a React component
import { useState, useEffect } from 'react';
import { WebSocket } from 'websocket';

export const ResumeCustomizer = ({ resumeId, jobId }) => {
  const [overallProgress, setOverallProgress] = useState(0);
  const [currentStage, setCurrentStage] = useState('');
  const [stageProgress, setStageProgress] = useState(0);
  const [details, setDetails] = useState({});
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  
  useEffect(() => {
    // Create WebSocket connection
    const token = localStorage.getItem('auth_token');
    const ws = new WebSocket(
      `wss://api.example.com/ws/customize?resumeId=${resumeId}&jobId=${jobId}&token=${token}`
    );
    
    // Handle connection open
    ws.onopen = () => {
      console.log('WebSocket connection established');
    };
    
    // Handle messages
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      // Update state with progress data
      setOverallProgress(data.overall_progress || 0);
      setCurrentStage(data.current_stage || '');
      setStageProgress(data.stage_progress || 0);
      setDetails(data.details || {});
      
      // Check for completion
      if (data.complete) {
        setResult(data.result);
      }
      
      // Check for errors
      if (data.error) {
        setError(data.error);
      }
    };
    
    // Handle connection close
    ws.onclose = () => {
      console.log('WebSocket connection closed');
    };
    
    // Cleanup on unmount
    return () => {
      ws.close();
    };
  }, [resumeId, jobId]);
  
  // Render progress UI
  return (
    <div className="customizer">
      <h2>Customizing Your Resume</h2>
      
      {/* Overall progress bar */}
      <div className="progress-bar">
        <div 
          className="progress-fill" 
          style={{ width: `${overallProgress}%` }}
        />
      </div>
      <div className="progress-label">
        {overallProgress}% complete
      </div>
      
      {/* Stage information */}
      <div className="stage-info">
        <h3>{formatStageName(currentStage)}</h3>
        <div className="stage-progress-bar">
          <div 
            className="stage-progress-fill" 
            style={{ width: `${stageProgress}%` }}
          />
        </div>
      </div>
      
      {/* Stage details */}
      {details.message && (
        <div className="stage-message">{details.message}</div>
      )}
      
      {/* Error display */}
      {error && (
        <div className="error-message">
          Error: {error}
        </div>
      )}
      
      {/* Results display (when complete) */}
      {result && (
        <div className="results">
          <h3>Customization Complete!</h3>
          {/* Render customized resume and other results */}
        </div>
      )}
    </div>
  );
};

// Helper function to format stage name
function formatStageName(stage) {
  switch (stage) {
    case 'evaluation': return 'Evaluating Resume';
    case 'planning': return 'Planning Improvements';
    case 'implementation': return 'Implementing Changes';
    case 'verification': return 'Verifying Changes';
    default: return 'Preparing';
  }
}
```

## Best Practices for Streaming Implementation

1. **Throttle Updates**: Limit update frequency to avoid overwhelming the WebSocket
2. **Graceful Degradation**: Provide fallback for clients that don't support WebSockets
3. **Structured Progress**: Create a clear model for progress tracking across stages
4. **Connection Management**: Handle WebSocket disconnections gracefully
5. **Error Handling**: Provide meaningful error messages when streaming fails
6. **Completion Detection**: Clearly indicate when the process is complete
7. **UI Responsiveness**: Ensure the UI remains responsive during streaming

By implementing these streaming patterns, our resume customization service will provide a more engaging and transparent experience for users, addressing the current issue of limited visibility into process progress.