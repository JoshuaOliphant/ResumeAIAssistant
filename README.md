# Resume AI Assistant

A powerful application that analyzes resumes against job descriptions using ATS (Applicant Tracking System) analysis, provides customization suggestions, and helps users optimize their resumes for specific job opportunities.

## Features

- **ATS Analysis**: Analyze resumes against job descriptions to identify keyword matches and suggest improvements
- **Resume Customization**: Automatically customize resumes based on job descriptions
- **Diff View**: Compare original and customized resumes with section-level analysis
- **Cover Letter Generation**: Generate tailored cover letters based on resume and job description

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
   uv add -r requirements.txt
   ```

## Running the Application

Start the application with:

```
uv run uvicorn main:app --host 0.0.0.0 --port 5000 --reload
```

Then open your browser to `http://localhost:5000`

## Testing

The project includes integration tests that run against the running application.

### Running Tests

Make sure the application is running, then:

```
# Run all integration tests
python run_integration_tests.py

# List available tests
python run_integration_tests.py --list

# Run a specific test
python run_integration_tests.py test_ats
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
├── static/                 # Static files (JS, CSS)
├── templates/              # HTML templates
├── tests/                  # Test suite
│   └── integration/        # Integration tests
├── main.py                 # Application entry point
└── run_integration_tests.py # Test runner script
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

## Future Enhancements

1. Advanced NLP using spaCy for better keyword extraction
2. Semantic matching to find similar terms (not just exact matches)
3. Section-based analysis of resumes
4. Multi-factor scoring system
5. Industry and position-level specific analysis
6. Format and structure analysis
7. Enhanced suggestion engine with actionable advice
