"""
Parallel Customization Service for resume optimization.

This service implements the parallel processing architecture for resume customization,
using the evaluator-optimizer pattern with concurrent processing of resume sections.
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
from app.services.parallel_processor import (
    ParallelProcessor,
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

class ParallelCustomizationService:
    """
    Service for resume customization using parallel processing architecture.
    
    This service leverages the evaluator-optimizer pattern with parallel processing
    to improve performance and reduce the time needed for resume customization.
    """
    
    def __init__(self, db: Session):
        """
        Initialize the parallel customization service with dependencies.
        
        Args:
            db: Database session
        """
        self.db = db
        self.processor = ParallelProcessor()
    
    @log_function_call
    async def generate_customization_plan(self, request: CustomizationPlanRequest) -> CustomizationPlan:
        """
        Generate a detailed customization plan for a resume based on a job description.
        Uses parallel processing architecture to improve performance.
        
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
        
        # Evaluate the match (evaluator stage) using parallel processing
        start_time_evaluator = time.time()
        logfire.info(
            "Starting parallel evaluator stage",
            resume_id=request.resume_id,
            job_id=request.job_description_id,
            customization_level=request.customization_strength.name,
            industry=request.industry if request.industry else "not specified"
        )
        
        # Process evaluation in parallel across resume sections
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
            "Parallel evaluator stage completed",
            resume_id=request.resume_id,
            job_id=request.job_description_id,
            duration_seconds=round(elapsed_time_evaluator, 2),
            match_score=evaluation.get("match_score", 0),
            term_mismatches_count=len(evaluation.get("term_mismatches", [])),
            sections_evaluated=len(evaluation.get("section_evaluations", []))
        )
        
        # Generate the optimization plan (optimizer stage) using parallel processing
        start_time_optimizer = time.time()
        logfire.info(
            "Starting parallel optimizer stage",
            resume_id=request.resume_id,
            job_id=request.job_description_id,
            customization_level=request.customization_strength.name,
            industry=request.industry if request.industry else "not specified"
        )
        
        # Process optimization plan generation in parallel across resume sections
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
            "Parallel optimizer stage completed",
            resume_id=request.resume_id,
            job_id=request.job_description_id,
            duration_seconds=round(elapsed_time_optimizer, 2),
            recommendations_count=len(plan.recommendations),
            keywords_added_count=len(plan.keywords_to_add),
            formatting_suggestions_count=len(plan.formatting_suggestions)
        )
        
        # Store the plan for future reference
        await self._store_plan(
            request.resume_id,
            request.job_description_id,
            plan
        )
        
        # Log overall performance
        total_duration = time.time() - start_time
        logfire.info(
            "Parallel customization plan generation completed",
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
        industry: Optional[str] = None
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
            
        Returns:
            Dictionary containing detailed evaluation of the section
        """
        # Determine the section type based on the content
        section_type = self._detect_section_type(section_content)
        
        logfire.info(
            f"Evaluating {section_type} section match",
            section_type=section_type,
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
            
            return section_evaluation
            
        except Exception as e:
            logfire.error(
                f"Error evaluating {section_type} section",
                error=str(e),
                error_type=type(e).__name__,
                section_type=section_type,
                section_length=len(section_content)
            )
            
            # Return basic result in case of error
            return {
                "section_type": section_type,
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
        industry: Optional[str] = None
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
            
        Returns:
            Dictionary containing optimization plan for the section
        """
        # Determine the section type based on the content
        section_type = self._detect_section_type(section_content)
        
        logfire.info(
            f"Generating optimization plan for {section_type} section",
            section_type=section_type,
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
                    "summary": f"The {section_type} section is too short or empty to optimize.",
                    "recommendations": [],
                    "keywords_to_add": [],
                    "formatting_suggestions": []
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
            
            # Convert to dictionary and add section type
            if hasattr(section_plan, "dict"):
                plan_dict = section_plan.dict()
                plan_dict["section_type"] = section_type
                return plan_dict
            else:
                # Handle if section_plan is already a dict
                section_plan["section_type"] = section_type
                return section_plan
            
        except Exception as e:
            logfire.error(
                f"Error generating optimization plan for {section_type} section",
                error=str(e),
                error_type=type(e).__name__,
                section_type=section_type,
                section_length=len(section_content)
            )
            
            # Return minimal empty plan in case of error
            return {
                "section_type": section_type,
                "summary": f"Unable to generate optimization plan for {section_type} section due to an error.",
                "recommendations": [],
                "keywords_to_add": [],
                "formatting_suggestions": [],
                "error": str(e)
            }
    
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
    
    async def _implement_optimization_plan(self, resume_content: str, plan: CustomizationPlan) -> str:
        """
        Implement an optimization plan by applying its recommendations to the resume.
        
        Args:
            resume_content: Original resume content
            plan: Customization plan with recommendations
            
        Returns:
            Optimized resume content with recommendations applied
        """
        # For now, we'll use the OpenAI implementation service to apply the recommendations
        # This remains largely unchanged as implementation is not parallelized currently
        
        # Create a simplified implementation message
        implementation_message = {
            "resume": resume_content,
            "plan": {
                "summary": plan.summary,
                "recommendations": [
                    {
                        "section": rec.section,
                        "what": rec.what,
                        "before_text": rec.before_text,
                        "after_text": rec.after_text
                    }
                    for rec in plan.recommendations
                ]
            }
        }
        
        # Define a basic prompt for implementing the changes
        prompt = """
        You are an expert resume writer implementing optimization recommendations.
        Apply ALL of the recommendations from the provided plan to the resume content.
        
        Important requirements:
        1. Make ONLY the changes specified in the recommendations
        2. Replace each "before_text" with its corresponding "after_text"
        3. Preserve all content that is not explicitly changed by a recommendation
        4. Maintain the overall structure and formatting of the resume
        5. Return the complete optimized resume in Markdown format
        6. NEVER remove any experience that is not explicitly part of a recommendation
        
        For each recommendation:
        - Locate the exact "before_text" in the resume
        - Replace it with the exact "after_text"
        - Ensure the replacement is done correctly
        
        Return ONLY the optimized resume with all recommendations applied.
        """
        
        try:
            # Create a temporary agent to implement the changes
            implementation_agent = ai_service.create_cover_letter_agent()  # Reuse this agent type
            
            # Build the agent message with the resume and plan
            message = f"""
            {prompt}
            
            # Original Resume
            
            {resume_content}
            
            # Recommendations to Apply
            
            {json.dumps(implementation_message["plan"], indent=2)}
            """
            
            # Run the agent to implement the changes
            optimized_content = await ai_service._run_agent(
                agent=implementation_agent,
                message=message
            )
            
            logfire.info(
                "Optimization plan implementation completed",
                original_length=len(resume_content),
                optimized_length=len(optimized_content)
            )
            
            return optimized_content
            
        except Exception as e:
            logfire.error(
                "Error implementing optimization plan",
                error=str(e),
                error_type=type(e).__name__
            )
            # In case of error, return the original content to avoid breaking the feedback loop
            return resume_content
    
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
def get_parallel_customization_service(db: Session = Depends(get_db)) -> ParallelCustomizationService:
    """
    Create a parallel customization service with all required dependencies.
    
    Args:
        db: Database session
        
    Returns:
        Initialized ParallelCustomizationService
    """
    return ParallelCustomizationService(db)