# ABOUTME: Result aggregation utilities for combining evaluation outcomes
# ABOUTME: Processes and combines results from multiple evaluators
"""
Result Aggregator

Utilities for aggregating and combining results from multiple evaluators
into comprehensive evaluation reports.
"""

from typing import Dict, List, Any
from ..test_data.models import EvaluationResult


class ResultAggregator:
    """Aggregates results from multiple evaluators."""
    
    def __init__(self):
        self.results: List[EvaluationResult] = []
    
    def add_result(self, result: EvaluationResult) -> None:
        """Add an evaluation result."""
        self.results.append(result)
    
    def aggregate(self) -> Dict[str, Any]:
        """
        Aggregate all results into a comprehensive summary.
        
        Returns:
            Dictionary containing aggregated metrics and analysis
        """
        # Placeholder implementation - will be enhanced in Issue #115
        return {
            "total_evaluations": len(self.results),
            "average_score": sum(r.overall_score for r in self.results) / len(self.results) if self.results else 0,
            "passed_evaluations": sum(1 for r in self.results if r.passed),
            "evaluator_breakdown": self._get_evaluator_breakdown()
        }
    
    def _get_evaluator_breakdown(self) -> Dict[str, Dict[str, Any]]:
        """Get breakdown by evaluator."""
        breakdown = {}
        for result in self.results:
            if result.evaluator_name not in breakdown:
                breakdown[result.evaluator_name] = {
                    "count": 0,
                    "total_score": 0,
                    "passed": 0
                }
            
            breakdown[result.evaluator_name]["count"] += 1
            breakdown[result.evaluator_name]["total_score"] += result.overall_score
            if result.passed:
                breakdown[result.evaluator_name]["passed"] += 1
        
        # Calculate averages
        for evaluator_data in breakdown.values():
            evaluator_data["average_score"] = evaluator_data["total_score"] / evaluator_data["count"]
            evaluator_data["pass_rate"] = evaluator_data["passed"] / evaluator_data["count"]
        
        return breakdown