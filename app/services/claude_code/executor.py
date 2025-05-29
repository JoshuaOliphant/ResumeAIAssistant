"""Claude Code Executor Service."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
import threading
import uuid
from typing import Any, Callable, Dict, Optional

from app.services.claude_code import output_parser, prompt_manager, subprocess_runner

logger = logging.getLogger(__name__)


class ClaudeCodeExecutionError(Exception):
    """Exception raised when Claude Code execution fails."""


class ClaudeCodeExecutor:
    """Service for running Claude Code resume customization tasks."""

    def __init__(
        self,
        working_dir: Optional[str] = None,
        prompt_template_path: Optional[str] = None,
        claude_cmd: str = "claude",
    ) -> None:
        self.working_dir = working_dir or tempfile.mkdtemp(prefix="claude_code_")
        self.claude_cmd = claude_cmd
        self.use_advanced_cli_features = False
        self.prompt_template = (
            prompt_manager.load_prompt_template(prompt_template_path)
            if prompt_template_path
            else None
        )

    def _create_temp_workspace(self) -> str:
        temp_dir = os.path.join(
            self.working_dir, f"claude_workspace_{uuid.uuid4().hex}"
        )
        os.makedirs(temp_dir, exist_ok=True)
        return temp_dir

    def customize_resume(
        self,
        resume_path: str,
        job_description_path: str,
        output_path: str,
        task_id: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute resume customization using Claude Code."""
        from app.core.config import settings
        from app.services.claude_code.log_streamer import get_log_streamer
        from app.services.claude_code.progress_tracker import progress_tracker

        timeout_seconds = timeout or settings.CLAUDE_CODE_TIMEOUT or 1800
        task = None
        if not task_id:
            task = progress_tracker.create_task()
            task_id = task.task_id
        else:
            task = progress_tracker.get_task(task_id) or progress_tracker.create_task()
            task.task_id = task_id

        log_streamer = get_log_streamer()
        log_streamer.create_log_stream(task_id)
        log_streamer.add_log(
            task_id, f"Starting Claude Code customization (timeout: {timeout_seconds}s)"
        )

        temp_dir = self._create_temp_workspace()

        prompt = prompt_manager.build_prompt(
            resume_path, job_description_path, self.prompt_template
        )

        command = [
            self.claude_cmd,
            "--model", "sonnet",  # Use Sonnet model for better performance and cost efficiency
            "--print",
            "--output-format",
            "stream-json",
            "--allowedTools",
            "Write,Read,Edit,Bash,Grep,Glob",
        ]

        # Note: System prompt is now included in the main prompt via build_prompt()
        # The --system-prompt-file flag is not supported by the claude CLI
        
        # Add MCP config file if created
        mcp_config_path = prompt_manager.prepare_mcp_config(temp_dir)
        if mcp_config_path:
            command.extend(["--mcp-config", mcp_config_path])

        try:
            stdout_content = subprocess_runner.run_claude_subprocess(
                command=command,
                temp_dir=temp_dir,
                prompt=prompt,
                log_streamer=log_streamer,
                task_id=task_id,
                timeout_seconds=timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            log_streamer.add_log(
                task_id, "ERROR: Claude Code execution timed out", level="error"
            )
            raise ClaudeCodeExecutionError("Claude Code execution timed out")
        except subprocess.CalledProcessError as exc:
            log_streamer.add_log(
                task_id, f"Process failed with code {exc.returncode}", level="error"
            )
            raise ClaudeCodeExecutionError("Claude Code process failed")

        files_found = os.listdir(temp_dir)
        customized_resume_path = os.path.join(temp_dir, "new_customized_resume.md")
        summary_path = os.path.join(temp_dir, "customized_resume_output.md")

        if not os.path.exists(customized_resume_path):
            alt = [
                f for f in files_found if f.endswith(".md") and "resume" in f.lower()
            ]
            if alt:
                customized_resume_path = os.path.join(temp_dir, alt[0])
        if not os.path.exists(summary_path):
            alt = [
                f for f in files_found if f.endswith(".md") and "summary" in f.lower()
            ]
            if alt:
                summary_path = os.path.join(temp_dir, alt[0])

        parsed_results = output_parser.process_output(stdout_content)

        if not parsed_results["customized_resume"] and os.path.exists(
            customized_resume_path
        ):
            with open(customized_resume_path, "r", encoding="utf-8") as file:
                parsed_results["customized_resume"] = file.read()
        if not parsed_results["customization_summary"] and os.path.exists(summary_path):
            with open(summary_path, "r", encoding="utf-8") as file:
                parsed_results["customization_summary"] = file.read()

        result = output_parser.save_results(parsed_results, output_path)
        log_streamer.add_log(task_id, "Claude Code execution completed successfully")
        
        # Read the original resume content
        original_resume_content = ""
        try:
            with open(resume_path, "r", encoding="utf-8") as file:
                original_resume_content = file.read()
        except Exception as e:
            logger.warning(f"Could not read original resume: {e}")

        if task:
            task.update("completed", 100, "Customization complete")
            # Store the actual content in the task result, not just file paths
            task.result = {
                "customized_resume": parsed_results.get("customized_resume", ""),
                "customization_summary": parsed_results.get("customization_summary", ""),
                "original_resume": original_resume_content,
                "customized_resume_path": result.get("customized_resume_path"),
                "customization_summary_path": result.get("customization_summary_path")
            }

        shutil.rmtree(temp_dir, ignore_errors=True)
        return result

    def customize_resume_with_progress(
        self,
        resume_path: str,
        job_description_path: str,
        output_path: str,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, str]:
        from app.services.claude_code.progress_tracker import progress_tracker

        task_id = str(uuid.uuid4())
        progress_tracker.create_task().task_id = task_id
        thread = threading.Thread(
            target=self._run_customization_with_progress,
            args=(
                resume_path,
                job_description_path,
                output_path,
                progress_callback,
                task_id,
                timeout,
            ),
            daemon=True,
        )
        thread.start()
        return {"task_id": task_id}

    def _run_customization_with_progress(
        self,
        resume_path: str,
        job_description_path: str,
        output_path: str,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]],
        task_id: str,
        timeout: Optional[int],
    ) -> None:
        from app.services.claude_code.log_streamer import get_log_streamer
        from app.services.claude_code.progress_tracker import progress_tracker

        log_streamer = get_log_streamer()
        progress_tracker.get_task(task_id).update("processing", 0, "Starting")

        def callback(update: Dict[str, Any]) -> None:
            if progress_callback:
                logs = log_streamer.get_logs(task_id)
                update["logs"] = logs
                progress_callback(update)

        try:
            self.customize_resume(
                resume_path=resume_path,
                job_description_path=job_description_path,
                output_path=output_path,
                task_id=task_id,
                timeout=timeout,
            )
            progress_tracker.get_task(task_id).update("completed", 100, "Completed")
            if progress_callback:
                callback({"task_id": task_id, "status": "completed", "progress": 100})
        except Exception as exc:
            progress_tracker.get_task(task_id).set_error(str(exc))
            if progress_callback:
                callback({"task_id": task_id, "status": "error", "progress": 0})

    def validate_sdk_features(self) -> Dict[str, bool]:
        """Validate helper methods extracted into submodules."""
        import tempfile

        results = {
            "system_prompt_creation": False,
            "mcp_config_creation": False,
            "stream_json_processing": False,
        }
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                path = prompt_manager.prepare_system_prompt(temp_dir)
                results["system_prompt_creation"] = path is not None and os.path.exists(
                    path
                )
            with tempfile.TemporaryDirectory() as temp_dir:
                path = prompt_manager.prepare_mcp_config(temp_dir)
                results["mcp_config_creation"] = path is not None and os.path.exists(
                    path
                )
            from app.services.claude_code.log_streamer import get_log_streamer

            log_streamer = get_log_streamer()
            log_streamer.create_log_stream("test")
            test_json = '{"type": "content", "content": "test"}'
            parsed = output_parser.process_stream_json(test_json, "test", log_streamer)
            results["stream_json_processing"] = (
                isinstance(parsed, dict) and "content" in parsed
            )
        except Exception as exc:  # pragma: no cover - unexpected errors
            logger.error("SDK feature validation failed: %s", exc)
        return results


_executor_instance: Optional[ClaudeCodeExecutor] = None


def get_claude_code_executor() -> ClaudeCodeExecutor:
    """Get or create the Claude Code executor singleton."""
    global _executor_instance
    if _executor_instance is None:
        _executor_instance = ClaudeCodeExecutor()
    return _executor_instance
