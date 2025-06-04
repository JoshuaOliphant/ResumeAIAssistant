# Resume AI Assistant

A powerful application that analyzes resumes against job descriptions and helps users optimize their resumes for specific job opportunities using Claude Code integration.

## Features

- **Claude Code Integration**: Leverage the Claude CLI for enhanced resume customization with truthfulness verification
- **Resume Customization**: Automatically customize resumes based on job descriptions using an evaluator-optimizer workflow
- **Diff View**: Compare original and customized resumes with enhanced side-by-side visualization and section-level analysis
- **Cover Letter Generation**: Generate tailored cover letters based on resume and job description
- **Real-time Progress Updates**: Track long-running operations with WebSocket updates
- **Evaluation History Management**: Limit in-memory history size to avoid excessive memory usage (configure with `EVALUATION_HISTORY_SIZE`)

## Setup and Installation

### Prerequisites

- Python 3.9+
- Node.js 14+ (for frontend development)
- Claude Code CLI ([installation instructions](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/overview))
- Anthropic API Key (for Claude Code)

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/ResumeAIAssistant.git
   cd ResumeAIAssistant
   ```

2. Run the setup script:

   For macOS/Linux:
   ```
   ./setup.sh
   ```

   For Windows:
   ```
   setup.bat
   ```

   The setup script will:
   - Check for required dependencies (Python 3.9+, Node.js 14+, uv)
   - Create a Python virtual environment
   - Install Python dependencies
   - Install Node.js dependencies for the frontend
   - Create a sample `.env.local` file

3. Manual installation (alternative to step 2):
   ```
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   uv sync  # Syncs dependencies from pyproject.toml
   cd nextjs-frontend && npm install && cd ..
   ```

## Running the Application

### Backend

Start the backend server with:

```
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv run uvicorn main:app --host 0.0.0.0 --port 5001 --reload
```

### Frontend

Start the Next.js frontend development server:

```
cd nextjs-frontend
npm run dev
```

Then open your browser to `http://localhost:3000`

### Verifying Your Setup

After running the setup script, you can verify that everything is correctly installed:

```
python verify_setup.py
```

This script will check:
- Python environment and required packages
- SpaCy language model installation
- Node.js version and frontend dependencies
- Configuration files
- Claude CLI installation

To check only SpaCy model installation:
```
python verify_setup.py --spacy
```

### Configuration

The setup script creates a sample `.env.local` file with configuration options. Before running the application, update this file with your actual values:

```
# Application Configuration
PORT=5001
HOST=0.0.0.0

# Anthropic API Configuration
ANTHROPIC_API_KEY=your-anthropic-api-key

# Logfire Configuration (Optional)
LOGFIRE_API_KEY=your-logfire-api-key
LOGFIRE_PROJECT=resume-ai-assistant
ENVIRONMENT=development
LOG_LEVEL=INFO
LOGFIRE_ENABLED=false

# SpaCy Configuration (Optional)
# SPACY_MODEL_PATH=/path/to/your/en_core_web_sm-3.7.0-py3-none-any.whl
```

### SpaCy Language Models

The application uses SpaCy for natural language processing. The setup script attempts to download and install the required SpaCy model (`en_core_web_sm`), but network issues may sometimes prevent this.

If you encounter errors installing the SpaCy model, you have several options:

1. **Retry the download manually**:
   ```
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   python -m spacy download en_core_web_sm
   ```

2. **Download the model separately**:
   - Download the wheel file from [SpaCy's GitHub releases](https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.0/en_core_web_sm-3.7.0-py3-none-any.whl)
   - Install it manually:
     ```
     source .venv/bin/activate  # On Windows: .venv\Scripts\activate
     python -m pip install /path/to/downloaded/en_core_web_sm-3.7.0-py3-none-any.whl
     ```

3. **Use a custom model path**:
   - Update your `.env.local` file with the path to the downloaded wheel file:
     ```
     SPACY_MODEL_PATH=/path/to/your/en_core_web_sm-3.7.0-py3-none-any.whl
     ```

You can verify if the SpaCy model is correctly installed by running:
```
python verify_setup.py --spacy
```

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
- **Claude Code Integration**: Leverages Claude CLI as a subprocess-driven agent for resume customization
- **Evaluator-Optimizer Pattern**: Assesses resume-job fit and iteratively improves it with explicit truth verification
- **WebSocket Progress Tracking**: Real-time updates for long-running processes
- **Evidence Tracking**: Verification system that ensures customizations maintain truthfulness

### Architecture Diagram

```
┌─────────────────┐     ┌───────────────────┐     ┌───────────────────┐
│  Web/API Layer  │────►│  Resume Manager   │────►│  Claude Code      │
│  (FastAPI)      │     │  (Python Service) │     │  Agent Executor   │
└─────────────────┘     └───────────────────┘     └───────────────────┘
                                                         │
                                                         ▼
                                                ┌───────────────────┐
                                                │  Output Processor │
                                                │  & File Manager   │
                                                └───────────────────┘
```

### Key Services
- **Claude Code Executor**: Runs Claude CLI as a subprocess with specialized prompts
- **Progress Tracker**: Manages task state and provides real-time updates
- **Job & Resume Analyzer**: Extracts structured information for customization
- **ATS Compatibility Checker**: Ensures resumes pass Applicant Tracking Systems

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
- Critical issues can be worked on in parallel:
  - Parallel Processing Architecture (backend)
  - Improved Diff Visualization (frontend)
  - Progress Tracking System (frontend/backend)

## Claude Code Integration

The application uses Claude Code CLI as a subprocess to customize resumes with an advanced workflow:

### Customization Workflow

1. **Research & Analysis**: Analyzes resume and job description to extract requirements and skills
2. **Enhancement Planning**: Identifies gaps and creates an evidence-backed optimization plan  
3. **Parallel Implementation**: Optimizes different resume sections concurrently
4. **Verification & Refinement**: Ensures all customizations are truthful with evidence tracking
5. **Finalization**: Generates the customized resume and detailed change summary

### Truth Verification Protocol

The system follows strict verification rules:

1. **Acceptable Without Verification**:
   - Reorganizing existing content
   - Rephrasing for clarity/impact
   - Highlighting relevant parts of verified experience

2. **Requiring Explicit Verification**:
   - Any quantitative metrics or percentages
   - Specific technical skills not in original resume
   - Project details not in original resume
   - Leadership roles or responsibilities

3. **Never Permitted**:
   - Fabricating experiences or achievements
   - Adding unverified skills
   - Exaggerating metrics or impact
   - Creating fictional projects

## Future Enhancements

1. Semantic matching to find similar terms across job description and resume
2. Industry and position-level specific customization templates
3. Enhanced verification with external data sources (LinkedIn, GitHub)
4. Personal branding optimization
5. Mock interview preparation based on resume-job gap analysis
6. Format and structure analysis with accessibility recommendations
7. Feature flag system for gradual rollout of new Claude Code capabilities
