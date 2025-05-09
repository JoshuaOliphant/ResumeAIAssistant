# Claude Code Prompts for ResumeAIAssistant

This directory contains specialized prompt templates for assigning development tasks to Claude Code instances. Each template is designed for a specific type of development task in the ResumeAIAssistant project.

## Available Templates

### 1. Backend Development (`backend_issue_prompt.md`)
For tasks related to FastAPI endpoints, database models, services, and backend performance optimizations.

Key focus areas:
- FastAPI implementation details
- SQLAlchemy and database interactions
- Performance considerations and benchmarks
- Error handling and testing requirements

### 2. Frontend Development (`frontend_issue_prompt.md`)
For tasks related to Next.js components, UI/UX improvements, and frontend interactions.

Key focus areas:
- Next.js and React component architecture
- Responsive design and accessibility requirements
- Browser compatibility guidelines
- Performance expectations and metrics

### 3. AI Model Development (`ai_model_issue_prompt.md`)
For tasks related to AI model integration, prompt engineering, and optimization.

Key focus areas:
- PydanticAI architecture and evaluator-optimizer pattern
- Prompt templates and examples
- Token/cost considerations and optimizations
- Model selection and integration patterns

## How to Use

1. Identify which template best matches the GitHub issue being assigned
2. Replace the `{ISSUE_NUMBER}` placeholder with the actual issue number
3. Use the resulting prompt when creating a new Claude Code instance

Example:
```bash
cat claude_prompts/frontend_issue_prompt.md | sed 's/{ISSUE_NUMBER}/14/g' | claude-cli
```

## Customizing Templates

Feel free to modify these templates to include additional context specific to particular issues. You might want to add:

- Links to relevant documentation
- More specific requirements for the task
- Examples of similar implementations
- Acceptance criteria
- Performance benchmarks

## Maintaining Templates

As the project evolves, these templates should be updated to reflect:
- New architectural decisions
- Updated coding standards
- New dependencies or tools
- Refined best practices

## Template Structure

Each template follows a consistent structure:
1. Task Overview
2. Setup Instructions
3. Project Architecture
4. Key Concepts for the domain
5. Development Guidelines
6. Getting Started steps
7. Additional Resources