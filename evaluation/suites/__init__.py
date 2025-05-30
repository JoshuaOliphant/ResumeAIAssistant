# ABOUTME: Evaluation suite configurations for different testing scenarios
# ABOUTME: Provides predefined and customizable evaluation workflows

"""
Evaluation Suites

Contains predefined evaluation suite configurations for different testing scenarios,
from quick development feedback to comprehensive production evaluation.
"""

from .quick_suite import QuickEvaluationSuite
from .comprehensive_suite import ComprehensiveEvaluationSuite
from .custom_suite import CustomEvaluationSuite

__all__ = [
    "QuickEvaluationSuite",
    "ComprehensiveEvaluationSuite", 
    "CustomEvaluationSuite"
]