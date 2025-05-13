#!/usr/bin/env python
"""
Test script for the circuit breaker implementation in ResumeAIAssistant.

This script tests the reset_circuit_breaker function and checks if it 
properly resets the circuit breaker state for specific providers or all providers.
"""

import sys
import os
import time
import asyncio
import json
from pprint import pprint

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the necessary modules
from app.services.model_optimizer import (
    reset_circuit_breaker,
    get_circuit_breaker_status,
    record_model_failure,
    optimizer_circuit_breaker_lock
)

async def main():
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
    
    # Step 3: Simulate a failure for the openai provider
    print("\nSimulating 1 failure for the openai provider...")
    with optimizer_circuit_breaker_lock:
        record_model_failure("openai", "Test failure", "TestError")
    
    # Step 4: Check the circuit breaker status after failures
    after_failures_status = get_circuit_breaker_status()
    print("\nStatus after failures:")
    pprint(after_failures_status)
    
    # Step 5: Reset the circuit breaker for the anthropic provider
    print("\nResetting circuit breaker for anthropic provider...")
    reset_result = reset_circuit_breaker("anthropic")
    print(f"Reset result: {reset_result}")
    
    # Step 6: Check the circuit breaker status after resetting anthropic
    after_reset_anthropic_status = get_circuit_breaker_status()
    print("\nStatus after resetting anthropic:")
    pprint(after_reset_anthropic_status)
    
    # Step 7: Reset all circuit breakers
    print("\nResetting all circuit breakers...")
    reset_all_result = reset_circuit_breaker()
    print(f"Reset all result: {reset_all_result}")
    
    # Step 8: Check the circuit breaker status after resetting all
    final_status = get_circuit_breaker_status()
    print("\nFinal status after resetting all:")
    pprint(final_status)
    
    # Step 9: Summarize the test results
    print("\nTest Summary:")
    print("-"*40)
    if initial_status["open_circuits"] == {} and final_status["open_circuits"] == {}:
        print("✅ Initial and final states are clean (no open circuits)")
    else:
        print("❌ Initial or final states have open circuits")
    
    if after_failures_status["open_circuits"].get("anthropic", False):
        print("✅ Anthropic circuit was opened after failures")
    else:
        print("❌ Anthropic circuit was not opened after failures")
    
    if not after_reset_anthropic_status["open_circuits"].get("anthropic", False):
        print("✅ Anthropic circuit was successfully reset")
    else:
        print("❌ Anthropic circuit reset failed")
    
    if after_reset_anthropic_status["open_circuits"].get("openai", False) and not final_status["open_circuits"].get("openai", False):
        print("✅ Reset all successfully cleared the openai circuit")
    else:
        print("❌ Issue with reset all functionality")
    
    print("-"*40)
    print("Circuit breaker test completed.")

if __name__ == "__main__":
    asyncio.run(main())