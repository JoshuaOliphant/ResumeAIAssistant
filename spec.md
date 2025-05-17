# Resume Customization Service Specification

## Overview

This specification outlines a complete redesign of the resume customization service using PydanticAI and a four-stage workflow approach. The primary objectives are improving match scores between resumes and job descriptions, ensuring truthfulness in customizations, and providing real-time progress updates to users.

The system will use a single AI model (Claude 3.7 Sonnet) and focus on a clean, testable architecture following the principles from [Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents).

## System Architecture

### Core Components

1. **PydanticAI Integration**: Using structured output types and validation
2. **Four-Stage Workflow**: Evaluation → Planning → Implementation → Verification
3. **WebSocket Progress Reporting**: Real-time stage-based updates
4. **Docx Template System**: Template-based resume generation
5. **Diff View Generation**: Git-style diff view for changes
6. **Section-by-Section Explanations**: Explaining changes by resume section
7. **File Storage & Database**: Tigris for object storage and LiteFS for database

### Workflow Details

#### Stage 1: Evaluation
- **Purpose**: Assess how well the resume matches the job description
- **Output**: Match score, key matches, missing skills, strengths, weaknesses
- **Validation**: Ensure score is between 0-100, identify at least 3 strengths

#### Stage 2: Planning
- **Purpose**: Create strategic plan for improvements
- **Output**: Target score, section changes, keywords to add, format improvements
- **Validation**: Verify plan addresses key gaps from evaluation

#### Stage 3: Implementation
- **Purpose**: Apply changes to resume using template
- **Output**: Customized resume in docx format
- **Validation**: Ensure all planned changes are implemented

#### Stage 4: Verification
- **Purpose**: Verify truthfulness and quality of customizations
- **Output**: Verification result with truthfulness assessment, final score
- **Validation**: Confirm no fabricated content, calculate improvement

## Data Models

### Core Schema Models

```python
from pydantic import BaseModel, Field
from typing import List, Dict, Optional

class ResumeAnalysis(BaseModel):
    """Evaluation of resume-job match."""
    match_score: int = Field(description="Overall match score (0-100)", ge=0, le=100)
    key_matches: List[Dict[str, str]] = Field(description="Skills found in resume")
    missing_skills: List[str] = Field(description="Important skills not in resume")
    strengths: List[str] = Field(description="Resume strengths for this job")
    weaknesses: List[str] = Field(description="Areas needing improvement")
    section_analysis: Dict[str, Dict] = Field(description="Analysis by section")

class CustomizationPlan(BaseModel):
    """Strategic plan for resume improvements."""
    target_score: int = Field(description="Target match score after changes", ge=0, le=100)
    section_changes: Dict[str, str] = Field(description="Changes for each section")
    keywords_to_add: List[str] = Field(description="Keywords to incorporate")
    format_improvements: List[str] = Field(description="Format and style changes")
    change_explanations: Dict[str, str] = Field(description="Explanations by section")

class VerificationResult(BaseModel):
    """Truthfulness verification of customized resume."""
    is_truthful: bool = Field(description="Whether resume is truthful")
    issues: List[Dict[str, str]] = Field(default_factory=list)
    final_score: int = Field(description="Final match score", ge=0, le=100)
    improvement: int = Field(description="Points improved", ge=0)
    section_assessments: Dict[str, Dict] = Field(description="Assessment by section")
```

## Storage Schema

### Tigris Object Storage Structure

```
/resumes/user_{id}/original/{resume_id}.docx
/resumes/user_{id}/customized/{resume_id}_{job_id}_{timestamp}.docx
/resumes/user_{id}/diff/{resume_id}_{job_id}_{timestamp}.html
/jobs/user_{id}/{job_id}.txt
/templates/resume/{template_id}.docx
```

### LiteFS (SQLite) Database Schema

```sql
-- Users table
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Resumes table
CREATE TABLE resumes (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Jobs table
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    company TEXT,
    storage_path TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Templates table
CREATE TABLE templates (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    storage_path TEXT NOT NULL,
    preview_path TEXT
);

-- Customizations table
CREATE TABLE customizations (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    resume_id TEXT NOT NULL,
    job_id TEXT NOT NULL,
    template_id TEXT NOT NULL,
    original_resume_path TEXT NOT NULL,
    customized_resume_path TEXT,
    diff_path TEXT,
    status TEXT NOT NULL,
    detailed_status JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (resume_id) REFERENCES resumes(id),
    FOREIGN KEY (job_id) REFERENCES jobs(id),
    FOREIGN KEY (template_id) REFERENCES templates(id)
);
```

## Implementation Details

### Resume Customizer Service

```python
from pydantic_ai import Agent, ModelRetry
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Callable, Awaitable
import logfire
import asyncio
import os
import uuid

class ResumeCustomizer:
    """End-to-end resume customization using evaluator-optimizer pattern."""
    
    def __init__(self):
        # Configure observability
        logfire.configure(app_name="resume-customizer")
        logfire.instrument_pydantic_ai()
        self.progress_callback = None
        self.model = "anthropic:claude-3-7-sonnet-latest"
    
    def set_progress_callback(self, callback: Callable[[str, int, str], Awaitable[None]]):
        """Set callback for progress updates."""
        self.progress_callback = callback
    
    async def customize_resume(
        self, 
        resume_content: str, 
        job_description: str, 
        template_id: str,
        customization_id: str = None
    ):
        """Customize a resume for a specific job using selected template."""
        customization_id = customization_id or str(uuid.uuid4())
        
        with logfire.span("customize_resume", {"customization_id": customization_id}):
            try:
                # Stage 1: Evaluation - Assess baseline match
                await self._update_progress("evaluation", 0, "Starting evaluation")
                analysis = await self._evaluate_resume(resume_content, job_description)
                await self._update_progress("evaluation", 100, "Evaluation complete")
                
                # Stage 2: Planning - Create strategic improvement plan 
                await self._update_progress("planning", 0, "Creating improvement plan")
                plan = await self._create_plan(resume_content, job_description, analysis)
                await self._update_progress("planning", 100, "Plan created")
                
                # Stage 3: Implementation - Apply changes with template
                await self._update_progress("implementation", 0, "Implementing changes")
                customized_resume = await self._implement_changes(
                    resume_content, 
                    job_description,
                    plan,
                    template_id
                )
                await self._update_progress("implementation", 100, "Changes implemented")
                
                # Stage 4: Verification - Ensure truthfulness and quality
                await self._update_progress("verification", 0, "Verifying truthfulness")
                verification = await self._verify_customization(
                    resume_content, 
                    customized_resume, 
                    job_description
                )
                await self._update_progress("verification", 100, "Verification complete")
                
                # Generate diff view
                diff_html = await self._generate_diff(resume_content, customized_resume)
                
                return {
                    "customization_id": customization_id,
                    "original_resume": resume_content,
                    "customized_resume": customized_resume,
                    "analysis": analysis.dict(),
                    "plan": plan.dict(),
                    "verification": verification.dict(),
                    "diff_html": diff_html,
                    "success": True
                }
            except Exception as e:
                logfire.error(f"Customization failed: {str(e)}", exc_info=True)
                await self._update_progress("error", 100, f"Error: {str(e)}")
                return {
                    "customization_id": customization_id,
                    "success": False,
                    "error": str(e)
                }
    
    async def _update_progress(self, stage: str, percentage: int, message: str):
        """Update progress via callback if set."""
        if self.progress_callback:
            await self.progress_callback(stage, percentage, message)
    
    async def _evaluate_resume(self, resume: str, job: str) -> ResumeAnalysis:
        """Stage 1: Evaluate resume-job match with validation."""
        try:
            agent = Agent(
                model=self.model,
                output_type=ResumeAnalysis,
                system_prompt=(
                    "You are an expert resume evaluator specializing in analyzing "
                    "how well resumes match job descriptions."
                )
            )
            
            @agent.output_validator()
            async def validate_analysis(ctx, result: ResumeAnalysis):
                """Ensure analysis meets quality standards."""
                if not (0 <= result.match_score <= 100):
                    raise ModelRetry("Match score must be between 0-100")
                if len(result.strengths) < 3:
                    raise ModelRetry("Identify at least 3 strengths")
                if len(result.weaknesses) < 2:
                    raise ModelRetry("Identify at least 2 areas for improvement")
                return result
            
            prompt = f"""
            Evaluate how well this resume matches the job description.
            
            RESUME:
            {resume}
            
            JOB DESCRIPTION:
            {job}
            
            Provide a detailed analysis including:
            1. Overall match score (0-100)
            2. Key skills/qualifications that match
            3. Important skills/qualifications missing from the resume
            4. The resume's strengths for this specific job
            5. Areas where the resume could be improved
            6. An analysis of each major resume section
            
            Be specific, objective, and focus on factual matches rather than subjective judgments.
            """
            
            return await agent.run(prompt)
        except Exception as e:
            logfire.error(f"Evaluation failed: {str(e)}", exc_info=True)
            raise
    
    async def _create_plan(
        self, 
        resume: str, 
        job: str, 
        analysis: ResumeAnalysis
    ) -> CustomizationPlan:
        """Stage 2: Create improvement plan with validation."""
        try:
            agent = Agent(
                model=self.model,
                output_type=CustomizationPlan,
                system_prompt=(
                    "You are an expert resume writer specializing in strategic resume "
                    "customization to match specific job descriptions."
                )
            )
            
            @agent.output_validator()
            async def validate_plan(ctx, result: CustomizationPlan):
                """Ensure plan addresses key gaps and is actionable."""
                if not (analysis.match_score <= result.target_score <= 100):
                    raise ModelRetry(
                        f"Target score ({result.target_score}) must be higher than "
                        f"current score ({analysis.match_score}) and at most 100"
                    )
                if len(result.section_changes) < 2:
                    raise ModelRetry("Plan must include changes for at least 2 sections")
                if len(result.keywords_to_add) < len(analysis.missing_skills) / 2:
                    raise ModelRetry("Plan should incorporate more missing keywords")
                return result
            
            prompt = f"""
            Create a strategic plan to customize this resume for the job description.
            
            RESUME:
            {resume}
            
            JOB DESCRIPTION:
            {job}
            
            CURRENT ANALYSIS:
            {analysis.json()}
            
            Develop a comprehensive plan that includes:
            1. Target match score after changes
            2. Specific changes to make for each major section
            3. Keywords and skills to incorporate from the job description
            4. Format or structure improvements
            5. Clear explanation for each change, connecting it to the job requirements
            
            Focus on substantive improvements that meaningfully increase the match score.
            IMPORTANT: All changes must maintain truthfulness - do not suggest fabricating experience or skills.
            """
            
            return await agent.run(prompt)
        except Exception as e:
            logfire.error(f"Planning failed: {str(e)}", exc_info=True)
            raise
    
    async def _implement_changes(
        self, 
        resume: str, 
        job: str,
        plan: CustomizationPlan,
        template_id: str
    ) -> str:
        """Stage 3: Implement changes according to plan and template."""
        try:
            # In a real implementation, we would load the template here
            # For now, we'll simulate template application with the LLM
            
            agent = Agent(
                model=self.model,
                output_type=str,  # Plain text for now
                system_prompt=(
                    "You are an expert resume writer who specializes in customizing "
                    "resumes to match job descriptions while maintaining truthfulness."
                )
            )
            
            prompt = f"""
            Customize this resume according to the improvement plan and template.
            
            ORIGINAL RESUME:
            {resume}
            
            JOB DESCRIPTION:
            {job}
            
            IMPROVEMENT PLAN:
            {plan.json()}
            
            TEMPLATE ID:
            {template_id}
            
            Instructions:
            1. Apply all the changes specified in the improvement plan
            2. Format the resume according to the template structure
            3. Incorporate the keywords and skills identified in the plan
            4. Ensure all content remains truthful to the original resume
            5. Return the complete customized resume in a clean, professional format
            
            The resume should be significantly improved for this specific job while
            maintaining truthfulness and following the selected template's structure.
            """
            
            # In a full implementation, we would parse the output and apply it to the template
            customized_resume = await agent.run(prompt)
            
            return customized_resume
        except Exception as e:
            logfire.error(f"Implementation failed: {str(e)}", exc_info=True)
            raise
    
    async def _verify_customization(
        self, 
        original: str, 
        customized: str, 
        job: str
    ) -> VerificationResult:
        """Stage 4: Verify truthfulness and quality of customizations."""
        try:
            agent = Agent(
                model=self.model,
                output_type=VerificationResult,
                system_prompt=(
                    "You are an expert resume verifier who ensures customized resumes "
                    "remain truthful and accurately represent the original content."
                )
            )
            
            @agent.output_validator()
            async def validate_verification(ctx, result: VerificationResult):
                """Ensure verification is thorough and accurate."""
                if result.is_truthful and len(result.issues) > 0:
                    raise ModelRetry(
                        "Inconsistent result: Cannot be truthful while having issues"
                    )
                if not (0 <= result.final_score <= 100):
                    raise ModelRetry("Final score must be between 0-100")
                return result
            
            prompt = f"""
            Verify the truthfulness and quality of this customized resume.
            
            ORIGINAL RESUME:
            {original}
            
            CUSTOMIZED RESUME:
            {customized}
            
            JOB DESCRIPTION:
            {job}
            
            Carefully verify:
            1. Whether all content in the customized resume is supported by the original
            2. If any information has been fabricated or exaggerated
            3. The final match score (0-100) with the job description
            4. How much the score improved from the original
            5. Assessment of each major section's customization
            
            Flag any truthfulness issues found, and provide a detailed assessment
            of how well the customization improves the resume for this job.
            """
            
            return await agent.run(prompt)
        except Exception as e:
            logfire.error(f"Verification failed: {str(e)}", exc_info=True)
            raise
    
    async def _generate_diff(self, original: str, customized: str) -> str:
        """Generate HTML diff view of changes between original and customized resume."""
        # In a real implementation, we would use a proper diff library
        # For now, we'll use the LLM to create a simplified diff view
        
        agent = Agent(
            model=self.model,
            output_type=str,
            system_prompt=(
                "You are an expert at creating clear, readable diffs between document versions."
            )
        )
        
        prompt = f"""
        Create an HTML diff view showing changes between the original and customized resume.
        
        ORIGINAL RESUME:
        {original}
        
        CUSTOMIZED RESUME:
        {customized}
        
        Create a Git-style HTML diff that:
        1. Shows added content in green with a '+' prefix
        2. Shows removed content in red with a '-' prefix
        3. Shows unchanged content in neutral color
        4. Groups changes by resume section
        5. Makes it easy to see all modifications at a glance
        
        Return only the HTML for the diff view, properly escaped and formatted.
        """
        
        diff_html = await agent.run(prompt)
        return diff_html
```

### API Endpoints

```python
from fastapi import APIRouter, Depends, BackgroundTasks, WebSocket, Query, HTTPException
from sqlalchemy.orm import Session
import uuid
from datetime import datetime

router = APIRouter()

@router.post("/customize/", response_model=CustomizationResponse)
async def customize_resume(
    request: CustomizationRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Initiate resume customization process."""
    # Generate customization ID
    customization_id = uuid.uuid4().hex
    
    # Get resume and job description
    resume = await get_resume(request.resume_id, user.id, db)
    job_description = await get_job_description(request.job_description_id, user.id, db)
    
    if not resume or not job_description:
        raise HTTPException(status_code=404, detail="Resume or job description not found")
    
    # Get template
    template = await get_template(request.template_id, db)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Store initial state in database
    customization = CustomizationModel(
        id=customization_id,
        user_id=user.id,
        resume_id=request.resume_id,
        job_id=request.job_description_id,
        template_id=request.template_id,
        original_resume_path=resume.storage_path,
        status="pending",
        created_at=datetime.utcnow()
    )
    db.add(customization)
    db.commit()
    
    # Start customization process in background
    background_tasks.add_task(
        run_customization_process,
        resume_customizer=ResumeCustomizer(),
        resume_content=resume.content,
        job_description=job_description.content,
        template_id=request.template_id,
        customization_id=customization_id,
        db=db
    )
    
    # Return initial response
    return CustomizationResponse(
        customization_id=customization_id,
        status="pending",
        message="Customization process started"
    )

@router.websocket("/ws/customize/{customization_id}")
async def websocket_customization_progress(
    websocket: WebSocket,
    customization_id: str,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    """WebSocket endpoint for progress updates."""
    # Authenticate user
    user = authenticate_token(token)
    if not user:
        await websocket.close(code=1008)  # Policy violation
        return
    
    # Check customization exists and belongs to user
    customization = db.query(CustomizationModel).filter(
        CustomizationModel.id == customization_id,
        CustomizationModel.user_id == user.id
    ).first()
    
    if not customization:
        await websocket.close(code=1008)  # Policy violation
        return
    
    # Create WebSocket manager for progress reporting
    websocket_manager = get_websocket_manager()
    
    # Accept connection
    await websocket.accept()
    
    # Register connection
    websocket_manager.register(customization_id, websocket)
    
    try:
        # Keep connection open
        while True:
            # Receive ping to keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        # Remove connection
        websocket_manager.remove(customization_id, websocket)

@router.get("/templates/", response_model=List[TemplateResponse])
async def get_templates(
    db: Session = Depends(get_db)
):
    """Get available resume templates."""
    templates = db.query(TemplateModel).all()
    return [
        TemplateResponse(
            id=template.id,
            name=template.name,
            description=template.description,
            preview_url=f"/templates/preview/{template.id}"
        )
        for template in templates
    ]

@router.get("/customize/{customization_id}", response_model=CustomizationResultResponse)
async def get_customization_result(
    customization_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the result of a customization process."""
    # Get customization from database
    customization = db.query(CustomizationModel).filter(
        CustomizationModel.id == customization_id,
        CustomizationModel.user_id == user.id
    ).first()
    
    if not customization:
        raise HTTPException(status_code=404, detail="Customization not found")
    
    # Create response
    return CustomizationResultResponse(
        customization_id=customization_id,
        status=customization.status,
        original_resume_url=f"/resumes/download/{customization.original_resume_path}",
        customized_resume_url=(
            f"/resumes/download/{customization.customized_resume_path}" 
            if customization.customized_resume_path else None
        ),
        diff_url=(
            f"/resumes/diff/{customization.diff_path}" 
            if customization.diff_path else None
        ),
        analysis=json.loads(customization.detailed_status).get("analysis") if customization.detailed_status else None,
        plan=json.loads(customization.detailed_status).get("plan") if customization.detailed_status else None,
        verification=json.loads(customization.detailed_status).get("verification") if customization.detailed_status else None,
        error_message=json.loads(customization.detailed_status).get("error") if customization.detailed_status else None
    )
```

### Background Task Processing

```python
async def run_customization_process(
    resume_customizer: ResumeCustomizer,
    resume_content: str,
    job_description: str,
    template_id: str,
    customization_id: str,
    db: Session
):
    """Run the resume customization process as a background task."""
    # Create progress callback for WebSocket
    websocket_manager = get_websocket_manager()
    
    async def progress_callback(stage, percentage, message):
        """Send progress updates via WebSocket."""
        data = {
            "stage": stage,
            "percentage": percentage,
            "message": message,
            "overall_progress": calculate_overall_progress(stage, percentage)
        }
        await websocket_manager.send_json(customization_id, data)
        
        # Update database with progress
        db.execute(
            update(CustomizationModel)
            .where(CustomizationModel.id == customization_id)
            .values(
                status="in_progress",
                detailed_status=json.dumps({
                    "stage": stage,
                    "percentage": percentage,
                    "message": message,
                    "overall_progress": calculate_overall_progress(stage, percentage)
                })
            )
        )
        db.commit()
    
    # Set progress callback
    resume_customizer.set_progress_callback(progress_callback)
    
    try:
        # Run customization
        result = await resume_customizer.customize_resume(
            resume_content=resume_content,
            job_description=job_description,
            template_id=template_id,
            customization_id=customization_id
        )
        
        if result["success"]:
            # Store customized resume in Tigris
            customized_resume_path = f"resumes/user_{user_id}/customized/{resume_id}_{job_id}_{int(time.time())}.docx"
            diff_path = f"resumes/user_{user_id}/diff/{resume_id}_{job_id}_{int(time.time())}.html"
            
            # Save files to Tigris
            await store_file_to_tigris(result["customized_resume"], customized_resume_path)
            await store_file_to_tigris(result["diff_html"], diff_path)
            
            # Update database
            db.execute(
                update(CustomizationModel)
                .where(CustomizationModel.id == customization_id)
                .values(
                    status="completed",
                    customized_resume_path=customized_resume_path,
                    diff_path=diff_path,
                    detailed_status=json.dumps({
                        "analysis": result["analysis"],
                        "plan": result["plan"],
                        "verification": result["verification"]
                    }),
                    completed_at=datetime.utcnow()
                )
            )
            db.commit()
        else:
            # Update database with error
            db.execute(
                update(CustomizationModel)
                .where(CustomizationModel.id == customization_id)
                .values(
                    status="failed",
                    detailed_status=json.dumps({"error": result["error"]}),
                    completed_at=datetime.utcnow()
                )
            )
            db.commit()
    except Exception as e:
        logfire.error(f"Customization failed: {str(e)}", exc_info=True)
        
        # Update database with error
        db.execute(
            update(CustomizationModel)
            .where(CustomizationModel.id == customization_id)
            .values(
                status="failed",
                detailed_status=json.dumps({"error": str(e)}),
                completed_at=datetime.utcnow()
            )
        )
        db.commit()

def calculate_overall_progress(stage, percentage):
    """Calculate overall progress based on stage and percentage."""
    stage_weights = {
        "evaluation": 0.25,
        "planning": 0.25,
        "implementation": 0.35,
        "verification": 0.15
    }
    
    stage_order = ["evaluation", "planning", "implementation", "verification"]
    current_stage_index = stage_order.index(stage) if stage in stage_order else 0
    
    # Calculate progress from completed stages
    completed_progress = sum(
        stage_weights[stage_order[i]] 
        for i in range(current_stage_index)
    ) * 100
    
    # Add current stage contribution
    current_stage_progress = stage_weights.get(stage, 0) * percentage
    
    return round(completed_progress + current_stage_progress)
```

### Template Handling with python-docx-template

```python
from docxtpl import DocxTemplate
import io
import os

class TemplateProcessor:
    """Handles docx template processing for resume customization."""
    
    def __init__(self, templates_dir="resume_templates"):
        self.templates_dir = templates_dir
    
    async def get_template(self, template_id):
        """Get a template by its ID."""
        template_path = os.path.join(self.templates_dir, f"{template_id}.docx")
        if not os.path.exists(template_path):
            raise ValueError(f"Template {template_id} not found")
        return template_path
    
    async def apply_template(self, template_id, context_data):
        """Apply customized content to a template."""
        template_path = await self.get_template(template_id)
        
        # Create DocxTemplate from the template file
        doc = DocxTemplate(template_path)
        
        # Render the document with the context data
        doc.render(context_data)
        
        # Save to a byte stream
        output = io.BytesIO()
        doc.save(output)
        output.seek(0)
        
        return output
    
    async def parse_resume_to_context(self, resume_content, structure=None):
        """Parse resume content into context data for templates."""
        # In a production system, this would extract structured data
        # For now, we'll use a simplified approach with sections
        
        sections = {}
        current_section = "header"
        sections[current_section] = []
        
        for line in resume_content.split("\n"):
            line = line.strip()
            if not line:
                continue
                
            # Check if this is a section header
            if line.isupper() or line.endswith(":"):
                current_section = line.lower().replace(":", "").strip()
                sections[current_section] = []
            else:
                sections[current_section].append(line)
        
        # Convert lists to strings
        for section, lines in sections.items():
            sections[section] = "\n".join(lines)
        
        return sections
```

### WebSocket Manager for Progress Updates

```python
class WebSocketManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        self.active_connections = {}
    
    def register(self, customization_id, websocket):
        """Register a WebSocket connection for a customization ID."""
        if customization_id not in self.active_connections:
            self.active_connections[customization_id] = []
        self.active_connections[customization_id].append(websocket)
    
    def remove(self, customization_id, websocket):
        """Remove a WebSocket connection."""
        if customization_id in self.active_connections:
            if websocket in self.active_connections[customization_id]:
                self.active_connections[customization_id].remove(websocket)
            if not self.active_connections[customization_id]:
                del self.active_connections[customization_id]
    
    async def send_json(self, customization_id, data):
        """Send JSON data to all connected WebSockets for a customization."""
        if customization_id not in self.active_connections:
            return
            
        # Create a copy of connections to avoid modification during iteration
        connections = self.active_connections[customization_id].copy()
        
        for websocket in connections:
            try:
                await websocket.send_json(data)
            except Exception as e:
                logfire.error(f"WebSocket send failed: {str(e)}")
                # Remove the failed connection
                self.remove(customization_id, websocket)
```

## Error Handling Strategy

1. **PydanticAI Model Retries**: Configure retry count=2 for the Claude model
2. **Validation Gates**: Implement validators at each workflow stage
3. **Exception Handling**: Catch and log exceptions with logfire
4. **User Feedback**: Report detailed error status via WebSocket
5. **Database Updates**: Store error details in the customization record
6. **Process Isolation**: Run customization in background tasks to isolate failures

## Testing Plan

1. **Unit Tests**
   - Test each stage function individually with mock responses
   - Verify validation logic for each stage
   - Test WebSocket communication with mock connections
   - Test template processing with sample templates
   
2. **Integration Tests**
   - Test end-to-end workflow with sample resumes and job descriptions
   - Verify progress reporting through all stages
   - Test error handling with simulated failures
   - Test database and storage interactions
   
3. **UI Tests**
   - Test WebSocket connection and progress display
   - Verify diff view rendering
   - Test template selection and preview
   - Test download of customized resume

## Deployment Considerations

1. **Environment Variables**
   - `ANTHROPIC_API_KEY`: For Claude 3.7 Sonnet access
   - `TIGRIS_API_KEY`: For object storage
   - `ENVIRONMENT`: production/development for logging configuration

2. **Fly.io Configuration**
   - Configure LiteFS for distributed SQLite
   - Configure Tigris for object storage
   - Set appropriate memory allocation for AI processing

3. **Resource Requirements**
   - Minimum 2GB RAM for AI processing
   - Appropriate storage quotas for templates and user files
   - Consider request timeouts for longer customization jobs

## Implementation Phases

1. **Phase 1: Core Infrastructure**
   - Set up database schema on LiteFS
   - Configure Tigris object storage
   - Implement basic PydanticAI integration
   - Create WebSocket manager

2. **Phase 2: Resume Customization Pipeline**
   - Implement four-stage workflow
   - Add validation and error handling
   - Create template processing system
   - Build progress reporting

3. **Phase 3: API and Frontend Integration**
   - Build FastAPI endpoints
   - Implement WebSocket communication
   - Create diff view generation
   - Add template selection and preview

4. **Phase 4: Testing and Optimization**
   - Comprehensive test suite
   - Performance optimization
   - Error handling improvements
   - User experience refinement