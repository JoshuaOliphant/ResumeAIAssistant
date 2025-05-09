# ResumeAIAssistant AI Model Development Assignment

## Task Overview
You are assigned to work on issue #{ISSUE_NUMBER} for the ResumeAIAssistant project. You'll need to:

1. Retrieve the issue details using GitHub CLI
2. Understand the AI system architecture
3. Implement the requested feature/fix according to project standards
4. Submit a pull request with your changes

## Setup and Authentication
The GitHub CLI is already authenticated and configured for this repository. You can access the issue using:

```bash
gh issue view {ISSUE_NUMBER} --repo JoshuaOliphant/ResumeAIAssistant
```

## Project Architecture Overview
ResumeAIAssistant is a resume customization and ATS optimization application with these key components:

1. **PydanticAI Architecture**: A model-agnostic AI system using the evaluator-optimizer pattern
2. **Multi-Model Support**: Integration with multiple AI providers (Anthropic Claude, Google Gemini, OpenAI)
3. **Dynamic Thinking Budget**: Resource allocation system for AI processing
4. **Evaluator-Optimizer Pattern**: Core of resume customization logic

## Key AI System Concepts

### Model Architecture
- **PydanticAI Framework**: Uses Pydantic models to structure AI inputs/outputs
- **Model-Agnostic Design**: System works with multiple AI providers interchangeably
- **Evaluator-Optimizer Pattern**: 
  - Evaluators: Analyze resumes and job descriptions to identify gaps and opportunities
  - Optimizers: Generate specific recommendations and implement changes
- **Dynamic Thinking Budget**: Allocates computational resources based on task complexity
- **Task-based Model Selection**: Intelligently selects models based on specific requirements

### Current Model Configuration
- **Primary Models**:
  - Anthropic Claude: Used for complex reasoning tasks and high-quality content generation
  - Google Gemini: Used for structured data extraction and analysis
  - OpenAI GPT-4: Optional fallback for certain tasks
- **Model Selection Logic**: Located in `app/services/model_selector.py`
- **Thinking Budget Management**: Located in `app/services/thinking_budget.py`
- **Prompt Templates**: Located in `app/services/prompts.py`

### Token/Cost Considerations
- **Average Token Usage**: ~5,000-15,000 tokens per resume customization
- **Cost Targets**: Maintain average cost < $0.10 per resume customization
- **Optimization Strategy**: Use cheaper/smaller models for simpler tasks
- **Parallel Processing**: Should reduce token usage through more focused prompts
- **Token Tracking**: Monitor and log token usage for each request

### AI Performance Metrics
- **Current Quality Score**: ~7.5/10 based on manual evaluations
- **Target Quality Score**: ≥8.5/10 while maintaining or reducing costs
- **Accuracy Targets**: 
  - 95%+ for keyword identification
  - 90%+ for relevant experience matching
  - 85%+ for improvement suggestions
- **Current Processing Time**: 30-60+ seconds for full customization
- **Target Processing Time**: <30 seconds for full customization

## AI Component Structure
- `/app/services/ats_service.py`: ATS scoring and analysis
- `/app/services/customization_service.py`: Resume customization logic
- `/app/services/diff_service.py`: Resume difference visualization
- `/app/services/model_selector.py`: AI model selection logic
- `/app/services/pydanticai_service.py`: Core PydanticAI implementation
- `/app/services/pydanticai_optimizer.py`: Optimizer implementation
- `/app/services/prompts.py`: Prompt templates and generation
- `/app/services/thinking_budget.py`: Token budget management

## Development Guidelines

### Prompt Engineering
- **Prompt Structure**: 
  - Clear instructions first
  - Context and examples next
  - Specific output format requirements last
- **Chunking Strategy**: Break large contexts into manageable pieces
- **Use Examples**: Include few-shot examples for complex tasks
- **Output Format**: Be explicit about required output format (JSON, Markdown, etc.)
- **Error Handling**: Include instructions for handling edge cases

### Model Integration
- **Provider Abstraction**: All model calls should go through the model selector
- **Token Counting**: Track token usage for all model calls
- **Error Handling**: Implement retries and fallbacks for API failures
- **Rate Limiting**: Respect API rate limits with appropriate backoff strategies
- **Async Implementation**: Use asyncio for concurrent API calls

### Testing AI Components
- **Evaluation Sets**: Use test suite in `/tests/integration/`
- **Deterministic Testing**: Set a seed when possible for reproducibility
- **Quality Metrics**: Use human evaluation frameworks for subjective tasks
- **Performance Benchmarks**: Compare token usage and response time against baselines
- **Mock Responses**: Use mocks for unit tests to avoid API costs

## Getting Started

1. Create a development branch:
```bash
gh issue develop {ISSUE_NUMBER} --repo JoshuaOliphant/ResumeAIAssistant --name feature/issue-{ISSUE_NUMBER}
```

2. Explore the existing AI components:
```bash
grep -r "class.*Evaluator\|class.*Optimizer" app/services/
```

3. Run existing tests to understand current behavior:
```bash
python -c "import tests.integration.test_pydanticai; tests.integration.test_pydanticai.test_optimizer()"
```

4. Implement your changes according to the issue requirements

5. Test your implementation with realistic inputs:
```bash
python -c "import tests.integration.test_resume_diff; tests.integration.test_resume_diff.test_customization()"
```

6. Create a pull request when complete:
```bash
gh pr create --title "Fix/Feature: Issue #{ISSUE_NUMBER} description" --body "Resolves #{ISSUE_NUMBER}"
```

## Example Prompt Templates

### Resume Analysis Prompt
```python
def create_resume_analysis_prompt(resume_text, job_description):
    return f"""
    # Task
    Analyze the resume below against the provided job description.
    
    # Resume
    {resume_text}
    
    # Job Description
    {job_description}
    
    # Instructions
    1. Identify key skills and qualifications mentioned in the job description
    2. Evaluate how well the resume demonstrates these skills
    3. Score the resume's match on a scale of 1-100
    4. Provide specific improvement suggestions
    
    # Output Format
    Return a JSON object with these fields:
    - match_score: number between 1-100
    - missing_keywords: array of strings
    - improvement_suggestions: array of objects with 'section' and 'suggestion' fields
    """
```

### Resume Customization Prompt
```python
def create_resume_customization_prompt(resume_text, job_description, analysis_results):
    return f"""
    # Task
    Customize the resume below to better match the job description.
    
    # Resume
    {resume_text}
    
    # Job Description
    {job_description}
    
    # Analysis Results
    {json.dumps(analysis_results, indent=2)}
    
    # Instructions
    1. Rewrite parts of the resume to better match the job description
    2. Focus on the sections highlighted in the analysis
    3. Maintain the candidate's experience and qualifications (no fabrication)
    4. Emphasize relevant skills and experiences
    
    # Output Format
    Return the customized resume in markdown format.
    """
```

## Additional Resources
- **PydanticAI Documentation**: Review services/README_OPENAI_AGENTS.md
- **Model Provider Documentation**:
  - Anthropic Claude: https://docs.anthropic.com/claude/
  - Google Gemini: https://ai.google.dev/docs/gemini_api_overview
  - OpenAI: https://platform.openai.com/docs/api-reference
- **Token Optimization Strategies**: services/thinking_budget.py
- **Test Fixtures**: Browse tests/integration/ for examples

Good luck with your implementation! Feel free to ask clarifying questions about the AI system as you work.