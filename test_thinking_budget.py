"""
Test script for the dynamic thinking budget utility.

This script tests the functionality of the thinking budget calculation for different tasks,
model providers, and content complexities.
"""

import asyncio
import logfire
from typing import List, Optional, Dict, Any

# Try to import pydanticai - wrap in try/except to handle missing dependencies
try:
    from pydanticai import Agent
    from pydantic import BaseModel, Field
    PYDANTICAI_AVAILABLE = True
except ImportError:
    print("WARNING: PydanticAI not installed - skipping model tests")
    PYDANTICAI_AVAILABLE = False
    
    # Create placeholder classes for testing
    class BaseModel:
        class Config:
            pass
            
    class Field:
        def __init__(self, *args, **kwargs):
            pass

from app.services.thinking_budget import (
    TaskComplexity,
    InputMetrics,
    calculate_thinking_budget,
    get_task_complexity_from_content,
    get_thinking_config_for_task
)

# Set up logging
try:
    logfire.configure(min_level="INFO", sinks=["console"])
except Exception as e:
    print(f"Warning: Unable to configure logfire: {str(e)}")

# Sample schema for testing
class SimpleResponse(BaseModel):
    """Simple response schema with a numbered list of facts."""
    facts: List[str] = Field(..., description="List of facts")
    summary: str = Field(..., description="Summary of facts")

# Sample resume content for testing
SAMPLE_RESUME = """
# John Doe
Software Engineer | johndoe@example.com | (123) 456-7890

## Summary
Experienced software engineer with 8+ years of experience in full-stack development, 
specializing in React, Node.js, and cloud infrastructure.

## Experience
### Senior Software Engineer | ABC Tech | 2019 - Present
- Led a team of 5 engineers in developing a high-traffic e-commerce platform
- Implemented microservices architecture using Node.js, resulting in 40% improved scalability
- Reduced page load time by 60% through optimization of React components and server-side rendering

### Software Engineer | XYZ Inc. | 2015 - 2019
- Developed and maintained RESTful APIs for mobile and web applications
- Implemented automated testing, increasing code coverage from 65% to 95%
- Participated in agile development workflows, including daily stand-ups and sprint planning

## Education
### Bachelor of Science in Computer Science | State University | 2015
- GPA: 3.8/4.0
- Senior Thesis: "Optimizing Database Performance in Distributed Systems"

## Skills
**Programming Languages**: JavaScript, TypeScript, Python, Java, SQL
**Frameworks/Libraries**: React, Node.js, Express, Django, Spring Boot
**Tools & Platforms**: AWS, Docker, Kubernetes, Git, Jenkins, MongoDB, PostgreSQL
"""

# Sample job description for testing
SAMPLE_JOB = """
# Senior Full Stack Engineer

## About Us
We're a fast-growing technology company building innovative solutions for the healthcare sector.

## Job Description
We are looking for a Senior Full Stack Engineer to join our engineering team. The ideal candidate will 
have expertise in building complex web applications and will collaborate with cross-functional teams 
to deliver high-quality software solutions.

## Requirements
- 5+ years of experience in full-stack web development
- Strong proficiency in JavaScript/TypeScript, React, and Node.js
- Experience with database design and SQL/NoSQL databases
- Understanding of cloud services (AWS, Azure, or GCP)
- Knowledge of containerization tools like Docker and Kubernetes
- Experience with agile development methodologies
- Bachelor's degree in Computer Science or related field

## Responsibilities
- Design and implement new features for our healthcare platform
- Write clean, maintainable, and efficient code
- Collaborate with product managers, designers, and other engineers
- Participate in code reviews and mentor junior developers
- Troubleshoot and debug issues in production environments
- Implement automated tests and deployment pipelines

## Benefits
- Competitive salary and equity package
- Health, dental, and vision insurance
- Flexible work hours and remote work options
- Professional development budget
- Generous vacation policy
"""

async def test_thinking_budget_calculations():
    """Test thinking budget calculations for different complexity levels."""
    print("\n=== Testing Thinking Budget Calculations ===")
    
    # Test for each complexity level
    for complexity in TaskComplexity:
        print(f"\nTesting {complexity.value} task complexity:")
        
        for provider in ["anthropic", "google"]:
            tokens, config = calculate_thinking_budget(
                task_complexity=complexity,
                model_provider=provider,
                input_metrics=InputMetrics(total_tokens=2000, section_count=5)
            )
            
            print(f"  {provider.capitalize()} Provider:")
            print(f"    Budget: {tokens} tokens")
            print(f"    Config: {config}")

async def test_content_complexity_analysis():
    """Test content analysis for complexity determination."""
    print("\n=== Testing Content Complexity Analysis ===")
    
    # Test with sample resume and job
    complexity, metrics = get_task_complexity_from_content(
        content=SAMPLE_RESUME,
        job_description=SAMPLE_JOB,
        industry="technology"
    )
    
    print(f"Resume Complexity: {complexity.value}")
    print(f"Total Tokens: {metrics.total_tokens}")
    print(f"Section Count: {metrics.section_count}")
    print(f"Keyword Count: {metrics.keyword_count}")
    print(f"Complexity Score: {metrics.complexity_score:.2f}")
    
    # Test with shorter content
    short_resume = "John Doe\nSoftware Engineer\nSkills: JavaScript, Python\nEducation: BS Computer Science"
    complexity, metrics = get_task_complexity_from_content(
        content=short_resume,
        job_description=None
    )
    
    print("\nShort Resume Complexity:")
    print(f"Complexity: {complexity.value}")
    print(f"Total Tokens: {metrics.total_tokens}")
    print(f"Complexity Score: {metrics.complexity_score:.2f}")

async def test_task_specific_config():
    """Test getting task-specific thinking configurations."""
    print("\n=== Testing Task-Specific Configurations ===")
    
    tasks = [
        "keyword_extraction",
        "resume_evaluation",
        "optimization_plan",
        "cover_letter_generation"
    ]
    
    for task in tasks:
        for provider in ["anthropic", "google"]:
            config = get_thinking_config_for_task(
                task_name=task,
                model_provider=provider,
                content=SAMPLE_RESUME,
                job_description=SAMPLE_JOB,
                industry="technology"
            )
            
            print(f"\n{task} ({provider}):")
            print(f"  Config: {config}")

async def test_with_gemini_model():
    """Test models with different thinking budgets."""
    print("\n=== Testing with Gemini Model ===")
    
    if not PYDANTICAI_AVAILABLE:
        print("PydanticAI not available - skipping model test")
        return
    
    try:
        # Create an agent with no thinking budget
        agent_no_thinking = Agent(
            "google:gemini-2.5-flash-preview-04-17",
            output_type=SimpleResponse,
            system_prompt="You are a helpful assistant that generates numbered facts.",
            thinking_config={"thinkingBudget": 0}  # No thinking
        )
        
        # Create an agent with thinking budget
        thinking_config = get_thinking_config_for_task(
            task_name="resume_evaluation",
            model_provider="google",
            content=SAMPLE_RESUME,
            job_description=SAMPLE_JOB
        )
        
        agent_with_thinking = Agent(
            "google:gemini-2.5-flash-preview-04-17",
            output_type=SimpleResponse,
            system_prompt="You are a helpful assistant that generates numbered facts.",
            thinking_config=thinking_config
        )
        
        print(f"Testing with thinking config: {thinking_config}")
        
        # Run both agents with the same prompt
        prompt = "List 3 facts about machine learning in healthcare."
        
        print("\nRunning agent with NO thinking...")
        start_time = asyncio.get_event_loop().time()
        result_no_thinking = await agent_no_thinking.run(prompt)
        no_thinking_time = asyncio.get_event_loop().time() - start_time
        
        print("\nRunning agent WITH thinking...")
        start_time = asyncio.get_event_loop().time()
        result_with_thinking = await agent_with_thinking.run(prompt)
        with_thinking_time = asyncio.get_event_loop().time() - start_time
        
        # Output results
        print("\nResults without thinking:")
        print(f"Time: {no_thinking_time:.2f} seconds")
        print(f"Facts: {result_no_thinking.facts}")
        print(f"Summary: {result_no_thinking.summary}")
        
        print("\nResults with thinking:")
        print(f"Time: {with_thinking_time:.2f} seconds")
        print(f"Facts: {result_with_thinking.facts}")
        print(f"Summary: {result_with_thinking.summary}")
        
    except Exception as e:
        print(f"Error testing models: {str(e)}")
        import traceback
        traceback.print_exc()

async def run_tests():
    """Run all tests."""
    await test_thinking_budget_calculations()
    await test_content_complexity_analysis()
    await test_task_specific_config()
    
    # Only run the model test if requested explicitly
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--with-model":
        await test_with_gemini_model()

if __name__ == "__main__":
    print("Testing Dynamic Thinking Budget utility...")
    asyncio.run(run_tests())
    print("\nTests completed.")