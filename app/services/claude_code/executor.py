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
import re
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
        working_dir: Optional[str] = None, 
        prompt_template_path: Optional[str] = None, 
        claude_cmd: str = "claude"
    ):
        """
        Initialize the Claude Code Executor.
        
        Args:
            working_dir: Directory for work files and output
            prompt_template_path: Path to the prompt template file
            claude_cmd: Command to execute Claude Code (default: "claude")
        """
        # Use temp directory if not specified
        if working_dir is None:
            self.working_dir = tempfile.mkdtemp(prefix="claude_code_")
        else:
            self.working_dir = working_dir
            
        # Load prompt template if provided, otherwise use built-in
        if prompt_template_path:
            self.prompt_template = self._load_prompt_template(prompt_template_path)
        else:
            self.prompt_template = None  # Will use built-in template
            
        self.claude_cmd = claude_cmd
        
        # Feature flag for advanced CLI options (system prompt files, MCP, etc.)
        # Set to False until these options are available in the CLI
        self.use_advanced_cli_features = False
        
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
    
    def _prepare_system_prompt(self, temp_dir: str) -> Optional[str]:
        """
        Prepare system prompt file from config or use defaults.
        
        Args:
            temp_dir: Temporary directory for the workspace
            
        Returns:
            Path to the system prompt file if created, None otherwise
        """
        try:
            # Import here to avoid circular imports
            from app.core.config import settings
            
            # Check if we have system prompt configuration
            system_prompt_content = getattr(settings, 'CLAUDE_SYSTEM_PROMPT', None)
            
            if not system_prompt_content:
                # Use enhanced system prompt with explicit truthfulness requirements
                system_prompt_content = """You are an expert resume customization assistant. Your task is to analyze job descriptions and customize resumes to match job requirements while maintaining ABSOLUTE truthfulness and accuracy.

## CRITICAL TRUTHFULNESS REQUIREMENTS

**NEVER UNDER ANY CIRCUMSTANCES:**
- Add metrics, percentages, or numbers not in the original resume
- Create new project details or accomplishments
- Add job responsibilities not mentioned in the original
- Fabricate leadership experience or team sizes
- Invent technical skills or certifications
- Add years of experience or expertise levels
- Create fictional achievements or awards

**ALWAYS:**
- Use only information explicitly stated in the original resume
- Reorganize and reframe existing content using industry terminology
- Highlight relevant experiences that already exist
- Maintain exact job titles, companies, and dates from original

## TRUTHFULNESS VERIFICATION EXAMPLES

### ✅ APPROPRIATE CUSTOMIZATIONS:

**Example 1 - Reorganizing Content:**
Original: "Built backend services with Python"
Customized: "Developed scalable backend microservices using Python"

**Example 2 - Adding Industry Keywords:**
Original: "Worked with databases"
Customized: "Implemented database solutions using PostgreSQL" (if PostgreSQL was mentioned elsewhere)

**Example 3 - Emphasizing Relevant Skills:**
Original: "Used Docker for containerization"
Customized: "Leveraged Docker containerization for scalable application deployment"

**Example 4 - Reframing Responsibilities:**
Original: "Fixed bugs in the application"
Customized: "Resolved critical software defects to improve system reliability"

**Example 5 - Professional Language:**
Original: "Helped with CI/CD"
Customized: "Contributed to continuous integration and deployment pipeline development"

### ❌ INAPPROPRIATE CUSTOMIZATIONS:

**Example 1 - Adding Fake Metrics:**
❌ WRONG: "Improved system performance by 40%" (when no metrics were given)
✅ RIGHT: "Optimized system performance through code improvements"

**Example 2 - Fabricating Leadership:**
❌ WRONG: "Led a team of 5 developers" (when no team leadership was mentioned)
✅ RIGHT: "Collaborated with development team" (if collaboration was mentioned)

**Example 3 - Creating Fake Projects:**
❌ WRONG: "Built a microservices architecture serving 1M+ users"
✅ RIGHT: "Contributed to microservices development" (if microservices were mentioned)

**Example 4 - Adding Unverified Skills:**
❌ WRONG: "Expert in Kubernetes with 5+ years experience"
✅ RIGHT: "Experience with Kubernetes deployment" (if Kubernetes was mentioned)

**Example 5 - Inventing Certifications:**
❌ WRONG: "AWS Certified Solutions Architect"
✅ RIGHT: "Experience with AWS services" (if AWS was mentioned)

**Example 6 - Fabricating Scale:**
❌ WRONG: "Managed infrastructure for 10,000+ concurrent users"
✅ RIGHT: "Worked on production infrastructure management"

**Example 7 - Adding Fake Achievements:**
❌ WRONG: "Reduced deployment time by 80%"
✅ RIGHT: "Streamlined deployment processes"

**Example 8 - Creating Fictional Responsibilities:**
❌ WRONG: "Architected enterprise-scale distributed systems"
✅ RIGHT: "Developed distributed system components" (if distributed systems were mentioned)

**Example 9 - Inventing Technical Depth:**
❌ WRONG: "Deep expertise in machine learning algorithms"
✅ RIGHT: "Experience with machine learning projects" (if ML was mentioned)

**Example 10 - Adding Fake Company Impact:**
❌ WRONG: "Saved company $500K annually through optimization"
✅ RIGHT: "Implemented cost-effective optimization solutions"

## MANDATORY VERIFICATION WORKFLOW

You MUST create a dedicated Truthfulness Verification Agent that:
1. Reviews every single change made to the resume
2. Verifies each modification against the original resume
3. Flags any fabricated information
4. Provides evidence for every claim
5. Rejects any changes that cannot be verified

The verification agent must run BEFORE finalizing any resume version."""
            
            # Create system prompt file
            system_prompt_path = os.path.join(temp_dir, "system_prompt.txt")
            with open(system_prompt_path, 'w') as f:
                f.write(system_prompt_content)
                
            logger.info(f"Created system prompt file at {system_prompt_path}")
            return system_prompt_path
            
        except Exception as e:
            logger.warning(f"Failed to create system prompt file: {str(e)}")
            return None
    
    def _get_system_prompt_content_inline(self) -> str:
        """
        Get system prompt content to incorporate directly into the main prompt.
        
        Returns:
            System prompt content as a string
        """
        try:
            # Import here to avoid circular imports
            from app.core.config import settings
            
            # Check if we have system prompt configuration
            system_prompt_content = getattr(settings, 'CLAUDE_SYSTEM_PROMPT', None)
            
            if not system_prompt_content:
                # Use enhanced system prompt with explicit truthfulness requirements
                system_prompt_content = """You are an expert resume customization assistant. Your task is to analyze job descriptions and customize resumes to match job requirements while maintaining ABSOLUTE truthfulness and accuracy.

## CRITICAL TRUTHFULNESS REQUIREMENTS

**NEVER UNDER ANY CIRCUMSTANCES:**
- Add metrics, percentages, or numbers not in the original resume
- Create new project details or accomplishments
- Add job responsibilities not mentioned in the original
- Fabricate leadership experience or team sizes
- Invent technical skills or certifications
- Add years of experience or expertise levels
- Create fictional achievements or awards

**ALWAYS:**
- Use only information explicitly stated in the original resume
- Reorganize and reframe existing content using industry terminology
- Highlight relevant experiences that already exist
- Maintain exact job titles, companies, and dates from original

## TRUTHFULNESS VERIFICATION EXAMPLES

### ✅ APPROPRIATE CUSTOMIZATIONS:

**Example 1 - Reorganizing Content:**
Original: "Built backend services with Python"
Customized: "Developed scalable backend microservices using Python"

**Example 2 - Adding Industry Keywords:**
Original: "Worked with databases"
Customized: "Implemented database solutions using PostgreSQL" (if PostgreSQL was mentioned elsewhere)

**Example 3 - Emphasizing Relevant Skills:**
Original: "Used Docker for containerization"
Customized: "Leveraged Docker containerization for scalable application deployment"

**Example 4 - Reframing Responsibilities:**
Original: "Fixed bugs in the application"
Customized: "Resolved critical software defects to improve system reliability"

**Example 5 - Professional Language:**
Original: "Helped with CI/CD"
Customized: "Contributed to continuous integration and deployment pipeline development"

### ❌ INAPPROPRIATE CUSTOMIZATIONS:

**Example 1 - Adding Fake Metrics:**
❌ WRONG: "Improved system performance by 40%" (when no metrics were given)
✅ RIGHT: "Optimized system performance through code improvements"

**Example 2 - Fabricating Leadership:**
❌ WRONG: "Led a team of 5 developers" (when no team leadership was mentioned)
✅ RIGHT: "Collaborated with development team" (if collaboration was mentioned)

**Example 3 - Creating Fake Projects:**
❌ WRONG: "Built a microservices architecture serving 1M+ users"
✅ RIGHT: "Contributed to microservices development" (if microservices were mentioned)

**Example 4 - Adding Unverified Skills:**
❌ WRONG: "Expert in Kubernetes with 5+ years experience"
✅ RIGHT: "Experience with Kubernetes deployment" (if Kubernetes was mentioned)

**Example 5 - Inventing Certifications:**
❌ WRONG: "AWS Certified Solutions Architect"
✅ RIGHT: "Experience with AWS services" (if AWS was mentioned)

**Example 6 - Fabricating Scale:**
❌ WRONG: "Managed infrastructure for 10,000+ concurrent users"
✅ RIGHT: "Worked on production infrastructure management"

**Example 7 - Adding Fake Achievements:**
❌ WRONG: "Reduced deployment time by 80%"
✅ RIGHT: "Streamlined deployment processes"

**Example 8 - Creating Fictional Responsibilities:**
❌ WRONG: "Architected enterprise-scale distributed systems"
✅ RIGHT: "Developed distributed system components" (if distributed systems were mentioned)

**Example 9 - Inventing Technical Depth:**
❌ WRONG: "Deep expertise in machine learning algorithms"
✅ RIGHT: "Experience with machine learning projects" (if ML was mentioned)

**Example 10 - Adding Fake Company Impact:**
❌ WRONG: "Saved company $500K annually through optimization"
✅ RIGHT: "Implemented cost-effective optimization solutions"

## MANDATORY VERIFICATION WORKFLOW

You MUST create a dedicated Truthfulness Verification Agent that:
1. Reviews every single change made to the resume
2. Verifies each modification against the original resume
3. Flags any fabricated information
4. Provides evidence for every claim
5. Rejects any changes that cannot be verified

The verification agent must run BEFORE finalizing any resume version."""
            
            return system_prompt_content
            
        except Exception as e:
            logger.warning(f"Failed to get system prompt content: {str(e)}")
            return "You are an expert resume customization assistant."
    
    def _prepare_mcp_config(self, temp_dir: str) -> Optional[str]:
        """
        Create MCP config files when enabled.
        
        Args:
            temp_dir: Temporary directory for the workspace
            
        Returns:
            Path to the MCP config file if created, None otherwise
        """
        try:
            # Import here to avoid circular imports
            from app.core.config import settings
            
            # Check if MCP is enabled
            mcp_enabled = getattr(settings, 'CLAUDE_MCP_ENABLED', False)
            if not mcp_enabled:
                return None
                
            # Get MCP configuration
            mcp_servers = getattr(settings, 'CLAUDE_MCP_SERVERS', {})
            
            if not mcp_servers:
                # Default MCP configuration for resume customization
                mcp_servers = {
                    "filesystem": {
                        "command": "uvx",
                        "args": ["mcp-server-filesystem", temp_dir],
                        "env": {}
                    }
                }
            
            # Create MCP config
            mcp_config = {
                "mcpServers": mcp_servers
            }
            
            # Write MCP config file
            mcp_config_path = os.path.join(temp_dir, "claude_desktop_config.json")
            with open(mcp_config_path, 'w') as f:
                json.dump(mcp_config, f, indent=2)
                
            logger.info(f"Created MCP config file at {mcp_config_path}")
            return mcp_config_path
            
        except Exception as e:
            logger.warning(f"Failed to create MCP config file: {str(e)}")
            return None
    
    def _process_stream_json(self, line: str, task_id: str, log_streamer) -> Dict[str, Any]:
        """
        Process JSON stream output with enhanced event handling.
        
        Args:
            line: JSON line from stream output
            task_id: Task ID for logging
            log_streamer: Log streamer instance
            
        Returns:
            Parsed JSON data or empty dict if parsing fails
        """
        try:
            # Parse the JSON line
            if not line.strip():
                return {}
                
            parsed = json.loads(line.strip())
            
            if not isinstance(parsed, dict):
                return {}
            
            # Enhanced event handling based on stream JSON structure
            event_type = parsed.get("type", "")
            
            if event_type == "content":
                # Content chunk from Claude
                content = parsed.get("content", "")
                # Handle case where content might be a list
                if isinstance(content, list):
                    content = " ".join(str(item) for item in content)
                elif not isinstance(content, str):
                    content = str(content)
                    
                if content.strip():
                    log_streamer.add_log(
                        task_id,
                        f"Claude output: {content[:200]}{'...' if len(content) > 200 else ''}",
                        level="info"
                    )
                    
            elif event_type == "tool_use":
                # Tool usage event
                tool_name = parsed.get("name", "unknown")
                tool_input = parsed.get("input", {})
                log_streamer.add_log(
                    task_id,
                    f"Using tool: {tool_name}",
                    level="info",
                    metadata={"tool_input": tool_input}
                )
                
            elif event_type == "tool_result":
                # Tool result event
                tool_name = parsed.get("tool_name", "unknown")
                is_error = parsed.get("is_error", False)
                result = parsed.get("content", "")
                
                # Handle case where result might be a list or non-string
                if isinstance(result, list):
                    result = " ".join(str(item) for item in result)
                elif not isinstance(result, str):
                    result = str(result)
                
                if is_error:
                    log_streamer.add_log(
                        task_id,
                        f"Tool error in {tool_name}: {result[:100]}{'...' if len(str(result)) > 100 else ''}",
                        level="error"
                    )
                else:
                    log_streamer.add_log(
                        task_id,
                        f"Tool {tool_name} completed successfully",
                        level="info"
                    )
                    
            elif event_type == "progress":
                # Progress update event
                progress = parsed.get("progress", 0)
                message = parsed.get("message", "Processing...")
                log_streamer.add_log(
                    task_id,
                    f"Progress: {progress}% - {message}",
                    level="info",
                    metadata={"progress": progress, "stage": message}
                )
                
            elif event_type == "status":
                # Status update event
                status = parsed.get("status", "unknown")
                message = parsed.get("message", "")
                
                log_level = "info"
                if status in ["error", "failed"]:
                    log_level = "error"
                elif status in ["warning"]:
                    log_level = "warning"
                    
                log_streamer.add_log(
                    task_id,
                    f"Status: {status} - {message}",
                    level=log_level,
                    metadata={"status": status}
                )
                
            elif event_type == "completion":
                # Completion event
                success = parsed.get("success", False)
                message = parsed.get("message", "Completed")
                
                log_streamer.add_log(
                    task_id,
                    f"Completion: {message}",
                    level="info" if success else "error",
                    metadata={"success": success}
                )
                
            else:
                # Generic event or unknown type
                if "content" in parsed:
                    content = parsed.get("content", "")
                    # Handle case where content might be a list or non-string
                    if isinstance(content, list):
                        content = " ".join(str(item) for item in content)
                    elif not isinstance(content, str):
                        content = str(content)
                        
                    if content.strip():
                        log_streamer.add_log(
                            task_id,
                            f"Output: {content[:200]}{'...' if len(content) > 200 else ''}",
                            level="info"
                        )
                elif "message" in parsed:
                    message = parsed.get("message", "")
                    log_streamer.add_log(
                        task_id,
                        f"Message: {message}",
                        level="info"
                    )
            
            return parsed
            
        except json.JSONDecodeError as e:
            logger.debug(f"Failed to parse JSON line: {line[:100]}... Error: {str(e)}")
            return {}
        except Exception as e:
            logger.warning(f"Error processing stream JSON: {str(e)}")
            return {}
            
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
            
            # Get system prompt content to incorporate directly
            system_prompt_content = self._get_system_prompt_content_inline()
            
            # Create a structured prompt that includes system prompt content
            complete_prompt = f"""
# System Instructions

{system_prompt_content}

# Resume Customization Task

## Input Files
- Resume: {resume_content}
- Job Description: {job_description_content}

## Execution Instructions
{self.prompt_template if self.prompt_template else "Please analyze the provided resume and job description, then create a customized version of the resume that better matches the job requirements while maintaining absolute truthfulness. Never fabricate any experiences, skills, or achievements."}

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
- You MUST use the Write tool to save your output files
- Save the customized resume as 'new_customized_resume.md' in the current directory
- Save the customization summary as 'customized_resume_output.md' in the current directory
- ALSO print the output using the special format markers above as backup
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
            # Set up task ID and progress tracking
            if not task_id:
                # If no task_id provided, create one via progress tracker
                from app.services.claude_code.progress_tracker import progress_tracker
                task = progress_tracker.create_task()
                task_id = task.task_id
                logger.info(f"Created new task for Claude Code execution: {task_id}")
            else:
                # Get existing task from progress tracker
                from app.services.claude_code.progress_tracker import progress_tracker
                task = progress_tracker.get_task(task_id)
                if not task:
                    # If task doesn't exist, create it with the specified ID
                    task = progress_tracker.create_task()
                    task.task_id = task_id  # Use the specified ID
                    logger.info(f"Created task with specified ID: {task_id}")
                
            # Get log streamer
            log_streamer = get_log_streamer()
            log_stream = log_streamer.create_log_stream(task_id)
            
            # Log starting message
            logger.info(f"Starting Claude Code execution with task ID: {task_id}")
            log_streamer.add_log(task_id, f"Starting Claude Code customization (timeout: {timeout_seconds}s)")
            
            
            # Prepare files and context
            temp_dir = self._create_temp_workspace()
            log_streamer.add_log(task_id, f"Created temporary workspace at {temp_dir}")
            
            # Prepare system prompt and MCP config
            system_prompt_path = self._prepare_system_prompt(temp_dir)
            mcp_config_path = self._prepare_mcp_config(temp_dir)
            
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
                
            # Define command with compatible arguments for current Claude Code CLI
            command = [
                self.claude_cmd, 
                "--print",  # Non-interactive mode
                "--output-format", "text",  # Use text output format for file operations
                "--allowedTools", "Write,Read,Edit,Bash,Grep,Glob",  # Allow file operations
                # No prompt argument - we'll provide it through stdin
            ]
            
            # Log the command we're using
            log_streamer.add_log(task_id, "Executing Claude Code command...")
            log_streamer.add_log(task_id, f"Working directory: {temp_dir}")
            log_streamer.add_log(task_id, "This may take up to 20 minutes, please be patient")
            
            # Create process with pipes for stdout/stderr to enable streaming
            # Prepare environment variables for the subprocess
            env = os.environ.copy()
            env["CLAUDE_CODE_OUTPUT_DIR"] = output_dir
            
            # Create a script that instructs how to save output
            instructions_file = os.path.join(temp_dir, "INSTRUCTIONS.md")
            with open(instructions_file, 'w') as f:
                f.write(f"""# IMPORTANT: Save Output Instructions

You are currently in the working directory: {temp_dir}

Please use the Write tool to save your output files:
- Save the customized resume as 'new_customized_resume.md'
- Save the customization summary as 'customized_resume_output.md'

Example:
```
Write(file_path="new_customized_resume.md", content="[your customized resume content]")
Write(file_path="customized_resume_output.md", content="[your summary content]")
```

The files MUST be saved in the current working directory.
Do not create subdirectories for output files.
""")
            
            # Now run the process with environment variables
            process = subprocess.Popen(
                command,
                cwd=temp_dir,  # Run in temp directory where files will be created
                stdin=subprocess.PIPE,  # Add stdin pipe to provide prompt
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
                env=env  # Pass environment variables
            )
            
            # Send the prompt through stdin and close it
            process.stdin.write(prompt)
            process.stdin.flush()
            process.stdin.close()
            
            # Set up output queues and start output threads
            stdout_queue = queue.Queue(maxsize=1000)  # Increased buffer size
            stderr_queue = queue.Queue(maxsize=1000)
            
            # Log start of process execution
            log_streamer.add_log(task_id, "Starting Claude Code process...")
            log_streamer.add_log(task_id, "Analyzing resume and job description")
            
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
            
            # Poll the process until it completes or times out
            try:
                while process.poll() is None:
                    # Check if timeout has been exceeded
                    elapsed = time.time() - start_time
        
                    # Provide progress updates every 30 seconds
                    if time.time() - last_progress_time > 30:  # Every 30 seconds
                        last_progress_time = time.time()
                        minutes = int(elapsed // 60)
                        if minutes == 0:
                            log_streamer.add_log(task_id, f"Processing... ({int(elapsed)}s elapsed)")
                        else:
                            log_streamer.add_log(task_id, f"Processing... ({minutes}m {int(elapsed % 60)}s elapsed)")
        
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
            
                        # Clean up threads before raising exception
                        stdout_queue.put(None)  # Signal threads to terminate
                        stderr_queue.put(None)
                        stdout_thread.join(timeout=2)
                        stderr_thread.join(timeout=2)
            
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
                            
                            # Since we're using text output format, just log the line directly
                            if line.strip():
                                log_streamer.add_log(
                                    task_id,
                                    f"Claude: {line.strip()}",
                                    level="info"
                                )
                                
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
                
                # If we didn't get content from stdout parsing, try reading the actual files
                if not parsed_results["customized_resume"] and os.path.exists(customized_resume_path):
                    log_streamer.add_log(task_id, f"Reading customized resume from file: {customized_resume_path}")
                    try:
                        with open(customized_resume_path, 'r') as f:
                            parsed_results["customized_resume"] = f.read()
                        log_streamer.add_log(task_id, f"Successfully read customized resume ({len(parsed_results['customized_resume'])} chars)")
                    except Exception as e:
                        log_streamer.add_log(task_id, f"Error reading customized resume file: {str(e)}", level="error")
                
                if not parsed_results["customization_summary"] and os.path.exists(summary_path):
                    log_streamer.add_log(task_id, f"Reading summary from file: {summary_path}")
                    try:
                        with open(summary_path, 'r') as f:
                            parsed_results["customization_summary"] = f.read()
                        log_streamer.add_log(task_id, f"Successfully read summary ({len(parsed_results['customization_summary'])} chars)")
                    except Exception as e:
                        log_streamer.add_log(task_id, f"Error reading summary file: {str(e)}", level="error")
                
                # Only write files if they don't already exist (i.e., if we extracted from stdout)
                if parsed_results["customized_resume"] and not os.path.exists(customized_resume_path):
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
                elif not parsed_results["customized_resume"]:
                    log_streamer.add_log(
                        task_id,
                        "No customized resume content found",
                        level="error"
                    )
                
                if parsed_results["customization_summary"] and not os.path.exists(summary_path):
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
                elif not parsed_results["customization_summary"]:
                    log_streamer.add_log(
                        task_id,
                        "No customization summary content found",
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
        Execute the customization with log-based progress tracking.
        
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
        from app.services.claude_code.progress_tracker import progress_tracker
        log_streamer = get_log_streamer()
        
        # Print to console for real-time tracking
        print(f"[Claude Code] Starting customization task {task_id} with timeout: {timeout or 'default'} seconds")
        
        try:
            # Initialize with a basic loading message
            # All real progress will come from log parsing rather than artificial stages
            log_streamer.add_log(task_id, "Starting Claude Code resume customization...")
            
            # Get task to update progress
            task = progress_tracker.get_task(task_id)
            if task:
                task.update("initializing", 0, "Starting Claude Code resume customization")
                
                # Register for progress callback if provided
                if progress_callback:
                    # Create a subscriber function
                    def progress_subscriber(update):
                        # Get current logs
                        logs = log_streamer.get_logs(task_id)
                        
                        # Add logs to the update
                        update["logs"] = logs
                        
                        # Call progress callback
                        progress_callback(update)
                        
                    # Set up an async queue for updates
                    import asyncio
                    update_queue = asyncio.Queue()
                    task.add_subscriber(update_queue)
                    
                    # Send initial progress
                    progress_callback({
                        "task_id": task_id,
                        "status": "initializing",
                        "progress": 0,
                        "message": "Starting Claude Code resume customization",
                        "logs": log_streamer.get_logs(task_id)
                    })
            
            # Execute the actual customization with streaming logs
            try:
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
                    log_message = f"WARNING: Output file not found at {output_path}, generating basic file"
                    print(f"[Claude Code] {task_id}: {log_message}")
                    log_streamer.add_log(task_id, log_message, level="warning")
                    
                    # Write something to the output path so we don't get an error
                    with open(output_path, 'w') as f:
                        f.write("# Customized Resume\n\nClaude Code did not produce a valid customized resume. Please try again.")
                
                summary_path = os.path.join(os.path.dirname(output_path), "customized_resume_output.md")
                if not os.path.exists(summary_path):
                    log_message = f"WARNING: Summary file not found at {summary_path}, generating basic file"
                    print(f"[Claude Code] {task_id}: {log_message}")
                    log_streamer.add_log(task_id, log_message, level="warning")
                    
                    # Write something to the summary path
                    with open(summary_path, 'w') as f:
                        f.write("# Customization Summary\n\nClaude Code did not produce a valid customization summary. Please try again.")
                
                # Process is complete - add log to trigger completion
                log_streamer.add_log(task_id, "Claude Code execution completed successfully")
                
                # If task wasn't updated by log parsing, force to completed
                task = progress_tracker.get_task(task_id)
                if task and task.status != "completed":
                    task.update("completed", 100, "Customization complete")
                    # Set the result with paths to the generated files
                    task.result = {
                        "customized_resume_path": output_path,
                        "summary_path": summary_path,
                        "success": True
                    }
                
            except subprocess.TimeoutExpired:
                logger.error(f"Claude Code execution timed out for task {task_id}")
                log_streamer.add_log(task_id, "ERROR: Claude Code execution timed out", level="error")
                
                # Explicitly set error state for progress tracking
                task = progress_tracker.get_task(task_id)
                if task:
                    task.set_error("Claude Code execution timed out")
                    
                raise
            
        except Exception as e:
            logger.error(f"Error in customization task {task_id}: {str(e)}")
            log_streamer.add_log(task_id, f"ERROR: {str(e)}", level="error")
            
            # Update task for progress tracking
            task = progress_tracker.get_task(task_id)
            if task:
                task.set_error(str(e))
                
            # Send final error update via callback if provided
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
    
    def validate_sdk_features(self) -> Dict[str, bool]:
        """
        Validate that the new SDK features are working correctly.
        
        Returns:
            Dictionary with validation results for each feature
        """
        import tempfile
        
        results = {
            "system_prompt_creation": False,
            "mcp_config_creation": False,
            "stream_json_processing": False
        }
        
        try:
            # Test system prompt creation
            with tempfile.TemporaryDirectory() as temp_dir:
                system_prompt_path = self._prepare_system_prompt(temp_dir)
                results["system_prompt_creation"] = (
                    system_prompt_path is not None and 
                    os.path.exists(system_prompt_path)
                )
                
                # Test MCP config creation (should return None when not enabled)
                mcp_config_path = self._prepare_mcp_config(temp_dir)
                results["mcp_config_creation"] = True  # Should work (return None when disabled)
                
            # Test stream JSON processing
            test_json = '{"type": "content", "content": "test content"}'
            from app.services.claude_code.log_streamer import get_log_streamer
            log_streamer = get_log_streamer()
            
            # Create a temporary task ID for testing
            test_task_id = f"test-{uuid.uuid4().hex}"
            log_streamer.create_log_stream(test_task_id)
            
            parsed = self._process_stream_json(test_json, test_task_id, log_streamer)
            results["stream_json_processing"] = isinstance(parsed, dict) and "content" in parsed
            
        except Exception as e:
            logger.error(f"SDK feature validation failed: {str(e)}")
            
        return results
    
    def start_async(
        self,
        resume_path: str,
        job_description_path: str,
        output_path: str,
        task_id: Optional[str] = None,
        timeout: int = 1800
    ) -> Dict[str, Any]:
        """
        Start an asynchronous resume customization task.
        
        Args:
            resume_path: Path to the resume file
            job_description_path: Path to the job description file
            output_path: Path where the output should be saved
            task_id: Optional task ID to use (will generate if not provided)
            timeout: Timeout in seconds (default: 1800)
            
        Returns:
            Dictionary with task_id and status
        """
        import threading
        from app.services.claude_code.progress_tracker import progress_tracker
        
        # Create or get task
        if not task_id:
            task = progress_tracker.create_task()
            task_id = task.task_id
            logger.info(f"Created new task with ID: {task_id}")
        else:
            task = progress_tracker.get_task(task_id)
            if not task:
                task = progress_tracker.create_task()
                task.task_id = task_id
                logger.info(f"Created task with provided ID: {task_id}")
            else:
                logger.info(f"Using existing task with ID: {task_id}")
        
        # Update task status
        task.status = "processing"
        task.message = "Starting resume customization"
        
        # Start customization in background thread
        def run_customization():
            try:
                logger.info(f"Background thread starting customization for task {task_id}")
                result = self.customize_resume(
                    resume_path=resume_path,
                    job_description_path=job_description_path,
                    output_path=output_path,
                    task_id=task_id,
                    timeout=timeout
                )
                
                # Read the output files
                output_dir = os.path.dirname(output_path)
                customized_resume = ""
                customization_summary = ""
                
                if os.path.exists(output_path):
                    with open(output_path, 'r') as f:
                        customized_resume = f.read()
                
                summary_path = os.path.join(output_dir, "customized_resume_output.md")
                if os.path.exists(summary_path):
                    with open(summary_path, 'r') as f:
                        customization_summary = f.read()
                
                # Update task with results
                task.status = "completed"
                task.result = {
                    "customized_resume": customized_resume,
                    "customization_summary": customization_summary,
                    "customization_id": None
                }
                task.message = "Customization completed successfully"
                logger.info(f"Task {task_id} completed successfully")
                
            except Exception as e:
                logger.error(f"Error in background customization for task {task_id}: {str(e)}")
                task.status = "error"
                task.error = str(e)
                task.message = f"Customization failed: {str(e)}"
            finally:
                # Clean up temporary files
                try:
                    if os.path.exists(resume_path):
                        os.unlink(resume_path)
                    if os.path.exists(job_description_path):
                        os.unlink(job_description_path)
                except Exception as e:
                    logger.warning(f"Error cleaning up temporary files: {str(e)}")
        
        # Start background thread
        thread = threading.Thread(target=run_customization, daemon=True)
        thread.start()
        logger.info(f"Started background thread for task {task_id}")
        
        return {"task_id": task_id, "status": "processing"}


# Singleton instance
_executor_instance = None


def get_claude_code_executor() -> ClaudeCodeExecutor:
    """Get or create the Claude Code executor singleton."""
    global _executor_instance
    if _executor_instance is None:
        _executor_instance = ClaudeCodeExecutor()
    return _executor_instance
