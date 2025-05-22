"""
Section Analyzer Integration for ResumeAIAssistant.

This module implements the SectionAnalyzer interface to provide a unified
integration layer for the resume section analyzer framework.
"""

from typing import Dict, Any, Optional, List
import logfire
from enum import Enum

from app.services.integration.interfaces import SectionAnalyzer, SectionType as IntegrationSectionType
from app.services.section_analyzers.base import BaseSectionAnalyzer, SectionType as BaseAnalyzerSectionType
from app.schemas.customize import CustomizationLevel


# Map section types between frameworks
SECTION_TYPE_MAPPING = {
    IntegrationSectionType.SUMMARY: BaseAnalyzerSectionType.SUMMARY,
    IntegrationSectionType.EXPERIENCE: BaseAnalyzerSectionType.EXPERIENCE,
    IntegrationSectionType.EDUCATION: BaseAnalyzerSectionType.EDUCATION,
    IntegrationSectionType.SKILLS: BaseAnalyzerSectionType.SKILLS,
    IntegrationSectionType.ACHIEVEMENTS: BaseAnalyzerSectionType.ACHIEVEMENTS,
    IntegrationSectionType.PROJECTS: BaseAnalyzerSectionType.ALL,  # Map to ALL since not explicitly in base framework
    IntegrationSectionType.OTHER: BaseAnalyzerSectionType.ALL  # Map to ALL for general content
}

# Reverse mapping
BASE_TO_INTEGRATION_TYPE = {
    BaseAnalyzerSectionType.SUMMARY: IntegrationSectionType.SUMMARY,
    BaseAnalyzerSectionType.EXPERIENCE: IntegrationSectionType.EXPERIENCE,
    BaseAnalyzerSectionType.EDUCATION: IntegrationSectionType.EDUCATION,
    BaseAnalyzerSectionType.SKILLS: IntegrationSectionType.SKILLS,
    BaseAnalyzerSectionType.ACHIEVEMENTS: IntegrationSectionType.ACHIEVEMENTS,
    BaseAnalyzerSectionType.ALL: IntegrationSectionType.OTHER
}


class IntegratedSectionAnalyzer(SectionAnalyzer):
    """Implementation of the SectionAnalyzer interface using the existing section analyzers."""
    
    def __init__(self, base_analyzer: BaseSectionAnalyzer):
        """
        Initialize the integrated section analyzer.
        
        Args:
            base_analyzer: The base section analyzer to integrate
        """
        self._base_analyzer = base_analyzer
        self._integration_section_type = BASE_TO_INTEGRATION_TYPE.get(
            base_analyzer.section_type, IntegrationSectionType.OTHER
        )
        
    @property
    def section_type(self) -> IntegrationSectionType:
        """The type of section this analyzer handles."""
        return self._integration_section_type
        
    async def analyze(self, section_content: str, 
                    job_requirements: Dict[str, Any],
                    context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Analyze a resume section and return results.
        
        Args:
            section_content: The content of the section to analyze
            job_requirements: Key requirements extracted from the job description
            context: Optional additional context for analysis
            
        Returns:
            Analysis results
        """
        context = context or {}
        
        # Map any requirements format to what the base analyzer expects
        mapped_requirements = self._map_requirements_format(job_requirements)
        
        # Get resume content from context or use section_content as full resume
        resume_content = context.get("resume_content", section_content)
        
        # Get job description from context or extract from requirements
        job_description = context.get("job_description", 
                                    job_requirements.get("job_description", ""))
        
        try:
            # Call the base analyzer with the appropriate parameters
            result = await self._base_analyzer.analyze(
                resume_content=resume_content,
                job_description=job_description,
                section_content=section_content,
                context=context
            )
            
            # Convert result to dictionary if it's a Pydantic model
            if hasattr(result, "dict"):
                return result.dict()
                
            return result
            
        except Exception as e:
            logfire.error(
                "Error analyzing section",
                section_type=str(self.section_type),
                error=str(e)
            )
            
            # Return basic error result
            return {
                "section_type": str(self.section_type),
                "score": 0,
                "recommendations": [],
                "issues": [f"Analysis failed: {str(e)}"],
                "strengths": [],
                "improvement_suggestions": [],
                "error": str(e)
            }
    
    def _map_requirements_format(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map requirements to the format expected by the base analyzer.
        
        Args:
            requirements: Requirements from the key requirements extractor
            
        Returns:
            Mapped requirements in the format expected by the analyzer
        """
        # If requirements is already in the expected format, return as is
        if "categories" in requirements:
            return requirements
            
        # Map to expected format (depends on actual implementation)
        mapped = {
            "keywords": requirements.get("keywords", {}),
            "categories": []
        }
        
        # Try to extract categories if they exist
        category_data = requirements.get("requirements", {})
        if isinstance(category_data, dict):
            for category, reqs in category_data.items():
                mapped["categories"].append({
                    "category": category,
                    "requirements": reqs if isinstance(reqs, list) else []
                })
                
        return mapped


class SectionAnalyzerFactory:
    """Factory for creating integrated section analyzers."""
    
    @staticmethod
    def create_analyzer(section_type: IntegrationSectionType, 
                       customization_level: str = "balanced") -> SectionAnalyzer:
        """
        Create an appropriate section analyzer for the given section type.
        
        Args:
            section_type: The type of section to analyze
            customization_level: Level of customization (conservative, balanced, extensive)
            
        Returns:
            An integrated section analyzer for the specified section type
        """
        # Convert customization level string to enum
        level = CustomizationLevel.BALANCED
        if customization_level.lower() == "conservative":
            level = CustomizationLevel.CONSERVATIVE
        elif customization_level.lower() == "extensive":
            level = CustomizationLevel.EXTENSIVE
            
        # Map section type to base analyzer
        base_section_type = SECTION_TYPE_MAPPING.get(section_type, BaseAnalyzerSectionType.ALL)
        
        # Import specific analyzer classes
        from app.services.section_analyzers.skills_analyzer import SkillsQualificationsAnalyzer
        from app.services.section_analyzers.experience_analyzer import ExperienceAnalyzer
        from app.services.section_analyzers.education_analyzer import EducationAnalyzer
        from app.services.section_analyzers.achievement_analyzer import AchievementAnalyzer
        from app.services.section_analyzers.language_tone_optimizer import LanguageToneOptimizer
        
        # Create base analyzer based on section type
        base_analyzer = None
        if base_section_type == BaseAnalyzerSectionType.SKILLS:
            base_analyzer = SkillsQualificationsAnalyzer(customization_level=level)
        elif base_section_type == BaseAnalyzerSectionType.EXPERIENCE:
            base_analyzer = ExperienceAnalyzer(customization_level=level)
        elif base_section_type == BaseAnalyzerSectionType.EDUCATION:
            base_analyzer = EducationAnalyzer(customization_level=level)
        elif base_section_type == BaseAnalyzerSectionType.ACHIEVEMENTS:
            base_analyzer = AchievementAnalyzer(customization_level=level)
        elif base_section_type == BaseAnalyzerSectionType.SUMMARY:
            base_analyzer = LanguageToneOptimizer(customization_level=level)
        else:
            # Default to language tone optimizer for other sections
            base_analyzer = LanguageToneOptimizer(customization_level=level)
            
        # Create and return integrated analyzer
        return IntegratedSectionAnalyzer(base_analyzer)