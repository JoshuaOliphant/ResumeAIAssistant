# CLAUDE.md - Guidelines for ResumeAIAssistant

## Backend Development
- Setup: `python -m pip install -e .` (installs from pyproject.toml)
- Run server: `python -m uvicorn main:app --host 0.0.0.0 --port 5000 --reload`
- Start script: `./start_server.sh` (runs on port 8080)
- Run all tests: `python test_api.py`
- Run single test: `python -c "import test_api; test_api.test_NAME()"`
- Run basic tests: `python test_basic.py`
- This project uses `uv`, not `pip` for dependency management.
- Add new dependencies with `uv add ...`.
- This project has a virtual environment that needs to be sourced.
- After sourcing the virtual environment, `uv sync` can be used to sync the dependencies.
- Use uv to start the application with `uv run uvicorn main:app --host 0.0.0.0 --port 5001 --reload`
- Always source the virtual environment and use `uv sync` to install existing dependencies in pyproject.toml. If you need to install a new dependency, use `uv add`, never use pip.

## Project Architecture

### Core Components
- **PydanticAI Architecture**: Model-agnostic AI system using the evaluator-optimizer pattern
- **Multi-Model Support**: Integration with Anthropic Claude, Google Gemini, and OpenAI
- **Parallel Processing**: Resume sections are processed concurrently for improved performance
- **Dynamic Thinking Budget**: Resource allocation system for AI processing

### Key Services
- **Parallel Customization Service**: Processes resume sections in parallel
- **Task Scheduler**: Manages concurrent AI model requests with prioritization
- **Resume Segmenter**: Splits resumes into logical sections for parallel processing
- **Results Aggregator**: Combines parallel processing results into unified output

## Frontend Development (Next.js)
- Location: `/nextjs-frontend` directory
- Setup: `cd nextjs-frontend && npm install`
- Run development server: `npm run dev` (runs on port 3000)
- Build for production: `npm run build`
- Start production server: `npm run start`
- Lint code: `npm run lint`

### Frontend Tech Stack
- **Next.js 14**: React framework with App Router
- **TypeScript**: For type safety and better developer experience
- **Tailwind CSS**: For styling
- **shadcn/ui**: Component library for consistent UI (Button, Card, Form, etc.)
- **React Hook Form**: Form validation with Zod
- **next-themes**: Theme management (light/dark mode)
- **WebSockets**: For real-time progress updates

### Frontend Structure
- `/app`: Next.js App Router pages
- `/components`: Reusable React components
  - `/ui`: shadcn UI components
- `/lib`: Utility functions and API client
  - `client.ts`: API client for FastAPI backend (port 5000)
  - `utils.ts`: Helper functions

### UI Components
- **ResumeDiffView**: Enhanced diff visualization with side-by-side comparison
- **Progress Tracking**: Real-time updates for long-running processes
- **Section Analysis**: Expandable sections showing what changed and why 
- **ATS Improvement Metrics**: Shows score improvement for resume sections

### API Integration
- Backend connection configured in `lib/client.ts`
- API calls use fetch with proper error handling
- All API endpoints from FastAPI backend are implemented
- Authentication via JWT tokens stored in localStorage
- WebSocket connection for real-time progress updates

## Claude Prompts
- Location: `/claude_prompts` directory
- Purpose: Specialized prompts for Claude Code instances
- Available templates:
  - `backend_issue_prompt.md`: Backend development tasks
  - `frontend_issue_prompt.md`: Frontend development tasks
  - `ai_model_issue_prompt.md`: AI model integration tasks
  - `pr_review_feedback_prompt.md`: PR feedback implementation

## Git Conventions
- Write concise, descriptive commit messages
- Use present tense in commit messages
- Prefix commits with type: "Fix:", "Feature:", "Refactor:", etc.
- DO NOT include "Generated with Claude" footer in commits

## Environment Variables
- `ANTHROPIC_API_KEY`: Required for Claude AI integration
- `SECRET_KEY`: JWT secret key (auto-generated if not provided)
- `PORT`: Port for the application (default: 5000)

## Database
- SQLite database at `./resume_app.db`
- Created automatically on application startup
- No migrations needed - schema created with `Base.metadata.create_all()`
- Data models in `app/models/` (SQLAlchemy ORM)
- For deployment to fly.io, can use LiteFS for distributed SQLite

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

## Project Planning
- Project planning is documented in `planning_scratchpad.md`
- Issues are organized into epics in GitHub
- Critical issues can be worked on in parallel:
  - Parallel Processing Architecture (backend)
  - Improved Diff Visualization (frontend)
  - Progress Tracking System (frontend/backend)
- Each issue has clear sections for description, tasks, dependencies, and estimates