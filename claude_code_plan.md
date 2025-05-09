# Claude Code Integration Plan for Resume Customization Service

## 1. Overview

This document outlines a proof of concept (PoC) implementation for integrating Claude Code with the existing ResumeAIAssistant application. The goal is to leverage Claude Code's advanced capabilities to replace or augment the current AI implementation while maintaining compatibility with the existing tech stack.

## 2. Core Design Principles

Based on feedback and application review, this plan focuses on:

1. **Performance Optimization** - Addressing the slow resume customization process
2. **Enhanced User Experience** - Improving progress indication and diff visualization
3. **Cost Efficiency** - Using tiered models for different processing stages
4. **Essential Features** - Focusing on core functionality (temporarily disabling cover letters)
5. **Parallel Processing** - Leveraging Claude Code's ability to parallelize tasks

## 3. Architectural Concept

The architecture integrates Claude Code as a separate backend service that follows the same evaluator-optimizer pattern currently used in the application, with enhancements for parallelization and feedback loops.

```
┌─────────────────┐      ┌────────────────────┐      ┌─────────────────────┐
│                 │      │                    │      │                     │
│  Next.js        │◄────►│  FastAPI Backend   │◄────►│  Claude Code        │
│  Frontend       │      │  (Coordinator)     │      │  Service            │
│                 │      │                    │      │                     │
└─────────────────┘      └────────────────────┘      └─────────────────────┘
```

### 3.1 Enhanced Evaluator-Optimizer Pattern

Drawing from the Anthropic engineering article on agent workflows, this implementation enhances the traditional evaluator-optimizer pattern:

1. **Multi-Stage Evaluation** - Break resume analysis into parallel specialized evaluators
2. **Continuous Feedback Loops** - Add verification components to critique optimization plans
3. **Reflective Optimization** - Implement self-critique mechanisms for proposed changes
4. **Parallel Processing** - Divide tasks across multiple Claude Code instances working simultaneously

## 4. Claude Code Service Implementation

### 4.1 Core Components

1. **Claude Code Executor** - A service to securely execute Claude Code commands
2. **Context Manager** - Handles file preparation and context management
3. **Task Orchestrator** - Manages parallel processing and task dependencies
4. **Progress Reporter** - Streams real-time progress updates to the frontend
5. **Result Synthesizer** - Combines results from parallel processes

### 4.2 CLAUDE.md Design

The CLAUDE.md file will contain specialized knowledge tailored to resume customization:

```markdown
# Resume Customization Guidelines

## Core Evaluator-Optimizer Pattern
1. Evaluation: Assess how well the resume matches the job description
2. Optimization Planning: Create a detailed customization plan
3. Implementation: Apply the optimizations to the resume
4. Verification: Verify changes maintain truthfulness and improve match

## Resume Structure Guidelines
- Key sections: Summary, Experience, Skills, Education
- Format conventions and best practices
- ATS compatibility requirements

## Parallelization Strategy
- Section-by-section parallel processing
- Independent analyzer functions
- Hierarchical synthesis of results

## Domain Knowledge
- Industry-specific terminology
- Job role requirements mapping
- ATS scanning patterns and priorities
```

## 5. Performance Optimization

### 5.1 Parallel Processing Architecture

A key innovation in this implementation is the parallel processing architecture:

1. **Section-Based Parallelization**
   - Divide resume into logical sections (summary, experience, skills, education)
   - Process each section with dedicated Claude Code instances
   - Use separate CLAUDE.md contexts optimized for each section

2. **Tiered Model Approach**
   - Use simpler models for initial analysis and formatting tasks
   - Reserve more powerful models for complex reasoning tasks
   - Intelligently allocate tokens based on section complexity

3. **Progress Streaming**
   - Implement WebSocket-based progress reporting
   - Show section-by-section completion status
   - Provide accurate time estimates based on remaining tasks

### 5.2 Implementation Example

```python
# app/services/claude_code_parallel.py

class ClaudeCodeParallelExecutor:
    """Execute multiple Claude Code tasks in parallel."""
    
    async def parallelize_resume_customization(self, resume_content, job_description):
        """
        Process resume customization by dividing into parallel tasks.
        
        Returns:
            Dict with section results and progress information
        """
        # Parse resume into sections
        sections = self._extract_resume_sections(resume_content)
        
        # Create tasks for each section
        tasks = []
        for section_name, section_content in sections.items():
            task = self.process_section(
                section_name=section_name,
                section_content=section_content,
                job_description=job_description
            )
            tasks.append(task)
        
        # Execute all tasks in parallel
        section_results = await asyncio.gather(*tasks)
        
        # Synthesize results into cohesive resume
        customized_resume = self._synthesize_resume(section_results)
        
        return {
            "customized_resume": customized_resume,
            "section_results": section_results,
            "stats": self._calculate_diff_stats(resume_content, customized_resume)
        }
    
    async def process_section(self, section_name, section_content, job_description):
        """Process a specific resume section with appropriate Claude Code instance."""
        # Select appropriate memory file for section type
        memory_path = f"app/services/claude_memories/{section_name.lower()}.md"
        
        # Create section-specific context
        context = {
            "section_name": section_name,
            "section_content": section_content,
            "job_description": job_description
        }
        
        # Execute Claude Code with specialized context
        executor = ClaudeCodeExecutor(memory_path=memory_path)
        return await executor.execute(
            command=f"optimize_{section_name.lower()}_section", 
            input_data=context
        )
```

## 6. Improved Diff Visualization

### 6.1 Enhanced Visualization Components

The current diff visualization is a pain point in the UI. The PoC will implement:

1. **Interactive Side-by-Side Comparison**
   - Clear highlighting of changes with color coding
   - Ability to toggle between different visualization modes
   - Section-by-section navigation

2. **Change Summary Dashboard**
   - Visual representation of changes by category (additions, reformatting, etc.)
   - Keyword additions and optimization metrics
   - Hover tooltips explaining rationale for changes

### 6.2 Integration Example

```typescript
// nextjs-frontend/components/resume-diff-view.tsx

import { useState } from 'react';
import { DiffViewer, DiffMethod } from 'react-diff-viewer';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

interface ResumeDiffProps {
  original: string;
  modified: string;
  sectionChanges: Record<string, any>;
}

export const EnhancedResumeDiff = ({ original, modified, sectionChanges }: ResumeDiffProps) => {
  const [diffMethod, setDiffMethod] = useState<DiffMethod>('split');
  
  return (
    <div className="resume-diff-container">
      <div className="diff-controls mb-4">
        <div className="flex justify-between items-center">
          <h3 className="text-lg font-semibold">Resume Changes</h3>
          <div className="view-mode-toggle">
            <button 
              onClick={() => setDiffMethod('split')}
              className={`px-3 py-1 rounded-l-md ${diffMethod === 'split' ? 'bg-primary text-white' : 'bg-muted'}`}
            >
              Side by Side
            </button>
            <button 
              onClick={() => setDiffMethod('unified')}
              className={`px-3 py-1 rounded-r-md ${diffMethod === 'unified' ? 'bg-primary text-white' : 'bg-muted'}`}
            >
              Inline
            </button>
          </div>
        </div>
      </div>
      
      <Tabs defaultValue="full-resume">
        <TabsList>
          <TabsTrigger value="full-resume">Full Resume</TabsTrigger>
          {Object.keys(sectionChanges).map(section => (
            <TabsTrigger key={section} value={section}>
              {section}
            </TabsTrigger>
          ))}
        </TabsList>
        
        <TabsContent value="full-resume">
          <DiffViewer
            oldValue={original}
            newValue={modified}
            splitView={diffMethod === 'split'}
            disableWordDiff={false}
            useDarkTheme={true}
            showLineNumbers={true}
          />
        </TabsContent>
        
        {Object.entries(sectionChanges).map(([section, content]) => (
          <TabsContent key={section} value={section}>
            <DiffViewer
              oldValue={content.original}
              newValue={content.modified}
              splitView={diffMethod === 'split'}
              disableWordDiff={false}
              useDarkTheme={true}
              showLineNumbers={true}
            />
            <div className="change-rationale mt-4 p-4 bg-muted rounded-md">
              <h4 className="font-medium mb-2">Change Rationale</h4>
              <p>{content.rationale}</p>
            </div>
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
};
```

## 7. Integration with Existing Backend

### 7.1 Feature Flag Implementation

To allow seamless switching between existing PydanticAI and Claude Code implementations:

```python
# app/api/endpoints/customize.py

@router.post("/customize-resume")
async def customize_resume(
    request: ResumeCustomizationRequest,
    db: Session = Depends(get_db),
    use_claude_code: bool = Query(False, description="Use Claude Code implementation")
):
    """
    Customize a resume for a specific job.
    
    Allows switching between PydanticAI and Claude Code implementations.
    """
    # Get resume and job data
    resume = db.query(Resume).filter(Resume.id == request.resume_id).first()
    job = db.query(JobDescription).filter(JobDescription.id == request.job_id).first()
    
    if not resume or not job:
        raise HTTPException(status_code=404, detail="Resume or job not found")
    
    # Select implementation based on feature flag
    if use_claude_code:
        service = ClaudeCodeCustomizationService(db)
    else:
        service = PydanticAIOptimizerService(db)
    
    # Execute customization
    result = await service.customize_resume(
        resume_id=resume.id,
        job_id=job.id,
        customization_level=request.customization_level
    )
    
    return result
```

### 7.2 Progress Streaming Implementation

```python
# app/api/endpoints/customize.py

@router.post("/customize-resume/stream")
async def stream_customize_resume(
    request: ResumeCustomizationRequest,
    db: Session = Depends(get_db)
):
    """Stream progress updates during resume customization."""
    
    # Create background task for processing
    task_id = str(uuid.uuid4())
    background_tasks.add_task(
        process_customization_with_progress,
        task_id=task_id,
        resume_id=request.resume_id,
        job_id=request.job_id,
        customization_level=request.customization_level,
        db=db
    )
    
    # Return task ID for client to connect to SSE endpoint
    return {"task_id": task_id}


@router.get("/customize-resume/progress/{task_id}")
async def get_customization_progress(
    task_id: str,
    request: Request
):
    """SSE endpoint for streaming customization progress."""
    async def event_generator():
        try:
            # Set up connection to Redis for progress updates
            redis = aioredis.from_url(settings.REDIS_URL)
            pubsub = redis.pubsub()
            await pubsub.subscribe(f"progress:{task_id}")
            
            # Send initial event
            yield "data: " + json.dumps({"status": "started", "progress": 0}) + "\n\n"
            
            # Stream progress events
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    yield "data: " + json.dumps(data) + "\n\n"
                    
                    # If complete, break the loop
                    if data.get("status") == "complete":
                        break
                        
        except Exception as e:
            yield "data: " + json.dumps({"status": "error", "message": str(e)}) + "\n\n"
        finally:
            # Clean up
            await pubsub.unsubscribe(f"progress:{task_id}")
            await redis.close()
    
    return EventSourceResponse(event_generator())
```

### 7.3 Frontend Integration

```tsx
// nextjs-frontend/pages/customize/result/page.tsx

import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { Progress } from '@/components/ui/progress';
import { EnhancedResumeDiff } from '@/components/resume-diff-view';
import { CustomizationService } from '@/lib/client';

export default function CustomizationResultPage() {
  const router = useRouter();
  const { resumeId, jobId, level, taskId } = router.query;
  
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState('');
  const [result, setResult] = useState(null);
  const [isComplete, setIsComplete] = useState(false);
  
  useEffect(() => {
    if (!taskId) return;
    
    // Connect to SSE endpoint for progress updates
    const eventSource = new EventSource(`/api/customize/progress/${taskId}`);
    
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      setProgress(data.progress || 0);
      setCurrentStep(data.current_step || '');
      
      if (data.status === 'complete') {
        setResult(data.result);
        setIsComplete(true);
        eventSource.close();
      }
    };
    
    eventSource.onerror = () => {
      console.error('EventSource failed');
      eventSource.close();
    };
    
    return () => {
      eventSource.close();
    };
  }, [taskId]);
  
  return (
    <div className="container mx-auto py-8">
      <h1 className="text-2xl font-bold mb-6">Resume Customization</h1>
      
      {!isComplete ? (
        <div className="customization-progress">
          <Progress value={progress} className="w-full mb-4" />
          <p className="text-center text-muted-foreground">
            {currentStep || 'Processing your resume...'}
          </p>
          <p className="text-center text-sm mt-2">
            Estimated time remaining: {Math.ceil((100 - progress) / 10)} minutes
          </p>
        </div>
      ) : (
        <div className="customization-result">
          <div className="ats-score mb-8">
            <h2 className="text-xl font-semibold mb-4">ATS Compatibility Improvement</h2>
            <div className="flex justify-between items-center">
              <div className="text-center">
                <p className="text-sm text-muted-foreground">Before</p>
                <p className="text-2xl font-bold">{result.before_score}%</p>
              </div>
              <div className="arrow">→</div>
              <div className="text-center">
                <p className="text-sm text-muted-foreground">After</p>
                <p className="text-2xl font-bold text-green-500">
                  {result.after_score}% (+{result.after_score - result.before_score}%)
                </p>
              </div>
            </div>
          </div>
          
          <div className="resume-changes">
            <h2 className="text-xl font-semibold mb-4">Resume Changes</h2>
            <EnhancedResumeDiff 
              original={result.original_content}
              modified={result.customized_content}
              sectionChanges={result.section_changes}
            />
          </div>
        </div>
      )}
    </div>
  );
}
```

## 8. Security and Isolation

### 8.1 Docker Containerization

The Claude Code service will run in an isolated container with controlled permissions:

```dockerfile
# Dockerfile.claude-code
FROM python:3.9-slim

WORKDIR /app

# Install Claude CLI and dependencies
RUN pip install anthropic claude-cli fastapi uvicorn redis

# Copy only necessary files
COPY ./app/services/claude_memories /app/memories
COPY ./app/services/claude_code_service.py /app/
COPY ./app/services/claude_code_executor.py /app/

# Set up restricted user
RUN useradd -m claudeuser
USER claudeuser

# Configure Claude CLI
ENV CLAUDE_API_KEY=${CLAUDE_API_KEY}
ENV CLAUDE_MEMORY_DIR=/app/memories

# Run service
CMD ["uvicorn", "claude_code_service:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 8.2 Rate Limiting and Timeout Controls

```python
# app/services/claude_code_executor.py

class ClaudeCodeExecutor:
    """Secure executor for Claude Code commands."""
    
    def __init__(self, memory_path, max_execution_time=300):
        self.memory_path = memory_path
        self.max_execution_time = max_execution_time
        self.rate_limiter = RateLimiter(max_calls=10, period=60)  # 10 calls per minute
    
    async def execute(self, command, input_data):
        """Execute a Claude Code command with rate limiting and timeouts."""
        # Check rate limit
        await self.rate_limiter.acquire()
        
        try:
            # Execute with timeout
            return await asyncio.wait_for(
                self._execute_claude_code(command, input_data),
                timeout=self.max_execution_time
            )
        except asyncio.TimeoutError:
            raise TimeoutError(f"Claude Code execution timed out after {self.max_execution_time} seconds")
        except Exception as e:
            raise RuntimeError(f"Claude Code execution failed: {str(e)}")
```

## 9. Essential Features and Priorities

Based on feedback, the immediate priorities for the PoC are:

1. **Performance Improvement** - Implementing parallel processing architecture
2. **Progress Tracking** - Adding real-time progress updates
3. **Enhanced Diff Visualization** - Improving the resume comparison interface
4. **Feature Flags** - Creating toggles for optional features (like cover letters)

Lower priority items to consider after successful PoC:

1. Cover letter generation
2. Advanced research capabilities using web search
3. Additional export formats
4. User feedback collection system

## 10. Next Steps

1. Create a separate GitHub repository for the Claude Code PoC
2. Set up dockerized development environment with Claude Code CLI
3. Develop initial CLAUDE.md for resume customization
4. Implement basic parallel processing infrastructure
5. Create progress streaming components
6. Design and implement enhanced diff visualization

This plan addresses the key issues identified in the feedback while focusing on essential features for a successful PoC implementation.