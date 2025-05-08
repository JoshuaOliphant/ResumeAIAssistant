"""
Education and Certification Relevance Analyzer for resume customization.

This module analyzes the education and certification sections of a resume against a job description,
evaluating the relevance of qualifications to the position and providing specific
recommendations for better highlighting relevant credentials.
"""
import json
import time
from typing import Dict, Any, List, Optional
import logfire

from pydantic import BaseModel
from pydantic_ai import Agent

from app.core.config import settings
from app.schemas.customize import CustomizationLevel
from app.services.model_selector import ModelProvider, select_model_for_task
from app.services.section_analyzers.base import BaseSectionAnalyzer, SectionType
from app.schemas.section_analyzers import EducationAnalysisResult, SectionRecommendation, SectionIssue


class EducationCertificationAnalyzer(BaseSectionAnalyzer):
    """
    Specialized analyzer for education and certifications in resumes.
    
    This analyzer evaluates how well the candidate's educational background and certifications
    align with job requirements, identifies gaps and opportunities for better highlighting
    relevant qualifications, and provides specific recommendations for improvement.
    """
    
    def __init__(
        self,
        preferred_model_provider: Optional[ModelProvider] = None,
        customization_level: CustomizationLevel = CustomizationLevel.BALANCED
    ):
        """
        Initialize the education analyzer.
        
        Args:
            preferred_model_provider: Optional preferred AI model provider
            customization_level: Customization level affecting analysis depth
        """
        super().__init__(preferred_model_provider, customization_level)
        self.logger.info("Education analyzer initialized")
    
    @property
    def section_type(self) -> SectionType:
        """Get the section type this analyzer handles."""
        return SectionType.EDUCATION
    
    async def analyze(
        self,
        resume_content: str,
        job_description: str,
        section_content: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> EducationAnalysisResult:
        """
        Analyze the education and certification sections of a resume.
        
        Args:
            resume_content: Full resume content
            job_description: Full job description
            section_content: Optional pre-extracted education section
            context: Optional additional context for analysis
            
        Returns:
            EducationAnalysisResult with detailed analysis
        """
        start_time = time.time()
        self.logger.info(
            "Starting education analysis",
            resume_length=len(resume_content),
            job_description_length=len(job_description)
        )
        
        # Extract education section if not provided
        if not section_content:
            section_content = self._get_section_from_resume(resume_content)
            if not section_content:
                self.logger.warning("Could not extract education section, using full resume")
                section_content = resume_content
        
        # Get the appropriate model based on task
        model_config = await self.select_model("education_analysis", section_content)
        
        # Define the system prompt for the education analyzer
        system_prompt = self._get_education_analyzer_prompt()
        
        # Create the agent with the selected model
        education_agent = Agent(
            model_config["model"],
            output_type=EducationAnalysisResult,
            system_prompt=system_prompt,
            thinking_config=model_config.get("thinking_config"),
            temperature=model_config.get("temperature", 0.7)
        )
        
        # Apply fallback configuration if available
        if "fallback_config" in model_config:
            education_agent.fallback_config = model_config["fallback_config"]
        
        self.logger.info(
            "Education agent created",
            model=model_config["model"],
            temperature=model_config.get("temperature", 0.7)
        )
        
        # Build the input for the agent
        context_dict = context or {}
        input_message = f"""
        # Resume Content
        {resume_content}
        
        # Job Description
        {job_description}
        
        # Education Section
        {section_content}
        
        {f"# Additional Context\n{json.dumps(context_dict, indent=2)}" if context_dict else ""}
        
        Analyze the education and certification sections of this resume against the job description and provide detailed feedback.
        """
        
        try:
            # Run the agent
            agent_result = await education_agent.run(input_message)
            result = agent_result.output
            
            # Log the success and timing
            elapsed_time = time.time() - start_time
            self.logger.info(
                "Education analysis completed successfully",
                elapsed_seconds=round(elapsed_time, 2),
                score=result.score,
                education_matches_count=len(result.education_matches),
                education_gaps_count=len(result.education_gaps),
                certification_matches_count=len(result.certification_matches),
                certification_gaps_count=len(result.certification_gaps),
                recommendations_count=len(result.recommendations)
            )
            
            return result
            
        except Exception as e:
            # Log the error
            elapsed_time = time.time() - start_time
            self.logger.error(
                "Error in education analysis",
                error=str(e),
                elapsed_seconds=round(elapsed_time, 2)
            )
            
            # Return a default result with error information
            return EducationAnalysisResult(
                section_type=SectionType.EDUCATION,
                score=50,  # Default middle score
                education_matches=[],
                education_gaps=[],
                certification_matches=[],
                certification_gaps=[],
                relevant_coursework_opportunities=[],
                recommendations=[
                    SectionRecommendation(
                        what="Retry education analysis",
                        why="Error occurred during analysis",
                        how=f"Try again with more specific education section",
                        priority=10,
                        before_text=None,
                        after_text=None
                    )
                ],
                issues=[
                    SectionIssue(
                        issue_type="error",
                        description=f"Analysis error: {str(e)}",
                        severity=8,
                        fix_suggestion="Try again with more focused education section"
                    )
                ],
                strengths=[],
                improvement_suggestions=[],
                metadata={"error": str(e)}
            )
    
    def _get_education_analyzer_prompt(self) -> str:
        """Get the system prompt for the education analyzer agent."""
        # The prompt varies based on customization level
        depth_instruction = "Provide a balanced analysis focusing on key education and certification requirements"
        if self.customization_level == CustomizationLevel.CONSERVATIVE:
            depth_instruction = "Focus on the most critical education requirements and high-priority improvements"
        elif self.customization_level == CustomizationLevel.EXTENSIVE:
            depth_instruction = "Provide an extremely detailed analysis covering all aspects of education and certification alignment"
        
        return f"""
        You are an expert ATS (Applicant Tracking System) and resume education analyzer. Your task is to analyze the education and certification sections of a resume against a job description and provide detailed feedback and recommendations.

        # Approach
        1. Identify educational requirements and preferred certifications in the job description
        2. Extract and analyze the candidate's educational background and certifications from the resume
        3. Evaluate how well the candidate's qualifications align with the job requirements
        4. Identify qualification gaps and opportunities to better highlight relevant education
        5. {depth_instruction}

        # Analysis Requirements
        - Consider degree level alignment (Associate, Bachelor's, Master's, PhD)
        - Evaluate field of study relevance (major, specialization)
        - Assess educational institution reputation when relevant
        - Identify relevant coursework and academic projects
        - Evaluate certification relevance, recency, and validity
        - Consider continuing education and professional development
        - Look for educational achievements and honors
        - Identify educational keywords and terminology

        # Output Format
        Your analysis must include:
        - Overall education alignment score (0-100)
        - List of education qualifications matching job requirements
        - List of education gaps compared to job requirements
        - List of certifications matching job requirements
        - List of certification gaps compared to job requirements
        - Specific recommendations for improving education and certification presentation
        - Identified issues in education presentation
        - Strengths of the education section
        - Practical improvement suggestions
        - Opportunities to highlight relevant coursework or academic projects

        Before providing your results, consider multiple perspectives, including:
        - How an ATS system would parse and score these qualifications
        - How a hiring manager would perceive the relevance of these qualifications
        - Industry standards and expectations for this role
        - The relative importance of formal education versus certifications for this position
        
        IMPORTANT: Do not fabricate education or certifications or suggest adding qualifications that aren't already present in the resume. Focus on better highlighting and phrasing existing qualifications, and identifying genuine gaps.
        """