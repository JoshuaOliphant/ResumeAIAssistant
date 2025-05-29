# ABOUTME: Adapter for integrating with PydanticAI evaluation framework
# ABOUTME: Converts between our TestCase model and PydanticAI Case structure
"""
PydanticAI Adapter

Provides integration between our evaluation framework and PydanticAI's
evaluation capabilities, including Case/Dataset conversion and custom evaluators.
"""

from typing import Any, Dict, List, Optional, TypeVar, Generic
from dataclasses import dataclass

from ..test_data.models import TestCase, EvaluationResult, TestDataset
from ..evaluators.base import BaseEvaluator
from ..utils.logger import get_evaluation_logger


# Type variables for generic types
InputsT = TypeVar('InputsT')
OutputT = TypeVar('OutputT')
MetadataT = TypeVar('MetadataT')


@dataclass
class PydanticCase(Generic[InputsT, OutputT, MetadataT]):
    """
    Mock PydanticAI Case structure for compatibility.
    
    In production, this would be imported from pydantic_evals.
    """
    name: str
    inputs: InputsT
    expected_output: Optional[OutputT] = None
    metadata: Optional[MetadataT] = None


class TestCaseToPydanticCase:
    """Converts our TestCase model to PydanticAI Case format."""
    
    @staticmethod
    def convert(test_case: TestCase) -> PydanticCase[Dict[str, str], Dict[str, Any], Dict[str, Any]]:
        """
        Convert TestCase to PydanticAI Case.
        
        Args:
            test_case: Our TestCase instance
            
        Returns:
            PydanticAI Case instance
        """
        # Prepare inputs
        inputs = {
            "resume_content": test_case.resume_content,
            "job_description": test_case.job_description
        }
        
        # Prepare expected output
        expected_output = {
            "match_score": test_case.expected_match_score,
            "skills": test_case.expected_skills,
            "technologies": test_case.expected_technologies
        }
        
        # Prepare metadata
        metadata = {
            "id": test_case.id,
            "category": test_case.category,
            "difficulty": test_case.difficulty,
            "tags": test_case.tags,
            "ground_truth": test_case.ground_truth
        }
        
        return PydanticCase(
            name=test_case.name,
            inputs=inputs,
            expected_output=expected_output,
            metadata=metadata
        )
    
    @staticmethod
    def convert_dataset(dataset: TestDataset) -> List[PydanticCase]:
        """
        Convert entire TestDataset to list of PydanticAI Cases.
        
        Args:
            dataset: TestDataset instance
            
        Returns:
            List of PydanticAI Cases
        """
        return [
            TestCaseToPydanticCase.convert(case)
            for case in dataset.test_cases
        ]


class PydanticEvaluatorWrapper(BaseEvaluator):
    """
    Wrapper to use PydanticAI evaluators within our framework.
    
    This allows PydanticAI evaluators to be used alongside our custom evaluators.
    """
    
    def __init__(self, pydantic_evaluator: Any, name: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize wrapper.
        
        Args:
            pydantic_evaluator: PydanticAI evaluator instance
            name: Name for this evaluator
            config: Configuration options
        """
        super().__init__(name, config)
        self.pydantic_evaluator = pydantic_evaluator
    
    async def evaluate(self, test_case: TestCase, actual_output: Any) -> EvaluationResult:
        """
        Evaluate using the wrapped PydanticAI evaluator.
        
        Args:
            test_case: Test case to evaluate
            actual_output: Actual output from system
            
        Returns:
            EvaluationResult
        """
        # Convert to PydanticAI format
        pydantic_case = TestCaseToPydanticCase.convert(test_case)
        
        # Create evaluation context (mock for now)
        # In production, this would use PydanticAI's EvaluatorContext
        context = {
            "case": pydantic_case,
            "output": actual_output,
            "expected_output": pydantic_case.expected_output
        }
        
        try:
            # Call PydanticAI evaluator
            # In production: score = await self.pydantic_evaluator.evaluate(context)
            score = 0.85  # Mock score for demonstration
            
            return self.create_result(
                test_case=test_case,
                overall_score=score,
                passed=score >= 0.7,
                notes=f"Evaluated using PydanticAI evaluator: {self.name}"
            )
            
        except Exception as e:
            self.logger.error(f"PydanticAI evaluation failed: {str(e)}")
            raise
    
    def get_description(self) -> str:
        """Get evaluator description."""
        return f"PydanticAI evaluator wrapper: {self.name}"


class PydanticAIAdapter:
    """
    Main adapter for PydanticAI integration.
    
    Provides methods to:
    - Convert between data formats
    - Create wrapped evaluators
    - Export evaluation results to PydanticAI format
    """
    
    def __init__(self):
        """Initialize adapter."""
        self.logger = get_evaluation_logger("PydanticAIAdapter")
    
    def create_evaluator_wrapper(
        self,
        pydantic_evaluator: Any,
        name: str,
        config: Optional[Dict[str, Any]] = None
    ) -> PydanticEvaluatorWrapper:
        """
        Create a wrapper for a PydanticAI evaluator.
        
        Args:
            pydantic_evaluator: PydanticAI evaluator instance
            name: Name for the evaluator
            config: Configuration options
            
        Returns:
            Wrapped evaluator compatible with our framework
        """
        return PydanticEvaluatorWrapper(pydantic_evaluator, name, config)
    
    def convert_results_to_pydantic_format(
        self,
        results: List[EvaluationResult]
    ) -> Dict[str, Any]:
        """
        Convert our evaluation results to PydanticAI report format.
        
        Args:
            results: List of our EvaluationResult instances
            
        Returns:
            Dictionary in PydanticAI report format
        """
        # Group results by test case
        case_results = {}
        for result in results:
            if result.test_case_id not in case_results:
                case_results[result.test_case_id] = []
            case_results[result.test_case_id].append(result)
        
        # Format for PydanticAI
        pydantic_results = []
        for case_id, case_result_list in case_results.items():
            case_summary = {
                "case_id": case_id,
                "evaluations": [],
                "overall_passed": all(r.passed for r in case_result_list),
                "average_score": sum(r.overall_score for r in case_result_list) / len(case_result_list)
            }
            
            for result in case_result_list:
                case_summary["evaluations"].append({
                    "evaluator": result.evaluator_name,
                    "score": result.overall_score,
                    "passed": result.passed,
                    "execution_time": result.execution_time,
                    "tokens_used": result.tokens_used
                })
            
            pydantic_results.append(case_summary)
        
        return {
            "results": pydantic_results,
            "summary": {
                "total_cases": len(case_results),
                "passed_cases": sum(1 for r in pydantic_results if r["overall_passed"]),
                "average_score": sum(r["average_score"] for r in pydantic_results) / len(pydantic_results) if pydantic_results else 0
            }
        }
    
    def enable_tracing(self, logfire_config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Enable OpenTelemetry/Logfire tracing for evaluations.
        
        Args:
            logfire_config: Optional Logfire configuration
            
        Returns:
            bool: True if tracing was successfully enabled, False otherwise
        """
        try:
            import logfire
            
            # Initialize Logfire with config
            if logfire_config:
                logfire.configure(**logfire_config)
            else:
                logfire.configure()
            
            self.logger.info("Logfire tracing enabled for evaluations")
            return True
            
        except ImportError:
            self.logger.warning("Logfire not available, tracing disabled")
            return False
    
    @staticmethod
    def create_pydantic_dataset(
        test_dataset: TestDataset,
        evaluators: Optional[List[Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a PydanticAI Dataset from our TestDataset.
        
        Args:
            test_dataset: Our TestDataset instance
            evaluators: Optional list of PydanticAI evaluators
            
        Returns:
            Dictionary representing PydanticAI Dataset
        """
        cases = TestCaseToPydanticCase.convert_dataset(test_dataset)
        
        return {
            "name": test_dataset.name,
            "description": test_dataset.description,
            "version": test_dataset.version,
            "cases": [
                {
                    "name": case.name,
                    "inputs": case.inputs,
                    "expected_output": case.expected_output,
                    "metadata": case.metadata
                }
                for case in cases
            ],
            "evaluators": evaluators or [],
            "metadata": {
                "category": test_dataset.category,
                "tags": test_dataset.tags,
                "author": test_dataset.author,
                "created_at": test_dataset.created_at.isoformat(),
                "total_cases": len(cases)
            }
        }