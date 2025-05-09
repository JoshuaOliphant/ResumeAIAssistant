"""
Parallel Processing Architecture for Resume Customization.

This module implements a parallel processing architecture to improve the speed and 
efficiency of resume customization and analysis by:

1. Breaking resumes into logical sections for parallel processing
2. Managing concurrent AI model requests with a task scheduler
3. Implementing request batching and prioritization
4. Providing error recovery and fallback mechanisms
5. Combining results from parallel tasks

The architecture is designed to be model-agnostic and can be used with any AI provider
(Anthropic Claude, Google Gemini, OpenAI) supported by the application.
"""

import asyncio
import time
import uuid
import re
from typing import Dict, List, Any, Optional, Tuple, Callable, Union, Set
from enum import Enum
import logging
import logfire
from pydantic import BaseModel, Field
from app.core.config import settings
from app.schemas.customize import CustomizationLevel, CustomizationPlan, RecommendationItem

# Limit for concurrent tasks to prevent overloading
MAX_CONCURRENT_TASKS = settings.MAX_CONCURRENT_TASKS if hasattr(settings, 'MAX_CONCURRENT_TASKS') else 5

# Default section types for resume segmentation
class SectionType(str, Enum):
    """Resume section types for parallel processing."""
    SUMMARY = "summary"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    SKILLS = "skills"
    PROJECTS = "projects"
    CERTIFICATIONS = "certifications"
    OTHER = "other"
    
class TaskPriority(int, Enum):
    """Task priority levels for the scheduler."""
    CRITICAL = 1  # Highest priority tasks that block other processing
    HIGH = 2      # Important tasks that should be processed early
    MEDIUM = 3    # Standard tasks
    LOW = 4       # Background tasks that can wait
    
class TaskStatus(str, Enum):
    """Status of tasks in the scheduler."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ParallelTask(BaseModel):
    """Definition of a task for parallel processing."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    section_type: Optional[SectionType] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    func: Optional[Callable] = None
    args: List[Any] = []
    kwargs: Dict[str, Any] = {}
    result: Optional[Any] = None
    error: Optional[Exception] = None
    depends_on: List[str] = []  # List of task IDs this task depends on
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    
    class Config:
        arbitrary_types_allowed = True

class ParallelTaskScheduler:
    """
    Task scheduler for managing parallel model requests with priority queuing.
    
    This scheduler manages concurrent AI model requests, handles dependencies between tasks,
    and implements prioritization to ensure critical tasks are completed first.
    """
    
    def __init__(self, max_concurrent_tasks: int = MAX_CONCURRENT_TASKS):
        """
        Initialize the parallel task scheduler.
        
        Args:
            max_concurrent_tasks: Maximum number of tasks to run concurrently
        """
        self.tasks: Dict[str, ParallelTask] = {}
        self.max_concurrent_tasks = max_concurrent_tasks
        self.semaphore = asyncio.Semaphore(max_concurrent_tasks)
        self.running_tasks: Set[str] = set()
        self.completed_tasks: Set[str] = set()
        self.failed_tasks: Set[str] = set()
        
    def add_task(self, task: ParallelTask) -> str:
        """
        Add a task to the scheduler.
        
        Args:
            task: The parallel task to add
            
        Returns:
            The task ID
        """
        self.tasks[task.id] = task
        logfire.info(
            "Added task to scheduler",
            task_id=task.id,
            task_name=task.name, 
            priority=task.priority,
            depends_on=task.depends_on
        )
        return task.id
        
    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a pending task.
        
        Args:
            task_id: The ID of the task to cancel
            
        Returns:
            True if the task was cancelled, False otherwise
        """
        if task_id in self.tasks and self.tasks[task_id].status == TaskStatus.PENDING:
            self.tasks[task_id].status = TaskStatus.CANCELLED
            logfire.info("Task cancelled", task_id=task_id)
            return True
        return False
        
    def get_task(self, task_id: str) -> Optional[ParallelTask]:
        """
        Get a task by ID.
        
        Args:
            task_id: The ID of the task to get
            
        Returns:
            The task if found, None otherwise
        """
        return self.tasks.get(task_id)
        
    def get_ready_tasks(self) -> List[ParallelTask]:
        """
        Get tasks that are ready to run (pending and dependencies satisfied).
        
        Returns:
            List of tasks ready to run, sorted by priority
        """
        ready_tasks = []
        
        for task_id, task in self.tasks.items():
            if task.status != TaskStatus.PENDING:
                continue
                
            # Check if all dependencies are satisfied
            dependencies_met = True
            for dep_id in task.depends_on:
                if dep_id not in self.completed_tasks:
                    dependencies_met = False
                    break
                    
            if dependencies_met:
                ready_tasks.append(task)
                
        # Sort by priority (lower numeric value = higher priority)
        return sorted(ready_tasks, key=lambda t: t.priority)
        
    async def execute_task(self, task: ParallelTask) -> Any:
        """
        Execute a single task with error handling and retries.
        
        Args:
            task: The task to execute
            
        Returns:
            The result of the task
        """
        task.status = TaskStatus.RUNNING
        task.start_time = time.time()
        self.running_tasks.add(task.id)
        
        logfire.info(
            "Starting task execution",
            task_id=task.id,
            task_name=task.name
        )
        
        try:
            # Execute the task function with its arguments
            if task.func:
                result = await task.func(*task.args, **task.kwargs)
                task.result = result
                task.status = TaskStatus.COMPLETED
                task.end_time = time.time()
                self.completed_tasks.add(task.id)
                self.running_tasks.remove(task.id)
                
                duration = task.end_time - task.start_time
                logfire.info(
                    "Task completed successfully",
                    task_id=task.id,
                    task_name=task.name,
                    duration_seconds=round(duration, 2)
                )
                
                return result
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = e
            task.end_time = time.time()
            self.failed_tasks.add(task.id)
            self.running_tasks.remove(task.id)
            
            duration = task.end_time - task.start_time
            logfire.error(
                "Task execution failed",
                task_id=task.id,
                task_name=task.name,
                error=str(e),
                error_type=type(e).__name__,
                duration_seconds=round(duration, 2)
            )
            
            # Re-raise to allow for custom error handling by caller
            raise e
            
    async def run_task_with_semaphore(self, task: ParallelTask) -> Any:
        """
        Run a task with the concurrency semaphore.
        
        Args:
            task: The task to run
            
        Returns:
            The result of the task
        """
        async with self.semaphore:
            return await self.execute_task(task)
            
    async def execute_all(self) -> Dict[str, Any]:
        """
        Execute all pending tasks respecting dependencies and concurrency limits.
        
        Returns:
            Dictionary mapping task IDs to results
        """
        start_time = time.time()
        logfire.info("Starting execution of all tasks")
        
        results = {}
        pending_tasks = {task_id for task_id, task in self.tasks.items() 
                         if task.status == TaskStatus.PENDING}
        
        while pending_tasks:
            # Get tasks that are ready to run
            ready_tasks = self.get_ready_tasks()
            
            if not ready_tasks:
                # If no tasks are ready but we have pending tasks, 
                # we might have a dependency cycle
                if self.running_tasks:
                    # Wait for some running tasks to complete
                    await asyncio.sleep(0.1)
                    continue
                else:
                    # We have a dependency cycle or all remaining tasks have failed dependencies
                    logfire.info(
                        "Dependency issue detected - remaining tasks cannot be run",
                        pending_tasks=list(pending_tasks),
                        level="warning"
                    )
                    break
            
            # Start as many ready tasks as allowed by concurrency limit
            available_slots = self.max_concurrent_tasks - len(self.running_tasks)
            tasks_to_start = ready_tasks[:available_slots]
            
            if tasks_to_start:
                # Create task coroutines
                coros = [self.run_task_with_semaphore(task) for task in tasks_to_start]
                
                # Start tasks and continue - don't wait for completion
                for coro in coros:
                    asyncio.create_task(coro)
                    
                # Give the tasks a chance to start and update their status
                await asyncio.sleep(0.01)
                
                # Update pending tasks
                pending_tasks = {task_id for task_id, task in self.tasks.items() 
                                if task.status == TaskStatus.PENDING}
            else:
                # Wait for some running tasks to complete before checking again
                await asyncio.sleep(0.1)
                
                # Update pending tasks after wait
                pending_tasks = {task_id for task_id, task in self.tasks.items() 
                                if task.status == TaskStatus.PENDING}
        
        # Wait for all running tasks to complete
        while self.running_tasks:
            await asyncio.sleep(0.1)
            
        # Collect results
        for task_id, task in self.tasks.items():
            if task.status == TaskStatus.COMPLETED:
                results[task_id] = task.result
                
        duration = time.time() - start_time
        logfire.info(
            "All tasks execution completed",
            completed_count=len(self.completed_tasks),
            failed_count=len(self.failed_tasks),
            total_duration_seconds=round(duration, 2)
        )
        
        return results

class ResumeSegmenter:
    """
    Utility for splitting resumes into logical sections for parallel processing.
    
    This class detects and splits resume content into sections that can be
    processed independently in parallel.
    """
    
    # Common section headers for detection
    SECTION_PATTERNS = {
        SectionType.SUMMARY: [
            "professional summary", "summary", "executive summary", "career summary", 
            "profile summary", "professional profile", "career objective", "objective",
            "about me", "profile", "career profile", "summary of qualifications"
        ],
        SectionType.EXPERIENCE: [
            "experience", "work experience", "professional experience", "employment",
            "employment history", "work history", "career history", "job history",
            "professional background", "career accomplishments", "professional activities"
        ],
        SectionType.EDUCATION: [
            "education", "educational background", "academic background", "academic history",
            "qualifications", "academic qualifications", "educational qualifications",
            "training", "academic training", "certifications & education", "degrees"
        ],
        SectionType.SKILLS: [
            "skills", "technical skills", "core skills", "key skills", "professional skills",
            "competencies", "core competencies", "skill set", "expertise", "areas of expertise",
            "core capabilities", "strengths", "key strengths", "technical competencies"
        ],
        SectionType.PROJECTS: [
            "projects", "project experience", "key projects", "professional projects",
            "research projects", "major projects", "notable projects", "project portfolio"
        ],
        SectionType.CERTIFICATIONS: [
            "certifications", "professional certifications", "licenses", "licensure",
            "credentials", "accreditations", "professional licenses"
        ]
    }
    
    @staticmethod
    def identify_sections(resume_content: str) -> Dict[SectionType, str]:
        """
        Identify and extract sections from a resume.
        
        Args:
            resume_content: The full resume content
            
        Returns:
            Dictionary mapping section types to their content
        """
        sections = {}
        lines = resume_content.split('\n')
        current_section = SectionType.OTHER
        section_content = []
        
        # Process each line to identify section headers and content
        for i, line in enumerate(lines):
            line_lower = line.strip().lower()
            
            # Check if line is a section header
            found_section = False
            for section_type, patterns in ResumeSegmenter.SECTION_PATTERNS.items():
                # Exact match for section name
                if line_lower in patterns:
                    # Save previous section content
                    if section_content:
                        sections[current_section] = '\n'.join(section_content)
                    
                    # Start new section
                    current_section = section_type
                    section_content = []
                    found_section = True
                    break
                
                # Check for headers with markdown styling (##, ###, etc.)
                elif line_lower.startswith('#'):
                    header_text = re.sub(r'^#+\s*', '', line_lower).strip()
                    if header_text in patterns or any(pattern in header_text for pattern in patterns):
                        # Save previous section content
                        if section_content:
                            sections[current_section] = '\n'.join(section_content)
                        
                        # Start new section
                        current_section = section_type
                        section_content = []
                        found_section = True
                        break
                        
                # Check for other header patterns
                elif any(pattern in line_lower for pattern in patterns):
                    # Some headers might be like "Work Experience:" or "EDUCATION"
                    if (re.match(r'.*:\s*$', line_lower) or 
                        line.isupper() or 
                        re.match(r'\*\*.*\*\*', line)): # Check for **bold** headers
                        
                        # Save previous section content
                        if section_content:
                            sections[current_section] = '\n'.join(section_content)
                        
                        # Start new section
                        current_section = section_type
                        section_content = []
                        found_section = True
                        break
            
            # If not a section header, add to current section content
            if not found_section:
                section_content.append(line)
                
                # If first line and not a header, likely part of summary
                if i == 0 and current_section == SectionType.OTHER:
                    current_section = SectionType.SUMMARY
        
        # Add the final section content
        if section_content:
            sections[current_section] = '\n'.join(section_content)
            
        # Ensure we have a valid OTHER section if nothing else was identified
        if not sections and resume_content:
            sections[SectionType.OTHER] = resume_content
            
        logfire.info(
            "Resume sections identified",
            section_count=len(sections),
            identified_sections=list(sections.keys())
        )
            
        return sections
    
    @staticmethod
    def reassemble_resume(sections: Dict[SectionType, str]) -> str:
        """
        Reassemble a complete resume from processed sections.
        
        Args:
            sections: Dictionary mapping section types to their content
            
        Returns:
            Reassembled resume content
        """
        # Define the preferred order of sections
        section_order = [
            SectionType.SUMMARY,
            SectionType.EXPERIENCE,
            SectionType.EDUCATION,
            SectionType.SKILLS,
            SectionType.PROJECTS,
            SectionType.CERTIFICATIONS,
            SectionType.OTHER
        ]
        
        # Build the resume in the preferred order
        resume_parts = []
        for section_type in section_order:
            if section_type in sections and sections[section_type]:
                resume_parts.append(sections[section_type])
                
        return '\n\n'.join(resume_parts)

class ResultsAggregator:
    """
    Utility for aggregating results from parallel tasks.
    
    This class combines results from multiple parallel tasks into coherent
    output structures for resume analysis and optimization.
    """
    
    @staticmethod
    async def aggregate_section_analyses(
        section_results: Dict[SectionType, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Aggregate analysis results from multiple resume sections.
        
        Args:
            section_results: Dictionary mapping section types to their analysis results
            
        Returns:
            Consolidated analysis result
        """
        # Start with an empty aggregated result
        aggregated = {
            "match_score": 0,
            "matching_keywords": [],
            "missing_keywords": [],
            "improvements": [],
            "section_scores": [],
            "section_evaluations": []
        }
        
        # Track keywords to avoid duplicates
        matching_keywords_set = set()
        missing_keywords_set = set()
        
        # Add all sections' matching keywords while avoiding duplicates
        for section_type, result in section_results.items():
            # Add matching keywords if they don't already exist
            if "matching_keywords" in result:
                for keyword_match in result["matching_keywords"]:
                    keyword = keyword_match.get("keyword", "")
                    if keyword and keyword not in matching_keywords_set:
                        matching_keywords_set.add(keyword)
                        aggregated["matching_keywords"].append(keyword_match)
            
            # Add missing keywords if they don't already exist
            if "missing_keywords" in result:
                for keyword_match in result["missing_keywords"]:
                    keyword = keyword_match.get("keyword", "")
                    if keyword and keyword not in missing_keywords_set and keyword not in matching_keywords_set:
                        missing_keywords_set.add(keyword)
                        aggregated["missing_keywords"].append(keyword_match)
            
            # Add section-specific improvements
            if "improvements" in result:
                aggregated["improvements"].extend(result["improvements"])
            
            # Add section scores
            if "section_scores" in result:
                aggregated["section_scores"].extend(result["section_scores"])
                
            # Add section evaluations
            if "section_evaluations" in result:
                aggregated["section_evaluations"].append({
                    "section": section_type,
                    "evaluation": result["section_evaluations"]
                })
        
        # Calculate overall match score as weighted average of section scores
        section_weights = {
            SectionType.SUMMARY: 0.7,
            SectionType.EXPERIENCE: 1.5,
            SectionType.EDUCATION: 0.8,
            SectionType.SKILLS: 1.8,
            SectionType.PROJECTS: 1.0,
            SectionType.CERTIFICATIONS: 0.9,
            SectionType.OTHER: 0.5
        }
        
        total_weight = 0
        weighted_score_sum = 0
        
        for section_type, result in section_results.items():
            if "match_score" in result:
                weight = section_weights.get(section_type, 1.0)
                weighted_score_sum += result["match_score"] * weight
                total_weight += weight
        
        if total_weight > 0:
            aggregated["match_score"] = round(weighted_score_sum / total_weight)
        else:
            # Default if no match scores available
            aggregated["match_score"] = 50
        
        # Sort improvements by priority (if available)
        if aggregated["improvements"]:
            aggregated["improvements"] = sorted(
                aggregated["improvements"], 
                key=lambda x: x.get("priority", 999)
            )
            # Limit to top 5 improvements to avoid overwhelming the user
            aggregated["improvements"] = aggregated["improvements"][:5]
        
        return aggregated
    
    @staticmethod
    async def aggregate_optimization_plans(
        section_plans: Dict[SectionType, Dict[str, Any]]
    ) -> CustomizationPlan:
        """
        Aggregate optimization plans from multiple resume sections.
        
        Args:
            section_plans: Dictionary mapping section types to their optimization plans
            
        Returns:
            Consolidated CustomizationPlan
        """
        # Start with base structure for the plan
        aggregated_plan = CustomizationPlan(
            summary="",
            job_analysis="",
            recommendations=[],
            keywords_to_add=[],
            formatting_suggestions=[]
        )
        
        # Collect summaries to combine later
        summaries = []
        job_analyses = []
        
        # Process each section's plan
        for section_type, plan in section_plans.items():
            # Add summary and job analysis for later combination
            if "summary" in plan and plan["summary"]:
                summaries.append(f"{section_type.capitalize()}: {plan['summary']}")
            
            if "job_analysis" in plan and plan["job_analysis"]:
                job_analyses.append(plan["job_analysis"])
            
            # Add section-specific recommendations
            if "recommendations" in plan:
                for rec in plan["recommendations"]:
                    # Add section type if not already in the recommendation
                    if isinstance(rec, dict) and "section" not in rec:
                        rec["section"] = section_type.value
                    aggregated_plan.recommendations.append(rec)
            
            # Add keywords
            if "keywords_to_add" in plan:
                aggregated_plan.keywords_to_add.extend(plan["keywords_to_add"])
            
            # Add formatting suggestions
            if "formatting_suggestions" in plan:
                aggregated_plan.formatting_suggestions.extend(plan["formatting_suggestions"])
        
        # Combine summaries into an overall summary
        if summaries:
            aggregated_plan.summary = "\n".join(summaries)
        
        # Use the most comprehensive job analysis if available
        if job_analyses:
            # Select the longest job analysis as it's likely the most comprehensive
            aggregated_plan.job_analysis = max(job_analyses, key=len)
        
        # Remove duplicate keywords
        if aggregated_plan.keywords_to_add:
            aggregated_plan.keywords_to_add = list(set(aggregated_plan.keywords_to_add))
        
        # Remove duplicate formatting suggestions
        if aggregated_plan.formatting_suggestions:
            unique_suggestions = {}
            for suggestion in aggregated_plan.formatting_suggestions:
                if isinstance(suggestion, dict) and "suggestion" in suggestion:
                    unique_suggestions[suggestion["suggestion"]] = suggestion
                else:
                    unique_suggestions[str(suggestion)] = suggestion
            aggregated_plan.formatting_suggestions = list(unique_suggestions.values())
        
        return aggregated_plan

class ParallelProcessor:
    """
    Main entry point for the parallel processing architecture.
    
    This class manages the high-level parallel processing workflow for resume
    customization and provides easy-to-use interfaces for the rest of the application.
    """
    
    def __init__(self):
        """Initialize the parallel processor."""
        self.scheduler = ParallelTaskScheduler()
        self.segmenter = ResumeSegmenter
        self.aggregator = ResultsAggregator
    
    async def process_resume_analysis(
        self, 
        resume_content: str, 
        job_description: str,
        section_analysis_func: Callable,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Process resume analysis in parallel across sections.
        
        Args:
            resume_content: The full resume content
            job_description: The job description text
            section_analysis_func: Function to analyze each section
            **kwargs: Additional arguments to pass to the analysis function
            
        Returns:
            Aggregated analysis results
        """
        start_time = time.time()
        logfire.info(
            "Starting parallel resume analysis",
            resume_length=len(resume_content),
            job_description_length=len(job_description)
        )
        
        # Identify sections in the resume
        sections = self.segmenter.identify_sections(resume_content)
        
        # Clear existing tasks and prepare new ones
        self.scheduler = ParallelTaskScheduler()
        section_tasks = {}
        
        # Create analysis tasks for each section
        for section_type, section_content in sections.items():
            task = ParallelTask(
                name=f"analyze_{section_type}",
                section_type=section_type,
                priority=TaskPriority.MEDIUM,
                func=section_analysis_func,
                args=[section_content, job_description],
                kwargs=kwargs
            )
            
            # Prioritize important sections like experience and skills
            if section_type == SectionType.EXPERIENCE or section_type == SectionType.SKILLS:
                task.priority = TaskPriority.HIGH
            
            task_id = self.scheduler.add_task(task)
            section_tasks[section_type] = task_id
        
        # Execute all tasks and wait for completion
        results = await self.scheduler.execute_all()
        
        # Map results back to section types
        section_results = {
            section_type: results[task_id] 
            for section_type, task_id in section_tasks.items()
            if task_id in results
        }
        
        # Aggregate results from all sections
        aggregated_results = await self.aggregator.aggregate_section_analyses(section_results)
        
        duration = time.time() - start_time
        logfire.info(
            "Parallel resume analysis completed",
            duration_seconds=round(duration, 2),
            processed_sections=len(section_results),
            match_score=aggregated_results.get("match_score", 0)
        )
        
        return aggregated_results
    
    async def process_optimization_plan(
        self,
        resume_content: str,
        job_description: str,
        evaluation: Dict[str, Any],
        section_optimization_func: Callable,
        **kwargs
    ) -> CustomizationPlan:
        """
        Process optimization plan generation in parallel across sections.
        
        Args:
            resume_content: The full resume content
            job_description: The job description text
            evaluation: Evaluation dictionary from the evaluation stage
            section_optimization_func: Function to generate optimization plan for each section
            **kwargs: Additional arguments to pass to the optimization function
            
        Returns:
            Aggregated CustomizationPlan
        """
        start_time = time.time()
        logfire.info(
            "Starting parallel optimization plan generation",
            resume_length=len(resume_content),
            job_description_length=len(job_description)
        )
        
        # Identify sections in the resume
        sections = self.segmenter.identify_sections(resume_content)
        
        # Extract section evaluations from the evaluation if available
        section_evaluations = {}
        if "section_evaluations" in evaluation:
            for section_eval in evaluation["section_evaluations"]:
                section_name = section_eval.get("section", "").lower()
                for section_type in SectionType:
                    if section_name == section_type.value or section_name in self.segmenter.SECTION_PATTERNS.get(section_type, []):
                        section_evaluations[section_type] = section_eval
                        break
        
        # Clear existing tasks and prepare new ones
        self.scheduler = ParallelTaskScheduler()
        section_tasks = {}
        
        # Create optimization tasks for each section
        for section_type, section_content in sections.items():
            # Get section-specific evaluation if available
            section_eval = section_evaluations.get(section_type, {})
            
            task = ParallelTask(
                name=f"optimize_{section_type}",
                section_type=section_type,
                priority=TaskPriority.MEDIUM,
                func=section_optimization_func,
                args=[section_content, job_description, section_eval],
                kwargs=kwargs
            )
            
            # Prioritize important sections like experience and skills
            if section_type == SectionType.EXPERIENCE or section_type == SectionType.SKILLS:
                task.priority = TaskPriority.HIGH
            
            task_id = self.scheduler.add_task(task)
            section_tasks[section_type] = task_id
        
        # Execute all tasks and wait for completion
        results = await self.scheduler.execute_all()
        
        # Map results back to section types
        section_results = {
            section_type: results[task_id] 
            for section_type, task_id in section_tasks.items()
            if task_id in results
        }
        
        # Aggregate optimization plans from all sections
        aggregated_plan = await self.aggregator.aggregate_optimization_plans(section_results)
        
        duration = time.time() - start_time
        logfire.info(
            "Parallel optimization plan generation completed",
            duration_seconds=round(duration, 2),
            processed_sections=len(section_results),
            recommendation_count=len(aggregated_plan.recommendations)
        )
        
        return aggregated_plan
    
    @staticmethod
    async def run_with_fallback(
        primary_func: Callable,
        fallback_func: Callable,
        args: List[Any] = None,
        kwargs: Dict[str, Any] = None,
        max_retries: int = 2
    ) -> Any:
        """
        Run a function with error recovery and fallback mechanisms.
        
        Args:
            primary_func: The primary function to run
            fallback_func: The fallback function to run if primary fails
            args: Arguments to pass to the functions
            kwargs: Keyword arguments to pass to the functions
            max_retries: Maximum number of retries for the primary function
            
        Returns:
            Result from primary or fallback function
        """
        args = args or []
        kwargs = kwargs or {}
        retries = 0
        
        while retries <= max_retries:
            try:
                if retries == 0:
                    # First attempt with primary function
                    return await primary_func(*args, **kwargs)
                else:
                    # Retry with exponential backoff
                    await asyncio.sleep(0.5 * (2 ** (retries - 1)))
                    return await primary_func(*args, **kwargs)
            except Exception as e:
                retries += 1
                logfire.info(
                    f"Function failed (attempt {retries}), {'retrying' if retries <= max_retries else 'using fallback'}",
                    function=primary_func.__name__,
                    error=str(e),
                    error_type=type(e).__name__,
                    level="warning"
                )
                
                if retries > max_retries:
                    # All retries failed, use fallback
                    try:
                        return await fallback_func(*args, **kwargs)
                    except Exception as fallback_error:
                        # Both primary and fallback failed
                        logfire.error(
                            "Both primary and fallback functions failed",
                            primary_function=primary_func.__name__,
                            fallback_function=fallback_func.__name__,
                            fallback_error=str(fallback_error),
                            fallback_error_type=type(fallback_error).__name__
                        )
                        # Re-raise the fallback error
                        raise fallback_error