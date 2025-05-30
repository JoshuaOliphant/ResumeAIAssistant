# ABOUTME: Integration tests for RelevanceImpactEvaluator with the evaluation framework
# ABOUTME: Tests the evaluator working with TestRunner and real evaluation workflows
"""
Integration Tests for RelevanceImpactEvaluator

Tests the RelevanceImpactEvaluator integration with the broader evaluation framework
including TestRunner, test datasets, and real evaluation workflows.
"""

import pytest
import asyncio
from typing import Dict, Any

from evaluation.evaluators.quality import RelevanceImpactEvaluator
from evaluation.test_data.models import TestCase, TestDataset
from evaluation.test_runner import TestRunner
from evaluation.runner_config import TestRunnerConfig, ParallelismStrategy


class TestRelevanceImpactIntegration:
    """Test RelevanceImpactEvaluator integration with evaluation framework."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Sample test data for integration tests
        self.test_cases = [
            TestCase(
                name="Software Engineer Optimization",
                resume_content="""
                John Smith - Software Developer
                
                SUMMARY
                Developer with some programming experience.
                
                EXPERIENCE
                Developer at Company A
                - Worked on projects
                
                SKILLS
                Programming, basic tools
                """,
                job_description="""
                Senior Software Engineer - Python/AWS
                
                We need a Senior Software Engineer with strong Python skills,
                AWS cloud experience, and leadership capabilities.
                
                Requirements:
                - 5+ years Python development
                - AWS cloud platform experience  
                - Team leadership experience
                - CI/CD pipeline knowledge
                - Docker and Kubernetes experience
                """,
                expected_match_score=75.0,
                ground_truth={
                    'optimized_resume': """
                    John Smith - Senior Software Engineer
                    
                    SUMMARY
                    Experienced Senior Software Engineer with 6+ years of Python development
                    and proven AWS cloud architecture expertise. Strong team leadership 
                    background with extensive CI/CD and containerization experience.
                    
                    EXPERIENCE
                    Senior Software Engineer at Company A
                    - Led Python development team of 5 engineers
                    - Architected scalable AWS cloud solutions serving 100K+ users
                    - Implemented Docker/Kubernetes containerization reducing deployment time by 70%
                    - Built comprehensive CI/CD pipelines using AWS CodePipeline
                    
                    SKILLS
                    Languages: Python, JavaScript, SQL
                    Cloud: AWS (EC2, S3, Lambda, RDS), Docker, Kubernetes
                    DevOps: CI/CD, AWS CodePipeline, Jenkins, Git
                    Leadership: Team management, code reviews, mentoring
                    """
                }
            ),
            TestCase(
                name="Data Scientist Optimization",
                resume_content="""
                Jane Doe - Analyst
                
                SUMMARY
                Data analyst with some experience in analytics.
                
                EXPERIENCE
                Analyst at DataCorp
                - Analyzed data
                - Created reports
                
                SKILLS
                Excel, basic statistics
                """,
                job_description="""
                Senior Data Scientist - Machine Learning
                
                Looking for a Senior Data Scientist with machine learning expertise,
                Python programming skills, and experience with large datasets.
                
                Requirements:
                - Machine learning and statistical modeling
                - Python, R, or similar programming languages
                - Experience with big data tools (Spark, Hadoop)
                - Data visualization skills
                - PhD or Masters in quantitative field
                """,
                expected_match_score=80.0,
                ground_truth={
                    'optimized_resume': """
                    Jane Doe - Senior Data Scientist
                    
                    SUMMARY
                    Senior Data Scientist with 7+ years of machine learning and statistical 
                    modeling experience. Expert in Python, R, and big data technologies 
                    with proven track record of delivering ML solutions at scale.
                    
                    EXPERIENCE
                    Senior Data Scientist at DataCorp
                    - Developed machine learning models improving prediction accuracy by 35%
                    - Built end-to-end ML pipelines using Python, Spark, and Hadoop
                    - Created interactive data visualizations using Tableau and D3.js
                    - Led cross-functional analytics team of 4 data scientists
                    
                    SKILLS
                    Programming: Python, R, SQL, Scala
                    ML/Statistics: Scikit-learn, TensorFlow, PyTorch, Statistical Modeling
                    Big Data: Apache Spark, Hadoop, AWS EMR
                    Visualization: Tableau, D3.js, Matplotlib, Seaborn
                    
                    EDUCATION
                    PhD in Statistics, University of California
                    """
                }
            )
        ]
        
        self.test_dataset = TestDataset(
            name="Relevance Impact Test Dataset",
            description="Test cases for evaluating resume optimization impact"
        )
        
        for test_case in self.test_cases:
            self.test_dataset.add_test_case(test_case)
    
    @pytest.mark.asyncio
    async def test_single_evaluator_integration(self):
        """Test RelevanceImpactEvaluator with TestRunner."""
        evaluator = RelevanceImpactEvaluator()
        
        # Create test runner with single evaluator
        config = TestRunnerConfig()
        config.parallelism_strategy = ParallelismStrategy.NONE  # Sequential for predictable testing
        runner = TestRunner([evaluator], config)
        
        # Run evaluation
        report = await runner.run_evaluation(self.test_dataset)
        
        # Verify report structure
        assert report.total_cases == 2
        assert report.successful_cases == 2
        assert len(report.results) == 2
        assert report.average_score > 0.5
        
        # Verify all results are from our evaluator
        for result in report.results:
            assert result.evaluator_name == "relevance_impact"
            assert result.passed is True
            assert result.overall_score > 0.0
            
            # Check that analysis data is present
            assert hasattr(result, 'analysis')
            assert 'before_match_score' in result.analysis
            assert 'after_match_score' in result.analysis
    
    @pytest.mark.asyncio
    async def test_multi_evaluator_integration(self):
        """Test RelevanceImpactEvaluator alongside other evaluators."""
        from evaluation.evaluators.quality import TruthfulnessEvaluator, ContentQualityEvaluator
        
        evaluators = [
            RelevanceImpactEvaluator(),
            TruthfulnessEvaluator(), 
            ContentQualityEvaluator()
        ]
        
        # Create test runner with multiple evaluators
        config = TestRunnerConfig()
        config.parallelism_strategy = ParallelismStrategy.ASYNCIO
        config.max_workers = 3
        runner = TestRunner(evaluators, config)
        
        # Run evaluation
        report = await runner.run_evaluation(self.test_dataset)
        
        # Verify report structure
        assert report.total_cases == 2
        assert len(report.results) == 6  # 2 test cases * 3 evaluators
        
        # Verify we have results from all evaluators
        evaluator_names = {result.evaluator_name for result in report.results}
        assert evaluator_names == {"relevance_impact", "truthfulness", "content_quality"}
        
        # Verify RelevanceImpactEvaluator results
        relevance_results = [r for r in report.results if r.evaluator_name == "relevance_impact"]
        assert len(relevance_results) == 2
        
        for result in relevance_results:
            assert result.overall_score > 0.0
            assert hasattr(result, 'analysis')
            assert 'improvement_percentage' in result.analysis
    
    @pytest.mark.asyncio
    async def test_custom_configuration_integration(self):
        """Test RelevanceImpactEvaluator with custom configuration."""
        config = {
            "min_score_improvement": 0.1,
            "keyword_weight": 0.6,
            "semantic_weight": 0.4
        }
        
        evaluator = RelevanceImpactEvaluator(config)
        runner = TestRunner([evaluator])
        
        # Run evaluation
        report = await runner.run_evaluation(self.test_dataset)
        
        # Verify configuration was applied
        for result in report.results:
            assert result.configuration == config
            assert result.evaluator_name == "relevance_impact"
    
    @pytest.mark.asyncio
    async def test_batch_evaluation_performance(self):
        """Test evaluator performance with batch processing."""
        evaluator = RelevanceImpactEvaluator()
        
        # Create multiple test cases for performance testing
        large_dataset = TestDataset(name="Performance Test Dataset")
        for i in range(10):
            test_case = TestCase(
                name=f"Performance Test {i}",
                resume_content=f"Software Engineer {i} with basic experience",
                job_description="Looking for experienced Python developer",
                ground_truth={'optimized_resume': f"Senior Python Engineer {i} with 5+ years experience"}
            )
            large_dataset.add_test_case(test_case)
        
        # Configure for parallel processing
        config = TestRunnerConfig()
        config.parallelism_strategy = ParallelismStrategy.ASYNCIO
        config.max_workers = 5
        runner = TestRunner([evaluator], config)
        
        # Run evaluation and measure performance
        import time
        start_time = time.time()
        report = await runner.run_evaluation(large_dataset)
        duration = time.time() - start_time
        
        # Verify all cases completed successfully
        assert report.total_cases == 10
        assert report.successful_cases == 10
        assert len(report.results) == 10
        
        # Should complete reasonably quickly (less than 5 seconds)
        assert duration < 5.0
        
        # Verify all results have proper analysis data
        for result in report.results:
            assert hasattr(result, 'analysis')
            assert result.execution_time > 0
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self):
        """Test error handling in integration scenario."""
        evaluator = RelevanceImpactEvaluator()
        
        # Create test case with invalid data
        invalid_test_case = TestCase(
            name="Invalid Test Case",
            resume_content="Valid resume content",
            job_description="Valid job description"
            # Missing ground_truth optimized_resume
        )
        
        invalid_dataset = TestDataset(name="Invalid Dataset")
        invalid_dataset.add_test_case(invalid_test_case)
        
        # Configure runner to not fail fast
        config = TestRunnerConfig()
        config.fail_fast = False
        runner = TestRunner([evaluator], config)
        
        # Run evaluation
        report = await runner.run_evaluation(invalid_dataset)
        
        # Verify error handling - evaluator handles errors gracefully and returns failed result
        assert report.total_cases == 1
        assert report.successful_cases == 1  # TestRunner considers this successful since no exception was thrown
        assert len(report.results) == 1
        
        # Check that error was properly recorded in the result
        result = report.results[0]
        assert result.passed is False  # But the result itself indicates failure
        assert result.overall_score == 0.0
        assert "No optimized resume content found" in result.notes
        assert result.error_message is not None
    
    def test_evaluator_capabilities_reporting(self):
        """Test that evaluator properly reports its capabilities."""
        evaluator = RelevanceImpactEvaluator()
        capabilities = evaluator.get_capabilities()
        
        assert capabilities["name"] == "relevance_impact"
        assert capabilities["is_async"] is True
        assert capabilities["supports_batch"] is True
        assert "description" in capabilities
        assert "relevance" in capabilities["description"].lower()
    
    @pytest.mark.asyncio
    async def test_real_world_scenario(self):
        """Test evaluator with realistic resume optimization scenario."""
        # This test simulates a real-world optimization scenario
        realistic_before = """
        Michael Johnson
        Programmer
        
        SUMMARY
        Programmer with experience coding in various languages.
        
        EXPERIENCE
        Programmer at TechStart (2019-2023)
        - Wrote code for applications
        - Fixed bugs and issues
        - Participated in team meetings
        
        SKILLS
        Java, Python, HTML, CSS
        """
        
        realistic_after = """
        Michael Johnson
        Senior Full-Stack Engineer
        
        SUMMARY
        Senior Full-Stack Engineer with 4+ years developing scalable web applications 
        using modern frameworks. Proven track record of delivering high-quality software 
        solutions and collaborating effectively in agile environments.
        
        EXPERIENCE
        Senior Full-Stack Engineer at TechStart (2019-2023)
        - Developed and maintained 5+ web applications using React.js and Node.js
        - Implemented responsive UI components serving 50,000+ daily active users
        - Collaborated with cross-functional teams in agile development cycles
        - Reduced application load time by 40% through performance optimization
        
        SKILLS
        Frontend: JavaScript, React.js, HTML5, CSS3, TypeScript
        Backend: Node.js, Python, Java, RESTful APIs
        Databases: MySQL, MongoDB, PostgreSQL
        Tools: Git, Docker, AWS, Jenkins, JIRA
        """
        
        realistic_job = """
        Senior Full-Stack Developer
        
        We're seeking a Senior Full-Stack Developer to join our growing team.
        
        Requirements:
        - 3+ years full-stack development experience
        - Proficiency in JavaScript, React.js, and Node.js
        - Experience with modern web development practices
        - Knowledge of databases (SQL and NoSQL)
        - AWS cloud platform experience
        - Strong problem-solving and communication skills
        
        Preferred:
        - TypeScript experience
        - Docker containerization knowledge
        - CI/CD pipeline experience
        - Agile development methodology experience
        """
        
        realistic_case = TestCase(
            name="Real-world Full-Stack Optimization",
            resume_content=realistic_before,
            job_description=realistic_job,
            ground_truth={'optimized_resume': realistic_after}
        )
        
        evaluator = RelevanceImpactEvaluator()
        
        # Test direct evaluation
        optimization_output = {
            'resume_before': realistic_before,
            'resume_after': realistic_after,
            'job_description': realistic_job
        }
        
        result = await evaluator.evaluate(realistic_case, optimization_output)
        
        # Verify realistic optimization shows significant improvement
        assert result.overall_score > 0.7  # Should show good improvement
        assert result.passed is True
        
        # Check analysis details
        analysis = result.analysis
        assert analysis['improvement_percentage'] > 20  # Should show significant improvement
        assert analysis['after_match_score'] > analysis['before_match_score']
        assert analysis['keyword_coverage_after'] > analysis['keyword_coverage_before']
        
        # Check recommendations
        recommendations = analysis['recommendations']
        assert 'focus_areas' in recommendations
        assert 'missing_keywords' in recommendations
        assert recommendations['keyword_coverage_percentage'] > 30  # More realistic expectation