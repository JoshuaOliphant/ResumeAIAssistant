# ABOUTME: Evaluation suite configurations for different testing scenarios
# ABOUTME: Provides predefined and customizable evaluation workflows

"""
Evaluation Suites

Contains predefined evaluation suite configurations for different testing scenarios,
from quick development feedback to comprehensive production evaluation.
"""

from .quick_suite import QuickEvaluationSuite

__all__ = [
    "QuickEvaluationSuite",
]