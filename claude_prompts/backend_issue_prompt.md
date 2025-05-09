# ResumeAIAssistant Backend Development Assignment

## Task Overview
You are assigned to work on issue #{ISSUE_NUMBER} for the ResumeAIAssistant project. You'll need to:

1. Retrieve the issue details using GitHub CLI
2. Understand the codebase structure
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
3. **FastAPI Backend**: Handles resume analysis, customization, and user management
4. **SQLite Database**: Stores user data, resumes, job descriptions, and customization results

## Key Backend Concepts

### Core Architecture
- **FastAPI Framework**: All API endpoints use FastAPI's async approach
- **Pydantic Models**: Used for request/response validation and data transfer
- **SQLAlchemy ORM**: Used for database interactions
- **Evaluator-Optimizer Pattern**: Core of resume customization logic
  - Evaluators analyze resumes against job descriptions
  - Optimizers generate customization plans and implement changes
- **Dynamic Thinking Budget**: System for allocating computational resources based on task complexity
- **Task-based Model Selection**: Intelligently selects AI models based on specific requirements

### Performance Considerations
- **Current Bottlenecks**: Resume customization process can take 30-60+ seconds
- **Optimization Goals**: Reduce processing time by 50%+ through parallelization
- **Target Response Time**: Interactive API endpoints should respond in <100ms
- **Benchmarking**: Use the existing test suite to measure performance improvements
- **Caching Strategy**: Consider implementing appropriate caching mechanisms

### Backend Structure
- `/app/api/endpoints`: API endpoint implementations grouped by resource
- `/app/core`: Core configuration, security, and utility functions
- `/app/db`: Database connection and session management
- `/app/models`: SQLAlchemy ORM models
- `/app/schemas`: Pydantic schemas for request/response validation
- `/app/services`: Business logic implementation and AI service integration

## Development Guidelines

### Code Style
- Follow PEP 8 guidelines with 4-space indentation and 100 character line limit
- Imports order: stdlib, third-party, local (with blank lines between groups)
- Type hints required for all function parameters and return values
- Use Google docstring format for documentation
- Use snake_case for variables/functions, PascalCase for classes

### Error Handling
- Use try/except with specific exceptions, avoid bare except clauses
- Log errors properly using the app.core.logging module
- Return appropriate HTTP status codes with descriptive error messages
- Fail gracefully with sensible defaults when possible

### Testing
- Test files named test_*.py
- Each endpoint should have at least one test case
- Mock external services (AI APIs) when testing
- Include performance tests for optimization work

### Database
- Use SQLAlchemy ORM for all database interactions
- Define relationships and constraints in the model definitions
- Use migrations for schema changes (when needed)
- Ensure proper transaction handling and connection pooling

### Dependency Management
- Use `uv` (not pip) for package management
- Add new dependencies with `uv add ...`
- Source the virtual environment before running commands
- Sync dependencies with `uv sync`

## Getting Started

1. Create a development branch:
```bash
gh issue develop {ISSUE_NUMBER} --repo JoshuaOliphant/ResumeAIAssistant --name feature/issue-{ISSUE_NUMBER}
```

2. Start the development server:
```bash
uv run uvicorn main:app --host 0.0.0.0 --port 5001 --reload
```

3. Run tests to ensure everything is working:
```bash
python test_api.py
```

4. Implement your changes according to the issue requirements

5. Add appropriate tests for your changes

6. Run tests again to ensure everything still works:
```bash
python test_api.py
```

7. Create a pull request when complete:
```bash
gh pr create --title "Fix/Feature: Issue #{ISSUE_NUMBER} description" --body "Resolves #{ISSUE_NUMBER}"
```

## Additional Resources
- API Documentation: Available at http://localhost:5001/docs when running locally
- Database Schema: Review the models in app/models/ directory
- Logging: Use app.core.logging module for consistent logging
- Authentication: JWT-based authentication implemented in app.core.security

Good luck with your implementation! Feel free to ask clarifying questions about the codebase as you work.