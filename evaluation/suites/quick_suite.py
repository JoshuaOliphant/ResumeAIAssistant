# ABOUTME: Quick evaluation suite for fast development feedback
# ABOUTME: Runs essential evaluators with optimized settings for speed

"""
Quick Evaluation Suite

Provides fast evaluation feedback for development workflows by running
only essential evaluators with optimized configurations.
"""

from pathlib import Path
from typing import Dict, List, Optional

from ..pipeline import EvaluationPipeline, PipelineConfiguration, PipelineMode
from ..test_data.models import TestCase
from ..utils.logger import get_evaluation_logger


class QuickEvaluationSuite:
    """
    Quick evaluation suite optimized for development feedback.
    
    Focuses on essential metrics while maintaining fast execution times.
    Ideal for rapid iteration during development and testing.
    """
    
    def __init__(self, output_directory: Optional[Path] = None):
        """
        Initialize quick evaluation suite.
        
        Args:
            output_directory: Optional directory for saving results
        """
        self.logger = get_evaluation_logger("QuickEvaluationSuite")
        self.output_directory = output_directory
        
        # Quick suite configuration
        self.config = PipelineConfiguration(
            mode=PipelineMode.QUICK,
            parallel_execution=True,
            max_concurrent_evaluators=3,
            fail_fast=False,  # Continue even if one evaluator fails
            save_intermediate_results=bool(output_directory),
            output_directory=output_directory,
            
            # Optimized weights for quick feedback
            weight_accuracy=0.4,   # Higher weight on accuracy for dev feedback
            weight_quality=0.3,
            weight_relevance=0.3,
            confidence_threshold=0.6,  # Lower threshold for quick results
            
            # Fast error recovery
            retry_failed_evaluators=True,
            max_retries=1,  # Fewer retries for speed
            retry_delay=0.5
        )
        
        self.pipeline = EvaluationPipeline(self.config)
    
    async def evaluate_single(
        self,
        resume_content: str,
        job_description: str,
        test_case_id: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Run quick evaluation on a single resume-job pair.
        
        Args:
            resume_content: Resume content to evaluate
            job_description: Job description to match against
            test_case_id: Optional test case identifier
            
        Returns:
            Quick evaluation results with essential metrics
        """
        test_case_id = test_case_id or f"quick_eval_{int(time.time())}"
        
        self.logger.info(f"Running quick evaluation for test case {test_case_id}")
        
        # Create test case
        test_case = TestCase(
            id=test_case_id,
            name=f"Quick Evaluation {test_case_id}",
            resume_content=resume_content,
            job_description=job_description
        )
        
        # Create actual output
        actual_output = {
            "resume_content": resume_content,
            "job_description": job_description,
            "optimization_applied": False
        }
        
        # Run pipeline
        result = await self.pipeline.evaluate(test_case, actual_output, test_case_id)
        
        # Return simplified results for quick feedback
        return {
            "evaluation_id": result.pipeline_id,
            "test_case_id": result.test_case_id,
            "duration_seconds": result.total_duration,
            "overall_score": result.overall_score,
            "confidence_score": result.confidence_score,
            "category_scores": result.category_scores,
            "quick_summary": self._generate_quick_summary(result),
            "key_issues": self._identify_key_issues(result),
            "next_steps": self._suggest_next_steps(result)
        }
    
    async def evaluate_batch(
        self,
        resume_job_pairs: List[Dict[str, str]],
        batch_id: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Run quick evaluation on a batch of resume-job pairs.
        
        Args:
            resume_job_pairs: List of {"resume": str, "job": str} dictionaries
            batch_id: Optional batch identifier
            
        Returns:
            Batch evaluation results with aggregate metrics
        """
        import time
        batch_id = batch_id or f"quick_batch_{int(time.time())}"
        
        self.logger.info(f"Running quick batch evaluation {batch_id} on {len(resume_job_pairs)} pairs")
        
        results = []
        start_time = time.time()
        
        for i, pair in enumerate(resume_job_pairs):
            try:
                result = await self.evaluate_single(
                    pair["resume"],
                    pair["job"],
                    f"{batch_id}_case_{i+1}"
                )
                results.append(result)
                
            except Exception as e:
                self.logger.error(f"Failed to evaluate pair {i+1}: {str(e)}")
                results.append({
                    "evaluation_id": f"{batch_id}_case_{i+1}",
                    "error": str(e),
                    "overall_score": 0.0
                })
        
        total_duration = time.time() - start_time
        
        # Calculate batch metrics
        successful_results = [r for r in results if "error" not in r]
        
        batch_summary = {
            "batch_id": batch_id,
            "total_pairs": len(resume_job_pairs),
            "successful_evaluations": len(successful_results),
            "failed_evaluations": len(results) - len(successful_results),
            "batch_duration_seconds": total_duration,
            "average_score": sum(r["overall_score"] for r in successful_results) / len(successful_results) if successful_results else 0,
            "score_distribution": self._calculate_score_distribution(successful_results),
            "common_issues": self._identify_common_issues(successful_results),
            "batch_recommendations": self._generate_batch_recommendations(successful_results)
        }
        
        return {
            "batch_summary": batch_summary,
            "individual_results": results
        }
    
    def _generate_quick_summary(self, result) -> str:
        """Generate a quick text summary of results."""
        score = result.overall_score
        confidence = result.confidence_score
        
        if score >= 0.8:
            quality = "Excellent"
        elif score >= 0.6:
            quality = "Good"
        elif score >= 0.4:
            quality = "Fair"
        else:
            quality = "Poor"
        
        confidence_level = "High" if confidence >= 0.7 else "Medium" if confidence >= 0.5 else "Low"
        
        return f"{quality} resume-job match (score: {score:.2f}) with {confidence_level.lower()} confidence"
    
    def _identify_key_issues(self, result) -> List[str]:
        """Identify key issues for quick feedback."""
        issues = []
        
        # Check category scores
        for category, score in result.category_scores.items():
            if score < 0.5:
                issues.append(f"Low {category} score ({score:.2f})")
        
        # Check failed evaluators
        if result.failed_evaluators:
            issues.append(f"Failed evaluators: {', '.join(result.failed_evaluators.keys())}")
        
        # Check confidence
        if result.confidence_score < 0.5:
            issues.append("Low confidence in results - consider manual review")
        
        return issues[:3]  # Return top 3 issues for quick feedback
    
    def _suggest_next_steps(self, result) -> List[str]:
        """Suggest next steps based on quick evaluation."""
        next_steps = []
        
        # Based on overall score
        if result.overall_score < 0.6:
            next_steps.append("Consider comprehensive evaluation for detailed analysis")
        
        # Based on category scores
        if "accuracy" in result.category_scores and result.category_scores["accuracy"] < 0.6:
            next_steps.append("Review job parsing and skill extraction accuracy")
        
        if "quality" in result.category_scores and result.category_scores["quality"] < 0.6:
            next_steps.append("Improve resume content quality and formatting")
        
        if "relevance" in result.category_scores and result.category_scores["relevance"] < 0.6:
            next_steps.append("Better align resume content with job requirements")
        
        # Based on confidence
        if result.confidence_score < 0.6:
            next_steps.append("Run additional evaluators to increase confidence")
        
        return next_steps[:2]  # Return top 2 next steps
    
    def _calculate_score_distribution(self, results: List[Dict]) -> Dict[str, int]:
        """Calculate score distribution for batch results."""
        distribution = {"excellent": 0, "good": 0, "fair": 0, "poor": 0}
        
        for result in results:
            score = result["overall_score"]
            if score >= 0.8:
                distribution["excellent"] += 1
            elif score >= 0.6:
                distribution["good"] += 1
            elif score >= 0.4:
                distribution["fair"] += 1
            else:
                distribution["poor"] += 1
        
        return distribution
    
    def _identify_common_issues(self, results: List[Dict]) -> List[str]:
        """Identify common issues across batch results."""
        issue_counts = {}
        
        for result in results:
            for issue in result.get("key_issues", []):
                issue_counts[issue] = issue_counts.get(issue, 0) + 1
        
        # Return most common issues
        common_issues = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)
        return [issue for issue, count in common_issues[:3]]
    
    def _generate_batch_recommendations(self, results: List[Dict]) -> List[str]:
        """Generate recommendations for the entire batch."""
        recommendations = []
        
        if not results:
            return ["No successful evaluations to analyze"]
        
        avg_score = sum(r["overall_score"] for r in results) / len(results)
        
        if avg_score < 0.5:
            recommendations.append("Overall batch performance is low - consider systematic improvements")
        
        # Check if there are consistent patterns
        low_accuracy_count = sum(1 for r in results if any("accuracy" in issue for issue in r.get("key_issues", [])))
        low_quality_count = sum(1 for r in results if any("quality" in issue for issue in r.get("key_issues", [])))
        
        if low_accuracy_count > len(results) * 0.5:
            recommendations.append("Accuracy issues are common - review job parsing logic")
        
        if low_quality_count > len(results) * 0.5:
            recommendations.append("Quality issues are common - review content standards")
        
        return recommendations[:3]
    
    def get_evaluator_info(self) -> Dict[str, str]:
        """Get information about evaluators used in quick suite."""
        return {
            "job_parsing_accuracy": "Evaluates precision and recall of job requirement extraction",
            "match_score": "Analyzes correlation and consistency of resume-job match scoring", 
            "content_quality": "Assesses readability, professionalism, and ATS compatibility"
        }
    
    def get_configuration_summary(self) -> Dict[str, any]:
        """Get summary of quick suite configuration."""
        return {
            "mode": "Quick",
            "evaluators": ["job_parsing_accuracy", "match_score", "content_quality"],
            "parallel_execution": self.config.parallel_execution,
            "max_concurrent": self.config.max_concurrent_evaluators,
            "focus": "Speed and essential metrics",
            "typical_duration": "5-15 seconds per evaluation",
            "best_for": ["Development feedback", "Rapid prototyping", "Initial assessment"]
        }


# Import required for time functions
import time