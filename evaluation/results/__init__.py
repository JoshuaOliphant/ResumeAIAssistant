# ABOUTME: Result processing and analysis tools for evaluation data
# ABOUTME: Handles aggregation, reporting, and visualization of evaluation results
"""
Results Processing Module

Provides tools for processing, analyzing, and reporting evaluation results.
Includes aggregation utilities, report generation, and visualization components.
"""

from .aggregator import ResultAggregator
from .reporter import EvaluationReporter
from .analyzer import PerformanceAnalyzer

__all__ = [
    "ResultAggregator",
    "EvaluationReporter",
    "PerformanceAnalyzer",
]