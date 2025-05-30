# ABOUTME: Comprehensive tests for RelevanceImpactEvaluator implementation
# ABOUTME: Tests match score improvements, keyword alignment, and optimization effectiveness
"""
Test RelevanceImpactEvaluator

Comprehensive tests for the RelevanceImpactEvaluator class including:
- Match score improvement calculation
- Keyword alignment analysis
- Targeting effectiveness measurement
- Section-specific improvements
- Analysis and recommendations generation
"""

import pytest
import asyncio
from typing import Dict, Any
from unittest.mock import Mock, patch

from evaluation.evaluators.quality import RelevanceImpactEvaluator
from evaluation.test_data.models import TestCase, EvaluationResult


class TestRelevanceImpactEvaluator:
    """Test RelevanceImpactEvaluator functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.evaluator = RelevanceImpactEvaluator()
        
        # Sample resume content
        self.before_resume = """
        John Smith
        Software Developer
        
        SUMMARY
        Developer with experience in programming.
        
        EXPERIENCE
        Developer at Company A
        - Worked on projects
        - Fixed bugs
        
        SKILLS
        Programming, computers
        """
        
        self.after_resume = """
        John Smith
        Senior Software Engineer
        
        SUMMARY
        Experienced Senior Software Engineer with 5+ years developing scalable 
        Python applications and leading engineering teams.
        
        EXPERIENCE
        Senior Software Engineer at Company A
        - Led development of microservices using Python and Docker
        - Implemented CI/CD pipelines reducing deployment time by 60%
        - Mentored junior developers and conducted code reviews
        
        SKILLS
        Python, JavaScript, Docker, Kubernetes, AWS, CI/CD, Git
        """
        
        self.job_description = """
        Senior Software Engineer - Python/Cloud
        
        We are looking for a Senior Software Engineer with expertise in Python 
        development, cloud technologies, and team leadership. 
        
        Requirements:
        - 5+ years Python development experience
        - Experience with Docker, Kubernetes, AWS
        - CI/CD pipeline implementation
        - Team leadership and mentoring experience
        - Strong problem-solving skills
        
        Preferred:
        - Microservices architecture experience
        - Git version control
        - JavaScript knowledge
        """
        
        self.test_case = TestCase(
            name="Test Resume Optimization",
            resume_content=self.before_resume,
            job_description=self.job_description,
            expected_match_score=85.0
        )
        
        self.optimization_output = {
            'resume_before': self.before_resume,
            'resume_after': self.after_resume,
            'job_description': self.job_description,
            'optimization_details': {
                'changes_made': ['Enhanced summary section', 'Added technical skills', 'Quantified achievements']
            }
        }
    
    @pytest.mark.asyncio
    async def test_evaluator_initialization(self):
        """Test evaluator initialization with config."""
        config = {
            "min_score_improvement": 0.1,
            "keyword_weight": 0.5,
            "semantic_weight": 0.5
        }
        evaluator = RelevanceImpactEvaluator(config)
        
        assert evaluator.name == "relevance_impact"
        assert evaluator.min_score_improvement == 0.1
        assert evaluator.keyword_weight == 0.5
        assert evaluator.semantic_weight == 0.5
    
    @pytest.mark.asyncio
    async def test_evaluate_successful_optimization(self):
        """Test evaluation of successful optimization."""
        result = await self.evaluator.evaluate(self.test_case, self.optimization_output)
        
        assert isinstance(result, EvaluationResult)
        assert result.test_case_id == self.test_case.id
        assert result.evaluator_name == "relevance_impact"
        assert result.overall_score > 0.6  # Should pass threshold
        assert result.passed is True
        
        # Check detailed scores
        assert "match_score_improvement" in result.detailed_scores
        assert "keyword_alignment_improvement" in result.detailed_scores
        assert "targeting_effectiveness" in result.detailed_scores
        
        # Check analysis data (passed through **kwargs)
        assert hasattr(result, 'analysis')
        assert "before_match_score" in result.analysis
        assert "after_match_score" in result.analysis
        assert "improvement_percentage" in result.analysis
    
    @pytest.mark.asyncio
    async def test_evaluate_with_missing_after_resume(self):
        """Test evaluation when optimized resume is missing."""
        invalid_output = {'resume_before': self.before_resume}
        
        result = await self.evaluator.evaluate(self.test_case, invalid_output)
        
        assert result.overall_score == 0.0
        assert result.passed is False
        assert "No optimized resume content found" in result.notes
    
    @pytest.mark.asyncio
    async def test_evaluate_with_fallback_data(self):
        """Test evaluation using fallback to test case data."""
        # Test case with optimized resume in ground truth
        test_case_with_gt = TestCase(
            name="Test with ground truth",
            resume_content=self.before_resume,
            job_description=self.job_description,
            ground_truth={'optimized_resume': self.after_resume}
        )
        
        result = await self.evaluator.evaluate(test_case_with_gt, "simple_output")
        
        assert result.overall_score > 0.0
        assert result.passed is True
    
    def test_extract_content_from_dict_output(self):
        """Test content extraction from dictionary output."""
        before, after, job = self.evaluator._extract_content(self.test_case, self.optimization_output)
        
        assert before == self.before_resume
        assert after == self.after_resume
        assert job == self.job_description
    
    def test_extract_content_fallback(self):
        """Test content extraction fallback to test case."""
        test_case = TestCase(
            name="Test",
            resume_content=self.before_resume,
            job_description=self.job_description,
            ground_truth={'optimized_resume': self.after_resume}
        )
        
        before, after, job = self.evaluator._extract_content(test_case, "string_output")
        
        assert before == self.before_resume
        assert after == self.after_resume
        assert job == self.job_description
    
    def test_calculate_match_improvement(self):
        """Test match score improvement calculation."""
        score = self.evaluator._calculate_match_improvement(
            self.before_resume, self.after_resume, self.job_description
        )
        
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should show improvement
    
    def test_calculate_match_improvement_no_before_score(self):
        """Test match improvement when before score is zero."""
        empty_resume = ""
        good_resume = "Python developer with AWS experience"
        job_desc = "Looking for Python developer with AWS skills"
        
        score = self.evaluator._calculate_match_improvement(empty_resume, good_resume, job_desc)
        
        assert score == 1.0  # Maximum score when starting from zero
    
    def test_calculate_keyword_alignment_improvement(self):
        """Test keyword alignment improvement calculation."""
        score = self.evaluator._calculate_keyword_alignment_improvement(
            self.before_resume, self.after_resume, self.job_description
        )
        
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should show improvement in keyword coverage
    
    def test_calculate_keyword_alignment_no_keywords(self):
        """Test keyword alignment with no extractable keywords."""
        job_desc = "A job posting with no technical terms."
        
        score = self.evaluator._calculate_keyword_alignment_improvement(
            self.before_resume, self.after_resume, job_desc
        )
        
        assert score == 0.5  # Neutral score when no keywords found
    
    def test_calculate_targeting_effectiveness(self):
        """Test targeting effectiveness calculation."""
        score = self.evaluator._calculate_targeting_effectiveness(
            self.before_resume, self.after_resume, self.job_description, self.optimization_output
        )
        
        assert 0.0 <= score <= 1.0
    
    def test_calculate_targeting_effectiveness_no_changes(self):
        """Test targeting effectiveness when no changes are made."""
        score = self.evaluator._calculate_targeting_effectiveness(
            self.before_resume, self.before_resume, self.job_description, {}
        )
        
        assert score == 0.0  # Should be zero when no changes made
    
    def test_calculate_section_improvements(self):
        """Test section-specific improvement calculation."""
        scores = self.evaluator._calculate_section_improvements(
            self.before_resume, self.after_resume, self.job_description
        )
        
        expected_sections = ['summary_improvement', 'experience_improvement', 
                           'skills_improvement', 'education_improvement']
        
        for section in expected_sections:
            assert section in scores
            assert 0.0 <= scores[section] <= 1.0
    
    def test_semantic_similarity_calculation(self):
        """Test semantic similarity calculation."""
        text1 = "Python developer with AWS experience"
        text2 = "Looking for Python developer with AWS skills"
        
        similarity = self.evaluator._calculate_semantic_similarity(text1, text2)
        
        assert 0.0 <= similarity <= 1.0
        assert similarity > 0  # Should have some overlap
    
    def test_semantic_similarity_no_overlap(self):
        """Test semantic similarity with no word overlap."""
        text1 = "completely different words"
        text2 = "no matching terms here"
        
        similarity = self.evaluator._calculate_semantic_similarity(text1, text2)
        
        assert similarity == 0.0
    
    def test_extract_keywords(self):
        """Test keyword extraction from job description."""
        keywords = self.evaluator._extract_keywords(self.job_description)
        
        assert isinstance(keywords, list)
        assert len(keywords) > 0
        
        # Should contain technical keywords
        expected_keywords = ['python', 'docker', 'kubernetes', 'aws']
        for keyword in expected_keywords:
            assert keyword in keywords
    
    def test_extract_keywords_empty_text(self):
        """Test keyword extraction from empty text."""
        keywords = self.evaluator._extract_keywords("")
        
        assert keywords == []
    
    def test_calculate_keyword_coverage(self):
        """Test keyword coverage calculation."""
        keywords = ['python', 'docker', 'aws', 'kubernetes']
        
        before_coverage = self.evaluator._calculate_keyword_coverage(self.before_resume, keywords)
        after_coverage = self.evaluator._calculate_keyword_coverage(self.after_resume, keywords)
        
        assert after_coverage > before_coverage  # Should improve coverage
        assert before_coverage >= 0
        assert after_coverage <= len(keywords)
    
    def test_identify_changes(self):
        """Test change identification between resumes."""
        changes = self.evaluator._identify_changes(self.before_resume, self.after_resume)
        
        assert isinstance(changes, list)
        assert len(changes) > 0
        
        # Check change structure
        for change in changes:
            assert 'line' in change
            assert 'type' in change
            assert change['type'] in ['modification', 'addition']
    
    def test_identify_changes_no_changes(self):
        """Test change identification when no changes are made."""
        changes = self.evaluator._identify_changes(self.before_resume, self.before_resume)
        
        assert changes == []
    
    def test_is_change_relevant(self):
        """Test relevance determination for changes."""
        keywords = ['python', 'docker', 'leadership']
        
        relevant_change = {
            'before': 'Developer',
            'after': 'Python Developer with Docker experience',
            'type': 'modification'
        }
        
        irrelevant_change = {
            'before': 'John',
            'after': 'Jonathan',
            'type': 'modification'
        }
        
        assert self.evaluator._is_change_relevant(relevant_change, keywords) is True
        assert self.evaluator._is_change_relevant(irrelevant_change, keywords) is False
    
    def test_extract_section(self):
        """Test resume section extraction."""
        summary = self.evaluator._extract_section(self.after_resume, 'summary')
        skills = self.evaluator._extract_section(self.after_resume, 'skills')
        
        assert 'Senior Software Engineer' in summary
        assert 'Python' in skills
        assert 'Docker' in skills
    
    def test_extract_section_not_found(self):
        """Test section extraction when section doesn't exist."""
        section = self.evaluator._extract_section(self.before_resume, 'certifications')
        
        assert section == ""
    
    def test_generate_analysis(self):
        """Test analysis generation."""
        analysis = self.evaluator._generate_analysis(
            self.before_resume, self.after_resume, self.job_description, self.optimization_output
        )
        
        required_keys = [
            'summary', 'before_match_score', 'after_match_score', 
            'improvement_percentage', 'keyword_coverage_before', 
            'keyword_coverage_after', 'recommendations'
        ]
        
        for key in required_keys:
            assert key in analysis
        
        assert isinstance(analysis['recommendations'], dict)
        assert analysis['after_match_score'] >= analysis['before_match_score']
    
    def test_generate_recommendations(self):
        """Test recommendation generation."""
        recommendations = self.evaluator._generate_recommendations(
            self.before_resume, self.after_resume, self.job_description
        )
        
        required_keys = [
            'focus_areas', 'missing_keywords', 'keyword_coverage_percentage', 
            'improvement_suggestions'
        ]
        
        for key in required_keys:
            assert key in recommendations
        
        assert isinstance(recommendations['focus_areas'], list)
        assert isinstance(recommendations['missing_keywords'], list)
        assert isinstance(recommendations['improvement_suggestions'], list)
        assert 0 <= recommendations['keyword_coverage_percentage'] <= 100
    
    def test_get_description(self):
        """Test evaluator description."""
        description = self.evaluator.get_description()
        
        assert isinstance(description, str)
        assert len(description) > 0
        assert "relevance" in description.lower()
        assert "improve" in description.lower()
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling during evaluation."""
        # Create evaluator with method that will raise an exception
        evaluator = RelevanceImpactEvaluator()
        
        # Mock a method to raise an exception
        with patch.object(evaluator, '_extract_content', side_effect=Exception("Test error")):
            result = await evaluator.evaluate(self.test_case, self.optimization_output)
            
            assert result.overall_score == 0.0
            assert result.passed is False
            assert "Test error" in result.notes
            assert result.error_message == "Test error"
    
    @pytest.mark.asyncio
    async def test_performance_tracking(self):
        """Test that performance metrics are tracked."""
        result = await self.evaluator.evaluate(self.test_case, self.optimization_output)
        
        assert result.execution_time > 0
        assert result.api_calls_made == 0  # No external API calls
        assert result.tokens_used == 0  # No LLM usage


class TestRelevanceImpactEvaluatorEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.evaluator = RelevanceImpactEvaluator()
    
    @pytest.mark.asyncio
    async def test_empty_resume_content(self):
        """Test handling of empty resume content."""
        test_case = TestCase(
            name="Empty resume test",
            resume_content="",
            job_description="Looking for Python developer"
        )
        
        output = {
            'resume_before': "",
            'resume_after': "Python Developer",
            'job_description': "Looking for Python developer"
        }
        
        result = await self.evaluator.evaluate(test_case, output)
        
        assert result.overall_score >= 0.0
        assert isinstance(result, EvaluationResult)
    
    @pytest.mark.asyncio
    async def test_identical_before_after_resumes(self):
        """Test when before and after resumes are identical."""
        resume_content = "Software Developer with Python experience"
        test_case = TestCase(
            name="No change test",
            resume_content=resume_content,
            job_description="Looking for Python developer"
        )
        
        output = {
            'resume_before': resume_content,
            'resume_after': resume_content,
            'job_description': "Looking for Python developer"
        }
        
        result = await self.evaluator.evaluate(test_case, output)
        
        # Should still work but with low targeting effectiveness
        assert result.overall_score >= 0.0
        assert result.detailed_scores['targeting_effectiveness'] == 0.0
    
    @pytest.mark.asyncio
    async def test_very_long_content(self):
        """Test handling of very long resume and job description content."""
        long_resume = "Software Developer. " * 1000  # Very long content
        long_job_desc = "Looking for developer with experience. " * 500
        
        test_case = TestCase(
            name="Long content test",
            resume_content=long_resume,
            job_description=long_job_desc
        )
        
        output = {
            'resume_before': long_resume,
            'resume_after': long_resume + " Python expert.",
            'job_description': long_job_desc
        }
        
        result = await self.evaluator.evaluate(test_case, output)
        
        assert isinstance(result, EvaluationResult)
        assert result.execution_time > 0  # Should complete in reasonable time
    
    def test_keyword_extraction_special_characters(self):
        """Test keyword extraction with special characters."""
        job_desc = "Looking for C++ developer with .NET experience and API design skills!"
        
        keywords = self.evaluator._extract_keywords(job_desc)
        
        assert isinstance(keywords, list)
        # Should handle special characters gracefully
    
    def test_section_extraction_malformed_resume(self):
        """Test section extraction from malformed resume."""
        malformed_resume = """
        Name without proper sections
        Random text here
        SKILLS but no proper formatting
        More random content
        """
        
        summary = self.evaluator._extract_section(malformed_resume, 'summary')
        skills = self.evaluator._extract_section(malformed_resume, 'skills')
        
        # Should handle gracefully without crashing
        assert isinstance(summary, str)
        assert isinstance(skills, str)


class TestRelevanceImpactEvaluatorConfiguration:
    """Test evaluator configuration options."""
    
    def test_custom_configuration(self):
        """Test evaluator with custom configuration."""
        config = {
            "min_score_improvement": 0.2,
            "keyword_weight": 0.7,
            "semantic_weight": 0.3
        }
        
        evaluator = RelevanceImpactEvaluator(config)
        
        assert evaluator.min_score_improvement == 0.2
        assert evaluator.keyword_weight == 0.7
        assert evaluator.semantic_weight == 0.3
    
    def test_default_configuration(self):
        """Test evaluator with default configuration."""
        evaluator = RelevanceImpactEvaluator()
        
        assert evaluator.min_score_improvement == 0.05
        assert evaluator.keyword_weight == 0.4
        assert evaluator.semantic_weight == 0.6
    
    def test_none_configuration(self):
        """Test evaluator with None configuration."""
        evaluator = RelevanceImpactEvaluator(None)
        
        assert evaluator.min_score_improvement == 0.05
        assert evaluator.keyword_weight == 0.4
        assert evaluator.semantic_weight == 0.6