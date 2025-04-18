# PydanticAI Integration Plan for ResumeAIAssistant

This document outlines a comprehensive plan to migrate the ResumeAIAssistant from Anthropic's Claude API to a model-agnostic architecture using PydanticAI, leveraging its flexibility, type safety, and structured output validation.

## Table of Contents
1. [Current Architecture Analysis](#current-architecture-analysis)
2. [PydanticAI Features Overview](#pydanticai-features-overview)
3. [Migration Strategy](#migration-strategy)
4. [Implementation Plan](#implementation-plan)
5. [Evaluator-Optimizer Implementation with PydanticAI](#evaluator-optimizer-implementation-with-pydanticai)
6. [Code Generation Prompts](#code-generation-prompts)

## Current Architecture Analysis

The current architecture uses Claude for several AI-driven features:

1. **Resume Customization** (`customize_resume`): Tailors a resume to match a job description with different customization strengths.
2. **Resume-Job Match Evaluation** (`evaluate_resume_job_match`): Analyzes how well a resume matches a job description.
3. **Optimization Plan Generation** (`generate_optimization_plan`): Creates a detailed plan for improving a resume.
4. **Cover Letter Generation** (`generate_cover_letter`): Creates a personalized cover letter.

The application uses an "evaluator-optimizer" pattern where:
- The "evaluator" analyzes the resume-job match and provides structured feedback
- The "optimizer" then creates a detailed plan based on the evaluation
- This is a multi-step AI workflow with structured outputs

Key components include:
- `claude_service.py`: Core Claude API integration
- `prompts.py`: Detailed system prompts for different tasks
- `customization_service.py`: Business logic for the evaluator-optimizer pattern
- `ats.py` & `customize.py`: API endpoints

## PydanticAI Features Overview

PydanticAI offers several advanced capabilities that can enhance the application:

### Key PydanticAI Features

1. **Model Agnosticism**:
   - Support for multiple LLM providers (OpenAI, Anthropic, Gemini, etc.)
   - Seamless switching between models with fallback mechanisms
   - Same code works across different LLM backends
   - Perfect for avoiding vendor lock-in and optimizing cost/performance

2. **Type-Safe Design**:
   - Built on Pydantic's robust type validation system
   - Early error detection through type checking
   - Clear error messages for invalid responses
   - Ensures consistent and predictable behavior

3. **Structured Outputs**:
   - Uses Pydantic models to define and validate response structures
   - Automatic conversion between JSON and Python objects
   - Support for complex nested models
   - Perfect for the structured evaluation and optimization plans in ResumeAIAssistant

4. **Dependency Injection**:
   - Flexible context passing to agents
   - Dynamic system prompts based on runtime data
   - Simplified testing through dependency substitution
   - Enables more modular and maintainable code

5. **Tool Integration**:
   - Python decorator-based function tools
   - Automatic schema generation from function signatures
   - Type-safe parameter validation
   - Enables extending agents with custom capabilities

6. **Agent Composition Patterns**:
   - Uses Python's native control flow for agent composition
   - Flexible error handling and retry logic
   - Natural integration with Python's async capabilities
   - Supports complex agent workflows through function composition

### Supported Models

1. **OpenAI Models**:
   - GPT-4o, GPT-4o-mini, o3, o3-mini
   - Support for context windows up to 128K tokens
   - Function calling for structured outputs
   - Varying price points for cost optimization

2. **Anthropic Models**:
   - Claude 3 Series (Opus, Sonnet, Haiku)
   - Claude 3.5 Sonnet
   - Large context windows
   - Strong reasoning capabilities

3. **Google Gemini Models**:
   - Gemini 1.5 Pro, Flash
   - Multimodal capabilities
   - Competitive pricing

4. **Additional Providers**:
   - Mistral, Cohere, Groq, Ollama
   - AWS Bedrock integration
   - Local model support
   - Open-source model compatibility

## Migration Strategy

The migration will follow these principles:

1. **Gradual Model Transition**: Start with Anthropic models for compatibility, then expand to other providers
2. **Backward Compatibility**: Maintain existing API contracts and function signatures
3. **Type Safety Enhancement**: Add Pydantic models for all structured inputs and outputs
4. **Model Flexibility**: Configure model selection based on task requirements
5. **Cost Optimization**: Implement model selection strategies to balance performance and cost
6. **Future-Proofing**: Create a flexible architecture that can adapt to new models and features

## Implementation Plan

### Phase 1: PydanticAI Core Integration
1. **Environment Setup**
   - Install PydanticAI and dependencies
   - Configure environment variables for API keys
   - Set up logging and monitoring with Pydantic Logfire
   - Create `pydanticai_service.py` module as the foundation

2. **Schema Definition**
   - Define Pydantic models for all structured outputs:
     - `ResumeEvaluation` for resume analysis
     - `OptimizationPlan` for customization plans
     - `CustomizedResume` for modified resumes
     - `CoverLetter` for generated cover letters
   - Implement validation rules for each schema
   - Create comprehensive docstrings for schema clarity

3. **Basic Agent Implementation**
   - Create the base agent architecture
   - Implement prompt templates with Jinja2
   - Configure model providers (starting with Anthropic)
   - Set up error handling and retry logic
   - Create utility functions for token counting and rate limiting

### Phase 2: Evaluator-Optimizer Implementation
1. **Evaluator Agent**
   - Define the `ResumeEvaluator` agent with structured output
   - Implement the existing evaluator prompts
   - Add custom tools for keyword extraction
   - Create validation logic for evaluation outputs
   - Implement comprehensive logging

2. **Optimizer Agent**
   - Define the `ResumeOptimizer` agent with structured output
   - Implement the existing optimizer prompts
   - Add dependency injection for evaluation results
   - Create validation logic for optimization plans
   - Add tracing for optimization steps

3. **Agent Workflow Integration**
   - Implement the evaluator-optimizer workflow
   - Define iteration mechanisms and stopping criteria
   - Create error handling for the complete workflow
   - Implement performance metrics collection
   - Add detailed logging for each step

### Phase 3: Extension and Optimization
1. **Model Provider Expansion**
   - Add support for OpenAI models
   - Implement Gemini integration
   - Add model fallback chains
   - Create model selection strategies
   - Implement A/B testing capabilities

2. **Tool Development**
   - Create keyword extraction tool
   - Implement ATS simulation tool
   - Add formatting analysis tool
   - Develop industry-specific guidance tools
   - Implement scoring and metrics tools

3. **Performance Optimization**
   - Implement caching mechanisms
   - Create token usage optimization
   - Add parallel processing where applicable
   - Implement model-specific prompt optimization
   - Create performance monitoring dashboards

## Evaluator-Optimizer Implementation with PydanticAI

The evaluator-optimizer pattern is perfect for implementation with PydanticAI's type-safe design and structured outputs. Here's a detailed implementation approach:

### Schema Definition

```python
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal

class KeywordMatch(BaseModel):
    keyword: str
    found_in_resume: bool
    importance: Literal["critical", "important", "nice-to-have"]
    context: Optional[str] = None

class ResumeEvaluation(BaseModel):
    score: int = Field(..., ge=0, le=100, description="Overall match score from 0-100")
    keyword_matches: List[KeywordMatch] = Field(..., description="Detailed keyword match analysis")
    missing_keywords: List[str] = Field(..., description="Important keywords from job description missing in resume")
    suggestions: List[str] = Field(..., description="Specific suggestions for improvement")
    passes_ats: bool = Field(..., description="Whether the resume would pass an ATS system")
    strengths: List[str] = Field(..., description="Resume strengths relative to the job")
    weaknesses: List[str] = Field(..., description="Areas of improvement needed")

class SectionChange(BaseModel):
    section_name: str = Field(..., description="Name of the section to modify")
    original_content: str = Field(..., description="Original content in this section")
    modified_content: str = Field(..., description="Proposed modified content")
    rationale: str = Field(..., description="Explanation for the changes")

class OptimizationPlan(BaseModel):
    sections_to_modify: List[SectionChange] = Field(..., description="Specific sections to change")
    new_sections_to_add: List[SectionChange] = Field(..., description="New sections to add")
    overall_strategy: str = Field(..., description="Overall customization strategy")
    customization_level: Literal["light", "moderate", "heavy"] = Field(..., description="Level of changes applied")

class CustomizedResume(BaseModel):
    original_resume: str = Field(..., description="The original resume text")
    customized_resume: str = Field(..., description="The customized resume text")
    changes_made: List[SectionChange] = Field(..., description="Details of changes made")
    customization_level: Literal["light", "moderate", "heavy"] = Field(..., description="Level of customization applied")
```

### Agent Implementation

```python
from pydanticai import Agent, tool
from typing import Any, Dict

# Initialize the evaluator agent
evaluator_agent = Agent(
    'anthropic:claude-3-5-sonnet',  # Can be configured based on settings
    output_type=ResumeEvaluation,
    system_prompt="""
    You are an expert resume evaluator and ATS specialist. Your job is to analyze how well a resume matches a job description.
    
    Provide detailed feedback on:
    1. Keyword matches and missing keywords
    2. Overall match score (0-100)
    3. Whether the resume would pass an ATS system
    4. Specific suggestions for improvement
    5. Strengths and weaknesses of the resume
    
    Be thorough in your analysis and provide actionable feedback.
    """
)

# Define custom tools
@evaluator_agent.tool
def extract_keywords(job_description: str, max_keywords: int = 20) -> List[str]:
    """
    Extract important keywords from a job description.
    
    Args:
        job_description: The job description text
        max_keywords: Maximum number of keywords to extract
        
    Returns:
        List of important keywords
    """
    # Implementation would use NLP libraries
    # Placeholder for example
    return ["placeholder"]

@evaluator_agent.tool
def simulate_ats(resume: str, job_description: str) -> Dict[str, Any]:
    """
    Simulate how an ATS system would process this resume.
    
    Args:
        resume: The resume text
        job_description: The job description
        
    Returns:
        Dictionary with ATS simulation results
    """
    # Implementation would simulate ATS behavior
    # Placeholder for example
    return {"score": 85, "passes": True}

# Initialize the optimizer agent
optimizer_agent = Agent(
    'anthropic:claude-3-5-sonnet',  # Can be configured based on settings
    output_type=OptimizationPlan,
    system_prompt="""
    You are an expert resume optimizer. Your job is to create a detailed plan to improve a resume based on:
    
    1. The original resume
    2. The job description
    3. The evaluation feedback
    
    Create a section-by-section plan for improving the resume. For each section, provide:
    1. The original content
    2. The modified content
    3. A rationale for the changes
    
    Focus on addressing the missing keywords and suggestions from the evaluation.
    """
)
```

### Workflow Implementation

```python
async def evaluate_resume_job_match(
    resume: str, 
    job_description: str,
    industry: Optional[str] = None
) -> ResumeEvaluation:
    """
    Evaluate how well a resume matches a job description.
    
    Args:
        resume: The resume text
        job_description: The job description
        industry: Optional industry context
        
    Returns:
        Structured evaluation of the resume-job match
    """
    # Build the input prompt
    prompt = f"""
    Resume:
    {resume}
    
    Job Description:
    {job_description}
    """
    
    if industry:
        prompt += f"\nIndustry: {industry}"
    
    # Run the evaluator agent
    result = await evaluator_agent.run(
        prompt,
        deps={
            "extract_keywords_context": {"job_description": job_description},
            "simulate_ats_context": {"resume": resume, "job_description": job_description}
        }
    )
    
    # Result is already a validated ResumeEvaluation instance
    return result

async def generate_optimization_plan(
    resume: str,
    job_description: str,
    evaluation: ResumeEvaluation,
    customization_level: str = "moderate"
) -> OptimizationPlan:
    """
    Generate a plan to optimize the resume based on evaluation.
    
    Args:
        resume: The resume text
        job_description: The job description
        evaluation: The resume evaluation
        customization_level: How much to customize ("light", "moderate", "heavy")
        
    Returns:
        Structured optimization plan
    """
    # Build the input prompt
    prompt = f"""
    Resume:
    {resume}
    
    Job Description:
    {job_description}
    
    Evaluation:
    - Score: {evaluation.score}/100
    - Missing Keywords: {', '.join(evaluation.missing_keywords)}
    - Suggestions: {', '.join(evaluation.suggestions)}
    - Strengths: {', '.join(evaluation.strengths)}
    - Weaknesses: {', '.join(evaluation.weaknesses)}
    
    Customization Level: {customization_level}
    """
    
    # Run the optimizer agent
    result = await optimizer_agent.run(prompt)
    
    # Result is already a validated OptimizationPlan instance
    return result

async def customize_resume(
    resume: str,
    job_description: str,
    customization_strength: str = "moderate",
    industry: Optional[str] = None,
    iterations: int = 1
) -> CustomizedResume:
    """
    Customize a resume to better match a job description.
    
    Args:
        resume: The resume text
        job_description: The job description
        customization_strength: How much to customize ("light", "moderate", "heavy")
        industry: Optional industry context
        iterations: Number of improvement iterations
        
    Returns:
        Customized resume with details of changes
    """
    current_resume = resume
    current_evaluation = None
    changes_made = []
    
    for i in range(iterations):
        # Step 1: Evaluate current resume
        current_evaluation = await evaluate_resume_job_match(
            current_resume, job_description, industry
        )
        
        # Check if score is already good enough
        if current_evaluation.score >= 90:
            break
            
        # Step 2: Generate optimization plan
        optimization_plan = await generate_optimization_plan(
            current_resume, 
            job_description,
            current_evaluation,
            customization_strength
        )
        
        # Step 3: Apply changes to resume
        # In a real implementation, this would have more sophisticated 
        # section parsing and modification logic
        new_resume = current_resume
        
        for section in optimization_plan.sections_to_modify:
            # Simple replacement - in practice would need more robust section identification
            new_resume = new_resume.replace(
                section.original_content, 
                section.modified_content
            )
            changes_made.append(section)
            
        # Add new sections if any
        for new_section in optimization_plan.new_sections_to_add:
            # In practice, would need to insert at appropriate points in the resume
            new_resume += f"\n\n{new_section.section_name}\n{new_section.modified_content}"
            changes_made.append(new_section)
            
        current_resume = new_resume
    
    # Create the final result
    return CustomizedResume(
        original_resume=resume,
        customized_resume=current_resume,
        changes_made=changes_made,
        customization_level=customization_strength
    )
```

### Cover Letter Implementation

```python
class CoverLetter(BaseModel):
    content: str = Field(..., description="The full cover letter text")
    sections: Dict[str, str] = Field(..., description="The cover letter broken down by sections")
    personalization_elements: List[str] = Field(..., description="How the letter was personalized")
    formatting_notes: Optional[str] = Field(None, description="Notes about the formatting")

cover_letter_agent = Agent(
    'anthropic:claude-3-5-sonnet',  # Can be configured based on settings
    output_type=CoverLetter,
    system_prompt="""
    You are an expert cover letter writer. Your job is to create a compelling, personalized cover letter based on:
    
    1. The resume
    2. The job description
    3. Any personal details provided
    
    Create a professional cover letter that highlights relevant experience and skills,
    demonstrates enthusiasm for the role, and shows cultural fit with the company.
    
    The cover letter should have a clear structure with:
    - Introduction
    - 2-3 body paragraphs highlighting relevant experience
    - Closing paragraph
    
    Keep the tone professional but conversational, and limit to one page.
    """
)

async def generate_cover_letter(
    resume: str,
    job_description: str,
    personal_details: Optional[Dict[str, str]] = None,
    company_research: Optional[str] = None
) -> CoverLetter:
    """
    Generate a personalized cover letter based on resume and job description.
    
    Args:
        resume: The resume text
        job_description: The job description
        personal_details: Optional dict with name, contact info, etc.
        company_research: Optional additional company information
        
    Returns:
        Structured cover letter response
    """
    # Build the input prompt
    prompt = f"""
    Resume:
    {resume}
    
    Job Description:
    {job_description}
    """
    
    if personal_details:
        personal_info = "\n".join([f"{k}: {v}" for k, v in personal_details.items()])
        prompt += f"\n\nPersonal Details:\n{personal_info}"
        
    if company_research:
        prompt += f"\n\nCompany Information:\n{company_research}"
    
    # Run the cover letter agent
    result = await cover_letter_agent.run(prompt)
    
    # Result is already a validated CoverLetter instance
    return result
```

## Code Generation Prompts

The following section contains structured prompts for generating code for the PydanticAI implementation.

### Prompt 1: Create PydanticAI Service Module

```
Create a new Python module called pydanticai_service.py that will replace claude_service.py using PydanticAI.
The module should:
1. Import necessary dependencies:
   - PydanticAI (Agent, tool)
   - Pydantic for schema definition
   - Logging from app.core.logging
   - Configuration from app.core.config
2. Set up proper error handling for API key validation
3. Initialize logging similar to the Claude service
4. Define Pydantic schemas for all structured outputs:
   - ResumeEvaluation
   - OptimizationPlan
   - CustomizedResume
   - CoverLetter
5. Create the basic agent implementations:
   - Resume Evaluator Agent
   - Resume Optimizer Agent
   - Cover Letter Agent
6. Define stubs for the main API functions with the same signatures as claude_service.py:
   - evaluate_resume_job_match
   - generate_optimization_plan
   - customize_resume
   - generate_cover_letter

Include thorough documentation for the module and follow the proper project coding style.
```

### Prompt 2: Update Configuration Module

```
Update the app.core.config.py module to add PydanticAI configuration.
The changes should:
1. Add the following settings:
   - PYDANTICAI_DEFAULT_PROVIDER: Default model provider (e.g., "anthropic")
   - PYDANTICAI_DEFAULT_MODEL: Default model setting (e.g., "claude-3-5-sonnet")
   - PYDANTICAI_EVALUATOR_MODEL: Model for evaluation tasks
   - PYDANTICAI_OPTIMIZER_MODEL: Model for optimization tasks
   - PYDANTICAI_FALLBACK_MODELS: List of models to try if primary fails
   - PYDANTICAI_TEMPERATURE: Temperature setting for agent outputs
   - PYDANTICAI_MAX_TOKENS: Maximum tokens for responses
2. Add model configuration logic for different providers:
   - Anthropic configuration
   - OpenAI configuration (as fallback)
   - Gemini configuration (as fallback)
3. Maintain complete backward compatibility with existing Claude configuration
4. Add proper documentation for all new settings
5. Include error checking for missing API keys

Follow the existing code style and structure in the config module.
```

### Prompt 3: Implement Resume Evaluation Schema and Agent

```
Implement the resume evaluator schema and agent using PydanticAI. The implementation should:
1. Define a comprehensive ResumeEvaluation Pydantic model:
   - score: int (0-100)
   - keyword_matches: List of keyword match details
   - missing_keywords: List of missing keywords
   - suggestions: List of improvement suggestions
   - passes_ats: Boolean indicating ATS compatibility
   - strengths: List of resume strengths
   - weaknesses: List of areas for improvement
2. Create a ResumeEvaluator agent:
   - Configure with the appropriate model based on settings
   - Set up system prompt using the existing evaluator prompt
   - Add custom tools for keyword extraction and ATS simulation
3. Implement the evaluate_resume_job_match function:
   - Same signature as the existing function
   - Use the new agent to generate structured evaluation
   - Add proper error handling and logging
4. Add comprehensive docstrings and type hints
5. Include unit tests for the evaluation schema

Follow the project's coding style and ensure backward compatibility with existing code.
```

### Prompt 4: Implement Optimization Schema and Agent

```
Implement the resume optimizer schema and agent using PydanticAI. The implementation should:
1. Define a comprehensive OptimizationPlan Pydantic model:
   - sections_to_modify: List of section changes
   - new_sections_to_add: List of new sections
   - overall_strategy: String describing the approach
   - customization_level: Literal type for customization strength
2. Define a SectionChange Pydantic model:
   - section_name: Section identifier
   - original_content: Original text
   - modified_content: Proposed text
   - rationale: Explanation for changes
3. Create a ResumeOptimizer agent:
   - Configure with the appropriate model based on settings
   - Set up system prompt using the existing optimizer prompt
   - Add any necessary tools or dependencies
4. Implement the generate_optimization_plan function:
   - Same signature as the existing function
   - Use the new agent to generate structured optimization plan
   - Add proper error handling and logging
5. Add comprehensive docstrings and type hints
6. Include unit tests for the optimization schema

Follow the project's coding style and ensure backward compatibility with existing code.
```

### Prompt 5: Implement Customization Workflow

```
Implement the complete resume customization workflow using PydanticAI. The implementation should:
1. Define a CustomizedResume Pydantic model:
   - original_resume: The original text
   - customized_resume: The modified text
   - changes_made: List of section changes
   - customization_level: The level of customization applied
2. Implement the customize_resume function:
   - Same signature as the existing function
   - Use the evaluator and optimizer agents in a workflow
   - Support multiple iterations with stopping criteria
   - Implement section replacement logic
   - Add proper error handling and logging
3. Add support for different customization levels:
   - Adjust agent behavior based on customization strength
   - Implement appropriate prompt modifications
4. Include industry-specific guidance:
   - Pass industry information to agents
   - Adjust evaluation criteria based on industry
5. Add comprehensive docstrings and type hints
6. Include unit tests for the customization workflow

Follow the project's coding style and ensure backward compatibility with existing code.
```

### Prompt 6: Implement Cover Letter Generation

```
Implement the cover letter generation feature using PydanticAI. The implementation should:
1. Define a CoverLetter Pydantic model:
   - content: Full cover letter text
   - sections: Dictionary of letter sections
   - personalization_elements: List of personalization details
   - formatting_notes: Optional notes about formatting
2. Create a CoverLetterGenerator agent:
   - Configure with the appropriate model based on settings
   - Set up system prompt using the existing cover letter prompt
   - Add any necessary tools or dependencies
3. Implement the generate_cover_letter function:
   - Same signature as the existing function
   - Use the new agent to generate structured cover letter
   - Add proper error handling and logging
4. Add support for personalization:
   - Process personal details in the prompt
   - Include company research when available
5. Add comprehensive docstrings and type hints
6. Include unit tests for the cover letter generation

Follow the project's coding style and ensure backward compatibility with existing code.
```

### Prompt 7: Implement Custom Tools

```
Implement custom tools for the PydanticAI agents. The implementation should include:
1. Keyword extraction tool:
   - Function to extract key requirements from job descriptions
   - Use NLP techniques to identify important terms
   - Support prioritization (required vs preferred)
   - Return structured keyword information
2. ATS simulation tool:
   - Function to simulate ATS scanning of resumes
   - Score calculation based on keyword matches
   - Formatting analysis for ATS compatibility
   - Return detailed ATS results
3. Industry guidance tool:
   - Function to provide industry-specific resume advice
   - Support for various industries (tech, finance, healthcare, etc.)
   - Return tailored recommendations
4. Text formatting tool:
   - Function to analyze and improve resume formatting
   - Check for consistent styling and structure
   - Return formatting suggestions
5. Error handling for all tools
6. Comprehensive docstrings and type hints
7. Unit tests for tool functionality

Follow the project's coding style and ensure proper integration with the agents.
```

### Prompt 8: Implement Model Provider Management

```
Create a module for managing multiple model providers with PydanticAI. The implementation should:
1. Create a ModelManager class:
   - Configure multiple providers (Anthropic, OpenAI, Gemini)
   - Handle API key validation and error handling
   - Support fallback chains between providers
   - Track usage and performance metrics
2. Implement provider-specific configuration:
   - Anthropic provider setup
   - OpenAI provider setup
   - Gemini provider setup
   - Support for additional providers
3. Create model selection strategies:
   - Cost-based selection
   - Performance-based selection
   - Task-specific selection
   - Fallback handling
4. Implement token usage tracking:
   - Estimate token usage before requests
   - Track actual token usage
   - Calculate costs across providers
5. Add proper error handling and logging
6. Include comprehensive documentation
7. Add unit tests for provider management

Follow the project's modular architecture and provide thorough documentation.
```

### Prompt 9: Update API Endpoints

```
Update the API endpoints to use the new pydanticai_service module. The implementation should:
1. Update ATS Endpoints (app/api/endpoints/ats.py):
   - Import the pydanticai_service module
   - Update function calls to use the new service
   - Maintain the same API interface
   - Add any necessary error handling
   - Update response models if needed
2. Update Customization Endpoints (app/api/endpoints/customize.py):
   - Switch to the PydanticAI service
   - Maintain the existing API contracts
   - Add PydanticAI-specific error handling
   - Ensure all functionality is preserved
3. Update Cover Letter Endpoints (app/api/endpoints/cover_letter.py):
   - Replace Claude service calls with PydanticAI calls
   - Preserve the same interface
   - Update error handling
   - Ensure backward compatibility
4. Add monitoring and telemetry:
   - Track performance metrics
   - Monitor token usage
   - Log model selection details

Follow the project's API architecture and error handling patterns.
```

### Prompt 10: Create Integration Tests

```
Create comprehensive tests for the PydanticAI integration. The implementation should include:
1. Unit tests for schemas:
   - Test validation for all Pydantic models
   - Ensure proper error messages for invalid data
   - Test edge cases and boundary values
2. Integration tests for agents:
   - Test the evaluator agent with sample inputs
   - Test the optimizer agent with sample inputs
   - Test the cover letter agent with sample inputs
   - Verify structured output compliance
3. Workflow tests:
   - Test the complete customization workflow
   - Verify proper handling of iterations
   - Test different customization levels
   - Validate integrated agent behavior
4. Error handling tests:
   - Test API key validation
   - Test model fallback mechanisms
   - Test rate limiting handling
   - Verify appropriate error responses
5. Performance tests:
   - Measure response times across providers
   - Compare token efficiency
   - Test with various input sizes

Follow the project's testing conventions with pytest and provide comprehensive documentation.
```

## Next Steps and Considerations

- **Gradual Rollout**: Begin with Anthropic models for compatibility, then expand to other providers
- **A/B Testing**: Implement comparison testing between Claude direct implementation and PydanticAI
- **Cost Monitoring**: Track token usage and costs across different providers
- **Model Experimentation**: Test different models to find optimal price/performance balance
- **Tool Enhancement**: Continuously improve the custom tools based on performance data
- **Schema Refinement**: Iterate on the Pydantic models based on user feedback
- **Documentation**: Provide comprehensive documentation for the new architecture
- **UI Integration**: Update the frontend to utilize new capabilities
- **Performance Tuning**: Optimize prompt templates and token usage for efficiency