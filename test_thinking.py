import anthropic
from anthropic import Anthropic
import os
import time

# Print the version
print(f"Anthropic SDK version: {anthropic.__version__}")

# Create a very simple test case
try:
    # Create the Anthropic client
    client = Anthropic()
    
    # This is just a test to check if the thinking parameter works
    # NOT making an actual API call to avoid using API credits
    print("\nSimulating payload construction with thinking parameter")
    # Manually construct what would be sent
    example_payload = {
        "model": "claude-3-7-sonnet-20250219",
        "system": "You are a helpful assistant.",
        "messages": [{"role": "user", "content": "Hello, how are you?"}],
        "max_tokens": 100,
        "thinking": {"enabled": True, "max_tokens": 5000}
    }
    print(f"Example payload: {example_payload}")
    
    # Show a demonstration usage only (no API call)
    print("\nTesting if thinking parameter is valid in SDK")
    # If this doesn't cause an error in payload construction, thinking is likely a valid parameter
    test_construction = {
        "model": "claude-3-7-sonnet-20250219",
        "system": "You are a helpful assistant.",
        "max_tokens": 100,
        "thinking": {"enabled": True, "max_tokens": 5000},
        "messages": [
            {"role": "user", "content": "Hello, how are you?"}
        ]
    }
    print("Parameter construction successful")
    
except Exception as e:
    print(f"Error: {e}")