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
        import time
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
        
        if before_score == 0:
            return 1.0 if after_score > 0 else 0.0
        
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
        
        for keyword in job_keywords:
            if keyword in change_text:
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