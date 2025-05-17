#!/usr/bin/env python3
"""
Verification script for Resume AI Assistant setup.

This script checks if all required components and dependencies for the 
Resume AI Assistant application are properly set up.
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    NC = '\033[0m'  # No Color

    @staticmethod
    def colorize(color, text):
        """Colorize text if not on Windows."""
        if platform.system() == 'Windows' and not os.environ.get('TERM'):
            return text
        return f"{color}{text}{Colors.NC}"


def print_message(message):
    """Print info message."""
    print(f"{Colors.colorize(Colors.GREEN, '[INFO]')} {message}")


def print_warning(message):
    """Print warning message."""
    print(f"{Colors.colorize(Colors.YELLOW, '[WARNING]')} {message}")


def print_error(message):
    """Print error message."""
    print(f"{Colors.colorize(Colors.RED, '[ERROR]')} {message}")


def check_virtualenv():
    """Check if we're running in a virtual environment."""
    if not hasattr(sys, 'base_prefix') or sys.base_prefix == sys.prefix:
        print_warning("Not running in a virtual environment.")
        return False
    print_message("Running in a virtual environment.")
    return True


def check_python_version():
    """Check Python version."""
    required_version = (3, 9)
    current_version = sys.version_info[:2]
    
    if current_version >= required_version:
        print_message(f"Python version {sys.version.split()[0]} is OK (required: 3.9+).")
        return True
    else:
        print_error(f"Python version {sys.version.split()[0]} is too old. Required 3.9+.")
        return False


def check_python_packages():
    """Check if required Python packages are installed."""
    try:
        import fastapi
        import uvicorn
        import websockets
        import pydantic
        print_message("Required Python packages are installed.")
        return True
    except ImportError as e:
        print_error(f"Python package not found: {e.name}")
        return False


def check_spacy_model():
    """Check if SpaCy and required language models are installed."""
    try:
        import spacy
        print_message("SpaCy is installed.")
        
        # Check if the English model is installed
        try:
            nlp = spacy.load("en_core_web_sm")
            print_message("SpaCy English language model is installed.")
            return True
        except OSError:
            # Model not found
            print_warning("SpaCy English language model is not installed.")
            
            # Check for downloaded model in .downloads directory
            downloads_dir = Path('.downloads')
            if downloads_dir.exists():
                model_files = list(downloads_dir.glob('en_core_web_sm-*.whl'))
                if model_files:
                    print_message(f"Found downloaded SpaCy model at: {model_files[0]}")
                    print_message("You can install it with:")
                    if platform.system() == 'Windows':
                        print(f"  .venv\\Scripts\\activate.bat && python -m pip install {model_files[0]}")
                    else:
                        print(f"  source .venv/bin/activate && python -m pip install {model_files[0]}")
            
            print_warning("To install the model, run: python -m spacy download en_core_web_sm")
            return False
            
    except ImportError:
        print_warning("SpaCy is not installed.")
        return False


def check_node():
    """Check if Node.js is installed."""
    try:
        result = subprocess.run(
            ["node", "--version"], 
            capture_output=True, 
            text=True, 
            check=True
        )
        version = result.stdout.strip()
        major_version = int(version.lstrip('v').split('.')[0])
        
        if major_version >= 14:
            print_message(f"Node.js version {version} is OK (required: 14+).")
            return True
        else:
            print_error(f"Node.js version {version} is too old. Required 14+.")
            return False
    except (subprocess.SubprocessError, FileNotFoundError):
        print_error("Node.js is not installed or not in PATH.")
        return False


def check_npm_packages():
    """Check if required npm packages are installed in the frontend directory."""
    frontend_dir = Path('nextjs-frontend')
    
    if not frontend_dir.exists() or not frontend_dir.is_dir():
        print_error("Frontend directory 'nextjs-frontend' not found.")
        return False
    
    node_modules = frontend_dir / 'node_modules'
    package_json = frontend_dir / 'package.json'
    
    if not package_json.exists():
        print_error("package.json not found in frontend directory.")
        return False
    
    if not node_modules.exists() or not node_modules.is_dir():
        print_error("node_modules not found. npm install has not been run.")
        return False
    
    print_message("Frontend dependencies appear to be installed.")
    return True


def check_env_file():
    """Check if .env.local file exists."""
    env_file = Path('.env.local')
    
    if not env_file.exists():
        print_warning(".env.local file not found. Configuration settings may be missing.")
        return False
    
    with open(env_file, 'r') as f:
        content = f.read()
    
    if 'your-anthropic-api-key' in content:
        print_warning("Anthropic API key in .env.local appears to be the default value. "
                     "Make sure to update it with your actual API key.")
    
    # Check for SpaCy model path
    if 'SPACY_MODEL_PATH' in content and not content.strip().split('SPACY_MODEL_PATH=')[1].startswith('#'):
        model_path = content.strip().split('SPACY_MODEL_PATH=')[1].split('\n')[0].strip()
        if model_path and Path(model_path).exists():
            print_message(f"Custom SpaCy model path found: {model_path}")
        else:
            print_warning(f"Custom SpaCy model path specified but file not found: {model_path}")
    
    print_message(".env.local file found.")
    return True


def check_claude_cli():
    """Check if Claude CLI is installed."""
    claude_cli_path = shutil.which('claude')
    
    if claude_cli_path:
        print_message("Claude CLI is installed.")
        return True
    else:
        print_warning("Claude CLI not found in PATH. This is required for full functionality.")
        print_warning("Follow installation instructions at: "
                    "https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/overview")
        return False


def run_all_checks():
    """Run all verification checks."""
    print_message("Starting verification of Resume AI Assistant setup...")
    
    checks = [
        check_virtualenv,
        check_python_version,
        check_python_packages,
        check_spacy_model,
        check_node,
        check_npm_packages,
        check_env_file,
        check_claude_cli
    ]
    
    results = [check() for check in checks]
    success_rate = sum(results) / len(results) * 100
    
    print("\n" + "="*60)
    print(f"Verification complete: {success_rate:.1f}% passed")
    print("="*60)
    
    if all(results):
        print_message("All checks passed! Your setup appears to be complete.")
        print_message("You can start the application with:")
        print("  1. Backend:  uv run uvicorn main:app --host 0.0.0.0 --port 5001 --reload")
        print("  2. Frontend: cd nextjs-frontend && npm run dev")
    else:
        print_warning("Some checks failed. Please address the issues above.")
    
    return all(results)


if __name__ == "__main__":
    # Allow checking for specific components
    if len(sys.argv) > 1:
        if sys.argv[1] == "--spacy":
            success = check_spacy_model()
            sys.exit(0 if success else 1)
        elif sys.argv[1] == "--help":
            print("Usage: python verify_setup.py [option]")
            print("Options:")
            print("  --spacy   Check only SpaCy model installation")
            print("  --help    Show this help message")
            sys.exit(0)
            
    # Run all checks by default
    success = run_all_checks()
    sys.exit(0 if success else 1)