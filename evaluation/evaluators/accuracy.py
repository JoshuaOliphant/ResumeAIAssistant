# ABOUTME: Accuracy evaluators for parsing and matching functionality
# ABOUTME: Tests job parsing accuracy and match score reliability
"""
Accuracy Evaluators

Evaluators that test the accuracy of parsing and matching functionality
in the resume optimization system.
"""

import re
import time
import difflib
from typing import Any, Dict, List, Set, Tuple, Optional, Union
from .base import BaseEvaluator
from ..test_data.models import TestCase, EvaluationResult


class JobParsingAccuracyEvaluator(BaseEvaluator):
    """Evaluates accuracy of job requirement parsing with precision/recall metrics and fuzzy matching."""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("job_parsing_accuracy", config)
        
        # Fuzzy matching configurations
        self.skill_normalizations = {
            "javascript": ["js", "javascript", "java script", "ecmascript"],
            "react": ["react", "react.js", "reactjs", "react js"],
            "node": ["node", "node.js", "nodejs", "node js"],
            "postgresql": ["postgresql", "postgres", "psql", "postgre sql"],
            "kubernetes": ["kubernetes", "k8s", "kube"],
            "docker": ["docker", "containerization", "containers"],
            "aws": ["aws", "amazon web services", "amazon aws"],
            "git": ["git", "version control", "source control"],
            "python": ["python", "python3", "py"],
            "typescript": ["typescript", "ts", "type script"],
            "mongodb": ["mongodb", "mongo", "mongo db"],
            "redis": ["redis", "cache", "in-memory database"],
            "elasticsearch": ["elasticsearch", "elastic search", "es"],
            "jenkins": ["jenkins", "ci/cd", "continuous integration"],
            "terraform": ["terraform", "iac", "infrastructure as code"],
            "fastapi": ["fastapi", "fast api"],
            "django": ["django", "django framework"],
            "express": ["express", "express.js", "expressjs"],
            "api": ["api", "rest api", "restful", "web api", "api development"],
            "microservices": ["microservices", "micro services", "service architecture"],
            "leadership": ["leadership", "team lead", "team leader", "mentoring", "team management"],
            "devops": ["devops", "dev ops", "operations", "deployment"],
            "cicd": ["ci/cd", "cicd", "continuous integration", "continuous deployment", "automation"],
            "sql": ["sql", "database", "queries", "relational database"],
            "nosql": ["nosql", "no sql", "non-relational", "document database"],
            "cloud": ["cloud", "cloud computing", "cloud services", "cloud platforms"],
            "java": ["java", "java programming", "jvm"],
            "machine learning": ["ml", "machine learning", "ai", "artificial intelligence"],
            "data science": ["data science", "data analysis", "analytics", "data scientist"],
            "frontend": ["frontend", "front-end", "front end", "ui", "user interface"],
            "backend": ["backend", "back-end", "back end", "server-side"],
            "fullstack": ["fullstack", "full-stack", "full stack"],
        }
        
        # Configure all thresholds from config with sensible defaults
        if config:
            self.confidence_thresholds = {
                "required": float(config.get("confidence_threshold_required", 0.9)),
                "preferred": float(config.get("confidence_threshold_preferred", 0.7)),
                "nice_to_have": float(config.get("confidence_threshold_nice_to_have", 0.5))
            }
            self.similarity_threshold = float(config.get("similarity_threshold", 0.8))
            self.confidence_tolerance = float(config.get("confidence_tolerance", 0.2))
            self.pass_threshold = float(config.get("pass_threshold", 0.7))
            self.f1_threshold = float(config.get("f1_threshold", 0.6))
        else:
            # Default thresholds if no config provided
            self.confidence_thresholds = {
                "required": 0.9,
                "preferred": 0.7,
                "nice_to_have": 0.5
            }
            self.similarity_threshold = 0.8
            self.confidence_tolerance = 0.2
            self.pass_threshold = 0.7
            self.f1_threshold = 0.6
    
    async def evaluate(self, test_case: TestCase, actual_output: Any) -> EvaluationResult:
        """
        Evaluate job parsing accuracy with comprehensive metrics.
        
        Args:
            test_case: Test case with expected parsing results
            actual_output: Actual parsing output from parse_job_requirements()
            
        Returns:
            EvaluationResult with precision/recall metrics and detailed error analysis
        """
        start_time = time.time()
        self.validate_inputs(test_case, actual_output)
        
        # Extract expected and actual skill sets
        expected_skills = self._normalize_skills(test_case.expected_skills or [])
        expected_technologies = self._normalize_skills(test_case.expected_technologies or [])
        
        # Parse actual output based on structure
        actual_skills, actual_technologies, confidence_scores = self._extract_actual_data(actual_output)
        
        # Calculate precision and recall metrics
        skill_metrics = self._calculate_precision_recall(expected_skills, actual_skills, "skills")
        tech_metrics = self._calculate_precision_recall(expected_technologies, actual_technologies, "technologies")
        
        # Evaluate confidence score accuracy
        confidence_metrics = self._evaluate_confidence_accuracy(test_case, actual_output, confidence_scores)
        
        # Perform detailed error analysis
        error_analysis = self._analyze_errors(
            expected_skills, actual_skills,
            expected_technologies, actual_technologies,
            test_case, actual_output
        )
        
        # Calculate overall score (weighted average)
        overall_score = self._calculate_overall_score(skill_metrics, tech_metrics, confidence_metrics)
        
        # Create detailed scores dictionary
        detailed_scores = {
            "skill_precision": skill_metrics["precision"],
            "skill_recall": skill_metrics["recall"],
            "skill_f1": skill_metrics["f1_score"],
            "technology_precision": tech_metrics["precision"],
            "technology_recall": tech_metrics["recall"],
            "technology_f1": tech_metrics["f1_score"],
            "confidence_accuracy": confidence_metrics["mean_absolute_error"],
            "confidence_calibration": confidence_metrics["calibration_score"],
            "completeness": (skill_metrics["recall"] + tech_metrics["recall"]) / 2,
            "accuracy": (skill_metrics["precision"] + tech_metrics["precision"]) / 2
        }
        
        # Determine if evaluation passed using configurable thresholds
        passed = (
            overall_score >= self.pass_threshold and
            skill_metrics["f1_score"] >= self.f1_threshold and
            tech_metrics["f1_score"] >= self.f1_threshold
        )
        
        # Generate detailed notes
        notes = self._generate_evaluation_notes(
            skill_metrics, tech_metrics, confidence_metrics, error_analysis, overall_score
        )
        
        execution_time = time.time() - start_time
        
        return self.create_result(
            test_case=test_case,
            overall_score=overall_score,
            detailed_scores=detailed_scores,
            passed=passed,
            notes=notes,
            execution_time=execution_time,
            api_calls_made=1,  # Assuming one API call for parsing
            tokens_used=self._estimate_tokens_used(test_case.job_description, actual_output)
        )
    
    def _normalize_skills(self, skills: List[str]) -> Set[str]:
        """Normalize skill names for consistent comparison."""
        normalized = set()
        
        for skill in skills:
            skill_lower = skill.lower().strip()
            
            # Check against normalizations
            found_match = False
            for normalized_name, variations in self.skill_normalizations.items():
                if skill_lower in variations:
                    normalized.add(normalized_name)
                    found_match = True
                    break
            
            # If no normalization found, add the cleaned skill
            if not found_match:
                # Clean the skill name
                cleaned = re.sub(r'[^\w\s]', '', skill_lower)
                cleaned = re.sub(r'\s+', ' ', cleaned).strip()
                if cleaned:
                    normalized.add(cleaned)
        
        return normalized
    
    def _extract_actual_data(self, actual_output: Any) -> Tuple[Set[str], Set[str], Dict[str, float]]:
        """Extract skills, technologies, and confidence scores from actual output."""
        actual_skills = set()
        actual_technologies = set()
        confidence_scores = {}
        
        if isinstance(actual_output, dict):
            # Handle structured output from parse_job_requirements
            
            # Extract required skills
            for skill_data in actual_output.get("required_skills", []):
                if isinstance(skill_data, dict):
                    skill_name = skill_data.get("skill", "")
                    confidence = skill_data.get("confidence", 1.0)
                    if skill_name:
                        normalized_skills = self._normalize_skills([skill_name])
                        actual_skills.update(normalized_skills)
                        for norm_skill in normalized_skills:
                            confidence_scores[norm_skill] = confidence
                elif isinstance(skill_data, str):
                    normalized_skills = self._normalize_skills([skill_data])
                    actual_skills.update(normalized_skills)
            
            # Extract preferred skills
            for skill_data in actual_output.get("preferred_skills", []):
                if isinstance(skill_data, dict):
                    skill_name = skill_data.get("skill", "")
                    confidence = skill_data.get("confidence", 0.7)
                    if skill_name:
                        normalized_skills = self._normalize_skills([skill_name])
                        actual_skills.update(normalized_skills)
                        for norm_skill in normalized_skills:
                            confidence_scores[norm_skill] = confidence
                elif isinstance(skill_data, str):
                    normalized_skills = self._normalize_skills([skill_data])
                    actual_skills.update(normalized_skills)
            
            # Extract technologies
            technologies = actual_output.get("technologies_mentioned", [])
            if isinstance(technologies, list):
                for tech in technologies:
                    if isinstance(tech, str):
                        normalized_techs = self._normalize_skills([tech])
                        actual_technologies.update(normalized_techs)
        
        elif isinstance(actual_output, (list, tuple)):
            # Handle simple list output
            for item in actual_output:
                if isinstance(item, str):
                    normalized_skills = self._normalize_skills([item])
                    actual_skills.update(normalized_skills)
        
        elif isinstance(actual_output, str):
            # Handle string output - try to extract skills
            # This is a fallback for unstructured output
            self.logger.warning("Using string fallback parsing for actual_output")
            
            # Improved regex patterns for skill extraction
            # Pattern 1: Capitalized words and common tech terms
            capitalized_pattern = r'\b[A-Z][a-zA-Z]+(?:\.[a-zA-Z]+)?(?:\+\+)?\b'
            # Pattern 2: Common lowercase tech terms
            tech_terms_pattern = r'\b(?:python|java|javascript|react|node|docker|kubernetes|aws|git|sql|api|ci/cd|devops)\b'
            # Pattern 3: Acronyms and abbreviations
            acronym_pattern = r'\b[A-Z]{2,}(?:\.[A-Z]+)*\b'
            
            # Extract skills using all patterns
            skills = []
            skills.extend(re.findall(capitalized_pattern, actual_output, re.IGNORECASE))
            skills.extend(re.findall(tech_terms_pattern, actual_output, re.IGNORECASE))
            skills.extend(re.findall(acronym_pattern, actual_output))
            
            # Remove duplicates and normalize
            unique_skills = list(set(skills))
            normalized_skills = self._normalize_skills(unique_skills)
            actual_skills.update(normalized_skills)
            
            self.logger.info(f"String fallback extracted {len(normalized_skills)} skills")
        
        return actual_skills, actual_technologies, confidence_scores
    
    def _calculate_precision_recall(self, expected: Set[str], actual: Set[str], category: str) -> Dict[str, float]:
        """Calculate precision, recall, and F1 score with fuzzy matching."""
        
        # Perform fuzzy matching
        true_positives = set()
        false_positives = set()
        false_negatives = set()
        
        # Find matches using fuzzy matching
        matched_expected = set()
        matched_actual = set()
        
        for expected_item in expected:
            best_match = None
            best_score = 0.0
            
            for actual_item in actual:
                if actual_item in matched_actual:
                    continue
                
                # Calculate similarity score
                similarity = difflib.SequenceMatcher(None, expected_item, actual_item).ratio()
                
                if similarity >= self.similarity_threshold and similarity > best_score:
                    best_match = actual_item
                    best_score = similarity
            
            if best_match:
                true_positives.add(expected_item)
                matched_expected.add(expected_item)
                matched_actual.add(best_match)
        
        # False negatives: expected items not matched
        false_negatives = expected - matched_expected
        
        # False positives: actual items not matched
        false_positives = actual - matched_actual
        
        # Calculate metrics
        tp_count = len(true_positives)
        fp_count = len(false_positives)
        fn_count = len(false_negatives)
        
        precision = tp_count / (tp_count + fp_count) if (tp_count + fp_count) > 0 else 0.0
        recall = tp_count / (tp_count + fn_count) if (tp_count + fn_count) > 0 else 0.0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        return {
            "precision": precision,
            "recall": recall,
            "f1_score": f1_score,
            "true_positives": tp_count,
            "false_positives": fp_count,
            "false_negatives": fn_count,
            "tp_items": true_positives,
            "fp_items": false_positives,
            "fn_items": false_negatives
        }
    
    def _evaluate_confidence_accuracy(self, test_case: TestCase, actual_output: Any, confidence_scores: Dict[str, float]) -> Dict[str, float]:
        """Evaluate accuracy of confidence scores."""
        
        if not confidence_scores:
            return {
                "mean_absolute_error": 1.0,  # Maximum error if no confidence scores
                "calibration_score": 0.0,
                "score_distribution": {}
            }
        
        # Analyze confidence score distribution
        score_bins = {"high": 0, "medium": 0, "low": 0}
        total_scores = len(confidence_scores)
        
        for score in confidence_scores.values():
            if score >= 0.8:
                score_bins["high"] += 1
            elif score >= 0.6:
                score_bins["medium"] += 1
            else:
                score_bins["low"] += 1
        
        # Normalize distribution
        if total_scores > 0:
            score_distribution = {k: v / total_scores for k, v in score_bins.items()}
        else:
            score_distribution = {"high": 0, "medium": 0, "low": 0}
        
        # Calculate expected confidence distribution based on job posting language
        job_description = test_case.job_description.lower()
        required_indicators = ["required", "must", "essential", "mandatory"]
        preferred_indicators = ["preferred", "nice to have", "plus", "bonus"]
        
        required_count = sum(1 for indicator in required_indicators if indicator in job_description)
        preferred_count = sum(1 for indicator in preferred_indicators if indicator in job_description)
        
        # Expected high confidence ratio (rough heuristic)
        expected_high_confidence = min(0.7, (required_count * 0.2) + 0.3)
        
        # Calculate calibration score (how well confidence distribution matches expectations)
        actual_high_confidence = score_distribution.get("high", 0)
        calibration_score = 1.0 - abs(expected_high_confidence - actual_high_confidence)
        
        # For MAE, we don't have ground truth confidence scores, so we use a heuristic
        # based on whether skills are in expected lists
        expected_skills = set(test_case.expected_skills or [])
        mae_sum = 0.0
        mae_count = 0
        
        for skill, confidence in confidence_scores.items():
            # Heuristic: skills in expected list should have higher confidence
            if skill in expected_skills:
                expected_confidence = 0.9  # High confidence for expected skills
            else:
                expected_confidence = 0.5  # Medium confidence for unexpected skills
            
            mae_sum += abs(confidence - expected_confidence)
            mae_count += 1
        
        mean_absolute_error = mae_sum / mae_count if mae_count > 0 else 0.0
        
        return {
            "mean_absolute_error": mean_absolute_error,
            "calibration_score": calibration_score,
            "score_distribution": score_distribution,
            "expected_high_confidence": expected_high_confidence,
            "actual_high_confidence": actual_high_confidence
        }
    
    def _analyze_errors(self, expected_skills: Set[str], actual_skills: Set[str],
                       expected_technologies: Set[str], actual_technologies: Set[str],
                       test_case: TestCase, actual_output: Any) -> Dict[str, Any]:
        """Perform detailed error analysis and identify failure modes."""
        
        # Categorize missing skills by importance
        missing_critical_skills = []
        missing_preferred_skills = []
        
        # Analyze job description for importance indicators
        job_desc = test_case.job_description.lower()
        
        for skill in expected_skills - actual_skills:
            skill_context = self._find_skill_context(skill, job_desc)
            if any(indicator in skill_context for indicator in ["required", "must", "essential"]):
                missing_critical_skills.append(skill)
            else:
                missing_preferred_skills.append(skill)
        
        # Categorize false positive skills
        false_positive_skills = actual_skills - expected_skills
        
        # Analyze failure modes
        failure_modes = []
        
        if missing_critical_skills:
            failure_modes.append({
                "type": "missing_critical_skills",
                "severity": "high",
                "description": f"Failed to extract {len(missing_critical_skills)} critical skills",
                "details": missing_critical_skills
            })
        
        if len(false_positive_skills) > len(actual_skills) * 0.3:
            failure_modes.append({
                "type": "excessive_false_positives",
                "severity": "medium",
                "description": f"Too many false positive skills detected: {len(false_positive_skills)}",
                "details": list(false_positive_skills)
            })
        
        if len(actual_skills) < len(expected_skills) * 0.5:
            failure_modes.append({
                "type": "low_recall",
                "severity": "high",
                "description": "Very low skill extraction recall",
                "details": f"Extracted {len(actual_skills)} out of {len(expected_skills)} expected skills"
            })
        
        # Check for technology extraction issues
        missing_technologies = expected_technologies - actual_technologies
        if len(missing_technologies) > len(expected_technologies) * 0.4:
            failure_modes.append({
                "type": "poor_technology_extraction",
                "severity": "medium",
                "description": "Poor technology identification",
                "details": list(missing_technologies)
            })
        
        return {
            "missing_critical_skills": missing_critical_skills,
            "missing_preferred_skills": missing_preferred_skills,
            "false_positive_skills": list(false_positive_skills),
            "missing_technologies": list(missing_technologies),
            "failure_modes": failure_modes,
            "error_summary": {
                "total_errors": len(missing_critical_skills) + len(false_positive_skills),
                "critical_errors": len(missing_critical_skills),
                "precision_errors": len(false_positive_skills),
                "recall_errors": len(missing_critical_skills) + len(missing_preferred_skills)
            }
        }
    
    def _find_skill_context(self, skill: str, job_description: str) -> str:
        """Find the context around a skill mention in job description."""
        # Improved sentence boundary detection using regex
        # Handles periods, exclamation marks, question marks, and newlines
        import re
        
        # Split on sentence boundaries but keep the delimiters
        sentence_pattern = r'(?<=[.!?\n])\s+(?=[A-Z])|(?<=[.!?])\s*\n|\n\s*[-•]'
        sentences = re.split(sentence_pattern, job_description)
        
        skill_lower = skill.lower()
        for sentence in sentences:
            if skill_lower in sentence.lower():
                # Clean up the sentence
                cleaned = sentence.strip()
                # Ensure we have a complete sentence
                if len(cleaned) > 10:  # Minimum sentence length
                    return cleaned
        
        # Fallback: look for the skill in bullet points or shorter fragments
        lines = job_description.split('\n')
        for line in lines:
            if skill_lower in line.lower() and len(line.strip()) > 5:
                return line.strip()
        
        return ""
    
    def _calculate_overall_score(self, skill_metrics: Dict[str, float], 
                               tech_metrics: Dict[str, float], 
                               confidence_metrics: Dict[str, float]) -> float:
        """Calculate weighted overall score."""
        
        # Weights for different components
        skill_weight = 0.4
        tech_weight = 0.3
        confidence_weight = 0.3
        
        # Skill component (F1 score)
        skill_score = skill_metrics["f1_score"]
        
        # Technology component (F1 score)
        tech_score = tech_metrics["f1_score"]
        
        # Confidence component (inverted MAE + calibration)
        confidence_score = (
            (1.0 - confidence_metrics["mean_absolute_error"]) * 0.6 +
            confidence_metrics["calibration_score"] * 0.4
        )
        
        overall_score = (
            skill_score * skill_weight +
            tech_score * tech_weight +
            confidence_score * confidence_weight
        )
        
        return min(1.0, max(0.0, overall_score))
    
    def _generate_evaluation_notes(self, skill_metrics: Dict[str, float], 
                                 tech_metrics: Dict[str, float],
                                 confidence_metrics: Dict[str, float],
                                 error_analysis: Dict[str, Any],
                                 overall_score: float) -> str:
        """Generate detailed evaluation notes."""
        
        notes = []
        
        # Overall performance
        if overall_score >= 0.9:
            notes.append("🟢 Excellent job parsing performance")
        elif overall_score >= 0.7:
            notes.append("🟡 Good job parsing performance with room for improvement")
        else:
            notes.append("🔴 Poor job parsing performance requiring attention")
        
        # Skill extraction performance
        notes.append(f"Skill Extraction - Precision: {skill_metrics['precision']:.2f}, Recall: {skill_metrics['recall']:.2f}, F1: {skill_metrics['f1_score']:.2f}")
        
        # Technology extraction performance
        notes.append(f"Technology Extraction - Precision: {tech_metrics['precision']:.2f}, Recall: {tech_metrics['recall']:.2f}, F1: {tech_metrics['f1_score']:.2f}")
        
        # Confidence analysis
        notes.append(f"Confidence Accuracy - MAE: {confidence_metrics['mean_absolute_error']:.2f}, Calibration: {confidence_metrics['calibration_score']:.2f}")
        
        # Error analysis
        error_summary = error_analysis["error_summary"]
        if error_summary["critical_errors"] > 0:
            notes.append(f"⚠️ {error_summary['critical_errors']} critical skills missed")
        
        if error_summary["precision_errors"] > 3:
            notes.append(f"⚠️ High false positive rate: {error_summary['precision_errors']} incorrect skills")
        
        # Failure modes
        for failure in error_analysis["failure_modes"]:
            severity_emoji = "🔴" if failure["severity"] == "high" else "🟡"
            notes.append(f"{severity_emoji} {failure['description']}")
        
        # Recommendations
        if skill_metrics["recall"] < 0.7:
            notes.append("💡 Recommendation: Improve skill extraction recall by enhancing parsing prompts")
        
        if skill_metrics["precision"] < 0.7:
            notes.append("💡 Recommendation: Reduce false positives by adding skill validation logic")
        
        if confidence_metrics["calibration_score"] < 0.6:
            notes.append("💡 Recommendation: Improve confidence calibration based on job posting language")
        
        return " | ".join(notes)
    
    def _estimate_tokens_used(self, job_description: str, actual_output: Any) -> int:
        """Estimate tokens used based on input and output length."""
        # More accurate estimation: 1 token ≈ 3.3 characters for modern tokenizers
        # This is closer to GPT-3/4 and Claude tokenization patterns
        input_tokens = int(len(job_description) / 3.3)
        output_tokens = int(len(str(actual_output)) / 3.3)
        
        # Add a buffer for system prompt and formatting tokens
        system_overhead = 50  # Approximate tokens for system messages
        
        return input_tokens + output_tokens + system_overhead
    
    def get_description(self) -> str:
        """Get description of this evaluator."""
        return ("Evaluates job parsing accuracy with precision/recall metrics, fuzzy skill matching, "
                "confidence score validation, and detailed failure mode analysis")


class MatchScoreEvaluator(BaseEvaluator):
    """Evaluates reliability of resume-job match scoring."""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("match_score", config)
    
    async def evaluate(self, test_case: TestCase, actual_output: Any) -> EvaluationResult:
        """
        Evaluate match score reliability.
        
        Args:
            test_case: Test case with expected match score
            actual_output: Actual match evaluation output
            
        Returns:
            EvaluationResult with correlation and consistency metrics
        """
        self.validate_inputs(test_case, actual_output)
        
        # Placeholder implementation - will be implemented in Issue #111
        overall_score = 0.75  # Placeholder score
        detailed_scores = {
            "score_correlation": 0.80,
            "consistency": 0.70,
            "transferable_skills": 0.75
        }
        
        return self.create_result(
            test_case=test_case,
            overall_score=overall_score,
            detailed_scores=detailed_scores,
            passed=overall_score >= 0.7,
            notes="Placeholder implementation - full functionality in Issue #111"
        )
    
    def get_description(self) -> str:
        """Get description of this evaluator."""
        return "Evaluates reliability and consistency of resume-job match scoring"