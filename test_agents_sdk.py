"""
Test script for the OpenAI Agents SDK.
Simple test to verify the SDK works correctly.
"""
import os
import asyncio
from pprint import pprint

# Import from Agents SDK and OpenAI
from openai import OpenAI
from agents import Agent, Runner, OpenAIChatCompletionsModel, set_default_openai_client

# Check if API key is set
if not os.environ.get("OPENAI_API_KEY"):
    print("Error: OPENAI_API_KEY environment variable not set")
    print("Please set it before running this script")
    exit(1)

# Create OpenAI client and set it as default
openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
set_default_openai_client(openai_client)

# Define a simple agent
evaluator_agent = Agent(
    name="ResumeEvaluator",
    instructions="""
    You are an expert resume evaluator that analyzes how well a resume matches a job description.
    Provide a detailed evaluation with a match score from 0-100.
    """,
    model=OpenAIChatCompletionsModel(openai_client=openai_client, model="gpt-4o-2024-05-13")
)

def main():
    """Run a simple test of the Agents SDK."""
    print("Testing OpenAI Agents SDK...")
    
    # Sample data
    resume = """
    # John Smith
    Software Engineer
    
    ## Experience
    - Senior Developer at Tech Co (2020-Present)
    - Developer at Software Inc (2018-2020)
    
    ## Skills
    Python, JavaScript, React, Node.js
    """
    
    job_description = """
    # Senior Frontend Developer
    
    We're looking for a developer with 5+ years experience in:
    - React
    - TypeScript
    - CSS/SCSS
    """
    
    # We'll use Runner.run as a class method
    
    # Run the agent
    message = f"""
    Please evaluate this resume:
    
    {resume}
    
    Against this job description:
    
    {job_description}
    """
    
    # Use the synchronous run method instead of async
    result = Runner.run_sync(
        starting_agent=evaluator_agent,
        input=message
    )
    
    # Print the result
    print("\nAgent Response:")
    print(result.output)

if __name__ == "__main__":
    main()