"""
Achievement Quantification Analyzer for resume customization.

This module analyzes achievements throughout a resume against a job description,
evaluating the effectiveness of achievement statements, identifying opportunities
to better quantify results, and providing specific recommendations for improvement.
"""
import json
import time
import re
from typing import Dict, Any, List, Optional
import logfire

from pydantic import BaseModel
from pydantic_ai import Agent

from app.core.config import settings
from app.schemas.customize import CustomizationLevel
from app.services.model_selector import ModelProvider, select_model_for_task
from app.services.section_analyzers.base import BaseSectionAnalyzer, SectionType
from app.schemas.section_analyzers import AchievementAnalysisResult, SectionRecommendation, SectionIssue


class AchievementQuantificationAnalyzer(BaseSectionAnalyzer):
    """
    Specialized analyzer for achievements in resumes.
    
    This analyzer evaluates how effectively achievements are quantified throughout
    the resume, identifies opportunities to add metrics and measurable results,
    and provides specific recommendations for strengthening achievement statements.
    """
    
    def __init__(
        self,
        preferred_model_provider: Optional[ModelProvider] = None,
        customization_level: CustomizationLevel = CustomizationLevel.BALANCED
    ):
        """
        Initialize the achievement analyzer.
        
        Args:
            preferred_model_provider: Optional preferred AI model provider
            customization_level: Customization level affecting analysis depth
        """
        super().__init__(preferred_model_provider, customization_level)
        self.logger.info("Achievement analyzer initialized")
    
    @property
    def section_type(self) -> SectionType:
        """Get the section type this analyzer handles."""
        return SectionType.ACHIEVEMENTS
    
    async def analyze(
        self,
        resume_content: str,
        job_description: str,
        section_content: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> AchievementAnalysisResult:
        """
        Analyze achievements throughout a resume.
        
        Args:
            resume_content: Full resume content
            job_description: Full job description
            section_content: Optional pre-extracted achievements section
            context: Optional additional context for analysis
            
        Returns:
            AchievementAnalysisResult with detailed analysis
        """
        start_time = time.time()
        self.logger.info(
            "Starting achievement analysis",
            resume_length=len(resume_content),
            job_description_length=len(job_description)
        )
        
        # For achievements, we want to analyze both specific achievements sections
        # AND achievement statements throughout the resume, especially in experience
        achievements = []
        
        # Extract specific achievements section if available
        if not section_content:
            section_content = self._get_section_from_resume(resume_content)
            if section_content:
                achievements.append(section_content)
        else:
            achievements.append(section_content)
            
        # Extract experience section to look for achievements there
        experience_section = self._extract_experience_section(resume_content)
        if experience_section:
            achievements.append(experience_section)
            
        # If we still don't have any achievement content, use the full resume
        if not achievements:
            self.logger.warning("Could not extract achievement or experience sections, using full resume")
            achievements = [resume_content]
            
        # Join the achievement sections
        achievement_content = "\n\n".join(achievements)
        
        # Get the appropriate model based on task
        model_config = await self.select_model("achievement_analysis", achievement_content)
        
        # Define the system prompt for the achievement analyzer
        system_prompt = self._get_achievement_analyzer_prompt()
        
        # Create the agent with the selected model
        achievement_agent = Agent(
            model_config["model"],
            output_type=AchievementAnalysisResult,
            system_prompt=system_prompt,
            thinking_config=model_config.get("thinking_config"),
            temperature=model_config.get("temperature", 0.7)
        )
        
        # Apply fallback configuration if available
        if "fallback_config" in model_config:
            achievement_agent.fallback_config = model_config["fallback_config"]
        
        self.logger.info(
            "Achievement agent created",
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
        
        # Achievement-Related Content
        {achievement_content}
        
        {additional_context}
        
        Analyze the achievements in this resume, including achievements mentioned in work experience sections.
        Focus on how well achievements are quantified and provide detailed feedback on improving achievement statements.
        """
        
        # Format the template with the needed values
        input_message = input_template.format(
            resume_content=resume_content,
            job_description=job_description,
            achievement_content=achievement_content,
            additional_context=additional_context
        )
        
        try:
            # Run the agent
            agent_result = await achievement_agent.run(input_message)
            result = agent_result.output
            
            # Log the success and timing
            elapsed_time = time.time() - start_time
            self.logger.info(
                "Achievement analysis completed successfully",
                elapsed_seconds=round(elapsed_time, 2),
                score=result.score,
                quantified_achievements_count=len(result.quantified_achievements),
                unquantified_achievements_count=len(result.unquantified_achievements),
                recommendations_count=len(result.recommendations)
            )
            
            return result
            
        except Exception as e:
            # Log the error
            elapsed_time = time.time() - start_time
            self.logger.error(
                "Error in achievement analysis",
                error=str(e),
                elapsed_seconds=round(elapsed_time, 2)
            )
            
            # Return a default result with error information
            return AchievementAnalysisResult(
                section_type=SectionType.ACHIEVEMENTS,
                score=50,  # Default middle score
                quantified_achievements=[],
                unquantified_achievements=[],
                impact_assessment={},
                quantification_opportunities=[],
                recommendations=[
                    SectionRecommendation(
                        what="Retry achievement analysis",
                        why="Error occurred during analysis",
                        how=f"Try again with more specific achievement statements",
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
                        fix_suggestion="Try again with more focused achievement statements"
                    )
                ],
                strengths=[],
                improvement_suggestions=[],
                metadata={"error": str(e)}
            )
    
    def _extract_experience_section(self, resume_content: str) -> Optional[str]:
        """
        Extract the experience section from the resume content.
        
        Args:
            resume_content: Full resume content
            
        Returns:
            Extracted experience section or None if not found
        """
        # Similar to the base class _get_section_from_resume method but specifically for experience
        experience_headers = ["experience", "work experience", "professional experience", "employment", "work history"]
        
        lines = resume_content.split("\n")
        section_content = []
        in_section = False
        
        for i, line in enumerate(lines):
            # Check if this line looks like a section header
            line_lower = line.lower().strip()
            
            # Check if this line is our target section header
            if any(header.lower() in line_lower for header in experience_headers):
                in_section = True
                continue
                
            # Check if we've reached the next section header (end of our section)
            if in_section:
                # Common section headers that would indicate the end of experience section
                end_section_headers = [
                    "education", "skills", "certifications", "awards", 
                    "publications", "projects", "languages", "interests",
                    "volunteer", "references", "additional information"
                ]
                
                # If this is a header for a different section, we're done
                if any(header.lower() in line_lower and header.lower() in end_section_headers for header in end_section_headers):
                    break
                
                # Otherwise add the line to our section content
                section_content.append(line)
        
        if not section_content:
            self.logger.warning("Could not extract experience section")
            return None
            
        return "\n".join(section_content)
    
    def _get_achievement_analyzer_prompt(self) -> str:
        """Get the system prompt for the achievement analyzer agent."""
        # The prompt varies based on customization level
        depth_instruction = "Provide a balanced analysis focusing on key achievement statements"
        if self.customization_level == CustomizationLevel.CONSERVATIVE:
            depth_instruction = "Focus on the most critical achievement improvements for this specific role"
        elif self.customization_level == CustomizationLevel.EXTENSIVE:
            depth_instruction = "Provide an extremely detailed analysis covering all aspects of achievement quantification and impact"
        
        # Create prompt template as raw string
        prompt_template = r"""
        You are an expert resume achievement analyst specializing in achievement quantification. Your task is to analyze achievement statements in a resume against a job description and provide detailed feedback on how to improve the quantification and impact of these achievements.

        # Approach
        1. Identify all achievement statements throughout the resume, especially in work experience
        2. Categorize achievements as either quantified (with metrics) or unquantified
        3. Evaluate the impact and relevance of each achievement to the target job
        4. Identify opportunities to better quantify achievements with metrics
        5. {depth_instruction}

        # Analysis Requirements
        - Look for achievement statements using action verbs
        - Identify metrics and quantifiable results (%, $, #, time saved, etc.)
        - Evaluate whether the achievements demonstrate skills relevant to the job
        - Assess the specificity and clarity of achievement statements
        - Identify opportunities to add specific metrics to unquantified achievements
        - Consider the impact and scale of each achievement
        - Look for achievement patterns that could be better organized
        - Evaluate the use of action verbs and results-oriented language

        # Output Format
        Your analysis must include:
        - Overall achievement effectiveness score (0-100)
        - List of quantified achievements with existing metrics
        - List of unquantified achievements that need metrics
        - Assessment of achievement impact and relevance
        - Specific recommendations for improving achievement statements
        - Identified issues in achievement presentation
        - Strengths of the current achievement statements
        - Practical improvement suggestions
        - Opportunities to add specific metrics to achievements

        Before providing your results, consider multiple perspectives, including:
        - How an ATS system would parse and score these achievement statements
        - How a hiring manager would perceive the impact of these achievements
        - Industry standards and expectations for this role
        - The relative importance of different types of achievements for this position
        
        IMPORTANT: Do not fabricate achievements or suggest adding accomplishments that aren't already mentioned in the resume. Focus on better quantifying and highlighting existing achievements, and identifying opportunities to add metrics to statements that are already present.
        """
        
        # Format the prompt with the depth instruction
        return prompt_template.format(depth_instruction=depth_instruction)