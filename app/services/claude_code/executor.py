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
            
            # Create a structured prompt based on the template with clearer instructions
            complete_prompt = f"""
# Resume Customization Task

## Input Files
- Resume: {resume_content}
- Job Description: {job_description_content}

## Execution Instructions
{self.prompt_template}

## Expected Outputs
You will need to output two primary files and several optional intermediate files.

Instead of directly creating files (since you may not have permission), please PRINT the contents to stdout as follows:

1. First, perform your complete analysis of the resume and job description
2. Then output the customized resume with this exact format:
   ```
   === BEGIN CUSTOMIZED RESUME ===
   [Your complete customized resume content in markdown format]
   === END CUSTOMIZED RESUME ===
   ```

3. Then output the detailed change summary with this exact format:
   ```
   === BEGIN CUSTOMIZATION SUMMARY ===
   [Your complete customization summary in markdown format]
   === END CUSTOMIZATION SUMMARY ===
   ```

4. If you generate any intermediate files, output them with this format:
   ```
   === BEGIN INTERMEDIATE FILE: [filename] ===
   [Content of the intermediate file]
   === END INTERMEDIATE FILE: [filename] ===
   ```

## IMPORTANT INSTRUCTIONS
- Do NOT attempt to use Write or Edit tools as they might require permissions
- Instead, print ALL output using the special format markers above
- Ensure your customized resume is complete and properly formatted in markdown
- Include detailed change summary with match scores and specific changes made
- Use the exact BEGIN/END markers shown above to delimit each output
            """
            
            return complete_prompt
            
        except Exception as e:
            logger.error(f"Error building prompt: {str(e)}")
            raise ClaudeCodeExecutionError(f"Error building prompt: {str(e)}")
    
    def _process_output(self, output: str) -> Dict[str, Any]:
        """
        Process the output from Claude Code.
        
        Args:
            output: The raw output from Claude Code
            
        Returns:
            Parsed output as a dictionary
        """
        try:
            # Initialize result dictionary
            result = {
                "raw_output": output,
                "customized_resume": "",
                "customization_summary": "",
                "intermediate_files": {}
            }
            
            # Process output now
            
            # Check if we have the special format markers in the output
            # Extract customized resume
            resume_pattern = r'=== BEGIN CUSTOMIZED RESUME ===\s*([\s\S]*?)\s*=== END CUSTOMIZED RESUME ==='
            resume_match = re.search(resume_pattern, output)
            if resume_match:
                result["customized_resume"] = resume_match.group(1).strip()
                logger.info("Successfully extracted customized resume from output")
            
            # Extract customization summary
            summary_pattern = r'=== BEGIN CUSTOMIZATION SUMMARY ===\s*([\s\S]*?)\s*=== END CUSTOMIZATION SUMMARY ==='
            summary_match = re.search(summary_pattern, output)
            if summary_match:
                result["customization_summary"] = summary_match.group(1).strip()
                logger.info("Successfully extracted customization summary from output")
            
            # Extract any intermediate files
            intermediate_pattern = r'=== BEGIN INTERMEDIATE FILE: ([\w\.-]+) ===\s*([\s\S]*?)\s*=== END INTERMEDIATE FILE: \1 ==='
            intermediate_matches = re.finditer(intermediate_pattern, output)
            
            for match in intermediate_matches:
                filename = match.group(1)
                content = match.group(2).strip()
                result["intermediate_files"][filename] = content
                logger.info(f"Extracted intermediate file: {filename}")
            
            # If we found any of these, consider the extraction successful
            if result["customized_resume"] or result["customization_summary"] or result["intermediate_files"]:
                logger.info("Successfully extracted data using format markers")
                return result
            
            # Fallback: Try to parse JSON output if any is present
            json_match = re.search(r'({[\s\S]*})', output)
            if json_match:
                json_str = json_match.group(1)
                try:
                    # Parse the JSON output
                    parsed_output = json.loads(json_str)
                    
                    # Extract relevant parts if available
                    if "customized_resume" in parsed_output:
                        result["customized_resume"] = parsed_output.get("customized_resume", "")
                    if "customization_summary" in parsed_output:
                        result["customization_summary"] = parsed_output.get("customization_summary", "")
                    if "intermediate_files" in parsed_output:
                        result["intermediate_files"] = parsed_output.get("intermediate_files", {})
                    
                    logger.info("Successfully parsed JSON output")
                    return result
                except json.JSONDecodeError:
                    logger.warning(f"Found JSON-like content but failed to parse it: {json_str[:100]}...")
            
            # Fallback: Look for markdown content in the output
            if not result["customized_resume"]:
                # Try to find a markdown resume anywhere in the output
                md_sections = re.split(r'\n#{1,2} ', output)
                for section in md_sections:
                    if 'resume' in section.lower()[:50] and len(section) > 200:
                        result["customized_resume"] = section.strip()
                        logger.info("Found potential resume content in output")
                        break
            
            # If we have no resume content, generate a warning
            if not result["customized_resume"]:
                result["customized_resume"] = "Claude Code did not produce a valid customized resume. Please try again."
                logger.warning("No resume content found in output")
            
            # If we have no summary content, generate a warning
            if not result["customization_summary"]:
                result["customization_summary"] = "Claude Code execution failed to produce a valid summary."
                logger.warning("No summary content found in output")
            
            return result
            
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
        
        # Use specified timeout or default from config (30-minute default)
        timeout_seconds = timeout or settings.CLAUDE_CODE_TIMEOUT or 1800  # 30-minute default
        
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
            
            # Print to console and log for streaming
            print(f"[Claude Code] Starting customization for task: {task_id}")
            log_streamer.add_log(task_id, f"Starting customization with 30-minute timeout. Be patient, this may take a while...")
            
            # Set paths for Claude working directory and output
            claude_work_dir = os.path.join(temp_dir, ".claude_work")
            os.makedirs(claude_work_dir, exist_ok=True)
            
            # Create temp directories for input and output
            input_dir = os.path.join(claude_work_dir, "input")
            output_dir = os.path.join(claude_work_dir, "output")
            os.makedirs(input_dir, exist_ok=True)
            os.makedirs(output_dir, exist_ok=True)
            
            # Write input files to the input directory
            prompt_file_path = os.path.join(input_dir, "prompt.txt")
            with open(prompt_file_path, 'w') as f:
                f.write(prompt)
                
            # Define command with the correct arguments for streaming
            # Don't use --dangerously-skip-permissions since it requires interactive approval
            command = [
                self.claude_cmd, 
                "--print",  # Non-interactive mode
                "--output-format", "stream-json",  # Use streaming JSON output format
                "--verbose",  # Enable verbose output for debugging
                # Read the prompt from file instead of passing it directly
                f"@{prompt_file_path}"
            ]
            
            # Log the command we're using
            log_streamer.add_log(
                task_id, 
                f"Executing Claude Code command in directory: {temp_dir}",
                level="info",
                metadata={"command": " ".join(command)}
            )
            
            # Create process with pipes for stdout/stderr to enable streaming
            # Prepare environment variables for the subprocess
            env = os.environ.copy()
            env["CLAUDE_CODE_OUTPUT_DIR"] = output_dir
            
            # Create a script that instructs how to save output
            instructions_file = os.path.join(input_dir, "INSTRUCTIONS.md")
            with open(instructions_file, 'w') as f:
                f.write(f"""# IMPORTANT: Save Output Instructions

Please save your output files directly to the current working directory:
- Save the customized resume as 'new_customized_resume.md'
- Save the customization summary as 'customized_resume_output.md'
- Save any intermediate files to the current directory

Do not create subdirectories for output files.
""")
            
            # Now run the process with environment variables
            process = subprocess.Popen(
                command,
                cwd=temp_dir,  # Run in temp directory where files will be created
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
                env=env  # Pass environment variables
            )
            
            # Set up output queues and start output threads
            stdout_queue = queue.Queue(maxsize=1000)  # Increased buffer size
            stderr_queue = queue.Queue(maxsize=1000)
            
            # Log start of process execution
            log_streamer.add_log(
                task_id, 
                "Starting Claude Code process with customization task", 
                level="info",
                metadata={"command": " ".join(command)}
            )
            
            # Start streaming threads for stdout and stderr with improved naming
            stdout_thread = log_streamer.start_output_stream(
                task_id=task_id, 
                process_output=process.stdout, 
                output_queue=stdout_queue,
                stream_type="stdout"
            )
            
            stderr_thread = log_streamer.start_output_stream(
                task_id=task_id, 
                process_output=process.stderr, 
                output_queue=stderr_queue,
                stream_type="stderr"
            )
            
            # Wait for process to complete with timeout
            start_time = time.time()
            last_progress_time = start_time
            last_activity_time = start_time
            
            # Collect all stdout
            all_stdout = []
            stdout_buffer = []  # Buffer for collecting JSON output
            json_mode = False   # Flag to track if we're collecting JSON output
            
            # Send periodic progress updates based on elapsed time
            def update_progress(elapsed):
                # Calculate progress percentage based on elapsed time relative to timeout
                # Maximum 90% progress from time-based estimation
                progress_pct = min(90, int((elapsed / timeout_seconds) * 100))
                
                # Send progress update with appropriate message
                if progress_pct < 25:
                    message = "Analyzing resume and job requirements"
                elif progress_pct < 50:
                    message = "Generating customization strategy"
                elif progress_pct < 75:
                    message = "Applying optimization to resume sections"
                else:
                    message = "Finalizing customized resume"
                    
                # Add log with progress information
                log_streamer.add_log(
                    task_id, 
                    f"Progress: {message}",
                    level="info",
                    metadata={
                        "progress_pct": progress_pct,
                        "elapsed_time": elapsed,
                        "timeout": timeout_seconds
                    }
                )
                
                return last_progress_time
            
            # Poll the process until it completes or times out
            try:
                while process.poll() is None:
                    # Check if timeout has been exceeded
                    elapsed = time.time() - start_time
                    
                    # Send progress updates every 15 seconds if no other activity
                    if time.time() - last_progress_time > 15:
                        last_progress_time = time.time()
                        update_progress(elapsed)
                    
                    # Check for timeout
                    if elapsed > timeout_seconds:
                        log_streamer.add_log(
                            task_id, 
                            f"Process exceeded timeout limit of {timeout_seconds}s, terminating",
                            level="error"
                        )
                        process.terminate()
                        try:
                            process.wait(timeout=5)  # Give it 5 seconds to terminate
                        except subprocess.TimeoutExpired:
                            process.kill()  # Force kill if it doesn't terminate
                            log_streamer.add_log(task_id, "Process did not terminate, force killing", level="error")
                        
                        raise subprocess.TimeoutExpired(command, timeout_seconds)
                    
                    # Get any available stdout
                    stdout_activity = False
                    try:
                        while True:
                            line = stdout_queue.get_nowait()
                            if line is None:  # End of stream
                                break
                                
                            stdout_activity = True
                            last_activity_time = time.time()
                            
                            # Add to our collection of stdout lines
                            all_stdout.append(line)
                            
                            # First check if the line itself is JSON (from stream-json)
                            try:
                                if line.startswith("{") and line.endswith("}"):
                                    # This looks like JSON data directly from stream-json
                                    parsed = json.loads(line)
                                    if isinstance(parsed, dict):
                                        # Extract useful information from the streaming JSON output
                                        if "content" in parsed:
                                            # This is a content chunk, log it
                                            content = parsed.get("content", "")
                                            if content.strip():
                                                log_streamer.add_log(
                                                    task_id,
                                                    f"Output: {content}",
                                                    level="info"
                                                )
                                        elif "status" in parsed:
                                            # This is a status update
                                            status = parsed.get("status")
                                            if status == "complete":
                                                log_streamer.add_log(
                                                    task_id,
                                                    "Claude Code processing completed",
                                                    level="info",
                                                    metadata=parsed
                                                )
                                            else:
                                                log_streamer.add_log(
                                                    task_id, 
                                                    f"Status: {status}",
                                                    level="info",
                                                    metadata=parsed
                                                )
                            except json.JSONDecodeError:
                                # Not JSON or invalid JSON, continue with normal processing
                                pass
                                
                            # Check if line indicates JSON output beginning/ending in markdown format
                            if "```json" in line:
                                json_mode = True
                                stdout_buffer = []  # Clear buffer to start collecting
                            elif "```" in line and json_mode:
                                json_mode = False
                                # Process collected JSON content 
                                if stdout_buffer:
                                    json_content = "\n".join(stdout_buffer)
                                    try:
                                        # Try to parse and log any structured output
                                        import json
                                        parsed = json.loads(json_content)
                                        if isinstance(parsed, dict):
                                            # Extract and log specific parts of structured output
                                            log_message = "Received structured output from Claude Code"
                                            
                                            # If we have a progress update, use it
                                            if "progress" in parsed:
                                                log_message = f"Progress: {parsed.get('message', 'Processing')} ({parsed.get('progress', 0)}%)"
                                            
                                            # If we have a status update, show it
                                            elif "status" in parsed:
                                                log_message = f"Status: {parsed.get('status')}: {parsed.get('message', '')}"
                                                
                                            # If we have a completion message, show it
                                            elif "done" in parsed or "completed" in parsed:
                                                log_message = "Completed Claude Code processing"
                                                
                                            # Log the event with metadata
                                            log_streamer.add_log(
                                                task_id, 
                                                log_message,
                                                level="info",
                                                metadata={"structured_output": parsed}
                                            )
                                    except:
                                        pass
                            elif json_mode:
                                # Collect JSON content
                                stdout_buffer.append(line)
                                
                    except queue.Empty:
                        pass
                        
                    # Check stderr similarly
                    stderr_activity = False
                    try:
                        while True:
                            line = stderr_queue.get_nowait()
                            if line is None:  # End of stream
                                break
                                
                            stderr_activity = True
                            last_activity_time = time.time()
                            
                            # Log stderr lines as warnings/errors
                            if "error" in line.lower() or "exception" in line.lower():
                                log_streamer.add_log(task_id, line, level="error")
                            else:
                                log_streamer.add_log(task_id, line, level="warning")
                                
                    except queue.Empty:
                        pass
                    
                    # Update progress if we had activity
                    if stdout_activity or stderr_activity:
                        last_progress_time = time.time()
                        
                    # Check if process is inactive for too long (potential hanging)
                    if time.time() - last_activity_time > 60 and elapsed > 120:
                        log_streamer.add_log(
                            task_id, 
                            f"No output from process for 60 seconds, may be hanging",
                            level="warning"
                        )
                        # Only reset the timer, don't take action yet
                        last_activity_time = time.time()
                        
                    # Sleep briefly to avoid tight loop
                    time.sleep(0.1)
                
                # Process is done, get any remaining output
                try:
                    while True:
                        line = stdout_queue.get_nowait()
                        if line is None:  # End of stream
                            break
                        all_stdout.append(line)
                except queue.Empty:
                    pass
                
                # Try to join the threads with timeout
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
                
                # Add detailed completion log
                elapsed_time = time.time() - start_time
                log_streamer.add_log(
                    task_id, 
                    f"Claude Code process completed in {elapsed_time:.1f} seconds with return code {return_code}",
                    level="info"
                )
                
                # Check for output files directly in the temp directory
                log_streamer.add_log(task_id, f"Searching for output files in {temp_dir}")
                
                # First check temp_dir
                files_found = os.listdir(temp_dir)
                log_streamer.add_log(
                    task_id, 
                    f"Found {len(files_found)} files in temp directory", 
                    level="info",
                    metadata={"files": files_found}
                )
                
                # Look specifically for our expected output files
                customized_resume_path = os.path.join(temp_dir, "new_customized_resume.md")
                summary_path = os.path.join(temp_dir, "customized_resume_output.md")
                
                if not os.path.exists(customized_resume_path):
                    log_streamer.add_log(
                        task_id, 
                        f"Customized resume file not found at expected path: {customized_resume_path}",
                        level="warning"
                    )
                    # Look for any markdown files that might be the resume
                    potential_resume_files = [f for f in files_found if f.endswith('.md') and 'resume' in f.lower()]
                    if potential_resume_files:
                        customized_resume_path = os.path.join(temp_dir, potential_resume_files[0])
                        log_streamer.add_log(
                            task_id, 
                            f"Using alternative file as resume: {potential_resume_files[0]}",
                            level="info"
                        )
                
                if not os.path.exists(summary_path):
                    log_streamer.add_log(
                        task_id, 
                        f"Summary file not found at expected path: {summary_path}",
                        level="warning"
                    )
                    # Look for any markdown files that might be the summary
                    potential_summary_files = [f for f in files_found if f.endswith('.md') and 'summary' in f.lower()]
                    if potential_summary_files:
                        summary_path = os.path.join(temp_dir, potential_summary_files[0])
                        log_streamer.add_log(
                            task_id, 
                            f"Using alternative file as summary: {potential_summary_files[0]}",
                            level="info"
                        )
                
                # Process the output from Claude Code's stdout
                log_streamer.add_log(task_id, "Processing Claude Code output")
                parsed_results = self._process_output(stdout_content)
                
                # Write the extracted content back to files in the temp directory
                if parsed_results["customized_resume"]:
                    resume_output_path = os.path.join(temp_dir, "new_customized_resume.md")
                    try:
                        with open(resume_output_path, 'w') as f:
                            f.write(parsed_results["customized_resume"])
                        log_streamer.add_log(
                            task_id, 
                            f"Wrote extracted customized resume to {resume_output_path}",
                            level="info"
                        )
                    except Exception as e:
                        log_streamer.add_log(
                            task_id, 
                            f"Error writing customized resume: {str(e)}",
                            level="error"
                        )
                else:
                    log_streamer.add_log(
                        task_id,
                        "No customized resume content extracted from output",
                        level="warning"
                    )
                
                if parsed_results["customization_summary"]:
                    summary_output_path = os.path.join(temp_dir, "customized_resume_output.md")
                    try:
                        with open(summary_output_path, 'w') as f:
                            f.write(parsed_results["customization_summary"])
                        log_streamer.add_log(
                            task_id, 
                            f"Wrote extracted customization summary to {summary_output_path}",
                            level="info"
                        )
                    except Exception as e:
                        log_streamer.add_log(
                            task_id, 
                            f"Error writing customization summary: {str(e)}",
                            level="error"
                        )
                else:
                    log_streamer.add_log(
                        task_id,
                        "No customization summary content extracted from output",
                        level="warning"
                    )
                
                # Write any intermediate files extracted from output
                if parsed_results.get("intermediate_files"):
                    log_streamer.add_log(task_id, "Writing extracted intermediate files")
                    for filename, content in parsed_results["intermediate_files"].items():
                        file_path = os.path.join(temp_dir, filename)
                        try:
                            with open(file_path, 'w') as f:
                                f.write(content)
                            log_streamer.add_log(
                                task_id,
                                f"Wrote intermediate file: {filename} ({len(content)} bytes)",
                                level="info"
                            )
                        except Exception as e:
                            log_streamer.add_log(
                                task_id,
                                f"Error writing intermediate file {filename}: {str(e)}",
                                level="warning"
                            )
                                
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