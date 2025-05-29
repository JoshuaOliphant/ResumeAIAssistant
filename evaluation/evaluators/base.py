# ABOUTME: Base evaluator class defining the interface for all evaluators
# ABOUTME: Provides common functionality and abstract methods for evaluation components
"""
Base Evaluator

Abstract base class for all evaluators in the framework. Defines the common
interface and provides shared functionality for evaluation components.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from ..test_data.models import TestCase, EvaluationResult
from ..utils.logger import get_evaluation_logger


class BaseEvaluator(ABC):
    """Abstract base class for all evaluators."""
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the evaluator.
        
        Args:
            name: Name of the evaluator
            config: Configuration dictionary
        """
        self.name = name
        self.config = config or {}
        self.logger = get_evaluation_logger(name)
    
    @abstractmethod
    async def evaluate(self, test_case: TestCase, actual_output: Any) -> EvaluationResult:
        """
        Evaluate a test case against actual output.
        
        Args:
            test_case: Test case to evaluate
            actual_output: Actual output from the system being tested
            
        Returns:
            EvaluationResult with scores and analysis
        """
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Get a description of what this evaluator tests."""
        pass
    
    def validate_inputs(self, test_case: TestCase, actual_output: Any) -> bool:
        """
        Validate inputs before evaluation.
        
        Args:
            test_case: Test case to validate
            actual_output: Actual output to validate
            
        Returns:
            True if inputs are valid
            
        Raises:
            ValueError: If inputs are invalid
        """
        if not isinstance(test_case, TestCase):
            raise ValueError("test_case must be a TestCase instance")
        
        if actual_output is None:
            raise ValueError("actual_output cannot be None")
        
        return True
    
    def create_result(
        self,
        test_case: TestCase,
        overall_score: float,
        detailed_scores: Optional[Dict[str, float]] = None,
        passed: bool = True,
        notes: Optional[str] = None,
        **kwargs
    ) -> EvaluationResult:
        """
        Create an EvaluationResult instance.
        
        Args:
            test_case: Test case that was evaluated
            overall_score: Overall evaluation score (0-1)
            detailed_scores: Detailed scores by metric
            passed: Whether the evaluation passed
            notes: Additional notes
            **kwargs: Additional fields for the result
            
        Returns:
            EvaluationResult instance
        """
        return EvaluationResult(
            test_case_id=test_case.id,
            evaluator_name=self.name,
            overall_score=overall_score,
            detailed_scores=detailed_scores or {},
            passed=passed,
            notes=notes,
            **kwargs
        )