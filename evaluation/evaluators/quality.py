# ABOUTME: Quality evaluators for truthfulness, content quality, and relevance
# ABOUTME: Tests optimization quality and maintains professional standards
"""
Quality Evaluators

Evaluators that test the quality aspects of resume optimization including
truthfulness verification, content quality, and relevance impact.
"""

import re
import statistics
from collections import Counter
from typing import Any, Dict, List, Set, Tuple
import textstat
from .base import BaseEvaluator
from ..test_data.models import TestCase, EvaluationResult


class TruthfulnessEvaluator(BaseEvaluator):
    """Evaluates truthfulness of resume optimizations."""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("truthfulness", config)
    
    async def evaluate(self, test_case: TestCase, actual_output: Any) -> EvaluationResult:
        """
        Evaluate truthfulness of optimizations.
        
        Args:
            test_case: Test case with original and optimized content
            actual_output: Optimization results to verify
            
        Returns:
            EvaluationResult with truthfulness metrics
        """
        self.validate_inputs(test_case, actual_output)
        
        # Placeholder implementation - will be implemented in Issue #112
        overall_score = 0.90  # Placeholder score
        detailed_scores = {
            "fabrication_detection": 0.95,
            "content_comparison": 0.85,
            "scope_verification": 0.90
        }
        
        return self.create_result(
            test_case=test_case,
            overall_score=overall_score,
            detailed_scores=detailed_scores,
            passed=overall_score >= 0.8,
            notes="Placeholder implementation - full functionality in Issue #112"
        )
    
    def get_description(self) -> str:
        """Get description of this evaluator."""
        return "Evaluates truthfulness of resume optimizations to prevent fabrication"


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
            # Remove markdown formatting and HTML tags
            text = re.sub(r'[#*_`\[\]()]', '', content)
            text = re.sub(r'<[^>]+>', '', text)
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
        
        # Buzzword analysis
        buzzword_count = sum(1 for word in words if word in self.BUZZWORDS)
        buzzword_density = buzzword_count / len(words)
        buzzword_score = max(0, 1 - (buzzword_density / self.thresholds['max_buzzword_density']))
        
        # Action verb analysis
        strong_verbs = sum(1 for word in words if word in self.STRONG_ACTION_VERBS)
        weak_verbs = sum(1 for word in words if word in self.WEAK_VERBS)
        total_verbs = strong_verbs + weak_verbs
        
        if total_verbs > 0:
            action_verb_ratio = strong_verbs / total_verbs
            action_verb_score = min(1, action_verb_ratio / self.thresholds['min_action_verb_ratio'])
        else:
            action_verb_score = 0.0
        
        # Passive voice detection (simplified)
        passive_indicators = ['was', 'were', 'been', 'being']
        passive_count = sum(1 for word in words if word in passive_indicators)
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
            avg_frequency = sum(word_freq.values()) / len(word_freq)
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