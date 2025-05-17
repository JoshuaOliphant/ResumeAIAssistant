"""
Tests for the ResumeAIAssistant application.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path to resolve imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
