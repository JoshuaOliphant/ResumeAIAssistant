# PydanticAI Tools Integration

PydanticAI provides a powerful tools system that allows agents to interact with external systems, APIs, and functions. This document explores how to implement and use tools in the resume customization service.

## Understanding Tools in PydanticAI

Tools in PydanticAI are functions that can be registered with agents, enabling them to:

1. Fetch external data (e.g., job listings, resume formatting guidelines)
2. Perform complex calculations
3. Access specialized functionalities (e.g., resume parsing, ATS compatibility checks)
4. Store and retrieve state during the agent's execution

## Basic Tool Implementation

Tools can be implemented as either synchronous or asynchronous functions:

```python
from pydantic_ai import Agent, Tool
from pydantic_ai.run_context import RunContext
from typing import Dict, List, Optional

# Simple synchronous tool
def parse_skills(text: str) -> List[str]:
    """
    Extract skills from text.
    
    Args:
        text: Text containing skills to extract
        
    Returns:
        List of extracted skills
    """
    # Implementation that parses skills from text
    skills = [skill.strip() for skill in text.split(",") if skill.strip()]
    return skills

# Asynchronous tool with context
async def fetch_job_description(
    ctx: RunContext[Dict], 
    job_url: str
) -> str:
    """
    Fetch a job description from a URL.
    
    Args:
        ctx: Run context containing dependencies
        job_url: URL of the job listing
        
    Returns:
        Extracted job description text
    """
    # Access HTTP client from dependencies
    http_client = ctx.deps.get("http_client")
    
    # Fetch job description
    response = await http_client.get(job_url)
    
    # Process and return the job description
    if response.status_code == 200:
        # Process HTML to extract job description
        return extract_job_description(response.text)
    else:
        raise ValueError(f"Failed to fetch job description: {response.status_code}")

# Creating agent with tools
agent = Agent(
    model="anthropic:claude-3-7-sonnet-latest",
    tools=[
        Tool(parse_skills),
        Tool(fetch_job_description)
    ]
)
```

## Advanced Tool Configuration

Tools can be configured with various options:

```python
from pydantic_ai import Agent, Tool

agent = Agent(
    model="anthropic:claude-3-7-sonnet-latest",
    tools=[
        Tool(
            parse_skills,
            name="extract_skills",  # Custom name
            description="Extract skills from resume text",  # Custom description
            max_retries=3,  # Retry on failure
            takes_ctx=False,  # Doesn't take a context parameter
            strict=True  # Strict parameter validation
        )
    ]
)
```

## Dynamic Tool Registration

Tools can also be registered dynamically using the decorator pattern:

```python
from pydantic_ai import Agent

agent = Agent(model="anthropic:claude-3-7-sonnet-latest")

@agent.tool()
async def analyze_experience(experience_text: str) -> Dict:
    """
    Analyze an experience section from a resume.
    
    Args:
        experience_text: Text from the experience section
        
    Returns:
        Analysis of the experience section
    """
    # Implementation
    return {
        "duration": calculate_duration(experience_text),
        "keywords": extract_keywords(experience_text),
        "achievements": identify_achievements(experience_text)
    }
```

## Building a Tool-Enhanced Resume Customizer

For our resume customization service, we can implement specialized tools to enhance the workflow:

```python
from pydantic_ai import Agent, Tool
from typing import Dict, List
import aiohttp
import re

# Tool for extracting keywords from job descriptions
async def extract_job_keywords(job_description: str) -> List[str]:
    """
    Extract important keywords from a job description.
    
    Args:
        job_description: The full job description text
        
    Returns:
        List of extracted keywords in priority order
    """
    # Implementation using NLP or regex patterns
    # This is a simplified example
    words = re.findall(r'\b\w+\b', job_description.lower())
    frequency = {}
    for word in words:
        if word not in frequency:
            frequency[word] = 0
        frequency[word] += 1
    
    # Filter common words and sort by frequency
    common_words = {"the", "and", "a", "to", "of", "is", "in", "for", "with", "on"}
    keywords = [word for word, count in sorted(
        frequency.items(), 
        key=lambda x: x[1], 
        reverse=True
    ) if word not in common_words]
    
    return keywords[:20]  # Return top 20 keywords

# Tool for checking ATS compatibility
async def check_ats_compatibility(resume_text: str) -> Dict:
    """
    Check if a resume is ATS-friendly.
    
    Args:
        resume_text: The resume content
        
    Returns:
        Dictionary with ATS compatibility metrics
    """
    # Implementation of ATS compatibility checking
    has_tables = "<table" in resume_text.lower()
    has_images = re.search(r'<img|\.jpg|\.png|\.gif', resume_text.lower()) is not None
    has_complex_formatting = re.search(r'</?div|</?span', resume_text.lower()) is not None
    
    return {
        "is_ats_friendly": not (has_tables or has_images or has_complex_formatting),
        "issues": [
            "Contains tables" if has_tables else None,
            "Contains images" if has_images else None,
            "Contains complex formatting" if has_complex_formatting else None
        ],
        "score": 100 - (20 * sum([has_tables, has_images, has_complex_formatting]))
    }

# ResumeCustomizer with tools
class ToolEnhancedResumeCustomizer:
    """Resume customizer with integrated tools."""
    
    def __init__(self, api_key):
        self.agent = Agent(
            model="anthropic:claude-3-7-sonnet-latest",
            tools=[
                Tool(extract_job_keywords),
                Tool(check_ats_compatibility)
            ]
        )
    
    async def customize_resume(self, resume_content, job_description):
        """Customize a resume for a specific job using tools."""
        # Run the agent with access to tools
        result = await self.agent.run(
            f"""
            Customize this resume for the job description provided.
            
            RESUME:
            {resume_content}
            
            JOB DESCRIPTION:
            {job_description}
            
            First, extract keywords from the job description.
            Then, check if the resume is ATS-friendly.
            Finally, create a customized version of the resume
            that highlights relevant experience and skills.
            """
        )
        
        return result
```

## Application to Our Architecture

In our resume customization service, we can implement several useful tools:

1. **KeywordExtractionTool**: Extract keywords from job descriptions
2. **ATSCompatibilityTool**: Check resume ATS compatibility 
3. **SkillExtractorTool**: Parse skills from resume text
4. **RequirementMatcherTool**: Match resume content to job requirements
5. **FormatOptimizerTool**: Optimize resume formatting for readability

These tools can be integrated at different stages of our workflow:

- **Evaluation Stage**: Use keyword extraction and requirement matching tools
- **Planning Stage**: Use requirement matching to identify gaps
- **Implementation Stage**: Use format optimizer for the final resume
- **Verification Stage**: Use ATS compatibility tool to ensure the resume is ATS-friendly

## Best Practices for Tool Implementation

1. **Keep Tools Focused**: Each tool should have a single, clear responsibility
2. **Robust Error Handling**: Handle errors gracefully within tools
3. **Clear Documentation**: Provide comprehensive docstrings for tools
4. **Type Annotations**: Use proper type hints for all parameters and return values
5. **Context Awareness**: Pass context to tools that need access to shared resources
6. **Idempotency**: Design tools to be safely retried if they fail
7. **Testing**: Thoroughly test tools with unit and integration tests