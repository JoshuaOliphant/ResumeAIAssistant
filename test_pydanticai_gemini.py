"""
Test script for PydanticAI with Google Gemini models.
This script validates the Gemini integration with PydanticAI.
"""
import asyncio
import os
import json
from pprint import pprint
import logfire

# Import from PydanticAI
try:
    from pydanticai import Agent, tool
    PYDANTICAI_AVAILABLE = True
except ImportError:
    print("PydanticAI not installed. Please install with 'uv add pydanticai'")
    PYDANTICAI_AVAILABLE = False

# Import from app
from app.core.config import settings, get_pydanticai_model_config
from pydantic import BaseModel, Field

# Simple test models
class SimpleResponse(BaseModel):
    """A simple response model."""
    message: str = Field(..., description="A short message")
    count: int = Field(..., description="A number between 1 and 10")

class JobClassification(BaseModel):
    """Job classification model."""
    role: str = Field(..., description="The specific job role")
    industry: str = Field(..., description="The industry sector")
    skills: list[str] = Field(..., description="Array of key required skills")
    level: str = Field(..., description="Experience level required")

async def test_gemini_basic():
    """Test basic PydanticAI with Gemini model."""
    print("\n=== Testing Gemini with PydanticAI - Basic ===")
    
    if not PYDANTICAI_AVAILABLE:
        print("Skipping test: PydanticAI not installed")
        return
    
    if not settings.GEMINI_API_KEY:
        print("Skipping test: No Gemini API key configured")
        return
    
    try:
        # Set config
        config = get_pydanticai_model_config()
        print(f"Available providers: {list(config.keys())}")
        
        # Create a Gemini agent with PydanticAI
        agent = Agent(
            "google:gemini-2.5-flash-preview-04-17",  # Use Flash for faster response
            output_type=SimpleResponse,
            system_prompt="You are a helpful assistant that generates simple responses.",
            thinking_config={"thinkingBudget": 0}  # No thinking needed for this test
        )
        
        # Run the agent
        result = await agent.run("Generate a simple response with a message and count.")
        
        print("\nResponse from Gemini via PydanticAI:")
        print(f"Message: {result.message}")
        print(f"Count: {result.count}")
        print("\nBasic test completed successfully.")
        
    except Exception as e:
        print(f"Error testing Gemini with PydanticAI: {str(e)}")
        raise e

async def test_gemini_thinking():
    """Test PydanticAI with Gemini model using thinking budget."""
    print("\n=== Testing Gemini Thinking with PydanticAI ===")
    
    if not PYDANTICAI_AVAILABLE:
        print("Skipping test: PydanticAI not installed")
        return
    
    if not settings.GEMINI_API_KEY:
        print("Skipping test: No Gemini API key configured")
        return
    
    try:
        # Create agents with different thinking budgets
        agent_no_thinking = Agent(
            "google:gemini-2.5-flash-preview-04-17",
            output_type=SimpleResponse,
            system_prompt="You are a helpful assistant that generates numbered facts.",
            thinking_config={"thinkingBudget": 0}  # No thinking
        )
        
        agent_with_thinking = Agent(
            "google:gemini-2.5-flash-preview-04-17",
            output_type=SimpleResponse,
            system_prompt="You are a helpful assistant that generates numbered facts.",
            thinking_config={"thinkingBudget": 5000}  # 5K tokens for thinking
        )
        
        # Complex prompt that benefits from thinking
        prompt = """
        Consider the following complex problem: 
        
        A train travels at 60 mph from City A to City B, which are 180 miles apart.
        Another train travels at 90 mph from City B to City A.
        If both trains start at the same time, how far from City A will they meet?
        
        Solve this step by step and provide a message summarizing the answer.
        For the count field, return the answer rounded to the nearest whole number.
        """
        
        # Run both agents
        print("Running with no thinking budget...")
        result_no_thinking = await agent_no_thinking.run(prompt)
        
        print("Running with thinking budget...")
        result_with_thinking = await agent_with_thinking.run(prompt)
        
        # Compare results
        print("\nResults Comparison:")
        print(f"Without thinking: {result_no_thinking.message} (Count: {result_no_thinking.count})")
        print(f"With thinking: {result_with_thinking.message} (Count: {result_with_thinking.count})")
        
        print("\nThinking test completed successfully.")
        
    except Exception as e:
        print(f"Error testing Gemini thinking: {str(e)}")
        raise e

async def test_job_classifier():
    """Test job classification using PydanticAI with Gemini."""
    print("\n=== Testing Job Classification with PydanticAI and Gemini ===")
    
    if not PYDANTICAI_AVAILABLE:
        print("Skipping test: PydanticAI not installed")
        return
    
    if not settings.GEMINI_API_KEY:
        print("Skipping test: No Gemini API key configured")
        return
    
    try:
        # Create an agent using Google Gemini Flash
        agent = Agent(
            "google:gemini-2.5-flash-preview-04-17",
            output_type=JobClassification,
            system_prompt="""
            You are a job classification expert. 
            Analyze resumes and job descriptions to identify the job role, industry, key skills, and experience level.
            """,
            thinking_config={"thinkingBudget": 1000},  # Some thinking can help with classification
            temperature=0.2  # Lower temperature for more consistent results
        )
        
        # Sample resume and job description
        resume = """
        # John Doe

        Full-stack developer with 5 years of experience in Python, JavaScript, and cloud services.

        ## Experience
        ### Senior Developer, XYZ Company
        - Developed RESTful APIs using FastAPI
        - Implemented CI/CD pipelines with GitHub Actions
        - Managed AWS infrastructure using Terraform

        ## Skills
        - Python, FastAPI, Django
        - JavaScript, React, Node.js
        - AWS, Docker, Kubernetes
        """
        
        job_description = """
        # Backend Software Engineer

        We're looking for an experienced backend engineer to join our cloud team.

        ## Requirements
        - Strong experience with Python web frameworks (Django, Flask, FastAPI)
        - Experience with containerization and orchestration (Docker, Kubernetes)
        - Knowledge of cloud services (AWS, GCP, or Azure)
        - Understanding of CI/CD practices
        """
        
        # Run the agent
        user_message = f"""
        Please classify this job role based on the following resume and job description:
        
        RESUME:
        {resume}
        
        JOB DESCRIPTION:
        {job_description}
        """
        
        result = await agent.run(user_message)
        
        # Print results
        print("\nJob Classification Results:")
        print(f"Role: {result.role}")
        print(f"Industry: {result.industry}")
        print(f"Skills: {', '.join(result.skills)}")
        print(f"Experience Level: {result.level}")
        
        print("\nJob classification test completed successfully.")
        
    except Exception as e:
        print(f"Error testing job classification: {str(e)}")
        raise e

async def main():
    """Run all tests."""
    print("Starting PydanticAI with Gemini tests...")
    
    if not PYDANTICAI_AVAILABLE:
        print("PydanticAI not installed. Please install with 'uv add pydanticai'")
        return
    
    if not settings.GEMINI_API_KEY:
        print("No Gemini API key found. Please set GEMINI_API_KEY environment variable.")
        return
    
    # Ensure environment variable is set
    os.environ["GOOGLE_API_KEY"] = settings.GEMINI_API_KEY
    
    # Run tests
    await test_gemini_basic()
    await test_gemini_thinking()
    await test_job_classifier()
    
    print("\nAll PydanticAI with Gemini tests completed!")

if __name__ == "__main__":
    asyncio.run(main())