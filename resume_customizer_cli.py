#!/usr/bin/env python3
"""
Resume Customizer CLI

A command-line tool that uses Claude to customize a resume for a specific job description.
"""

import os
import sys
import subprocess
import click
import tempfile
from pathlib import Path


def read_prompt_template():
    """Read the Claude Code resume prompt template."""
    try:
        prompt_path = Path(__file__).parent / "claude_code_resume_prompt.md"
        with open(prompt_path, "r") as f:
            return f.read()
    except Exception as e:
        click.echo(f"Error reading prompt template: {e}", err=True)
        sys.exit(1)


def create_claude_code_command(resume_path, job_url, output_dir, claude_path="/Users/joshuaoliphant/.claude/local/claude"):
    """Create the claude code command to run."""
    prompt_template = read_prompt_template()
    
    # Replace template placeholders
    prompt = prompt_template.replace("{{RESUME_PATH}}", resume_path)
    prompt = prompt.replace("{{JOB_URL}}", job_url)
    
    # Create a temporary file for the prompt
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as temp_file:
        temp_file.write(prompt)
        prompt_file_path = temp_file.name
    
    # Create the command to run - we'll use a different approach to handle streaming
    # Instead of piping with shell commands, we'll use Python's file handling
    output_file = os.path.join(output_dir, "customized_resume_output.md")
    
    # Command to run claude directly with the prompt file
    claude_command = [
        claude_path,
        "-p",
        "--allowedTools", "fetch,brave-search,filesystem,memory,graph-memory,sequential-thinking,taskmaster-ai",
    ]
    
    return claude_command, prompt_file_path, output_file


@click.command()
@click.option('--resume', '-r', required=True, type=click.Path(exists=True),
              help='Path to the resume file (markdown or text format)')
@click.option('--job-url', '-j', required=True,
              help='URL to the job description')
@click.option('--output-dir', '-o', default='./customized_resume_output',
              help='Directory to store the customized resume and related files')
@click.option('--claude-path', default="/Users/joshuaoliphant/.claude/local/claude",
              help='Path to the Claude executable')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
def customize_resume(resume, job_url, output_dir, claude_path, verbose):
    """
    Customize a resume for a specific job posting using Claude Code.
    
    This tool uses Claude's agent capabilities to analyze a job description,
    evaluate your resume, and create a tailored version optimized for both
    ATS systems and human reviewers.
    """
    # Check if Claude CLI exists at the specified path
    if not os.path.exists(claude_path):
        click.echo(f"❌ Error: Claude CLI not found at '{claude_path}'", err=True)
        click.echo("\nPlease specify the correct path with --claude-path option.")
        click.echo("You can find your Claude path with: which claude")
        sys.exit(1)
    
    # Ensure the output directory exists
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    click.echo(f"🔍 Customizing resume for job at: {job_url}")
    click.echo(f"📄 Using resume from: {resume}")
    click.echo(f"📁 Output will be saved to: {output_dir}")
    
    # Get the absolute path to the resume
    resume_abs_path = str(Path(resume).resolve())
    
    # Create the claude command
    claude_command, prompt_file_path, output_file = create_claude_code_command(
        resume_abs_path, job_url, str(output_path.resolve()), claude_path
    )
    
    try:
        if verbose:
            click.echo("\n🤖 Running Claude with the following command:")
            cmd_display = " ".join(claude_command)
            click.echo(cmd_display)
            click.echo("\n⏳ This may take a few minutes. You'll see output as it's generated...\n")
        
        # Open the prompt file
        with open(prompt_file_path, 'r') as prompt_file, open(output_file, 'w') as output_f:
            # Run the claude command
            process = subprocess.Popen(
                claude_command,
                stdin=prompt_file,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1  # Line buffered
            )
            
            # Stream output in real-time, and also write to file
            click.echo("🔄 Claude is generating the customized resume:")
            click.echo("-" * 50)
            for line in process.stdout:
                # Display output to console
                click.echo(line.rstrip())
                # Write to output file
                output_f.write(line)
                output_f.flush()  # Ensure it's written immediately
            
            # Collect any stderr output
            stderr_output = process.stderr.read()
            process.wait()
        
        # Check if there was an error
        if process.returncode != 0:
            click.echo(f"❌ Error running Claude: {stderr_output}", err=True)
            sys.exit(process.returncode)
        
        click.echo("-" * 50)
        click.echo("\n✅ Resume customization complete!")
        click.echo(f"📁 Results saved to: {output_file}")
        
        # Add a message about file size
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            click.echo(f"📄 Customized resume saved ({file_size / 1024:.1f} KB)")
        else:
            click.echo("\n⚠️ Output file was not created. Check for errors in the process.")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)
    finally:
        # Clean up the temporary prompt file
        try:
            os.unlink(prompt_file_path)
        except:
            pass


if __name__ == "__main__":
    customize_resume()