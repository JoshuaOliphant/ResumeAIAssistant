#!/usr/bin/env python
"""
Script to run all integration tests for the ResumeAIAssistant application.
This script assumes the application is already running.
"""
import os
import sys
import unittest
import importlib
import glob

def run_all_tests():
    """Run all integration tests in the tests/integration directory."""
    # Set up the test loader
    loader = unittest.TestLoader()
    
    # Discover and load all test modules in the integration directory
    test_dir = os.path.join(os.path.dirname(__file__), 'tests', 'integration')
    test_suite = loader.discover(test_dir, pattern='test_*.py')
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Return appropriate exit code
    return 0 if result.wasSuccessful() else 1

def run_specific_test(test_name):
    """Run a specific integration test."""
    # Check if the test file exists
    test_file = os.path.join('tests', 'integration', f'{test_name}.py')
    if not os.path.exists(test_file):
        print(f"Error: Test file '{test_file}' not found.")
        return 1
    
    # Import the test module
    module_name = f'tests.integration.{test_name}'
    try:
        module = importlib.import_module(module_name)
        # Run the main function if it exists
        if hasattr(module, 'main'):
            module.main()
        elif hasattr(module, '__main__'):
            getattr(module, '__main__')()
        else:
            print(f"Warning: No main function found in {test_name}. Running unittest discovery.")
            loader = unittest.TestLoader()
            test_suite = loader.loadTestsFromModule(module)
            runner = unittest.TextTestRunner(verbosity=2)
            result = runner.run(test_suite)
            return 0 if result.wasSuccessful() else 1
        return 0
    except Exception as e:
        print(f"Error running test {test_name}: {e}")
        return 1

def list_available_tests():
    """List all available integration tests."""
    test_dir = os.path.join(os.path.dirname(__file__), 'tests', 'integration')
    test_files = glob.glob(os.path.join(test_dir, 'test_*.py'))
    
    if not test_files:
        print("No integration tests found.")
        return
    
    print("Available integration tests:")
    for test_file in sorted(test_files):
        test_name = os.path.basename(test_file)[:-3]  # Remove .py extension
        print(f"  - {test_name}")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        # No arguments, run all tests
        sys.exit(run_all_tests())
    elif sys.argv[1] == "--list":
        # List available tests
        list_available_tests()
    else:
        # Run specific test
        test_name = sys.argv[1]
        if not test_name.startswith('test_'):
            test_name = f'test_{test_name}'
        sys.exit(run_specific_test(test_name))
