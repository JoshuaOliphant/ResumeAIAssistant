# Resume AI Assistant

A powerful application that analyzes resumes against job descriptions using ATS (Applicant Tracking System) analysis, provides customization suggestions, and helps users optimize their resumes for specific job opportunities.

## Features

- **ATS Analysis**: Analyze resumes against job descriptions to identify keyword matches and suggest improvements
- **Resume Customization**: Automatically customize resumes based on job descriptions using a streamlined sequential pipeline
- **Diff View**: Compare original and customized resumes with enhanced side-by-side visualization and section-level analysis
- **Cover Letter Generation**: Generate tailored cover letters based on resume and job description
- **Real-time Progress Updates**: Track long-running operations with WebSocket updates

## Setup and Installation

### Prerequisites

- Python 3.9+
- Node.js 14+ (for frontend development)

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/ResumeAIAssistant.git
   cd ResumeAIAssistant
   ```

2. Set up a virtual environment and install dependencies:
   ```
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   uv sync  # Syncs dependencies from pyproject.toml
   ```

## Running the Application

### Backend

Start the backend server with:

```
uv run uvicorn main:app --host 0.0.0.0 --port 5001 --reload
```

### Frontend

Start the Next.js frontend development server:

```
cd nextjs-frontend
npm install
npm run dev
```

Then open your browser to `http://localhost:3000`

## Testing

The project includes integration tests that run against the running application.

### Running Tests

Make sure the application is running, then:

```
# Run all tests
python test_api.py

# Run a specific test
python -c "import test_api; test_api.test_NAME()"

# Run basic tests
python test_basic.py
```

Each test file is named according to its function (e.g., `test_ats.py`, `test_diff_service.py`). All API endpoints have at least one test case, and external services like Claude API are mocked during testing.

## Project Architecture

### Core Components
- **PydanticAI Architecture**: Model-agnostic AI system using the evaluator-optimizer pattern
- **Multi-Model Support**: Integration with Anthropic Claude, Google Gemini, and OpenAI
- **Holistic Processing**: End-to-end resume analysis and optimization
- **Dynamic Thinking Budget**: Resource allocation system for AI processing

### Key Services
- **ResumeCustomizer**: End-to-end resume customization service
- **EvidenceTracker**: Ensures truthfulness in resume customizations
- **ProgressReporter**: Provides real-time updates via WebSockets
- **Agent Factory**: Creates specialized AI agents for each customization stage

### TODO: Cleanup Deprecated Code
- Remove deprecated endpoints in `app/api/endpoints/customize.py` and `app/api/endpoints/enhance_customize.py` that return deprecation notices
- Remove the deprecated Next.js API route in `nextjs-frontend/app/api/customize/plan/route.ts`
- These endpoints were part of the old architecture and have been replaced by the four-stage workflow with WebSocket progress reporting

### Using ``ResumeCustomizer``

The ``ResumeCustomizer`` orchestrates evaluation, planning, implementation, and
verification. A minimal usage example:

```python
from app.services.resume_customizer.executor import ResumeCustomizer

customizer = ResumeCustomizer()
result = await customizer.customize_resume(
    resume_content=my_resume,
    job_description=my_job_desc,
    template_id="modern",
)
print(result["customized_resume"])
```

## Project Structure

```
ResumeAIAssistant/
├── app/                    # Main application package
│   ├── api/                # API endpoints
│   ├── core/               # Core functionality
│   ├── models/             # Database models
│   ├── schemas/            # Pydantic schemas
│   └── services/           # Business logic services
├── claude_prompts/         # Templates for Claude Code instances
├── nextjs-frontend/        # Next.js frontend application
│   ├── app/                # Next.js App Router pages
│   ├── components/         # React components
│   │   └── ui/             # shadcn UI components
│   └── lib/                # Utility functions and API client
├── static/                 # Static files (JS, CSS)
├── templates/              # HTML templates
├── tests/                  # Test suite
│   └── integration/        # Integration tests
├── main.py                 # Application entry point
└── CLAUDE.md               # Development guidelines
```

## Observability with Logfire

The application is instrumented with [Logfire](https://logfire.pydantic.dev) for comprehensive observability.

### Setting up Logfire

1. Sign up for a Logfire account at [logfire.pydantic.dev](https://logfire.pydantic.dev)
2. Create a project in the Logfire dashboard
3. Get your Logfire API key from the dashboard
4. Add Logfire configuration to your `.env.local` file:

```
LOGFIRE_API_KEY=your-logfire-api-key
LOGFIRE_PROJECT=resume-ai-assistant
ENVIRONMENT=development
LOG_LEVEL=INFO
LOGFIRE_ENABLED=true
```

### Logged Information

The application logs the following information:

- **Request/Response**: All HTTP requests and responses with timing information
- **LLM Calls**: API calls to Anthropic Claude, including parameters and response timing
- **Web Scraping**: Job description extraction details from URLs
- **Database Operations**: Critical database operations
- **Errors**: All exceptions with stack traces and context
- **Performance Metrics**: Timing information for critical operations

### Monitoring Dashboard

You can view logs and metrics in the Logfire dashboard to:

- Track application health
- Debug errors in real-time
- Analyze performance bottlenecks
- Monitor LLM API usage and costs
- Set up alerts for critical issues

## Environment Variables

The following environment variables configure deployment as described in
`spec.md`:

| Variable | Purpose |
| --- | --- |
| `ANTHROPIC_API_KEY` | Access token for Claude models |
| `TIGRIS_API_KEY` | Object storage key for file uploads |
| `ENVIRONMENT` | `production` or `development` to control logging |
| `SECRET_KEY` | JWT signing secret |
| `PORT` | Backend listening port |

### Deployment Notes

- Allocate **at least 2GB RAM** for AI processing.
- Configure LiteFS for distributed SQLite when deploying to fly.io.
- Set reasonable request timeouts for long-running jobs.

## Development Workflow

### Claude Prompts

The repository contains specialized prompt templates for Claude Code instances in the `/claude_prompts` directory:

- `backend_issue_prompt.md`: For backend development tasks
- `frontend_issue_prompt.md`: For frontend development tasks
- `ai_model_issue_prompt.md`: For AI model integration tasks
- `pr_review_feedback_prompt.md`: For implementing PR feedback

### Project Planning

- Project planning is documented in `planning_scratchpad.md`
- Issues are organized into epics in GitHub
- Critical issues are tackled sequentially to simplify coordination

## Future Enhancements

1. Advanced NLP using spaCy for better keyword extraction
2. Semantic matching to find similar terms (not just exact matches)
3. Section-based analysis of resumes with specialized analyzers
4. Multi-factor scoring system with customizable weights
5. Industry and position-level specific analysis
6. Format and structure analysis
7. Enhanced suggestion engine with actionable advice
8. Feature flag system for gradual rollout of new capabilities
