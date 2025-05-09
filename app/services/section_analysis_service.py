"""
Service layer for integrating section analyzers with the resume customization process.

This module provides the interface between the section analyzers and the rest of the
resume customization system, enabling both standalone section analysis and integration
with the existing customization workflow.
"""
import time
from typing import Dict, Any, List, Optional
import logfire

from app.db.session import get_db
from sqlalchemy.orm import Session
from app.models.resume import Resume, ResumeVersion
from app.models.job import JobDescription
from app.schemas.customize import CustomizationLevel, CustomizationPlan, CustomizationPlanRequest
from app.services.model_selector import ModelProvider
from app.services.section_analyzers.base import SectionType
from app.services.section_analyzers.synthesis import ResumeAnalysisSynthesizer
from app.schemas.section_analyzers import CombinedAnalysisResult


class SectionAnalysisService:
    """
    Service for integrating section analyzers with the resume customization process.
    
    This service provides methods for running individual or combined section analyzers
    and integrating the results with the existing customization workflow.
    """
    
    def __init__(self, db: Session):
        """
        Initialize the section analysis service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.logger = logfire.logger.getChild(self.__class__.__name__)
        self.logger.info("Section analysis service initialized")
    
    async def analyze_resume_sections(
        self,
        resume_id: str,
        job_id: str,
        customization_strength: CustomizationLevel = CustomizationLevel.BALANCED,
        industry: Optional[str] = None,
        enabled_analyzers: Optional[List[SectionType]] = None,
        preferred_model_provider: Optional[ModelProvider] = None
    ) -> CombinedAnalysisResult:
        """
        Analyze a resume using the specialized section analyzers.
        
        Args:
            resume_id: Resume ID
            job_id: Job description ID
            customization_strength: Level of customization
            industry: Optional industry name for industry-specific guidance
            enabled_analyzers: Optional list of section analyzers to enable
            preferred_model_provider: Optional preferred AI model provider
            
        Returns:
            CombinedAnalysisResult with synthesized analysis from all analyzers
        """
        start_time = time.time()
        self.logger.info(
            "Starting section analysis for resume",
            resume_id=resume_id,
            job_id=job_id,
            customization_level=customization_strength.name,
            industry=industry if industry else "not specified"
        )
        
        # Get resume and job description
        resume_content, job_description = await self._get_resume_and_job(resume_id, job_id)
        
        # Create synthesizer
        synthesizer = ResumeAnalysisSynthesizer(
            preferred_model_provider=preferred_model_provider,
            customization_level=customization_strength,
            enabled_analyzers=enabled_analyzers
        )
        
        # Create context with industry information if provided
        context = {}
        if industry:
            context["industry"] = industry
        
        # Run the analysis
        combined_result = await synthesizer.analyze_resume(
            resume_content=resume_content,
            job_description=job_description,
            context=context
        )
        
        # Log completion
        elapsed_time = time.time() - start_time
        self.logger.info(
            "Section analysis completed",
            resume_id=resume_id,
            job_id=job_id,
            overall_score=combined_result.overall_score,
            recommendation_count=len(combined_result.integrated_recommendations),
            elapsed_seconds=round(elapsed_time, 2)
        )
        
        return combined_result
    
    async def generate_customization_plan(
        self,
        request: CustomizationPlanRequest
    ) -> CustomizationPlan:
        """
        Generate a detailed customization plan using section analyzers.
        
        This method is compatible with the existing customization service interface
        but uses the new section analyzers for more detailed analysis.
        
        Args:
            request: The customization plan request
            
        Returns:
            CustomizationPlan with detailed recommendations
        """
        start_time = time.time()
        self.logger.info(
            "Generating customization plan with section analyzers",
            resume_id=request.resume_id,
            job_id=request.job_description_id,
            customization_level=request.customization_strength.name,
            industry=request.industry if request.industry else "not specified"
        )
        
        # Get resume and job description
        resume_content, job_description = await self._get_resume_and_job(
            request.resume_id, request.job_description_id
        )
        
        # Determine which analyzers to use based on customization level
        enabled_analyzers = [SectionType.SKILLS, SectionType.EXPERIENCE]  # Always include these
        
        # Add more analyzers for higher customization levels
        if request.customization_strength in [CustomizationLevel.BALANCED, CustomizationLevel.EXTENSIVE]:
            enabled_analyzers.extend([SectionType.EDUCATION, SectionType.ACHIEVEMENTS])
            
        if request.customization_strength == CustomizationLevel.EXTENSIVE:
            enabled_analyzers.append(SectionType.ALL)  # Add language/tone for extensive
        
        # Create synthesizer
        synthesizer = ResumeAnalysisSynthesizer(
            customization_level=request.customization_strength,
            enabled_analyzers=enabled_analyzers
        )
        
        # Create context with industry and ATS analysis if provided
        context = {}
        if request.industry:
            context["industry"] = request.industry
        if request.ats_analysis:
            context["ats_analysis"] = request.ats_analysis
        
        # Run the analysis
        combined_result = await synthesizer.analyze_resume(
            resume_content=resume_content,
            job_description=job_description,
            context=context
        )
        
        # Convert to customization plan format
        customization_plan = await synthesizer.convert_to_customization_plan(
            combined_result=combined_result,
            resume_content=resume_content,
            job_description=job_description
        )
        
        # Log completion
        elapsed_time = time.time() - start_time
        self.logger.info(
            "Customization plan generation completed",
            resume_id=request.resume_id,
            job_id=request.job_description_id,
            recommendation_count=len(customization_plan.recommendations),
            elapsed_seconds=round(elapsed_time, 2)
        )
        
        return customization_plan
    
    async def _get_resume_and_job(self, resume_id: str, job_id: str) -> tuple[str, str]:
        """
        Retrieve resume content and job description from the database.
        
        Args:
            resume_id: Resume ID
            job_id: Job description ID
            
        Returns:
            Tuple of (resume_content, job_description)
            
        Raises:
            ValueError: If resume or job not found
        """
        # Get resume content
        resume_version = self.db.query(ResumeVersion).filter(
            ResumeVersion.resume_id == resume_id
        ).order_by(ResumeVersion.version_number.desc()).first()
        
        if not resume_version:
            self.logger.error("Resume version not found", resume_id=resume_id)
            raise ValueError(f"Resume content not found for ID: {resume_id}")
        
        # Get job description
        job = self.db.query(JobDescription).filter(JobDescription.id == job_id).first()
        if not job:
            self.logger.error("Job description not found", job_id=job_id)
            raise ValueError(f"Job description not found for ID: {job_id}")
        
        return resume_version.content, job.description


# Factory function to create a section analysis service
def get_section_analysis_service(db: Session) -> SectionAnalysisService:
    """
    Create a section analysis service with all required dependencies.
    
    Args:
        db: Database session
        
    Returns:
        Initialized SectionAnalysisService
    """
    return SectionAnalysisService(db)