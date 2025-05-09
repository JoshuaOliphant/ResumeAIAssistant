"""
Base class and interface for specialized resume section analyzers.

This module defines the common interface for all section analyzers, ensuring consistency
in their implementation and integration with the larger resume customization system.
"""
import abc
from typing import Dict, Any, List, Optional
from enum import Enum
from pydantic import BaseModel
import logfire

from app.schemas.customize import CustomizationLevel
from app.services.model_selector import ModelProvider, select_model_for_task


class SectionType(str, Enum):
    """Types of resume sections for specialized analysis."""
    SKILLS = "skills"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    ACHIEVEMENTS = "achievements"
    SUMMARY = "summary"
    ALL = "all"  # For analyzers that work across the entire resume


class SectionAnalysisResult(BaseModel):
    """Base schema for section analysis results."""
    section_type: SectionType
    score: int
    recommendations: List[Dict[str, Any]]
    issues: List[str]
    strengths: List[str]
    improvement_suggestions: List[Dict[str, Any]]
    metadata: Dict[str, Any] = {}


class BaseSectionAnalyzer(abc.ABC):
    """
    Abstract base class for all section analyzers.
    
    Each specialized analyzer must implement this interface to ensure consistent
    integration with the resume customization system.
    """
    
    def __init__(
        self,
        preferred_model_provider: Optional[ModelProvider] = None,
        customization_level: CustomizationLevel = CustomizationLevel.BALANCED
    ):
        """
        Initialize the section analyzer.
        
        Args:
            preferred_model_provider: Optional preferred AI model provider
            customization_level: Customization level affecting analysis depth
        """
        self.preferred_model_provider = preferred_model_provider
        self.customization_level = customization_level
        self._setup_logging()
    
    def _setup_logging(self):
        """Configure logging for this analyzer."""
        self.logger = logfire.logger.getChild(self.__class__.__name__)
        self.logger.info(
            f"Initialized {self.__class__.__name__}", 
            preferred_provider=self.preferred_model_provider,
            customization_level=self.customization_level
        )
    
    @abc.abstractmethod
    async def analyze(
        self,
        resume_content: str,
        job_description: str,
        section_content: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> SectionAnalysisResult:
        """
        Analyze a specific resume section against the job description.
        
        Args:
            resume_content: Full resume content
            job_description: Full job description
            section_content: Optional specific section content if already extracted
            context: Optional additional context for analysis
            
        Returns:
            SectionAnalysisResult with analysis details
        """
        pass
    
    @abc.abstractproperty
    def section_type(self) -> SectionType:
        """Get the section type this analyzer handles."""
        pass
    
    @property
    def name(self) -> str:
        """Get the human-readable name of this analyzer."""
        return self.__class__.__name__
    
    async def select_model(self, task_name: str, content: str) -> Dict[str, Any]:
        """
        Select the appropriate model for this analyzer based on task.
        
        Args:
            task_name: The specific task being performed
            content: The content being analyzed (for complexity estimation)
            
        Returns:
            Dictionary with model configuration
        """
        # Get cost sensitivity based on customization level
        cost_sensitivity = 1.0  # Default balanced
        if self.customization_level == CustomizationLevel.CONSERVATIVE:
            cost_sensitivity = 1.5  # More cost-sensitive
        elif self.customization_level == CustomizationLevel.EXTENSIVE:
            cost_sensitivity = 0.7  # Less cost-sensitive
        
        # Use the central model selector with our preferences
        return select_model_for_task(
            task_name=f"{self.section_type.value}_{task_name}",
            content=content,
            preferred_provider=self.preferred_model_provider,
            cost_sensitivity=cost_sensitivity
        )
    
    def _get_section_from_resume(self, resume_content: str) -> Optional[str]:
        """
        Extract the relevant section from the resume content.
        
        Args:
            resume_content: Full resume content
            
        Returns:
            Extracted section content or None if not found
        """
        # Base implementation does simple keyword-based extraction
        # Subclasses can override with more sophisticated extraction logic
        section_headers = {
            SectionType.SKILLS: ["skills", "technical skills", "core competencies", "expertise"],
            SectionType.EXPERIENCE: ["experience", "work experience", "professional experience", "employment"],
            SectionType.EDUCATION: ["education", "academic background", "certifications", "academic credentials"],
            SectionType.ACHIEVEMENTS: ["achievements", "accomplishments", "key projects", "highlights"],
            SectionType.SUMMARY: ["summary", "professional summary", "profile", "objective"]
        }
        
        # If this analyzer works on the entire resume, return it all
        if self.section_type == SectionType.ALL:
            return resume_content
        
        # Otherwise try to extract the specific section
        headers = section_headers.get(self.section_type, [])
        if not headers:
            return None
        
        # Simple extraction based on section headers
        # This is a basic implementation - subclasses can override with more sophisticated logic
        lines = resume_content.split("\n")
        section_content = []
        in_section = False
        
        for i, line in enumerate(lines):
            # Check if this line looks like a section header
            line_lower = line.lower().strip()
            
            # Check if this line is our target section header
            if any(header.lower() in line_lower for header in headers):
                in_section = True
                continue
                
            # Check if we've reached the next section header (end of our section)
            if in_section:
                # If this is a header for a different section, we're done
                if any(line_lower.startswith(header.lower()) or 
                       line_lower.endswith(header.lower()) or 
                       line_lower == header.lower()
                       for section_type in SectionType if section_type != self.section_type
                       for header in section_headers.get(section_type, [])):
                    break
                
                # Otherwise add the line to our section content
                section_content.append(line)
        
        if not section_content:
            self.logger.warning(
                f"Could not extract {self.section_type.value} section",
                checked_headers=headers
            )
            return None
            
        return "\n".join(section_content)