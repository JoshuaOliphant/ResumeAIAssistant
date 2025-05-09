"""
Integration tests for the specialized resume section analyzers.

This module tests both individual section analyzers and the synthesis mechanism
for combining their results.
"""
import os
import pytest
import asyncio
from datetime import datetime
from typing import Dict, Any, List

from app.schemas.customize import CustomizationLevel
from app.services.model_selector import ModelProvider
from app.services.section_analyzers.base import SectionType, BaseSectionAnalyzer
from app.services.section_analyzers.skills_analyzer import SkillsQualificationsAnalyzer
from app.services.section_analyzers.experience_analyzer import ExperienceAlignmentAnalyzer
from app.services.section_analyzers.education_analyzer import EducationCertificationAnalyzer
from app.services.section_analyzers.achievement_analyzer import AchievementQuantificationAnalyzer
from app.services.section_analyzers.language_tone_optimizer import LanguageToneOptimizer
from app.services.section_analyzers.synthesis import ResumeAnalysisSynthesizer
from app.schemas.section_analyzers import (
    SkillsAnalysisResult,
    ExperienceAnalysisResult,
    EducationAnalysisResult,
    AchievementAnalysisResult,
    LanguageToneAnalysisResult,
    CombinedAnalysisResult
)
from app.services.section_analysis_service import SectionAnalysisService
from app.db.session import get_db

# Test resume and job description samples
SAMPLE_RESUME = """
# John Smith
Software Engineer | john.smith@example.com | (555) 123-4567 | LinkedIn: johnsmith

## Summary
Experienced software engineer with 5+ years of experience developing web applications and backend services.
Proficient in Python, JavaScript, and cloud technologies. Strong problem-solving skills and focus on
writing clean, maintainable code.

## Skills
- Programming Languages: Python, JavaScript, TypeScript, HTML, CSS
- Frameworks & Libraries: Django, Flask, React, Express
- Cloud & DevOps: AWS (S3, EC2, Lambda), Docker, Kubernetes
- Databases: PostgreSQL, MongoDB, Redis
- Tools: Git, GitHub, JIRA, CI/CD pipelines
- Soft Skills: Communication, teamwork, problem-solving

## Experience
### Senior Software Engineer
XYZ Tech | Jan 2020 - Present
- Led development of a microservices-based backend system that improved API response times by 40%
- Designed and implemented a centralized authentication service for multiple applications
- Mentored junior developers and conducted code reviews to maintain high quality standards
- Optimized database queries resulting in 30% reduction in processing time
- Collaborated with product teams to refine requirements and deliver features on schedule

### Software Engineer
ABC Solutions | Mar 2017 - Dec 2019
- Developed RESTful APIs using Django and Flask for internal and external applications
- Created front-end interfaces using React that improved user engagement by 25%
- Implemented automated testing that increased code coverage from 60% to 90%
- Participated in agile development processes, contributing to sprint planning and retrospectives

## Education
### Bachelor of Science in Computer Science
University of Technology | 2013 - 2017
- GPA: 3.8/4.0
- Relevant coursework: Data Structures, Algorithms, Web Development, Database Systems

## Projects
### Personal Portfolio Website
- Designed and developed a responsive portfolio website using React and Node.js
- Implemented CI/CD pipeline using GitHub Actions

### Task Management Application
- Built a full-stack task management application with Django and React
- Integrated with third-party APIs for calendar synchronization
"""

SAMPLE_JOB_DESCRIPTION = """
# Senior Software Engineer

## About Us
We are a fast-growing tech company building innovative solutions for enterprise clients. Our team is passionate about creating high-quality software that solves real-world problems.

## Job Description
We are looking for a Senior Software Engineer to join our backend development team. The ideal candidate will have strong experience with web application development and cloud technologies.

## Responsibilities
- Design and implement scalable, high-performance backend services
- Work with microservices architecture and containerized applications
- Collaborate with front-end developers, product managers, and other stakeholders
- Participate in code reviews and mentor junior team members
- Contribute to technical architecture decisions
- Implement best practices for testing, security, and performance
- Troubleshoot and resolve complex technical issues

## Requirements
- Bachelor's degree in Computer Science or related field
- 4+ years of experience in software development
- Strong proficiency in Python and JavaScript
- Experience with web frameworks like Django, Flask, or Express
- Knowledge of cloud services (AWS, GCP, or Azure)
- Experience with containerization technologies (Docker, Kubernetes)
- Familiarity with Git and CI/CD pipelines
- Excellent problem-solving and communication skills
- Experience with RESTful API design and implementation
- Understanding of database design and optimization

## Preferred Qualifications
- Experience with React or Angular
- Knowledge of TypeScript
- Experience with message brokers (RabbitMQ, Kafka)
- Understanding of infrastructure as code (Terraform, CloudFormation)
- Contributions to open-source projects
- Master's degree in Computer Science or related field

## Benefits
- Competitive salary and equity
- Health, dental, and vision insurance
- Flexible work arrangements
- Professional development opportunities
- Modern equipment and tools
"""


@pytest.fixture
def db():
    """Get database session for tests."""
    return next(get_db())


@pytest.mark.asyncio
async def test_skills_analyzer():
    """Test the skills and qualifications analyzer."""
    # Create the analyzer
    analyzer = SkillsQualificationsAnalyzer(
        customization_level=CustomizationLevel.BALANCED
    )
    
    # Run the analysis
    result = await analyzer.analyze(
        resume_content=SAMPLE_RESUME,
        job_description=SAMPLE_JOB_DESCRIPTION
    )
    
    # Verify the result structure
    assert isinstance(result, SkillsAnalysisResult)
    assert result.section_type == SectionType.SKILLS
    assert isinstance(result.score, int)
    assert 0 <= result.score <= 100
    assert len(result.job_required_skills) > 0
    assert len(result.matching_skills) > 0
    
    # Log some key metrics for manual review
    print(f"Skills analyzer score: {result.score}")
    print(f"Job required skills: {', '.join(result.job_required_skills[:5])}...")
    print(f"Matching skills count: {len(result.matching_skills)}")
    print(f"Missing skills count: {len(result.missing_skills)}")
    print(f"Recommendations count: {len(result.recommendations)}")


@pytest.mark.asyncio
async def test_synthesizer():
    """Test the resume analysis synthesizer."""
    # Create the synthesizer
    synthesizer = ResumeAnalysisSynthesizer(
        customization_level=CustomizationLevel.BALANCED,
        # Only enable skills and experience analyzers for faster testing
        enabled_analyzers=[SectionType.SKILLS, SectionType.EXPERIENCE]
    )
    
    # Run the analysis
    result = await synthesizer.analyze_resume(
        resume_content=SAMPLE_RESUME,
        job_description=SAMPLE_JOB_DESCRIPTION
    )
    
    # Verify the result structure
    assert isinstance(result, CombinedAnalysisResult)
    assert isinstance(result.overall_score, int)
    assert 0 <= result.overall_score <= 100
    assert result.skills_analysis is not None
    assert result.experience_analysis is not None
    assert len(result.integrated_recommendations) > 0
    
    # Log some key metrics for manual review
    print(f"Overall score: {result.overall_score}")
    print(f"Skills score: {result.skills_analysis.score}")
    print(f"Experience score: {result.experience_analysis.score}")
    print(f"Integrated recommendations count: {len(result.integrated_recommendations)}")
    
    # Convert to customization plan
    plan = await synthesizer.convert_to_customization_plan(
        combined_result=result,
        resume_content=SAMPLE_RESUME,
        job_description=SAMPLE_JOB_DESCRIPTION
    )
    
    # Verify the plan structure
    assert plan.summary is not None
    assert len(plan.summary) > 0
    assert len(plan.recommendations) > 0


@pytest.mark.asyncio
async def test_section_analysis_service(db):
    """Test the section analysis service."""
    # Create the service
    service = SectionAnalysisService(db)
    
    # Build a test request with direct content instead of IDs
    # to avoid database dependencies for testing
    # This requires a slight modification to the service's methods
    from app.schemas.customize import CustomizationPlanRequest
    from unittest.mock import patch
    
    # Mock the _get_resume_and_job method to return our test content
    # instead of querying the database
    with patch.object(
        service, 
        '_get_resume_and_job', 
        return_value=(SAMPLE_RESUME, SAMPLE_JOB_DESCRIPTION)
    ):
        # Create a test request
        request = CustomizationPlanRequest(
            resume_id="test-resume-id",
            job_description_id="test-job-id",
            customization_strength=CustomizationLevel.BALANCED
        )
        
        # Generate the customization plan
        plan = await service.generate_customization_plan(request)
        
        # Verify the plan structure
        assert plan.summary is not None
        assert len(plan.summary) > 0
        assert len(plan.recommendations) > 0
        
        # Log some key metrics for manual review
        print(f"Customization plan summary: {plan.summary}")
        print(f"Recommendations count: {len(plan.recommendations)}")
        print(f"Keywords to add count: {len(plan.keywords_to_add)}")
        if len(plan.recommendations) > 0:
            print(f"First recommendation: {plan.recommendations[0].what}")


# Only run this test if explicitly requested as it's slow and uses multiple models
@pytest.mark.skip(reason="Long-running test that uses all analyzers")
@pytest.mark.asyncio
async def test_all_analyzers():
    """Test all section analyzers individually."""
    analyzers = [
        (SectionType.SKILLS, SkillsQualificationsAnalyzer(customization_level=CustomizationLevel.BALANCED)),
        (SectionType.EXPERIENCE, ExperienceAlignmentAnalyzer(customization_level=CustomizationLevel.BALANCED)),
        (SectionType.EDUCATION, EducationCertificationAnalyzer(customization_level=CustomizationLevel.BALANCED)),
        (SectionType.ACHIEVEMENTS, AchievementQuantificationAnalyzer(customization_level=CustomizationLevel.BALANCED)),
        (SectionType.ALL, LanguageToneOptimizer(customization_level=CustomizationLevel.BALANCED))
    ]
    
    for section_type, analyzer in analyzers:
        print(f"\nTesting {section_type.value} analyzer...")
        result = await analyzer.analyze(
            resume_content=SAMPLE_RESUME,
            job_description=SAMPLE_JOB_DESCRIPTION
        )
        
        # Log results
        print(f"Score: {result.score}")
        print(f"Recommendations count: {len(result.recommendations)}")
        print(f"Issues count: {len(result.issues)}")
        print(f"First recommendation: {result.recommendations[0].what if result.recommendations else 'N/A'}")
        
        # Verify the result structure
        assert isinstance(result.score, int)
        assert 0 <= result.score <= 100
        assert result.section_type == section_type