# PydanticAI Agent Configuration

This document covers advanced configuration options for PydanticAI agents, focusing on settings relevant to the resume customization service.

## Basic Agent Initialization

The most basic agent initialization looks like this:

```python
from pydantic_ai import Agent

agent = Agent(
    model="anthropic:claude-3-7-sonnet-latest",
    output_type=str
)
```

## Model Configuration Options

PydanticAI supports various model configuration options:

```python
agent = Agent(
    # Model selection (provider:model_name format)
    model="anthropic:claude-3-7-sonnet-latest",
    
    # Output format definition
    output_type=ResumeEvaluation,
    
    # General guidance
    system_prompt="You are an expert resume evaluator.",
    
    # Generation parameters
    model_kwargs={
        "temperature": 0.2,  # Lower for more deterministic outputs
        "max_tokens": 1500,  # Control response length
        "top_p": 0.95,  # Nucleus sampling parameter
    }
)
```

## Using Instructions vs. System Prompts

PydanticAI recommends using instructions over system prompts for more flexibility:

```python
from pydantic_ai.run_context import RunContext

agent = Agent(
    model="anthropic:claude-3-7-sonnet-latest",
    output_type=ResumeEvaluation
)

@agent.instructions()
def provide_instructions(ctx: RunContext) -> str:
    """Generate dynamic instructions at runtime."""
    return f"""
    You are an expert resume evaluator with {ctx.deps.years_experience} years 
    of experience in the {ctx.deps.industry} industry.
    
    Provide a detailed evaluation of how well the resume matches job requirements.
    Focus on relevance, skills match, and improvement opportunities.
    """
```

## Model-Specific Settings

Different models may have specific configuration options:

```python
# Claude 3.7 Sonnet configuration
claude_agent = Agent(
    model="anthropic:claude-3-7-sonnet-latest",
    model_kwargs={
        "temperature": 0.2,
        "max_tokens": 1500,
        "top_p": 0.95,
    }
)

# GPT-4o configuration (if needed as fallback)
gpt_agent = Agent(
    model="openai:gpt-4o",
    model_kwargs={
        "temperature": 0.3,
        "max_tokens": 2000,
        "top_p": 0.9,
        "frequency_penalty": 0.5,
        "presence_penalty": 0.5,
    }
)
```

## Output Validation and Retry

PydanticAI provides mechanisms for validating outputs and triggering retries:

```python
from pydantic_ai import ModelRetry

agent = Agent(
    model="anthropic:claude-3-7-sonnet-latest",
    output_type=ResumeEvaluation
)

@agent.output_validator()
def validate_evaluation(evaluation: ResumeEvaluation) -> None:
    """Validate evaluation output and trigger retry if needed."""
    # Check that the overall score is within bounds
    if not (0 <= evaluation.overall_match_score <= 100):
        raise ModelRetry(
            "Overall match score must be between 0 and 100. Please recalculate."
        )
    
    # Ensure there are at least 3 strengths identified
    if len(evaluation.top_strengths) < 3:
        raise ModelRetry(
            "Please identify at least 3 strengths in the resume."
        )
```

## Timeout and Usage Control

Control resource usage with timeout and token limits:

```python
agent = Agent(
    model="anthropic:claude-3-7-sonnet-latest",
    output_type=ResumeEvaluation,
    # Set timeout for the entire agent call (in seconds)
    timeout=60,
    # Control token usage
    usage_limits={
        "max_input_tokens": 4000,  # Limit input size
        "max_output_tokens": 2000,  # Limit output size
        "max_hourly_requests": 100,  # Rate limiting
    }
)
```

## Context Window Management

For working with larger resumes and job descriptions:

```python
from pydantic_ai.utils import count_tokens

async def process_large_resume(resume_content, job_description):
    # Count tokens to check context window limits
    resume_tokens = count_tokens(resume_content, model="anthropic:claude-3-7-sonnet-latest")
    job_tokens = count_tokens(job_description, model="anthropic:claude-3-7-sonnet-latest")
    
    # If total exceeds safe limit, truncate or summarize
    max_safe_tokens = 3500  # Leave room for system prompt and output
    if resume_tokens + job_tokens > max_safe_tokens:
        # Truncate or summarize
        if resume_tokens > job_tokens:
            resume_content = truncate_resume(resume_content, max_safe_tokens - job_tokens - 500)
        else:
            job_description = summarize_job_description(job_description, 1500)
    
    # Create agent with appropriate context window
    agent = Agent(
        model="anthropic:claude-3-7-sonnet-latest",
        output_type=ResumeEvaluation,
        model_kwargs={
            "max_tokens": 2000,
        }
    )
    
    # Run agent with prepared content
    return await agent.run(
        f"""
        Evaluate how well this resume matches the job description:
        
        RESUME:
        {resume_content}
        
        JOB DESCRIPTION:
        {job_description}
        """
    )
```

## Configuring Tool Usage

Configure how agents use tools:

```python
from pydantic_ai import Agent, Tool

# Define tools with retry configuration
keyword_extractor = Tool(
    extract_keywords,
    max_retries=3,  # Allow up to 3 retries
)

# Create agent with tools and tool configuration
agent = Agent(
    model="anthropic:claude-3-7-sonnet-latest",
    output_type=str,
    tools=[keyword_extractor],
    # Configure how the agent should use tools
    tool_config={
        "max_tool_calls": 10,  # Maximum number of tool calls per agent execution
        "auto_retry_count": 2,  # Auto-retry tools on failure
    }
)
```

## Streaming Configuration

Configure streaming behavior for progress reporting:

```python
agent = Agent(
    model="anthropic:claude-3-7-sonnet-latest",
    output_type=ResumeEvaluation,
    streaming_config={
        "chunk_size": 10,  # Characters per chunk
        "min_chunk_time_ms": 50,  # Minimum time between chunks
    }
)

# Stream the response
async def stream_customization_progress(resume_content, job_description):
    """Stream customization progress for real-time updates."""
    async for partial_result in agent.run_stream(
        f"""
        Customize this resume for the job description:
        
        RESUME:
        {resume_content}
        
        JOB DESCRIPTION:
        {job_description}
        """
    ):
        # Report progress based on partial result
        progress = estimate_progress(partial_result)
        yield {
            "progress": progress,
            "partial_result": partial_result
        }
```

## Optimized Configuration for Resume Customization

Based on our understanding of PydanticAI configuration options, here's an optimized configuration for the resume customization service:

```python
class ResumeCustomizerAgentFactory:
    """Creates optimized agents for different resume customization stages."""
    
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = "anthropic:claude-3-7-sonnet-latest"
    
    def create_evaluation_agent(self):
        """Create an agent optimized for resume evaluation."""
        return Agent(
            model=self.model,
            output_type=ResumeEvaluation,
            system_prompt="""
            You are an expert resume evaluator with deep knowledge of recruitment 
            and applicant tracking systems (ATS).
            """,
            model_kwargs={
                "temperature": 0.2,  # Low temperature for consistent evaluations
                "max_tokens": 1500,
            },
            timeout=45  # 45 seconds timeout
        )
    
    def create_planning_agent(self):
        """Create an agent optimized for improvement planning."""
        return Agent(
            model=self.model,
            output_type=ImprovementPlan,
            system_prompt="""
            You are an expert resume improvement strategist who creates
            actionable plans to optimize resumes for specific job descriptions.
            """,
            model_kwargs={
                "temperature": 0.3,  # Slightly higher for creative improvements
                "max_tokens": 2000,
            },
            timeout=60  # 60 seconds timeout
        )
    
    def create_implementation_agent(self):
        """Create an agent optimized for implementing changes."""
        return Agent(
            model=self.model,
            output_type=str,  # Plain text output for the resume
            system_prompt="""
            You are an expert resume writer with a focus on clear, 
            ATS-friendly formatting and compelling, truthful content.
            """,
            model_kwargs={
                "temperature": 0.4,  # Higher for varied phrasing
                "max_tokens": 4000,  # Larger output for full resume
            },
            timeout=90  # 90 seconds timeout
        )
    
    def create_verification_agent(self):
        """Create an agent optimized for verification."""
        return Agent(
            model=self.model,
            output_type=VerificationResult,
            system_prompt="""
            You are a fact-checking expert who verifies that resume customizations
            maintain truthfulness and do not fabricate information.
            """,
            model_kwargs={
                "temperature": 0.1,  # Very low for accurate verification
                "max_tokens": 1500,
            },
            timeout=45  # 45 seconds timeout
        )
```

This configuration provides optimized agents for each stage of the resume customization workflow, with appropriate settings for the specific tasks they need to perform.