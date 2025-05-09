"""
Customization service implementing the evaluator-optimizer pattern for resume customization.

This service now integrates with specialized section analyzers for more detailed analysis.
"""
import uuid
import json
import time
import logfire
from typing import Optional, Dict, Any

from fastapi import Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.resume import Resume, ResumeVersion
from app.models.job import JobDescription

from app.schemas.customize import (
    CustomizationLevel, 
    CustomizationPlanRequest,
    CustomizationPlan
)

from app.core.logging import log_function_call
from app.services import pydanticai_service as ai_service
from app.services.prompts import MAX_FEEDBACK_ITERATIONS
from app.services.section_analysis_service import get_section_analysis_service, SectionAnalysisService
from app.services.section_analyzers.base import SectionType


class CustomizationService:
    """
    Service for resume customization using the evaluator-optimizer pattern.
    This implements a multi-stage AI workflow:
    1. Basic analysis (existing ATS analyzer)
    2. Specialized section analyzers (skills, experience, education, achievements, language)
    3. Evaluation (Claude acting as ATS expert)
    4. Optimization (Claude generating a detailed plan)
    """
    
    def __init__(self, db: Session):
        """
        Initialize the customization service with dependencies.
        
        Args:
            db: Database session
        """
        self.db = db
        self.section_analysis_service = get_section_analysis_service(db)
    
    @log_function_call
    async def generate_customization_plan(self, request: CustomizationPlanRequest) -> CustomizationPlan:
        """
        Generate a detailed customization plan for a resume based on a job description.
        This implements the evaluator-optimizer pattern with specialized section analyzers.
        
        Args:
            request: The customization plan request containing resume_id, job_description_id,
                    customization_strength, and optional ats_analysis
                    
        Returns:
            A CustomizationPlan with detailed recommendations
        """
        start_time = time.time()
        
        # Check if we should use the new section analyzers
        # This is controlled by a feature flag to allow gradual rollout
        use_section_analyzers = True
        
        if use_section_analyzers:
            # Use the new section analyzers approach
            logfire.info(
                "Using specialized section analyzers for customization plan",
                resume_id=request.resume_id,
                job_id=request.job_description_id,
                customization_level=request.customization_strength.name
            )
            
            # Generate plan using section analyzers
            plan = await self.section_analysis_service.generate_customization_plan(request)
            
            # Store the plan for future reference
            await self._store_plan(
                request.resume_id,
                request.job_description_id,
                plan
            )
            
            # Log completion with metrics
            elapsed_time = time.time() - start_time
            logfire.info(
                "Customization plan generation completed with section analyzers",
                resume_id=request.resume_id,
                job_id=request.job_description_id,
                duration_seconds=round(elapsed_time, 2),
                recommendations_count=len(plan.recommendations),
                keywords_added_count=len(plan.keywords_to_add),
                formatting_suggestions_count=len(plan.formatting_suggestions)
            )
            
            return plan
            
        else:
            # Use the original approach as fallback
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
            
            # Evaluate the match (evaluator stage)
            start_time_evaluator = time.time()
            logfire.info(
                "Starting evaluator stage with extended thinking",
                resume_id=request.resume_id,
                job_id=request.job_description_id,
                customization_level=request.customization_strength.name,
                industry=request.industry if request.industry else "not specified",
                using_extended_thinking=True
            )
            evaluation = await self._evaluate_match(
                resume_content, 
                job_description, 
                basic_analysis,
                request.customization_strength,
                request.industry
            )
            
            # Log evaluation results with metrics
            elapsed_time_evaluator = time.time() - start_time_evaluator
            logfire.info(
                "Evaluator stage completed",
                resume_id=request.resume_id,
                job_id=request.job_description_id,
                duration_seconds=round(elapsed_time_evaluator, 2),
                match_score=evaluation.get("match_score", 0),
                term_mismatches_count=len(evaluation.get("term_mismatches", [])),
                sections_evaluated=len(evaluation.get("section_evaluations", []))
            )
            
            # Generate the optimization plan (optimizer stage)
            start_time_optimizer = time.time()
            logfire.info(
                "Starting optimizer stage with extended thinking",
                resume_id=request.resume_id,
                job_id=request.job_description_id,
                customization_level=request.customization_strength.name,
                industry=request.industry if request.industry else "not specified",
                using_extended_thinking=True
            )
            plan = await self._generate_optimization_plan(
                resume_content, 
                job_description, 
                evaluation,
                request.customization_strength,
                request.industry
            )
            
            # Log optimizer results with metrics
            elapsed_time_optimizer = time.time() - start_time_optimizer
            logfire.info(
                "Optimizer stage completed",
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
    
    async def _evaluate_match(
        self, 
        resume_content: str, 
        job_description: str, 
        basic_analysis: Dict, 
        level: CustomizationLevel,
        industry: Optional[str] = None
    ) -> Dict:
        """
        Evaluate how well a resume matches a job description.
        This is the "evaluator" stage of the evaluator-optimizer pattern.
        
        Args:
            resume_content: Resume content in Markdown format
            job_description: Job description text
            basic_analysis: Results from basic keyword analysis
            level: Customization level (affects evaluation detail)
            industry: Optional industry name for industry-specific guidance
            
        Returns:
            Dictionary containing detailed evaluation
        """
        logfire.info(
            "Evaluating resume-job match",
            resume_length=len(resume_content),
            job_description_length=len(job_description),
            customization_level=level.name,
            industry=industry if industry else "not specified"
        )
        
        # Call OpenAI evaluator function
        return await ai_service.evaluate_resume_job_match(
            resume_content=resume_content,
            job_description=job_description,
            basic_analysis=basic_analysis,
            customization_level=level,
            industry=industry
        )
    
    async def _generate_optimization_plan(
        self, 
        resume_content: str, 
        job_description: str, 
        evaluation: Dict, 
        level: CustomizationLevel,
        industry: Optional[str] = None
    ) -> CustomizationPlan:
        """
        Generate an optimization plan based on the evaluation.
        This is the "optimizer" stage of the evaluator-optimizer pattern.
        
        Args:
            resume_content: Resume content in Markdown format
            job_description: Job description text
            evaluation: Evaluation dictionary from evaluator stage
            level: Customization level (affects optimization detail)
            industry: Optional industry name for industry-specific guidance
            
        Returns:
            CustomizationPlan with detailed recommendations
        """
        logfire.info(
            "Generating optimization plan",
            resume_length=len(resume_content),
            job_description_length=len(job_description),
            customization_level=level.name,
            industry=industry if industry else "not specified"
        )
        
        # Call OpenAI optimizer function
        return await ai_service.generate_optimization_plan(
            resume_content=resume_content,
            job_description=job_description,
            evaluation=evaluation,
            customization_level=level,
            industry=industry
        )
    
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
        # Since this is just for evaluation purposes in the feedback loop, we don't need to store versions
        
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
            user_id = resume.user_id if resume is not None else None
            
            # Convert recommendations to a list of dicts for JSON storage
            recommendations_json = []
            for rec in plan.recommendations:
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
def get_customization_service(db: Session = Depends(get_db)) -> CustomizationService:
    """
    Create a customization service with all required dependencies.
    
    Args:
        db: Database session
        
    Returns:
        Initialized CustomizationService
    """
    return CustomizationService(db)