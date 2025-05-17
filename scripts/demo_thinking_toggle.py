"""
Demonstrate the thinking toggle functionality.

This script shows how to toggle the thinking capability via environment variables
and how it affects model configurations.
"""

import os
import sys
import json
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# First import with thinking enabled (default)
print("=== Testing with thinking ENABLED (default) ===")
from app.core.config import settings
from app.services.thinking_budget import calculate_thinking_budget, TaskComplexity

print(f"PYDANTICAI_ENABLE_THINKING = {settings.PYDANTICAI_ENABLE_THINKING}")

# Calculate budget with thinking enabled
budget, config = calculate_thinking_budget(
    task_complexity=TaskComplexity.COMPLEX,
    model_provider="google"
)

print(f"Thinking Budget: {budget} tokens")
print(f"Thinking Config: {json.dumps(config, indent=2)}")
print("\n")

# Now disable thinking and re-import settings
print("=== Testing with thinking DISABLED ===")
os.environ["PYDANTICAI_ENABLE_THINKING"] = "false"

# Force reload the settings module
import importlib
importlib.reload(sys.modules['app.core.config'])
from app.core.config import settings

print(f"PYDANTICAI_ENABLE_THINKING = {settings.PYDANTICAI_ENABLE_THINKING}")

# Reload thinking_budget to pick up new settings
importlib.reload(sys.modules['app.services.thinking_budget'])
from app.services.thinking_budget import calculate_thinking_budget, TaskComplexity

# Calculate budget with thinking disabled
budget, config = calculate_thinking_budget(
    task_complexity=TaskComplexity.COMPLEX,
    model_provider="google"
)

print(f"Thinking Budget: {budget} tokens")
print(f"Thinking Config: {json.dumps(config, indent=2)}")

print("\n=== How to use in your application ===")
print("To disable thinking: export PYDANTICAI_ENABLE_THINKING=false")
print("To enable thinking:  export PYDANTICAI_ENABLE_THINKING=true (default)")
print("Accepted values for true: 'true', '1', 'yes', 'y', 't' (case-insensitive)")
print("Accepted values for false: 'false', '0', 'no', 'n', 'f' (case-insensitive)")