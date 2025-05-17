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
import queue
import time
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List

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
1. Generate customized resume in markdown format and save it to a file named "new_customized_resume.md"
2. Create a detailed change summary and save it to a file named "customized_resume_output.md"
3. Both output files should be saved in the current working directory (not in subdirectories)
4. Save any intermediate files for verification

IMPORTANT: After completing all your analysis, you MUST directly create the output markdown files "new_customized_resume.md" and "customized_resume_output.md" in the current directory. Do not rely on the platform to extract content from your response.
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
            # Clean the output to handle only the JSON part
            # Look for content that looks like JSON output
            import re
            json_match = re.search(r'({[\s\S]*})', output)
            
            if json_match:
                json_str = json_match.group(1)
                try:
                    # Parse the JSON output
                    parsed_output = json.loads(json_str)
                    
                    # Extract the relevant parts
                    return {
                        "customized_resume": parsed_output.get("customized_resume", ""),
                        "customization_summary": parsed_output.get("customization_summary", ""),
                        "intermediate_files": parsed_output.get("intermediate_files", {})
                    }
                except json.JSONDecodeError:
                    logger.warning(f"Found JSON-like content but failed to parse it: {json_str[:100]}...")
            
            # If output contains markdown content, try to extract it directly
            markdown_content = ""
            summary_content = ""
            
            # Try to find files in the executor's current working directory
            if os.path.exists("new_customized_resume.md"):
                try:
                    with open("new_customized_resume.md", 'r') as f:
                        markdown_content = f.read()
                    logger.info("Found new_customized_resume.md in current working directory")
                except Exception as e:
                    logger.error(f"Error reading new_customized_resume.md: {str(e)}")
            
            if os.path.exists("customized_resume_output.md"):
                try:
                    with open("customized_resume_output.md", 'r') as f:
                        summary_content = f.read()
                    logger.info("Found customized_resume_output.md in current working directory")
                except Exception as e:
                    logger.error(f"Error reading customized_resume_output.md: {str(e)}")
                    
            # If not found in current directory, try looking in the working directory
            if not markdown_content or not summary_content:
                temp_dir = self.working_dir
                logger.info(f"Searching for output files in working directory: {temp_dir}")
                for filename in os.listdir(temp_dir):
                    full_path = os.path.join(temp_dir, filename)
                    
                    if filename == "new_customized_resume.md" and os.path.isfile(full_path) and not markdown_content:
                        with open(full_path, 'r') as f:
                            markdown_content = f.read()
                            logger.info(f"Found new_customized_resume.md in {temp_dir}")
                            
                    elif filename == "customized_resume_output.md" and os.path.isfile(full_path) and not summary_content:
                        with open(full_path, 'r') as f:
                            summary_content = f.read()
                            logger.info(f"Found customized_resume_output.md in {temp_dir}")
            
            if markdown_content or summary_content:
                logger.info("Found markdown files directly in output directory")
                return {
                    "customized_resume": markdown_content,
                    "customization_summary": summary_content,
                    "raw_output": output
                }
                
            # If all else fails
            logger.warning("Claude Code output is not valid JSON and no files found, returning raw output")
            return {
                "raw_output": output,
                "customized_resume": "Claude Code did not produce a valid customized resume. Please try again.",
                "customization_summary": "Claude Code execution failed to produce a valid summary."
            }
        except Exception as e:
            logger.error(f"Error processing Claude Code output: {str(e)}")
            return {
                "raw_output": output,
                "customized_resume": "Error processing Claude Code output.",
                "customization_summary": f"Error: {str(e)}"
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
        output_path: str,
        task_id: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute the resume customization using Claude Code.
        
        Args:
            resume_path: Path to the resume file
            job_description_path: Path to the job description file
            output_path: Path where to save the customized resume
            task_id: Optional task ID for logging
            timeout: Optional custom timeout in seconds (default uses config value)
            
        Returns:
            Dictionary with paths to the customized resume and summary
        """
        # Import here to avoid circular imports
        from app.core.config import settings
        from app.services.claude_code.log_streamer import get_log_streamer
        
        # Use specified timeout or default from config
        timeout_seconds = timeout or settings.CLAUDE_CODE_TIMEOUT or 600  # 10-minute default
        
        try:
            # Set up task ID for logging if not provided
            if not task_id:
                task_id = f"claude-code-{uuid.uuid4().hex}"
                
            # Get log streamer
            log_streamer = get_log_streamer()
            log_stream = log_streamer.create_log_stream(task_id)
            
            # Log starting message
            logger.info(f"Starting Claude Code execution with task ID: {task_id}")
            log_streamer.add_log(task_id, f"Starting Claude Code customization (timeout: {timeout_seconds}s)")
            
            # Prepare files and context
            temp_dir = self._create_temp_workspace()
            log_streamer.add_log(task_id, f"Created temporary workspace at {temp_dir}")
            
            # Build the complete prompt with template and inputs
            prompt = self._build_prompt(resume_path, job_description_path)
            log_streamer.add_log(task_id, "Built prompt from resume and job description")
            
            # Execute Claude Code as subprocess with our prompt
            logger.info("Executing Claude Code for resume customization")
            log_streamer.add_log(task_id, "Executing Claude Code process...")
            
            # Print to console 
            print(f"[Claude Code] Starting customization for task: {task_id}")
            
            command = [
                self.claude_cmd, 
                "--print", prompt,
                "--output-format", "json",  # Use JSON format as required with --verbose
                "--verbose",  # Enable verbose output
            ]
            
            # Create process with pipes for stdout/stderr to enable streaming
            process = subprocess.Popen(
                command,
                cwd=temp_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1  # Line buffered
            )
            
            # Set up output queue and start output threads
            stdout_queue = queue.Queue()
            stderr_queue = queue.Queue()
            
            # Start streaming threads for stdout and stderr
            stdout_thread = log_streamer.start_output_stream(task_id, process.stdout, stdout_queue)
            stderr_thread = log_streamer.start_output_stream(task_id, process.stderr, stderr_queue)
            
            # Wait for process to complete with timeout
            start_time = time.time()
            
            # Collect all stdout
            all_stdout = []
            
            # Poll the process until it completes or times out
            try:
                while process.poll() is None:
                    # Check if timeout has been exceeded
                    elapsed = time.time() - start_time
                    if elapsed > timeout_seconds:
                        process.terminate()
                        try:
                            process.wait(timeout=5)  # Give it 5 seconds to terminate
                        except subprocess.TimeoutExpired:
                            process.kill()  # Force kill if it doesn't terminate
                        
                        log_streamer.add_log(task_id, f"ERROR: Process timed out after {elapsed:.1f} seconds")
                        raise subprocess.TimeoutExpired(command, timeout_seconds)
                    
                    # Get any available stdout
                    try:
                        while True:
                            line = stdout_queue.get_nowait()
                            if line is None:  # End of stream
                                break
                            all_stdout.append(line)
                    except queue.Empty:
                        pass
                    
                    # Sleep briefly to avoid tight loop
                    time.sleep(0.1)
                
                # Get any remaining stdout
                try:
                    while True:
                        line = stdout_queue.get_nowait()
                        if line is None:  # End of stream
                            break
                        all_stdout.append(line)
                except queue.Empty:
                    pass
                
                # Join the stdout thread
                stdout_thread.join(timeout=5)
                stderr_thread.join(timeout=5)
                
                # Check return code
                return_code = process.returncode
                if return_code != 0:
                    error_logs = log_streamer.get_logs(task_id)
                    error_msg = "\n".join(error_logs[-10:]) if error_logs else "Unknown error"
                    log_streamer.add_log(task_id, f"Process failed with return code {return_code}")
                    raise ClaudeCodeExecutionError(f"Claude Code execution failed with code {return_code}: {error_msg}")
                
                # Join stdout lines
                stdout_content = "\n".join(all_stdout)
                
                # Process the output and extract results
                log_streamer.add_log(task_id, "Processing Claude Code output")
                parsed_results = self._process_output(stdout_content)
                
                # Save and return customized resume
                log_streamer.add_log(task_id, f"Saving results to {output_path}")
                result = self._save_results(parsed_results, output_path)
                
                log_streamer.add_log(task_id, "Claude Code execution completed successfully")
                return result
                
            except subprocess.TimeoutExpired:
                log_streamer.add_log(task_id, f"ERROR: Claude Code execution timed out after {timeout_seconds} seconds")
                logger.error(f"Claude Code execution timed out after {timeout_seconds} seconds")
                raise ClaudeCodeExecutionError(f"Claude Code execution timed out after {timeout_seconds} seconds")
                
        except Exception as e:
            if task_id:
                log_streamer.add_log(task_id, f"ERROR: {str(e)}")
            logger.error(f"Error executing Claude Code: {str(e)}")
            raise ClaudeCodeExecutionError(f"Error executing Claude Code: {str(e)}")

    def customize_resume_with_progress(
        self, 
        resume_path: str, 
        job_description_path: str, 
        output_path: str, 
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, str]:
        """
        Execute the resume customization with progress tracking.
        
        Args:
            resume_path: Path to the resume file
            job_description_path: Path to the job description file
            output_path: Path where to save the customized resume
            progress_callback: Callback function for progress updates
            timeout: Optional custom timeout in seconds
            
        Returns:
            Dictionary with task_id for tracking progress
        """
        # Import here to avoid circular imports
        from app.core.config import settings
        from app.services.claude_code.log_streamer import get_log_streamer
        
        # Set up task ID and progress tracking
        task_id = str(uuid.uuid4())
        
        # Initialize log streamer
        log_streamer = get_log_streamer()
        log_streamer.create_log_stream(task_id)
        
        # Set initial progress status
        progress_status = {
            "task_id": task_id,
            "status": "initializing",
            "progress": 0,
            "message": "Preparing customization process",
            "logs": []
        }
        
        # Log initial message
        log_streamer.add_log(task_id, "Initializing Claude Code customization with progress tracking")
        
        if progress_callback:
            progress_callback(progress_status)
        
        # Start Claude Code in background thread
        thread = threading.Thread(
            target=self._run_customization_with_progress,
            args=(resume_path, job_description_path, output_path, progress_callback, task_id, timeout)
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
        task_id: str,
        timeout: Optional[int] = None
    ):
        """
        Execute the customization with progress updates.
        
        Args:
            resume_path: Path to the resume file
            job_description_path: Path to the job description file
            output_path: Path where to save the customized resume
            progress_callback: Callback function for progress updates
            task_id: Unique ID for the task
            timeout: Optional custom timeout in seconds
        """
        # Import log streamer
        from app.services.claude_code.log_streamer import get_log_streamer
        log_streamer = get_log_streamer()
        
        # Print to console for real-time tracking
        print(f"[Claude Code] Starting customization task {task_id} with timeout: {timeout or 'default'} seconds")
        
        try:
            def update_progress(status: str, progress: int, message: str):
                # Add to log
                log_streamer.add_log(task_id, f"Progress: {message} ({progress}%)")
                
                # Print to console for real-time tracking
                print(f"[Claude Code] {task_id}: Progress: {message} ({progress}%)")
                
                if progress_callback:
                    # Get current logs
                    logs = log_streamer.get_logs(task_id)
                    
                    # Call progress callback with status, progress, and logs
                    progress_callback({
                        "task_id": task_id,
                        "status": status,
                        "progress": progress,
                        "message": message,
                        "logs": logs
                    })
            
            # Phase 1: Research & Analysis
            update_progress("analyzing", 10, "Analyzing resume and job description")
            
            # Execute the actual customization with streaming logs
            try:
                # This will run with logs streamed to the log_streamer
                update_progress("executing", 30, "Executing Claude Code")
                
                # Run customization with our task_id for log streaming
                result = self.customize_resume(
                    resume_path=resume_path,
                    job_description_path=job_description_path,
                    output_path=output_path,
                    task_id=task_id,
                    timeout=timeout
                )
                
                # Check if output files exist and create them if not
                if not os.path.exists(output_path):
                    print(f"[Claude Code] {task_id}: WARNING: Output file not found at {output_path}, generating basic file")
                    # Write something to the output path so we don't get an error
                    with open(output_path, 'w') as f:
                        f.write("# Customized Resume\n\nClaude Code did not produce a valid customized resume. Please try again.")
                
                summary_path = os.path.join(os.path.dirname(output_path), "customized_resume_output.md")
                if not os.path.exists(summary_path):
                    print(f"[Claude Code] {task_id}: WARNING: Summary file not found at {summary_path}, generating basic file")
                    # Write something to the summary path
                    with open(summary_path, 'w') as f:
                        f.write("# Customization Summary\n\nClaude Code did not produce a valid customization summary. Please try again.")
                
                # Process is complete, update progress
                update_progress("processing", 90, "Finalizing customization")
                
                # Complete
                update_progress("completed", 100, "Customization complete")
                
            except subprocess.TimeoutExpired:
                logger.error(f"Claude Code execution timed out for task {task_id}")
                update_progress("error", 0, "Claude Code execution timed out")
                raise
            
        except Exception as e:
            logger.error(f"Error in customization task {task_id}: {str(e)}")
            log_streamer.add_log(task_id, f"ERROR: {str(e)}")
            
            if progress_callback:
                # Get logs for error context
                logs = log_streamer.get_logs(task_id)
                
                progress_callback({
                    "task_id": task_id,
                    "status": "error",
                    "progress": 0,
                    "message": f"Error: {str(e)}",
                    "logs": logs
                })