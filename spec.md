# Resume Customization Service Redesign Specification

## Overview

This specification outlines a redesign of the resume customization service to improve reliability, performance, and user experience. The main goal is to break down the current monolithic architecture into a series of smaller, more focused steps that can handle API timeouts and failures gracefully.

The redesign follows principles from the [Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents) article, including workflow decomposition, modular design, and validation gates.

## Current Issues

1. API calls to external AI services (especially Gemini) can time out or hang
2. Large model requests with extensive context can lead to poor performance
3. No graceful fallback when one step of the process fails
4. Limited visibility into process progress for users

## High-Level Architecture

We'll transform the current workflow:

```
Original Flow: 
Job Description + Resume → [Single Large API Call] → Customized Resume

Improved Flow: 
Job Description + Resume → 
  1. Extract Key Requirements (small API call)
  2. Analyze Resume Sections (sequential small API calls)
  3. Generate Improvement Plan (small API call)
  4. Implement Changes Per Section (sequential small API calls)
  5. Validate & Refine Changes (small API call)
  → Customized Resume
```

## Work Breakdown Structure

The following issues can be worked on individually by different developers or AI agents with minimal overlap.

---

### Issue 1: Micro-Task Orchestration Framework

**Priority:** High  
**Dependencies:** None

**Description:**  
Implement a framework for orchestrating small, focused AI tasks executed sequentially with proper error handling and recovery.

**Tasks:**
1. Create a MicroTask base class with common properties and methods
2. Implement TaskOrchestrator to manage task execution
3. Add state management for task progress and results
4. Implement timeout handling and retry logic
5. Create visualization/reporting for task progress

**Code Outline:**
```python
class MicroTask:
    """Base class for all micro-tasks in the resume customization workflow."""
    
    def __init__(self, name, timeout_seconds=45):
        self.name = name
        self.timeout_seconds = timeout_seconds
        self.status = TaskStatus.PENDING
        self.result = None
        self.start_time = None
        self.end_time = None
        self.error = None
        
    async def execute(self, **kwargs):
        """Execute the task with timeout handling."""
        try:
            self.start_time = time.time()
            self.status = TaskStatus.RUNNING
            
            # Use asyncio.wait_for to add timeout handling
            result = await asyncio.wait_for(
                self._execute(**kwargs),
                timeout=self.timeout_seconds
            )
            
            self.result = result
            self.status = TaskStatus.COMPLETED
            self.end_time = time.time()
            return result
        except asyncio.TimeoutError:
            self.status = TaskStatus.FAILED
            self.end_time = time.time()
            self.error = f"Task timed out after {self.timeout_seconds} seconds"
            raise TimeoutException(f"Task {self.name} timed out")
        except Exception as e:
            self.status = TaskStatus.FAILED
            self.end_time = time.time()
            self.error = str(e)
            raise
    
    async def _execute(self, **kwargs):
        """Override this method in subclasses."""
        raise NotImplementedError()


class TaskOrchestrator:
    """Manages the execution of micro-tasks with dependency tracking."""
    
    def __init__(self, max_concurrent_tasks=5):
        self.tasks = {}
        self.max_concurrent_tasks = max_concurrent_tasks
        self.semaphore = asyncio.Semaphore(max_concurrent_tasks)
        
    def add_task(self, task, dependencies=None):
        """Add a task with optional dependencies."""
        self.tasks[task.name] = {
            "task": task,
            "dependencies": dependencies or []
        }
        
    async def execute_all(self):
        """Execute all tasks respecting dependencies."""
        results = {}
        pending_tasks = set(self.tasks.keys())
        
        while pending_tasks:
            # Get runnable tasks (dependencies satisfied)
            runnable_tasks = [
                name for name in pending_tasks
                if all(dep in results for dep in self.tasks[name]["dependencies"])
            ]
            
            if not runnable_tasks:
                if not any(self.tasks[name]["task"].status == TaskStatus.RUNNING 
                           for name in self.tasks):
                    # No tasks are running and none can be started - dependency issue
                    raise DependencyException("Cannot resolve task dependencies")
                    
                # Wait for some tasks to complete
                await asyncio.sleep(0.1)
                continue
                
            # Create execution coroutines
            coros = []
            for name in runnable_tasks[:self.max_concurrent_tasks]:
                task_info = self.tasks[name]
                task = task_info["task"]
                
                # Gather inputs from dependencies
                inputs = {dep: results[dep] for dep in task_info["dependencies"]}
                
                # Create coroutine
                coros.append(self._execute_task_with_semaphore(task, **inputs))
                pending_tasks.remove(name)
                
            # Execute tasks sequentially
            for coro in coros:
                await coro
                
        # Wait for all tasks to complete
        all_completed = False
        while not all_completed:
            all_completed = all(
                self.tasks[name]["task"].status in (TaskStatus.COMPLETED, TaskStatus.FAILED)
                for name in self.tasks
            )
            if not all_completed:
                await asyncio.sleep(0.1)
                
        # Collect results
        for name, task_info in self.tasks.items():
            if task_info["task"].status == TaskStatus.COMPLETED:
                results[name] = task_info["task"].result
                
        return results
        
    async def _execute_task_with_semaphore(self, task, **kwargs):
        """Execute a task with the concurrency semaphore."""
        async with self.semaphore:
            try:
                result = await task.execute(**kwargs)
                return result
            except Exception as e:
                # Log but don't re-raise, let the task handle its error state
                logfire.error(f"Task {task.name} failed: {str(e)}")
                return None
```

---

### Issue 2: Resume Section Analyzer Framework

**Priority:** High  
**Dependencies:** None

**Description:**  
Create a framework for section-specific analysis and customization of resumes.

**Tasks:**
1. Implement base classes for section analyzers
2. Create specialized analyzers for key resume sections (Experience, Skills, Summary, Education)
3. Implement section extraction and reassembly logic
4. Add validator functions to ensure section quality

**Code Outline:**
```python
class SectionAnalyzer(MicroTask):
    """Base class for resume section analyzers."""
    
    def __init__(self, section_type, section_content, timeout_seconds=45):
        super().__init__(f"analyze_{section_type}", timeout_seconds)
        self.section_type = section_type
        self.section_content = section_content
        
    async def _execute(self, job_description, **kwargs):
        """Analyze a resume section against job requirements."""
        # Implement in subclasses
        raise NotImplementedError()


class ExperienceAnalyzer(SectionAnalyzer):
    """Specialized analyzer for experience sections."""
    
    def __init__(self, section_content, timeout_seconds=45):
        super().__init__("experience", section_content, timeout_seconds)
        
    async def _execute(self, job_description, **kwargs):
        """Analyze experience section against job requirements."""
        # Prepare prompt for the AI model
        prompt = f"""
        Analyze this experience section for relevance to the job description:
        
        Experience section:
        {self.section_content}
        
        Job description:
        {job_description}
        
        Provide analysis of:
        1. Relevance of experience to job requirements
        2. Notable achievements that match job needs
        3. Experience gaps compared to requirements
        4. Terminology that should be aligned with job description
        """
        
        # Use a smaller, faster model for this focused task
        agent = Agent(
            "google:gemini-flash",  # Use smaller model for focused task
            output_format="json",
            system_prompt=prompt,
            timeout=self.timeout_seconds - 1
        )
        
        try:
            # Execute with explicit timeout
            result = await asyncio.wait_for(
                agent.run("Analyze the experience section"),
                timeout=self.timeout_seconds - 1
            )
            return result
        except Exception as e:
            # Try with fallback model if primary fails
            try:
                agent = Agent(
                    "anthropic:claude-3-haiku",  # Fallback to different provider
                    output_format="json",
                    system_prompt=prompt,
                    timeout=self.timeout_seconds - 1
                )
                return await agent.run("Analyze the experience section")
            except Exception as fallback_error:
                # Both attempts failed
                raise AnalysisException(f"Could not analyze experience section: {str(e)}, fallback error: {str(fallback_error)}")


class SkillsAnalyzer(SectionAnalyzer):
    """Specialized analyzer for skills sections."""
    
    def __init__(self, section_content, timeout_seconds=45):
        super().__init__("skills", section_content, timeout_seconds)
        
    async def _execute(self, job_description, **kwargs):
        """Analyze skills section against job requirements."""
        # Similar implementation to ExperienceAnalyzer but focused on skills
        # ...
```

---

### Issue 3: Key Requirements Extractor

**Priority:** High  
**Dependencies:** None

**Description:**  
Create a service to extract key requirements from job descriptions to reduce context size for subsequent steps.

**Tasks:**
1. Implement a focused extraction service that identifies essential requirements
2. Create a categorization system for requirements (skills, experience, education, etc.)
3. Add keyword extraction for ATS matching
4. Implement priority ranking of requirements

**Code Outline:**
```python
class RequirementsExtractor(MicroTask):
    """Extracts key requirements from job descriptions."""
    
    def __init__(self, timeout_seconds=30):
        super().__init__("extract_requirements", timeout_seconds)
        
    async def _execute(self, job_description, **kwargs):
        """Extract key requirements from a job description."""
        prompt = f"""
        Extract the key requirements from this job description:
        
        {job_description}
        
        Break them down into these categories:
        1. Required technical skills
        2. Required soft skills
        3. Experience requirements (years and type)
        4. Education requirements
        5. Industry knowledge/domain expertise
        6. Key responsibilities
        
        For each requirement, include:
        - The exact text from the job description
        - The priority level (critical, important, nice-to-have)
        - Suggested keywords/terms to include in the resume
        
        Format your response as structured JSON.
        """
        
        # Use a smaller model for this focused task
        try:
            agent = Agent(
                "anthropic:claude-3-haiku",  # Small, fast model for extraction
                output_format="json",
                system_prompt=prompt,
                timeout=self.timeout_seconds - 1
            )
            
            result = await asyncio.wait_for(
                agent.run("Extract key requirements from the job description"),
                timeout=self.timeout_seconds - 1
            )
            
            # Validate the extraction has the expected structure
            self._validate_extraction(result)
            
            return result
        except Exception as e:
            # Try with fallback model
            try:
                agent = Agent(
                    "google:gemini-flash",  # Fallback to different provider
                    output_format="json",
                    system_prompt=prompt,
                    timeout=self.timeout_seconds - 1
                )
                result = await agent.run("Extract key requirements from the job description")
                self._validate_extraction(result)
                return result
            except Exception as fallback_error:
                raise ExtractionException(f"Failed to extract requirements: {str(e)}, fallback error: {str(fallback_error)}")
                
    def _validate_extraction(self, extraction):
        """Validate the extraction has expected structure."""
        required_categories = [
            "required_technical_skills",
            "required_soft_skills",
            "experience_requirements",
            "education_requirements"
        ]
        
        for category in required_categories:
            if category not in extraction or not extraction[category]:
                logfire.warning(f"Requirements extraction missing category: {category}")
                # Initialize with empty array if missing
                extraction[category] = []
```

---

### Issue 4: Improvement Plan Generator

**Priority:** High  
**Dependencies:** Issue 2, Issue 3

**Description:**  
Create a service to generate a customization plan based on section analyses and key requirements.

**Tasks:**
1. Implement a plan generator that consolidates section analyses
2. Create a prioritization system for improvements
3. Add validation for plan quality and completeness
4. Implement fallback plans for partial failures

**Code Outline:**
```python
class ImprovementPlanGenerator(MicroTask):
    """Generates an improvement plan based on section analyses."""
    
    def __init__(self, timeout_seconds=45):
        super().__init__("generate_plan", timeout_seconds)
        
    async def _execute(self, section_analyses, key_requirements, customization_level, **kwargs):
        """Generate an improvement plan from analyses."""
        # Consolidate the section analyses
        consolidated_analysis = self._consolidate_analyses(section_analyses)
        
        # Prioritize requirements based on customization level
        prioritized_requirements = self._prioritize_requirements(
            key_requirements, 
            customization_level
        )
        
        # Create the optimization prompt
        prompt = f"""
        Generate a detailed resume customization plan based on these analyses:
        
        {json.dumps(consolidated_analysis, indent=2)}
        
        Prioritize these key requirements:
        
        {json.dumps(prioritized_requirements, indent=2)}
        
        Customization level: {customization_level.value}
        
        Your plan should include:
        1. A summary of recommended changes
        2. Section-by-section recommendations with specific text changes
        3. Keywords to add or emphasize
        4. Formatting or structural suggestions
        
        For each recommendation, include:
        - The section it applies to
        - What specific change to make
        - Why this change helps match the job requirements
        - Before/after text examples when appropriate
        
        Format your response as structured JSON matching the CustomizationPlan schema.
        """
        
        # Use an appropriate model for this higher-complexity task
        try:
            # Choose model based on customization level complexity
            model = self._select_model_for_customization_level(customization_level)
            
            agent = Agent(
                model,
                output_type=CustomizationPlan,
                system_prompt=prompt,
                timeout=self.timeout_seconds - 1
            )
            
            result = await asyncio.wait_for(
                agent.run("Generate an improvement plan based on the analyses"),
                timeout=self.timeout_seconds - 1
            )
            
            # Validate the plan
            self._validate_plan(result)
            
            return result
        except Exception as e:
            # Generate a fallback plan
            logfire.error(f"Error generating improvement plan: {str(e)}")
            return self._generate_fallback_plan(section_analyses, key_requirements)
            
    def _consolidate_analyses(self, section_analyses):
        """Consolidate analyses from different sections."""
        return {
            "summary": self._extract_summary_from_analyses(section_analyses),
            "section_specific_findings": section_analyses,
            "overall_assessment": self._calculate_overall_assessment(section_analyses)
        }
        
    def _prioritize_requirements(self, requirements, customization_level):
        """Prioritize requirements based on customization level."""
        # Implement prioritization logic based on customization level
        # ...
        
    def _select_model_for_customization_level(self, customization_level):
        """Select appropriate model based on customization level."""
        if customization_level == CustomizationLevel.EXTENSIVE:
            return "google:gemini-2.5-pro"  # More capable for complex customization
        else:
            return "google:gemini-1.5-flash"  # Faster for simpler customization
            
    def _validate_plan(self, plan):
        """Validate the generated plan."""
        # Ensure plan has required elements
        if not plan.recommendations or len(plan.recommendations) == 0:
            raise ValidationException("Plan has no recommendations")
            
        # Check for other quality issues
        # ...
        
    def _generate_fallback_plan(self, section_analyses, key_requirements):
        """Generate a basic fallback plan if the main plan fails."""
        # Create a minimal viable plan when the full generation fails
        # ...
```

---

### Issue 5: Section-Based Customization Implementer

**Priority:** High  
**Dependencies:** Issue 4

**Description:**  
Create a service to implement customization changes section by section based on the improvement plan.

**Tasks:**
1. Implement a text manipulation service for section-based changes
2. Create validation for each section's changes
3. Add rollback capability for failed changes
4. Implement section reassembly logic

**Code Outline:**
```python
class SectionCustomizer(MicroTask):
    """Customizes a specific resume section based on improvement plan."""
    
    def __init__(self, section_type, section_content, timeout_seconds=45):
        super().__init__(f"customize_{section_type}", timeout_seconds)
        self.section_type = section_type
        self.section_content = section_content
        
    async def _execute(self, improvement_plan, key_requirements, **kwargs):
        """Customize a resume section based on the improvement plan."""
        # Extract recommendations for this section
        section_recommendations = [
            rec for rec in improvement_plan.recommendations 
            if rec.section.lower() == self.section_type.lower()
        ]
        
        if not section_recommendations:
            # No changes for this section
            return {
                "customized_content": self.section_content,
                "changes_made": [],
                "original_content": self.section_content
            }
            
        # Prepare customization prompt
        prompt = f"""
        Customize this resume section based on these recommendations:
        
        Section content:
        {self.section_content}
        
        Recommendations:
        {json.dumps([rec.dict() for rec in section_recommendations], indent=2)}
        
        Key requirements to emphasize:
        {json.dumps(key_requirements, indent=2)}
        
        Make ONLY the changes specified in the recommendations.
        Return the customized section and a list of changes made.
        Ensure all formatting and structure is preserved.
        """
        
        # Use a reliable model for text generation
        try:
            agent = Agent(
                "anthropic:claude-3-haiku",  # Good for text editing tasks
                output_format="json",
                system_prompt=prompt,
                timeout=self.timeout_seconds - 1
            )
            
            result = await asyncio.wait_for(
                agent.run("Customize this resume section"),
                timeout=self.timeout_seconds - 1
            )
            
            # Validate the customized section
            valid = self._validate_customization(
                original=self.section_content,
                customized=result["customized_content"]
            )
            
            if not valid:
                # Fall back to a simpler approach
                return await self._perform_simple_customization(section_recommendations)
                
            return result
        except Exception as e:
            # Try with fallback model
            try:
                agent = Agent(
                    "google:gemini-flash",  # Fallback to different provider
                    output_format="json",
                    system_prompt=prompt,
                    timeout=self.timeout_seconds - 1
                )
                result = await agent.run("Customize this resume section")
                return result
            except Exception as fallback_error:
                # Both attempts failed, fall back to a simpler approach
                logfire.error(f"Section customization failed: {str(e)}, fallback error: {str(fallback_error)}")
                return await self._perform_simple_customization(section_recommendations)
                
    def _validate_customization(self, original, customized):
        """Validate that the customization is acceptable."""
        # Check the length is reasonable
        if len(customized) < len(original) * 0.5 or len(customized) > len(original) * 2:
            return False
            
        # Perform other validations
        # ...
        
        return True
        
    async def _perform_simple_customization(self, recommendations):
        """Fall back to a simpler customization approach."""
        # Implement a rule-based or template-based customization
        # ...
```

---

### Issue 6: Final Resume Assembler and Validator

**Priority:** Medium  
**Dependencies:** Issue 5

**Description:**  
Create a service to assemble customized sections into a cohesive resume and validate the overall result.

**Tasks:**
1. Implement a resume assembly service with section ordering
2. Create overall resume validation
3. Add formatting consistency checks
4. Implement comparison metrics between original and customized resume

**Code Outline:**
```python
class ResumeAssembler(MicroTask):
    """Assembles customized sections into a complete resume."""
    
    def __init__(self, original_resume, timeout_seconds=45):
        super().__init__("assemble_resume", timeout_seconds)
        self.original_resume = original_resume
        
    async def _execute(self, customized_sections, improvement_plan, **kwargs):
        """Assemble customized sections into a complete resume."""
        # Order sections according to standard resume order
        ordered_sections = self._order_sections(customized_sections)
        
        # Join the sections with appropriate spacing
        assembled_resume = self._join_sections(ordered_sections)
        
        # Validate the assembled resume
        validation_result = self._validate_assembled_resume(
            assembled_resume, 
            self.original_resume
        )
        
        if not validation_result["valid"]:
            # There are issues with the assembled resume
            logfire.warning(
                "Assembled resume has validation issues",
                issues=validation_result["issues"]
            )
            
            # Try to fix issues
            assembled_resume = await self._fix_assembly_issues(
                assembled_resume,
                validation_result["issues"]
            )
            
        # Add global formatting improvements from the plan
        if improvement_plan.formatting_suggestions:
            assembled_resume = await self._apply_formatting_suggestions(
                assembled_resume,
                improvement_plan.formatting_suggestions
            )
            
        return {
            "customized_resume": assembled_resume,
            "original_resume": self.original_resume,
            "diff_stats": self._calculate_diff_stats(self.original_resume, assembled_resume),
            "validation_result": validation_result
        }
        
    def _order_sections(self, customized_sections):
        """Order sections according to standard resume order."""
        # Define the desired order
        section_order = [
            "summary", "experience", "skills", "education", 
            "projects", "certifications", "other"
        ]
        
        # Order the sections accordingly
        ordered = []
        for section_type in section_order:
            if section_type in customized_sections:
                ordered.append({
                    "type": section_type,
                    "content": customized_sections[section_type]["customized_content"]
                })
                
        return ordered
        
    def _join_sections(self, ordered_sections):
        """Join the sections with appropriate spacing."""
        # Convert sections to text with proper spacing
        joined = ""
        for section in ordered_sections:
            joined += f"\n\n{section['content']}"
            
        # Clean up any double line breaks
        joined = re.sub(r'\n{3,}', '\n\n', joined)
        return joined.strip()
        
    def _validate_assembled_resume(self, assembled, original):
        """Validate the assembled resume against the original."""
        issues = []
        
        # Check if resume is significantly shorter
        if len(assembled) < len(original) * 0.75:
            issues.append("Assembled resume is significantly shorter than the original")
            
        # Check for other validation issues
        # ...
        
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }
        
    async def _fix_assembly_issues(self, assembled, issues):
        """Try to fix assembly issues."""
        # Implement fixes for common issues
        # ...
        
    async def _apply_formatting_suggestions(self, resume, suggestions):
        """Apply global formatting suggestions."""
        # Implement formatting improvements
        # ...
        
    def _calculate_diff_stats(self, original, customized):
        """Calculate diff statistics between original and customized resume."""
        # Implement diff calculation
        # ...
```

---

### Issue 7: Progress Tracking and Visualization

**Priority:** Medium  
**Dependencies:** Issue 1

**Description:**  
Create a service to track and visualize the progress of the resume customization process.

**Tasks:**
1. Create a WebSocket-based progress reporting system
2. Implement a visual progress indicator component
3. Add detailed task status reporting
4. Create error visualization for failed tasks

**Code Outline:**

Backend (Python):
```python
class ProgressTracker:
    """Tracks and reports progress of the customization process."""
    
    def __init__(self, websocket_manager):
        self.websocket_manager = websocket_manager
        self.task_statuses = {}
        self.overall_progress = 0
        self.start_time = None
        self.end_time = None
        self.status = "not_started"
        
    def start_tracking(self):
        """Start tracking progress."""
        self.start_time = time.time()
        self.status = "in_progress"
        self.overall_progress = 0
        self._send_update()
        
    def update_task_status(self, task_name, status, progress=None, details=None):
        """Update the status of a specific task."""
        self.task_statuses[task_name] = {
            "status": status,
            "progress": progress,
            "details": details,
            "updated_at": time.time()
        }
        
        # Recalculate overall progress
        self._recalculate_overall_progress()
        
        # Send update
        self._send_update()
        
    def complete_tracking(self, success=True):
        """Complete tracking with success or failure."""
        self.end_time = time.time()
        self.status = "completed" if success else "failed"
        self.overall_progress = 100 if success else self.overall_progress
        self._send_update()
        
    def _recalculate_overall_progress(self):
        """Recalculate the overall progress percentage."""
        if not self.task_statuses:
            self.overall_progress = 0
            return
            
        # Calculate weighted progress
        total_weight = 0
        weighted_progress = 0
        
        # Define task weights (importance)
        task_weights = {
            "extract_requirements": 0.1,
            "analyze_experience": 0.2,
            "analyze_skills": 0.2,
            "analyze_summary": 0.1,
            "analyze_education": 0.1,
            "generate_plan": 0.4,
            "customize_experience": 0.3,
            "customize_skills": 0.3,
            "customize_summary": 0.2,
            "customize_education": 0.2,
            "assemble_resume": 0.2
        }
        
        for task_name, status in self.task_statuses.items():
            weight = task_weights.get(task_name, 0.1)
            total_weight += weight
            
            # Calculate progress for this task
            task_progress = 0
            if status["status"] == "completed":
                task_progress = 100
            elif status["status"] == "failed":
                task_progress = 0
            elif status["status"] == "in_progress":
                task_progress = status.get("progress", 50)
            elif status["status"] == "pending":
                task_progress = 0
                
            weighted_progress += task_progress * weight
            
        # Calculate overall progress
        if total_weight > 0:
            self.overall_progress = int(weighted_progress / total_weight)
        else:
            self.overall_progress = 0
            
    def _send_update(self):
        """Send progress update via WebSocket."""
        update = {
            "overall_progress": self.overall_progress,
            "status": self.status,
            "task_statuses": self.task_statuses,
            "elapsed_seconds": int(time.time() - self.start_time) if self.start_time else 0,
            "estimated_remaining_seconds": self._estimate_remaining_time()
        }
        
        self.websocket_manager.broadcast_json("progress_update", update)
        
    def _estimate_remaining_time(self):
        """Estimate remaining time based on progress and elapsed time."""
        if self.overall_progress <= 0 or not self.start_time:
            return None
            
        elapsed = time.time() - self.start_time
        estimated_total = elapsed / (self.overall_progress / 100)
        remaining = estimated_total - elapsed
        
        # Cap at reasonable value
        return min(int(remaining), 300)  # Cap at 5 minutes
```

Frontend (React):
```typescript
import React, { useEffect, useState } from 'react';
import { Progress, Card, Text, Heading, Stack, Badge } from '@chakra-ui/react';

interface ProgressTrackerProps {
  customizationId: string;
}

interface TaskStatus {
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  progress?: number;
  details?: string;
  updated_at: number;
}

interface ProgressUpdate {
  overall_progress: number;
  status: 'not_started' | 'in_progress' | 'completed' | 'failed';
  task_statuses: Record<string, TaskStatus>;
  elapsed_seconds: number;
  estimated_remaining_seconds?: number;
}

export const CustomizationProgressTracker: React.FC<ProgressTrackerProps> = ({ 
  customizationId 
}) => {
  const [progress, setProgress] = useState<ProgressUpdate | null>(null);
  const [socket, setSocket] = useState<WebSocket | null>(null);
  
  useEffect(() => {
    // Connect to WebSocket
    const ws = new WebSocket(`ws://${window.location.host}/api/ws/progress/${customizationId}`);
    
    ws.onopen = () => {
      console.log('Connected to progress WebSocket');
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'progress_update') {
        setProgress(data.payload);
      }
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    setSocket(ws);
    
    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, [customizationId]);
  
  if (!progress) {
    return <Text>Preparing to customize your resume...</Text>;
  }
  
  return (
    <Card p={4}>
      <Heading size="md">Resume Customization Progress</Heading>
      
      <Progress 
        value={progress.overall_progress} 
        colorScheme={progress.status === 'failed' ? 'red' : 'blue'}
        my={4}
      />
      
      <Text>
        {progress.overall_progress}% Complete 
        {progress.estimated_remaining_seconds && 
          ` (${Math.ceil(progress.estimated_remaining_seconds / 60)} min remaining)`
        }
      </Text>
      
      <Stack mt={4} spacing={2}>
        {Object.entries(progress.task_statuses).map(([taskName, status]) => (
          <Stack key={taskName} direction="row" align="center">
            <Badge colorScheme={
              status.status === 'completed' ? 'green' :
              status.status === 'in_progress' ? 'blue' :
              status.status === 'failed' ? 'red' : 'gray'
            }>
              {status.status}
            </Badge>
            <Text>{taskName}</Text>
            {status.progress !== undefined && (
              <Progress 
                value={status.progress} 
                size="sm" 
                width="100px" 
                colorScheme={status.status === 'failed' ? 'red' : 'blue'}
              />
            )}
          </Stack>
        ))}
      </Stack>
    </Card>
  );
};
```

---

### Issue 8: Smart Request Chunking System

**Priority:** Medium  
**Dependencies:** None

**Description:**  
Create a system to intelligently chunk large requests into smaller parts for more reliable processing.

**Tasks:**
1. Implement job description chunking
2. Create resume content chunking system
3. Add context management to maintain continuity between chunks
4. Implement reassembly of chunked results

**Code Outline:**
```python
class ContentChunker:
    """Chunks large content into manageable pieces for AI models."""
    
    def __init__(self, max_chunk_size=8000):
        self.max_chunk_size = max_chunk_size
        
    def chunk_text(self, text, chunk_strategy='paragraph'):
        """Chunk text into manageable pieces."""
        if len(text) <= self.max_chunk_size:
            # No chunking needed
            return [text]
            
        if chunk_strategy == 'paragraph':
            return self._chunk_by_paragraphs(text)
        elif chunk_strategy == 'section':
            return self._chunk_by_sections(text)
        else:
            return self._chunk_by_characters(text)
            
    def _chunk_by_paragraphs(self, text):
        """Chunk text by paragraphs."""
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            # If adding this paragraph would exceed max size, start a new chunk
            if len(current_chunk) + len(paragraph) + 2 > self.max_chunk_size:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = paragraph
            else:
                if current_chunk:
                    current_chunk += '\n\n' + paragraph
                else:
                    current_chunk = paragraph
                    
        # Add the last chunk if it has content
        if current_chunk:
            chunks.append(current_chunk)
            
        return chunks
        
    def _chunk_by_sections(self, text):
        """Chunk resume or job description by sections."""
        # Use regex to identify section headers
        import re
        section_pattern = r'^(#+\s+.+|[A-Z][A-Z\s]+:?|.+\n[-=]+)$'
        sections = []
        
        # Split by potential section headers
        lines = text.split('\n')
        current_section = ""
        
        for line in lines:
            if re.match(section_pattern, line):
                # This looks like a section header
                if current_section:
                    sections.append(current_section)
                current_section = line
            else:
                current_section += '\n' + line
                
        # Add the last section
        if current_section:
            sections.append(current_section)
            
        # Now combine sections into chunks
        return self._combine_sections_into_chunks(sections)
        
    def _combine_sections_into_chunks(self, sections):
        """Combine sections into chunks that don't exceed max size."""
        chunks = []
        current_chunk = ""
        
        for section in sections:
            if len(section) > self.max_chunk_size:
                # This single section is too big, need to split it
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""
                    
                # Split this oversized section
                section_chunks = self._chunk_by_paragraphs(section)
                chunks.extend(section_chunks)
            elif len(current_chunk) + len(section) + 2 > self.max_chunk_size:
                # Adding this section would make the chunk too big
                chunks.append(current_chunk)
                current_chunk = section
            else:
                # Add to current chunk
                if current_chunk:
                    current_chunk += '\n\n' + section
                else:
                    current_chunk = section
                    
        # Add the last chunk
        if current_chunk:
            chunks.append(current_chunk)
            
        return chunks
        
    def _chunk_by_characters(self, text):
        """Chunk text by character count as a last resort."""
        chunks = []
        for i in range(0, len(text), self.max_chunk_size):
            chunks.append(text[i:i + self.max_chunk_size])
        return chunks


class ChunkedProcessor:
    """Processes content in chunks with context management."""
    
    def __init__(self, chunker=None):
        self.chunker = chunker or ContentChunker()
        
    async def process_with_context(self, processor_func, content, **kwargs):
        """Process content in chunks, maintaining context between chunks."""
        # Chunk the content
        chunks = self.chunker.chunk_text(content, 'section')
        
        if len(chunks) == 1:
            # No chunking needed
            return await processor_func(content, **kwargs)
            
        # Initialize context
        context = {
            "previous_results": [],
            "chunk_number": 0,
            "total_chunks": len(chunks)
        }
        
        all_results = []
        
        # Process each chunk with context
        for i, chunk in enumerate(chunks):
            # Update context
            context["chunk_number"] = i + 1
            context["current_chunk_text"] = chunk
            
            # Process this chunk
            chunk_result = await processor_func(
                chunk, 
                context=context,
                **kwargs
            )
            
            # Add to results and update context
            all_results.append(chunk_result)
            context["previous_results"].append(chunk_result)
            
        # Combine results
        return self._combine_results(all_results)
        
    def _combine_results(self, results):
        """Combine results from multiple chunks."""
        # This needs to be implemented based on the result type
        # For text, simple concatenation might work
        # For structured data, more complex merging is needed
        # ...
        
        # This is a placeholder implementation
        if all(isinstance(r, str) for r in results):
            return "\n\n".join(results)
        elif all(isinstance(r, dict) for r in results):
            combined = {}
            for r in results:
                for k, v in r.items():
                    if k in combined:
                        if isinstance(combined[k], list) and isinstance(v, list):
                            combined[k].extend(v)
                        else:
                            # Just keep the latest value
                            combined[k] = v
                    else:
                        combined[k] = v
            return combined
        else:
            # Can't combine heterogeneous results
            return results
```

---

### Issue 9: Error Recovery and Partial Results Handler

**Priority:** Medium  
**Dependencies:** Issue 1

**Description:**  
Create a system to handle API errors and timeouts while still providing useful partial results.

**Tasks:**
1. Implement error recovery strategies for different failure points
2. Create a partial results assembler
3. Add fallback processing paths for critical failures
4. Implement graceful degradation of service quality

**Code Outline:**
```python
class ErrorRecoveryHandler:
    """Handles errors and provides recovery strategies."""
    
    def __init__(self):
        self.recovery_strategies = {
            "timeout": self._handle_timeout,
            "api_error": self._handle_api_error,
            "validation_error": self._handle_validation_error,
            "parsing_error": self._handle_parsing_error,
            "unknown": self._handle_unknown_error
        }
        
    async def recover(self, error, task_name, task_args, task_result=None):
        """Attempt to recover from an error."""
        # Determine error type
        error_type = self._categorize_error(error)
        
        # Get the appropriate recovery strategy
        recovery_func = self.recovery_strategies.get(error_type, self.recovery_strategies["unknown"])
        
        # Execute recovery strategy
        return await recovery_func(error, task_name, task_args, task_result)
        
    def _categorize_error(self, error):
        """Categorize the error to determine recovery strategy."""
        if isinstance(error, asyncio.TimeoutError):
            return "timeout"
        elif isinstance(error, ValidationException):
            return "validation_error"
        elif "API" in str(error):
            return "api_error"
        elif "parse" in str(error).lower() or "json" in str(error).lower():
            return "parsing_error"
        else:
            return "unknown"
            
    async def _handle_timeout(self, error, task_name, task_args, task_result):
        """Handle timeout errors."""
        logfire.warning(f"Timeout in task {task_name}, attempting recovery")
        
        if task_name.startswith("analyze_"):
            # For analysis tasks, use a simpler model with less context
            return await self._retry_with_simpler_model(task_name, task_args)
        elif task_name.startswith("customize_"):
            # For customization tasks, fall back to simple text replacement
            return await self._fallback_to_simple_customization(task_name, task_args)
        elif task_name == "generate_plan":
            # For plan generation, create a minimal plan
            return await self._create_minimal_plan(task_args)
        else:
            # General fallback
            return self._create_error_response(task_name, error)
            
    async def _handle_api_error(self, error, task_name, task_args, task_result):
        """Handle API-related errors."""
        # Similar to timeout but with different strategies
        # ...
        
    async def _handle_validation_error(self, error, task_name, task_args, task_result):
        """Handle validation errors."""
        # Create a valid but possibly lower-quality result
        # ...
        
    async def _handle_parsing_error(self, error, task_name, task_args, task_result):
        """Handle parsing errors in API responses."""
        # Attempt to fix common parsing issues
        # ...
        
    async def _handle_unknown_error(self, error, task_name, task_args, task_result):
        """Handle unknown errors."""
        # Generic error response
        # ...
        
    async def _retry_with_simpler_model(self, task_name, task_args):
        """Retry a task with a simpler model and reduced context."""
        # Create a simpler version of the task
        # ...
        
    async def _fallback_to_simple_customization(self, task_name, task_args):
        """Fall back to a simple rule-based customization approach."""
        # Implement simple customization logic
        # ...
        
    async def _create_minimal_plan(self, task_args):
        """Create a minimal plan with basic recommendations."""
        # Create a simplified plan
        # ...
        
    def _create_error_response(self, task_name, error):
        """Create a standard error response for a task."""
        return {
            "error": str(error),
            "task_name": task_name,
            "status": "failed",
            "fallback_result": None
        }


class PartialResultsHandler:
    """Handles and combines partial results when some tasks fail."""
    
    def __init__(self, error_recovery_handler=None):
        self.error_recovery_handler = error_recovery_handler or ErrorRecoveryHandler()
        
    async def assemble_partial_results(self, task_results, original_resume, job_description):
        """Assemble the best possible result from partial successes."""
        # Count successful vs failed tasks
        success_count = len([r for r in task_results.values() if not isinstance(r, Exception)])
        total_count = len(task_results)
        
        if success_count == 0:
            # Complete failure, create a minimal response
            return await self._handle_complete_failure(original_resume, job_description)
            
        success_ratio = success_count / total_count
        
        if success_ratio >= 0.8:
            # Most tasks succeeded, we can still produce a good result
            return await self._assemble_mostly_successful(task_results, original_resume)
        elif success_ratio >= 0.5:
            # Some tasks succeeded, create a partial result
            return await self._assemble_partially_successful(task_results, original_resume)
        else:
            # Few tasks succeeded, create a minimal result
            return await self._assemble_mostly_failed(task_results, original_resume, job_description)
            
    async def _handle_complete_failure(self, original_resume, job_description):
        """Handle the case where all tasks failed."""
        logfire.error("All customization tasks failed, returning minimal results")
        
        # Create a minimal result
        return {
            "customized_resume": original_resume,
            "success": False,
            "message": "We encountered issues customizing your resume. Here are some general suggestions...",
            "general_suggestions": await self._generate_general_suggestions(original_resume, job_description)
        }
        
    async def _assemble_mostly_successful(self, task_results, original_resume):
        """Assemble results when most tasks succeeded."""
        # For the failed tasks, use empty or placeholder results
        # ...
        
    async def _assemble_partially_successful(self, task_results, original_resume):
        """Assemble results when some tasks succeeded."""
        # Prioritize the most important sections
        # ...
        
    async def _assemble_mostly_failed(self, task_results, original_resume, job_description):
        """Assemble minimal results when most tasks failed."""
        # Use the few successful results and generic suggestions
        # ...
        
    async def _generate_general_suggestions(self, original_resume, job_description):
        """Generate general suggestions for resume improvement."""
        # Create basic tips based on job description
        # ...
```

---

### Issue 10: Integration with Existing Services

**Priority:** Medium  
**Dependencies:** Issues 1-9

**Description:**  
Integrate the new architecture with existing services and APIs.

**Tasks:**
1. Update API endpoints to use the new architecture
2. Ensure backward compatibility with existing clients
3. Add feature flags for gradual rollout
4. Update documentation and client code

**Code Outline:**

API Endpoint:
```python
@router.post("/customize/", response_model=CustomizationResponse)
async def customize_resume_endpoint(
    request: CustomizationRequest,
    feature_flags: FeatureFlags = Depends(get_feature_flags),
    db: Session = Depends(get_db),
):
    """Customize a resume for a specific job description."""
    # Check feature flag for the new architecture
    if feature_flags.use_new_customization_architecture:
        return await customize_resume_new_architecture(request, db)
    else:
        # Use the original implementation for backward compatibility
        return await customize_resume_original(request, db)


async def customize_resume_new_architecture(request: CustomizationRequest, db: Session):
    """Customize a resume using the new micro-task architecture."""
    try:
        # Create the orchestrator
        orchestrator = TaskOrchestrator()
        
        # Setup progress tracking if websocket connection is active
        progress_tracker = ProgressTracker(request.customization_id)
        progress_tracker.start_tracking()
        
        # Create content chunker
        chunker = ContentChunker()
        
        # Extract resume and job description
        resume_content, job_description = await get_resume_and_job(
            request.resume_id, 
            request.job_description_id,
            db
        )
        
        # 1. Extract key requirements
        requirements_extractor = RequirementsExtractor()
        orchestrator.add_task(requirements_extractor)
        
        # 2. Create section analyzers
        resume_sections = ResumeSegmenter.identify_sections(resume_content)
        section_analyzers = {}
        
        for section_type, section_content in resume_sections.items():
            if section_type == SectionType.EXPERIENCE:
                analyzer = ExperienceAnalyzer(section_content)
            elif section_type == SectionType.SKILLS:
                analyzer = SkillsAnalyzer(section_content)
            elif section_type == SectionType.SUMMARY:
                analyzer = SummaryAnalyzer(section_content)
            elif section_type == SectionType.EDUCATION:
                analyzer = EducationAnalyzer(section_content)
            else:
                analyzer = GenericSectionAnalyzer(section_type, section_content)
                
            section_analyzers[section_type] = analyzer
            orchestrator.add_task(analyzer, dependencies=["extract_requirements"])
            
        # 3. Add plan generator
        plan_generator = ImprovementPlanGenerator()
        orchestrator.add_task(
            plan_generator,
            dependencies=["extract_requirements"] + list(section_analyzers.keys())
        )
        
        # 4. Add section customizers
        section_customizers = {}
        for section_type, section_content in resume_sections.items():
            customizer = SectionCustomizer(section_type, section_content)
            section_customizers[section_type] = customizer
            orchestrator.add_task(
                customizer,
                dependencies=["generate_plan"]
            )
            
        # 5. Add resume assembler
        assembler = ResumeAssembler(resume_content)
        orchestrator.add_task(
            assembler,
            dependencies=list(section_customizers.keys())
        )
        
        # Execute all tasks
        try:
            results = await orchestrator.execute_all()
            
            # Extract the final result
            assembled_result = results.get("assemble_resume")
            
            if assembled_result:
                # Success
                progress_tracker.complete_tracking(success=True)
                
                # Return results
                return CustomizationResponse(
                    customized_resume=assembled_result["customized_resume"],
                    original_resume=resume_content,
                    success=True,
                    customization_id=request.customization_id,
                    resume_id=request.resume_id,
                    job_id=request.job_description_id
                )
            else:
                # Missing final assembly result
                logfire.error("Missing assembler result, using partial results handler")
                partial_handler = PartialResultsHandler()
                partial_result = await partial_handler.assemble_partial_results(
                    results, 
                    resume_content, 
                    job_description
                )
                
                progress_tracker.complete_tracking(success=False)
                
                return CustomizationResponse(
                    customized_resume=partial_result["customized_resume"],
                    original_resume=resume_content,
                    success=False,
                    error_message=partial_result.get("message"),
                    customization_id=request.customization_id,
                    resume_id=request.resume_id,
                    job_id=request.job_description_id
                )
                
        except Exception as e:
            # Execution error
            logfire.error(f"Error during task execution: {str(e)}")
            progress_tracker.complete_tracking(success=False)
            
            # Try to recover using partial results
            error_handler = ErrorRecoveryHandler()
            partial_handler = PartialResultsHandler(error_handler)
            
            # Get any results that did complete
            completed_results = {
                name: task_info["task"].result
                for name, task_info in orchestrator.tasks.items()
                if task_info["task"].status == TaskStatus.COMPLETED
            }
            
            partial_result = await partial_handler.assemble_partial_results(
                completed_results,
                resume_content,
                job_description
            )
            
            return CustomizationResponse(
                customized_resume=partial_result["customized_resume"],
                original_resume=resume_content,
                success=False,
                error_message=f"Error during customization: {str(e)}",
                customization_id=request.customization_id,
                resume_id=request.resume_id,
                job_id=request.job_description_id
            )
            
    except Exception as e:
        # Top-level error
        logfire.error(f"Critical error in customization: {str(e)}")
        return CustomizationResponse(
            customized_resume=resume_content,
            original_resume=resume_content,
            success=False,
            error_message=f"Critical error during customization: {str(e)}",
            customization_id=request.customization_id,
            resume_id=request.resume_id,
            job_id=request.job_description_id
        )
```

## Implementation Strategy

### Phase 1: Core Infrastructure

1. Implement the MicroTask and TaskOrchestrator classes (Issue 1)
2. Create the RequirementsExtractor service (Issue 3)
3. Implement basic Error Recovery (Issue 9)
4. Add the Progress Tracking system (Issue 7)

### Phase 2: Section-Based Processing

1. Implement the Resume Section Analyzer Framework (Issue 2)
2. Create specialized analyzers for key resume sections
3. Implement the Content Chunker (Issue 8)
4. Add validation gates between process steps

### Phase 3: Plan Generation and Customization

1. Implement the Improvement Plan Generator (Issue 4)
2. Create the Section Customizer services (Issue 5)
3. Implement the Resume Assembler and Validator (Issue 6)
4. Add detailed error handling and recovery strategies

### Phase 4: Integration and Testing

1. Update API endpoints to use the new architecture (Issue 10)
2. Add feature flags for gradual rollout
3. Implement comprehensive testing
4. Monitor performance and reliability

## Prioritization

1. First priority: Fix timeouts and add error handling
2. Second priority: Implement section-based processing
3. Third priority: Add progress tracking and visualization
4. Fourth priority: Integrate with existing services

## Conclusion

This redesign breaks down the resume customization process into smaller, more manageable tasks that can handle failures gracefully. The modular architecture allows for:

1. Better isolation of failures
2. More detailed progress reporting
3. Streamlined sequential processing of tasks
4. Improved reliability with multiple fallback strategies

Each component can be developed and tested independently, allowing multiple contributors to work without conflicts.
