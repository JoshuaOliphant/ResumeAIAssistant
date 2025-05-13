"""
Claude Code integration for ResumeAI Assistant.

This package provides services for integrating Claude Code as a subprocess
for resume customization tasks, replacing the complex multi-LLM workflow
with a simpler, more robust approach.
"""

from app.services.claude_code.executor import ClaudeCodeExecutor, ClaudeCodeExecutionError

__all__ = ['ClaudeCodeExecutor', 'ClaudeCodeExecutionError']