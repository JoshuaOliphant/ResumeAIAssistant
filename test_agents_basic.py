"""
Test script for the OpenAI Agents SDK, following the quickstart guide exactly.
Simple test to verify the SDK works correctly.
"""
import asyncio
import os
from agents import Agent, Runner

# Check if API key is set
if not os.environ.get("OPENAI_API_KEY"):
    print("Error: OPENAI_API_KEY environment variable not set")
    print("Please set it before running this script")
    exit(1)

# Create a simple agent
resume_evaluator = Agent(
    name="Resume Evaluator",
    instructions="""
    You are an expert resume evaluator. Given a resume and job description, analyze how well they match.
    Provide a score from 0-100 and explain strengths and areas for improvement.
    """
)

# Sample data
SAMPLE_RESUME = """
# John Smith
Software Engineer

## Experience
- Senior Developer at Tech Co (2020-Present)
- Developer at Software Inc (2018-2020)

## Skills
Python, JavaScript, React, Node.js
"""

SAMPLE_JOB_DESCRIPTION = """
# Senior Frontend Developer

We're looking for a developer with 5+ years experience in:
- React
- TypeScript
- CSS/SCSS
"""

async def main():
    """Run a simple test of the Agents SDK."""
    print("Testing OpenAI Agents SDK...")
    
    # Create the user prompt
    prompt = f"""
    Please evaluate how well this resume matches the job description.
    
    Resume:
    {SAMPLE_RESUME}
    
    Job Description:
    {SAMPLE_JOB_DESCRIPTION}
    
    Provide a match score from 0-100 and explain why.
    """
    
    # Run the agent
    result = await Runner.run(resume_evaluator, prompt)
    
    # Print the result
    print("\nAgent Response:")
    print(result.final_output)

if __name__ == "__main__":
    asyncio.run(main())