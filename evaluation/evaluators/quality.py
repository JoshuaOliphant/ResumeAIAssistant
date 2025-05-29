# ABOUTME: Quality evaluators for truthfulness, content quality, and relevance
# ABOUTME: Tests optimization quality and maintains professional standards
"""
Quality Evaluators

Evaluators that test the quality aspects of resume optimization including
truthfulness verification, content quality, and relevance impact.
"""

from typing import Any, Dict
from .base import BaseEvaluator
from ..test_data.models import TestCase, EvaluationResult


class TruthfulnessEvaluator(BaseEvaluator):
    """Evaluates truthfulness of resume optimizations to prevent fabrication."""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("truthfulness", config)
        self._setup_nlp_models()
    
    def _setup_nlp_models(self):
        """Initialize NLP models and similarity tools."""
        try:
            import spacy
            import nltk
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
            
            # Try to load spacy model, fallback to basic if not available
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except OSError:
                self.logger.warning("spaCy en_core_web_sm model not found, using basic tokenization")
                self.nlp = None
            
            self.vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2))
            
            # Download NLTK data if needed
            try:
                nltk.data.find('tokenizers/punkt')
            except LookupError:
                nltk.download('punkt', quiet=True)
                
        except ImportError as e:
            self.logger.error(f"Failed to import required NLP libraries: {e}")
            self.nlp = None
            self.vectorizer = None
    
    async def evaluate(self, test_case: TestCase, actual_output: Any) -> EvaluationResult:
        """
        Evaluate truthfulness of optimizations by detecting fabrications.
        
        Args:
            test_case: Test case with original and optimized content
            actual_output: Dict containing 'original_content' and 'optimized_content'
            
        Returns:
            EvaluationResult with truthfulness metrics and violation details
        """
        import time
        start_time = time.time()
        
        self.validate_inputs(test_case, actual_output)
        
        # Extract content from actual_output
        if isinstance(actual_output, dict):
            original_content = actual_output.get('original_content', test_case.resume_content)
            optimized_content = actual_output.get('optimized_content', '')
        else:
            original_content = test_case.resume_content
            optimized_content = str(actual_output)
        
        if not optimized_content:
            return self.create_result(
                test_case=test_case,
                overall_score=0.0,
                detailed_scores={},
                passed=False,
                notes="No optimized content provided for evaluation",
                execution_time=time.time() - start_time
            )
        
        # Perform truthfulness analysis
        analysis_results = self._analyze_truthfulness(original_content, optimized_content)
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(analysis_results)
        
        # Create detailed scores
        detailed_scores = {
            "content_similarity": analysis_results["content_similarity"],
            "entity_consistency": analysis_results["entity_consistency"], 
            "numerical_integrity": analysis_results["numerical_integrity"],
            "skill_authenticity": analysis_results["skill_authenticity"],
            "fabrication_risk": 1.0 - analysis_results["fabrication_confidence"]
        }
        
        # Determine if evaluation passed
        passed = overall_score >= self.config.get("min_truthfulness_score", 0.7)
        
        # Generate detailed notes
        notes = self._generate_evaluation_notes(analysis_results)
        
        execution_time = time.time() - start_time
        
        return self.create_result(
            test_case=test_case,
            overall_score=overall_score,
            detailed_scores=detailed_scores,
            passed=passed,
            notes=notes,
            execution_time=execution_time,
            violations=analysis_results["violations"],
            change_summary=analysis_results["change_summary"]
        )
    
    def _analyze_truthfulness(self, original: str, optimized: str) -> Dict[str, Any]:
        """Perform comprehensive truthfulness analysis."""
        results = {
            "violations": [],
            "change_summary": {},
            "content_similarity": 0.0,
            "entity_consistency": 0.0,
            "numerical_integrity": 0.0,
            "skill_authenticity": 0.0,
            "fabrication_confidence": 0.0
        }
        
        # 1. Content similarity analysis
        results["content_similarity"] = self._calculate_content_similarity(original, optimized)
        
        # 2. Entity consistency check
        entity_analysis = self._analyze_entity_consistency(original, optimized)
        results["entity_consistency"] = entity_analysis["consistency_score"]
        results["violations"].extend(entity_analysis["violations"])
        
        # 3. Numerical integrity check
        numerical_analysis = self._analyze_numerical_integrity(original, optimized)
        results["numerical_integrity"] = numerical_analysis["integrity_score"]
        results["violations"].extend(numerical_analysis["violations"])
        
        # 4. Skill authenticity check
        skill_analysis = self._analyze_skill_authenticity(original, optimized)
        results["skill_authenticity"] = skill_analysis["authenticity_score"]
        results["violations"].extend(skill_analysis["violations"])
        
        # 5. Generate change summary
        results["change_summary"] = self._generate_change_summary(original, optimized)
        
        # 6. Calculate fabrication confidence
        results["fabrication_confidence"] = self._calculate_fabrication_confidence(results)
        
        return results
    
    def _calculate_content_similarity(self, original: str, optimized: str) -> float:
        """Calculate semantic similarity between original and optimized content."""
        if not self.vectorizer:
            # Fallback to basic character-level similarity
            import difflib
            return difflib.SequenceMatcher(None, original.lower(), optimized.lower()).ratio()
        
        try:
            # Use TF-IDF cosine similarity
            from sklearn.metrics.pairwise import cosine_similarity
            texts = [original, optimized]
            tfidf_matrix = self.vectorizer.fit_transform(texts)
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            return float(similarity)
        except Exception as e:
            self.logger.error(f"Error calculating content similarity: {e}")
            return 0.0
    
    def _analyze_entity_consistency(self, original: str, optimized: str) -> Dict[str, Any]:
        """Analyze consistency of named entities between original and optimized content."""
        result = {"consistency_score": 1.0, "violations": []}
        
        if self.nlp:
            try:
                orig_doc = self.nlp(original)
                opt_doc = self.nlp(optimized)
                
                # Extract entities
                orig_entities = {ent.text.lower(): ent.label_ for ent in orig_doc.ents}
                opt_entities = {ent.text.lower(): ent.label_ for ent in opt_doc.ents}
                
                # Check for new organizations/people that weren't in original
                new_orgs = set()
                new_people = set()
                
                for entity, label in opt_entities.items():
                    if entity not in orig_entities:
                        if label in ["ORG", "COMPANY"]:
                            new_orgs.add(entity)
                        elif label in ["PERSON", "PER"]:
                            new_people.add(entity)
                
                # Flag potential violations
                if new_orgs:
                    result["violations"].append({
                        "type": "new_organizations",
                        "confidence": 0.8,
                        "details": f"New organizations found: {', '.join(new_orgs)}",
                        "entities": list(new_orgs)
                    })
                
                if new_people:
                    result["violations"].append({
                        "type": "new_people",
                        "confidence": 0.9,
                        "details": f"New people mentioned: {', '.join(new_people)}",
                        "entities": list(new_people)
                    })
                
                # Calculate consistency score
                if new_orgs or new_people:
                    penalty = min(0.5, (len(new_orgs) + len(new_people)) * 0.1)
                    result["consistency_score"] = max(0.0, 1.0 - penalty)
                
            except Exception as e:
                self.logger.error(f"Error in entity analysis: {e}")
        
        return result
    
    def _analyze_numerical_integrity(self, original: str, optimized: str) -> Dict[str, Any]:
        """Detect inflated or fabricated numerical metrics."""
        import re
        
        result = {"integrity_score": 1.0, "violations": []}
        
        # Extract numbers from both texts
        number_pattern = r'\b\d+(?:\.\d+)?(?:%|\s*percent|k|K|M|million|billion)?\b'
        
        orig_numbers = re.findall(number_pattern, original, re.IGNORECASE)
        opt_numbers = re.findall(number_pattern, optimized, re.IGNORECASE)
        
        # Convert to normalized values for comparison
        orig_values = [self._normalize_number(num) for num in orig_numbers]
        opt_values = [self._normalize_number(num) for num in opt_numbers]
        
        # Look for suspicious inflation
        inflated_values = []
        for opt_val in opt_values:
            if opt_val is not None:
                # Check if this value is significantly higher than any original value
                max_orig = max(orig_values) if orig_values and any(v is not None for v in orig_values) else 0
                if max_orig > 0 and opt_val > max_orig * 2:  # More than 2x increase
                    inflated_values.append(opt_val)
        
        if inflated_values:
            result["violations"].append({
                "type": "numerical_inflation", 
                "confidence": 0.7,
                "details": f"Potentially inflated metrics found: {inflated_values}",
                "values": inflated_values
            })
            result["integrity_score"] = max(0.0, 1.0 - len(inflated_values) * 0.2)
        
        return result
    
    def _normalize_number(self, num_str: str) -> float:
        """Convert number string to normalized float value."""
        try:
            # Remove common suffixes and convert
            clean_num = num_str.lower().replace('%', '').replace('percent', '').replace(',', '')
            
            multiplier = 1
            if 'k' in clean_num:
                multiplier = 1000
                clean_num = clean_num.replace('k', '')
            elif 'm' in clean_num or 'million' in clean_num:
                multiplier = 1000000
                clean_num = clean_num.replace('m', '').replace('illion', '')
            elif 'billion' in clean_num:
                multiplier = 1000000000
                clean_num = clean_num.replace('billion', '')
            
            return float(clean_num.strip()) * multiplier
        except (ValueError, AttributeError):
            return None
    
    def _analyze_skill_authenticity(self, original: str, optimized: str) -> Dict[str, Any]:
        """Check for fabricated skills not present in original resume."""
        result = {"authenticity_score": 1.0, "violations": []}
        
        # Common technical skills to watch for
        technical_skills = [
            'python', 'java', 'javascript', 'react', 'angular', 'vue', 'node.js',
            'docker', 'kubernetes', 'aws', 'azure', 'gcp', 'tensorflow', 'pytorch',
            'machine learning', 'artificial intelligence', 'data science', 'sql',
            'mongodb', 'postgresql', 'redis', 'elasticsearch'
        ]
        
        orig_lower = original.lower()
        opt_lower = optimized.lower()
        
        new_skills = []
        for skill in technical_skills:
            if skill in opt_lower and skill not in orig_lower:
                new_skills.append(skill)
        
        if new_skills:
            result["violations"].append({
                "type": "new_technical_skills",
                "confidence": 0.6,
                "details": f"New technical skills found: {', '.join(new_skills)}",
                "skills": new_skills
            })
            # Lower penalty for skills as they might be legitimate additions
            result["authenticity_score"] = max(0.0, 1.0 - len(new_skills) * 0.1)
        
        return result
    
    def _generate_change_summary(self, original: str, optimized: str) -> Dict[str, Any]:
        """Generate summary of changes between original and optimized content."""
        import difflib
        
        # Get unified diff
        diff_lines = list(difflib.unified_diff(
            original.splitlines(keepends=True),
            optimized.splitlines(keepends=True),
            fromfile='original',
            tofile='optimized',
            n=3
        ))
        
        # Count additions and deletions
        additions = len([line for line in diff_lines if line.startswith('+')])
        deletions = len([line for line in diff_lines if line.startswith('-')])
        
        return {
            "total_changes": len(diff_lines),
            "additions": additions,
            "deletions": deletions,
            "modification_ratio": min(1.0, len(diff_lines) / max(len(original.splitlines()), 1))
        }
    
    def _calculate_fabrication_confidence(self, analysis_results: Dict[str, Any]) -> float:
        """Calculate overall confidence that content contains fabrications."""
        violation_scores = []
        
        for violation in analysis_results["violations"]:
            violation_scores.append(violation["confidence"])
        
        if not violation_scores:
            return 0.0
        
        # Use weighted average with emphasis on higher confidence violations
        sorted_scores = sorted(violation_scores, reverse=True)
        weighted_sum = sum(score * (1.0 - i * 0.1) for i, score in enumerate(sorted_scores))
        weight_total = sum(1.0 - i * 0.1 for i in range(len(sorted_scores)))
        
        return weighted_sum / weight_total if weight_total > 0 else 0.0
    
    def _calculate_overall_score(self, analysis_results: Dict[str, Any]) -> float:
        """Calculate overall truthfulness score from all analysis components."""
        # Weight different aspects of truthfulness
        weights = {
            "content_similarity": 0.3,
            "entity_consistency": 0.25,
            "numerical_integrity": 0.25, 
            "skill_authenticity": 0.2
        }
        
        weighted_score = sum(
            analysis_results[metric] * weight 
            for metric, weight in weights.items()
        )
        
        return min(1.0, max(0.0, weighted_score))
    
    def _generate_evaluation_notes(self, analysis_results: Dict[str, Any]) -> str:
        """Generate human-readable notes about the evaluation."""
        notes = []
        
        # Overall assessment
        fab_confidence = analysis_results["fabrication_confidence"]
        if fab_confidence < 0.3:
            notes.append("✓ Low fabrication risk detected")
        elif fab_confidence < 0.7:
            notes.append("⚠ Moderate fabrication risk - review flagged items")
        else:
            notes.append("🚨 High fabrication risk - significant concerns identified")
        
        # Specific violations
        if analysis_results["violations"]:
            notes.append(f"\nViolations found ({len(analysis_results['violations'])}):")
            for violation in analysis_results["violations"]:
                confidence_icon = "🔴" if violation["confidence"] > 0.7 else "🟡" if violation["confidence"] > 0.4 else "🟢"
                notes.append(f"{confidence_icon} {violation['type']}: {violation['details']}")
        
        # Change summary
        changes = analysis_results["change_summary"]
        notes.append(f"\nContent changes: {changes['additions']} additions, {changes['deletions']} deletions")
        
        return "\n".join(notes)
    
    def get_description(self) -> str:
        """Get description of this evaluator."""
        return ("Evaluates truthfulness of resume optimizations using content similarity, "
                "entity consistency, numerical integrity, and skill authenticity analysis")


class ContentQualityEvaluator(BaseEvaluator):
    """Evaluates professional quality of optimized content."""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("content_quality", config)
    
    async def evaluate(self, test_case: TestCase, actual_output: Any) -> EvaluationResult:
        """
        Evaluate content quality.
        
        Args:
            test_case: Test case with content to evaluate
            actual_output: Optimized content to assess
            
        Returns:
            EvaluationResult with quality metrics
        """
        self.validate_inputs(test_case, actual_output)
        
        # Placeholder implementation - will be implemented in Issue #113
        overall_score = 0.85  # Placeholder score
        detailed_scores = {
            "readability": 0.80,
            "professional_language": 0.90,
            "ats_compatibility": 0.85
        }
        
        return self.create_result(
            test_case=test_case,
            overall_score=overall_score,
            detailed_scores=detailed_scores,
            passed=overall_score >= 0.7,
            notes="Placeholder implementation - full functionality in Issue #113"
        )
    
    def get_description(self) -> str:
        """Get description of this evaluator."""
        return "Evaluates professional quality and readability of optimized resume content"


class RelevanceImpactEvaluator(BaseEvaluator):
    """Evaluates impact of optimizations on job relevance."""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("relevance_impact", config)
    
    async def evaluate(self, test_case: TestCase, actual_output: Any) -> EvaluationResult:
        """
        Evaluate relevance impact.
        
        Args:
            test_case: Test case with before/after data
            actual_output: Optimization impact results
            
        Returns:
            EvaluationResult with impact metrics
        """
        self.validate_inputs(test_case, actual_output)
        
        # Placeholder implementation - will be implemented in Issue #114
        overall_score = 0.78  # Placeholder score
        detailed_scores = {
            "match_score_improvement": 0.75,
            "keyword_alignment": 0.80,
            "targeting_effectiveness": 0.75
        }
        
        return self.create_result(
            test_case=test_case,
            overall_score=overall_score,
            detailed_scores=detailed_scores,
            passed=overall_score >= 0.6,
            notes="Placeholder implementation - full functionality in Issue #114"
        )
    
    def get_description(self) -> str:
        """Get description of this evaluator."""
        return "Evaluates whether optimizations actually improve job relevance and match scores"