# Claude SDK Integration Plan

This document outlines the step-by-step plan for integrating the Claude Code SDK enhancements into the ResumeAI Assistant application.

## Current Architecture

Our current implementation:
- Uses Claude Code as a subprocess with custom output parsing
- Has limited streaming capability through custom log parsing
- Handles progress tracking through our own implementation
- Doesn't leverage Model Context Protocol (MCP) features

## Phase 1: Command-Line SDK Enhancements

### 1. Update Command Construction (1-2 days)

**File:** `app/services/claude_code/executor.py`

```python
# Current command:
command = [
    self.claude_cmd,
    "--print",  # Non-interactive mode
    "--output-format", "stream-json",  # Using streaming JSON already
    "--verbose",  # Enable verbose output
    f"@{prompt_file_path}"
]

# Enhanced command:
command = [
    self.claude_cmd,
    "--print",  # Non-interactive mode
    "--output-format", "stream-json",  # Keep streaming JSON
    "--append-system-prompt", system_prompt_file_path,  # Append to system prompt
    "--mcp-config", mcp_config_path,  # Add MCP configuration if enabled
    "--allowedTools", "brave-search.brave_web_search",  # Explicitly allow specific tools
    f"@{prompt_file_path}"
]
```

### 2. Implement System Prompt Separation (1 day)

**File:** `app/services/claude_code/executor.py`

Add method to prepare system prompt files:

```python
def _prepare_system_prompt(self, temp_dir: str) -> str:
    """
    Create a file with additional system prompt instructions.

    Args:
        temp_dir: Temporary directory to create the file in

    Returns:
        Path to the system prompt file
    """
    system_prompt_path = os.path.join(temp_dir, "system_prompt.txt")

    # Get system prompt content from config or use default
    from app.core.config import settings
    system_prompt_content = settings.CLAUDE_SYSTEM_PROMPT or """
    # Resume Customization Instructions

    ## Guidelines
    - Follow strict verification protocols
    - Never fabricate experiences or credentials
    - Only reorganize and emphasize existing content
    - Focus on ATS optimization

    ## Expected Outputs
    - Maintain truthfulness while optimizing for the job
    - Track all changes with evidence from the original resume
    - Provide clear before/after comparisons
    """

    with open(system_prompt_path, 'w') as f:
        f.write(system_prompt_content)

    return system_prompt_path
```

### 3. Add MCP Configuration Support (2 days)

**File:** `app/core/config.py`

Add new configuration settings:

```python
# Claude Code SDK configuration
CLAUDE_USE_MCP: bool = os.getenv("CLAUDE_USE_MCP", "false").lower() == "true"
BRAVE_SEARCH_API_KEY: Optional[str] = os.getenv("BRAVE_SEARCH_API_KEY")
```

**File:** `app/services/claude_code/executor.py`

Add method to prepare MCP configuration:

```python
def _prepare_mcp_config(self, temp_dir: str) -> Optional[str]:
    """
    Create MCP configuration file if enabled.

    Args:
        temp_dir: Temporary directory to create the file in

    Returns:
        Path to the MCP config file, or None if MCP is disabled
    """
    # Import here to avoid circular imports
    from app.core.config import settings

    # Skip if MCP is disabled or missing API keys
    if not settings.CLAUDE_USE_MCP:
        return None

    mcp_config_path = os.path.join(temp_dir, "mcp_config.json")

    mcp_config = {
        "servers": {}
    }

    # Add Brave Search if API key is available
    if settings.BRAVE_SEARCH_API_KEY:
        mcp_config["servers"]["brave-search"] = {
            "url": "https://brave-search.mcp.anthropic.com",
            "auth": {
                "type": "bearer",
                "token": settings.BRAVE_SEARCH_API_KEY
            }
        }

    # Only create file if we have at least one server configured
    if mcp_config["servers"]:
        with open(mcp_config_path, 'w') as f:
            json.dump(mcp_config, f, indent=2)
        return mcp_config_path

    return None
```

### 4. Enhance Stream Output Processing (2-3 days)

**File:** `app/services/claude_code/executor.py`

Improve the JSON stream parsing:

```python
def _process_stream_json(self, line: str, task_id: str, log_streamer) -> Dict[str, Any]:
    """
    Process a line of stream-json output from Claude Code.

    Args:
        line: Line of JSON output
        task_id: Task ID for logging
        log_streamer: Log streamer instance

    Returns:
        Parsed event data or empty dict if not valid
    """
    try:
        if not (line.startswith("{") and line.endswith("}")):
            return {}

        parsed = json.loads(line)
        if not isinstance(parsed, dict):
            return {}

        # Extract event type information
        event_type = parsed.get("type")

        # Skip events without a type
        if not event_type:
            return parsed

        # Handle different event types
        if event_type == "content_block_start":
            log_streamer.add_log(task_id, "Starting new content generation", level="info")

        elif event_type == "content_block_delta":
            # Content chunk
            content = parsed.get("delta", {}).get("text", "")
            if content.strip():
                # Only log substantial content
                log_streamer.add_log(task_id, f"Output: {content}", level="info")

        elif event_type == "message_stop":
            # Message complete
            log_streamer.add_log(task_id, "Claude Code processing completed", level="info")

        # Track usage and cost information
        if "usage" in parsed:
            usage = parsed.get("usage", {})
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            cost = usage.get("cost", 0)

            log_streamer.add_log(
                task_id,
                f"Usage stats: {input_tokens} input tokens, {output_tokens} output tokens, cost: ${cost:.4f}",
                level="info"
            )

        return parsed

    except json.JSONDecodeError:
        return {}
```

### 5. Update Progress Tracking (1-2 days)

**File:** `app/services/claude_code/progress_tracker.py`

Enhance the `Task.update()` method to handle more detailed status information:

```python
def update(self, status: str, progress: float = 0, message: str = ""):
    """
    Update the task status and notify subscribers.

    Args:
        status: Current status of the task
        progress: Progress percentage (0-100)
        message: Status message
    """
    self.status = status
    self.progress = progress
    self.message = message or self.message
    self.updated_at = time.time()

    # Notify all subscribers of the update
    self.notify_subscribers()
```

## Phase 2: Integration Improvements

### 6. Update Prompt Template for MCP Tools (1 day)

**File:** `claude_code_resume_prompt.md`

Add instructions for using the MCP tools:

```markdown
## Using External Tools

You have access to Brave Search through the MCP brave-search.brave_web_search tool. You can use this to:

1. Research latest trends or skills for the industry in the job description
2. Find relevant information about the company to better customize the resume
3. Research specific technical terms or requirements mentioned in the job

Example usage:
```
mcp__brave-search__brave_web_search:
{
  "query": "latest skills for [job role] 2024"
}
```

Use these insights to better align the resume with current industry expectations.
```

### 7. Update Frontend Progress Display (1-2 days)

**File:** `nextjs-frontend/components/progress-tracker.tsx`

Enhance the progress tracker to handle detailed status messages:

```typescript
// Update the WebSocket message handler
ws.onmessage = (event) => {
  try {
    console.log('WebSocket message received:', event.data);
    const data: StatusUpdate = JSON.parse(event.data);

    if (data.task_id === taskId) {
      console.log('Task status update:', data.status, data.message);
      setStatus(data.status);
      setMessage(data.message);

      // Add progress percentage if available
      if (data.progress !== undefined) {
        setProgress(data.progress);
      }

      // Add token usage data if available
      if (data.usage) {
        setUsageData(data.usage);
      }

      // Handle completion and errors
      if (data.status === 'completed' && onComplete) {
        console.log('Task completed, calling onComplete handler');
        onComplete(data);
        sendNotification('Resume Customization Complete', 'Your resume has been customized successfully.');
      } else if (data.status === 'error' && onError) {
        console.log('Task error, calling onError handler');
        onError(new Error(data.error || 'Unknown error'));
        sendNotification('Customization Failed', data.error || 'An error occurred during processing.');
      }
    }
  } catch (error) {
    console.error('Error parsing WebSocket message:', error);
  }
};
```

### 8. Testing Plan (3-4 days)

1. **Unit Tests:**
   - Update tests for ClaudeCodeExecutor
   - Test MCP configuration generation
   - Test system prompt file creation
   - Test enhanced stream parsing

2. **Integration Tests:**
   - Test end-to-end resume customization with new SDK features
   - Test WebSocket progress updates with enhanced status information
   - Test MCP-enabled customization (if API keys available)

3. **Manual Testing:**
   - Verify UI updates correctly with enhanced progress information
   - Test customization with and without MCP features
   - Compare outputs to ensure quality is maintained or improved

## Phase 3: Python SDK Migration (Future)

Once the Python SDK is released, we will:

1. Replace command-line execution with direct Python SDK calls
2. Simplify output parsing by using structured SDK responses
3. Leverage native streaming capabilities
4. Integrate MCP features directly through the SDK

## Timeline

| Phase | Estimated Timeline |
|-------|-------------------|
| Phase 1 | 7-10 days |
| Phase 2 | 5-7 days |
| Testing | 3-4 days |
| Total | 15-21 days |

## Dependencies and Requirements

1. Claude Code CLI (latest version with SDK features)
2. Brave Search API key (if using MCP features)
3. Updated configuration settings for system prompt and MCP enablement
4. Documentation updates for setup instructions

## Rollout Strategy

1. Implement in development environment
2. Conduct thorough testing
3. Prepare documentation for configuration changes
4. Deploy to staging environment
5. Monitor for any issues or performance changes
6. Deploy to production environment
