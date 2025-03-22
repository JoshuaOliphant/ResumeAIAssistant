# CLAUDE.md - Guidelines for ResumeAIAssistant

## Development
- Setup: `python -m pip install -e .` (installs from pyproject.toml)
- Run server: `python -m uvicorn main:app --host 0.0.0.0 --port 5000 --reload`
- Start script: `./start_server.sh` (runs on port 8080)
- Run all tests: `python test_api.py`
- Run single test: `python -c "import test_api; test_api.test_NAME()"`
- Run basic tests: `python test_basic.py`

## Environment Variables
- `ANTHROPIC_API_KEY`: Required for Claude AI integration
- `DATABASE_URL`: PostgreSQL connection string (e.g., `postgresql://user:password@localhost:5432/dbname`)
  - Default: SQLite (`sqlite:///./resume_app.db`)
- `SECRET_KEY`: JWT secret key (auto-generated if not provided)
- `PORT`: Port for the application (default: 5000)

## Database
- SQLite for development/testing: Used by default
- PostgreSQL for production: Set `DATABASE_URL` environment variable
- Data models in `app/models/` (SQLAlchemy ORM)
- No explicit migrations; tables created with `Base.metadata.create_all()`

## Code Style
- Imports: 1) stdlib 2) third-party 3) local (with blank lines between groups)
- Typing: Use type hints for all function parameters and return values
- Docstrings: Triple quotes with Args/Returns sections using Google docstring format
- Error handling: Use try/except with specific exceptions, log errors properly
- Naming: snake_case for variables/functions, PascalCase for classes
- Formatting: 4-space indentation, 100 char line limit
- API endpoints: Group by resource in app/api/endpoints/
- Services: Business logic in app/services/, data access in app/models/
- Exception handling: Catch at service level, propagate appropriate responses
- Pydantic: Use for all schema validation and data transfer
- Async/await: Use for all API endpoints and service functions

## Testing
- Test files named test_*.py
- Each endpoint should have at least one test case
- Mock external services (Claude API) when testing
- Use pprint() for debugging API responses