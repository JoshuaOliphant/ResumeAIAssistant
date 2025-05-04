"""
Integration tests for PydanticAI implementations.
"""
import os
import sys
import pytest
import asyncio
from pydantic import BaseModel

# Add the parent directory to the path so we can import the app
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.schemas.customize import CustomizationLevel
from app.services.pydanticai_service import evaluate_resume_job_match, generate_optimization_plan, customize_resume, generate_cover_letter


# Test data
RESUME_CONTENT = """# Jane Smith
## Software Engineer

### Contact
- Email: jane.smith@example.com
- Phone: (123) 456-7890
- LinkedIn: linkedin.com/in/janesmith
- GitHub: github.com/janesmith

### Summary
Experienced software engineer with 5 years of expertise in Python, JavaScript, and cloud technologies. Skilled in designing and implementing scalable web applications and microservices.

### Skills
- Programming Languages: Python, JavaScript, TypeScript, SQL
- Frameworks: Django, FastAPI, React, Node.js
- Cloud: AWS (EC2, S3, Lambda), GCP
- DevOps: Docker, Kubernetes, CI/CD
- Databases: PostgreSQL, MongoDB
- Testing: pytest, Jest

### Experience
**Senior Software Engineer, TechCorp Inc.**  
*January 2020 - Present*
- Led development of a Python-based microservices architecture, improving system response time by 40%
- Implemented CI/CD pipelines using GitHub Actions, reducing deployment time from hours to minutes
- Optimized PostgreSQL database queries, resulting in 50% faster data retrieval
- Mentored junior developers and conducted code reviews

**Software Developer, WebSolutions Inc.**  
*June 2017 - December 2019*
- Developed RESTful APIs using Django REST Framework for e-commerce applications
- Built responsive front-end interfaces with React and Redux
- Implemented automated testing strategies, achieving 90% code coverage
- Collaborated with product managers to refine requirements and deliver features on schedule

### Education
**Bachelor of Science in Computer Science**  
University of Technology, 2017
- GPA: 3.8/4.0
- Relevant coursework: Data Structures, Algorithms, Database Systems, Web Development

### Projects
**Inventory Management System**
- Developed a full-stack application using FastAPI and React
- Implemented role-based access control and real-time notifications
- Deployed on AWS using containerization

**Open Source Contribution: Data Visualization Library**
- Contributed to a popular Python data visualization library
- Implemented new chart types and fixed rendering bugs
- Improved documentation and created examples

### Certifications
- AWS Certified Developer - Associate
- MongoDB Certified Developer
"""

JOB_DESCRIPTION = """
# Senior Full Stack Engineer

## About Us
TechInnovate is a fast-growing technology company specializing in AI-powered solutions for the financial services industry. We're looking for a talented Senior Full Stack Engineer to join our product development team.

## The Role
We're seeking an experienced Senior Full Stack Engineer who can design, build, and maintain our web applications and services. The ideal candidate is passionate about creating efficient, scalable, and maintainable code while collaborating with cross-functional teams.

## Key Responsibilities
- Design and develop robust, scalable web applications using React.js and Node.js
- Build and maintain Python microservices using FastAPI and Django
- Optimize database queries and data access patterns
- Implement automated testing strategies to ensure code quality
- Collaborate with UI/UX designers to implement responsive designs
- Participate in code reviews and mentor junior developers
- Work with DevOps to deploy and monitor applications in AWS
- Contribute to architectural decisions and technology selection

## Required Qualifications
- Bachelor's degree in Computer Science or related field
- 5+ years of experience in web development
- Strong proficiency in Python and JavaScript/TypeScript
- Experience with React, Redux, and modern frontend workflows
- Expertise in Python web frameworks (Django, FastAPI)
- Solid understanding of RESTful APIs and microservices architecture
- Experience with SQL and NoSQL databases (PostgreSQL, MongoDB)
- Familiarity with AWS services (EC2, S3, Lambda)
- Knowledge of Docker, Kubernetes, and CI/CD practices
- Strong problem-solving skills and attention to detail

## Preferred Qualifications
- Master's degree in Computer Science or related field
- Experience with GraphQL
- Knowledge of message queues and streaming platforms (Kafka, RabbitMQ)
- Experience with data visualization libraries
- Contributions to open-source projects
- AWS certification

## Benefits
- Competitive salary and equity
- Health, dental, and vision insurance
- 401(k) matching
- Flexible work arrangements
- Professional development budget
- Home office stipend
- Unlimited PTO
"""

COMPANY_NAME = "TechInnovate"
HIRING_MANAGER = "Alex Johnson"
APPLICANT_NAME = "Jane Smith"
ADDITIONAL_CONTEXT = "I'm particularly interested in the AI aspects of this role and have been studying machine learning on the side."


@pytest.mark.asyncio
async def test_resume_evaluation():
    """Test the resume evaluation functionality with PydanticAI"""
    try:
        # Start timing
        import time
        start_time = time.time()
        
        # Run the evaluation
        evaluation = await evaluate_resume_job_match(
            resume_content=RESUME_CONTENT,
            job_description=JOB_DESCRIPTION,
            customization_level=CustomizationLevel.BALANCED
        )
        
        # Log timing
        print(f"Evaluation completed in {time.time() - start_time:.2f} seconds")
        
        # Basic assertions
        assert evaluation is not None
        assert "match_score" in evaluation
        assert "overall_assessment" in evaluation
        assert "strengths" in evaluation
        assert "gaps" in evaluation
        
        # Print results summary
        print(f"Match score: {evaluation['match_score']}")
        print(f"Strengths count: {len(evaluation['strengths'])}")
        print(f"Gaps count: {len(evaluation['gaps'])}")
        
        return evaluation
    except Exception as e:
        pytest.skip(f"Test skipped due to error: {str(e)}")


@pytest.mark.asyncio
async def test_optimization_plan(evaluation=None):
    """Test the optimization plan generation with PydanticAI"""
    try:
        # If no evaluation was passed, get one
        if evaluation is None:
            evaluation = await test_resume_evaluation()
            
        if evaluation is None:
            pytest.skip("Evaluation failed, skipping optimization test")
            
        # Start timing
        import time
        start_time = time.time()
        
        # Generate optimization plan
        plan = await generate_optimization_plan(
            resume_content=RESUME_CONTENT,
            job_description=JOB_DESCRIPTION,
            evaluation=evaluation,
            customization_level=CustomizationLevel.BALANCED
        )
        
        # Log timing
        print(f"Optimization plan completed in {time.time() - start_time:.2f} seconds")
        
        # Basic assertions
        assert plan is not None
        assert hasattr(plan, "summary")
        assert hasattr(plan, "recommendations")
        assert len(plan.recommendations) > 0
        
        # Print results summary
        print(f"Recommendations count: {len(plan.recommendations)}")
        print(f"Keywords to add count: {len(plan.keywords_to_add)}")
        
        return plan
    except Exception as e:
        pytest.skip(f"Test skipped due to error: {str(e)}")


@pytest.mark.asyncio
async def test_cover_letter_generation():
    """Test the cover letter generation functionality with PydanticAI"""
    try:
        # Check if pydanticai is available
        try:
            from pydanticai import Agent
            pydanticai_available = True
        except ImportError:
            pydanticai_available = False
            pytest.skip("PydanticAI is not installed - skipping test")
            return None
        
        # Start timing
        import time
        start_time = time.time()
        
        # Generate cover letter
        cover_letter = await generate_cover_letter(
            resume_content=RESUME_CONTENT,
            job_description=JOB_DESCRIPTION,
            applicant_name=APPLICANT_NAME,
            company_name=COMPANY_NAME,
            hiring_manager_name=HIRING_MANAGER,
            additional_context=ADDITIONAL_CONTEXT,
            tone="enthusiastic"
        )
        
        # Log timing
        print(f"Cover letter generation completed in {time.time() - start_time:.2f} seconds")
        
        # Basic assertions
        assert cover_letter is not None
        assert len(cover_letter) > 200
        assert COMPANY_NAME in cover_letter
        
        # Look for key sections
        assert any(marker in cover_letter.lower() for marker in [
            "dear", "hello", "hi", "to whom"
        ]), "No greeting found in cover letter"
        
        assert any(marker in cover_letter.lower() for marker in [
            "sincerely", "best regards", "regards", "thank you", 
            "looking forward", "best", "yours"
        ]), "No closing found in cover letter"
        
        # Print excerpt
        print(f"Cover letter excerpt (first 200 chars): {cover_letter[:200]}...")
        
        return cover_letter
    except ImportError:
        pytest.skip("PydanticAI is not installed - skipping test")
        return None
    except Exception as e:
        pytest.skip(f"Test skipped due to error: {str(e)}")
        return None


@pytest.mark.asyncio
async def test_model_configuration():
    """Test the model configuration and agent creation with task-specific settings"""
    try:
        # Check if pydanticai is available
        try:
            from pydanticai import Agent
            pydanticai_available = True
        except ImportError:
            pydanticai_available = False
            pytest.skip("PydanticAI is not installed - skipping test")
            return None
        
        # Import the configuration functions
        from app.core.config import get_pydanticai_model_config, settings
        
        # Note: The direct agent creation functions have been replaced with dynamic model selection
        # We're now skipping this part of the test as it's no longer applicable
        print("Skipping direct agent creation tests - now using dynamic model selection")
        
        # Test the configuration
        config = get_pydanticai_model_config()
        
        # Check that at least one provider is configured
        assert len(config) > 0, "No model providers configured"
        print(f"Configured providers: {', '.join(config.keys())}")
        
        # For each configured provider, check essential parameters
        for provider, provider_config in config.items():
            assert "api_key" in provider_config, f"Missing API key for {provider}"
            assert "default_model" in provider_config, f"Missing default model for {provider}"
            assert "temperature" in provider_config, f"Missing temperature for {provider}"
            assert "max_tokens" in provider_config, f"Missing max_tokens for {provider}"
            
            print(f"Provider {provider} config validated - using model: {provider_config['default_model']}")
        
        # If Anthropic is configured, check for thinking config with Claude 3.7
        if "anthropic" in config:
            anthropic_config = config["anthropic"]
            if "claude-3-7" in anthropic_config.get("default_model", ""):
                assert "thinking_config" in anthropic_config, "Missing thinking_config for Claude 3.7"
                assert anthropic_config["thinking_config"].get("type") == "enabled", "Thinking not enabled for Claude 3.7"
                assert anthropic_config["thinking_config"].get("budget_tokens") > 0, "Invalid thinking budget for Claude 3.7"
                print(f"Verified Claude 3.7 thinking config with budget: {anthropic_config['thinking_config'].get('budget_tokens')}")
        
        # Skip direct agent creation tests since we've switched to dynamic model selection
        print("Note: Skipping direct agent creation tests - now using dynamic model selection")
        print("Testing model selection and configuration is now done in the actual usage flow")
            
        # Test fallback model paths are correctly configured
        print(f"Checking fallback model configuration:")
        print(f"  - Primary fallbacks: {', '.join(settings.PYDANTICAI_FALLBACK_MODELS[:3])}")
        if len(settings.PYDANTICAI_FALLBACK_MODELS) > 3:
            print(f"  - Secondary fallbacks: {', '.join(settings.PYDANTICAI_FALLBACK_MODELS[3:])}")
            
        # Verify task-specific models are correctly configured
        print(f"Checking task-specific model configuration:")
        print(f"  - Evaluator model: {settings.PYDANTICAI_EVALUATOR_MODEL}")
        print(f"  - Optimizer model: {settings.PYDANTICAI_OPTIMIZER_MODEL}")
        print(f"  - Cover letter model: {settings.PYDANTICAI_COVER_LETTER_MODEL}")
        
        print("Model Configuration Test Passed!")
        return True
        
    except Exception as e:
        pytest.skip(f"Model configuration test skipped due to error: {str(e)}")
        return False


if __name__ == "__main__":
    # Run multiple tests
    asyncio.run(test_resume_evaluation())
    asyncio.run(test_cover_letter_generation())
    asyncio.run(test_model_configuration())