# PydanticAI Best Practices for Resume Customization

This document outlines best practices for using PydanticAI in the resume customization service redesign.

## Architecture Recommendations

1. **Use the Evaluator-Optimizer Pattern**
   - Separate evaluation from optimization
   - Create distinct models and agents for each step of the workflow
   - Break complex tasks into manageable subtasks

2. **Standardize on a Single Model**
   - Use Claude 3.7 Sonnet as the standard model for consistency
   - Remove complex model selection and fallback logic
   - Focus on implementing robust error handling instead

3. **Implement Robust Error Handling**
   - Set appropriate timeouts for each workflow stage
   - Use try/except blocks around all agent executions
   - Log detailed error information with logfire
   - Consider implementing circuit breakers for external API calls

4. **Focus on Truthfulness**
   - Implement evidence extraction and tracking
   - Verify all customizations against the original resume
   - Create well-structured verification models
   - Include specific prompts about maintaining truthfulness

5. **Enable Progress Reporting**
   - Implement WebSocket-based progress tracking
   - Update progress at key points in the workflow
   - Provide meaningful status messages to users
   - Design the UI to reflect current processing stage

## Implementation Guidelines

### Agent Factory

Create a simplified AgentFactory for consistent agent creation:

```python
class AgentFactory:
    """Creates PydanticAI agents for resume customization tasks."""
    
    def __init__(self):
        # Use a single model for all tasks
        self.model = "anthropic:claude-3-7-sonnet-latest"
        
    async def create_agent(self, output_schema, system_prompt=None, timeout=60):
        """Create an agent with the Claude model."""
        try:
            # Create the agent with Claude 3.7 Sonnet
            agent = Agent(
                model=self.model,
                output_type=output_schema,
                system_prompt=system_prompt
            )
            
            return agent
        except Exception as e:
            logfire.error(f"Error creating agent: {str(e)}")
            raise AgentCreationError(f"Failed to create agent: {str(e)}")
            
    async def run_agent(self, agent, prompt, timeout=60):
        """Run an agent with the provided prompt."""
        try:
            # Run the agent
            result = await agent.run(prompt, timeout=timeout)
            return result
        except Exception as e:
            logfire.error(f"Agent execution failed: {str(e)}")
            raise AgentExecutionError(f"Agent execution failed: {str(e)}")
```

### Effective Prompting

Structure your prompts for optimal results:

```python
def create_evaluation_prompt(resume_content, job_description):
    return f"""
    You're a professional resume evaluator with expertise in analyzing how well
    resumes match specific job descriptions.
    
    RESUME:
    {resume_content}
    
    JOB DESCRIPTION:
    {job_description}
    
    TASK:
    Thoroughly evaluate how well this resume matches the job description.
    
    FOCUS ON:
    1. Overall match (0-100% score)
    2. Section-by-section assessment
    3. Keyword matching
    4. Strengths relative to job requirements
    5. Gaps and areas for improvement
    
    INSTRUCTIONS:
    - Be specific and detailed
    - Support assessments with evidence from the resume and job description
    - Assess both content and presentation
    - Prioritize essential job requirements in your evaluation
    - Identify both obvious and subtle gaps
    
    Provide a structured, comprehensive evaluation.
    """
```

### Custom Exceptions

Create custom exceptions for better error handling:

```python
class CustomizationError(Exception):
    """Base exception for resume customization errors."""
    pass

class AgentCreationError(CustomizationError):
    """Raised when agent creation fails."""
    pass

class AgentExecutionError(CustomizationError):
    """Raised when agent execution fails."""
    pass

class EvaluationError(CustomizationError):
    """Raised when resume evaluation fails."""
    pass

class PlanningError(CustomizationError):
    """Raised when improvement planning fails."""
    pass

class ImplementationError(CustomizationError):
    """Raised when customization implementation fails."""
    pass

class VerificationError(CustomizationError):
    """Raised when verification fails."""
    pass
```

## Complete 4-Stage Workflow Example

```python
class ResumeCustomizer:
    """Customizes resumes for job descriptions using AI."""
    
    def __init__(
        self,
        agent_factory=None,
        evidence_tracker=None,
        progress_reporter=None
    ):
        self.agent_factory = agent_factory or AgentFactory()
        self.evidence_tracker = evidence_tracker or EvidenceTracker()
        self.progress_reporter = progress_reporter
        
    async def customize_resume(self, resume_content, job_description):
        """Customize a resume for a specific job description."""
        # Start progress reporting
        if self.progress_reporter:
            await self.progress_reporter.start_reporting()
            
        try:
            # Stage 1: Evaluation
            evaluation_result = await self._evaluate_resume_job_match(
                resume_content, 
                job_description
            )
            
            # Stage 2: Planning
            improvement_plan = await self._generate_improvement_plan(
                resume_content,
                job_description,
                evaluation_result
            )
            
            # Stage 3: Implementation
            customized_resume = await self._implement_customizations(
                resume_content,
                job_description,
                improvement_plan
            )
            
            # Stage 4: Verification
            verification_result = await self._verify_customization(
                resume_content,
                customized_resume,
                job_description
            )
            
            # Create final result
            result = {
                "customized_resume": customized_resume,
                "original_resume": resume_content,
                "evaluation": evaluation_result,
                "improvement_plan": improvement_plan,
                "verification_result": verification_result,
                "success": True
            }
            
            # Complete progress reporting
            if self.progress_reporter:
                await self.progress_reporter.complete_reporting(success=True)
                
            return result
        except Exception as e:
            logfire.error(f"Error during resume customization: {str(e)}")
            
            # Complete progress reporting
            if self.progress_reporter:
                await self.progress_reporter.complete_reporting(success=False)
                
            # Re-raise or return error info
            raise CustomizationError(f"Resume customization failed: {str(e)}")
            
    async def _evaluate_resume_job_match(self, resume_content, job_description):
        """Stage 1: Evaluate how well the resume matches the job description."""
        # Implementation details
        
    async def _generate_improvement_plan(self, resume_content, job_description, evaluation_result):
        """Stage 2: Generate a plan for improving the resume."""
        # Implementation details
        
    async def _implement_customizations(self, resume_content, job_description, improvement_plan):
        """Stage 3: Implement the planned customizations."""
        # Implementation details
        
    async def _verify_customization(self, original_resume, customized_resume, job_description):
        """Stage 4: Verify the truthfulness of customizations."""
        # Implementation details
```

By following these best practices, the resume customization service will be more reliable, maintainable, and effective.