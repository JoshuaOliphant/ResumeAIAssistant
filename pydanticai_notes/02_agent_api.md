# PydanticAI Agent API

The `Agent` class is the primary interface for working with AI models in PydanticAI. It manages interaction with AI models, handling prompts, generating completions, and converting responses to the desired output format.

## Initialization

```python
agent = Agent(
    model="anthropic:claude-3-7-sonnet-latest",
    output_type=MyOutputModel,
    system_prompt="Be helpful and concise",
    instructions=None,
    tools=None,
    deps_type=None,
    name=None
)
```

### Parameters

- **model** (str): The AI model to use. Format is "provider:model_name"
  - Anthropic: "anthropic:claude-3-7-sonnet-latest", "anthropic:claude-3-opus-latest", etc.
  - OpenAI: "openai:gpt-4o", "openai:gpt-4", etc.
  - Google: "google-gla:gemini-1.5-flash", etc.
- **output_type** (Type): A Pydantic model class or other type defining the structure of the output
- **system_prompt** (str, optional): A system prompt to guide the model's behavior
- **instructions** (list, optional): List of instruction generators
- **tools** (list, optional): List of tools the agent can use
- **deps_type** (Type, optional): Dependency injection type
- **name** (str, optional): Name for logging purposes

## Core Methods

### run

```python
result = await agent.run(prompt, images=None)
```

Executes the agent with the given prompt and returns a structured result of the specified output_type.

- **prompt** (str): The prompt to send to the model
- **images** (list, optional): List of image URLs or base64 encoded images (for multimodal models)
- **returns**: An instance of the output_type specified during initialization

### run_sync

```python
result = agent.run_sync(prompt, images=None)
```

Synchronous version of `run()`.

### run_stream

```python
async for partial_response in agent.run_stream(prompt, images=None):
    print(partial_response)
```

Streams the response from the model as it's generated.

## Example for Resume Customization

```python
from pydantic_ai import Agent
from pydantic import BaseModel, Field
from typing import List

class ResumeEvaluation(BaseModel):
    match_score: int = Field(description="Overall match score (0-100)")
    strengths: List[str] = Field(description="Resume strengths for this job")
    gaps: List[str] = Field(description="Areas for improvement")
    missing_keywords: List[str] = Field(description="Keywords from job not in resume")

async def evaluate_resume(resume_content, job_description):
    agent = Agent(
        model="anthropic:claude-3-7-sonnet-latest",
        output_type=ResumeEvaluation,
        system_prompt="You are an expert resume evaluator."
    )
    
    prompt = f"""
    Evaluate how well this resume matches the job description:
    
    RESUME:
    {resume_content}
    
    JOB DESCRIPTION:
    {job_description}
    
    Provide a detailed evaluation focusing on match score, strengths, 
    gaps, and missing keywords.
    """
    
    evaluation = await agent.run(prompt)
    return evaluation
```

## Application to Our Architecture

In the redesigned Resume Customization Service, we'll use separate agents for each stage of the workflow:

1. **Evaluation Agent**: Assess resume-job match
2. **Planning Agent**: Generate improvement plan
3. **Implementation Agent**: Apply changes to resume
4. **Verification Agent**: Verify truthfulness of customizations

Each agent will use a specialized Pydantic model for its output, ensuring structured and validated data flows between stages.