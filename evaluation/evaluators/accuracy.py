# ABOUTME: Accuracy evaluators for parsing and matching functionality
# ABOUTME: Tests job parsing accuracy and match score reliability
"""
Accuracy Evaluators

Evaluators that test the accuracy of parsing and matching functionality
in the resume optimization system.
"""

from typing import Any, Dict, List
from .base import BaseEvaluator
from ..test_data.models import TestCase, EvaluationResult


class JobParsingAccuracyEvaluator(BaseEvaluator):
    """Evaluates accuracy of job requirement parsing."""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("job_parsing_accuracy", config)
    
    async def evaluate(self, test_case: TestCase, actual_output: Any) -> EvaluationResult:
        """
        Evaluate job parsing accuracy.
        
        Args:
            test_case: Test case with expected parsing results
            actual_output: Actual parsing output from parse_job_requirements()
            
        Returns:
            EvaluationResult with accuracy metrics
        """
        self.validate_inputs(test_case, actual_output)
        
        # Placeholder implementation - will be implemented in Issue #110
        overall_score = 0.8  # Placeholder score
        detailed_scores = {
            "skill_extraction_accuracy": 0.85,
            "confidence_score_accuracy": 0.75,
            "technology_identification": 0.80
        }
        
        return self.create_result(
            test_case=test_case,
            overall_score=overall_score,
            detailed_scores=detailed_scores,
            passed=overall_score >= 0.7,
            notes="Placeholder implementation - full functionality in Issue #110"
        )
    
    def get_description(self) -> str:
        """Get description of this evaluator."""
        return "Evaluates accuracy of job requirement parsing including skill extraction and confidence scoring"


class MatchScoreEvaluatorConfig:
    """Configuration for MatchScoreEvaluator."""
    
    # Component weights for overall score calculation
    COMPONENT_WEIGHTS = {
        "correlation_analysis": 0.3,
        "consistency_analysis": 0.2,
        "transferable_skills": 0.2,
        "experience_alignment": 0.15,
        "bias_analysis": 0.1,
        "distribution_analysis": 0.05
    }
    
    # Score boundaries
    MIN_MATCH_SCORE = 0.0
    MAX_MATCH_SCORE = 100.0
    
    # Consistency thresholds
    MAX_SCORE_DIFFERENCE = 10.0
    CONSISTENCY_THRESHOLD = 0.85
    
    # Correlation thresholds
    STRONG_CORRELATION_THRESHOLD = 0.7
    MODERATE_CORRELATION_THRESHOLD = 0.5
    
    # Bias detection thresholds
    BIAS_CLUSTERING_THRESHOLD = 0.3
    BIAS_EXTREME_THRESHOLD = 0.15
    
    # Statistical parameters
    MIN_SAMPLES_FOR_CORRELATION = 3
    MIN_SAMPLES_FOR_STATS = 2


class MatchScoreEvaluator(BaseEvaluator):
    """Evaluates reliability of resume-job match scoring."""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("match_score", config)
        self.evaluator_config = MatchScoreEvaluatorConfig()
        # Initialize storage for consistency testing
        self.consistency_cache = {}
    
    async def evaluate(self, test_case: TestCase, actual_output: Any) -> EvaluationResult:
        """
        Evaluate match score reliability.
        
        Args:
            test_case: Test case with expected match score
            actual_output: Actual match evaluation output
            
        Returns:
            EvaluationResult with correlation and consistency metrics
        """
        import time
        start_time = time.time()
        
        try:
            self.validate_inputs(test_case, actual_output)
            
            # Extract match score from actual output
            actual_score = self._extract_match_score(actual_output)
            expected_score = test_case.expected_match_score
            
            if actual_score is None or expected_score is None:
                return self._create_error_result(
                    test_case, 
                    "Missing match score data",
                    execution_time=time.time() - start_time
                )
            
            # Run all analyses
            analyses = {
                "correlation_analysis": await self._analyze_correlation(test_case, actual_score, expected_score),
                "consistency_analysis": await self._analyze_consistency(test_case, actual_score),
                "transferable_skills": await self._analyze_transferable_skills(test_case),
                "experience_alignment": await self._analyze_experience_alignment(test_case),
                "bias_analysis": await self._analyze_bias(test_case, actual_score),
                "distribution_analysis": await self._analyze_distribution(test_case, actual_score)
            }
            
            # Calculate overall score
            overall_score = self._calculate_weighted_score(analyses)
            
            # Compile detailed scores
            detailed_scores = {name: analysis["score"] for name, analysis in analyses.items()}
            
            # Determine if passed
            passed = overall_score >= self.config.get("min_score", 0.7)
            
            # Generate notes
            notes = self._generate_notes(analyses, actual_score, expected_score)
            
            return self.create_result(
                test_case=test_case,
                overall_score=overall_score,
                detailed_scores=detailed_scores,
                passed=passed,
                notes=notes,
                execution_time=time.time() - start_time,
                analyses_details=analyses
            )
            
        except Exception as e:
            self.logger.error(f"Error in MatchScoreEvaluator: {str(e)}")
            return self._create_error_result(
                test_case,
                f"Evaluation failed: {str(e)}",
                execution_time=time.time() - start_time
            )
    
    def _extract_match_score(self, actual_output: Any) -> float:
        """Extract match score from actual output."""
        if isinstance(actual_output, (int, float)):
            return float(actual_output)
        elif isinstance(actual_output, dict):
            return actual_output.get('match_score', actual_output.get('score'))
        elif hasattr(actual_output, 'match_score'):
            return actual_output.match_score
        return None
    
    async def _analyze_correlation(self, test_case: TestCase, actual_score: float, expected_score: float) -> Dict[str, Any]:
        """Analyze correlation between actual and expected scores."""
        score_diff = abs(actual_score - expected_score)
        max_diff = self.evaluator_config.MAX_SCORE_DIFFERENCE
        
        # Calculate correlation score based on difference
        if score_diff <= max_diff * 0.5:
            correlation_score = 1.0
            assessment = "Excellent correlation"
        elif score_diff <= max_diff:
            correlation_score = 1.0 - (score_diff - max_diff * 0.5) / (max_diff * 0.5) * 0.3
            assessment = "Good correlation"
        elif score_diff <= max_diff * 2:
            correlation_score = 0.7 - (score_diff - max_diff) / max_diff * 0.4
            assessment = "Moderate correlation"
        else:
            correlation_score = max(0.0, 0.3 - (score_diff - max_diff * 2) / max_diff * 0.3)
            assessment = "Poor correlation"
        
        return {
            "score": correlation_score,
            "actual_score": actual_score,
            "expected_score": expected_score,
            "score_difference": score_diff,
            "assessment": assessment
        }
    
    async def _analyze_consistency(self, test_case: TestCase, actual_score: float) -> Dict[str, Any]:
        """Analyze consistency by tracking multiple evaluations of same input."""
        cache_key = f"{test_case.resume_content[:100]}_{test_case.job_description[:100]}"
        
        if cache_key not in self.consistency_cache:
            self.consistency_cache[cache_key] = []
        
        self.consistency_cache[cache_key].append(actual_score)
        scores = self.consistency_cache[cache_key]
        
        if len(scores) < 2:
            return {
                "score": 1.0,
                "evaluations": len(scores),
                "assessment": "Insufficient data for consistency analysis"
            }
        
        # Calculate statistics with fallback for missing libraries
        try:
            import numpy as np
            std_dev = np.std(scores)
            mean_score = np.mean(scores)
            cv = std_dev / mean_score if mean_score > 0 else 0
        except ImportError:
            # Fallback implementation
            mean_score = sum(scores) / len(scores)
            variance = sum((x - mean_score) ** 2 for x in scores) / len(scores)
            std_dev = variance ** 0.5
            cv = std_dev / mean_score if mean_score > 0 else 0
        
        # Score based on coefficient of variation
        if cv < 0.05:
            consistency_score = 1.0
            assessment = "Highly consistent"
        elif cv < 0.10:
            consistency_score = 0.9
            assessment = "Good consistency"
        elif cv < 0.15:
            consistency_score = 0.7
            assessment = "Moderate consistency"
        else:
            consistency_score = max(0.0, 0.5 - (cv - 0.15) * 2)
            assessment = "Poor consistency"
        
        return {
            "score": consistency_score,
            "evaluations": len(scores),
            "std_deviation": std_dev,
            "coefficient_of_variation": cv,
            "scores": scores,
            "assessment": assessment
        }
    
    async def _analyze_transferable_skills(self, test_case: TestCase) -> Dict[str, Any]:
        """Analyze recognition of transferable skills."""
        # Define transferable skill mappings
        skill_mappings = {
            'aws': ['cloud', 'azure', 'gcp'],
            'azure': ['cloud', 'aws', 'gcp'],
            'react': ['frontend', 'angular', 'vue'],
            'angular': ['frontend', 'react', 'vue'],
            'python': ['programming', 'java', 'javascript'],
            'docker': ['containerization', 'kubernetes'],
            'sql': ['database', 'postgresql', 'mysql']
        }
        
        # Extract skills from resume and job description
        resume_skills = self._extract_skills(test_case.resume_content)
        job_skills = self._extract_skills(test_case.job_description)
        
        # Find transferable matches
        transferable_matches = 0
        total_transferable = 0
        matched_skills = []
        
        for job_skill in job_skills:
            skill_lower = job_skill.lower()
            if skill_lower in skill_mappings:
                total_transferable += 1
                for resume_skill in resume_skills:
                    if resume_skill.lower() in skill_mappings.get(skill_lower, []):
                        transferable_matches += 1
                        matched_skills.append(f"{resume_skill} → {job_skill}")
                        break
        
        if total_transferable == 0:
            score = 1.0
            assessment = "No transferable skills to evaluate"
        else:
            score = transferable_matches / total_transferable
            if score > 0.8:
                assessment = "Excellent transferable skill recognition"
            elif score > 0.6:
                assessment = "Good transferable skill recognition"
            elif score > 0.4:
                assessment = "Moderate transferable skill recognition"
            else:
                assessment = "Poor transferable skill recognition"
        
        return {
            "score": score,
            "transferable_matches": transferable_matches,
            "total_transferable": total_transferable,
            "matched_skills": matched_skills,
            "assessment": assessment
        }
    
    async def _analyze_experience_alignment(self, test_case: TestCase) -> Dict[str, Any]:
        """Analyze alignment of experience levels."""
        # Extract experience indicators
        resume_experience = self._extract_experience_level(test_case.resume_content)
        job_experience = self._extract_experience_level(test_case.job_description)
        
        # Map to numeric levels
        level_map = {
            'entry': 1, 'junior': 2, 'mid': 3, 'senior': 4, 
            'lead': 5, 'principal': 6, 'staff': 6, 'architect': 6
        }
        
        resume_level = level_map.get(resume_experience, 3)
        job_level = level_map.get(job_experience, 3)
        
        # Calculate alignment score
        level_diff = abs(resume_level - job_level)
        
        if level_diff == 0:
            score = 1.0
            assessment = "Perfect experience alignment"
        elif level_diff == 1:
            score = 0.8
            assessment = "Good experience alignment"
        elif level_diff == 2:
            score = 0.6
            assessment = "Moderate experience alignment"
        else:
            score = max(0.0, 0.4 - (level_diff - 2) * 0.2)
            assessment = "Poor experience alignment"
        
        return {
            "score": score,
            "resume_level": resume_experience,
            "job_level": job_experience,
            "level_difference": level_diff,
            "assessment": assessment
        }
    
    async def _analyze_bias(self, test_case: TestCase, actual_score: float) -> Dict[str, Any]:
        """Analyze potential biases in scoring."""
        # Check for score clustering (bias towards certain ranges)
        score_ranges = {
            'very_low': (0, 20),
            'low': (20, 40),
            'medium': (40, 60),
            'high': (60, 80),
            'very_high': (80, 100)
        }
        
        # Determine which range the score falls into
        score_range = None
        for range_name, (min_val, max_val) in score_ranges.items():
            if min_val <= actual_score <= max_val:
                score_range = range_name
                break
        
        # Check if score is at extreme ends
        is_extreme = actual_score < 20 or actual_score > 80
        
        # Simple bias detection
        bias_indicators = []
        bias_score = 1.0
        
        if is_extreme:
            bias_indicators.append("Score at extreme range")
            bias_score -= 0.2
        
        if actual_score % 10 == 0:
            bias_indicators.append("Round number bias")
            bias_score -= 0.1
        
        if actual_score in [25, 50, 75]:
            bias_indicators.append("Quarter-point bias")
            bias_score -= 0.1
        
        assessment = "No significant bias detected" if bias_score > 0.8 else "Potential bias detected"
        
        return {
            "score": max(0.0, bias_score),
            "score_range": score_range,
            "is_extreme": is_extreme,
            "bias_indicators": bias_indicators,
            "assessment": assessment
        }
    
    async def _analyze_distribution(self, test_case: TestCase, actual_score: float) -> Dict[str, Any]:
        """Analyze score distribution patterns."""
        # Simple distribution analysis based on expected patterns
        # Normal distribution should have most scores in 40-70 range
        
        if 40 <= actual_score <= 70:
            distribution_score = 1.0
            assessment = "Score within normal distribution"
        elif 30 <= actual_score <= 80:
            distribution_score = 0.8
            assessment = "Score in extended normal range"
        elif 20 <= actual_score <= 90:
            distribution_score = 0.6
            assessment = "Score in outer distribution"
        else:
            distribution_score = 0.4
            assessment = "Score at distribution extreme"
        
        return {
            "score": distribution_score,
            "actual_score": actual_score,
            "assessment": assessment,
            "percentile_estimate": self._estimate_percentile(actual_score)
        }
    
    def _extract_skills(self, text: str) -> List[str]:
        """Extract skills from text using regex for performance."""
        import re
        
        # Common technical skills pattern
        skill_patterns = [
            r'\b(?:python|java|javascript|typescript|c\+\+|c#|ruby|go|rust|swift|kotlin)\b',
            r'\b(?:react|angular|vue|django|flask|spring|nodejs|express)\b',
            r'\b(?:aws|azure|gcp|docker|kubernetes|jenkins|terraform)\b',
            r'\b(?:sql|postgresql|mysql|mongodb|redis|elasticsearch)\b',
            r'\b(?:git|agile|scrum|ci/cd|devops|microservices)\b'
        ]
        
        skills = []
        text_lower = text.lower()
        
        for pattern in skill_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            skills.extend(matches)
        
        return list(set(skills))  # Remove duplicates
    
    def _extract_experience_level(self, text: str) -> str:
        """Extract experience level from text."""
        import re
        
        text_lower = text.lower()
        
        # Check for experience level keywords
        if re.search(r'\b(?:senior|sr\.?|lead|principal|staff|architect)\b', text_lower):
            if 'principal' in text_lower or 'staff' in text_lower or 'architect' in text_lower:
                return 'principal'
            elif 'lead' in text_lower:
                return 'lead'
            else:
                return 'senior'
        elif re.search(r'\b(?:junior|jr\.?|entry.?level|graduate)\b', text_lower):
            return 'junior'
        elif re.search(r'\b(?:mid.?level|intermediate)\b', text_lower):
            return 'mid'
        
        # Check years of experience
        years_match = re.search(r'(\d+)\+?\s*years?', text_lower)
        if years_match:
            years = int(years_match.group(1))
            if years >= 7:
                return 'senior'
            elif years >= 3:
                return 'mid'
            else:
                return 'junior'
        
        return 'mid'  # Default
    
    def _calculate_weighted_score(self, analyses: Dict[str, Dict[str, Any]]) -> float:
        """Calculate weighted overall score from component analyses."""
        total_score = 0.0
        
        for component, weight in self.evaluator_config.COMPONENT_WEIGHTS.items():
            if component in analyses:
                total_score += analyses[component]["score"] * weight
        
        return min(1.0, max(0.0, total_score))
    
    def _estimate_percentile(self, score: float) -> float:
        """Estimate percentile based on assumed normal distribution."""
        # Simple percentile estimation
        if score >= 90:
            return 95.0
        elif score >= 80:
            return 85.0
        elif score >= 70:
            return 75.0
        elif score >= 60:
            return 60.0
        elif score >= 50:
            return 50.0
        elif score >= 40:
            return 40.0
        elif score >= 30:
            return 25.0
        elif score >= 20:
            return 15.0
        else:
            return 5.0
    
    def _generate_notes(self, analyses: Dict[str, Dict[str, Any]], actual_score: float, expected_score: float) -> str:
        """Generate comprehensive evaluation notes."""
        notes = []
        notes.append(f"Match Score Evaluation: Actual={actual_score:.1f}, Expected={expected_score:.1f}")
        notes.append("\nComponent Analysis:")
        
        for component, analysis in analyses.items():
            component_name = component.replace('_', ' ').title()
            score_pct = analysis['score'] * 100
            notes.append(f"- {component_name}: {score_pct:.0f}% - {analysis['assessment']}")
        
        # Add specific insights
        if analyses['consistency_analysis']['evaluations'] > 1:
            notes.append(f"\nConsistency: Evaluated {analyses['consistency_analysis']['evaluations']} times")
        
        if analyses['transferable_skills']['matched_skills']:
            notes.append(f"\nTransferable Skills Found: {', '.join(analyses['transferable_skills']['matched_skills'][:3])}")
        
        if analyses['bias_analysis']['bias_indicators']:
            notes.append(f"\nBias Indicators: {', '.join(analyses['bias_analysis']['bias_indicators'])}")
        
        return "\n".join(notes)
    
    def _create_error_result(self, test_case: TestCase, error_message: str, execution_time: float) -> EvaluationResult:
        """Create an error result."""
        return self.create_result(
            test_case=test_case,
            overall_score=0.0,
            detailed_scores={},
            passed=False,
            error_message=error_message,
            execution_time=execution_time
        )
    
    def get_description(self) -> str:
        """Get description of this evaluator."""
        return ("Evaluates reliability and consistency of resume-job match scoring through "
                "correlation analysis, consistency testing, transferable skills recognition, "
                "experience alignment, bias detection, and distribution analysis")