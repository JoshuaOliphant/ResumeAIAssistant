#!/usr/bin/env python
"""
Diagnostic script to identify problematic tests.

This script runs each test file and then each test class/function individually
to help identify which tests might be causing issues in CI.
"""

import os
import sys
import subprocess
import time
from pathlib import Path


def run_test(test_path, timeout=10):
    """Run a single test or test file with timeout."""
    start_time = time.time()
    cmd = ["python", "-m", "pytest", test_path, "-v"]
    
    print(f"\n\033[1;34mRunning: {' '.join(cmd)}\033[0m")
    
    try:
        # Set timeout to avoid hanging tests
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True,
            timeout=timeout
        )
        duration = time.time() - start_time
        
        # Print status based on return code
        if result.returncode == 0:
            print(f"\033[1;32m✅ PASSED\033[0m in {duration:.2f}s")
            return True
        else:
            print(f"\033[1;31m❌ FAILED\033[0m in {duration:.2f}s")
            print(f"\033[0;31mStdout:\033[0m\n{result.stdout}")
            print(f"\033[0;31mStderr:\033[0m\n{result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"\033[1;33m⚠️ TIMEOUT after {timeout}s\033[0m")
        return False


def get_test_classes_and_functions(test_file):
    """Get all test classes and functions in a test file."""
    cmd = ["python", "-m", "pytest", test_file, "--collect-only", "-v"]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error collecting tests from {test_file}")
        return []
    
    items = []
    for line in result.stdout.splitlines():
        if "<Function " in line or "<Class " in line:
            # Extract the test name - looks for patterns like 'test_name' or 'TestClass::test_method'
            parts = line.split()
            for part in parts:
                if "::" in part:
                    test_id = part
                    items.append(f"{test_file}::{test_id}")
                    break
    
    return items


def main():
    """Main function to run diagnostics on tests."""
    # Get the tests directory
    tests_dir = Path(__file__).parent.parent / "tests" / "unit"
    
    if not tests_dir.exists():
        print(f"Tests directory not found: {tests_dir}")
        return 1
    
    # Get all test files
    test_files = list(tests_dir.glob("test_*.py"))
    
    if not test_files:
        print(f"No test files found in {tests_dir}")
        return 1
    
    print(f"Found {len(test_files)} test files")
    
    # Test results
    results = {
        "passing_files": [],
        "failing_files": [],
        "timeout_files": [],
        "passing_tests": [],
        "failing_tests": [],
        "timeout_tests": []
    }
    
    # First, run each test file
    print("\n\033[1;36m=== Running Test Files ===\033[0m")
    for test_file in test_files:
        file_path = str(test_file.relative_to(tests_dir.parent.parent))
        if run_test(file_path):
            results["passing_files"].append(file_path)
        else:
            results["failing_files"].append(file_path)
    
    # For each failing file, run tests individually
    print("\n\033[1;36m=== Running Individual Tests from Failing Files ===\033[0m")
    for file_path in results["failing_files"]:
        print(f"\n\033[1;35mAnalyzing tests in {file_path}\033[0m")
        
        test_items = get_test_classes_and_functions(file_path)
        
        if not test_items:
            print(f"No individual tests found in {file_path}")
            continue
        
        print(f"Found {len(test_items)} individual tests")
        
        for test_item in test_items:
            if run_test(test_item):
                results["passing_tests"].append(test_item)
            else:
                results["failing_tests"].append(test_item)
    
    # Print summary
    print("\n\033[1;36m=== Summary ===\033[0m")
    print(f"Passing files: {len(results['passing_files'])}")
    for file in results["passing_files"]:
        print(f"  \033[1;32m✅ {file}\033[0m")
    
    print(f"\nFailing files: {len(results['failing_files'])}")
    for file in results["failing_files"]:
        print(f"  \033[1;31m❌ {file}\033[0m")
    
    print(f"\nPassing individual tests: {len(results['passing_tests'])}")
    for test in results["passing_tests"]:
        print(f"  \033[1;32m✅ {test}\033[0m")
    
    print(f"\nFailing individual tests: {len(results['failing_tests'])}")
    for test in results["failing_tests"]:
        print(f"  \033[1;31m❌ {test}\033[0m")
    
    # Print recommendation
    print("\n\033[1;36m=== Recommendation ===\033[0m")
    
    # Create a pytest command that runs only passing files and tests
    passing_command = "pytest "
    passing_command += " ".join(results["passing_files"])
    
    if results["passing_tests"]:
        passing_command += " " + " ".join(results["passing_tests"])
    
    print(f"Run only passing tests with:\n\033[1;32m{passing_command}\033[0m")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())