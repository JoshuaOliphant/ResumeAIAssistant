"""
Integration tests for PydanticAI implementations.

NOTE: These tests are now skipped as PydanticAI functionality has been 
replaced by Claude Code. These are kept for reference only.
"""
import os
import sys
import pytest
import asyncio
from pydantic import BaseModel

# Add the parent directory to the path so we can import the app
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.schemas.customize import CustomizationLevel

# PydanticAI service has been removed
# Keeping function signatures for reference but all tests will be skipped


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
    pytest.skip("PydanticAI functionality has been replaced by Claude Code")
    return None


@pytest.mark.asyncio
async def test_optimization_plan(evaluation=None):
    """Test the optimization plan generation with PydanticAI"""
    pytest.skip("PydanticAI functionality has been replaced by Claude Code")
    return None


@pytest.mark.asyncio
async def test_cover_letter_generation():
    """Test the cover letter generation functionality with PydanticAI"""
    pytest.skip("PydanticAI functionality has been replaced by Claude Code")
    return None


@pytest.mark.asyncio
async def test_model_configuration():
    """Test the model configuration and agent creation with task-specific settings"""
    pytest.skip("PydanticAI functionality has been replaced by Claude Code")
    return None


if __name__ == "__main__":
    # All tests are skipped since PydanticAI has been replaced
    print("PydanticAI tests are skipped - functionality has been replaced by Claude Code")