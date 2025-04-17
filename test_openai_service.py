"""
Test script for the OpenAI Agents Service module.
This tests the full implementation of the service.
"""
import asyncio
import os
import time
from pprint import pprint
import json

import logfire
from app.schemas.customize import CustomizationLevel

# Configure logging
logfire.configure(service_name="resume-ai-assistant-test", console={"verbose": True})

# Import after logging is configured
from app.services.openai_agents_service import (
    evaluate_resume_job_match, 
    generate_optimization_plan, 
    customize_resume
)

# Sample data
SAMPLE_RESUME = """# John Smith
**Software Engineer**
john.smith@example.com | (555) 123-4567 | San Francisco, CA

## Summary
Experienced software engineer with 5+ years of experience in full-stack web development, specializing in React, Node.js, and Python. Proven track record of delivering high-quality software solutions on time and within budget.

## Experience
### Senior Software Engineer, Tech Solutions Inc.
*Jan 2020 - Present*
- Developed and maintained multiple React-based web applications
- Implemented RESTful APIs using Node.js and Express
- Reduced application load time by 40% through code optimization
- Led a team of 3 junior developers on various projects

### Software Developer, Digital Innovations LLC
*Jun 2017 - Dec 2019*
- Built responsive web applications using React and Redux
- Created backend services with Python and Django
- Implemented automated testing using Jest and Pytest
- Collaborated with design and product teams to deliver user-friendly interfaces

## Education
**Bachelor of Science in Computer Science**
University of California, Berkeley
*Graduated: May 2017*

## Skills
- Languages: JavaScript, Python, HTML, CSS, SQL
- Frameworks: React, Node.js, Express, Django
- Tools: Git, Docker, AWS, Jest, Pytest
- Other: RESTful APIs, Agile methodologies, CI/CD pipelines
"""

SAMPLE_JOB_DESCRIPTION = """
# Senior Frontend Developer

Our fast-growing tech company is looking for a Senior Frontend Developer to join our product team. You will be responsible for building responsive and interactive web applications that provide exceptional user experiences.

## Responsibilities:
- Develop and maintain responsive web applications using React and TypeScript
- Collaborate with UX/UI designers to implement visually appealing interfaces
- Optimize applications for maximum speed and scalability
- Implement automated testing to ensure code quality and performance
- Mentor junior developers and conduct code reviews
- Stay up-to-date with emerging trends and technologies

## Requirements:
- 5+ years of experience with frontend development
- Strong proficiency in React, Redux, and TypeScript
- Experience with modern frontend build tools (Webpack, Babel, etc.)
- Knowledge of responsive design principles and CSS preprocessors
- Understanding of cross-browser compatibility issues and solutions
- Experience with testing frameworks like Jest and React Testing Library
- Excellent problem-solving skills and attention to detail
- Strong communication and collaboration abilities
- Bachelor's degree in Computer Science or related field

## Preferred Qualifications:
- Experience with GraphQL and Apollo Client
- Knowledge of Node.js and Express
- Familiarity with AWS or other cloud platforms
- Experience with CI/CD pipelines
- Contributions to open-source projects
"""

async def test_evaluate_match():
    """Test the evaluate_resume_job_match function."""
    print("\n=== Testing evaluate_resume_job_match ===\n")
    start_time = time.time()
    
    result = await evaluate_resume_job_match(
        resume_content=SAMPLE_RESUME,
        job_description=SAMPLE_JOB_DESCRIPTION,
        customization_level=CustomizationLevel.BALANCED
    )
    
    elapsed = time.time() - start_time
    print(f"Evaluation completed in {elapsed:.2f} seconds")
    print("\nEvaluation Result:")
    print(json.dumps(result, indent=2))
    
    assert isinstance(result, dict)
    assert "match_score" in result
    assert "strengths" in result
    assert "gaps" in result
    
    return result

async def test_generate_plan(evaluation):
    """Test the generate_optimization_plan function."""
    print("\n=== Testing generate_optimization_plan ===\n")
    start_time = time.time()
    
    result = await generate_optimization_plan(
        resume_content=SAMPLE_RESUME,
        job_description=SAMPLE_JOB_DESCRIPTION,
        evaluation=evaluation,
        customization_level=CustomizationLevel.BALANCED
    )
    
    elapsed = time.time() - start_time
    print(f"Optimization plan generation completed in {elapsed:.2f} seconds")
    print("\nOptimization Plan:")
    print(json.dumps(result.model_dump(), indent=2))
    
    assert hasattr(result, "summary")
    assert hasattr(result, "recommendations")
    assert len(result.recommendations) > 0
    
    return result

async def test_customize_resume():
    """Test the customize_resume function."""
    print("\n=== Testing customize_resume ===\n")
    start_time = time.time()
    
    result = await customize_resume(
        resume_content=SAMPLE_RESUME,
        job_description=SAMPLE_JOB_DESCRIPTION,
        customization_strength=2
    )
    
    elapsed = time.time() - start_time
    print(f"Resume customization completed in {elapsed:.2f} seconds")
    print("\nCustomized Resume:")
    print(result)
    
    assert isinstance(result, str)
    assert len(result) > 0
    
    return result

async def main():
    """Run all tests."""
    print("Starting OpenAI Agents Service tests...")
    
    # Test evaluation
    evaluation = await test_evaluate_match()
    
    # Test optimization
    plan = await test_generate_plan(evaluation)
    
    # Test customization
    customized = await test_customize_resume()
    
    print("\nAll tests completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())