"""Prompt and template management utilities for Claude Code."""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def load_prompt_template(path: str) -> str:
    """Load a prompt template from disk.

    Args:
        path: Path to the template file.

    Returns:
        The template content.
    """
    try:
        with open(path, "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError as exc:
        logger.error("Prompt template file not found: %s", path)
        raise exc


def get_system_prompt_content_inline() -> str:
    """Return system prompt content for inline use."""
    try:
        from app.core.config import settings

        system_prompt_content = getattr(settings, "CLAUDE_SYSTEM_PROMPT", None)
        if not system_prompt_content:
            system_prompt_content = (
                "You are an expert resume customization assistant. Your task is to "
                "analyze job descriptions and customize resumes to match job "
                "requirements while maintaining ABSOLUTE truthfulness and accuracy."
            )
        return system_prompt_content
    except Exception as exc:  # pragma: no cover - settings import failure
        logger.warning("Failed to get system prompt content: %s", exc)
        return "You are an expert resume customization assistant."


def prepare_system_prompt(temp_dir: str) -> Optional[str]:
    """Create a system prompt file in ``temp_dir`` if configured."""
    try:
        from app.core.config import settings

        system_prompt_content = getattr(settings, "CLAUDE_SYSTEM_PROMPT", None)
        if not system_prompt_content:
            system_prompt_content = get_system_prompt_content_inline()

        os.makedirs(temp_dir, exist_ok=True)
        path = os.path.join(temp_dir, "system_prompt.txt")
        with open(path, "w", encoding="utf-8") as file:
            file.write(system_prompt_content)
        logger.info("Created system prompt file at %s", path)
        return path
    except Exception as exc:  # pragma: no cover - filesystem errors
        logger.warning("Failed to create system prompt file: %s", exc)
        return None


def prepare_mcp_config(temp_dir: str) -> Optional[str]:
    """Generate an MCP configuration file when enabled."""
    try:
        from app.core.config import settings

        if not getattr(settings, "CLAUDE_MCP_ENABLED", False):
            return None

        mcp_servers = getattr(settings, "CLAUDE_MCP_SERVERS", {})
        if not mcp_servers:
            mcp_servers = {
                "filesystem": {
                    "command": "uvx",
                    "args": ["mcp-server-filesystem", temp_dir],
                    "env": {},
                }
            }

        config = {"mcpServers": mcp_servers}
        os.makedirs(temp_dir, exist_ok=True)
        path = os.path.join(temp_dir, "claude_desktop_config.json")
        with open(path, "w", encoding="utf-8") as file:
            json.dump(config, file, indent=2)
        logger.info("Created MCP config file at %s", path)
        return path
    except Exception as exc:  # pragma: no cover - filesystem errors
        logger.warning("Failed to create MCP config file: %s", exc)
        return None
def build_prompt(resume_path: str, job_description_path: str, template: Optional[str]) -> str:
    """Construct the full prompt for Claude Code execution."""
    try:
        with open(resume_path, "r", encoding="utf-8") as r_file:
            resume_content = r_file.read()
        with open(job_description_path, "r", encoding="utf-8") as j_file:
            job_description_content = j_file.read()
        with open(job_description_path, "r", encoding="utf-8") as j_file:
            job_description_content = j_file.read()

        system_prompt = get_system_prompt_content_inline()
        instructions = template or (
            "Please analyze the provided resume and job description, then create "
            "a customized version of the resume that better matches the job "
            "requirements while maintaining absolute truthfulness. Never "
            "fabricate any experiences, skills, or achievements."
        )

        return (
            f"# System Instructions\n\n{system_prompt}\n\n"
            "# Resume Customization Task\n\n"
            "## Input Files\n"
            f"- Resume: {resume_content}\n"
            f"- Job Description: {job_description_content}\n\n"
            "## Execution Instructions\n"
            f"{instructions}\n\n"
            "## Expected Outputs\n"
            "You will need to output two primary files and several optional "
            "intermediate files.\n\n"
            "Instead of directly creating files (since you may not have permission), "
            "please PRINT the contents to stdout as follows:\n\n"
            "1. First, perform your complete analysis of the resume and job description\n"
            "2. Then output the customized resume with this exact format:\n"
            "   ```\n   === BEGIN CUSTOMIZED RESUME ===\n   [Your complete customized resume content in markdown format]\n   === END CUSTOMIZED RESUME ===\n   ```\n\n"
            "3. Then output the detailed change summary with this exact format:\n"
            "   ```\n   === BEGIN CUSTOMIZATION SUMMARY ===\n   [Your complete customization summary in markdown format]\n   === END CUSTOMIZATION SUMMARY ===\n   ```\n\n"
            "4. If you generate any intermediate files, output them with this format:\n"
            "   ```\n   === BEGIN INTERMEDIATE FILE: [filename] ===\n   [Content of the intermediate file]\n   === END INTERMEDIATE FILE: [filename] ===\n   ```\n\n"
            "## IMPORTANT INSTRUCTIONS\n"
            "- You MUST use the Write tool to save your output files\n"
            "- Save the customized resume as 'new_customized_resume.md' in the current directory\n"
            "- Save the customization summary as 'customized_resume_output.md' in the current directory\n"
            "- ALSO print the output using the special format markers above as backup\n"
            "- Ensure your customized resume is complete and properly formatted in markdown\n"
            "- Include detailed change summary with match scores and specific changes made\n"
            "- Use the exact BEGIN/END markers shown above to delimit each output"
        )
    except Exception as exc:
        logger.error("Error building prompt: %s", exc)
        raise

