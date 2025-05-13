"""
Claude Code Executor Service

This module implements a service for executing resume customization tasks
via Claude Code as a subprocess. It handles building prompts, managing execution,
and processing outputs.
"""

import os
import json
import uuid
import shutil
import logging
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Dict, Any, Optional, Callable

logger = logging.getLogger(__name__)

class ClaudeCodeExecutionError(Exception):
    """Exception raised when Claude Code execution fails"""
    pass

class ClaudeCodeExecutor:
    """
    Service for executing Claude Code as a subprocess for resume customization tasks.
    
    This service handles:
    - Building prompts from resume and job description
    - Executing Claude Code as a subprocess
    - Managing temporary workspaces
    - Processing outputs from Claude Code
    - Progress tracking for long-running tasks
    """
    
    def __init__(
        self, 
        working_dir: str, 
        prompt_template_path: str, 
        claude_cmd: str = "claude"
    ):
        """
        Initialize the Claude Code Executor.
        
        Args:
            working_dir: Directory for work files and output
            prompt_template_path: Path to the prompt template file
            claude_cmd: Command to execute Claude Code (default: "claude")
        """
        self.working_dir = working_dir
        self.prompt_template = self._load_prompt_template(prompt_template_path)
        self.claude_cmd = claude_cmd
        
    def _load_prompt_template(self, path: str) -> str:
        """
        Load the prompt template from a file.
        
        Args:
            path: Path to the prompt template file
            
        Returns:
            The content of the prompt template file
        """
        try:
            with open(path, 'r') as f:
                return f.read()
        except FileNotFoundError:
            logger.error(f"Prompt template file not found: {path}")
            raise ClaudeCodeExecutionError(f"Prompt template file not found: {path}")
            
    def _create_temp_workspace(self) -> str:
        """
        Create a temporary workspace directory for Claude Code execution.
        
        Returns:
            Path to the temporary workspace directory
        """
        temp_dir = os.path.join(
            self.working_dir, 
            f"claude_workspace_{uuid.uuid4().hex}"
        )
        os.makedirs(temp_dir, exist_ok=True)
        return temp_dir
        
    def _build_prompt(self, resume_path: str, job_description_path: str) -> str:
        """
        Build the complete prompt for Claude Code.
        
        Args:
            resume_path: Path to the resume file
            job_description_path: Path to the job description file
            
        Returns:
            The complete prompt for Claude Code
        """
        try:
            # Load the resume and job description contents
            with open(resume_path, 'r') as f:
                resume_content = f.read()
                
            with open(job_description_path, 'r') as f:
                job_description_content = f.read()
            
            # Create a structured prompt based on the template
            complete_prompt = f"""
# Resume Customization Task

## Input Files
- Resume: {resume_content}
- Job Description: {job_description_content}

## Execution Instructions
{self.prompt_template}

## Expected Outputs
1. Generate customized resume in markdown format (new_customized_resume.md)
2. Create a detailed change summary (customized_resume_output.md)
3. Save all intermediate files for verification
            """
            
            return complete_prompt
            
        except Exception as e:
            logger.error(f"Error building prompt: {str(e)}")
            raise ClaudeCodeExecutionError(f"Error building prompt: {str(e)}")
    
    def _process_output(self, output: str) -> Dict[str, Any]:
        """
        Process the JSON output from Claude Code.
        
        Args:
            output: The raw output from Claude Code
            
        Returns:
            Parsed output as a dictionary
        """
        try:
            # Parse the JSON output
            parsed_output = json.loads(output)
            
            # Extract the relevant parts
            return {
                "customized_resume": parsed_output.get("customized_resume", ""),
                "customization_summary": parsed_output.get("customization_summary", ""),
                "intermediate_files": parsed_output.get("intermediate_files", {})
            }
        except json.JSONDecodeError:
            # If output isn't valid JSON, try to find the markdown files referenced in the text
            logger.warning("Claude Code output is not valid JSON, attempting to extract file references")
            return {
                "raw_output": output,
                "customized_resume": "",
                "customization_summary": ""
            }
    
    def _save_results(self, results: Dict[str, Any], output_path: str) -> Dict[str, Any]:
        """
        Save the customization results to files.
        
        Args:
            results: The processed results from Claude Code
            output_path: Path where to save the customized resume
            
        Returns:
            Dictionary with paths to the saved files
        """
        try:
            # Ensure output directory exists
            output_dir = os.path.dirname(output_path)
            os.makedirs(output_dir, exist_ok=True)
            
            # Save customized resume
            with open(output_path, 'w') as f:
                f.write(results.get("customized_resume", ""))
            
            # Save customization summary
            summary_path = os.path.join(output_dir, "customized_resume_output.md")
            with open(summary_path, 'w') as f:
                f.write(results.get("customization_summary", ""))
            
            # Save intermediate files if available
            for file_name, content in results.get("intermediate_files", {}).items():
                file_path = os.path.join(output_dir, file_name)
                with open(file_path, 'w') as f:
                    if isinstance(content, (dict, list)):
                        json.dump(content, f, indent=2)
                    else:
                        f.write(content)
            
            return {
                "customized_resume_path": output_path,
                "customization_summary_path": summary_path
            }
            
        except Exception as e:
            logger.error(f"Error saving results: {str(e)}")
            raise ClaudeCodeExecutionError(f"Error saving results: {str(e)}")
            
    def customize_resume(
        self, 
        resume_path: str, 
        job_description_path: str, 
        output_path: str
    ) -> Dict[str, Any]:
        """
        Execute the resume customization using Claude Code.
        
        Args:
            resume_path: Path to the resume file
            job_description_path: Path to the job description file
            output_path: Path where to save the customized resume
            
        Returns:
            Dictionary with paths to the customized resume and summary
        """
        try:
            # Prepare files and context
            temp_dir = self._create_temp_workspace()
            
            # Build the complete prompt with template and inputs
            prompt = self._build_prompt(resume_path, job_description_path)
            
            # Execute Claude Code as subprocess with our prompt
            logger.info("Executing Claude Code for resume customization")
            command = [
                self.claude_cmd, 
                "--print", prompt,
                "--output-format", "json",
            ]
            
            result = subprocess.run(
                command,
                cwd=temp_dir,
                capture_output=True,
                text=True,
                timeout=600  # 10-minute timeout
            )
            
            if result.returncode != 0:
                logger.error(f"Claude Code execution failed with return code {result.returncode}")
                logger.error(f"stderr: {result.stderr}")
                raise ClaudeCodeExecutionError(f"Claude Code execution failed: {result.stderr}")
            
            # Process the output and extract results
            parsed_results = self._process_output(result.stdout)
            
            # Save and return customized resume
            return self._save_results(parsed_results, output_path)
            
        except subprocess.TimeoutExpired:
            logger.error("Claude Code execution timed out")
            raise ClaudeCodeExecutionError("Claude Code execution timed out")
        except Exception as e:
            logger.error(f"Error executing Claude Code: {str(e)}")
            raise ClaudeCodeExecutionError(f"Error executing Claude Code: {str(e)}")

    def customize_resume_with_progress(
        self, 
        resume_path: str, 
        job_description_path: str, 
        output_path: str, 
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Dict[str, str]:
        """
        Execute the resume customization with progress tracking.
        
        Args:
            resume_path: Path to the resume file
            job_description_path: Path to the job description file
            output_path: Path where to save the customized resume
            progress_callback: Callback function for progress updates
            
        Returns:
            Dictionary with task_id for tracking progress
        """
        # Set up progress tracking
        task_id = str(uuid.uuid4())
        progress_status = {
            "task_id": task_id,
            "status": "initializing",
            "progress": 0,
            "message": "Preparing customization process"
        }
        
        if progress_callback:
            progress_callback(progress_status)
        
        # Start Claude Code in background thread
        thread = threading.Thread(
            target=self._run_customization_with_progress,
            args=(resume_path, job_description_path, output_path, progress_callback, task_id)
        )
        thread.daemon = True
        thread.start()
        
        return {"task_id": task_id}
    
    def _run_customization_with_progress(
        self, 
        resume_path: str, 
        job_description_path: str, 
        output_path: str, 
        progress_callback: Optional[Callable[[Dict[str, Any]], None]],
        task_id: str
    ):
        """
        Execute the customization with progress updates.
        
        Args:
            resume_path: Path to the resume file
            job_description_path: Path to the job description file
            output_path: Path where to save the customized resume
            progress_callback: Callback function for progress updates
            task_id: Unique ID for the task
        """
        try:
            def update_progress(status: str, progress: int, message: str):
                if progress_callback:
                    progress_callback({
                        "task_id": task_id,
                        "status": status,
                        "progress": progress,
                        "message": message
                    })
            
            # Phase 1: Research & Analysis
            update_progress("analyzing", 10, "Analyzing resume and job description")
            
            # Prepare execution
            temp_dir = self._create_temp_workspace()
            prompt = self._build_prompt(resume_path, job_description_path)
            
            # Start execution
            update_progress("executing", 30, "Executing Claude Code")
            
            command = [
                self.claude_cmd, 
                "--print", prompt,
                "--output-format", "json",
            ]
            
            result = subprocess.run(
                command,
                cwd=temp_dir,
                capture_output=True,
                text=True,
                timeout=600  # 10-minute timeout
            )
            
            if result.returncode != 0:
                raise ClaudeCodeExecutionError(f"Claude Code execution failed: {result.stderr}")
            
            # Process results
            update_progress("processing", 80, "Processing customization results")
            parsed_results = self._process_output(result.stdout)
            self._save_results(parsed_results, output_path)
            
            # Complete
            update_progress("completed", 100, "Customization complete")
            
        except Exception as e:
            logger.error(f"Error in customization task {task_id}: {str(e)}")
            if progress_callback:
                progress_callback({
                    "task_id": task_id,
                    "status": "error",
                    "progress": 0,
                    "message": f"Error: {str(e)}"
                })