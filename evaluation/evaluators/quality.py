# ABOUTME: Quality evaluators for truthfulness, content quality, and relevance
# ABOUTME: Tests optimization quality and maintains professional standards
"""
Quality Evaluators

Evaluators that test the quality aspects of resume optimization including
truthfulness verification, content quality, and relevance impact.
"""

import re
import statistics
import time
from collections import Counter
from typing import Any, Dict, List, Set, Tuple
import textstat
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
    """Evaluates the professional quality of optimized resume content."""
    
    # Common resume buzzwords to detect overuse
    BUZZWORDS = {
        'synergy', 'leverage', 'innovative', 'dynamic', 'proactive', 'strategic',
        'results-driven', 'detail-oriented', 'team-player', 'self-motivated',
        'passionate', 'dedicated', 'experienced', 'proven', 'excellent',
        'outstanding', 'exceptional', 'world-class', 'cutting-edge', 'best-in-class'
    }
    
    # Professional action verbs (stronger alternatives)
    STRONG_ACTION_VERBS = {
        'achieved', 'analyzed', 'built', 'created', 'designed', 'developed',
        'directed', 'established', 'executed', 'implemented', 'improved',
        'increased', 'led', 'managed', 'optimized', 'organized', 'streamlined',
        'transformed', 'collaborated', 'coordinated', 'facilitated', 'mentored'
    }
    
    # Weak verbs to flag
    WEAK_VERBS = {
        'helped', 'assisted', 'worked', 'did', 'was', 'were', 'had', 'made',
        'got', 'went', 'came', 'tried', 'attempted'
    }
    
    # ATS-unfriendly elements
    ATS_PROBLEMATIC_ELEMENTS = {
        'special_chars': r'[^\w\s\-\.\,\;\:\(\)\[\]\/\&\%\$\#\@\!\?]',
        'graphics_indicators': ['│', '■', '●', '◆', '▲', '►', '✓', '★'],
        'complex_formatting': ['<table>', '<div>', '<span style=', 'text-align:'],
        'non_standard_headers': ['EXPERIENCE', 'WORK HISTORY', 'CAREER SUMMARY']
    }
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the Content Quality Evaluator."""
        super().__init__("content_quality", config)
        
        # Configuration thresholds
        default_thresholds = {
            'min_readability_score': 60,  # Flesch Reading Ease
            'max_grade_level': 12,        # Flesch-Kincaid Grade Level
            'max_buzzword_density': 0.03, # 3% of total words
            'min_action_verb_ratio': 0.15, # 15% of verbs should be strong
            'max_passive_voice_ratio': 0.20, # Max 20% passive voice
            'min_ats_compatibility': 0.80  # 80% ATS compatibility
        }
        self.thresholds = default_thresholds.copy()
        self.thresholds.update(self.config.get('thresholds', {}))
    
    async def evaluate(self, test_case: TestCase, actual_output: Any) -> EvaluationResult:
        """
        Evaluate content quality of resume text.
        
        Args:
            test_case: Test case with resume content
            actual_output: Optimized resume content to evaluate
            
        Returns:
            EvaluationResult with comprehensive quality metrics
        """
        self.validate_inputs(test_case, actual_output)
        
        # Extract text content for analysis
        resume_text = self._extract_text_content(actual_output)
        
        if not resume_text.strip():
            return self.create_result(
                test_case=test_case,
                overall_score=0.0,
                passed=False,
                notes="No readable text content found in resume"
            )
        
        # Perform all quality assessments
        readability_scores = self._assess_readability(resume_text)
        language_scores = self._assess_professional_language(resume_text)
        ats_scores = self._assess_ats_compatibility(resume_text)
        formatting_scores = self._assess_formatting_consistency(resume_text)
        
        # Combine all scores
        detailed_scores = {
            **readability_scores,
            **language_scores,
            **ats_scores,
            **formatting_scores
        }
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(detailed_scores)
        
        # Generate feedback
        feedback = self._generate_feedback(detailed_scores, resume_text)
        
        return self.create_result(
            test_case=test_case,
            overall_score=overall_score,
            detailed_scores=detailed_scores,
            passed=overall_score >= 0.70,
            notes=feedback
        )
    
    def _extract_text_content(self, content: Any) -> str:
        """Extract plain text from various content formats."""
        if isinstance(content, str):
            # Remove HTML tags first
            text = re.sub(r'<[^>]+>', '', content)
            # Remove markdown formatting while preserving sentence structure
            # Keep periods, commas, semicolons for readability analysis
            text = re.sub(r'#+\s*', '', text)  # Remove headers
            text = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', text)  # Remove bold/italic
            text = re.sub(r'_([^_]+)_', r'\1', text)  # Remove underscore emphasis
            text = re.sub(r'`([^`]+)`', r'\1', text)  # Remove code blocks
            text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)  # Extract link text
            return text.strip()
        elif isinstance(content, dict):
            # Extract from structured content
            if 'content' in content:
                return self._extract_text_content(content['content'])
            elif 'text' in content:
                return self._extract_text_content(content['text'])
            elif 'resume_content' in content:
                return self._extract_text_content(content['resume_content'])
        
        return str(content)
    
    def _assess_readability(self, text: str) -> Dict[str, float]:
        """Assess readability using multiple metrics."""
        try:
            flesch_ease = textstat.flesch_reading_ease(text)
            flesch_kincaid = textstat.flesch_kincaid_grade(text)
            ari = textstat.automated_readability_index(text)
            smog = textstat.smog_index(text)
            
            # Normalize scores (0-1 scale)
            readability_score = max(0, min(1, flesch_ease / 100))
            grade_level_score = max(0, min(1, (20 - flesch_kincaid) / 20))
            ari_score = max(0, min(1, (20 - ari) / 20))
            smog_score = max(0, min(1, (20 - smog) / 20))
            
            return {
                'flesch_reading_ease': flesch_ease / 100,
                'flesch_kincaid_grade': grade_level_score,
                'automated_readability_index': ari_score,
                'smog_index': smog_score,
                'overall_readability': statistics.mean([
                    readability_score, grade_level_score, ari_score, smog_score
                ])
            }
        except Exception as e:
            self.logger.warning(f"Readability assessment failed: {e}")
            return {
                'flesch_reading_ease': 0.0,
                'flesch_kincaid_grade': 0.0,
                'automated_readability_index': 0.0,
                'smog_index': 0.0,
                'overall_readability': 0.0
            }
    
    def _assess_professional_language(self, text: str) -> Dict[str, float]:
        """Assess professional language quality."""
        words = re.findall(r'\b\w+\b', text.lower())
        sentences = re.split(r'[.!?]+', text)
        
        if not words:
            return {
                'buzzword_density': 1.0,  # Penalty for no content
                'action_verb_strength': 0.0,
                'passive_voice_ratio': 1.0,
                'sentence_variety': 0.0,
                'professional_language_score': 0.0
            }
        
        # Single pass through words for performance
        buzzword_count = 0
        strong_verbs = 0
        weak_verbs = 0
        passive_count = 0
        passive_indicators = {'was', 'were', 'been', 'being'}
        
        for word in words:
            if word in self.BUZZWORDS:
                buzzword_count += 1
            if word in self.STRONG_ACTION_VERBS:
                strong_verbs += 1
            elif word in self.WEAK_VERBS:
                weak_verbs += 1
            if word in passive_indicators:
                passive_count += 1
        
        # Calculate scores
        buzzword_density = buzzword_count / len(words)
        buzzword_score = max(0, 1 - (buzzword_density / self.thresholds['max_buzzword_density']))
        
        total_verbs = strong_verbs + weak_verbs
        if total_verbs > 0:
            action_verb_ratio = strong_verbs / total_verbs
            action_verb_score = min(1, action_verb_ratio / self.thresholds['min_action_verb_ratio'])
        else:
            # Use neutral score for sections without verbs (e.g., contact info)
            action_verb_score = 0.5
        
        passive_ratio = passive_count / len(words)
        passive_score = max(0, 1 - (passive_ratio / self.thresholds['max_passive_voice_ratio']))
        
        # Sentence variety
        sentence_lengths = [len(s.split()) for s in sentences if s.strip()]
        if sentence_lengths:
            avg_length = statistics.mean(sentence_lengths)
            length_variance = statistics.variance(sentence_lengths) if len(sentence_lengths) > 1 else 0
            # Ideal sentence length: 15-20 words with good variety
            length_score = max(0, 1 - abs(avg_length - 17.5) / 17.5)
            variety_score = min(1, length_variance / 25)  # Normalize variance
            sentence_score = (length_score + variety_score) / 2
        else:
            sentence_score = 0.0
        
        professional_score = statistics.mean([
            buzzword_score, action_verb_score, passive_score, sentence_score
        ])
        
        return {
            'buzzword_density': 1 - buzzword_score,  # Lower is better
            'action_verb_strength': action_verb_score,
            'passive_voice_ratio': 1 - passive_score,  # Lower is better
            'sentence_variety': sentence_score,
            'professional_language_score': professional_score
        }
    
    def _assess_ats_compatibility(self, text: str) -> Dict[str, float]:
        """Assess ATS (Applicant Tracking System) compatibility."""
        # Handle empty text
        if not text:
            return {
                'ats_special_characters': 0.0,
                'ats_graphics_compatibility': 0.0,
                'ats_formatting_compatibility': 0.0,
                'ats_header_standards': 0.0,
                'ats_keyword_optimization': 0.0,
                'ats_compatibility_score': 0.0
            }
        
        # Check for problematic special characters
        special_char_matches = len(re.findall(
            self.ATS_PROBLEMATIC_ELEMENTS['special_chars'], text
        ))
        special_char_score = max(0, 1 - (special_char_matches / (len(text) / 100)))
        
        # Check for graphics indicators
        graphics_count = sum(1 for char in self.ATS_PROBLEMATIC_ELEMENTS['graphics_indicators'] 
                           if char in text)
        graphics_score = 1.0 if graphics_count == 0 else max(0, 1 - (graphics_count / 10))
        
        # Check for complex formatting
        complex_formatting_count = sum(1 for element in self.ATS_PROBLEMATIC_ELEMENTS['complex_formatting']
                                     if element in text)
        formatting_score = 1.0 if complex_formatting_count == 0 else max(0, 1 - (complex_formatting_count / 5))
        
        # Standard section headers check
        standard_headers = ['experience', 'education', 'skills', 'summary', 'contact']
        text_lower = text.lower()
        header_matches = sum(1 for header in standard_headers if header in text_lower)
        header_score = min(1, header_matches / len(standard_headers))
        
        # Keyword density optimization detection
        words = re.findall(r'\b\w+\b', text.lower())
        word_freq = Counter(words)
        
        # Flag potential keyword stuffing
        if words:
            max_frequency = max(word_freq.values())
            keyword_stuffing_ratio = max_frequency / len(words)
            
            # Penalize if any word appears more than 3% of total words
            keyword_score = max(0, 1 - max(0, keyword_stuffing_ratio - 0.03) * 10)
        else:
            keyword_score = 0.0
        
        ats_score = statistics.mean([
            special_char_score, graphics_score, formatting_score, 
            header_score, keyword_score
        ])
        
        return {
            'ats_special_characters': special_char_score,
            'ats_graphics_compatibility': graphics_score,
            'ats_formatting_compatibility': formatting_score,
            'ats_header_standards': header_score,
            'ats_keyword_optimization': keyword_score,
            'ats_compatibility_score': ats_score
        }
    
    def _assess_formatting_consistency(self, text: str) -> Dict[str, float]:
        """Assess formatting consistency."""
        lines = text.split('\n')
        
        # Check for consistent header formatting
        headers = [line.strip() for line in lines if line.strip().isupper() or 
                  (line.strip() and not line.strip()[0].islower())]
        
        if not headers:
            header_consistency = 0.5  # Neutral if no clear headers
        else:
            # Check if headers follow consistent pattern
            header_patterns = set()
            for header in headers:
                if header.isupper():
                    header_patterns.add('upper')
                elif header.istitle():
                    header_patterns.add('title')
                else:
                    header_patterns.add('mixed')
            
            header_consistency = 1.0 if len(header_patterns) == 1 else 0.5
        
        # Check for consistent bullet point usage
        bullet_lines = [line for line in lines if re.match(r'^\s*[-•*]\s', line)]
        if bullet_lines:
            bullet_chars = []
            for line in bullet_lines:
                match = re.match(r'^\s*([-•*])', line)
                if match:
                    bullet_chars.append(match.group(1))
            unique_bullets = set(bullet_chars)
            bullet_consistency = 1.0 if len(unique_bullets) == 1 else 0.5
        else:
            bullet_consistency = 1.0  # No bullets is consistent
        
        # Check for consistent spacing
        empty_lines = [i for i, line in enumerate(lines) if not line.strip()]
        if len(lines) > 1:
            spacing_patterns = []
            for i in range(len(empty_lines) - 1):
                spacing_patterns.append(empty_lines[i + 1] - empty_lines[i])
            
            if spacing_patterns:
                spacing_consistency = 1.0 if len(set(spacing_patterns)) <= 2 else 0.7
            else:
                spacing_consistency = 1.0
        else:
            spacing_consistency = 1.0
        
        formatting_score = statistics.mean([
            header_consistency, bullet_consistency, spacing_consistency
        ])
        
        return {
            'header_consistency': header_consistency,
            'bullet_consistency': bullet_consistency,
            'spacing_consistency': spacing_consistency,
            'formatting_consistency_score': formatting_score
        }
    
    def _calculate_overall_score(self, detailed_scores: Dict[str, float]) -> float:
        """Calculate weighted overall quality score."""
        weights = {
            'overall_readability': 0.25,
            'professional_language_score': 0.30,
            'ats_compatibility_score': 0.30,
            'formatting_consistency_score': 0.15
        }
        
        weighted_score = 0.0
        total_weight = 0.0
        
        for metric, weight in weights.items():
            if metric in detailed_scores:
                weighted_score += detailed_scores[metric] * weight
                total_weight += weight
        
        return weighted_score / total_weight if total_weight > 0 else 0.0
    
    def _generate_feedback(self, scores: Dict[str, float], text: str) -> str:
        """Generate actionable feedback based on quality scores."""
        feedback = []
        
        # Readability feedback
        if scores.get('overall_readability', 0) < 0.6:
            feedback.append("Consider simplifying sentence structure for better readability")
        
        # Professional language feedback
        if scores.get('buzzword_density', 0) > 0.05:
            feedback.append("Reduce use of generic buzzwords; focus on specific achievements")
        
        if scores.get('action_verb_strength', 0) < 0.5:
            feedback.append("Use stronger action verbs to describe accomplishments")
        
        if scores.get('passive_voice_ratio', 0) > 0.3:
            feedback.append("Reduce passive voice usage; prefer active voice constructions")
        
        # ATS compatibility feedback
        if scores.get('ats_compatibility_score', 0) < 0.8:
            feedback.append("Improve ATS compatibility by using standard formatting")
        
        # Formatting feedback
        if scores.get('formatting_consistency_score', 0) < 0.8:
            feedback.append("Ensure consistent formatting throughout the document")
        
        if not feedback:
            feedback.append("Content quality is good overall")
        
        return "; ".join(feedback)
    
    def get_description(self) -> str:
        """Get description of this evaluator."""
        return ("Evaluates professional quality of resume content including readability metrics, "
                "professional language assessment, ATS compatibility, and formatting consistency")


class RelevanceImpactEvaluator(BaseEvaluator):
    """Evaluates impact of optimizations on job relevance."""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("relevance_impact", config)
        self.min_score_improvement = config.get("min_score_improvement", 0.05) if config else 0.05
        self.keyword_weight = config.get("keyword_weight", 0.4) if config else 0.4
        self.semantic_weight = config.get("semantic_weight", 0.6) if config else 0.6
    
    async def evaluate(self, test_case: TestCase, actual_output: Any) -> EvaluationResult:
        """
        Evaluate relevance impact of resume optimization.
        
        Args:
            test_case: Test case with before/after resume data
            actual_output: Optimization results containing before/after content
            
        Returns:
            EvaluationResult with impact metrics
        """
        start_time = time.time()
        
        self.validate_inputs(test_case, actual_output)
        
        try:
            # Extract data from test case and actual output
            before_resume, after_resume, job_description = self._extract_content(test_case, actual_output)
            
            # Calculate match score improvements
            match_improvement_score = self._calculate_match_improvement(
                before_resume, after_resume, job_description
            )
            
            # Calculate keyword alignment improvements
            keyword_alignment_score = self._calculate_keyword_alignment_improvement(
                before_resume, after_resume, job_description
            )
            
            # Calculate targeting effectiveness
            targeting_effectiveness_score = self._calculate_targeting_effectiveness(
                before_resume, after_resume, job_description, actual_output
            )
            
            # Calculate section-specific improvements
            section_scores = self._calculate_section_improvements(
                before_resume, after_resume, job_description
            )
            
            # Generate analysis and recommendations
            analysis = self._generate_analysis(
                before_resume, after_resume, job_description, actual_output
            )
            
            # Calculate overall score
            overall_score = (
                match_improvement_score * 0.4 +
                keyword_alignment_score * 0.3 +
                targeting_effectiveness_score * 0.3
            )
            
            detailed_scores = {
                "match_score_improvement": match_improvement_score,
                "keyword_alignment_improvement": keyword_alignment_score,
                "targeting_effectiveness": targeting_effectiveness_score,
                **section_scores
            }
            
            execution_time = time.time() - start_time
            
            return self.create_result(
                test_case=test_case,
                overall_score=overall_score,
                detailed_scores=detailed_scores,
                passed=overall_score >= 0.6,
                notes=f"Relevance impact analysis completed. {analysis.get('summary', '')}",
                execution_time=execution_time,
                api_calls_made=0,
                tokens_used=0,
                analysis=analysis
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Error in relevance impact evaluation: {str(e)}")
            
            return self.create_result(
                test_case=test_case,
                overall_score=0.0,
                detailed_scores={},
                passed=False,
                notes=f"Evaluation failed: {str(e)}",
                execution_time=execution_time,
                error_message=str(e)
            )
    
    def _extract_content(self, test_case: TestCase, actual_output: Any) -> tuple:
        """Extract before/after resume content and job description."""
        # Check if actual_output contains optimization results in expected format
        if isinstance(actual_output, dict):
            # Check for direct optimization results format
            if 'resume_before' in actual_output and 'resume_after' in actual_output:
                before_resume = actual_output['resume_before']
                after_resume = actual_output['resume_after']
                job_description = actual_output.get('job_description', test_case.job_description)
            # Check for alternative format with optimized_resume
            elif 'optimized_resume' in actual_output:
                before_resume = test_case.resume_content
                after_resume = actual_output['optimized_resume']
                job_description = test_case.job_description
            # Handle TestRunner's ActualOutput format - use ground truth for optimization
            elif 'resume' in actual_output and 'job' in actual_output:
                before_resume = test_case.resume_content
                after_resume = test_case.ground_truth.get('optimized_resume', '')
                job_description = test_case.job_description
            else:
                # Fallback to ground truth
                before_resume = test_case.resume_content
                after_resume = test_case.ground_truth.get('optimized_resume', '')
                job_description = test_case.job_description
        else:
            # Fallback to test case data
            before_resume = test_case.resume_content
            after_resume = test_case.ground_truth.get('optimized_resume', str(actual_output) if actual_output else '')
            job_description = test_case.job_description
        
        if not after_resume:
            raise ValueError("No optimized resume content found in actual_output or test_case.ground_truth")
        
        return before_resume, after_resume, job_description
    
    def _calculate_match_improvement(self, before_resume: str, after_resume: str, job_description: str) -> float:
        """Calculate improvement in match score between before and after."""
        before_score = self._calculate_semantic_similarity(before_resume, job_description)
        after_score = self._calculate_semantic_similarity(after_resume, job_description)
        
        # Handle very small or zero before_score to avoid division issues
        if before_score < 0.001:
            return 1.0 if after_score > 0.001 else 0.0
        
        improvement = (after_score - before_score) / before_score
        # Normalize to 0-1 scale, with 0.5 being no improvement
        normalized_score = min(1.0, max(0.0, 0.5 + improvement))
        
        return normalized_score
    
    def _calculate_keyword_alignment_improvement(self, before_resume: str, after_resume: str, job_description: str) -> float:
        """Calculate improvement in keyword alignment."""
        job_keywords = self._extract_keywords(job_description)
        
        before_coverage = self._calculate_keyword_coverage(before_resume, job_keywords)
        after_coverage = self._calculate_keyword_coverage(after_resume, job_keywords)
        
        if len(job_keywords) == 0:
            return 0.5  # Neutral score if no keywords found
        
        improvement = after_coverage - before_coverage
        # Normalize improvement to 0-1 scale
        max_possible_improvement = len(job_keywords) - before_coverage
        
        if max_possible_improvement == 0:
            return 1.0  # Already at maximum coverage
        
        normalized_improvement = improvement / max_possible_improvement
        return min(1.0, max(0.0, 0.5 + normalized_improvement))
    
    def _calculate_targeting_effectiveness(self, before_resume: str, after_resume: str, 
                                         job_description: str, actual_output: Any) -> float:
        """Calculate how effectively the optimization targeted relevant improvements."""
        # Extract optimization details if available
        optimization_details = {}
        if isinstance(actual_output, dict):
            optimization_details = actual_output.get('optimization_details', {})
        
        # Calculate the relevance of changes made
        changes_made = self._identify_changes(before_resume, after_resume)
        job_keywords = self._extract_keywords(job_description)
        
        if not changes_made:
            return 0.0  # No changes made
        
        relevant_changes = 0
        total_changes = len(changes_made)
        
        for change in changes_made:
            if self._is_change_relevant(change, job_keywords):
                relevant_changes += 1
        
        targeting_score = relevant_changes / total_changes if total_changes > 0 else 0.0
        return targeting_score
    
    def _calculate_section_improvements(self, before_resume: str, after_resume: str, job_description: str) -> Dict[str, float]:
        """Calculate improvements by resume section."""
        sections = ['summary', 'experience', 'skills', 'education']
        section_scores = {}
        
        for section in sections:
            before_section = self._extract_section(before_resume, section)
            after_section = self._extract_section(after_resume, section)
            
            if before_section and after_section:
                before_score = self._calculate_semantic_similarity(before_section, job_description)
                after_score = self._calculate_semantic_similarity(after_section, job_description)
                
                improvement = (after_score - before_score) if before_score > 0 else (after_score if after_score > 0 else 0)
                section_scores[f"{section}_improvement"] = min(1.0, max(0.0, 0.5 + improvement))
            else:
                section_scores[f"{section}_improvement"] = 0.5  # Neutral if section not found
        
        return section_scores
    
    def _generate_analysis(self, before_resume: str, after_resume: str, 
                          job_description: str, actual_output: Any) -> Dict[str, Any]:
        """Generate detailed analysis and recommendations."""
        before_match = self._calculate_semantic_similarity(before_resume, job_description)
        after_match = self._calculate_semantic_similarity(after_resume, job_description)
        improvement_percentage = ((after_match - before_match) / before_match * 100) if before_match > 0 else 0
        
        job_keywords = self._extract_keywords(job_description)
        before_keyword_coverage = self._calculate_keyword_coverage(before_resume, job_keywords)
        after_keyword_coverage = self._calculate_keyword_coverage(after_resume, job_keywords)
        
        changes = self._identify_changes(before_resume, after_resume)
        effective_changes = [c for c in changes if self._is_change_relevant(c, job_keywords)]
        counterproductive_changes = [c for c in changes if not self._is_change_relevant(c, job_keywords)]
        
        return {
            "summary": f"Match score improved by {improvement_percentage:.1f}%",
            "before_match_score": before_match * 100,
            "after_match_score": after_match * 100,
            "improvement_percentage": improvement_percentage,
            "keyword_coverage_before": before_keyword_coverage,
            "keyword_coverage_after": after_keyword_coverage,
            "total_keywords": len(job_keywords),
            "top_effective_changes": effective_changes[:5],
            "counterproductive_changes": counterproductive_changes[:3],
            "recommendations": self._generate_recommendations(before_resume, after_resume, job_description)
        }
    
    def _calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity between two texts using simple overlap."""
        # Simple implementation - could be enhanced with more sophisticated methods
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def _extract_keywords(self, job_description: str) -> list:
        """Extract important keywords from job description."""
        # Simple keyword extraction - could be enhanced with NLP libraries
        import re
        
        # Common technical skills and keywords
        tech_keywords = [
            'python', 'javascript', 'java', 'react', 'node.js', 'aws', 'docker', 'kubernetes',
            'sql', 'postgresql', 'mongodb', 'git', 'ci/cd', 'agile', 'scrum', 'api', 'rest',
            'microservices', 'cloud', 'devops', 'machine learning', 'ai', 'data', 'analytics'
        ]
        
        # Extract words from job description
        words = re.findall(r'\b\w+\b', job_description.lower())
        
        # Find technical keywords
        keywords = []
        for word in words:
            if word in tech_keywords or len(word) > 6:  # Include longer words as potential keywords
                keywords.append(word)
        
        # Remove duplicates and return
        return list(set(keywords))
    
    def _calculate_keyword_coverage(self, resume: str, keywords: list) -> int:
        """Calculate how many keywords are covered in the resume."""
        resume_lower = resume.lower()
        covered = 0
        
        for keyword in keywords:
            if keyword in resume_lower:
                covered += 1
        
        return covered
    
    def _identify_changes(self, before_text: str, after_text: str) -> list:
        """Identify changes between before and after text."""
        # Simple diff implementation - could be enhanced
        before_lines = before_text.split('\n')
        after_lines = after_text.split('\n')
        
        changes = []
        for i, (before_line, after_line) in enumerate(zip(before_lines, after_lines)):
            if before_line.strip() != after_line.strip():
                changes.append({
                    'line': i,
                    'before': before_line.strip(),
                    'after': after_line.strip(),
                    'type': 'modification'
                })
        
        # Handle added lines
        if len(after_lines) > len(before_lines):
            for i in range(len(before_lines), len(after_lines)):
                changes.append({
                    'line': i,
                    'before': '',
                    'after': after_lines[i].strip(),
                    'type': 'addition'
                })
        
        return changes
    
    def _is_change_relevant(self, change: dict, job_keywords: list) -> bool:
        """Determine if a change is relevant to the job requirements."""
        change_text = (change.get('after', '') + ' ' + change.get('before', '')).lower()
        # Split into words to avoid false positives from substring matches
        change_words = set(change_text.split())
        
        for keyword in job_keywords:
            # Check both word boundary match and substring match for compound terms
            if keyword in change_words or (len(keyword) > 3 and keyword in change_text):
                return True
        
        return False
    
    def _extract_section(self, resume: str, section_name: str) -> str:
        """Extract a specific section from the resume."""
        lines = resume.split('\n')
        section_lines = []
        in_section = False
        
        section_headers = {
            'summary': ['summary', 'objective', 'profile'],
            'experience': ['experience', 'work experience', 'employment'],
            'skills': ['skills', 'technical skills', 'competencies'],
            'education': ['education', 'education background']
        }
        
        headers = section_headers.get(section_name, [section_name])
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # Check if this line is a section header
            if any(header in line_lower for header in headers):
                in_section = True
                continue
            
            # Check if this is a different section header
            if line_lower and line.isupper() and in_section and not any(header in line_lower for header in headers):
                break
            
            if in_section and line.strip():
                section_lines.append(line)
        
        return '\n'.join(section_lines)
    
    def _generate_recommendations(self, before_resume: str, after_resume: str, job_description: str) -> Dict[str, Any]:
        """Generate recommendations for future improvements."""
        job_keywords = self._extract_keywords(job_description)
        after_coverage = self._calculate_keyword_coverage(after_resume, job_keywords)
        missing_keywords = [kw for kw in job_keywords if kw not in after_resume.lower()]
        
        focus_areas = []
        if missing_keywords:
            focus_areas.append("keyword_optimization")
        
        sections = ['summary', 'experience', 'skills']
        for section in sections:
            section_content = self._extract_section(after_resume, section)
            if not section_content or len(section_content.strip()) < 50:
                focus_areas.append(f"{section}_enhancement")
        
        return {
            "focus_areas": focus_areas[:3],  # Top 3 focus areas
            "missing_keywords": missing_keywords[:5],  # Top 5 missing keywords
            "keyword_coverage_percentage": (after_coverage / len(job_keywords) * 100) if job_keywords else 100,
            "improvement_suggestions": [
                "Incorporate more industry-specific terminology",
                "Quantify achievements with specific metrics",
                "Align experience bullets with job requirements"
            ]
        }
    
    def get_description(self) -> str:
        """Get description of this evaluator."""
        return "Evaluates whether optimizations actually improve job relevance and match scores"