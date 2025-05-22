# ResumeAIAssistant Project Blueprint

## Phase 1: Foundation Setup

### Step 1: Project Structure and Basic Dependencies

**Prompt:**
```
Create the basic project structure for a ResumeAIAssistant application using FastAPI and PydanticAI. Set up the following:

1. Create a `pyproject.toml` file with the necessary dependencies:
   - FastAPI
   - Uvicorn
   - SQLAlchemy
   - PydanticAI
   - Anthropic Python SDK
   - python-docx-template
   - python-multipart
   - logfire
   - python-jose[cryptography] for JWT
   - passlib[bcrypt] for password hashing

2. Initialize the basic project structure with these directories:
   - app/
     - api/
       - endpoints/
     - core/
     - db/
     - models/
     - schemas/
     - services/
   - tests/
     - unit/
     - integration/

3. Create a main.py file at the root that will serve as the entry point

4. Set up the basic FastAPI application with CORS enabled and include a simple health check endpoint at GET /health that returns {"status": "ok"}

5. Write a simple test for the health check endpoint to verify the setup.

Implement this with clean code following Python best practices including proper typing and docstrings.
```

### Step 2: Core Configuration

**Prompt:**
```
Create the core configuration system for the ResumeAIAssistant application:

1. Implement app/core/config.py with:
   - Settings class using Pydantic BaseSettings
   - Environment variable loading
   - Configuration for:
     - API keys (ANTHROPIC_API_KEY)
     - JWT Secret key (auto-generated if not provided)
     - Database URL (default to SQLite)
     - CORS settings
     - Logging configuration

2. Create app/core/logging.py with:
   - Logfire integration
   - Standard logging setup for non-AI components
   - Log formatter configuration

3. Create a .env.example file with all necessary environment variables documented

4. Create a simple test in tests/unit/ to verify that the configuration loads correctly from environment variables.

Ensure proper error handling for missing critical configuration (like API keys) and provide helpful error messages.
```

### Step 3: Database Setup

**Prompt:**
```
Implement the database foundation for the ResumeAIAssistant application:

1. Create app/db/base.py with:
   - SQLAlchemy Base class definition
   - Mixin classes for common fields (id, created_at, updated_at)

2. Create app/db/session.py with:
   - Database engine configuration
   - SessionLocal factory
   - get_db dependency function for FastAPI endpoints

3. Write a basic test to verify database connection and session creation.

4. Create basic data models in app/models/:
   - user.py: User model with email, hashed_password, is_active fields
   - resume.py: Resume model with user_id, title, content, created_at fields
   - job.py: Job model with user_id, title, description, url, created_at fields
   - customization.py: Customization model linking resume_id, job_id, status, result fields

5. Implement a database initialization function that creates tables if they don't exist.

Ensure proper relationship definitions between models and add appropriate indexes for performance.
```

## Phase 2: Basic API and Schema Implementation

### Step 4: Authentication System

**Prompt:**
```
Implement a JWT-based authentication system for the ResumeAIAssistant application:

1. Create app/core/security.py with functions for:
   - Password hashing and verification
   - JWT token creation, validation, and refreshing
   - get_current_user dependency for protected endpoints

2. Create app/api/endpoints/auth.py with endpoints for:
   - POST /auth/register: User registration
   - POST /auth/login: Login with email/password to get JWT token
   - POST /auth/refresh: Refresh token
   - GET /auth/me: Get current user information

3. Create corresponding Pydantic schemas in app/schemas/user.py:
   - UserCreate
   - UserResponse
   - Token
   - TokenPayload

4. Implement a user repository in app/repositories/user.py with methods for:
   - create_user
   - get_user_by_email
   - get_user_by_id

5. Write tests for:
   - User registration endpoint
   - Login endpoint
   - Token validation
   - Protected endpoint access

Ensure proper error handling for duplicate emails, invalid credentials, and expired tokens.
```

### Step 5: Resume Management API

**Prompt:**
```
Implement the Resume Management API for the ResumeAIAssistant application:

1. Create app/repositories/resume.py with a ResumeRepository class that includes methods for:
   - create_resume
   - get_resume_by_id
   - get_resumes_by_user_id
   - update_resume
   - delete_resume

2. Create app/schemas/resume.py with Pydantic models:
   - ResumeCreate
   - ResumeUpdate
   - ResumeResponse
   - ResumeList

3. Create app/api/endpoints/resumes.py with endpoints for:
   - POST /resumes: Create a new resume
   - GET /resumes: List user's resumes
   - GET /resumes/{resume_id}: Get a specific resume
   - PUT /resumes/{resume_id}: Update a resume
   - DELETE /resumes/{resume_id}: Delete a resume

4. Add permissions checking to ensure users can only access their own resumes.

5. Write integration tests for each endpoint.

Implement pagination for the list endpoint and ensure proper error handling for not found and permission denied cases.
```

### Step 6: Job Management API

**Prompt:**
```
Implement the Job Management API for the ResumeAIAssistant application:

1. Create app/repositories/job.py with a JobRepository class that includes methods for:
   - create_job
   - get_job_by_id
   - get_jobs_by_user_id
   - update_job
   - delete_job

2. Create app/schemas/job.py with Pydantic models:
   - JobCreate
   - JobUpdate
   - JobResponse
   - JobList

3. Create app/api/endpoints/jobs.py with endpoints for:
   - POST /jobs: Create a new job
   - GET /jobs: List user's jobs
   - GET /jobs/{job_id}: Get a specific job
   - PUT /jobs/{job_id}: Update a job
   - DELETE /jobs/{job_id}: Delete a job

4. Add a POST /jobs/extract endpoint that extracts job details from a provided URL.

5. Implement a basic job_scraper.py service to extract job information from URLs.

6. Write integration tests for each endpoint.

Ensure proper validation for job URLs and error handling for scraping failures. Implement pagination for the list endpoint.
```

## Phase 3: PydanticAI Integration and Resume Customization

### Step 7: PydanticAI Model Schemas

**Prompt:**
```
Implement the PydanticAI model schemas for the resume customization process:

1. Create app/schemas/pydanticai_models.py with these Pydantic models for the AI workflow:
   - JobAnalysis: Schema for job description analysis
   - ResumeAnalysis: Schema for resume analysis
   - CustomizationPlan: Schema for planning resume changes
   - SectionChange: Schema for tracking changes to resume sections
   - ImplementationResult: Schema for the implementation results
   - VerificationResult: Schema for verification results
   - EvidenceItem: Schema for tracking evidence of resume claims
   - ProgressUpdate: Schema for progress updates

2. Add validators and examples to each model to guide the AI.

3. Create app/schemas/requirements.py with models for extracting job requirements:
   - JobRequirement
   - RequirementsList
   - RequirementType enum (SKILL, EDUCATION, EXPERIENCE, etc.)

4. Create tests that verify these models work correctly with sample data.

Each model should include detailed field descriptions and type annotations to guide the AI in generating proper outputs.
```

### Step 8: PydanticAI Service Integration

**Prompt:**
```
Implement the core PydanticAI integration for the ResumeAIAssistant:

1. Create app/services/pydanticai_service.py with:
   - Configuration for PydanticAI with Claude 3.7 Sonnet
   - Function to initialize PydanticAI with proper system messages
   - Basic error handling and retry logic
   - Streaming response handling

2. Create app/services/model_selector.py to handle model selection:
   - Function to select appropriate model based on task complexity
   - Default to Claude 3.7 Sonnet for all operations

3. Create app/services/thinking_budget.py with a ThinkingBudget class:
   - Methods to allocate tokens across customization stages
   - Functions to track token usage

4. Implement progress tracking helpers in app/services/progress_tracker.py:
   - ProgressTracker class for sending updates to clients
   - Functions to calculate percentage completed

5. Write unit tests for these components.

Ensure proper error handling for API failures and token budget management. Set up retry logic with appropriate backoff.
```

### Step 9: WebSocket Progress Reporting

**Prompt:**
```
Implement the WebSocket-based progress reporting system:

1. Create app/services/smart_request_handler.py with:
   - WebSocketManager class to manage WebSocket connections
   - Methods for sending progress updates to specific clients
   - Connection tracking by user_id and request_id

2. Create a WebSocket endpoint in app/api/api.py at /ws/{user_id}/{request_id}:
   - Connection handling with authentication
   - Integration with WebSocketManager
   - Heartbeat mechanism to keep connections alive

3. Implement a ConnectionManager in app/core/websocket.py:
   - Methods to add, remove, and get connections
   - Broadcasting to specific connections
   - Authentication validation

4. Create a simple client-side test script that connects to WebSocket and prints updates.

5. Write tests for WebSocket connection handling and message broadcasting.

Ensure proper error handling for disconnections and authentication failures. Implement message queue for offline clients.
```

### Step 10: Resume Analysis Implementation

**Prompt:**
```
Implement the resume analysis phase using PydanticAI:

1. Create app/services/section_analysis_service.py with:
   - ResumeAnalyzer class that breaks a resume into sections
   - Integration with PydanticAI for analyze_resume method
   - Functions to identify key skills, experiences, and education

2. Create specialized analyzers in app/services/section_analyzers/:
   - base.py: Base section analyzer with common functionality
   - experience_analyzer.py: Experience section analyzer
   - education_analyzer.py: Education section analyzer 
   - skills_analyzer.py: Skills section analyzer
   - achievement_analyzer.py: Achievements analyzer

3. Implement app/schemas/section_analyzers.py with models for section analysis results.

4. Create app/api/endpoints/analysis.py with a POST /analysis/resume endpoint.

5. Write comprehensive tests for the analysis service and specific analyzers.

Design the system to be extensible for future section types. Ensure proper error handling for malformed resume inputs.
```

### Step 11: Job Requirements Extraction

**Prompt:**
```
Implement the job requirements extraction service using PydanticAI:

1. Create app/services/requirements_extractor.py with:
   - RequirementsExtractor class that uses PydanticAI to extract requirements
   - Methods to categorize requirements by type
   - Functions to identify key skills, experience level, and qualifications

2. Implement app/api/endpoints/requirements.py with a POST /requirements/extract endpoint.

3. Add models to app/schemas/requirements.py for:
   - RequirementMatch (for matching resume to requirements)
   - JobRequirementResponse
   - RequirementCategory enum

4. Create app/services/job_scraper.py to extract job descriptions from URLs.

5. Write tests for requirements extraction with example job descriptions.

Implement proper validation for extracted requirements and ensure comprehensive extraction of both explicit and implicit job requirements.
```

## Phase 4: Resume Customization Core Functionality

### Step 12: Customization Planning

**Prompt:**
```
Implement the customization planning phase using PydanticAI:

1. Create app/services/customization_service.py with:
   - CustomizationPlanner class that takes job requirements and resume analysis
   - plan_customization method that generates a detailed plan using PydanticAI
   - Functions to prioritize changes based on impact

2. Create app/schemas/customize.py with models for:
   - CustomizationPlanRequest
   - CustomizationPlanResponse
   - PlannedChange
   - ChangeType enum

3. Implement app/api/endpoints/customize.py with:
   - POST /customize/plan endpoint that generates a customization plan
   - GET /customize/{customization_id} endpoint to retrieve a plan

4. Implement a database model for storing customization plans.

5. Write tests for plan generation with different resume and job combinations.

Ensure plans include justifications for each change and prioritize changes by potential impact. Include confidence scores for suggested changes.
```

### Step 13: Resume Customization Implementation

**Prompt:**
```
Implement the resume customization implementation phase using PydanticAI:

1. Enhance app/services/customization_service.py with:
   - CustomizationImplementer class that executes the customization plan
   - implement_changes method using PydanticAI to modify resume sections
   - Functions to track detailed changes to each section

2. Add to app/schemas/customize.py with models for:
   - CustomizationImplementationRequest
   - CustomizationImplementationResponse
   - ImplementedChange

3. Implement the evidence tracking system in app/services/evidence_tracker.py:
   - EvidenceTracker class that validates resume claims
   - Methods to extract and verify evidence from the original resume
   - Functions to flag potentially unverifiable changes

4. Add to app/api/endpoints/customize.py:
   - POST /customize/implement endpoint that implements a customization plan

5. Write tests for implementation with different customization plans.

Ensure implemented changes maintain truthfulness by referencing the EvidenceTracker. Implement proper error handling for changes that can't be implemented.
```

### Step 14: Verification and Export

**Prompt:**
```
Implement the verification and export functionality:

1. Enhance app/services/customization_service.py with:
   - CustomizationVerifier class that validates implemented changes
   - verify_customization method using PydanticAI to check results
   - Functions to calculate improvement metrics

2. Create app/services/export_service.py with:
   - ResumeExporter class for document generation
   - export_to_docx method using python-docx-template
   - export_to_pdf method (via docx conversion)

3. Implement app/api/endpoints/export.py with:
   - POST /export/docx endpoint that exports a customized resume
   - POST /export/pdf endpoint that exports as PDF

4. Add templates folder with docx templates for different resume styles.

5. Write tests for verification and export functionality.

Ensure exported documents maintain proper formatting. Implement template selection based on user preferences. Add watermarking for free tier users.
```

## Phase 5: Diff and ATS Optimization

### Step 15: Resume Diff Generation

**Prompt:**
```
Implement the resume diff generation service:

1. Create app/services/diff_service.py with:
   - DiffGenerator class that produces Git-style diffs
   - generate_diff method for comparing original and customized resumes
   - html_diff method for generating colored HTML diff
   - section_diff method for section-by-section comparison

2. Create app/schemas/diff.py with models for:
   - DiffRequest
   - DiffResponse
   - SectionDiff
   - ChangeExplanation

3. Implement app/api/endpoints/diff.py with:
   - POST /diff/generate endpoint that creates a diff
   - GET /diff/{customization_id} endpoint to retrieve a stored diff

4. Create tests for diff generation with different resume pairs.

Implement both line-by-line and semantic diffing. Include options for showing/hiding minor changes. Store diffs with customization results.
```

### Step 16: ATS Optimization Service

**Prompt:**
```
Implement the ATS (Applicant Tracking System) optimization service:

1. Create app/services/ats_service.py with:
   - ATSOptimizer class that evaluates resumes against job descriptions
   - analyze_ats_compatibility method using PydanticAI
   - keyword_matching function for identifying important keywords
   - score_calculation function for generating an ATS score

2. Create app/schemas/ats.py with models for:
   - ATSRequest
   - ATSResponse
   - KeywordMatch
   - ATSScore
   - OptimizationSuggestion

3. Implement app/api/endpoints/ats.py with:
   - POST /ats/analyze endpoint that analyzes ATS compatibility
   - POST /ats/optimize endpoint that suggests optimizations

4. Write comprehensive tests for ATS analysis with various resumes and jobs.

Include detailed metrics on keyword coverage, formatting issues, and overall ATS compatibility. Provide specific suggestions for improvement.
```

## Phase 6: Parallel Processing and Enhanced Functionality

### Step 17: Parallel Processing Implementation

**Prompt:**
```
Implement parallel processing for resume customization:

1. Create app/services/parallel_processor.py with:
   - ParallelProcessor class for concurrent section processing
   - process_sections method that distributes work across processors
   - aggregate_results method for combining parallel results

2. Enhance app/core/parallel_config.py with:
   - Configuration for max concurrent operations
   - Batch size settings
   - Timeout configurations

3. Create app/services/enhanced_parallel_processor.py with:
   - EnhancedParallelProcessor that extends ParallelProcessor
   - Advanced error handling and retry logic
   - Result validation checks

4. Update app/services/customization_service.py to use parallel processing.

5. Write performance tests comparing sequential vs parallel processing.

Implement proper concurrency control and error handling for parallel operations. Add monitoring for parallel processing efficiency.
```

### Step 18: Cover Letter Generation

**Prompt:**
```
Implement cover letter generation functionality:

1. Create app/services/cover_letter_service.py with:
   - CoverLetterGenerator class that uses PydanticAI
   - generate_cover_letter method that creates customized cover letters
   - Functions to incorporate resume highlights and job requirements

2. Create app/schemas/cover_letter.py with models for:
   - CoverLetterRequest
   - CoverLetterResponse
   - CoverLetterStyle enum
   - CoverLetterSection

3. Implement app/api/endpoints/cover_letter.py with:
   - POST /cover-letter/generate endpoint
   - GET /cover-letter/{id} endpoint

4. Add cover letter templates to the templates folder.

5. Write tests for cover letter generation with different styles.

Implement multiple cover letter styles (traditional, modern, specific industry). Ensure cover letters highlight the most relevant experience for each job.
```

## Phase 7: Integration and Polishing

### Step 19: Background Task Processing

**Prompt:**
```
Implement background task processing for long-running operations:

1. Create app/services/background_tasks.py with:
   - BackgroundTaskManager class for managing async tasks
   - Task status tracking functionality
   - Methods for canceling and retrieving task results

2. Create app/api/endpoints/tasks.py with:
   - POST /tasks/start endpoint to start a background task
   - GET /tasks/{task_id} endpoint to check task status
   - DELETE /tasks/{task_id} endpoint to cancel a task

3. Update customization endpoints to use background tasks.

4. Implement database models for task storage and retrieval.

5. Write tests for background task management.

Ensure proper cleanup of completed tasks. Implement task prioritization for premium users. Add task timeout handling to prevent stuck operations.
```

### Step 20: End-to-End Integration

**Prompt:**
```
Implement the end-to-end integration for the ResumeAIAssistant application:

1. Create app/services/claude_code/executor.py with the ResumeCustomizer class:
   - Four-stage workflow implementation (evaluation, planning, implementation, verification)
   - Progress tracking with WebSocket updates
   - Evidence tracking integration
   - Error handling and recovery

2. Create app/api/endpoints/claude_code.py with comprehensive endpoints for:
   - POST /customize/resume endpoint for end-to-end customization
   - WebSocket connection for progress updates
   - GET /customize/status/{id} endpoint for status checks

3. Implement app/services/claude_code/log_streamer.py for token-by-token streaming.

4. Update app/api/api.py to include all endpoints and WebSocket handlers.

5. Create end-to-end integration tests for the complete workflow.

Ensure seamless integration between all components. Implement comprehensive error handling and recovery. Add detailed logging for debugging and monitoring.
```

### Step 21: Final Testing and Documentation

**Prompt:**
```
Complete final testing and documentation for the ResumeAIAssistant application:

1. Create comprehensive tests covering:
   - Unit tests for all services
   - Integration tests for API endpoints
   - End-to-end tests for complete workflows
   - Performance tests for parallel processing

2. Update README.md with:
   - Project overview and features
   - Setup instructions
   - API documentation
   - Configuration options
   - Examples

3. Create CONTRIBUTING.md with development guidelines.

4. Add detailed docstrings and type hints to all functions.

5. Create sample data for demonstration purposes.

Ensure test coverage exceeds 90%. Document all API endpoints with examples. Include troubleshooting information and performance optimization tips.
```

This blueprint provides a detailed, step-by-step approach to building the ResumeAIAssistant project with PydanticAI. Each step builds incrementally on previous work, ensuring testability and maintainability throughout the development process. The prompts are designed to guide code generation in a test-driven manner, focusing on best practices and complete integration at each stage.