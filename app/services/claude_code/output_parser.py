"""Output parsing and file management utilities."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict

logger = logging.getLogger(__name__)


def process_stream_json(line: str, task_id: str, log_streamer) -> Dict[str, Any]:
    """Parse a line from Claude Code stream-json output."""
    try:
        if not line.strip():
            return {}
        parsed = json.loads(line.strip())
        if not isinstance(parsed, dict):
            return {}

        event_type = parsed.get("type", "")
        if event_type == "content":
            content = parsed.get("content", "")
            if isinstance(content, list):
                content = " ".join(str(item) for item in content)
            elif not isinstance(content, str):
                content = str(content)
            if content.strip():
                log_streamer.add_log(
                    task_id,
                    f"Claude output: {content[:200]}{'...' if len(content) > 200 else ''}",
                    level="info",
                )
        elif event_type == "tool_use":
            tool_name = parsed.get("name", "unknown")
            tool_input = parsed.get("input", {})
            log_streamer.add_log(task_id, f"Using tool: {tool_name}", level="info", metadata={"tool_input": tool_input})
        elif event_type == "tool_result":
            tool_name = parsed.get("tool_name", "unknown")
            is_error = parsed.get("is_error", False)
            content = parsed.get("content", "")
            if is_error:
                log_streamer.add_log(task_id, f"Tool error in {tool_name}: {content}", level="error")
            else:
                log_streamer.add_log(task_id, f"Tool {tool_name} completed successfully", level="info")
        elif event_type == "progress":
            progress = parsed.get("progress", 0)
            message = parsed.get("message", "")
            log_streamer.add_log(task_id, f"Progress: {progress}% - {message}", level="info")
        elif event_type == "status":
            status = parsed.get("status", "")
            message = parsed.get("message", "")
            log_streamer.add_log(task_id, f"Status: {status} - {message}", level="info")
        elif event_type == "completion":
            message = parsed.get("message", "")
            log_streamer.add_log(task_id, f"Completion: {message}", level="info")
        else:
            message = parsed.get("message", "")
            if message:
                log_streamer.add_log(task_id, f"Message: {message}", level="info")
        return parsed
    except json.JSONDecodeError as exc:
        logger.debug("Failed to parse JSON line: %s", line[:100])
        return {}
    except Exception as exc:  # pragma: no cover - unexpected errors
        logger.warning("Error processing stream JSON: %s", exc)
        return {}


def process_output(output: str) -> Dict[str, Any]:
    """Process final output from Claude Code."""
    try:
        result = {
            "raw_output": output,
            "customized_resume": "",
            "customization_summary": "",
            "intermediate_files": {},
        }

        resume_pattern = r"=== BEGIN CUSTOMIZED RESUME ===\s*([\s\S]*?)\s*=== END CUSTOMIZED RESUME ==="
        match = re.search(resume_pattern, output)
        if match:
            result["customized_resume"] = match.group(1).strip()

        summary_pattern = r"=== BEGIN CUSTOMIZATION SUMMARY ===\s*([\s\S]*?)\s*=== END CUSTOMIZATION SUMMARY ==="
        match = re.search(summary_pattern, output)
        if match:
            result["customization_summary"] = match.group(1).strip()

        intermediate_pattern = r"=== BEGIN INTERMEDIATE FILE: ([\w\.-]+) ===\s*([\s\S]*?)\s*=== END INTERMEDIATE FILE: \1 ==="
        for im in re.finditer(intermediate_pattern, output):
            result["intermediate_files"][im.group(1)] = im.group(2).strip()

        if result["customized_resume"] or result["customization_summary"] or result["intermediate_files"]:
            return result

        json_match = re.search(r"({[\s\S]*})", output)
        if json_match:
            try:
                parsed_output = json.loads(json_match.group(1))
                result["customized_resume"] = parsed_output.get("customized_resume", "")
                result["customization_summary"] = parsed_output.get("customization_summary", "")
                result["intermediate_files"] = parsed_output.get("intermediate_files", {})
                return result
            except json.JSONDecodeError:
                logger.warning("Found JSON-like content but failed to parse")

        if not result["customized_resume"]:
            md_sections = re.split(r"\n#{1,2} ", output)
            for section in md_sections:
                if "resume" in section.lower()[:50] and len(section) > 200:
                    result["customized_resume"] = section.strip()
                    break

        if not result["customized_resume"]:
            result["customized_resume"] = (
                "Claude Code did not produce a valid customized resume. Please try again."
            )
        if not result["customization_summary"]:
            result["customization_summary"] = (
                "Claude Code execution failed to produce a valid summary."
            )
        return result
    except Exception as exc:  # pragma: no cover - unexpected errors
        logger.error("Error processing Claude Code output: %s", exc)
        return {
            "raw_output": output,
            "customized_resume": "Error processing Claude Code output.",
            "customization_summary": f"Error: {exc}",
        }


def save_results(results: Dict[str, Any], output_path: str) -> Dict[str, Any]:
    """Save parsed results to ``output_path`` and return file locations."""
    try:
        output_dir = os.path.dirname(output_path)
        os.makedirs(output_dir, exist_ok=True)

        with open(output_path, "w") as file:
            file.write(results.get("customized_resume", ""))

        summary_path = os.path.join(output_dir, "customized_resume_output.md")
        with open(summary_path, "w") as file:
            file.write(results.get("customization_summary", ""))

        for name, content in results.get("intermediate_files", {}).items():
            file_path = os.path.join(output_dir, name)
            with open(file_path, "w") as file:
                if isinstance(content, (dict, list)):
                    json.dump(content, file, indent=2)
                else:
                    file.write(content)

        return {
            "customized_resume_path": output_path,
            "customization_summary_path": summary_path,
        }
    except Exception as exc:
        logger.error("Error saving results: %s", exc)
        raise

