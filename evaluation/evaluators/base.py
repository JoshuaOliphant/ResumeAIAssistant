# ABOUTME: Base evaluator class defining the interface for all evaluators
# ABOUTME: Provides common functionality and abstract methods for evaluation components
"""
Base Evaluator

Abstract base class for all evaluators in the framework. Defines the common
interface and provides shared functionality for evaluation components.
"""

from abc import ABC, abstractmethod
import asyncio
import time
from typing import Any, Dict, List, Optional, Union
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
        self._is_async = asyncio.iscoroutinefunction(self.evaluate)
    
    @abstractmethod
    async def evaluate(self, test_case: TestCase, actual_output: Any) -> EvaluationResult:
        """
        Evaluate a test case against actual output (async version).
        
        Args:
            test_case: Test case to evaluate
            actual_output: Actual output from the system being tested
            
        Returns:
            EvaluationResult with scores and analysis
        """
        pass
    
    def evaluate_sync(self, test_case: TestCase, actual_output: Any) -> EvaluationResult:
        """
        Synchronous version of evaluate method.
        
        Args:
            test_case: Test case to evaluate
            actual_output: Actual output from the system being tested
            
        Returns:
            EvaluationResult with scores and analysis
        """
        # Default implementation runs async method in event loop
        if self._is_async:
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(self.evaluate(test_case, actual_output))
            finally:
                loop.close()
        else:
            # If evaluate is not async, call it directly
            return self.evaluate(test_case, actual_output)
    
    async def evaluate_batch(
        self,
        test_cases: List[TestCase],
        actual_outputs: List[Any]
    ) -> List[EvaluationResult]:
        """
        Evaluate multiple test cases in batch.
        
        Args:
            test_cases: List of test cases to evaluate
            actual_outputs: List of actual outputs corresponding to test cases
            
        Returns:
            List of EvaluationResult instances
        """
        if len(test_cases) != len(actual_outputs):
            raise ValueError("Number of test cases must match number of outputs")
        
        # Run evaluations concurrently
        tasks = [
            self.evaluate(case, output)
            for case, output in zip(test_cases, actual_outputs)
        ]
        
        return await asyncio.gather(*tasks)
    
    @abstractmethod
    def get_description(self) -> str:
        """Get a description of what this evaluator tests."""
        pass
    
    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get evaluator capabilities and requirements.
        
        Returns:
            Dictionary describing evaluator capabilities
        """
        return {
            "name": self.name,
            "description": self.get_description(),
            "is_async": self._is_async,
            "supports_batch": True,
            "config": self.config
        }
    
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
        execution_time: Optional[float] = None,
        api_calls_made: int = 0,
        tokens_used: int = 0,
        **kwargs
    ) -> EvaluationResult:
        """
        Create an EvaluationResult instance with resource tracking.
        
        Args:
            test_case: Test case that was evaluated
            overall_score: Overall evaluation score (0-1)
            detailed_scores: Detailed scores by metric
            passed: Whether the evaluation passed
            notes: Additional notes
            execution_time: Time taken for evaluation in seconds
            api_calls_made: Number of API calls made
            tokens_used: Total tokens consumed
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
            execution_time=execution_time or 0.0,
            api_calls_made=api_calls_made,
            tokens_used=tokens_used,
            evaluation_model=self.config.get("model", ""),
            configuration=self.config,
            **kwargs
        )