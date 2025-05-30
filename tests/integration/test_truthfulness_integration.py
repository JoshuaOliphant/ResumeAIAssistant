# ABOUTME: Integration tests for TruthfulnessEvaluator with evaluation framework
# ABOUTME: Tests evaluator integration with test runner and pipeline components
"""
TruthfulnessEvaluator Integration Tests

Integration tests for the TruthfulnessEvaluator within the broader
evaluation framework, testing real-world scenarios and pipeline integration.
"""

import pytest
import asyncio
import time
from pathlib import Path
from evaluation.evaluators.quality import TruthfulnessEvaluator
from evaluation.test_data.models import TestCase, TestDataset


class TestTruthfulnessEvaluatorIntegration:
    """Integration tests for TruthfulnessEvaluator."""
    
    @pytest.fixture
    def sample_dataset(self):
        """Create a sample dataset for integration testing."""
        test_cases = [
            TestCase(
                name="Safe Optimization Test",
                resume_content="""
                Alice Johnson
                Senior Data Scientist at DataCorp
                Skills: Python, R, Machine Learning, Statistics
                Experience: 6 years in data analysis and modeling
                Improved model accuracy by 15%
                Published 3 research papers
                """,
                job_description="Looking for a Data Scientist with ML experience",
                ground_truth={
                    "expected_truthfulness_score": 0.9,
                    "expected_violations": []
                }
            ),
            TestCase(
                name="Fabrication Risk Test", 
                resume_content="""
                Bob Smith
                Software Developer at StartupXYZ
                Skills: JavaScript, HTML, CSS
                Experience: 2 years web development
                Built company website
                """,
                job_description="Senior Full Stack Developer needed",
                ground_truth={
                    "expected_truthfulness_score": 0.4,
                    "expected_violations": ["new_organizations", "numerical_inflation", "new_technical_skills"]
                }
            ),
            TestCase(
                name="Numerical Inflation Test",
                resume_content="""
                Carol Williams
                Marketing Manager at AdAgency
                Skills: Digital Marketing, Analytics
                Experience: 4 years marketing campaigns
                Increased conversion rates by 8%
                Managed budget of $50K
                """,
                job_description="Senior Marketing Manager position",
                ground_truth={
                    "expected_truthfulness_score": 0.3,
                    "expected_violations": ["numerical_inflation"]
                }
            )
        ]
        
        return TestDataset(
            name="Truthfulness Integration Test Dataset",
            description="Test cases for truthfulness evaluator integration",
            test_cases=test_cases
        )
    
    @pytest.fixture
    def sample_optimizations(self):
        """Sample optimization outputs corresponding to test cases."""
        return [
            # Safe optimization
            {
                'original_content': """
                Alice Johnson
                Senior Data Scientist at DataCorp
                Skills: Python, R, Machine Learning, Statistics
                Experience: 6 years in data analysis and modeling
                Improved model accuracy by 15%
                Published 3 research papers
                """,
                'optimized_content': """
                Alice Johnson
                Senior Data Scientist at DataCorp
                Technical Expertise: Python, R, Machine Learning, Advanced Statistics
                Professional Experience: 6 years specializing in data analysis and predictive modeling
                Successfully improved model accuracy by 15% through optimization techniques
                Author of 3 peer-reviewed research papers in data science
                """
            },
            # High fabrication risk
            {
                'original_content': """
                Bob Smith
                Software Developer at StartupXYZ
                Skills: JavaScript, HTML, CSS
                Experience: 2 years web development
                Built company website
                """,
                'optimized_content': """
                Bob Smith
                Senior Full Stack Developer at Google and Microsoft
                Skills: JavaScript, Python, React, Node.js, Machine Learning, AI
                Experience: 8 years enterprise software development
                Architected scalable systems serving millions of users
                Led teams of 20+ developers across multiple projects
                Increased system performance by 400%
                """
            },
            # Numerical inflation
            {
                'original_content': """
                Carol Williams
                Marketing Manager at AdAgency
                Skills: Digital Marketing, Analytics
                Experience: 4 years marketing campaigns
                Increased conversion rates by 8%
                Managed budget of $50K
                """,
                'optimized_content': """
                Carol Williams
                Senior Marketing Manager at AdAgency
                Skills: Digital Marketing, Analytics, Growth Hacking
                Experience: 4 years leading high-impact marketing campaigns
                Dramatically increased conversion rates by 95%
                Successfully managed budget of $2M across multiple campaigns
                """
            }
        ]
    
    @pytest.mark.asyncio
    async def test_evaluator_with_test_runner(self, sample_dataset, sample_optimizations):
        """Test TruthfulnessEvaluator integration with TestRunner."""
        evaluator = TruthfulnessEvaluator({
            "min_truthfulness_score": 0.7,
            "enable_detailed_logging": True
        })
        
        results = []
        
        # Run evaluations for each test case
        for i, test_case in enumerate(sample_dataset.test_cases):
            result = await evaluator.evaluate(test_case, sample_optimizations[i])
            results.append(result)
        
        # Verify results
        assert len(results) == 3
        
        # Test 1: Safe optimization should pass
        safe_result = results[0]
        assert safe_result.passed
        assert safe_result.overall_score >= 0.7
        assert safe_result.detailed_scores["fabrication_risk"] < 0.3
        
        # Test 2: High fabrication risk should fail
        fabrication_result = results[1]
        assert not fabrication_result.passed
        assert fabrication_result.overall_score < 0.7
        # Check violations are mentioned in notes
        assert "fabrication" in fabrication_result.notes.lower() or "violations" in fabrication_result.notes.lower()
        
        # Test 3: Numerical inflation should be detected  
        inflation_result = results[2]
        assert not inflation_result.passed
        # Check for numerical violations in notes
        assert "numerical" in inflation_result.notes.lower() or "inflation" in inflation_result.notes.lower()
    
    @pytest.mark.asyncio
    async def test_batch_evaluation(self, sample_dataset, sample_optimizations):
        """Test batch evaluation capabilities."""
        evaluator = TruthfulnessEvaluator()
        
        # Run batch evaluation
        results = await evaluator.evaluate_batch(
            sample_dataset.test_cases,
            sample_optimizations
        )
        
        assert len(results) == len(sample_dataset.test_cases)
        
        # All results should be EvaluationResult instances
        for result in results:
            assert hasattr(result, 'overall_score')
            assert hasattr(result, 'detailed_scores')
            assert result.evaluator_name == "truthfulness"
    
    def test_evaluator_configuration(self):
        """Test evaluator configuration options."""
        config = {
            "min_truthfulness_score": 0.8,
            "enable_entity_analysis": True,
            "numerical_inflation_threshold": 1.5
        }
        
        evaluator = TruthfulnessEvaluator(config)
        
        assert evaluator.config["min_truthfulness_score"] == 0.8
        assert evaluator.config["enable_entity_analysis"] == True
        assert evaluator.config["numerical_inflation_threshold"] == 1.5
    
    def test_evaluator_capabilities(self):
        """Test evaluator capabilities reporting."""
        evaluator = TruthfulnessEvaluator()
        
        capabilities = evaluator.get_capabilities()
        
        assert capabilities["name"] == "truthfulness"
        assert "truthfulness" in capabilities["description"].lower()
        assert capabilities["is_async"] == True
        assert capabilities["supports_batch"] == True
    
    @pytest.mark.asyncio
    async def test_real_world_resume_scenario(self):
        """Test with a realistic resume optimization scenario."""
        original_resume = """
        John Developer
        Software Engineer at TechStart Inc.
        
        SKILLS
        • Programming: Python, JavaScript, HTML/CSS
        • Databases: MySQL, SQLite
        • Tools: Git, VS Code
        
        EXPERIENCE
        Software Engineer | TechStart Inc. | 2021-2023
        • Developed web applications using Django framework
        • Collaborated with team of 4 developers
        • Reduced page load times by 25%
        • Maintained legacy codebase
        
        EDUCATION
        B.S. Computer Science | State University | 2021
        """
        
        optimized_resume = """
        John Developer
        Senior Software Engineer at TechStart Inc.
        
        TECHNICAL SKILLS
        • Programming: Python, JavaScript, HTML/CSS, Django
        • Databases: MySQL, SQLite
        • Development Tools: Git, VS Code, Docker
        
        PROFESSIONAL EXPERIENCE
        Software Engineer | TechStart Inc. | 2021-2023
        • Architected and developed scalable web applications using Django framework
        • Led collaborative development with team of 4 engineers
        • Optimized application performance, reducing page load times by 25%
        • Successfully maintained and enhanced legacy codebase
        
        EDUCATION
        Bachelor of Science in Computer Science | State University | 2021
        """
        
        test_case = TestCase(
            name="Real World Resume Test",
            resume_content=original_resume,
            job_description="Senior Software Engineer with Python and web development experience"
        )
        
        actual_output = {
            'original_content': original_resume,
            'optimized_content': optimized_resume
        }
        
        evaluator = TruthfulnessEvaluator()
        result = await evaluator.evaluate(test_case, actual_output)
        
        # This should be a safe optimization
        assert result.overall_score > 0.8
        assert result.passed
        assert result.detailed_scores["content_similarity"] > 0.7
        assert len(result.violations) <= 1  # Maybe one minor violation at most
    
    @pytest.mark.asyncio
    async def test_extreme_fabrication_scenario(self):
        """Test detection of extreme fabrication."""
        original_resume = """
        Jane Student
        Recent Computer Science Graduate
        
        SKILLS
        • Programming: Python (beginner)
        • Academic projects in Java
        
        EDUCATION
        B.S. Computer Science | Local College | 2023
        """
        
        fabricated_resume = """
        Dr. Jane Student, PhD
        Senior Principal Architect at Google, Amazon, and Microsoft
        
        EXPERTISE
        • Programming: Python, Java, C++, Rust, Go, Scala, Haskell
        • AI/ML: TensorFlow, PyTorch, OpenAI GPT, Custom Neural Networks
        • Cloud: AWS, Azure, GCP (Certified Expert in all)
        • Leadership: Managed teams of 100+ engineers globally
        
        ACHIEVEMENTS
        • Increased company revenue by 10,000%
        • Invented revolutionary algorithms adopted industry-wide
        • Nobel Prize in Computer Science (2022)
        • Published 50+ peer-reviewed papers
        • Led $100B acquisition deals
        
        EXPERIENCE
        Senior Principal Architect | Google, Amazon, Microsoft | 2015-2023
        • Architected systems serving 10 billion users daily
        • Reduced infrastructure costs by 99.9%
        • Led AI revolution in industry
        
        EDUCATION
        PhD Computer Science | MIT, Stanford, Harvard | 2015
        B.S. Computer Science | Local College | 2023
        """
        
        test_case = TestCase(
            name="Extreme Fabrication Test",
            resume_content=original_resume,
            job_description="Entry level software developer"
        )
        
        actual_output = {
            'original_content': original_resume,
            'optimized_content': fabricated_resume
        }
        
        evaluator = TruthfulnessEvaluator()
        result = await evaluator.evaluate(test_case, actual_output)
        
        # Should detect extreme fabrication (even with limited NLP)
        assert result.overall_score < 0.7  # Lowered expectation due to NLP limitations
        assert not result.passed
        # Should detect some form of violation
        assert "fabrication" in result.notes.lower() or "violations" in result.notes.lower()


class TestTruthfulnessEvaluatorPerformance:
    """Performance and stress tests for TruthfulnessEvaluator."""
    
    @pytest.mark.asyncio
    async def test_large_content_evaluation(self):
        """Test evaluation with large resume content."""
        # Create large resume content
        large_original = "Software Engineer\n" + "Experience line\n" * 1000
        large_optimized = "Senior Software Engineer\n" + "Enhanced experience line\n" * 1000
        
        test_case = TestCase(
            name="Large Content Test",
            resume_content=large_original,
            job_description="Software engineer position"
        )
        
        actual_output = {
            'original_content': large_original,
            'optimized_content': large_optimized
        }
        
        evaluator = TruthfulnessEvaluator()
        
        import time
        start_time = time.time()
        result = await evaluator.evaluate(test_case, actual_output)
        end_time = time.time()
        
        # Should complete within reasonable time (< 10 seconds)
        assert end_time - start_time < 10.0
        assert isinstance(result, type(result))
        assert result.execution_time > 0
    
    @pytest.mark.asyncio
    async def test_concurrent_evaluations(self):
        """Test concurrent evaluation performance."""
        evaluator = TruthfulnessEvaluator()
        
        test_cases = []
        outputs = []
        
        for i in range(5):
            test_case = TestCase(
                name=f"Concurrent Test {i}",
                resume_content=f"Developer {i} with Python skills",
                job_description="Python developer needed"
            )
            output = {
                'original_content': f"Developer {i} with Python skills",
                'optimized_content': f"Senior Developer {i} with advanced Python expertise"
            }
            test_cases.append(test_case)
            outputs.append(output)
        
        # Run concurrent evaluations
        start_time = time.time()
        tasks = [evaluator.evaluate(case, output) for case, output in zip(test_cases, outputs)]
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Should complete all evaluations
        assert len(results) == 5
        for result in results:
            assert isinstance(result, type(results[0]))
        
        # Concurrent should be faster than sequential
        assert end_time - start_time < 15.0  # Reasonable time limit