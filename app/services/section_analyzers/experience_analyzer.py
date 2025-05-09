"""
Experience Alignment Analyzer for resume customization.

This module analyzes the professional experience section of a resume against a job description,
evaluating the alignment of the candidate's experience with the job requirements and
providing specific recommendations for better highlighting relevant experience.
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
from app.schemas.section_analyzers import ExperienceAnalysisResult, SectionRecommendation, SectionIssue


class ExperienceAlignmentAnalyzer(BaseSectionAnalyzer):
    """
    Specialized analyzer for professional experience in resumes.
    
    This analyzer evaluates how well the candidate's professional experience aligns with
    the job requirements, identifies gaps and opportunities for better highlighting relevant
    experience, and provides specific recommendations for improvement.
    """
    
    def __init__(
        self,
        preferred_model_provider: Optional[ModelProvider] = None,
        customization_level: CustomizationLevel = CustomizationLevel.BALANCED
    ):
        """
        Initialize the experience analyzer.
        
        Args:
            preferred_model_provider: Optional preferred AI model provider
            customization_level: Customization level affecting analysis depth
        """
        super().__init__(preferred_model_provider, customization_level)
        self.logger.info("Experience analyzer initialized")
    
    @property
    def section_type(self) -> SectionType:
        """Get the section type this analyzer handles."""
        return SectionType.EXPERIENCE
    
    async def analyze(
        self,
        resume_content: str,
        job_description: str,
        section_content: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ExperienceAnalysisResult:
        """
        Analyze the professional experience section of a resume.
        
        Args:
            resume_content: Full resume content
            job_description: Full job description
            section_content: Optional pre-extracted experience section
            context: Optional additional context for analysis
            
        Returns:
            ExperienceAnalysisResult with detailed analysis
        """
        start_time = time.time()
        self.logger.info(
            "Starting experience analysis",
            resume_length=len(resume_content),
            job_description_length=len(job_description)
        )
        
        # Extract experience section if not provided
        if not section_content:
            section_content = self._get_section_from_resume(resume_content)
            if not section_content:
                self.logger.warning("Could not extract experience section, using full resume")
                section_content = resume_content
        
        # Get the appropriate model based on task
        model_config = await self.select_model("experience_analysis", section_content)
        
        # Define the system prompt for the experience analyzer
        system_prompt = self._get_experience_analyzer_prompt()
        
        # Create the agent with the selected model
        experience_agent = Agent(
            model_config["model"],
            output_type=ExperienceAnalysisResult,
            system_prompt=system_prompt,
            thinking_config=model_config.get("thinking_config"),
            temperature=model_config.get("temperature", 0.7)
        )
        
        # Apply fallback configuration if available
        if "fallback_config" in model_config:
            experience_agent.fallback_config = model_config["fallback_config"]
        
        self.logger.info(
            "Experience agent created",
            model=model_config["model"],
            temperature=model_config.get("temperature", 0.7)
        )
        
        # Build the input for the agent
        context_dict = context or {}
        
        # Format additional context section conditionally
        additional_context = ""
        if context_dict:
            additional_context = f"# Additional Context\n{json.dumps(context_dict, indent=2)}"
        
        # Create the input message using a template
        input_template = """
        # Resume Content
        {resume_content}
        
        # Job Description
        {job_description}
        
        # Experience Section
        {section_content}
        
        {additional_context}
        
        Analyze the professional experience section of this resume against the job description and provide detailed feedback.
        """
        
        # Format the template with the needed values
        input_message = input_template.format(
            resume_content=resume_content,
            job_description=job_description,
            section_content=section_content,
            additional_context=additional_context
        )
        
        try:
            # Run the agent
            agent_result = await experience_agent.run(input_message)
            result = agent_result.output
            
            # Log the success and timing
            elapsed_time = time.time() - start_time
            self.logger.info(
                "Experience analysis completed successfully",
                elapsed_seconds=round(elapsed_time, 2),
                score=result.score,
                relevant_experiences_count=len(result.relevant_experiences),
                missing_experiences_count=len(result.missing_experiences),
                recommendations_count=len(result.recommendations)
            )
            
            return result
            
        except Exception as e:
            # Log the error
            elapsed_time = time.time() - start_time
            self.logger.error(
                "Error in experience analysis",
                error=str(e),
                elapsed_seconds=round(elapsed_time, 2)
            )
            
            # Return a default result with error information
            return ExperienceAnalysisResult(
                section_type=SectionType.EXPERIENCE,
                score=50,  # Default middle score
                relevant_experiences=[],
                missing_experiences=[],
                experience_alignment={},
                role_specific_keywords=[],
                keyword_alignment_opportunities=[],
                recommendations=[
                    SectionRecommendation(
                        what="Retry experience analysis",
                        why="Error occurred during analysis",
                        how=f"Try again with more specific experience section",
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
                        fix_suggestion="Try again with more focused experience section"
                    )
                ],
                strengths=[],
                improvement_suggestions=[],
                metadata={"error": str(e)}
            )
    
    def _get_experience_analyzer_prompt(self) -> str:
        """Get the system prompt for the experience analyzer agent."""
        # The prompt varies based on customization level
        depth_instruction = "Provide a balanced analysis focusing on key alignment issues"
        if self.customization_level == CustomizationLevel.CONSERVATIVE:
            depth_instruction = "Focus on the most critical experience gaps and high-priority improvements"
        elif self.customization_level == CustomizationLevel.EXTENSIVE:
            depth_instruction = "Provide an extremely detailed analysis covering all aspects of experience alignment"
        
        # Create prompt template as raw string
        prompt_template = r"""
        You are an expert ATS (Applicant Tracking System) and resume experience analyzer. Your task is to analyze the professional experience section of a resume against a job description and provide detailed feedback and recommendations.

        # Approach
        1. Identify key responsibilities and required experience in the job description
        2. Extract and analyze the candidate's professional experiences from the resume
        3. Evaluate how well each experience aligns with the job requirements
        4. Identify experience gaps and opportunities to better highlight relevant experience
        5. {depth_instruction}

        # Analysis Requirements
        - Consider job title alignment and job function similarity
        - Evaluate experience relevance, recency, and duration
        - Assess achievement alignment with job responsibilities
        - Identify domain/industry experience relevance
        - Evaluate leadership/management experience if relevant
        - Assess team size and scope of responsibility
        - Consider project complexity and impact
        - Look for experience with relevant tools, technologies, and methodologies
        - Identify role-specific keywords and terminology in experiences

        # Output Format
        Your analysis must include:
        - Overall alignment score (0-100)
        - List of experiences relevant to the job requirements
        - List of missing experiences compared to job requirements
        - Detailed alignment assessment for each major job requirement
        - Role-specific keywords found in experiences
        - Specific recommendations for improving experience descriptions
        - Identified issues in experience presentation
        - Strengths of the experience section
        - Practical improvement suggestions
        - Opportunities to better align keywords in experience descriptions

        Before providing your results, consider multiple perspectives, including:
        - How an ATS system would parse and score these experiences
        - How a hiring manager would perceive the relevance of these experiences
        - Industry standards and expectations for this role
        - The relative importance of different experiences for this position
        
        IMPORTANT: Do not fabricate experiences or suggest adding experience that isn't already present in the resume. Focus on better highlighting and phrasing existing experiences, and identifying genuine gaps.
        """
        
        # Format the prompt with the depth instruction
        return prompt_template.format(depth_instruction=depth_instruction)