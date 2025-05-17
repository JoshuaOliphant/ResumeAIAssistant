# Progress Reporting with PydanticAI

Implementing effective progress reporting is crucial for enhancing user experience during long-running operations such as resume customization.

## Streaming Responses

PydanticAI supports streaming responses from AI models, which can be used for real-time progress updates:

```python
from pydantic_ai import Agent
from pydantic import BaseModel, Field

class Analysis(BaseModel):
    key_points: list[str] = Field(description="Key points from the text")
    summary: str = Field(description="A brief summary")

agent = Agent(
    model="anthropic:claude-3-7-sonnet-latest",
    output_type=Analysis
)

async def stream_analysis(text, progress_callback=None):
    async for partial_response in agent.run_stream(f"Analyze this text:\n\n{text}"):
        # partial_response contains incomplete fields as they're generated
        if progress_callback and "key_points" in partial_response:
            # Estimate progress based on partial content
            progress_percentage = estimate_progress(partial_response)
            await progress_callback(progress_percentage, "Generating analysis...")
    
    # Final complete response is the last item yielded
    return partial_response
```

## WebSocket-Based Progress Reporting

For the resume customization service, we'll implement a WebSocket-based progress reporting system:

```python
class ProgressReporter:
    """Reports progress of resume customization process via WebSocket."""
    
    def __init__(self, websocket_manager, customization_id):
        self.websocket_manager = websocket_manager
        self.customization_id = customization_id
        self.stages = [
            {"name": "evaluation", "description": "Evaluating resume-job match", "weight": 0.25},
            {"name": "planning", "description": "Planning improvements", "weight": 0.25},
            {"name": "implementation", "description": "Implementing changes", "weight": 0.4},
            {"name": "verification", "description": "Verifying changes", "weight": 0.1}
        ]
        self.current_stage = None
        self.stage_progress = {stage["name"]: 0 for stage in self.stages}
        self.overall_progress = 0
        self.start_time = None
        self.end_time = None
        self.status = "not_started"
        self.detailed_status = ""
        
    async def start_reporting(self):
        """Start progress reporting."""
        self.start_time = time.time()
        self.status = "in_progress"
        self.overall_progress = 0
        await self._send_update()
        
    async def update_stage_progress(self, stage_name, progress, detailed_status=""):
        """Update progress for a specific stage."""
        if stage_name not in self.stage_progress:
            return
            
        # Update stage progress
        self.stage_progress[stage_name] = progress
        
        # Update current stage if needed
        if self.current_stage != stage_name:
            self.current_stage = stage_name
            
        # Update detailed status
        if detailed_status:
            self.detailed_status = detailed_status
            
        # Recalculate overall progress
        self._recalculate_overall_progress()
        
        # Send update
        await self._send_update()
```

## Integration with PydanticAI Workflow

Integrating progress reporting with the PydanticAI workflow involves updating progress at key points:

```python
async def _evaluate_resume_job_match(self, resume_content, job_description):
    """Evaluate how well the resume matches the job description."""
    # Start progress reporting
    if self.progress_reporter:
        await self.progress_reporter.update_stage_progress(
            "evaluation", 
            10, 
            "Starting resume-job match evaluation"
        )
    
    try:
        # Create agent
        agent = await self.agent_factory.create_agent(
            output_schema=ResumeEvaluation,
            system_prompt="..."
        )
        
        # Update progress
        if self.progress_reporter:
            await self.progress_reporter.update_stage_progress(
                "evaluation", 
                30, 
                "Analyzing resume against job requirements"
            )
        
        # Run evaluation
        evaluation_result = await self.agent_factory.run_agent(
            agent,
            "Evaluate the resume against the job description"
        )
        
        # Complete progress for this stage
        if self.progress_reporter:
            await self.progress_reporter.update_stage_progress(
                "evaluation", 
                100, 
                "Completed resume-job match evaluation"
            )
        
        return evaluation_result
    except Exception as e:
        # Update progress on error
        if self.progress_reporter:
            await self.progress_reporter.update_stage_progress(
                "evaluation", 
                100, 
                f"Error during evaluation: {str(e)}"
            )
        raise
```

## WebSocket Implementation

The server-side WebSocket implementation using FastAPI:

```python
@router.websocket("/ws/customize/{customization_id}")
async def websocket_customization_progress(
    websocket: WebSocket,
    customization_id: str,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    """WebSocket endpoint for progress updates."""
    # Authenticate user
    user = authenticate_token(token)
    if not user:
        await websocket.close(code=1008)
        return
        
    # Accept connection
    await websocket.accept()
    
    # Register connection
    websocket_manager = get_websocket_manager()
    websocket_manager.register(customization_id, websocket)
    
    try:
        # Keep connection open
        while True:
            # Receive ping to keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        # Remove connection
        websocket_manager.remove(customization_id, websocket)
```

## Frontend Integration

On the frontend, use WebSockets to display real-time progress:

```typescript
// In a React component
import { useState, useEffect } from 'react';

const CustomizationProgress = ({ customizationId }) => {
  const [progress, setProgress] = useState(0);
  const [stage, setStage] = useState('');
  const [message, setMessage] = useState('');
  
  useEffect(() => {
    const token = localStorage.getItem('auth_token');
    const ws = new WebSocket(`ws://api.example.com/ws/customize/${customizationId}?token=${token}`);
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setProgress(data.overall_progress);
      setStage(data.current_stage);
      setMessage(data.detailed_status);
    };
    
    return () => {
      ws.close();
    };
  }, [customizationId]);
  
  return (
    <div className="progress-container">
      <h3>Customizing Your Resume</h3>
      <div className="progress-bar">
        <div className="progress-fill" style={{ width: `${progress}%` }}></div>
      </div>
      <p>{message}</p>
    </div>
  );
};
```

This implementation provides users with real-time visibility into the resume customization process, addressing a key issue identified in the spec.