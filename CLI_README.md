# Resume Customizer CLI

A command-line tool that uses PydanticAI to customize a resume for a specific job description.

## Prerequisites

1. Python 3.7 or higher
2. PydanticAI installed and configured
   - Follow the installation instructions in the PydanticAI documentation
3. Required Python dependencies installed
4. Click Python package installed (`pip install click` or `uv pip install click`)

## Installation

1. Install required dependencies:

```bash
uv pip install -r requirements-cli.txt
```

## Usage

```bash
./resume_customizer_cli.py --resume path/to/your/resume.md --job-url https://example.com/job-posting
```

### Options

- `--resume`, `-r`: Path to the resume file (markdown or text format) [required]
- `--job-url`, `-j`: URL to the job description [required]
- `--output-dir`, `-o`: Directory to store the customized resume and related files [default: ./customized_resume_output]
- `--verbose`, `-v`: Enable verbose output

### Example

```bash
./resume_customizer_cli.py -r original_resume.md -j https://www.linkedin.com/jobs/view/12345 -o ./output -v
```

## How It Works

1. The tool uses PydanticAI's evaluator-optimizer pattern to:
   - Analyze the job description URL
   - Read and evaluate your resume
   - Research industry standards and ATS optimization
   - Create a customized version of your resume
   - Generate a report of changes and improvements

2. PydanticAI utilizes a multi-stage AI workflow to:
   - Research job requirements
   - Analyze your background
   - Implement targeted improvements
   - Verify and refine the results

3. The output includes:
   - A customized resume in markdown format
   - A summary of changes made
   - An ATS optimization report
   - Interview preparation suggestions

## Required Python Packages

This tool requires the following Python packages to be installed:
- pydantic_ai
- click
- requests
- markdown
- nltk
- logfire
- difflib
- bs4 (BeautifulSoup)

## Model Support

The tool supports multiple AI model providers:
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- Google (Gemini)

Model selection is handled automatically based on availability, cost, and capabilities. You can configure preferred models in the configuration file.