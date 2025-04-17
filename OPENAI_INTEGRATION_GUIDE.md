# OpenAI Integration Guide

This guide explains how to use the OpenAI Agents SDK integration in the Resume AI Assistant.

## Table of Contents

1. [Installation](#installation)
2. [Configuration](#configuration)
3. [Usage](#usage)
4. [Advanced Features](#advanced-features)
5. [Troubleshooting](#troubleshooting)

## Installation

To install the required dependencies for the OpenAI integration:

```bash
uv add openai-agents
```

## Configuration

Set the following environment variables:

```bash
export OPENAI_API_KEY=your-api-key
```

You can also configure the specific models to use in `app/core/config.py`:

```python
# Default to gpt-4o for best performance
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-2024-05-13")

# Models for specific tasks
OPENAI_EVALUATOR_MODEL: str = os.getenv("OPENAI_EVALUATOR_MODEL", "gpt-4o-2024-05-13")
OPENAI_OPTIMIZER_MODEL: str = os.getenv("OPENAI_OPTIMIZER_MODEL", "gpt-4o-2024-05-13")
```

## Usage

The OpenAI integration provides the same functions as the Claude-based implementation:

```python
from app.services.openai_agents_service import (
    evaluate_resume_job_match,
    generate_optimization_plan,
    customize_resume,
    generate_cover_letter
)
```

### Evaluate Resume-Job Match

```python
evaluation = await evaluate_resume_job_match(
    resume_content="Your resume content...",
    job_description="Job description...",
    customization_level=CustomizationLevel.BALANCED,
    industry="technology"  # Optional
)
```

### Generate Optimization Plan

```python
plan = await generate_optimization_plan(
    resume_content="Your resume content...",
    job_description="Job description...",
    evaluation=evaluation,  # Results from evaluate_resume_job_match
    customization_level=CustomizationLevel.BALANCED,
    industry="technology"  # Optional
)
```

### Customize Resume

```python
customized_resume = await customize_resume(
    resume_content="Your resume content...",
    job_description="Job description...",
    customization_strength=2,  # 1=minimal, 2=moderate, 3=extensive
    focus_areas="Skills, Experience"  # Optional
)
```

### Generate Cover Letter

```python
cover_letter = await generate_cover_letter(
    resume_content="Your resume content...",
    job_description="Job description...",
    applicant_name="John Doe",  # Optional
    company_name="Acme Corp",  # Optional
    hiring_manager_name="Jane Smith",  # Optional
    additional_context="I was referred by...",  # Optional
    tone="professional"  # Optional
)
```

## Advanced Features

### Customization Levels

Three levels of customization are available:

- **Conservative** (`CustomizationLevel.CONSERVATIVE`): Minimal changes, focusing only on the most critical aspects
- **Balanced** (`CustomizationLevel.BALANCED`): Moderate changes to highlight relevant experience and skills
- **Extensive** (`CustomizationLevel.EXTENSIVE`): More aggressive optimization for maximum impact

### Industry-Specific Guidance

You can provide an industry name to get industry-specific optimization guidance:

```python
evaluation = await evaluate_resume_job_match(
    resume_content="...",
    job_description="...",
    industry="technology"  # Or "healthcare", "finance", "marketing", "education"
)
```

## Troubleshooting

### Model Errors

If you encounter errors related to model availability:

```
Error code: 404 - {'error': {'message': 'Your organization must be verified to use the model...'}}
```

Update the model names in `app/core/config.py` to use models that are available to your OpenAI account:

```python
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-2024-05-13")
OPENAI_EVALUATOR_MODEL: str = os.getenv("OPENAI_EVALUATOR_MODEL", "gpt-4o-2024-05-13")
OPENAI_OPTIMIZER_MODEL: str = os.getenv("OPENAI_OPTIMIZER_MODEL", "gpt-4o-2024-05-13")
```

### API Key Issues

If you see authentication errors:

```
Error calling OpenAI API: Authentication error
```

Make sure your API key is set correctly:

```bash
export OPENAI_API_KEY=your-api-key
```

### Testing the Implementation

Run the test script to verify everything is working:

```bash
python test_openai_service.py
```

### Comparing Claude vs. OpenAI

You can run the comparison test to see the differences between Claude and OpenAI implementations:

```bash
python test_comparison.py
```

This will generate a `comparison_results.json` file with detailed timing and output comparisons.