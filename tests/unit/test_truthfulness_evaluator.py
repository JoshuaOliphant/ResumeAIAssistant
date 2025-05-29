# ABOUTME: Unit tests for TruthfulnessEvaluator class
# ABOUTME: Tests fabrication detection, entity consistency, and scoring algorithms
"""
TruthfulnessEvaluator Tests

Comprehensive unit tests for the TruthfulnessEvaluator class, covering
fabrication detection, entity consistency, numerical integrity, and scoring.
"""

import pytest
from unittest.mock import Mock, patch
from evaluation.evaluators.quality import TruthfulnessEvaluator
from evaluation.test_data.models import TestCase, EvaluationResult


class TestTruthfulnessEvaluator:
    """Test suite for TruthfulnessEvaluator."""
    
    @pytest.fixture
    def evaluator(self):
        """Create a TruthfulnessEvaluator instance for testing."""
        config = {"min_truthfulness_score": 0.7}
        return TruthfulnessEvaluator(config)
    
    @pytest.fixture
    def sample_test_case(self):
        """Create a sample test case for testing."""
        return TestCase(
            name="Sample Test Case",
            resume_content="""
            John Doe
            Software Engineer at TechCorp
            Skills: Python, JavaScript, SQL
            Experience: 5 years developing web applications
            Increased team productivity by 20%
            Led a team of 3 developers
            """,
            job_description="Looking for a Senior Python Developer with 5+ years experience"
        )
    
    @pytest.mark.asyncio
    async def test_evaluate_basic_functionality(self, evaluator, sample_test_case):
        """Test basic evaluation functionality."""
        actual_output = {
            'original_content': sample_test_case.resume_content,
            'optimized_content': """
            John Doe
            Senior Software Engineer at TechCorp
            Skills: Python, JavaScript, SQL, Django
            Experience: 5 years developing scalable web applications
            Improved team productivity by 20%
            Led a team of 3 developers on critical projects
            """
        }
        
        result = await evaluator.evaluate(sample_test_case, actual_output)
        
        assert isinstance(result, EvaluationResult)
        assert result.test_case_id == sample_test_case.id
        assert result.evaluator_name == "truthfulness"
        assert 0.0 <= result.overall_score <= 1.0
        assert result.execution_time > 0
        
        # Check detailed scores
        expected_metrics = ["content_similarity", "entity_consistency", "numerical_integrity", "skill_authenticity", "fabrication_risk"]
        for metric in expected_metrics:
            assert metric in result.detailed_scores
            assert 0.0 <= result.detailed_scores[metric] <= 1.0
    
    @pytest.mark.asyncio
    async def test_evaluate_no_optimized_content(self, evaluator, sample_test_case):
        """Test evaluation with no optimized content."""
        actual_output = {'optimized_content': ''}
        
        result = await evaluator.evaluate(sample_test_case, actual_output)
        
        assert result.overall_score == 0.0
        assert not result.passed
        assert "No optimized content provided" in result.notes
    
    def test_content_similarity_calculation(self, evaluator):
        """Test content similarity calculation."""
        original = "John Doe is a Python developer with 5 years experience"
        optimized = "John Doe is an experienced Python developer with 5 years of experience"
        
        similarity = evaluator._calculate_content_similarity(original, optimized)
        
        assert 0.0 <= similarity <= 1.0
        assert similarity > 0.5  # Should be similar content
    
    def test_content_similarity_fallback(self, evaluator):
        """Test content similarity with no vectorizer (fallback mode)."""
        # Temporarily disable vectorizer to test fallback
        original_vectorizer = evaluator.vectorizer
        evaluator.vectorizer = None
        
        try:
            original = "Python developer"
            optimized = "Python developer with experience"
            
            similarity = evaluator._calculate_content_similarity(original, optimized)
            
            assert 0.0 <= similarity <= 1.0
        finally:
            evaluator.vectorizer = original_vectorizer
    
    def test_entity_consistency_no_nlp(self, evaluator):
        """Test entity consistency when NLP model is not available."""
        # Temporarily disable NLP model
        original_nlp = evaluator.nlp
        evaluator.nlp = None
        
        try:
            original = "John worked at Microsoft"
            optimized = "John worked at Google"
            
            result = evaluator._analyze_entity_consistency(original, optimized)
            
            assert result["consistency_score"] == 1.0
            assert len(result["violations"]) == 0
        finally:
            evaluator.nlp = original_nlp
    
    @patch('spacy.load')
    def test_entity_consistency_new_organizations(self, mock_spacy, evaluator):
        """Test detection of new organizations."""
        # Mock spaCy entities
        mock_doc_orig = Mock()
        mock_doc_opt = Mock()
        
        mock_ent_orig = Mock()
        mock_ent_orig.text = "TechCorp"
        mock_ent_orig.label_ = "ORG"
        
        mock_ent_new = Mock()
        mock_ent_new.text = "NewCorp"
        mock_ent_new.label_ = "ORG"
        
        mock_doc_orig.ents = [mock_ent_orig]
        mock_doc_opt.ents = [mock_ent_orig, mock_ent_new]
        
        evaluator.nlp = Mock()
        evaluator.nlp.side_effect = [mock_doc_orig, mock_doc_opt]
        
        original = "Worked at TechCorp"
        optimized = "Worked at TechCorp and NewCorp"
        
        result = evaluator._analyze_entity_consistency(original, optimized)
        
        assert result["consistency_score"] < 1.0
        assert len(result["violations"]) > 0
        assert result["violations"][0]["type"] == "new_organizations"
        assert "newcorp" in result["violations"][0]["entities"]
    
    def test_numerical_integrity_inflation(self, evaluator):
        """Test detection of numerical inflation."""
        original = "Increased sales by 10%"
        optimized = "Increased sales by 50%"
        
        result = evaluator._analyze_numerical_integrity(original, optimized)
        
        assert result["integrity_score"] < 1.0
        assert len(result["violations"]) > 0
        assert result["violations"][0]["type"] == "numerical_inflation"
    
    def test_numerical_integrity_no_inflation(self, evaluator):
        """Test no detection when numbers are reasonable."""
        original = "Managed a team of 5 developers for 3 years"
        optimized = "Led a team of 5 developers for 3 years with great success"
        
        result = evaluator._analyze_numerical_integrity(original, optimized)
        
        assert result["integrity_score"] == 1.0
        assert len(result["violations"]) == 0
    
    def test_normalize_number(self, evaluator):
        """Test number normalization."""
        assert evaluator._normalize_number("100") == 100.0
        assert evaluator._normalize_number("10k") == 10000.0
        assert evaluator._normalize_number("1M") == 1000000.0
        assert evaluator._normalize_number("50%") == 50.0
        assert evaluator._normalize_number("invalid") is None
    
    def test_skill_authenticity_new_skills(self, evaluator):
        """Test detection of new technical skills."""
        original = "Experience with Python and SQL"
        optimized = "Experience with Python, SQL, and machine learning"
        
        result = evaluator._analyze_skill_authenticity(original, optimized)
        
        assert result["authenticity_score"] < 1.0
        assert len(result["violations"]) > 0
        assert result["violations"][0]["type"] == "new_technical_skills"
        assert "machine learning" in result["violations"][0]["skills"]
    
    def test_skill_authenticity_no_new_skills(self, evaluator):
        """Test no detection when skills are existing."""
        original = "Experience with Python, JavaScript, and React"
        optimized = "Strong experience with Python, JavaScript, and React frameworks"
        
        result = evaluator._analyze_skill_authenticity(original, optimized)
        
        assert result["authenticity_score"] == 1.0
        assert len(result["violations"]) == 0
    
    def test_change_summary_generation(self, evaluator):
        """Test change summary generation."""
        original = "Line one\nLine two\nLine three"
        optimized = "Line one\nModified line two\nLine three\nNew line four"
        
        summary = evaluator._generate_change_summary(original, optimized)
        
        assert "total_changes" in summary
        assert "additions" in summary
        assert "deletions" in summary
        assert "modification_ratio" in summary
        assert summary["total_changes"] > 0
    
    def test_fabrication_confidence_calculation(self, evaluator):
        """Test fabrication confidence calculation."""
        analysis_results = {
            "violations": [
                {"confidence": 0.8, "type": "test1"},
                {"confidence": 0.6, "type": "test2"},
                {"confidence": 0.9, "type": "test3"}
            ]
        }
        
        confidence = evaluator._calculate_fabrication_confidence(analysis_results)
        
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.0  # Should have some confidence with violations
    
    def test_fabrication_confidence_no_violations(self, evaluator):
        """Test fabrication confidence with no violations."""
        analysis_results = {"violations": []}
        
        confidence = evaluator._calculate_fabrication_confidence(analysis_results)
        
        assert confidence == 0.0
    
    def test_overall_score_calculation(self, evaluator):
        """Test overall score calculation."""
        analysis_results = {
            "content_similarity": 0.8,
            "entity_consistency": 0.9,
            "numerical_integrity": 0.7,
            "skill_authenticity": 0.85
        }
        
        score = evaluator._calculate_overall_score(analysis_results)
        
        assert 0.0 <= score <= 1.0
        # Should be weighted average of input scores
        expected = (0.8 * 0.3 + 0.9 * 0.25 + 0.7 * 0.25 + 0.85 * 0.2)
        assert abs(score - expected) < 0.01
    
    def test_evaluation_notes_generation(self, evaluator):
        """Test evaluation notes generation."""
        analysis_results = {
            "fabrication_confidence": 0.4,
            "violations": [
                {
                    "type": "new_organizations",
                    "confidence": 0.8,
                    "details": "Found new company XYZ"
                }
            ],
            "change_summary": {
                "additions": 5,
                "deletions": 2
            }
        }
        
        notes = evaluator._generate_evaluation_notes(analysis_results)
        
        assert "Moderate fabrication risk" in notes
        assert "Violations found (1)" in notes
        assert "new_organizations" in notes
        assert "Content changes: 5 additions, 2 deletions" in notes
    
    def test_get_description(self, evaluator):
        """Test evaluator description."""
        description = evaluator.get_description()
        
        assert "truthfulness" in description.lower()
        assert "content similarity" in description.lower()
        assert "entity consistency" in description.lower()
    
    @pytest.mark.asyncio
    async def test_high_fabrication_scenario(self, evaluator, sample_test_case):
        """Test scenario with high fabrication risk."""
        actual_output = {
            'original_content': sample_test_case.resume_content,
            'optimized_content': """
            John Doe
            Senior Software Engineer at Google and Microsoft
            Skills: Python, JavaScript, SQL, Machine Learning, AI, Blockchain
            Experience: 10 years developing enterprise applications
            Increased team productivity by 500%
            Led a team of 50 developers
            Won Nobel Prize in Computer Science
            """
        }
        
        result = await evaluator.evaluate(sample_test_case, actual_output)
        
        # Should detect multiple violations
        assert result.overall_score < 0.7
        assert not result.passed
        # Check that some violations were detected (even without full NLP)
        assert "fabrication" in result.notes.lower() or "violations" in result.notes.lower()
    
    @pytest.mark.asyncio 
    async def test_safe_optimization_scenario(self, evaluator, sample_test_case):
        """Test scenario with safe optimizations."""
        actual_output = {
            'original_content': sample_test_case.resume_content,
            'optimized_content': """
            John Doe
            Experienced Software Engineer at TechCorp
            Technical Skills: Python, JavaScript, SQL
            Professional Experience: 5 years developing robust web applications
            Successfully increased team productivity by 20%
            Effectively led a team of 3 developers
            """
        }
        
        result = await evaluator.evaluate(sample_test_case, actual_output)
        
        # Should pass with minor rephrasing
        assert result.overall_score >= 0.7
        assert result.passed
        assert result.detailed_scores["content_similarity"] > 0.5  # Lowered threshold


class TestTruthfulnessEvaluatorEdgeCases:
    """Test edge cases and error conditions."""
    
    @pytest.fixture
    def evaluator(self):
        """Create evaluator for edge case testing."""
        return TruthfulnessEvaluator()
    
    @pytest.mark.asyncio
    async def test_empty_content(self, evaluator):
        """Test with empty content."""
        test_case = TestCase(
            name="Empty Test",
            resume_content="",
            job_description="Test job"
        )
        
        actual_output = {
            'original_content': "",
            'optimized_content': ""
        }
        
        result = await evaluator.evaluate(test_case, actual_output)
        
        assert result.overall_score == 0.0
        assert not result.passed
    
    @pytest.mark.asyncio
    async def test_invalid_input_format(self, evaluator):
        """Test with invalid input format."""
        test_case = TestCase(
            name="Invalid Test",
            resume_content="Test content",
            job_description="Test job"
        )
        
        # Pass string instead of dict
        actual_output = "Just a string"
        
        result = await evaluator.evaluate(test_case, actual_output)
        
        # Should handle gracefully
        assert isinstance(result, EvaluationResult)
    
    def test_setup_without_dependencies(self):
        """Test setup when NLP dependencies are missing."""
        with patch('spacy.load', side_effect=ImportError("spacy not found")):
            evaluator = TruthfulnessEvaluator()
            
            # Should still create evaluator but with limited functionality
            assert evaluator.nlp is None
            # vectorizer might still be available from sklearn