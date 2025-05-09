"""
Integration tests for parallel processing architecture.

This module tests the parallel processing architecture for resume customization,
including section splitting, task scheduling, and results aggregation.
"""

import os
import sys
import asyncio
import unittest
import time
from typing import Dict, Any, List

# Ensure path includes project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.services.parallel_processor import (
    ParallelProcessor,
    ParallelTaskScheduler,
    ResumeSegmenter,
    ResultsAggregator,
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

class TestParallelProcessing(unittest.TestCase):
    """Test cases for parallel processing architecture."""
    
    def test_resume_segmenter(self):
        """Test that the ResumeSegmenter correctly identifies sections."""
        sections = ResumeSegmenter.identify_sections(SAMPLE_RESUME)
        
        # Check that key sections are identified
        self.assertIn(SectionType.SUMMARY, sections)
        self.assertIn(SectionType.EXPERIENCE, sections)
        self.assertIn(SectionType.EDUCATION, sections)
        self.assertIn(SectionType.SKILLS, sections)
        
        # Check content of sections
        self.assertIn("Experienced software engineer", sections[SectionType.SUMMARY])
        self.assertIn("Senior Software Engineer", sections[SectionType.EXPERIENCE])
        self.assertIn("Bachelor of Science", sections[SectionType.EDUCATION])
        self.assertIn("Python, JavaScript", sections[SectionType.SKILLS])
    
    def test_resume_reassembly(self):
        """Test that resume sections can be reassembled correctly."""
        sections = ResumeSegmenter.identify_sections(SAMPLE_RESUME)
        reassembled = ResumeSegmenter.reassemble_resume(sections)
        
        # Check that key content is preserved
        # Note: Header might be missing in reassembly since we're only focusing on section content
        self.assertIn("Senior Software Engineer", reassembled)
        self.assertIn("Python, JavaScript", reassembled)
        
        # Basic structure check - not exact match due to formatting differences
        self.assertGreater(len(reassembled), len(SAMPLE_RESUME) * 0.8)
    
    def test_parallel_task_scheduler(self):
        """Test that the ParallelTaskScheduler correctly manages tasks."""
        scheduler = ParallelTaskScheduler(max_concurrent_tasks=3)
        
        # Define some test tasks
        async def test_function(value):
            await asyncio.sleep(0.1)  # Simulate work
            return value * 2
        
        # Add tasks with different priorities
        task1 = ParallelTask(
            name="task1",
            priority=TaskPriority.HIGH,
            func=test_function,
            args=[1]
        )
        task1_id = scheduler.add_task(task1)
        
        task2 = ParallelTask(
            name="task2",
            priority=TaskPriority.MEDIUM,
            func=test_function,
            args=[2]
        )
        task2_id = scheduler.add_task(task2)
        
        task3 = ParallelTask(
            name="task3",
            priority=TaskPriority.LOW,
            func=test_function,
            args=[3]
        )
        task3_id = scheduler.add_task(task3)
        
        # Create a dependent task
        task4 = ParallelTask(
            name="task4",
            priority=TaskPriority.HIGH,
            func=test_function,
            args=[4],
            depends_on=[task1_id]
        )
        task4_id = scheduler.add_task(task4)
        
        # Check that ready tasks are correctly identified
        ready_tasks = scheduler.get_ready_tasks()
        ready_task_names = set(task.name for task in ready_tasks)
        # Only tasks 1, 2, 3 should be ready (task4 depends on task1)
        self.assertEqual(ready_task_names, {"task1", "task2", "task3"})
        
        # Check that the tasks are ordered by priority
        self.assertEqual(ready_tasks[0].name, "task1")  # HIGH priority
    
    async def run_tasks_test(self):
        """Run asynchronous tests for task execution."""
        scheduler = ParallelTaskScheduler(max_concurrent_tasks=3)
        
        # Define test tasks
        async def test_function(value):
            await asyncio.sleep(0.1)  # Simulate work
            return value * 2
        
        # Add tasks
        tasks = []
        for i in range(5):
            task = ParallelTask(
                name=f"task{i}",
                priority=TaskPriority.MEDIUM,
                func=test_function,
                args=[i]
            )
            task_id = scheduler.add_task(task)
            tasks.append(task_id)
        
        # Execute all tasks
        results = await scheduler.execute_all()
        
        # Check results
        self.assertEqual(len(results), 5)
        for i in range(5):
            self.assertEqual(results[tasks[i]], i * 2)
        
        # Check task statuses
        for task_id in tasks:
            self.assertEqual(scheduler.tasks[task_id].status, TaskStatus.COMPLETED)
        
        return True
    
    def test_task_execution(self):
        """Test task execution with the scheduler."""
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(self.run_tasks_test())
        self.assertTrue(result)
    
    async def run_dependencies_test(self):
        """Run asynchronous tests for task dependencies."""
        scheduler = ParallelTaskScheduler(max_concurrent_tasks=3)
        
        # Define test function
        async def test_function(value):
            await asyncio.sleep(0.1)  # Simulate work
            return value * 2
        
        # Create a chain of dependent tasks
        task1 = ParallelTask(
            name="task1",
            priority=TaskPriority.MEDIUM,
            func=test_function,
            args=[1]
        )
        task1_id = scheduler.add_task(task1)
        
        task2 = ParallelTask(
            name="task2",
            priority=TaskPriority.MEDIUM,
            func=test_function,
            args=[2],
            depends_on=[task1_id]
        )
        task2_id = scheduler.add_task(task2)
        
        task3 = ParallelTask(
            name="task3",
            priority=TaskPriority.MEDIUM,
            func=test_function,
            args=[3],
            depends_on=[task2_id]
        )
        task3_id = scheduler.add_task(task3)
        
        # Execute all tasks
        results = await scheduler.execute_all()
        
        # Check results
        self.assertEqual(len(results), 3)
        self.assertEqual(results[task1_id], 2)
        self.assertEqual(results[task2_id], 4)
        self.assertEqual(results[task3_id], 6)
        
        # Verify the execution order using timestamps
        self.assertLess(scheduler.tasks[task1_id].start_time, 
                        scheduler.tasks[task2_id].start_time)
        self.assertLess(scheduler.tasks[task2_id].start_time, 
                        scheduler.tasks[task3_id].start_time)
        
        return True
    
    def test_task_dependencies(self):
        """Test that task dependencies are respected during execution."""
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(self.run_dependencies_test())
        self.assertTrue(result)
    
    async def run_error_handling_test(self):
        """Run asynchronous tests for error handling."""
        scheduler = ParallelTaskScheduler(max_concurrent_tasks=3)
        
        # Define test functions
        async def success_function(value):
            await asyncio.sleep(0.1)
            return value * 2
        
        async def error_function(value):
            await asyncio.sleep(0.1)
            raise ValueError("Test error")
        
        # Add tasks
        task1 = ParallelTask(
            name="success_task",
            priority=TaskPriority.MEDIUM,
            func=success_function,
            args=[1]
        )
        task1_id = scheduler.add_task(task1)
        
        task2 = ParallelTask(
            name="error_task",
            priority=TaskPriority.MEDIUM,
            func=error_function,
            args=[2]
        )
        task2_id = scheduler.add_task(task2)
        
        # Task dependent on error task
        task3 = ParallelTask(
            name="dependent_task",
            priority=TaskPriority.MEDIUM,
            func=success_function,
            args=[3],
            depends_on=[task2_id]
        )
        task3_id = scheduler.add_task(task3)
        
        # Execute all tasks
        results = await scheduler.execute_all()
        
        # Verify results
        self.assertEqual(len(results), 1)  # Only task1 should succeed
        self.assertEqual(results[task1_id], 2)
        
        # Verify task statuses
        self.assertEqual(scheduler.tasks[task1_id].status, TaskStatus.COMPLETED)
        self.assertEqual(scheduler.tasks[task2_id].status, TaskStatus.FAILED)
        # Task3 should still be pending because its dependency failed
        self.assertEqual(scheduler.tasks[task3_id].status, TaskStatus.PENDING)
        
        # Check that the error was captured
        self.assertIsInstance(scheduler.tasks[task2_id].error, ValueError)
        
        return True
    
    def test_error_handling(self):
        """Test error handling in the parallel task scheduler."""
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(self.run_error_handling_test())
        self.assertTrue(result)
    
    async def run_fallback_test(self):
        """Run asynchronous tests for fallback mechanism."""
        # Test the run_with_fallback function
        
        async def primary_func(value):
            raise ValueError("Primary function failed")
        
        async def fallback_func(value):
            return value * 3
        
        processor = ParallelProcessor()
        
        # Run with both functions
        result = await processor.run_with_fallback(
            primary_func=primary_func,
            fallback_func=fallback_func,
            args=[5],
            max_retries=1
        )
        
        # Fallback should execute and return
        self.assertEqual(result, 15)  # 5 * 3
        
        return True
    
    def test_fallback_mechanism(self):
        """Test the fallback mechanism for error recovery."""
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(self.run_fallback_test())
        self.assertTrue(result)
    
    async def run_aggregation_test(self):
        """Run asynchronous tests for results aggregation."""
        # Sample section results for testing
        section_results = {
            SectionType.SUMMARY: {
                "match_score": 70,
                "matching_keywords": [
                    {"keyword": "software engineer", "count_in_resume": 1, "count_in_job": 1, "is_match": True},
                    {"keyword": "python", "count_in_resume": 1, "count_in_job": 1, "is_match": True}
                ],
                "missing_keywords": [
                    {"keyword": "full stack", "count_in_resume": 0, "count_in_job": 1, "is_match": False}
                ],
                "improvements": [
                    {"category": "Keywords", "suggestion": "Add missing keywords", "priority": 1}
                ],
                "section_scores": [
                    {"section": "Summary", "score": 70, "weight": 0.7}
                ]
            },
            SectionType.EXPERIENCE: {
                "match_score": 85,
                "matching_keywords": [
                    {"keyword": "mentored", "count_in_resume": 1, "count_in_job": 1, "is_match": True},
                    {"keyword": "developed", "count_in_resume": 1, "count_in_job": 1, "is_match": True}
                ],
                "missing_keywords": [
                    {"keyword": "cloud", "count_in_resume": 0, "count_in_job": 1, "is_match": False}
                ],
                "improvements": [
                    {"category": "Experience", "suggestion": "Highlight mentoring experience", "priority": 2}
                ],
                "section_scores": [
                    {"section": "Experience", "score": 85, "weight": 1.5}
                ]
            }
        }
        
        # Aggregate the results
        aggregator = ResultsAggregator()
        aggregated = await aggregator.aggregate_section_analyses(section_results)
        
        # Verify the aggregated results
        self.assertIn("match_score", aggregated)
        self.assertIn("matching_keywords", aggregated)
        self.assertIn("missing_keywords", aggregated)
        self.assertIn("improvements", aggregated)
        
        # Check that match score is calculated correctly (weighted average)
        # (70 * 0.7 + 85 * 1.5) / (0.7 + 1.5) ≈ 80.9, rounded to 80 or 81 depending on implementation
        self.assertIn(aggregated["match_score"], [80, 81])
        
        # Check that keywords are combined
        self.assertEqual(len(aggregated["matching_keywords"]), 4)
        self.assertEqual(len(aggregated["missing_keywords"]), 2)
        
        # Check that improvements are sorted by priority
        self.assertEqual(aggregated["improvements"][0]["priority"], 1)
        
        return True
    
    def test_results_aggregation(self):
        """Test that results from multiple sections are correctly aggregated."""
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(self.run_aggregation_test())
        self.assertTrue(result)
    
    async def run_processor_test(self):
        """Run asynchronous tests for the full parallel processor."""
        processor = ParallelProcessor()
        
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
            await asyncio.sleep(0.01 * (len(section_content) // 100))
            
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
        end_time = time.time()
        
        # Verify results
        self.assertIn("match_score", results)
        self.assertIn("matching_keywords", results)
        
        # Verify parallel execution was faster than sequential would be
        # We can estimate sequential time based on section count and delay
        sections = ResumeSegmenter.identify_sections(SAMPLE_RESUME)
        estimated_sequential_time = sum(0.01 * (len(content) // 100) for content in sections.values())
        actual_time = end_time - start_time
        
        # Parallel should be faster (but add a buffer for test overhead)
        self.assertLessEqual(actual_time, estimated_sequential_time * 0.8 + 0.1)
        
        return True
    
    def test_full_processor(self):
        """Test the full parallel processor with resume analysis."""
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(self.run_processor_test())
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()