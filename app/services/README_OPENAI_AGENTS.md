# OpenAI Agents Service

This module implements the evaluator-optimizer pattern using the OpenAI Agents SDK for AI-driven resume customization.

## Overview

The `openai_agents_service.py` module replaces the existing Claude-based implementation with the OpenAI Agents SDK. It maintains the same API interface while leveraging OpenAI's specialized agents for various tasks.

## Key Components

- **Resume Evaluator Agent**: Analyzes how well a resume matches a job description
- **Resume Optimizer Agent**: Creates customization plans based on evaluation results
- **Cover Letter Agent**: Generates personalized cover letters

## Functions

The module maintains the same function signatures as the Claude-based service:

- `evaluate_resume_job_match`: Evaluates how well a resume matches a job description
- `generate_optimization_plan`: Generates a customization plan based on evaluation results
- `customize_resume`: Directly customizes a resume for a specific job
- `generate_cover_letter`: Creates a personalized cover letter

## Configuration

Configuration is managed through the settings in `app/core/config.py`:

```python
# OpenAI API
OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-2024-05-13")
OPENAI_EVALUATOR_MODEL: str = os.getenv("OPENAI_EVALUATOR_MODEL", "o3")
OPENAI_OPTIMIZER_MODEL: str = os.getenv("OPENAI_OPTIMIZER_MODEL", "o3")
```

## Model Recommendations

- For best results, use `gpt-4o-2024-05-13` as the general model
- For cost optimization, use `o3` or `o3-mini` for the evaluator and optimizer agents

## Example Usage

```python
import asyncio
from app.services.openai_agents_service import evaluate_resume_job_match, generate_optimization_plan
from app.schemas.customize import CustomizationLevel

async def optimize_resume(resume_content, job_description):
    # Step 1: Evaluate resume match
    evaluation = await evaluate_resume_job_match(
        resume_content=resume_content,
        job_description=job_description,
        customization_level=CustomizationLevel.BALANCED
    )
    
    # Step 2: Generate optimization plan
    plan = await generate_optimization_plan(
        resume_content=resume_content,
        job_description=job_description,
        evaluation=evaluation,
        customization_level=CustomizationLevel.BALANCED
    )
    
    return plan

# Run the async function
plan = asyncio.run(optimize_resume(resume_content, job_description))
```

## Testing

You can test the implementation using the provided test scripts:

- `test_openai_agents.py`: Basic demonstration of the OpenAI Agents service
- `test_comparison.py`: Compares Claude and OpenAI implementations side by side
- `tests/integration/test_openai_agents.py`: Unit tests for the OpenAI Agents service

## Error Handling

The service includes robust error handling:

- API key validation
- JSON parsing error recovery with fallback responses
- Request/response logging with logfire
- Exception handling with proper error propagation

## Instrumentation and Logging

The OpenAI client is instrumented using logfire:

```python
# Create the OpenAI client
client = OpenAI(api_key=settings.OPENAI_API_KEY)

# Setup instrumentation for this specific client
setup_openai_instrumentation(client)
```

## Performance Considerations

- The o3-series models provide good reasoning capabilities at lower cost
- Agent creation can be time-consuming, so caching strategies may be beneficial
- Monitor token usage for cost optimization