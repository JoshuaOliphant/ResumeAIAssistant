# Resume Customizer CLI

A command-line tool that uses Claude to customize a resume for a specific job description.

## Prerequisites

1. Python 3.7 or higher
2. Claude CLI installed and in your PATH
   - Follow the installation instructions at: https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/overview
3. Required Claude tools enabled
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

1. The tool uses a prompt template that instructs Claude Code to:
   - Analyze the job description URL
   - Read and evaluate your resume
   - Research industry standards and ATS optimization
   - Create a customized version of your resume
   - Generate a report of changes and improvements

2. Claude Code utilizes multiple agents working in parallel to:
   - Research job requirements
   - Analyze your background
   - Implement targeted improvements
   - Verify and refine the results

3. The output includes:
   - A customized resume in markdown format
   - A summary of changes made
   - An ATS optimization report
   - Interview preparation suggestions

## Required Claude Tools

This tool requires the following Claude tools to be enabled:
- fetch
- brave-search
- filesystem
- memory
- graph-memory
- sequential-thinking
- taskmaster-ai

## Claude CLI

This tool uses the Claude CLI to invoke Claude with the appropriate tools and permissions. It utilizes the UNIX-style pipe approach for sending the prompt to Claude:

```bash
cat prompt_file.md | claude -p --allowedTools tool1,tool2,tool3 > output_file.md
```

For more information on the Claude CLI, see:
- [Claude CLI Documentation](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/overview#cli-commands)
- [Using Claude as a Unix-style Utility](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/tutorials#use-claude-as-a-unix-style-utility)