# OpenAI Integration Plan for ResumeAIAssistant

This document outlines a comprehensive plan to migrate the ResumeAIAssistant from Anthropic's Claude API to OpenAI's ecosystem, including incorporating various OpenAI features like function calling, the Responses API, and the Agents SDK.

## Table of Contents
1. [Current Architecture Analysis](#current-architecture-analysis)
2. [OpenAI Models & Features Overview](#openai-models--features-overview)
3. [Migration Strategy](#migration-strategy)
4. [Implementation Plan](#implementation-plan)
5. [Evaluator-Optimizer Implementation with Agents SDK](#evaluator-optimizer-implementation-with-agents-sdk)
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

## OpenAI Models & Features Overview

OpenAI offers several advanced capabilities that can enhance the application:

### Models

1. **GPT-4o**: OpenAI's flagship multimodal model with:
   - Strong reasoning capabilities
   - 128K token context window (approximately 300 pages)
   - Lower latency than previous models
   - Support for function calling
   - RAG capabilities
   - ~$5/million input tokens, ~$15/million output tokens

2. **GPT-4.1**: Latest model family focused on coding with:
   - Multiple variants: GPT-4.1, GPT-4.1 mini, GPT-4.1 nano
   - Improved performance on coding tasks
   - Available through API

3. **o-Series Models**:
   - **o3**: OpenAI's most advanced reasoning model
     - "Think before they speak" approach
     - Scores 69.1% on SWE-bench verified coding test
     - Improved logical reasoning
   - **o4-mini**: Smaller, cheaper, faster reasoning model
     - Similar performance to o3 (68.1% on SWE-bench)
     - Lower cost with strong reasoning capabilities
   - **o3-mini**: Smaller reasoning model
     - Available on free ChatGPT tier
     - Scores 49.3% on SWE-bench

4. **GPT-4o mini**: More affordable model with:
   - 128K token context window
   - Good performance for cost-sensitive applications
   - Support for function calling
   - ~$0.15/million input tokens, ~$0.60/million output tokens

### Key OpenAI Features

1. **Function Calling**:
   - Allows models to generate structured JSON that calls specified functions
   - Helps extract structured data from natural language
   - Ensures consistent output format for evaluations and recommendations
   - Perfect for the structured outputs in the resume customization workflow

2. **Responses API**:
   - OpenAI's newest API for building agents (replacing the Assistants API)
   - The Assistants API will be deprecated by mid-2026 in favor of the Responses API
   - Simple, synchronous API that combines Chat Completions with agentic features
   - Provides built-in support for web search, file search, and other tools
   - Allows for the creation of stateful, multi-turn conversations
   - Integrates well with the Agents SDK
   - Usage in Python:
     ```python
     from openai import OpenAI
     
     client = OpenAI()
     
     response = client.responses.create(
         model="gpt-4o",
         messages=[{"role": "user", "content": "Hello!"}]
     )
     ```

3. **Agents SDK**:
   - Lightweight, open-source framework for building agentic applications
   - Enables multi-agent workflows with custom orchestration
   - Can be integrated with the Responses API or Chat Completions API
   - Key components:
     - `Agent`: LLMs configured with instructions, tools, and handoffs
     - `Handoffs`: Tools for transferring control between agents
     - `Tools`: Functional capabilities that agents can use
     - `Runner`: Executes agent workflows
   - Built-in tracing for monitoring and debugging
   - Recommended implementation uses `OpenAIResponsesModel` which connects to the Responses API
   - Basic usage:
     ```python
     from agents import Agent, Runner
     import asyncio
     
     agent = Agent(
         name="Assistant",
         instructions="You are a helpful assistant"
     )
     
     async def main():
         result = await Runner.run(agent, "Write a resume summary for a software engineer.")
         print(result.final_output)
     
     asyncio.run(main())
     ```

4. **Vector Stores and RAG**:
   - Used for retrieval-augmented generation
   - Can be integrated with Responses API and Agents SDK
   - Useful for storing and retrieving industry-specific resume templates and job descriptions
   - Enables more effective customization based on industry standards

## Migration Strategy

The migration will follow these principles:

1. **Incremental Approach**: Replace functionality in small, testable steps
2. **Backward Compatibility**: Maintain existing API contracts
3. **Feature Enhancement**: Improve functionality using OpenAI capabilities
4. **Cost Optimization**: Use appropriate models for different tasks (consider o-series models for reasoning tasks)
5. **Future-Proofing**: Implement Responses API instead of Assistants API to avoid future migration
6. **Error Handling**: Implement robust error handling for API transitions

## Implementation Plan

### Phase 1: Basic API Migration (Weeks 1-2)

1. **Infrastructure & Environment Setup**
   - Create OpenAI API client
   - Set up environment variables
   - Update dependency management

2. **Direct API Replacement**
   - Replace Claude API calls with equivalent OpenAI Responses API calls
   - Keep the same input/output interfaces
   - Maintain existing business logic

3. **Prompt Engineering**
   - Convert Claude prompts to OpenAI format
   - Optimize prompts for OpenAI models
   - Test prompt effectiveness

### Phase 2: Function Calling Integration (Weeks 3-4)

1. **Schema Definitions**
   - Define JSON schema for structured outputs
   - Create function calling definitions

2. **Service Refactoring**
   - Implement function calling for:
     - Resume evaluation
     - Optimization plan generation
     - ATS analysis
   - Update parsing logic for function outputs

3. **Error Handling & Testing**
   - Implement fallbacks for function calling errors
   - Test edge cases
   - Create testing framework for function output validation

### Phase 3: Agents SDK Integration (Weeks 5-6)

1. **SDK Setup**
   - Install and configure the OpenAI Agents SDK
   - Create specialized agents for different tasks:
     - Resume Evaluator Agent
     - Resume Optimizer Agent
     - Cover Letter Agent
   - Configure agent parameters, tools, and handoffs

2. **Multi-Agent Workflow**
   - Implement handoffs between evaluation and optimization agents
   - Set up agent orchestration
   - Integrate tools for resume parsing and analysis

3. **Service Integration**
   - Refactor services to use Agents SDK with Responses API
   - Update business logic to handle agent workflows
   - Implement state management for multi-step processes

### Phase 4: Vector Store & Advanced Features (Weeks 7-8)

1. **Vector Database Setup**
   - Set up vector store (e.g., Pinecone, Qdrant, or OpenAI's embeddings)
   - Populate with industry guidelines and examples
   - Implement retrieval functionality

2. **RAG Implementation**
   - Create industry-specific RAG pipelines
   - Implement resume template retrieval
   - Enhance job-specific optimization

3. **Custom Tools Development**
   - Implement custom tools for resume parsing
   - Create tools for ATS analysis
   - Integrate with Agents SDK and Responses API

### Phase 5: Optimization & Scaling (Weeks 9-10)

1. **Performance Optimization**
   - Analyze and optimize token usage
   - Implement model switching based on task complexity
   - Consider o3-mini for cost-effective reasoning tasks
   - Optimize prompt length and efficiency

2. **Cost Management**
   - Implement token counting and budgeting
   - Create cost allocation and monitoring
   - Optimize for cost-effectiveness

3. **Scalability & Monitoring**
   - Set up monitoring for API calls
   - Implement rate limiting and batching
   - Create dashboards for API usage and performance

## Evaluator-Optimizer Implementation with Agents SDK

The evaluator-optimizer pattern is a powerful workflow where one agent generates content and another agent evaluates it, providing feedback for improvement in an iterative loop. This pattern is well-suited for the resume customization task, where we want to both evaluate the resume-job match and optimize the resume based on that evaluation.

### How the Evaluator-Optimizer Pattern Works

1. **Generator Agent**: Creates or modifies content (in our case, resume customizations)
2. **Evaluator Agent**: Assesses the content against specific criteria and provides feedback
3. **Iteration Loop**: The feedback is fed back to the Generator to improve the content
4. **Termination Condition**: The loop continues until the Evaluator determines the content meets requirements

### Implementation with OpenAI Agents SDK

Here's how to implement the evaluator-optimizer pattern for ResumeAIAssistant using the OpenAI Agents SDK:

#### 1. Define Specialized Agents

```python
from agents import Agent, Runner, function_tool, OpenAIResponsesModel
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import asyncio

# Define structured output for evaluator
class ResumeEvaluation(BaseModel):
    score: int = Field(..., description="Overall match score from 0-100")
    keyword_matches: List[str] = Field(..., description="Keywords found in both resume and job description")
    missing_keywords: List[str] = Field(..., description="Important keywords from job description missing in resume")
    suggestions: List[str] = Field(..., description="Specific suggestions for improvement")
    passes_evaluation: bool = Field(..., description="Whether the resume passes minimum requirements")

# Create Evaluator Agent
evaluator_agent = Agent(
    name="Resume Evaluator",
    instructions="""
    You are an expert resume evaluator. Your job is to analyze how well a resume matches a job description.
    Provide detailed feedback on:
    1. Keyword matches and missing keywords
    2. Overall match score
    3. Specific suggestions for improvement
    4. Whether the resume passes minimum requirements
    
    Be thorough in your analysis and provide actionable feedback.
    """,
    output_type=ResumeEvaluation,
    model=OpenAIResponsesModel(model="gpt-4o")
)

# Define structured output for optimizer
class ResumeCustomization(BaseModel):
    customized_sections: Dict[str, str] = Field(..., description="Modified sections of the resume")
    reasoning: str = Field(..., description="Explanation of changes made")
    customization_level: str = Field(..., description="Level of customization applied: 'light', 'moderate', or 'heavy'")

# Create Optimizer Agent
optimizer_agent = Agent(
    name="Resume Optimizer",
    instructions="""
    You are an expert resume optimizer. Your job is to customize a resume based on:
    1. The original resume
    2. The job description
    3. Evaluation feedback
    
    Make targeted improvements to better match the job requirements while maintaining authenticity.
    Explain your reasoning for each change.
    You can customize at different levels: 'light', 'moderate', or 'heavy' based on the user's preference.
    """,
    output_type=ResumeCustomization,
    model=OpenAIResponsesModel(model="gpt-4o")
)
```

#### 2. Implement the Evaluator-Optimizer Workflow

```python
async def evaluator_optimizer_workflow(
    resume: str, 
    job_description: str, 
    customization_level: str = "moderate",
    max_iterations: int = 3
) -> Dict[str, Any]:
    """
    Run the evaluator-optimizer workflow to customize a resume for a job description.
    
    Args:
        resume: The original resume text
        job_description: The target job description
        customization_level: The desired level of customization ('light', 'moderate', 'heavy')
        max_iterations: Maximum number of improvement iterations
        
    Returns:
        Dictionary containing the final customized resume and evaluation metrics
    """
    current_resume = resume
    iteration_history = []
    
    for i in range(max_iterations):
        # 1. Evaluate current resume
        eval_prompt = f"""
        Original Resume:
        {current_resume}
        
        Job Description:
        {job_description}
        
        Evaluate how well this resume matches the job description.
        """
        
        eval_result = await Runner.run(evaluator_agent, eval_prompt)
        evaluation = eval_result.final_output
        
        # Store iteration data
        iteration_history.append({
            "iteration": i + 1,
            "evaluation": evaluation,
            "resume": current_resume
        })
        
        # Check if resume passes evaluation
        if evaluation.passes_evaluation:
            break
            
        # 2. Optimize resume based on evaluation
        optimize_prompt = f"""
        Original Resume:
        {current_resume}
        
        Job Description:
        {job_description}
        
        Evaluation Feedback:
        - Score: {evaluation.score}/100
        - Keyword Matches: {', '.join(evaluation.keyword_matches)}
        - Missing Keywords: {', '.join(evaluation.missing_keywords)}
        - Suggestions: {', '.join(evaluation.suggestions)}
        
        Please customize this resume at the '{customization_level}' level to better match the job description.
        """
        
        optimize_result = await Runner.run(optimizer_agent, optimize_prompt)
        optimization = optimize_result.final_output
        
        # Apply customizations to create new resume
        new_resume = current_resume
        for section, content in optimization.customized_sections.items():
            # In a real implementation, you would have logic to replace specific sections
            # This is a simplified example
            new_resume = new_resume.replace(section, content)
            
        current_resume = new_resume
    
    # Final evaluation after all iterations
    final_eval_prompt = f"""
    Original Resume:
    {resume}
    
    Customized Resume:
    {current_resume}
    
    Job Description:
    {job_description}
    
    Evaluate how well this customized resume matches the job description.
    """
    
    final_eval_result = await Runner.run(evaluator_agent, final_eval_prompt)
    final_evaluation = final_eval_result.final_output
    
    return {
        "original_resume": resume,
        "customized_resume": current_resume,
        "final_evaluation": final_evaluation,
        "iteration_history": iteration_history
    }
```

#### 3. Add Custom Tools for Enhanced Functionality

```python
# Define custom tool for keywords extraction
@function_tool
def extract_keywords(text: str, max_keywords: int = 20) -> List[str]:
    """
    Extract important keywords from text using NLP techniques.
    
    Args:
        text: The text to extract keywords from
        max_keywords: Maximum number of keywords to extract
        
    Returns:
        List of important keywords
    """
    # Implementation would use NLP libraries like spacy or NLTK
    # This is a placeholder
    return ["placeholder_keyword"]

# Define custom tool for ATS simulation
@function_tool
def simulate_ats_scan(resume: str, job_description: str) -> Dict[str, Any]:
    """
    Simulate how an ATS system would process this resume for the given job.
    
    Args:
        resume: The resume text
        job_description: The job description text
        
    Returns:
        Dictionary with ATS simulation results
    """
    # Implementation would use algorithms to simulate ATS behavior
    # This is a placeholder
    return {
        "ats_score": 85,
        "parsed_sections": {"experience": "...", "education": "..."},
        "flagged_issues": ["formatting inconsistency"],
        "passed_initial_screening": True
    }

# Enhanced Evaluator Agent with tools
enhanced_evaluator_agent = Agent(
    name="Enhanced Resume Evaluator",
    instructions="""
    You are an expert resume evaluator with ATS simulation capabilities.
    Your job is to analyze how well a resume matches a job description.
    Use the provided tools to extract keywords and simulate ATS scanning.
    
    Provide detailed feedback on:
    1. Keyword matches and missing keywords
    2. Overall match score
    3. Specific suggestions for improvement
    4. Whether the resume passes minimum requirements
    5. ATS compatibility issues
    
    Be thorough in your analysis and provide actionable feedback.
    """,
    output_type=ResumeEvaluation,
    model=OpenAIResponsesModel(model="gpt-4o"),
    tools=[extract_keywords, simulate_ats_scan]
)
```

#### 4. Integration with Main Application

```python
# Service function that can be called from API endpoints
async def customize_resume_with_agents(
    resume_text: str,
    job_description: str,
    customization_strength: str = "moderate",
    iterations: int = 2
) -> Dict[str, Any]:
    """
    Service function to customize a resume using the evaluator-optimizer workflow.
    
    Args:
        resume_text: The original resume text
        job_description: The job description 
        customization_strength: How much to customize (light, moderate, heavy)
        iterations: Maximum number of improvement iterations
        
    Returns:
        Dictionary with customized resume and evaluation details
    """
    result = await evaluator_optimizer_workflow(
        resume=resume_text,
        job_description=job_description,
        customization_level=customization_strength,
        max_iterations=iterations
    )
    
    # Extract the relevant parts from the result
    return {
        "original_resume": result["original_resume"],
        "customized_resume": result["customized_resume"],
        "match_score": result["final_evaluation"].score,
        "keyword_matches": result["final_evaluation"].keyword_matches,
        "missing_keywords": result["final_evaluation"].missing_keywords,
        "suggestions": result["final_evaluation"].suggestions,
        "passes_ats": result["final_evaluation"].passes_evaluation
    }

# Example FastAPI endpoint
@router.post("/customize", response_model=schemas.CustomizedResumeResponse)
async def customize_resume_endpoint(
    request: schemas.CustomizeResumeRequest
) -> schemas.CustomizedResumeResponse:
    """API endpoint for resume customization."""
    result = await customize_resume_with_agents(
        resume_text=request.resume,
        job_description=request.job_description,
        customization_strength=request.customization_strength,
        iterations=request.max_iterations if request.max_iterations else 2
    )
    
    return schemas.CustomizedResumeResponse(**result)
```

### Benefits of This Approach

1. **Structured Output**: Each agent produces structured data using Pydantic models
2. **Iterative Improvement**: The feedback loop ensures continuous improvement
3. **Configurable Settings**: Customization level and iteration count can be adjusted
4. **Custom Tools**: Enhanced functionality through specialized tools like ATS simulation
5. **Separation of Concerns**: Clear division between evaluation and optimization
6. **Detailed Feedback**: Comprehensive evaluation at each step
7. **Traceable Process**: Complete history of iterations for transparency

By implementing the evaluator-optimizer pattern using OpenAI's Agents SDK, we can create a more robust and effective resume customization system that provides detailed feedback and iteratively improves the resume until it meets the desired criteria.

## Code Generation Prompts

The following section contains prompts for generating code for each implementation step.

### Prompt 1: Create OpenAI Service Module

```
Create a new Python module called openai_service.py that will replace the functionality in claude_service.py. 
The module should:
1. Initialize the OpenAI client with proper error handling
2. Import configuration from app.core.config
3. Set up logging similar to the Claude service
4. Create stub functions with the same signatures as in claude_service.py
5. Include documentation for each function
Use the OpenAI Python SDK (v1.0+) with the Responses API and follow the project's coding style.
```

### Prompt 2: Update Configuration Module

```
Update the app.core.config.py module to add OpenAI configuration. 
The changes should:
1. Add OPENAI_API_KEY, OPENAI_MODEL, and OPENAI_TEMPERATURE settings
2. Create model selection logic that maps different tasks to appropriate models (including o-series)
3. Keep backward compatibility with existing Claude configuration
4. Add documentation for new settings
Keep the same code style as the existing configuration module.
```

### Prompt 3: Implement Function Calling for Resume Evaluation

```
Implement the evaluate_resume_job_match function in openai_service.py using OpenAI's function calling with the Responses API.
The implementation should:
1. Define a JSON schema for the evaluation output
2. Set up function calling parameters for the OpenAI Responses API
3. Handle response parsing for function outputs
4. Implement error handling and fallbacks
5. Match the output format of the original Claude function
Match the coding style of the existing codebase and add thorough documentation.
```

### Prompt 4: Implement Function Calling for Optimization Plan

```
Implement the generate_optimization_plan function in openai_service.py using OpenAI's function calling with the Responses API.
The implementation should:
1. Define a JSON schema for the CustomizationPlan output
2. Set up function calling parameters for the OpenAI Responses API
3. Parse the response and convert to the CustomizationPlan model
4. Handle error cases with appropriate fallbacks
5. Match the original function's signature and behavior
Follow the project's error handling patterns and coding style.
```

### Prompt 5: Create Evaluator-Optimizer Agents

```
Create a module for implementing the evaluator-optimizer pattern using the OpenAI Agents SDK.
The module should:
1. Define the Evaluator Agent with instructions for resume evaluation
2. Define the Optimizer Agent with instructions for resume customization
3. Implement the workflow to connect these agents in an iterative feedback loop
4. Include custom tools for enhanced functionality (keyword extraction, ATS simulation)
5. Provide proper error handling and retry logic
The implementation should match the project's architecture and follow best practices for agent design.
```

### Prompt 6: Implement Vector Store Integration

```
Create a module for integrating vector databases with the application. The module should:
1. Set up a connection to a vector database (e.g., Pinecone or similar)
2. Implement functions to index and retrieve industry guidelines
3. Create RAG pipelines for enhancing prompts with relevant knowledge
4. Include error handling and performance optimization
5. Support integration with both Responses API and Agents SDK
Follow the project's modular architecture and error handling patterns.
```

### Prompt 7: Update ATS Endpoints

```
Update the app/api/endpoints/ats.py module to use the new OpenAI service instead of Claude.
The changes should:
1. Import the openai_service module instead of claude_service
2. Keep the same API interface and response formats
3. Add any necessary error handling for the new service
4. Update logging to track OpenAI-specific metrics
5. Maintain backward compatibility with existing clients
Ensure the code follows the project's style and error handling patterns.
```

### Prompt 8: Implementation of Cost Tracking

```
Create a module for tracking and optimizing OpenAI API usage costs. The module should:
1. Implement token counting for requests and responses
2. Create functions to estimate costs for different operations and models
3. Add logging for token usage and estimated costs
4. Implement model selection logic to optimize for cost (including o-series models)
5. Create helpers for breaking large requests into smaller chunks
Match the project's overall architecture and logging approach.
```

### Prompt 9: Testing Framework for API Migration

```
Create testing utilities for validating the OpenAI API migration. The code should:
1. Create test cases for comparing Claude and OpenAI outputs
2. Implement validation for output structure and content
3. Create benchmarking tools for performance comparison
4. Add tests for error conditions and edge cases
5. Support both synchronous and asynchronous testing
Follow the project's testing patterns and convention.
```

### Prompt 10: Documentation Update

```
Update the project documentation to reflect the OpenAI migration. The documentation should:
1. Describe the new OpenAI functionality including Responses API and Agents SDK
2. Update API documentation with any changes
3. Add troubleshooting information for common issues
4. Include cost estimation and optimization guidelines
5. Provide examples of using the new features
Follow the existing documentation format and style.
```

## Next Steps and Considerations

- **Evaluation**: Test each phase thoroughly before proceeding
- **Rollback Plan**: Maintain the ability to switch back to Claude if needed
- **A/B Testing**: Consider running both APIs in parallel to compare results
- **Cost Monitoring**: Implement detailed monitoring of API costs
- **Prompt Optimization**: Continuously refine prompts for best results
- **Model Selection**: Evaluate o-series models for reasoning tasks
- **Future-Proofing**: Use Responses API to avoid future migration from Assistants API
- **Agents SDK**: Explore advanced orchestration capabilities for complex workflows
- **Evaluator-Optimizer Loop**: Fine-tune the feedback loop for optimal resume customization