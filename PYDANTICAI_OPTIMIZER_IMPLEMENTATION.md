# PydanticAI Evaluator-Optimizer Implementation

This document provides an overview of the PydanticAI implementation of the evaluator-optimizer pattern for resume customization in the ResumeAIAssistant project.

## Overview

The implementation follows the evaluator-optimizer pattern, which consists of a multi-stage AI workflow:

1. **Evaluation Stage**: A resume is evaluated against a job description to analyze how well they match.
2. **Optimization Stage**: Based on the evaluation, a detailed optimization plan is generated.
3. **Feedback Loop**: The optimization plan is evaluated and improved iteratively.
4. **Implementation Stage**: The optimization plan is applied to the resume to create a customized version.

## Files Implemented

1. **`app/services/pydanticai_optimizer.py`**: The core module implementing the PydanticAI-powered evaluator-optimizer pattern.
2. **`app/api/endpoints/customize.py`**: Updated API endpoints with support for PydanticAI as a provider option.
3. **`tests/integration/test_pydanticai.py`**: Integration tests for the PydanticAI optimizer implementation.
4. **`test_pydanticai_optimizer.py`**: A simple test script for testing the PydanticAI optimizer.

## Key Features

### Model Agnosticism
- Support for multiple AI providers (Anthropic, OpenAI, Google)
- Seamless switching between models through configuration
- Fallback chains for resilience

### Evaluator-Optimizer Pattern
- Structured evaluation of resume-job match
- Detailed optimization plan generation
- Progressive enhancement through feedback loop
- Configurable iteration count

### Enhanced AI Capabilities
- Support for Claude 3.7's extended thinking capability
- Configurable thinking budget for complex reasoning
- Industry-specific guidance customization

### Error Handling and Resilience
- Comprehensive error handling at every stage
- Fallback mechanisms for API failures
- Multiple iteration attempts for optimal results

### Monitoring and Logging
- Detailed logging with performance metrics
- Tracing for each stage of the process
- Error tracking and reporting

## API Integration

The implementation integrates with the existing API with minimal changes:

- Added a `provider` parameter to existing endpoints
- Maintained backward compatibility with existing Claude and OpenAI implementations
- Consistent response formats across all providers

## Configuration

The implementation leverages the existing configuration system:

- `app/core/config.py` defines settings for PydanticAI
- Multiple models and providers are configured
- Environment variables for API keys and model selection

## Usage

### API Endpoints

```
POST /api/v1/customize/?provider=pydanticai
{
    "resume_id": "uuid",
    "job_description_id": "uuid",
    "customization_strength": 2,
    "focus_areas": "technology"
}
```

```
POST /api/v1/customize/plan?provider=pydanticai
{
    "resume_id": "uuid",
    "job_description_id": "uuid",
    "customization_strength": 2,
    "industry": "technology"
}
```

### Testing

Run the integration tests:
```
pytest tests/integration/test_pydanticai.py
```

Run the simple test script:
```
python test_pydanticai_optimizer.py <resume_id> <job_id> --implement
```

## Future Improvements

1. **Performance Optimization**: Implement caching for common evaluation patterns
2. **Extended Tools**: Add support for custom PydanticAI tools for keyword extraction and ATS simulation
3. **A/B Testing**: Compare results across different providers and models
4. **Cost Optimization**: Implement model selection based on cost/performance tradeoffs
5. **User Feedback Loop**: Incorporate user feedback to improve the optimization process