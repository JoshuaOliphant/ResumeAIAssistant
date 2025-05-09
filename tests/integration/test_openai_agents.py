"""
Integration tests for the OpenAI Agents service.
"""
import asyncio
import os
import unittest
from pprint import pprint

# Set up the environment for testing
os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY", "dummy-key-for-testing")
os.environ["OPENAI_MODEL"] = "o4-mini"  # Use cost-efficient model with reasoning capabilities for testing
os.environ["OPENAI_EVALUATOR_MODEL"] = "o4-mini"  # Use cost-efficient model with reasoning capabilities for testing
os.environ["OPENAI_OPTIMIZER_MODEL"] = "o4-mini"  # Use cost-efficient model with reasoning capabilities for testing

import logfire
from app.services.openai_agents_service import evaluate_resume_job_match, generate_optimization_plan, customize_resume
from app.schemas.customize import CustomizationLevel

# Configure logging for tests
logfire.configure(service_name="resume-ai-assistant-test", console={"verbose": True})

# Sample data for testing
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

class TestOpenAIAgentsService(unittest.TestCase):
    """Test the OpenAI agents service functionality."""
    
    def test_imports(self):
        """Test that imports work correctly."""
        self.assertTrue(callable(evaluate_resume_job_match))
        self.assertTrue(callable(generate_optimization_plan))
        self.assertTrue(callable(customize_resume))
        
    @unittest.skipIf(os.environ.get("OPENAI_API_KEY") == "dummy-key-for-testing", 
                    "Skipping test that requires valid API key")
    def test_evaluation(self):
        """Test the resume evaluation function with OpenAI."""
        async def run_test():
            result = await evaluate_resume_job_match(
                resume_content=SAMPLE_RESUME, 
                job_description=SAMPLE_JOB_DESCRIPTION,
                customization_level=CustomizationLevel.BALANCED
            )
            pprint(result)
            self.assertIsInstance(result, dict)
            self.assertIn("match_score", result)
            self.assertIn("strengths", result)
            self.assertIn("gaps", result)
        
        asyncio.run(run_test())
        
    @unittest.skipIf(os.environ.get("OPENAI_API_KEY") == "dummy-key-for-testing", 
                    "Skipping test that requires valid API key")
    def test_optimization_plan(self):
        """Test the optimization plan generation with OpenAI."""
        async def run_test():
            # First get the evaluation
            evaluation = await evaluate_resume_job_match(
                resume_content=SAMPLE_RESUME, 
                job_description=SAMPLE_JOB_DESCRIPTION,
                customization_level=CustomizationLevel.BALANCED
            )
            
            # Then generate the plan
            plan = await generate_optimization_plan(
                resume_content=SAMPLE_RESUME,
                job_description=SAMPLE_JOB_DESCRIPTION,
                evaluation=evaluation,
                customization_level=CustomizationLevel.BALANCED
            )
            
            pprint(plan.model_dump())
            self.assertIsInstance(plan.summary, str)
            self.assertIsInstance(plan.recommendations, list)
            self.assertGreater(len(plan.recommendations), 0)
        
        asyncio.run(run_test())
        
    @unittest.skipIf(os.environ.get("OPENAI_API_KEY") == "dummy-key-for-testing", 
                    "Skipping test that requires valid API key")
    def test_resume_customization(self):
        """Test the resume customization function with OpenAI."""
        async def run_test():
            result = await customize_resume(
                resume_content=SAMPLE_RESUME, 
                job_description=SAMPLE_JOB_DESCRIPTION,
                customization_strength=2
            )
            
            print("\n--- Customized Resume ---\n")
            print(result)
            self.assertIsInstance(result, str)
            self.assertGreater(len(result), 0)
        
        asyncio.run(run_test())

if __name__ == "__main__":
    unittest.main()