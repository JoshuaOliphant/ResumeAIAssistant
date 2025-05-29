# ABOUTME: Unit tests for MatchScoreEvaluator implementation
# ABOUTME: Tests correlation, consistency, transferable skills, experience alignment, bias, and distribution analysis

"""
Test Match Score Evaluator

Tests for the MatchScoreEvaluator implementation that evaluates the reliability 
and consistency of resume-job match scoring.
"""

import pytest
from unittest.mock import MagicMock, patch
from evaluation.evaluators.accuracy import MatchScoreEvaluator, MatchScoreEvaluatorConfig
from evaluation.test_data.models import TestCase


@pytest.fixture
def evaluator():
    """Create a MatchScoreEvaluator instance."""
    return MatchScoreEvaluator()


@pytest.fixture
def test_case():
    """Create a basic test case."""
    return TestCase(
        name="Test Case",
        resume_content="Senior Software Engineer with 8 years experience in Python and AWS",
        job_description="Looking for Senior Software Engineer with Python and cloud experience",
        expected_match_score=85.0
    )


@pytest.mark.asyncio
async def test_evaluator_initialization(evaluator):
    """Test evaluator initializes correctly."""
    assert evaluator.name == "match_score"
    assert isinstance(evaluator.evaluator_config, MatchScoreEvaluatorConfig)
    assert evaluator.consistency_cache == {}


@pytest.mark.asyncio
async def test_evaluate_with_numeric_score(evaluator, test_case):
    """Test evaluation with numeric actual output."""
    actual_output = 90.0
    result = await evaluator.evaluate(test_case, actual_output)
    
    assert result.overall_score > 0
    assert result.passed
    assert "correlation_analysis" in result.detailed_scores
    assert "consistency_analysis" in result.detailed_scores
    assert "transferable_skills" in result.detailed_scores
    assert "experience_alignment" in result.detailed_scores
    assert "bias_analysis" in result.detailed_scores
    assert "distribution_analysis" in result.detailed_scores


@pytest.mark.asyncio
async def test_evaluate_with_dict_output(evaluator, test_case):
    """Test evaluation with dictionary actual output."""
    actual_output = {"match_score": 80.0, "confidence": 0.9}
    result = await evaluator.evaluate(test_case, actual_output)
    
    assert result.overall_score > 0
    assert result.passed


@pytest.mark.asyncio
async def test_evaluate_missing_score(evaluator, test_case):
    """Test evaluation with missing match score."""
    actual_output = {"confidence": 0.9}  # No match_score
    result = await evaluator.evaluate(test_case, actual_output)
    
    assert result.overall_score == 0.0
    assert not result.passed
    assert "Missing match score data" in result.error_message


@pytest.mark.asyncio
async def test_correlation_analysis_excellent(evaluator, test_case):
    """Test correlation analysis with excellent match."""
    # Score within 5 points (half of max diff)
    actual_score = 87.0
    expected_score = 85.0
    
    analysis = await evaluator._analyze_correlation(test_case, actual_score, expected_score)
    
    assert analysis["score"] == 1.0
    assert analysis["assessment"] == "Excellent correlation"
    assert analysis["score_difference"] == 2.0


@pytest.mark.asyncio
async def test_correlation_analysis_poor(evaluator, test_case):
    """Test correlation analysis with poor match."""
    # Score difference > 20 points
    actual_score = 30.0
    expected_score = 85.0
    
    analysis = await evaluator._analyze_correlation(test_case, actual_score, expected_score)
    
    assert analysis["score"] < 0.5
    assert analysis["assessment"] == "Poor correlation"


@pytest.mark.asyncio
async def test_consistency_analysis_first_evaluation(evaluator, test_case):
    """Test consistency analysis on first evaluation."""
    actual_score = 85.0
    
    analysis = await evaluator._analyze_consistency(test_case, actual_score)
    
    assert analysis["score"] == 1.0
    assert analysis["evaluations"] == 1
    assert "Insufficient data" in analysis["assessment"]


@pytest.mark.asyncio
async def test_consistency_analysis_multiple_evaluations(evaluator, test_case):
    """Test consistency analysis with multiple evaluations."""
    # Simulate multiple evaluations
    scores = [85.0, 84.0, 86.0]
    
    for score in scores:
        await evaluator._analyze_consistency(test_case, score)
    
    # Get final analysis
    analysis = await evaluator._analyze_consistency(test_case, 85.0)
    
    assert analysis["evaluations"] == 4  # 3 previous + 1 current
    assert analysis["score"] > 0.8  # Should be highly consistent
    assert "consistent" in analysis["assessment"].lower()


@pytest.mark.asyncio
async def test_transferable_skills_recognition(evaluator):
    """Test transferable skills analysis."""
    test_case = TestCase(
        name="Transferable Skills Test",
        resume_content="Experience with Azure cloud platform and React frontend",
        job_description="Looking for AWS cloud expert and Angular developer",
        expected_match_score=70.0
    )
    
    analysis = await evaluator._analyze_transferable_skills(test_case)
    
    assert analysis["total_transferable"] == 2  # AWS and Angular in job
    assert analysis["transferable_matches"] == 2  # Azure->AWS, React->Angular
    assert analysis["score"] == 1.0
    assert len(analysis["matched_skills"]) == 2


@pytest.mark.asyncio
async def test_experience_alignment_perfect(evaluator):
    """Test experience alignment with perfect match."""
    test_case = TestCase(
        name="Experience Test",
        resume_content="Senior Software Engineer with 8 years experience",
        job_description="Looking for Senior Software Engineer",
        expected_match_score=90.0
    )
    
    analysis = await evaluator._analyze_experience_alignment(test_case)
    
    assert analysis["score"] == 1.0
    assert analysis["resume_level"] == "senior"
    assert analysis["job_level"] == "senior"
    assert analysis["level_difference"] == 0


@pytest.mark.asyncio
async def test_experience_alignment_mismatch(evaluator):
    """Test experience alignment with mismatch."""
    test_case = TestCase(
        name="Experience Mismatch",
        resume_content="Junior Developer with 1 year experience",
        job_description="Looking for Principal Engineer",
        expected_match_score=30.0
    )
    
    analysis = await evaluator._analyze_experience_alignment(test_case)
    
    assert analysis["score"] < 0.5
    assert analysis["resume_level"] == "junior"
    assert analysis["job_level"] == "principal"
    assert analysis["level_difference"] > 3


@pytest.mark.asyncio
async def test_bias_detection_extreme_score(evaluator, test_case):
    """Test bias detection with extreme scores."""
    # Test extreme low score
    analysis = await evaluator._analyze_bias(test_case, 10.0)
    
    assert analysis["score"] < 1.0
    assert analysis["is_extreme"]
    assert "extreme range" in str(analysis["bias_indicators"])
    
    # Test extreme high score
    analysis = await evaluator._analyze_bias(test_case, 95.0)
    
    assert analysis["score"] < 1.0
    assert analysis["is_extreme"]


@pytest.mark.asyncio
async def test_bias_detection_round_numbers(evaluator, test_case):
    """Test bias detection with round numbers."""
    # Test round number bias
    analysis = await evaluator._analyze_bias(test_case, 50.0)
    
    assert "Round number bias" in analysis["bias_indicators"]
    assert "Quarter-point bias" in analysis["bias_indicators"]
    assert analysis["score"] < 1.0


@pytest.mark.asyncio
async def test_distribution_analysis_normal(evaluator, test_case):
    """Test distribution analysis with normal range score."""
    analysis = await evaluator._analyze_distribution(test_case, 55.0)
    
    assert analysis["score"] == 1.0
    assert "normal distribution" in analysis["assessment"]
    assert analysis["percentile_estimate"] == 50.0


@pytest.mark.asyncio
async def test_distribution_analysis_extreme(evaluator, test_case):
    """Test distribution analysis with extreme score."""
    analysis = await evaluator._analyze_distribution(test_case, 5.0)
    
    assert analysis["score"] < 0.5
    assert "extreme" in analysis["assessment"]
    assert analysis["percentile_estimate"] == 5.0


@pytest.mark.asyncio
async def test_skill_extraction(evaluator):
    """Test skill extraction from text."""
    text = """
    Looking for a developer with Python, JavaScript, and React experience.
    Must have AWS cloud experience and Docker containerization skills.
    Knowledge of PostgreSQL and MongoDB databases required.
    """
    
    skills = evaluator._extract_skills(text)
    
    assert "python" in skills
    assert "javascript" in skills
    assert "react" in skills
    assert "aws" in skills
    assert "docker" in skills
    assert "postgresql" in skills
    assert "mongodb" in skills


@pytest.mark.asyncio
async def test_experience_level_extraction(evaluator):
    """Test experience level extraction."""
    # Test senior level
    text = "Senior Software Engineer position"
    assert evaluator._extract_experience_level(text) == "senior"
    
    # Test junior level
    text = "Entry-level developer role"
    assert evaluator._extract_experience_level(text) == "junior"
    
    # Test by years
    text = "Requires 10+ years of experience"
    assert evaluator._extract_experience_level(text) == "senior"
    
    # Test principal/staff
    text = "Principal Engineer opportunity"
    assert evaluator._extract_experience_level(text) == "principal"


@pytest.mark.asyncio
async def test_weighted_score_calculation(evaluator):
    """Test weighted score calculation."""
    analyses = {
        "correlation_analysis": {"score": 0.9},
        "consistency_analysis": {"score": 0.8},
        "transferable_skills": {"score": 0.7},
        "experience_alignment": {"score": 0.6},
        "bias_analysis": {"score": 1.0},
        "distribution_analysis": {"score": 0.8}
    }
    
    score = evaluator._calculate_weighted_score(analyses)
    
    # Verify it's a weighted average
    assert 0 <= score <= 1.0
    # With these scores and default weights, should be around 0.79
    assert 0.75 <= score <= 0.85


@pytest.mark.asyncio
async def test_generate_notes(evaluator):
    """Test note generation."""
    analyses = {
        "correlation_analysis": {
            "score": 0.9,
            "assessment": "Excellent correlation"
        },
        "consistency_analysis": {
            "score": 0.8,
            "assessment": "Good consistency",
            "evaluations": 3
        },
        "transferable_skills": {
            "score": 0.7,
            "assessment": "Good transferable skill recognition",
            "matched_skills": ["Python → Java", "AWS → Azure"]
        },
        "experience_alignment": {
            "score": 1.0,
            "assessment": "Perfect experience alignment"
        },
        "bias_analysis": {
            "score": 0.9,
            "assessment": "No significant bias detected",
            "bias_indicators": []
        },
        "distribution_analysis": {
            "score": 1.0,
            "assessment": "Score within normal distribution"
        }
    }
    
    notes = evaluator._generate_notes(analyses, 85.0, 80.0)
    
    assert "Actual=85.0" in notes
    assert "Expected=80.0" in notes
    assert "Correlation Analysis: 90%" in notes
    assert "Consistency: Evaluated 3 times" in notes
    assert "Transferable Skills Found:" in notes


@pytest.mark.asyncio
async def test_error_handling(evaluator, test_case):
    """Test error handling in evaluation."""
    # Simulate an error by passing invalid input
    with patch.object(evaluator, '_extract_match_score', side_effect=Exception("Test error")):
        result = await evaluator.evaluate(test_case, 85.0)
        
        assert result.overall_score == 0.0
        assert not result.passed
        assert "Test error" in result.error_message


@pytest.mark.asyncio
async def test_consistency_fallback_statistics(evaluator, test_case):
    """Test consistency analysis with fallback statistics when numpy is not available."""
    # Mock ImportError for numpy
    with patch('builtins.__import__', side_effect=ImportError("No module named 'numpy'")):
        # Add multiple scores
        evaluator.consistency_cache["test_key"] = [85.0, 84.0, 86.0]
        test_case.resume_content = "test"
        test_case.job_description = "key"
        
        analysis = await evaluator._analyze_consistency(test_case, 85.0)
        
        # Verify fallback calculation worked
        assert "score" in analysis
        assert "std_deviation" in analysis
        assert "coefficient_of_variation" in analysis
        assert analysis["evaluations"] == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])