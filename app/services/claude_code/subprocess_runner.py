"""Run Claude Code as a subprocess with timeout handling."""

from __future__ import annotations

import os
import queue
import subprocess
import time
from typing import List


def run_claude_subprocess(
    command: List[str],
    temp_dir: str,
    prompt: str,
    log_streamer,
    task_id: str,
    timeout_seconds: int,
) -> str:
    """Execute the Claude Code command and return its stdout."""
    claude_work_dir = os.path.join(temp_dir, ".claude_work")
    os.makedirs(claude_work_dir, exist_ok=True)
    input_dir = os.path.join(claude_work_dir, "input")
    output_dir = os.path.join(claude_work_dir, "output")
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    prompt_file_path = os.path.join(input_dir, "prompt.txt")
    with open(prompt_file_path, "w", encoding="utf-8") as file:
        file.write(prompt)

    env = os.environ.copy()
    env["CLAUDE_CODE_OUTPUT_DIR"] = output_dir

    instructions_file = os.path.join(temp_dir, "INSTRUCTIONS.md")
    with open(instructions_file, "w", encoding="utf-8") as file:
        file.write(
            f"# IMPORTANT: Save Output Instructions\n\n"
            f"You are currently in the working directory: {temp_dir}\n\n"
            "Please use the Write tool to save your output files:\n"
            "- Save the customized resume as 'new_customized_resume.md'\n"
            "- Save the customization summary as 'customized_resume_output.md'\n"
            "\nExample:\n"
            "```\nWrite(file_path=\"new_customized_resume.md\", content=\"[your customized resume content]\")\n"
            "Write(file_path=\"customized_resume_output.md\", content=\"[your summary content]\")\n``""\n"
            "\nThe files MUST be saved in the current working directory.\n"
            "Do not create subdirectories for output files."
        )

    process = subprocess.Popen(
        command,
        cwd=temp_dir,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        env=env,
    )

    try:
        process.stdin.write(prompt)
        process.stdin.flush()
        process.stdin.close()
    except (BrokenPipeError, IOError) as e:
        log_streamer.add_log(task_id, f"Error writing to subprocess: {e}", level="error")

    stdout_queue: queue.Queue[str] = queue.Queue(maxsize=1000)
    stderr_queue: queue.Queue[str] = queue.Queue(maxsize=1000)

    stdout_thread = log_streamer.start_output_stream(
        task_id=task_id,
        process_output=process.stdout,
        output_queue=stdout_queue,
        stream_type="stdout",
    )
    stderr_thread = log_streamer.start_output_stream(
        task_id=task_id,
        process_output=process.stderr,
        output_queue=stderr_queue,
        stream_type="stderr",
    )

    start_time = time.time()
    last_progress_time = start_time
    last_activity_time = start_time
    all_stdout: List[str] = []

    try:
        while process.poll() is None:
            elapsed = time.time() - start_time
            if elapsed > timeout_seconds:
                log_streamer.add_log(
                    task_id,
                    f"Process exceeded timeout limit of {timeout_seconds}s, terminating",
                    level="error",
                )
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    log_streamer.add_log(task_id, "Process did not terminate, force killing", level="error")
                stdout_queue.put(None)
                stderr_queue.put(None)
                stdout_thread.join(timeout=2)
                stderr_thread.join(timeout=2)
                raise subprocess.TimeoutExpired(command, timeout_seconds)

            if time.time() - last_progress_time > 30:
                last_progress_time = time.time()
                minutes = int(elapsed // 60)
                if minutes == 0:
                    log_streamer.add_log(task_id, f"Processing... ({int(elapsed)}s elapsed)")
                else:
                    log_streamer.add_log(task_id, f"Processing... ({minutes}m {int(elapsed % 60)}s elapsed)")

            stdout_activity = False
            try:
                while True:
                    line = stdout_queue.get_nowait()
                    if line is None:
                        break
                    stdout_activity = True
                    last_activity_time = time.time()
                    all_stdout.append(line)
                    if line.strip():
                        # Try to parse as stream-json, fallback to plain logging
                        try:
                            from app.services.claude_code import output_parser
                            parsed = output_parser.process_stream_json(line.strip(), task_id, log_streamer)
                        except Exception:
                            log_streamer.add_log(task_id, f"Claude: {line.strip()}", level="info")
            except queue.Empty:
                pass

            stderr_activity = False
            try:
                while True:
                    line = stderr_queue.get_nowait()
                    if line is None:
                        break
                    stderr_activity = True
                    last_activity_time = time.time()
                    if "error" in line.lower() or "exception" in line.lower():
                        log_streamer.add_log(task_id, line, level="error")
                    else:
                        log_streamer.add_log(task_id, line, level="warning")
            except queue.Empty:
                pass

            if stdout_activity or stderr_activity:
                last_progress_time = time.time()

            if time.time() - last_activity_time > 60 and elapsed > 120:
                log_streamer.add_log(
                    task_id,
                    "No output from process for 60 seconds, may be hanging",
                    level="warning",
                )
                last_activity_time = time.time()

            time.sleep(0.1)

        try:
            while True:
                line = stdout_queue.get_nowait()
                if line is None:
                    break
                all_stdout.append(line)
        except queue.Empty:
            pass

        stdout_thread.join(timeout=5)
        stderr_thread.join(timeout=5)

        if process.returncode != 0:
            error_output = "\n".join(all_stdout[-20:]) if all_stdout else "No output captured"
            raise subprocess.CalledProcessError(process.returncode, command, output=error_output)

        return "\n".join(all_stdout)
    finally:
        stdout_thread.join(timeout=1)
        stderr_thread.join(timeout=1)

