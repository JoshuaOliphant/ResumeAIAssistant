"""
Enhanced Customization Service for resume optimization.

This service implements the enhanced parallel processing architecture for resume customization,
using advanced features like request batching, circuit breakers, caching, and a sequential
consistency pass.
"""

import uuid
import json
import time
import logfire
import asyncio
from typing import Optional, Dict, Any, List

from fastapi import Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.resume import Resume, ResumeVersion
from app.models.job import JobDescription

from app.schemas.customize import (
    CustomizationLevel, 
    CustomizationPlanRequest,
    CustomizationPlan,
    RecommendationItem
)

from app.core.logging import log_function_call
from app.services import pydanticai_service as ai_service
from app.services.prompts import MAX_FEEDBACK_ITERATIONS
from app.services.enhanced_parallel_processor import (
    EnhancedParallelProcessor,
    SectionType,
    TaskPriority,
    TaskStatus
)
from app.core.parallel_config import (
    SECTION_WEIGHTS,
    JOB_TYPE_WEIGHTS,
    get_section_model_preferences
)
from app.services.model_selector import get_model_config_for_task

class EnhancedCustomizationService:
    """
    Enhanced service for resume customization using advanced parallel processing architecture.
    
    This service leverages the enhanced parallel processing architecture with features like
    request batching, circuit breakers for API failure handling, caching, and a sequential
    consistency pass to improve performance and reliability.
    """
    
    def __init__(self, db: Session):
        """
        Initialize the enhanced customization service with dependencies.
        
        Args:
            db: Database session
        """
        self.db = db
        self.processor = EnhancedParallelProcessor()
    
    @log_function_call
    async def generate_customization_plan(self, request: CustomizationPlanRequest) -> CustomizationPlan:
        """
        Generate a detailed customization plan for a resume based on a job description.
        Uses enhanced parallel processing architecture for improved performance and reliability.
        
        Args:
            request: The customization plan request containing resume_id, job_description_id,
                    customization_strength, and optional ats_analysis
                    
        Returns:
            A CustomizationPlan with detailed recommendations
        """
        # Record start time for performance tracking
        start_time = time.time()
        
        # Gather the necessary data
        resume_content, job_description = await self._get_resume_and_job(
            request.resume_id, request.job_description_id
        )
        
        # Use provided analysis or perform basic analysis
        basic_analysis = request.ats_analysis
        if not basic_analysis:
            basic_analysis = await self._perform_basic_analysis(
                request.resume_id, request.job_description_id
            )
        
        # Evaluate the match (evaluator stage) using enhanced parallel processing
        start_time_evaluator = time.time()
        logfire.info(
            "Starting enhanced parallel evaluator stage",
            resume_id=request.resume_id,
            job_id=request.job_description_id,
            customization_level=request.customization_strength.name,
            industry=request.industry if request.industry else "not specified"
        )
        
        # Process evaluation in parallel across resume sections with enhanced features
        evaluation = await self.processor.process_resume_analysis(
            resume_content=resume_content,
            job_description=job_description,
            section_analysis_func=self._evaluate_section_match,
            basic_analysis=basic_analysis,
            customization_level=request.customization_strength,
            industry=request.industry
        )
        
        # Log evaluation results with metrics
        elapsed_time_evaluator = time.time() - start_time_evaluator
        logfire.info(
            "Enhanced parallel evaluator stage completed",
            resume_id=request.resume_id,
            job_id=request.job_description_id,
            duration_seconds=round(elapsed_time_evaluator, 2),
            match_score=evaluation.get("match_score", 0),
            term_mismatches_count=len(evaluation.get("term_mismatches", [])),
            sections_evaluated=len(evaluation.get("section_evaluations", []))
        )
        
        # Generate the optimization plan (optimizer stage) using enhanced parallel processing
        start_time_optimizer = time.time()
        logfire.info(
            "Starting enhanced parallel optimizer stage",
            resume_id=request.resume_id,
            job_id=request.job_description_id,
            customization_level=request.customization_strength.name,
            industry=request.industry if request.industry else "not specified"
        )
        
        # Process optimization plan generation in parallel with enhanced features
        plan = await self.processor.process_optimization_plan(
            resume_content=resume_content,
            job_description=job_description,
            evaluation=evaluation,
            section_optimization_func=self._generate_section_optimization_plan,
            customization_level=request.customization_strength,
            industry=request.industry
        )
        
        # Log optimizer results with metrics
        elapsed_time_optimizer = time.time() - start_time_optimizer
        logfire.info(
            "Enhanced parallel optimizer stage completed",
            resume_id=request.resume_id,
            job_id=request.job_description_id,
            duration_seconds=round(elapsed_time_optimizer, 2),
            recommendations_count=len(plan.recommendations),
            keywords_added_count=len(plan.keywords_to_add),
            formatting_suggestions_count=len(plan.formatting_suggestions)
        )
        
        # Store the plan for future reference
        try:
            await self._store_plan(
                request.resume_id,
                request.job_description_id,
                plan
            )
        except Exception as e:
            logfire.error(
                "Error storing customization plan",
                error=str(e),
                resume_id=request.resume_id,
                job_id=request.job_description_id
            )
            # Don't raise the exception since this is non-critical
        
        # Log overall performance
        total_duration = time.time() - start_time
        logfire.info(
            "Enhanced parallel customization plan generation completed",
            resume_id=request.resume_id,
            job_id=request.job_description_id,
            total_duration_seconds=round(total_duration, 2),
            evaluator_duration_seconds=round(elapsed_time_evaluator, 2),
            optimizer_duration_seconds=round(elapsed_time_optimizer, 2)
        )
        
        return plan
    
    async def _get_resume_and_job(self, resume_id: str, job_id: str) -> tuple[str, str]:
        """
        Retrieve resume content and job description from the database.
        
        Args:
            resume_id: Resume ID
            job_id: Job description ID
            
        Returns:
            Tuple of (resume_content, job_description)
            
        Raises:
            HTTPException: If resume or job not found
        """
        # Get resume content
        resume_version = self.db.query(ResumeVersion).filter(
            ResumeVersion.resume_id == resume_id
        ).order_by(ResumeVersion.version_number.desc()).first()
        
        if not resume_version:
            logfire.error("Resume version not found", resume_id=resume_id)
            raise ValueError(f"Resume content not found for ID: {resume_id}")
        
        # Get job description
        job = self.db.query(JobDescription).filter(JobDescription.id == job_id).first()
        if not job:
            logfire.error("Job description not found", job_id=job_id)
            raise ValueError(f"Job description not found for ID: {job_id}")
        
        return resume_version.content, job.description
    
    async def _perform_basic_analysis(self, resume_id: str, job_id: str) -> Dict:
        """
        Perform basic ATS analysis of resume vs job description.
        This function remains largely unchanged but now imports ATS service dynamically.
        
        Args:
            resume_id: Resume ID
            job_id: Job description ID
            
        Returns:
            Dictionary containing basic analysis results
        """
        logfire.info(
            "Performing basic ATS analysis",
            resume_id=resume_id,
            job_id=job_id
        )
        
        try:
            # Get resume content and job description
            resume_content, job_description = await self._get_resume_and_job(resume_id, job_id)
            
            # Import here to avoid circular imports
            from app.services.ats_service import analyze_resume_for_ats
            
            # Perform the analysis using the ATS service
            analysis_result = await analyze_resume_for_ats(
                resume_content=resume_content,
                job_description=job_description
            )
            
            # Add the IDs to the result
            analysis_result["resume_id"] = resume_id
            analysis_result["job_description_id"] = job_id
            
            logfire.info(
                "Basic ATS analysis completed successfully",
                resume_id=resume_id,
                job_id=job_id,
                match_score=analysis_result.get("match_score", 0)
            )
            
            return analysis_result
            
        except Exception as e:
            logfire.error(
                "Error performing basic ATS analysis",
                error=str(e),
                resume_id=resume_id,
                job_id=job_id
            )
            
            # Return a basic structure in case of error
            return {
                "resume_id": resume_id,
                "job_description_id": job_id,
                "match_score": 50,  # Default middle score
                "matching_keywords": [],
                "missing_keywords": [],
                "error": str(e)
            }
    
    async def _evaluate_section_match(
        self, 
        section_content: str, 
        job_description: str, 
        basic_analysis: Dict, 
        customization_level: CustomizationLevel,
        industry: Optional[str] = None,
        **kwargs
    ) -> Dict:
        """
        Evaluate how well a resume section matches a job description.
        This is used as a worker function for parallel section processing.
        
        Args:
            section_content: Content of a specific resume section
            job_description: Job description text
            basic_analysis: Results from basic keyword analysis
            customization_level: Customization level (affects evaluation detail)
            industry: Optional industry name for industry-specific guidance
            **kwargs: Additional arguments for tracking and caching
            
        Returns:
            Dictionary containing detailed evaluation of the section
        """
        # Determine the section type based on the content
        section_type = kwargs.get("section_type", self._detect_section_type(section_content))
        
        # For tracking, use section_name if provided
        section_name = kwargs.get("section_name", section_type)
        
        logfire.info(
            f"Evaluating {section_name} section match",
            section_name=section_name,
            section_length=len(section_content),
            job_description_length=len(job_description),
            customization_level=customization_level.name
        )
        
        # Get model preferences for this section
        model_prefs = get_section_model_preferences(section_type)
        
        # Get model configuration for this section
        model_config = get_model_config_for_task(
            task_name="resume_evaluation",
            content=section_content,
            job_description=job_description,
            industry=industry,
            preferred_provider=model_prefs.get("preferred_provider"),
            cost_sensitivity=model_prefs.get("cost_sensitivity", 1.0)
        )
        
        # Call PydanticAI service with section-specific config
        try:
            section_evaluation = await ai_service.evaluate_resume_job_match(
                resume_content=section_content,
                job_description=job_description,
                basic_analysis=basic_analysis,
                customization_level=customization_level,
                industry=industry,
                model_config=model_config
            )
            
            # Add section type to the result
            section_evaluation["section_type"] = section_type
            section_evaluation["section_name"] = section_name
            
            return section_evaluation
            
        except Exception as e:
            logfire.error(
                f"Error evaluating {section_name} section",
                error=str(e),
                error_type=type(e).__name__,
                section_name=section_name,
                section_length=len(section_content)
            )
            
            # Return basic result in case of error
            return {
                "section_type": section_type,
                "section_name": section_name,
                "match_score": 50,
                "matching_keywords": [],
                "missing_keywords": [],
                "term_mismatches": [],
                "section_evaluations": [],
                "error": str(e)
            }
    
    async def _generate_section_optimization_plan(
        self, 
        section_content: str, 
        job_description: str, 
        section_evaluation: Dict, 
        customization_level: CustomizationLevel,
        industry: Optional[str] = None,
        **kwargs
    ) -> Dict:
        """
        Generate an optimization plan for a specific resume section.
        This is used as a worker function for parallel section processing.
        
        Args:
            section_content: Content of a specific resume section
            job_description: Job description text
            section_evaluation: Evaluation dictionary for this section
            customization_level: Customization level (affects optimization detail)
            industry: Optional industry name for industry-specific guidance
            **kwargs: Additional arguments for tracking and caching
            
        Returns:
            Dictionary containing optimization plan for the section
        """
        # Determine the section type based on the content
        section_type = kwargs.get("section_type", self._detect_section_type(section_content))
        
        # For tracking, use section_name if provided
        section_name = kwargs.get("section_name", section_type)
        
        logfire.info(
            f"Generating optimization plan for {section_name} section",
            section_name=section_name,
            section_length=len(section_content),
            job_description_length=len(job_description),
            customization_level=customization_level.name
        )
        
        # Get model preferences for this section
        model_prefs = get_section_model_preferences(section_type)
        
        # Get model configuration for this section
        model_config = get_model_config_for_task(
            task_name="optimization_plan",
            content=section_content,
            job_description=job_description,
            industry=industry,
            preferred_provider=model_prefs.get("preferred_provider"),
            cost_sensitivity=model_prefs.get("cost_sensitivity", 1.0)
        )
        
        # Create a full evaluation dict if only a section evaluation was provided
        if "section_type" in section_evaluation and "match_score" not in section_evaluation:
            evaluation = {
                "match_score": 50,
                "matching_keywords": [],
                "missing_keywords": [],
                "term_mismatches": [],
                "section_evaluations": [section_evaluation]
            }
        else:
            evaluation = section_evaluation
        
        # Call PydanticAI service with section-specific config
        try:
            # Check if section is empty or too short
            if not section_content or len(section_content) < 50:
                # Return minimal empty plan for empty sections
                return {
                    "section_type": section_type,
                    "section_name": section_name,
                    "summary": f"The {section_name} section is too short or empty to optimize.",
                    "recommendations": [],
                    "keywords_to_add": [],
                    "formatting_suggestions": [],
                    "optimized_content": section_content
                }
            
            # Generate optimization plan for this section
            section_plan = await ai_service.generate_optimization_plan(
                resume_content=section_content,
                job_description=job_description,
                evaluation=evaluation,
                customization_level=customization_level,
                industry=industry,
                model_config=model_config
            )
            
            # Generate optimized content for this section
            optimized_content = await self._implement_section_optimization(
                section_content,
                section_plan,
                model_config
            )
            
            # Convert to dictionary and add section type
            if hasattr(section_plan, "dict"):
                plan_dict = section_plan.dict()
                plan_dict["section_type"] = section_type
                plan_dict["section_name"] = section_name
                plan_dict["optimized_content"] = optimized_content
                return plan_dict
            else:
                # Handle if section_plan is already a dict
                section_plan["section_type"] = section_type
                section_plan["section_name"] = section_name
                section_plan["optimized_content"] = optimized_content
                return section_plan
            
        except Exception as e:
            logfire.error(
                f"Error generating optimization plan for {section_name} section",
                error=str(e),
                error_type=type(e).__name__,
                section_name=section_name,
                section_length=len(section_content)
            )
            
            # Return minimal empty plan in case of error
            return {
                "section_type": section_type,
                "section_name": section_name,
                "summary": f"Unable to generate optimization plan for {section_name} section due to an error.",
                "recommendations": [],
                "keywords_to_add": [],
                "formatting_suggestions": [],
                "optimized_content": section_content,
                "error": str(e)
            }
    
    async def _implement_section_optimization(
        self,
        section_content: str,
        section_plan: Any,
        model_config: Dict[str, Any]
    ) -> str:
        """
        Implement optimization for a single section.
        
        Args:
            section_content: Original section content
            section_plan: Optimization plan for this section
            model_config: Model configuration for implementation
            
        Returns:
            Optimized section content
        """
        try:
            # Extract recommendations from the plan
            if hasattr(section_plan, "recommendations"):
                recommendations = section_plan.recommendations
            elif isinstance(section_plan, dict) and "recommendations" in section_plan:
                recommendations = section_plan["recommendations"]
            else:
                # No recommendations to implement
                return section_content
                
            if not recommendations:
                return section_content
                
            # Format recommendations for implementation
            impl_recommendations = []
            for rec in recommendations:
                if isinstance(rec, dict):
                    impl_recommendations.append({
                        "section": rec.get("section", ""),
                        "what": rec.get("what", ""),
                        "before_text": rec.get("before_text", ""),
                        "after_text": rec.get("after_text", "")
                    })
                else:
                    impl_recommendations.append({
                        "section": rec.section if hasattr(rec, "section") else "",
                        "what": rec.what if hasattr(rec, "what") else "",
                        "before_text": rec.before_text if hasattr(rec, "before_text") else "",
                        "after_text": rec.after_text if hasattr(rec, "after_text") else ""
                    })
            
            # Define a basic prompt for implementing the changes
            prompt = """
            You are an expert resume writer implementing optimization recommendations.
            Apply the following recommendations to the section content.
            
            Important requirements:
            1. Make ONLY the changes specified in the recommendations
            2. Replace each "before_text" with its corresponding "after_text"
            3. Preserve all content that is not explicitly changed by a recommendation
            4. Maintain the overall structure and formatting of the section
            5. Return the complete optimized section in the same format
            6. NEVER remove any experience or skills that are not explicitly part of a recommendation
            
            For each recommendation:
            - Locate the exact "before_text" in the section
            - Replace it with the exact "after_text"
            - Ensure the replacement is done correctly
            
            Return ONLY the optimized section with all recommendations applied.
            """
            
            # Create an implementation message
            implementation_message = {
                "section": section_content,
                "recommendations": impl_recommendations
            }
            
            # Create a temporary agent to implement the changes
            implementation_agent = ai_service.create_cover_letter_agent(model_config=model_config)
            
            # Build the agent message with the section and recommendations
            message = f"""
            {prompt}
            
            # Original Section
            
            {section_content}
            
            # Recommendations to Apply
            
            {json.dumps(implementation_message["recommendations"], indent=2)}
            """
            
            # Run the agent to implement the changes
            optimized_content = await ai_service._run_agent(
                agent=implementation_agent,
                message=message
            )
            
            logfire.info(
                "Section optimization implementation completed",
                original_length=len(section_content),
                optimized_length=len(optimized_content),
                recommendation_count=len(impl_recommendations)
            )
            
            return optimized_content
            
        except Exception as e:
            logfire.error(
                "Error implementing section optimization",
                error=str(e),
                error_type=type(e).__name__
            )
            # In case of error, return the original content
            return section_content
    
    def _detect_section_type(self, section_content: str) -> str:
        """
        Detect the section type from content by looking for common patterns.
        
        Args:
            section_content: Content of a specific resume section
            
        Returns:
            String indicating the section type
        """
        # Check for common section indicators in content
        section_content_lower = section_content.lower()
        
        # Define patterns for each section type
        section_patterns = {
            "summary": ["summary", "objective", "profile", "about me"],
            "experience": ["experience", "employment", "work history", "professional background"],
            "education": ["education", "degree", "university", "college", "academic"],
            "skills": ["skills", "technologies", "competencies", "expertise", "proficient in"],
            "projects": ["projects", "portfolio", "case studies", "research"],
            "certifications": ["certifications", "certificates", "licenses", "credentials"]
        }
        
        # Check for patterns in the content
        for section_type, patterns in section_patterns.items():
            if any(pattern in section_content_lower for pattern in patterns):
                return section_type
        
        # Default to other if no match
        return "other"
    
    async def _store_plan(self, resume_id: str, job_id: str, plan: CustomizationPlan) -> None:
        """
        Store the customization plan for future reference.
        This function remains largely unchanged.
        
        Args:
            resume_id: Resume ID
            job_id: Job description ID
            plan: The generated customization plan
        """
        try:
            # Import the database model
            from app.models.customization import CustomizationPlan as CustomizationPlanModel
            
            # Get the resume to find the user_id
            resume = self.db.query(Resume).filter(Resume.id == resume_id).first()
            user_id = resume.user_id if resume else None
            
            # Convert recommendations to a list of dicts for JSON storage
            recommendations_json = []
            for rec in plan.recommendations:
                # Handle both dictionary and object formats
                if isinstance(rec, dict):
                    recommendations_json.append(rec)
                else:
                    recommendations_json.append({
                        "section": rec.section,
                        "what": rec.what,
                        "why": rec.why,
                        "before_text": rec.before_text,
                        "after_text": rec.after_text,
                        "description": rec.description
                    })
            
            # Create a new plan record
            db_plan = CustomizationPlanModel(
                id=str(uuid.uuid4()),
                resume_id=resume_id,
                job_description_id=job_id,
                user_id=user_id,
                customization_strength=2,  # Default to balanced
                summary=plan.summary or "No summary provided",
                job_analysis=plan.job_analysis or "No job analysis provided",
                keywords_to_add=plan.keywords_to_add or [],
                formatting_suggestions=plan.formatting_suggestions or [],
                recommendations=recommendations_json or []
            )
            
            # Add and commit to database
            self.db.add(db_plan)
            self.db.commit()
            
            logfire.info(
                "Customization plan stored successfully",
                resume_id=resume_id,
                job_id=job_id,
                plan_id=db_plan.id,
                recommendation_count=len(plan.recommendations)
            )
            
            return db_plan.id
            
        except Exception as e:
            logfire.error(
                "Error storing customization plan",
                error=str(e),
                resume_id=resume_id,
                job_id=job_id
            )
            # Don't raise the exception since this is non-critical
            # We want the overall workflow to succeed even if storage fails

# Factory function to create a customization service
def get_enhanced_customization_service(db: Session = Depends(get_db)) -> EnhancedCustomizationService:
    """
    Create an enhanced customization service with all required dependencies.
    
    Args:
        db: Database session
        
    Returns:
        Initialized EnhancedCustomizationService
    """
    return EnhancedCustomizationService(db)