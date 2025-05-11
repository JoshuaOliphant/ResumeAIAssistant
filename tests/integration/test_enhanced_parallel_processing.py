"""
Integration tests for enhanced parallel processing architecture.

This module tests the enhanced parallel processing architecture for resume customization,
including advanced features like request batching, circuit breakers, caching, and
the sequential consistency pass.
"""

import os
import sys
import asyncio
import unittest
import time
from typing import Dict, Any, List
import re

# Ensure path includes project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.services.enhanced_parallel_processor import (
    EnhancedParallelProcessor,
    EnhancedTaskScheduler,
    EnhancedResumeSegmenter,
    SequentialConsistencyPass,
    ProcessingCache,
    CircuitBreaker,
    CircuitState,
    BatchedTask,
    ParallelTask,
    TaskPriority,
    TaskStatus,
    SectionType
)
from app.schemas.customize import (
    CustomizationLevel,
    CustomizationPlan
)

# Sample resume and job description for testing
SAMPLE_RESUME = """
# John Doe
Software Engineer | john@example.com | (123) 456-7890

## Summary
Experienced software engineer with 5+ years of experience in Python and JavaScript.

## Experience
### Senior Software Engineer, XYZ Corp (2020-Present)
- Led development of new features for the company's main product
- Improved system performance by 30% through code optimization
- Mentored junior developers

### Software Developer, ABC Inc (2018-2020)
- Developed and maintained web applications using Python and Django
- Implemented CI/CD pipelines

## Education
### Bachelor of Science in Computer Science
University of Technology (2014-2018)

## Skills
Python, JavaScript, React, Node.js, SQL, Git, Docker, AWS
"""

SAMPLE_JOB_DESCRIPTION = """
# Senior Full Stack Developer

We're looking for a Senior Full Stack Developer to join our team.

## Requirements
- 5+ years of experience in web development
- Strong knowledge of Python and JavaScript
- Experience with React, Node.js, and SQL
- Familiarity with cloud platforms like AWS
- Good communication skills

## Responsibilities
- Develop and maintain web applications
- Collaborate with cross-functional teams
- Mentor junior developers
- Optimize application performance
"""

class TestEnhancedParallelProcessing(unittest.TestCase):
    """Test cases for enhanced parallel processing architecture."""
    
    def test_enhanced_resume_segmenter(self):
        """Test that the EnhancedResumeSegmenter correctly identifies sections and subsections."""
        # Test basic section identification (inherited from base class)
        sections = EnhancedResumeSegmenter.identify_sections(SAMPLE_RESUME)
        
        # Check that key sections are identified
        self.assertIn(SectionType.SUMMARY, sections)
        self.assertIn(SectionType.EXPERIENCE, sections)
        self.assertIn(SectionType.EDUCATION, sections)
        self.assertIn(SectionType.SKILLS, sections)
        
        # Check content of sections
        self.assertIn("Experienced software engineer", sections[SectionType.SUMMARY])
        self.assertIn("Senior Software Engineer", sections[SectionType.EXPERIENCE])
        
        # Test subsection identification
        experience_section = sections[SectionType.EXPERIENCE]
        subsections = EnhancedResumeSegmenter.identify_subsections(experience_section)
        
        # Should identify at least one subsection
        self.assertGreaterEqual(len(subsections), 1)
        
        # The combined content of subsections should contain all key content
        combined_content = ' '.join(subsections.values())
        self.assertIn("Senior Software Engineer", combined_content)
        self.assertIn("Software Developer", combined_content)
    
    def test_section_importance_detection(self):
        """Test that section importance is correctly detected."""
        sections = EnhancedResumeSegmenter.identify_sections(SAMPLE_RESUME)
        
        # Check importance of experience section
        experience_importance = EnhancedResumeSegmenter.detect_section_importance(
            SectionType.EXPERIENCE, 
            sections[SectionType.EXPERIENCE]
        )
        
        # Experience section should have high importance (> 1.0)
        self.assertGreater(experience_importance, 1.0)
        
        # Check importance of skills section
        skills_importance = EnhancedResumeSegmenter.detect_section_importance(
            SectionType.SKILLS, 
            sections[SectionType.SKILLS]
        )
        
        # Skills section should have importance near or above 1.0
        self.assertGreaterEqual(skills_importance, 0.9)
    
    def test_circuit_breaker(self):
        """Test the circuit breaker pattern for API failure handling."""
        # Create a circuit breaker
        breaker = CircuitBreaker(
            name="test_api",
            failure_threshold=3,
            recovery_timeout=1,  # Short timeout for testing
            half_open_max_calls=2
        )
        
        # Initially, circuit should be closed
        self.assertEqual(breaker.state, CircuitState.CLOSED)
        self.assertTrue(breaker.is_allowed())
        
        # Record failures up to threshold
        for i in range(3):
            breaker.record_failure()
            
        # Circuit should now be open
        self.assertEqual(breaker.state, CircuitState.OPEN)
        self.assertFalse(breaker.is_allowed())
        
        # Wait for recovery timeout
        time.sleep(1.1)
        
        # Circuit should transition to half-open and allow limited requests
        self.assertTrue(breaker.is_allowed())
        self.assertEqual(breaker.state, CircuitState.HALF_OPEN)
        
        # Second request in half-open should still be allowed
        self.assertTrue(breaker.is_allowed())
        
        # Record success to close the circuit
        breaker.record_success()
        breaker.record_success()
        
        # Circuit should now be closed again
        self.assertEqual(breaker.state, CircuitState.CLOSED)
        self.assertTrue(breaker.is_allowed())
    
    def test_processing_cache(self):
        """Test the processing cache for intermediate results."""
        # Create a cache
        cache = ProcessingCache(max_size=5, ttl_seconds=1)
        
        # Store a value
        key1 = "test_key1"
        value1 = {"result": "test_value1"}
        cache.set(key1, value1)
        
        # Retrieve the value
        retrieved_value = cache.get(key1)
        self.assertEqual(retrieved_value, value1)
        
        # Test expiration
        time.sleep(1.1)
        expired_value = cache.get(key1)
        self.assertIsNone(expired_value)
        
        # Test max size limit
        for i in range(6):
            cache.set(f"key_{i}", f"value_{i}")
            
        # The first key should have been evicted
        self.assertIsNone(cache.get("key_0"))
        
        # Test cache key generation
        section_type = SectionType.EXPERIENCE
        content = "Test content"
        task = "analysis"
        model = "test_model"
        
        key = cache.generate_key(section_type, content, task, model)
        self.assertIn(task, key)
        self.assertIn(section_type.value, key)
        self.assertIn(model, key)
    
    async def run_sequential_consistency_pass_test(self):
        """Run asynchronous tests for sequential consistency pass."""
        # Sample section content with inconsistent terminology
        sections = {
            SectionType.SUMMARY: "A skilled Software Engineer with experience in ReactJS",
            SectionType.EXPERIENCE: "Developed web applications using React.js and NodeJS",
            SectionType.SKILLS: "Proficient in React, Node.js, and SQL"
        }
        
        # Individual optimization results with inconsistent terminology
        optimized_sections = {
            SectionType.SUMMARY: "A skilled Software Engineer with experience in React.js",
            SectionType.EXPERIENCE: "Developed web applications using ReactJS and Node.js",
            SectionType.SKILLS: "Proficient in React.js, Node.js, and SQL"
        }
        
        # Job description with terminology preference
        job_description = "Looking for a Software Engineer with React.js experience"
        
        # Mock model config
        model_config = {"model": "test_model"}
        
        # Create consistency pass
        consistency_pass = SequentialConsistencyPass()
        
        # Process sections for consistency
        consistent_sections = await consistency_pass.process(
            sections,
            optimized_sections,
            job_description,
            model_config
        )
        
        # All React references should now be consistent (React.js)
        self.assertIn("React.js", consistent_sections[SectionType.SUMMARY])
        self.assertIn("React.js", consistent_sections[SectionType.EXPERIENCE])
        self.assertIn("React.js", consistent_sections[SectionType.SKILLS])
        
        # No ReactJS references should remain
        self.assertNotIn("ReactJS", consistent_sections[SectionType.EXPERIENCE])
        
        return True
    
    def test_sequential_consistency_pass(self):
        """Test sequential consistency pass for optimized sections."""
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(self.run_sequential_consistency_pass_test())
        self.assertTrue(result)
    
    async def run_enhanced_task_scheduler_test(self):
        """Run asynchronous tests for the enhanced task scheduler."""
        # Create an enhanced scheduler
        scheduler = EnhancedTaskScheduler(max_concurrent_tasks=3)
        
        # Define test functions
        async def success_func(value):
            await asyncio.sleep(0.1)
            return value * 2
        
        async def slow_func(value):
            await asyncio.sleep(0.3)
            return value * 3
        
        async def error_func(value):
            await asyncio.sleep(0.1)
            raise ValueError("Test error")
        
        # Add tasks with retry options
        task1 = ParallelTask(
            name="success_task",
            priority=TaskPriority.MEDIUM,
            func=success_func,
            args=[1],
            kwargs={"model_config": {"model": "test_model"}}
        )
        retry_options = {"max_retries": 2, "retry_count": 0}
        task1_id = scheduler.add_task_with_retry(task1, retry_options)
        
        task2 = ParallelTask(
            name="slow_task",
            priority=TaskPriority.LOW,
            func=slow_func,
            args=[2]
        )
        task2_id = scheduler.add_task(task2)
        
        task3 = ParallelTask(
            name="error_task",
            priority=TaskPriority.HIGH,
            func=error_func,
            args=[3],
            kwargs={"model_config": {"model": "anthropic:test_model"}}
        )
        retry_options = {"max_retries": 1, "retry_count": 0}
        task3_id = scheduler.add_task_with_retry(task3, retry_options)
        
        # Test batch creation (should create a batch if tasks are similar)
        if scheduler.batch_similar_tasks:
            scheduler.batch_similar_tasks()
        
        # Execute all tasks
        results = await scheduler.execute_all()
        
        # Check results - task1 should succeed, task3 should fail after retry
        self.assertIn(task1_id, results)
        self.assertEqual(results[task1_id], 2)  # 1 * 2
        
        self.assertIn(task2_id, results)
        self.assertEqual(results[task2_id], 6)  # 2 * 3
        
        # Task3 should have failed
        self.assertNotIn(task3_id, results)
        self.assertEqual(scheduler.tasks[task3_id].status, TaskStatus.FAILED)
        
        # Circuit breaker for anthropic should have recorded failures
        self.assertIn("anthropic", scheduler.circuit_breakers)
        anthropic_breaker = scheduler.circuit_breakers["anthropic"]
        self.assertGreater(anthropic_breaker.failure_count, 0)
        
        # Performance metrics should have been recorded
        self.assertGreater(scheduler.metrics.get_execution_count("success_task"), 0)
        self.assertGreater(scheduler.metrics.get_execution_count("error_task"), 0)
        
        return True
    
    def test_enhanced_task_scheduler(self):
        """Test the enhanced task scheduler with batching and circuit breakers."""
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(self.run_enhanced_task_scheduler_test())
        self.assertTrue(result)
    
    async def run_batch_execution_test(self):
        """Run asynchronous tests for batch execution of similar tasks."""
        # Create an enhanced scheduler
        scheduler = EnhancedTaskScheduler(max_concurrent_tasks=3)
        
        # Define test function with batch capability
        async def batch_func(value):
            await asyncio.sleep(0.1)
            return value * 2
        
        # Add batch execution capability
        async def batch_execute(batch_args, batch_kwargs):
            await asyncio.sleep(0.1)
            return [arg[0] * 2 for arg in batch_args]
        
        batch_func.batch_execute = batch_execute
        
        # Create similar tasks
        tasks = []
        for i in range(5):
            task = ParallelTask(
                name="batch_task",
                priority=TaskPriority.MEDIUM,
                func=batch_func,
                args=[i]
            )
            task_id = scheduler.add_task(task)
            tasks.append(task_id)
        
        # Create a batch task
        batch = BatchedTask(
            name="test_batch",
            priority=TaskPriority.MEDIUM,
            tasks=[scheduler.tasks[task_id] for task_id in tasks]
        )
        
        # Execute the batch
        batch_results = await scheduler.execute_batch(batch.id)
        
        # Check results - all tasks should succeed
        self.assertEqual(len(batch_results), 5)
        
        # Results should match expected values
        for i, task_id in enumerate(tasks):
            self.assertEqual(batch_results[task_id], i * 2)
        
        return True
    
    def test_batch_execution(self):
        """Test batch execution of similar tasks."""
        # Set up batch test
        scheduler = EnhancedTaskScheduler(max_concurrent_tasks=3)
        
        # Define test function with batch capability
        async def batch_func(value):
            await asyncio.sleep(0.1)
            return value * 2
        
        # Add batch execution capability
        async def batch_execute(batch_args, batch_kwargs):
            await asyncio.sleep(0.1)
            return [arg[0] * 2 for arg in batch_args]
        
        batch_func.batch_execute = batch_execute
        
        # Create similar tasks for a batch
        tasks = []
        for i in range(5):
            task = ParallelTask(
                name="batch_task",
                priority=TaskPriority.MEDIUM,
                func=batch_func,
                args=[i]
            )
            scheduler.tasks[task.id] = task
            tasks.append(task.id)
        
        # Create a batch task
        batch = BatchedTask(
            name="test_batch",
            priority=TaskPriority.MEDIUM,
            tasks=[scheduler.tasks[task_id] for task_id in tasks]
        )
        scheduler.batched_tasks[batch.id] = batch
        
        # Run the test
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(scheduler.execute_batch(batch.id))
        
        # Check results - all tasks should succeed
        self.assertEqual(len(result), 5)
        
        # Results should match expected values
        for i, task_id in enumerate(tasks):
            self.assertEqual(result[task_id], i * 2)
    
    async def run_full_processor_test(self):
        """Run asynchronous tests for the full enhanced parallel processor."""
        processor = EnhancedParallelProcessor()
        
        # Define test analysis function
        async def test_analysis_func(section_content, job_description, **kwargs):
            # Simulate different scores for different sections
            if "Summary" in section_content:
                score = 70
            elif "Experience" in section_content:
                score = 85
            elif "Education" in section_content:
                score = 75
            elif "Skills" in section_content:
                score = 90
            else:
                score = 60
                
            # Simulate processing delay based on content length
            await asyncio.sleep(0.01 * (len(section_content) // 200))
            
            # Save in cache if cache key is provided
            if "section_cache_key" in kwargs:
                cache_key = kwargs["section_cache_key"]
                processor.cache.set(cache_key, {
                    "match_score": score,
                    "matching_keywords": [
                        {"keyword": "python", "count_in_resume": 1, "count_in_job": 1, "is_match": True}
                    ],
                    "missing_keywords": [],
                    "improvements": [
                        {"category": "General", "suggestion": f"Improve {section_content[:10]}...", "priority": 2}
                    ],
                    "section_scores": [
                        {"section": section_content[:10], "score": score, "weight": 1.0}
                    ]
                })
            
            return {
                "match_score": score,
                "matching_keywords": [
                    {"keyword": "python", "count_in_resume": 1, "count_in_job": 1, "is_match": True}
                ],
                "missing_keywords": [],
                "improvements": [
                    {"category": "General", "suggestion": f"Improve {section_content[:10]}...", "priority": 2}
                ],
                "section_scores": [
                    {"section": section_content[:10], "score": score, "weight": 1.0}
                ]
            }
        
        # Process resume in parallel
        start_time = time.time()
        results = await processor.process_resume_analysis(
            resume_content=SAMPLE_RESUME,
            job_description=SAMPLE_JOB_DESCRIPTION,
            section_analysis_func=test_analysis_func
        )
        first_run_time = time.time() - start_time
        
        # Verify results
        self.assertIn("match_score", results)
        self.assertIn("matching_keywords", results)
        
        # Run a second time - should be faster due to caching
        start_time = time.time()
        cached_results = await processor.process_resume_analysis(
            resume_content=SAMPLE_RESUME,
            job_description=SAMPLE_JOB_DESCRIPTION,
            section_analysis_func=test_analysis_func
        )
        second_run_time = time.time() - start_time
        
        # Second run should be faster due to caching
        self.assertLess(second_run_time, first_run_time)
        
        # Results should be equivalent
        self.assertEqual(results["match_score"], cached_results["match_score"])
        self.assertEqual(len(results["matching_keywords"]), len(cached_results["matching_keywords"]))
        
        return True
    
    def test_full_enhanced_processor(self):
        """Test the full enhanced parallel processor with resume analysis."""
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(self.run_full_processor_test())
        self.assertTrue(result)
    
    async def run_optimization_plan_test(self):
        """Run asynchronous tests for optimization plan generation."""
        processor = EnhancedParallelProcessor()
        
        # Sample evaluation result
        evaluation = {
            "match_score": 80,
            "matching_keywords": [
                {"keyword": "python", "count_in_resume": 1, "count_in_job": 1, "is_match": True},
                {"keyword": "javascript", "count_in_resume": 1, "count_in_job": 1, "is_match": True}
            ],
            "missing_keywords": [
                {"keyword": "aws", "count_in_resume": 0, "count_in_job": 1, "is_match": False}
            ],
            "section_evaluations": [
                {
                    "section": "summary",
                    "evaluation": "Good summary but could emphasize cloud experience"
                },
                {
                    "section": "experience",
                    "evaluation": "Strong experience but missing cloud platforms"
                }
            ]
        }
        
        # Define test optimization function
        async def test_optimization_func(section_content, job_description, section_evaluation, **kwargs):
            # Simulate different recommendations for different sections
            if "Summary" in section_content:
                recommendations = [
                    {
                        "section": "summary",
                        "what": "Add cloud experience",
                        "before_text": "Experienced software engineer with 5+ years of experience in Python and JavaScript.",
                        "after_text": "Experienced software engineer with 5+ years of experience in Python, JavaScript, and cloud platforms like AWS."
                    }
                ]
                optimized_content = "Experienced software engineer with 5+ years of experience in Python, JavaScript, and cloud platforms like AWS."
            elif "Experience" in section_content:
                recommendations = [
                    {
                        "section": "experience",
                        "what": "Highlight AWS experience",
                        "before_text": "Developed and maintained web applications using Python and Django",
                        "after_text": "Developed and maintained web applications using Python, Django, and AWS"
                    }
                ]
                optimized_content = section_content.replace(
                    "Developed and maintained web applications using Python and Django",
                    "Developed and maintained web applications using Python, Django, and AWS"
                )
            else:
                recommendations = []
                optimized_content = section_content
                
            # Simulate processing delay based on content length
            await asyncio.sleep(0.01 * (len(section_content) // 200))
            
            # Save in cache if cache key is provided
            if "section_cache_key" in kwargs:
                cache_key = kwargs["section_cache_key"]
                processor.cache.set(cache_key, {
                    "section_type": section_content[:10],
                    "summary": f"Optimized {section_content[:10]}...",
                    "recommendations": recommendations,
                    "keywords_to_add": ["aws"] if "aws" not in section_content.lower() else [],
                    "formatting_suggestions": [],
                    "optimized_content": optimized_content
                })
            
            return {
                "section_type": section_content[:10],
                "summary": f"Optimized {section_content[:10]}...",
                "recommendations": recommendations,
                "keywords_to_add": ["aws"] if "aws" not in section_content.lower() else [],
                "formatting_suggestions": [],
                "optimized_content": optimized_content
            }
        
        # Process optimization plan in parallel
        start_time = time.time()
        plan = await processor.process_optimization_plan(
            resume_content=SAMPLE_RESUME,
            job_description=SAMPLE_JOB_DESCRIPTION,
            evaluation=evaluation,
            section_optimization_func=test_optimization_func,
            customization_level=CustomizationLevel.BALANCED
        )
        first_run_time = time.time() - start_time
        
        # Verify plan
        self.assertIsInstance(plan, CustomizationPlan)
        self.assertGreater(len(plan.recommendations), 0)
        self.assertIn("aws", plan.keywords_to_add)
        
        # Run a second time - should be faster due to caching
        start_time = time.time()
        cached_plan = await processor.process_optimization_plan(
            resume_content=SAMPLE_RESUME,
            job_description=SAMPLE_JOB_DESCRIPTION,
            evaluation=evaluation,
            section_optimization_func=test_optimization_func,
            customization_level=CustomizationLevel.BALANCED
        )
        second_run_time = time.time() - start_time
        
        # Second run should be faster due to caching
        self.assertLess(second_run_time, first_run_time)
        
        # Plans should be equivalent
        self.assertEqual(len(plan.recommendations), len(cached_plan.recommendations))
        self.assertEqual(plan.keywords_to_add, cached_plan.keywords_to_add)
        
        return True
    
    def test_optimization_plan_generation(self):
        """Test optimization plan generation with enhanced parallel processor."""
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(self.run_optimization_plan_test())
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()