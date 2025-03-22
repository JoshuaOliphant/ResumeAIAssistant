# CLAUDE.md - Guidelines for ResumeAIAssistant

## Commands
- Run server: `python -m uvicorn main:app --host 0.0.0.0 --port 5000 --reload`
- Run all tests: `python test_api.py`
- Run single test: `python -c "import test_api; test_api.test_NAME()"`
- Run basic tests: `python test_basic.py`

## Code Style
- Imports: Group by stdlib, third-party, local with blank line separators
- Typing: Use type hints for function parameters and return values
- Docstrings: Use triple quotes with Args/Returns sections for functions
- Error handling: Use try/except with specific exceptions, log errors
- Naming: snake_case for variables/functions, PascalCase for classes
- Formatting: 4-space indentation, 100 char line limit
- API endpoints: Group by resource in app/api/endpoints/
- Services: Keep business logic in app/services/
- Exception handling: Catch exceptions at service level, propagate appropriate responses
- Pydantic: Use for schema validation and data transfer
- Async/await: Use for API endpoints and service functions

## Testing
- Test files should be named test_*.py
- Each endpoint should have at least one test case
- Mock external services when testing