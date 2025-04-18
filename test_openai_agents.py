"""
Test script for the OpenAI Agents service.
Run this script to test the OpenAI Agents SDK implementation.

Usage: python test_openai_agents.py
"""
import asyncio
import os
from pprint import pprint

import logfire
from app.services.openai_agents_service import evaluate_resume_job_match, generate_optimization_plan, customize_resume
from app.schemas.customize import CustomizationLevel

# Configure logging
logfire.configure(service_name="resume-ai-assistant-demo", console={"verbose": True})

# Sample data for demo
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

async def main():
    """Run a demo of the OpenAI agents service."""
    print("Starting OpenAI Agents demo...")
    
    # Step 1: Evaluate the resume
    print("\n=== STEP 1: Evaluating resume match with job description ===\n")
    evaluation = await evaluate_resume_job_match(
        resume_content=SAMPLE_RESUME,
        job_description=SAMPLE_JOB_DESCRIPTION,
        customization_level=CustomizationLevel.BALANCED
    )
    
    print("\nEvaluation Result:")
    pprint(evaluation)
    
    # Step 2: Generate optimization plan
    print("\n=== STEP 2: Generating optimization plan ===\n")
    plan = await generate_optimization_plan(
        resume_content=SAMPLE_RESUME,
        job_description=SAMPLE_JOB_DESCRIPTION,
        evaluation=evaluation,
        customization_level=CustomizationLevel.BALANCED
    )
    
    print("\nOptimization Plan:")
    pprint(plan.model_dump())
    
    # Step 3: Customize resume
    print("\n=== STEP 3: Customizing resume ===\n")
    customized_resume = await customize_resume(
        resume_content=SAMPLE_RESUME,
        job_description=SAMPLE_JOB_DESCRIPTION,
        customization_strength=2
    )
    
    print("\nCustomized Resume:")
    print(customized_resume)
    
    print("\nDemo completed!")

if __name__ == "__main__":
    asyncio.run(main())