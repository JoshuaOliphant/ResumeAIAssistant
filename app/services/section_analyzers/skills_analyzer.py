"""
Skills and Qualifications Analyzer for resume customization.

This module analyzes the skills and qualifications section of a resume against a job description,
identifying matches, gaps, and providing specific recommendations for improvement.
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
from app.schemas.section_analyzers import SkillsAnalysisResult, KeywordMatch, KeywordGap, SectionRecommendation, SectionIssue


class SkillsQualificationsAnalyzer(BaseSectionAnalyzer):
    """
    Specialized analyzer for skills and qualifications in resumes.
    
    This analyzer identifies key skills required by the job description,
    maps them to skills mentioned in the resume, and provides recommendations
    for adding missing skills or better highlighting existing ones.
    """
    
    def __init__(
        self,
        preferred_model_provider: Optional[ModelProvider] = None,
        customization_level: CustomizationLevel = CustomizationLevel.BALANCED
    ):
        """
        Initialize the skills analyzer.
        
        Args:
            preferred_model_provider: Optional preferred AI model provider
            customization_level: Customization level affecting analysis depth
        """
        super().__init__(preferred_model_provider, customization_level)
        self.logger.info("Skills analyzer initialized")
    
    @property
    def section_type(self) -> SectionType:
        """Get the section type this analyzer handles."""
        return SectionType.SKILLS
    
    async def analyze(
        self,
        resume_content: str,
        job_description: str,
        section_content: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> SkillsAnalysisResult:
        """
        Analyze the skills and qualifications section of a resume.
        
        Args:
            resume_content: Full resume content
            job_description: Full job description
            section_content: Optional pre-extracted skills section
            context: Optional additional context for analysis
            
        Returns:
            SkillsAnalysisResult with detailed analysis
        """
        start_time = time.time()
        self.logger.info(
            "Starting skills analysis",
            resume_length=len(resume_content),
            job_description_length=len(job_description)
        )
        
        # Extract skills section if not provided
        if not section_content:
            section_content = self._get_section_from_resume(resume_content)
            if not section_content:
                self.logger.warning("Could not extract skills section, using full resume")
                section_content = resume_content
        
        # Get the appropriate model based on task
        model_config = await self.select_model("skills_analysis", section_content)
        
        # Define the system prompt for the skills analyzer
        system_prompt = self._get_skills_analyzer_prompt()
        
        # Create the agent with the selected model
        skills_agent = Agent(
            model_config["model"],
            output_type=SkillsAnalysisResult,
            system_prompt=system_prompt,
            thinking_config=model_config.get("thinking_config"),
            temperature=model_config.get("temperature", 0.7)
        )
        
        # Apply fallback configuration if available
        if "fallback_config" in model_config:
            skills_agent.fallback_config = model_config["fallback_config"]
        
        self.logger.info(
            "Skills agent created",
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
        
        # Skills Section
        {section_content}
        
        {f"# Additional Context\n{json.dumps(context_dict, indent=2)}" if context_dict else ""}
        
        Analyze the skills section of this resume against the job description and provide detailed feedback.
        """
        
        try:
            # Run the agent
            agent_result = await skills_agent.run(input_message)
            result = agent_result.output
            
            # Log the success and timing
            elapsed_time = time.time() - start_time
            self.logger.info(
                "Skills analysis completed successfully",
                elapsed_seconds=round(elapsed_time, 2),
                score=result.score,
                matching_skills_count=len(result.matching_skills),
                missing_skills_count=len(result.missing_skills),
                recommendations_count=len(result.recommendations)
            )
            
            return result
            
        except Exception as e:
            # Log the error
            elapsed_time = time.time() - start_time
            self.logger.error(
                "Error in skills analysis",
                error=str(e),
                elapsed_seconds=round(elapsed_time, 2)
            )
            
            # Return a default result with error information
            return SkillsAnalysisResult(
                section_type=SectionType.SKILLS,
                score=50,  # Default middle score
                job_required_skills=[],
                matching_skills=[],
                missing_skills=[],
                skill_categorization={},
                recommendations=[
                    SectionRecommendation(
                        what="Retry skills analysis",
                        why="Error occurred during analysis",
                        how=f"Try again with more specific skills section",
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
                        fix_suggestion="Try again with more focused skills section"
                    )
                ],
                strengths=[],
                improvement_suggestions=[],
                metadata={"error": str(e)}
            )
    
    def _get_skills_analyzer_prompt(self) -> str:
        """Get the system prompt for the skills analyzer agent."""
        # The prompt varies based on customization level
        depth_instruction = "Provide a detailed and comprehensive analysis"
        if self.customization_level == CustomizationLevel.CONSERVATIVE:
            depth_instruction = "Focus on the most critical skills gaps and high-priority improvements"
        elif self.customization_level == CustomizationLevel.EXTENSIVE:
            depth_instruction = "Provide an extremely detailed analysis covering all aspects of skills alignment"
        
        return f"""
        You are an expert ATS (Applicant Tracking System) and resume skills analyzer. Your task is to analyze the skills section of a resume against a job description and provide detailed feedback and recommendations.

        # Approach
        1. Identify all hard and soft skills mentioned in the job description
        2. Extract all skills mentioned in the resume
        3. Match skills between resume and job description, accounting for synonyms and related terms
        4. Categorize skills (technical, soft, domain-specific, tools, methodologies, etc.)
        5. Identify high-priority skill gaps
        6. {depth_instruction}

        # Analysis Requirements
        - Consider both explicit skills and implied skills
        - Account for different terminology that may refer to the same skill
        - Evaluate both the presence of skills and how they are presented
        - Consider industry-specific terminology and expectations
        - Focus on skills that are most relevant to the target job
        - Provide specific, actionable recommendations

        # Output Format
        Your analysis must include:
        - Overall match score (0-100)
        - List of skills required by the job
        - List of matching skills found in the resume
        - List of missing skills not found in the resume
        - Categorization of skills by type
        - Specific recommendations for improvement
        - Identified issues in the skills section
        - Strengths of the skills section
        - Practical improvement suggestions

        Before providing your results, consider multiple perspectives, including:
        - How an ATS system would parse and score these skills
        - How a hiring manager would perceive these skills
        - Industry standards and expectations for this role
        - The relative importance of different skills for this position
        
        IMPORTANT: Do not fabricate or suggest adding skills that aren't already present in the resume in some form. Focus on better highlighting and phrasing existing skills, and identifying genuine gaps.
        """