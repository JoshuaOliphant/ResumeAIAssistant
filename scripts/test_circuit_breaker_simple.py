#!/usr/bin/env python
"""
Simplified test script for the circuit breaker implementation in ResumeAIAssistant.
"""

import sys
import os
import json
from pprint import pprint

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set environment variable to ignore logfire warnings
os.environ["LOGFIRE_IGNORE_NO_CONFIG"] = "1"

# Import the necessary modules
from app.services.model_optimizer import (
    reset_circuit_breaker,
    get_circuit_breaker_status,
    record_model_failure,
    optimizer_circuit_breaker_lock
)

def main():
    """Main test function."""
    print("Testing circuit breaker implementation...")
    
    # Step 1: Check the initial circuit breaker status
    initial_status = get_circuit_breaker_status()
    print("\nInitial status:")
    pprint(initial_status)
    
    # Step 2: Simulate failures for the anthropic provider
    print("\nSimulating 3 failures for the anthropic provider...")
    with optimizer_circuit_breaker_lock:
        print("Failure 1")
        record_model_failure("anthropic", "Test failure 1", "TestError")
        
        print("Failure 2")
        record_model_failure("anthropic", "Test failure 2", "TestError")
        
        print("Failure 3")
        record_model_failure("anthropic", "Test failure 3", "TestError")
    
    # Step 3: Check the circuit breaker status after failures
    after_failures_status = get_circuit_breaker_status()
    print("\nStatus after failures:")
    pprint(after_failures_status)
    
    # Step 4: Reset the circuit breaker for the anthropic provider
    print("\nResetting circuit breaker for anthropic provider...")
    reset_result = reset_circuit_breaker("anthropic")
    print(f"Reset result: {reset_result}")
    
    # Step 5: Check the circuit breaker status after resetting anthropic
    after_reset_status = get_circuit_breaker_status()
    print("\nStatus after resetting anthropic:")
    pprint(after_reset_status)
    
    # Step 6: Summarize the test results
    print("\nTest Summary:")
    print("-"*40)
    
    # Check if anthropic circuit was opened after failures
    if after_failures_status["open_circuits"].get("anthropic", False):
        print("✅ Anthropic circuit was opened after failures")
    else:
        print("❌ Anthropic circuit was not opened after failures")
    
    # Check if anthropic circuit was successfully reset
    if not after_reset_status["open_circuits"].get("anthropic", False):
        print("✅ Anthropic circuit was successfully reset")
    else:
        print("❌ Anthropic circuit reset failed")
    
    print("-"*40)
    print("Circuit breaker test completed.")

if __name__ == "__main__":
    main()