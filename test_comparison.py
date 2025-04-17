"""
Comparison test script for Claude service vs OpenAI Agents service.
Run this script to compare the two implementations side by side.

Usage: python test_comparison.py
"""
import asyncio
import os
import time
from pprint import pprint
import json

import logfire
from app.services.claude_service import evaluate_resume_job_match as claude_evaluate
from app.services.claude_service import generate_optimization_plan as claude_optimize
from app.services.claude_service import customize_resume as claude_customize

from app.services.openai_agents_service import evaluate_resume_job_match as openai_evaluate
from app.services.openai_agents_service import generate_optimization_plan as openai_optimize
from app.services.openai_agents_service import customize_resume as openai_customize

from app.schemas.customize import CustomizationLevel

# Configure logging
logfire.configure(service_name="resume-ai-assistant-comparison", console={"verbose": True})

# Sample data for comparison
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

async def run_comparison():
    """Run a comparison of Claude service vs OpenAI Agents service."""
    print("Starting comparison between Claude and OpenAI Agents implementations...")
    
    with open("comparison_results.json", "w") as f:
        results = {"claude": {}, "openai": {}, "timings": {}}
        
        # Test 1: Evaluate resume match with job description
        print("\n=== TEST 1: Comparing resume evaluation ===\n")
        
        # Claude implementation
        print("Running Claude evaluation...")
        claude_start = time.time()
        claude_eval = await claude_evaluate(
            resume_content=SAMPLE_RESUME,
            job_description=SAMPLE_JOB_DESCRIPTION,
            customization_level=CustomizationLevel.BALANCED
        )
        claude_eval_time = time.time() - claude_start
        results["claude"]["evaluation"] = claude_eval
        results["timings"]["claude_evaluation"] = claude_eval_time
        print(f"Claude evaluation completed in {claude_eval_time:.2f} seconds")
        
        # OpenAI implementation
        print("Running OpenAI evaluation...")
        openai_start = time.time()
        openai_eval = await openai_evaluate(
            resume_content=SAMPLE_RESUME,
            job_description=SAMPLE_JOB_DESCRIPTION,
            customization_level=CustomizationLevel.BALANCED
        )
        openai_eval_time = time.time() - openai_start
        results["openai"]["evaluation"] = openai_eval
        results["timings"]["openai_evaluation"] = openai_eval_time
        print(f"OpenAI evaluation completed in {openai_eval_time:.2f} seconds")
        
        # Test 2: Generate optimization plan
        print("\n=== TEST 2: Comparing optimization plan generation ===\n")
        
        # Claude implementation
        print("Running Claude optimization plan generation...")
        claude_start = time.time()
        claude_plan = await claude_optimize(
            resume_content=SAMPLE_RESUME,
            job_description=SAMPLE_JOB_DESCRIPTION,
            evaluation=claude_eval,
            customization_level=CustomizationLevel.BALANCED
        )
        claude_plan_time = time.time() - claude_start
        results["claude"]["optimization_plan"] = claude_plan.model_dump()
        results["timings"]["claude_optimization"] = claude_plan_time
        print(f"Claude optimization plan completed in {claude_plan_time:.2f} seconds")
        
        # OpenAI implementation
        print("Running OpenAI optimization plan generation...")
        openai_start = time.time()
        openai_plan = await openai_optimize(
            resume_content=SAMPLE_RESUME,
            job_description=SAMPLE_JOB_DESCRIPTION,
            evaluation=openai_eval,
            customization_level=CustomizationLevel.BALANCED
        )
        openai_plan_time = time.time() - openai_start
        results["openai"]["optimization_plan"] = openai_plan.model_dump()
        results["timings"]["openai_optimization"] = openai_plan_time
        print(f"OpenAI optimization plan completed in {openai_plan_time:.2f} seconds")
        
        # Test 3: Customize resume
        print("\n=== TEST 3: Comparing resume customization ===\n")
        
        # Claude implementation
        print("Running Claude resume customization...")
        claude_start = time.time()
        claude_custom = await claude_customize(
            resume_content=SAMPLE_RESUME,
            job_description=SAMPLE_JOB_DESCRIPTION,
            customization_strength=2
        )
        claude_custom_time = time.time() - claude_start
        results["claude"]["customized_resume"] = claude_custom
        results["timings"]["claude_customization"] = claude_custom_time
        print(f"Claude resume customization completed in {claude_custom_time:.2f} seconds")
        
        # OpenAI implementation
        print("Running OpenAI resume customization...")
        openai_start = time.time()
        openai_custom = await openai_customize(
            resume_content=SAMPLE_RESUME,
            job_description=SAMPLE_JOB_DESCRIPTION,
            customization_strength=2
        )
        openai_custom_time = time.time() - openai_start
        results["openai"]["customized_resume"] = openai_custom
        results["timings"]["openai_customization"] = openai_custom_time
        print(f"OpenAI resume customization completed in {openai_custom_time:.2f} seconds")
        
        # Calculate overall time differences
        results["timings"]["total_claude_time"] = claude_eval_time + claude_plan_time + claude_custom_time
        results["timings"]["total_openai_time"] = openai_eval_time + openai_plan_time + openai_custom_time
        results["timings"]["time_difference_percentage"] = (
            (results["timings"]["total_claude_time"] - results["timings"]["total_openai_time"]) 
            / results["timings"]["total_claude_time"] * 100
        )
        
        # Write results to file
        json.dump(results, f, indent=2)
    
    print("\n=== COMPARISON SUMMARY ===\n")
    print(f"Total Claude time: {results['timings']['total_claude_time']:.2f} seconds")
    print(f"Total OpenAI time: {results['timings']['total_openai_time']:.2f} seconds")
    print(f"Difference: {abs(results['timings']['time_difference_percentage']):.2f}% {'faster' if results['timings']['time_difference_percentage'] > 0 else 'slower'} with OpenAI")
    print("\nDetailed results saved to comparison_results.json")
    print("\nComparison completed!")

if __name__ == "__main__":
    asyncio.run(run_comparison())