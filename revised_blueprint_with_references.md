# Revised Blueprint with Dependencies and References

This blueprint includes specific references to `spec.md` and the `pydanticai_notes/` documentation to guide implementation. The prompts direct the implementing agent to refer to these resources for detailed guidance.

## Phase 1: PydanticAI Foundation and Schema Models

### Step 1: PydanticAI Schema Models [INDEPENDENT]
**Dependencies:** None - This is a foundation step that can be started immediately
**Can be worked on in parallel with:** Step 2 (PydanticAI Core Integration), Step 3 (WebSocket Manager)

**Prompt:**
```
Create the core PydanticAI schema models that will drive the four-stage resume customization workflow. Follow the evaluator-optimizer pattern and the data models specified in spec.md.

1. First, review these reference materials:
   - The Core Schema Models section in spec.md (lines 45-75) which defines ResumeAnalysis, CustomizationPlan, and VerificationResult models
   - pydanticai_notes/06_schema_models.md for guidance on effective model design
   - pydanticai_notes/03_evaluator_optimizer_pattern.md to understand how these models support the pattern

2. Create app/schemas/pydanticai_models.py with these Pydantic models:
   - ResumeAnalysis: Model for evaluation stage (match_score, key_matches, missing_skills, strengths, weaknesses, section_analysis)
   - CustomizationPlan: Model for planning stage (target_score, section_changes, keywords_to_add, format_improvements, change_explanations)
   - ImplementationResult: Model for implementation stage results
   - VerificationResult: Model for verification stage (is_truthful, issues, final_score, improvement, section_assessments)
   - EvidenceItem: Model for tracking truthfulness of resume claims

3. Add proper field validation as described in pydanticai_notes/13_validation_and_self_correction.md:
   - Scores should be between 0-100
   - Each field should have clear descriptions to guide the AI
   - Include example values to help the model generate appropriate outputs

4. Create a WebSocketProgressUpdate model for real-time progress reporting based on the progress calculation in spec.md (lines 765-786):
   - Fields for stage, percentage, message, and overall_progress
   - Include validation for stage values matching the four stages of the workflow

Ensure all models include detailed docstrings and type annotations following the examples in spec.md. The models should be structured to guide the AI through each stage of the four-stage workflow (Evaluation → Planning → Implementation → Verification).
```

### Step 2: PydanticAI Core Integration [INDEPENDENT]
**Dependencies:** None - Can be started immediately
**Can be worked on in parallel with:** Step 1 (Schema Models), Step 3 (WebSocket Manager)

**Prompt:**
```
Implement the core PydanticAI integration for the ResumeAIAssistant application, building on the existing configuration in app/core/config.py.

1. First, review these reference materials:
   - The ResumeCustomizer class in spec.md (lines 155-498) which demonstrates the integration approach
   - pydanticai_notes/01_overview.md for the fundamental concepts
   - pydanticai_notes/02_agent_api.md for details on Agent configuration
   - pydanticai_notes/10_agent_configuration.md for model configuration best practices

2. Create app/services/pydanticai_service.py with:
   - Base Agent configuration for Claude 3.7 Sonnet following examples in spec.md
   - Implementation of the evaluator-optimizer pattern as described in pydanticai_notes/03_evaluator_optimizer_pattern.md
   - Output validation with ModelRetry as shown in spec.md lines 258-267 and pydanticai_notes/13_validation_and_self_correction.md
   - Logfire integration for tracing following pydanticai_notes/14_tracing_and_observability.md

3. Update app/core/config.py to properly configure PydanticAI:
   - Configure thinking capability for Claude 3.7 models (see lines 121-130 in spec.md)
   - Set appropriate temperature and token limits per spec.md guidance
   - Use Claude 3.7 Sonnet as the primary model
   - Ensure fallback model configuration is in place

4. Create app/services/thinking_budget.py based on pydanticai_notes/11_dependency_injection.md:
   - ThinkingBudget class to manage token allocation
   - Methods to distribute tokens across the four workflow stages
   - Functions to track and log token usage

5. Create app/services/evidence_tracker.py:
   - EvidenceTracker class to validate truthfulness
   - Methods to extract facts from the original resume
   - Functions to verify changes against original content
   - Integration with the validation steps from spec.md lines 408-462

Include comprehensive logging throughout using logfire as shown in spec.md, and implement proper error handling for API failures. Follow the patterns in pydanticai_notes/04_error_handling.md to ensure robust operation.
```

## Phase 2: WebSocket Progress Reporting

### Step 3: WebSocket Manager Implementation [INDEPENDENT]
**Dependencies:** None - Can be started immediately
**Can be worked on in parallel with:** Step 1 (Schema Models), Step 2 (PydanticAI Core)

**Prompt:**
```
Implement the WebSocket-based progress reporting system to provide real-time updates during the resume customization process, following the pattern described in spec.md.

1. First, review these reference materials:
   - The WebSocketManager class in spec.md (lines 857-892)
   - The progress calculation function in spec.md (lines 765-786)
   - pydanticai_notes/05_progress_reporting.md for guidance on effective progress tracking
   - pydanticai_notes/12_streaming_implementation.md for streaming patterns

2. Create app/services/websocket_manager.py following the implementation in spec.md:
   - WebSocketManager class with active_connections dictionary
   - register(), remove(), and send_json() methods
   - Connection tracking by customization_id
   - Error handling for disconnections

3. Enhance app/api/endpoints/progress.py with a WebSocket endpoint:
   - Follow the pattern in spec.md lines 566-605
   - Implement authentication validation
   - Add connection management
   - Include a heartbeat mechanism

4. Create app/services/progress_tracker.py:
   - ProgressTracker class following the pattern in spec.md
   - Implement the stage-based calculation from spec.md lines 765-786
   - Methods to format and broadcast progress updates
   - Support for the four workflow stages

5. Add to app/schemas/progress.py:
   - WebSocketProgressUpdate schema model
   - StageProgress model with validation
   - Overall progress calculation logic

Ensure all components handle errors gracefully and provide meaningful feedback to users. The progress reporting should accurately track the four stages of the workflow as defined in spec.md (Evaluation → Planning → Implementation → Verification).
```

## Phase 3: Four-Stage Workflow Implementation

### Step 4: Evaluation Stage Implementation [DEPENDENT]
**Dependencies:** Step 1 (Schema Models), Step 2 (PydanticAI Core)
**Can be worked on in parallel with:** Step 3 (WebSocket Manager)

**Prompt:**
```
Implement the first stage of the four-stage workflow: evaluation. This stage analyzes how well a resume matches a job description as defined in spec.md.

1. First, review these reference materials:
   - The Evaluation stage description in spec.md (lines 23-26)
   - The _evaluate_resume method in spec.md (lines 246-292)
   - pydanticai_notes/03_evaluator_optimizer_pattern.md for the evaluator role
   - pydanticai_notes/13_validation_and_self_correction.md for output validation

2. Create app/services/claude_code/resume_evaluator.py:
   - ResumeEvaluator class following the pattern in spec.md
   - evaluate_resume method returning a ResumeAnalysis object
   - Integration with evidence_tracker to establish baseline facts
   - Section-by-section analysis as shown in spec.md

3. Implement the Agent configuration following spec.md lines 249-256:
   - Use Claude 3.7 Sonnet model
   - Configure ResumeAnalysis as the output_type
   - Use the system prompt from spec.md

4. Add output validation as shown in spec.md lines 258-267:
   - Validate match_score is between 0-100
   - Ensure at least 3 strengths are identified
   - Require at least 2 weaknesses/improvement areas

5. Use the prompt template from spec.md lines 269-287, which includes:
   - Instructions for analyzing the resume against the job description
   - Request for key skills matching and missing
   - Analysis of strengths and weaknesses
   - Section-by-section evaluation

Include comprehensive error handling with logfire as shown in spec.md lines 290-292. Ensure all code follows the patterns established in the specification and pydanticai_notes documentation.
```

### Step 5: Planning Stage Implementation [DEPENDENT]
**Dependencies:** Step 4 (Evaluation Stage)
**Can be worked on in parallel with:** Step 6 (Implementation Stage) if using mock evaluation results

**Prompt:**
```
Implement the second stage of the four-stage workflow: planning. This stage creates a strategic plan for resume improvements based on the evaluation results.

1. First, review these reference materials:
   - The Planning stage description in spec.md (lines 28-31)
   - The _create_plan method in spec.md (lines 294-351)
   - pydanticai_notes/03_evaluator_optimizer_pattern.md for the optimizer role
   - pydanticai_notes/13_validation_and_self_correction.md for validation techniques

2. Create app/services/claude_code/resume_planner.py:
   - ResumePlanner class following the pattern in spec.md
   - plan_customization method taking ResumeAnalysis and returning CustomizationPlan
   - Logic to prioritize changes based on impact as described in spec.md
   - Functions to ensure the plan addresses evaluation gaps

3. Implement the Agent configuration following spec.md lines 302-309:
   - Use Claude 3.7 Sonnet model
   - Configure CustomizationPlan as the output_type
   - Use the system prompt from spec.md

4. Add output validation as shown in spec.md lines 311-323:
   - Ensure target_score is higher than current match_score
   - Require changes for at least 2 sections
   - Validate that a sufficient number of missing keywords are addressed

5. Use the prompt template from spec.md lines 325-346, which includes:
   - Instructions for creating a strategic customization plan
   - Including the original analysis results
   - Requirements for specific section changes
   - Emphasis on truthfulness maintenance

Include comprehensive error handling with logfire as shown in spec.md lines 349-351. Ensure all code follows the patterns established in the specification and pydanticai_notes documentation.
```

### Step 6: Implementation Stage [DEPENDENT]
**Dependencies:** Step 5 (Planning Stage)
**Can be worked on in parallel with:** Step 7 (Verification Stage) if using mock plans and implementations

**Prompt:**
```
Implement the third stage of the four-stage workflow: implementation. This stage applies the planned changes to the resume to create a customized version.

1. First, review these reference materials:
   - The Implementation stage description in spec.md (lines 33-36)
   - The _implement_changes method in spec.md (lines 353-406)
   - The TemplateProcessor class in spec.md (lines 796-851)
   - pydanticai_notes/03_evaluator_optimizer_pattern.md for implementation patterns

2. Create app/services/claude_code/resume_implementer.py:
   - ResumeImplementer class following the pattern in spec.md
   - implement_changes method taking CustomizationPlan and returning a customized resume
   - Functions to track all modifications made to each section
   - Integration with EvidenceTracker to maintain truthfulness

3. Implement the Agent configuration following spec.md lines 365-372:
   - Use Claude 3.7 Sonnet model
   - Configure appropriate output_type
   - Use the system prompt from spec.md

4. Use the prompt template from spec.md lines 374-398, which includes:
   - Instructions for customizing the resume according to the plan
   - References to the original resume, job description, and improvement plan
   - Requirements for maintaining truthfulness
   - Template application guidance

5. Create or enhance app/services/export_service.py with template processing, following spec.md lines 796-851:
   - TemplateProcessor class for handling docx templates
   - Methods to apply templates to customized content
   - Functions to parse resume content into template context

Include comprehensive error handling with logfire as shown in spec.md. Ensure all code follows the patterns established in the specification and pydanticai_notes documentation, particularly regarding truthfulness maintenance and template application.
```

### Step 7: Verification Stage [DEPENDENT]
**Dependencies:** Step 6 (Implementation Stage)
**Can be worked on in parallel with:** Step 9 (Frontend Integration) if mock verification results are used

**Prompt:**
```
Implement the fourth and final stage of the workflow: verification. This stage validates the truthfulness and quality of the customized resume.

1. First, review these reference materials:
   - The Verification stage description in spec.md (lines 38-41)
   - The _verify_customization method in spec.md (lines 408-462)
   - The _generate_diff method in spec.md (lines 464-497)
   - pydanticai_notes/13_validation_and_self_correction.md for verification techniques

2. Create app/services/claude_code/resume_verifier.py:
   - ResumeVerifier class following the pattern in spec.md
   - verify_customization method returning VerificationResult
   - Integration with the EvidenceTracker for truthfulness validation
   - Functions to calculate improvement metrics and final scores

3. Implement the Agent configuration following spec.md lines 416-423:
   - Use Claude 3.7 Sonnet model
   - Configure VerificationResult as the output_type
   - Use the system prompt from spec.md

4. Add output validation as shown in spec.md lines 425-434:
   - Ensure consistency between is_truthful flag and issues list
   - Validate final_score is between 0-100
   - Verify other constraints on the verification result

5. Use the prompt template from spec.md lines 436-457, which includes:
   - Instructions for verifying truthfulness
   - Comparison between original and customized resumes
   - Final score calculation
   - Assessment of improvement

6. Enhance app/services/diff_service.py following spec.md lines 464-497:
   - DiffGenerator class that produces visual diffs
   - Methods for line-by-line and section-by-section comparison
   - HTML diff view generation with highlighting for changes

Include comprehensive error handling with logfire as shown in spec.md. Ensure all code follows the patterns established in the specification and pydanticai_notes documentation.
```

## Phase 4: Integration and API Endpoints

### Step 8: Resume Customizer Executor [DEPENDENT]
**Dependencies:** Steps 1-7 (All previous implementation steps)
**Can be worked on in parallel with:** Step 9 (Frontend Integration) using mock endpoints

**Prompt:**
```
Implement the ResumeCustomizer executor class that orchestrates the four-stage workflow following the implementation in spec.md.

1. First, review these reference materials:
   - The complete ResumeCustomizer class in spec.md (lines 164-498)
   - The Background Task Processing section in spec.md (lines 661-786)
   - pydanticai_notes/11_dependency_injection.md for RunContext integration
   - pydanticai_notes/14_tracing_and_observability.md for logfire integration

2. Create app/services/claude_code/executor.py with the ResumeCustomizer class:
   - Implement the class matching spec.md (lines 164-498)
   - Include the four-stage workflow methods (evaluation, planning, implementation, verification)
   - Add WebSocket progress updates via progress_callback
   - Implement comprehensive error handling and recovery
   - Include diff generation after customization

3. Create app/services/claude_code/log_streamer.py:
   - Based on pydanticai_notes/12_streaming_implementation.md
   - Implement token-by-token streaming for progress visibility
   - Track token usage for monitoring
   - Format and send updates via WebSocket

4. Create or enhance app/api/endpoints/claude_code.py with endpoints:
   - Following the API Endpoints section in spec.md (lines 502-657)
   - POST /customize/resume endpoint using ResumeCustomizer
   - Background task processing as shown in spec.md (lines 661-763)
   - GET /customize/status/{id} endpoint for checking status

5. Ensure end-to-end integration between all components:
   - Set up logfire spans for tracing as shown in spec.md
   - Connect all stages of the workflow
   - Implement progress reporting and database status updates
   - Add persistent storage for results

Follow the complete implementation in spec.md, particularly the customize_resume method (lines 178-239) which orchestrates the entire workflow. Ensure proper error handling, database updates, and WebSocket communication throughout.
```

### Step 9: Frontend Integration [PARTIALLY DEPENDENT]
**Dependencies:** Step 3 (WebSocket Manager), Step 8 (Resume Customizer Executor)
**Can be worked on in parallel with:** Step 7 (Verification Stage), Step 8 (Resume Customizer) with mock data

**Prompt:**
```
Update the frontend components to support the enhanced PydanticAI-based resume customization flow with WebSocket progress updates and improved diff views.

1. First, review these reference materials:
   - The WebSocket connection handling in spec.md (lines 566-605)
   - The progress calculation in spec.md (lines 765-786)
   - The Overall Progress tracking described in spec.md

2. Update nextjs-frontend/components/customize-resume.tsx:
   - Add WebSocket connection following the pattern in spec.md
   - Implement progress bar with the four stages from spec.md
   - Display detailed status messages
   - Add customization options based on the API

3. Enhance nextjs-frontend/components/resume-diff-view.tsx:
   - Implement side-by-side comparison
   - Add highlighting for additions and removals
   - Include section-by-section comparison
   - Add explanations from the CustomizationPlan

4. Create or update nextjs-frontend/components/customization-details.tsx:
   - Display metrics from evaluation and verification stages
   - Show match score improvements
   - Present a summary of changes made
   - Add export options

5. Update nextjs-frontend/lib/client.ts:
   - Add methods for the new PydanticAI endpoints
   - Implement WebSocket connection handling
   - Add functions for downloading and exporting

Focus on providing a smooth user experience with real-time updates and clear visualization of the customization process. The frontend should accurately represent the four-stage workflow and provide detailed insights into the changes made to the resume.
```

## Phase 5: Testing and Enhancement

### Step 10: Comprehensive Testing [DEPENDENT]
**Dependencies:** Steps 1-9 (All previous implementation steps)
**Can be worked on in parallel with:** None - Requires complete implementation

**Prompt:**
```
Implement comprehensive testing for the PydanticAI integration, following the Testing Plan section in spec.md (lines 903-921).

1. First, review these reference materials:
   - The Testing Plan in spec.md (lines 903-921)
   - pydanticai_notes/04_error_handling.md for testing error scenarios
   - pydanticai_notes/07_best_practices.md for testing best practices

2. Create unit tests for each component:
   - Test schema models validation and examples
   - Test evidence tracking and verification
   - Test each workflow stage (evaluation, planning, implementation, verification)
   - Test WebSocket communication
   - Test template processing

3. Create integration tests according to spec.md:
   - Test end-to-end workflow with sample data
   - Verify progress reporting
   - Test error handling scenarios
   - Test database and storage interactions

4. Add UI tests following spec.md:
   - Test WebSocket connection and progress display
   - Verify diff view rendering
   - Test template selection and preview
   - Test download functionality

5. Create test helpers and fixtures:
   - Sample resumes and job descriptions
   - Mock AI responses for predictable testing
   - WebSocket client for testing

Ensure tests are comprehensive and cover normal operation, edge cases, and error scenarios. Follow the testing approach outlined in spec.md and best practices from pydanticai_notes.
```

### Step 11: Final Documentation and Refinement [DEPENDENT]
**Dependencies:** Steps 1-10 (All previous implementation steps)
**Can be worked on in parallel with:** None - Requires complete implementation and testing

**Prompt:**
```
Complete the PydanticAI integration with comprehensive documentation and final refinements, following the best practices in spec.md and pydanticai_notes.

1. First, review these reference materials:
   - The Deployment Considerations in spec.md (lines 923-939)
   - pydanticai_notes/07_best_practices.md for documentation standards
   - pydanticai_notes/14_tracing_and_observability.md for monitoring best practices

2. Update documentation:
   - Add detailed docstrings to all classes and methods
   - Create API documentation for all endpoints
   - Document the WebSocket protocol and message format
   - Create a developer guide for extending the system
   - Add usage examples for the ResumeCustomizer

3. Implement monitoring and observability:
   - Following pydanticai_notes/14_tracing_and_observability.md
   - Add comprehensive logging throughout the system
   - Implement metrics collection for performance monitoring
   - Add tracing for debugging and optimization

4. Optimize performance:
   - Profile the system to identify bottlenecks
   - Implement caching where appropriate
   - Optimize database queries and API calls
   - Fine-tune PydanticAI configuration

5. Enhance error handling:
   - Implement robust error handling for Claude API calls
   - Add graceful degradation paths for component failures
   - Improve error messages for better user experience

6. Prepare for deployment:
   - Configure environment variables as specified in spec.md
   - Set up resource requirements following spec.md guidance
   - Document deployment procedures

The final system should be robust, well-documented, and ready for production use, with comprehensive monitoring and error handling as described in spec.md and pydanticai_notes documentation.
```

## Parallel Development Workflow

For optimal development efficiency, the following parallel tracks can be established:

### Track 1: Schema and Service Foundation
- Step 1: PydanticAI Schema Models
- Step 2: PydanticAI Core Integration
- Step 4: Evaluation Stage Implementation (after Steps 1-2)

### Track 2: WebSocket and Frontend
- Step 3: WebSocket Manager Implementation
- Step 9: Frontend Integration (can start UI components that don't require backend integration)

### Track 3: Workflow Stages
- Step 5: Planning Stage Implementation (after Step 4)
- Step 6: Implementation Stage (after Step 5)
- Step 7: Verification Stage (after Step 6)

### Track 4: Integration
- Step 8: Resume Customizer Executor (after all workflow stages)
- Complete Frontend Integration (after backend is ready)

### Track 5: Testing and Documentation
- Step 10: Comprehensive Testing (after implementation)
- Step 11: Final Documentation (after testing)

Many components can be developed with mock implementations of their dependencies to enable parallel development. For example, frontend work can begin with mocked API responses before the actual backend is complete.
