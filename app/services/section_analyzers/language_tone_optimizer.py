"""
Language and Tone Optimizer for resume customization.

This module analyzes and optimizes the language and tone used throughout a resume,
evaluating alignment with job description language, use of action verbs, 
industry terminology, and providing recommendations for improvement.
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
from app.schemas.section_analyzers import LanguageToneAnalysisResult, SectionRecommendation, SectionIssue


class LanguageToneOptimizer(BaseSectionAnalyzer):
    """
    Specialized analyzer for language and tone used throughout a resume.
    
    This analyzer evaluates the effectiveness of language and tone used in the resume,
    focusing on action verb usage, industry terminology alignment, clarity, 
    professionalism, and consistency, providing specific recommendations for improvement.
    """
    
    def __init__(
        self,
        preferred_model_provider: Optional[ModelProvider] = None,
        customization_level: CustomizationLevel = CustomizationLevel.BALANCED
    ):
        """
        Initialize the language and tone optimizer.
        
        Args:
            preferred_model_provider: Optional preferred AI model provider
            customization_level: Customization level affecting analysis depth
        """
        super().__init__(preferred_model_provider, customization_level)
        self.logger.info("Language and tone optimizer initialized")
    
    @property
    def section_type(self) -> SectionType:
        """Get the section type this analyzer handles."""
        return SectionType.ALL  # This analyzer works across the entire resume
    
    async def analyze(
        self,
        resume_content: str,
        job_description: str,
        section_content: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> LanguageToneAnalysisResult:
        """
        Analyze the language and tone used throughout a resume.
        
        Args:
            resume_content: Full resume content
            job_description: Full job description
            section_content: Optional specific section to analyze (ignored since this works across the resume)
            context: Optional additional context for analysis
            
        Returns:
            LanguageToneAnalysisResult with detailed analysis
        """
        start_time = time.time()
        self.logger.info(
            "Starting language and tone analysis",
            resume_length=len(resume_content),
            job_description_length=len(job_description)
        )
        
        # For language and tone, we analyze the entire resume
        # But we might want to focus on specific sections like summary and experience
        
        # Get the appropriate model based on task
        model_config = await self.select_model("language_tone_analysis", resume_content)
        
        # Define the system prompt for the language tone analyzer
        system_prompt = self._get_language_tone_analyzer_prompt()
        
        # Create the agent with the selected model
        language_agent = Agent(
            model_config["model"],
            output_type=LanguageToneAnalysisResult,
            system_prompt=system_prompt,
            thinking_config=model_config.get("thinking_config"),
            temperature=model_config.get("temperature", 0.7)
        )
        
        # Apply fallback configuration if available
        if "fallback_config" in model_config:
            language_agent.fallback_config = model_config["fallback_config"]
        
        self.logger.info(
            "Language and tone agent created",
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
        
        {f"# Additional Context\n{json.dumps(context_dict, indent=2)}" if context_dict else ""}
        
        Analyze the language and tone used throughout this resume and provide detailed feedback on improving clarity, impact, and alignment with the job description terminology.
        """
        
        try:
            # Run the agent
            agent_result = await language_agent.run(input_message)
            result = agent_result.output
            
            # Log the success and timing
            elapsed_time = time.time() - start_time
            self.logger.info(
                "Language and tone analysis completed successfully",
                elapsed_seconds=round(elapsed_time, 2),
                score=result.score,
                recommendations_count=len(result.recommendations),
                issues_count=len(result.issues)
            )
            
            return result
            
        except Exception as e:
            # Log the error
            elapsed_time = time.time() - start_time
            self.logger.error(
                "Error in language and tone analysis",
                error=str(e),
                elapsed_seconds=round(elapsed_time, 2)
            )
            
            # Return a default result with error information
            return LanguageToneAnalysisResult(
                section_type=SectionType.ALL,
                score=50,  # Default middle score
                tone_assessment={},
                language_style_match={},
                action_verb_usage={},
                industry_terminology_alignment={},
                tone_improvement_opportunities=[],
                recommendations=[
                    SectionRecommendation(
                        what="Retry language and tone analysis",
                        why="Error occurred during analysis",
                        how=f"Try again with different model or settings",
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
                        fix_suggestion="Try again with different analyzer settings"
                    )
                ],
                strengths=[],
                improvement_suggestions=[],
                metadata={"error": str(e)}
            )
    
    def _get_language_tone_analyzer_prompt(self) -> str:
        """Get the system prompt for the language and tone analyzer agent."""
        # The prompt varies based on customization level
        depth_instruction = "Provide a balanced analysis focusing on key language patterns and tone issues"
        if self.customization_level == CustomizationLevel.CONSERVATIVE:
            depth_instruction = "Focus on the most critical language and tone improvements for this specific role"
        elif self.customization_level == CustomizationLevel.EXTENSIVE:
            depth_instruction = "Provide an extremely detailed analysis covering all aspects of language and tone throughout the resume"
        
        return f"""
        You are an expert resume language and tone analyst. Your task is to analyze the language and tone used throughout a resume, evaluate its effectiveness for the target job, and provide specific recommendations for improvement.

        # Approach
        1. Analyze the overall language and tone used in the resume
        2. Evaluate how well it aligns with the job description language
        3. Assess the use of action verbs, industry terminology, and professional language
        4. Identify opportunities to improve clarity, impact, and alignment
        5. {depth_instruction}

        # Analysis Requirements
        - Evaluate action verb usage and effectiveness
        - Assess language alignment with industry and job terminology
        - Identify passive voice and weak language patterns
        - Evaluate tone consistency throughout the resume
        - Check for unnecessarily complex language or jargon
        - Identify opportunities to use more impactful language
        - Assess clarity and conciseness of language
        - Evaluate the professionalism and appropriateness of tone

        # Output Format
        Your analysis must include:
        - Overall language effectiveness score (0-100)
        - Assessment of the resume's tone and its appropriateness
        - Analysis of language style match with job description
        - Evaluation of action verb usage effectiveness
        - Assessment of industry terminology alignment
        - Specific recommendations for improving language and tone
        - Identified issues in language usage
        - Strengths of the current language and tone
        - Practical improvement suggestions
        - Opportunities to improve tone and language impact

        Before providing your results, consider multiple perspectives, including:
        - How an ATS system would parse and score this language
        - How a hiring manager would perceive the tone and clarity
        - Industry standards and expectations for this role
        - The importance of specific terminology for this position
        
        IMPORTANT: Do not suggest complete rewrites of sections. Focus on specific language improvements that maintain the original content and experience while enhancing impact, clarity, and alignment with the job description.
        """