# Dependency Injection in PydanticAI

Based on the examples and documentation explored, this document outlines how dependency injection works in PydanticAI and how we can apply it to the resume customization service.

## Core Concepts

Dependency injection in PydanticAI enables tools and agents to receive shared dependencies through a typed context object. This provides several benefits:

1. **Type Safety**: Dependencies are properly typed
2. **Testability**: Dependencies can be easily mocked for testing
3. **Reusability**: Shared resources can be consistently accessed across tools
4. **Separation of Concerns**: Tools focus on specific tasks while dependencies handle infrastructure

## Implementation Pattern

### 1. Define Dependencies Class

First, create a Pydantic model or dataclass defining the dependencies:

```python
from dataclasses import dataclass
from typing import Dict, Optional
from aiohttp import ClientSession
from databases import Database

@dataclass
class ResumeDeps:
    """Dependencies for the resume customization service."""
    
    # External API clients
    http_client: ClientSession
    
    # Database access
    db: Database
    
    # Configuration
    config: Dict[str, str]
    
    # Optional API keys
    anthropic_api_key: Optional[str] = None
```

### 2. Create Agent with Dependency Type

When creating the agent, specify the dependency type:

```python
from pydantic_ai import Agent
from pydantic_ai.run_context import RunContext

agent = Agent(
    model="anthropic:claude-3-7-sonnet-latest",
    output_type=ResumeEvaluation,
    deps_type=ResumeDeps  # Specify dependency type
)
```

### 3. Create Tools That Use Dependencies

Tools can access dependencies through the `RunContext`:

```python
@agent.tool()
async def fetch_job_requirements(
    ctx: RunContext[ResumeDeps],  # Context with typed dependencies
    job_description: str
) -> List[str]:
    """
    Extract key requirements from a job description.
    
    Args:
        ctx: Run context with dependencies
        job_description: Text of the job description
        
    Returns:
        List of key job requirements
    """
    # Access HTTP client from dependencies
    http_client = ctx.deps.http_client
    
    # Use HTTP client to call external API
    async with http_client.post(
        "https://api.example.com/extract-requirements",
        json={"text": job_description},
        headers={"Authorization": f"Bearer {ctx.deps.anthropic_api_key}"}
    ) as response:
        data = await response.json()
        return data["requirements"]
```

### 4. Pass Dependencies When Running the Agent

When running the agent, provide the dependencies:

```python
async def customize_resume(resume_content, job_description):
    # Create dependencies
    async with ClientSession() as http_client:
        deps = ResumeDeps(
            http_client=http_client,
            db=Database("sqlite:///resume_app.db"),
            config={"max_requirements": "10"},
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY")
        )
        
        # Run agent with dependencies
        result = await agent.run(
            f"""
            Customize this resume for the job description:
            
            RESUME:
            {resume_content}
            
            JOB DESCRIPTION:
            {job_description}
            """,
            deps=deps  # Pass dependencies to the agent
        )
        
        return result
```

## Advanced Pattern: Hierarchical Dependencies

For more complex applications, dependencies can be structured hierarchically:

```python
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class ApiClients:
    """API client dependencies."""
    http_client: ClientSession
    anthropic_client: Optional[Any] = None
    
@dataclass
class DataStores:
    """Data storage dependencies."""
    db: Database
    cache: Optional[Redis] = None
    
@dataclass
class ResumeDeps:
    """Root dependencies container."""
    apis: ApiClients
    data: DataStores
    config: Dict[str, str]
```

Tools can then access nested dependencies:

```python
@agent.tool()
async def store_customized_resume(
    ctx: RunContext[ResumeDeps],
    user_id: str,
    resume_content: str
) -> str:
    """Store a customized resume in the database."""
    # Access database from nested dependencies
    db = ctx.deps.data.db
    
    # Store resume
    resume_id = uuid.uuid4().hex
    await db.execute(
        "INSERT INTO resumes (id, user_id, content) VALUES (:id, :user_id, :content)",
        {"id": resume_id, "user_id": user_id, "content": resume_content}
    )
    
    return resume_id
```

## Application to Resume Customization

For our resume customization service, we'll implement a comprehensive dependency injection pattern:

### 1. Define Dependencies

```python
from dataclasses import dataclass
from typing import Dict, Optional, Any
from aiohttp import ClientSession
from databases import Database
from redis.asyncio import Redis

@dataclass
class ExternalServices:
    """External service clients."""
    http_client: ClientSession
    anthropic_client: Optional[Any] = None
    
@dataclass
class Storage:
    """Data storage services."""
    db: Database
    cache: Optional[Redis] = None
    
@dataclass
class ResumeCustomizerDeps:
    """Dependencies for resume customization."""
    external: ExternalServices
    storage: Storage
    websocket_manager: Optional[Any] = None
    config: Dict[str, Any] = None
```

### 2. Implement Agent Factory with Dependencies

```python
class AgentFactory:
    """Creates PydanticAI agents with dependencies for resume customization tasks."""
    
    def __init__(self, deps: ResumeCustomizerDeps):
        self.deps = deps
        self.model = "anthropic:claude-3-7-sonnet-latest"
        
    async def create_evaluation_agent(self):
        """Create an agent for resume evaluation."""
        return Agent(
            model=self.model,
            output_type=ResumeEvaluation,
            deps_type=ResumeCustomizerDeps,
            system_prompt="You are an expert resume evaluator."
        )
    
    async def create_planning_agent(self):
        """Create an agent for improvement planning."""
        return Agent(
            model=self.model,
            output_type=ImprovementPlan,
            deps_type=ResumeCustomizerDeps,
            system_prompt="You are an expert resume improvement planner."
        )
        
    # Additional agent creation methods...
```

### 3. Create Specialized Tools

```python
@agent.tool()
async def store_evaluation_result(
    ctx: RunContext[ResumeCustomizerDeps],
    customization_id: str,
    evaluation: Dict
) -> None:
    """Store evaluation results in the database."""
    db = ctx.deps.storage.db
    
    await db.execute(
        """
        UPDATE customizations 
        SET evaluation_data = :evaluation_data
        WHERE id = :id
        """,
        {
            "id": customization_id,
            "evaluation_data": json.dumps(evaluation)
        }
    )

@agent.tool()
async def report_progress(
    ctx: RunContext[ResumeCustomizerDeps],
    customization_id: str,
    stage: str,
    progress: int,
    message: str
) -> None:
    """Report progress via WebSocket."""
    if not ctx.deps.websocket_manager:
        return
        
    await ctx.deps.websocket_manager.send_json(
        customization_id, 
        {
            "stage": stage,
            "progress": progress,
            "message": message
        }
    )
```

### 4. Main Service with Dependency Injection

```python
class ResumeCustomizer:
    """Customizes resumes for job descriptions using AI with dependency injection."""
    
    def __init__(self, deps: ResumeCustomizerDeps):
        self.deps = deps
        self.agent_factory = AgentFactory(deps)
        
    async def customize_resume(self, resume_content, job_description, customization_id):
        """Customize a resume for a specific job description."""
        try:
            # Create evaluation agent
            evaluation_agent = await self.agent_factory.create_evaluation_agent()
            
            # Run evaluation with dependencies
            evaluation_result = await evaluation_agent.run(
                f"""
                Evaluate this resume against the job description:
                
                RESUME:
                {resume_content}
                
                JOB DESCRIPTION:
                {job_description}
                """,
                deps=self.deps  # Pass dependencies
            )
            
            # Store results using tool
            await store_evaluation_result(
                RunContext(self.deps), 
                customization_id, 
                evaluation_result.model_dump()
            )
            
            # Report progress
            await report_progress(
                RunContext(self.deps),
                customization_id,
                "evaluation",
                100,
                "Evaluation completed"
            )
            
            # Continue with remaining stages...
            
            return evaluation_result
            
        except Exception as e:
            # Error handling
            logfire.error(f"Error during resume customization: {str(e)}")
            raise
```

## Benefits for Our Project

Using dependency injection in our resume customization service provides several benefits:

1. **Shared Resources**: WebSocket connections, database sessions, and API clients can be shared
2. **Testability**: We can mock dependencies for unit testing
3. **Configuration**: Configuration can be centralized and distributed through dependencies
4. **Separation of Concerns**: Tools and agents focus on their tasks, not on resource management
5. **Progress Reporting**: WebSocket manager can be injected for progress updates

By following these patterns, we'll create a more maintainable, testable, and flexible resume customization service.