"""
Integration tests for the ResumeAIAssistant integration components.

These tests verify that the unified interfaces for task orchestration, section analyzers,
requirements extraction, and content chunking work as expected and integrate correctly.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch
from typing import Dict, Any, List

from app.services.integration.interfaces import (
    Task, TaskOrchestrator, ProgressTracker, ErrorHandler, CircuitBreaker,
    SectionAnalyzer, RequirementsExtractor, ContentChunkingService, 
    Priority, TaskStatus, TaskResult, SectionType
)
from app.services.integration.orchestrator import IntegratedTaskOrchestrator, OrchestratorTask
from app.services.integration.progress_tracking import IntegratedProgressTracker
from app.services.integration.error_handling import (
    IntegratedErrorHandler, IntegratedCircuitBreaker, PartialResultsHandler
)
from app.services.integration.section_analyzer import (
    IntegratedSectionAnalyzer, SectionAnalyzerFactory
)
from app.services.integration.requirements_extractor import (
    IntegratedRequirementsExtractor, MockRequirementsExtractor
)
from app.services.integration.content_chunking import IntegratedContentChunker


# Test OrchestratorTask
class TestOrchestratorTask:
    """Tests for the OrchestratorTask class."""
    
    async def test_task_execution_success(self):
        """Test successful task execution."""
        # Create a task with a simple implementation
        class TestTask(OrchestratorTask):
            async def _execute_impl(self, context):
                return {"result": "success", "data": context.get("input", "default")}
        
        # Create and execute task
        task = TestTask("test_task")
        result = await task.execute({"input": "test_input"})
        
        # Check result
        assert result.success is True
        assert result.data["result"] == "success"
        assert result.data["data"] == "test_input"
    
    async def test_task_execution_failure(self):
        """Test task execution with failure."""
        # Create a task that will fail
        class FailingTask(OrchestratorTask):
            async def _execute_impl(self, context):
                raise ValueError("Test error")
        
        # Create and execute task
        task = FailingTask("failing_task")
        result = await task.execute({})
        
        # Check result
        assert result.success is False
        assert "Test error" in result.error


# Test IntegratedTaskOrchestrator
class TestIntegratedTaskOrchestrator:
    """Tests for the IntegratedTaskOrchestrator class."""
    
    async def test_add_task(self):
        """Test adding a task to the orchestrator."""
        orchestrator = IntegratedTaskOrchestrator()
        
        # Create a simple task
        task = OrchestratorTask("test_task")
        await orchestrator.add_task(task)
        
        # Check if task was added
        assert task.id in orchestrator.tasks
    
    async def test_execute_all_no_dependencies(self):
        """Test executing tasks with no dependencies."""
        orchestrator = IntegratedTaskOrchestrator()
        
        # Create tasks with mock implementations
        class SuccessTask(OrchestratorTask):
            async def _execute_impl(self, context):
                return {"result": f"success_{self.name}"}
        
        # Add tasks
        tasks = [SuccessTask(f"task_{i}") for i in range(3)]
        for task in tasks:
            await orchestrator.add_task(task)
        
        # Execute all tasks
        results = await orchestrator.execute_all()
        
        # Check results
        assert len(results) == 3
        for task in tasks:
            assert task.id in results
            assert results[task.id].success is True
            assert results[task.id].data["result"] == f"success_{task.name}"
    
    async def test_execute_with_dependencies(self):
        """Test executing tasks with dependencies."""
        orchestrator = IntegratedTaskOrchestrator()
        
        # Create tasks with dependencies
        executed_order = []
        
        class OrderedTask(OrchestratorTask):
            async def _execute_impl(self, context):
                executed_order.append(self.name)
                return {"task": self.name}
        
        # Create tasks
        task_a = OrderedTask("task_a")
        task_b = OrderedTask("task_b")
        task_c = OrderedTask("task_c")
        
        # Add tasks with dependencies
        await orchestrator.add_task(task_a)
        await orchestrator.add_task(task_b, [task_a.id])
        await orchestrator.add_task(task_c, [task_b.id])
        
        # Execute all tasks
        await orchestrator.execute_all()
        
        # Check execution order
        assert executed_order == ["task_a", "task_b", "task_c"]


# Test IntegratedProgressTracker
class TestIntegratedProgressTracker:
    """Tests for the IntegratedProgressTracker class."""
    
    @pytest.fixture
    def tracker(self):
        """Create a progress tracker for testing."""
        return IntegratedProgressTracker()
    
    @patch('app.services.integration.progress_tracking.httpx.AsyncClient.post')
    async def test_initialize(self, mock_post, tracker):
        """Test tracker initialization."""
        await tracker.initialize(task_count=5, operation_id="test_op")
        
        assert tracker.task_id == "test_op"
        assert tracker.task_count == 5
        assert tracker.completed_tasks == 0
        assert tracker.overall_progress == 0.0
        
        # Verify API call was made
        mock_post.assert_called_once()
    
    @patch('app.services.integration.progress_tracking.httpx.AsyncClient.post')
    async def test_update_progress(self, mock_post, tracker):
        """Test updating task progress."""
        await tracker.initialize(task_count=5, operation_id="test_op")
        
        # Reset mock to clear initialization call
        mock_post.reset_mock()
        
        # Update progress for a task
        await tracker.update_progress(
            task_id="task_1",
            percent_complete=50.0,
            status="running",
            message="Halfway done"
        )
        
        # Check progress was updated
        assert tracker.overall_progress > 0
        assert "Halfway done" in tracker.message
        
        # Verify API call was made
        mock_post.assert_called_once()
    
    @patch('app.services.integration.progress_tracking.httpx.AsyncClient.post')
    async def test_complete_task(self, mock_post, tracker):
        """Test marking a task as complete."""
        await tracker.initialize(task_count=2, operation_id="test_op")
        
        # Reset mock to clear initialization call
        mock_post.reset_mock()
        
        # Complete one task
        await tracker.complete_task(
            task_id="task_1",
            success=True,
            message="Task completed"
        )
        
        # Check progress was updated
        assert tracker.completed_tasks == 1
        assert tracker.overall_progress == 0.5
        
        # Complete all tasks
        await tracker.complete_task(
            task_id="task_2",
            success=True,
            message="All tasks completed"
        )
        
        # Check all tasks are complete
        assert tracker.completed_tasks == 2
        assert tracker.overall_progress == 1.0
        assert tracker.status == "completed"


# Test IntegratedErrorHandler and CircuitBreaker
class TestErrorHandling:
    """Tests for error handling and recovery mechanisms."""
    
    def test_circuit_breaker(self):
        """Test circuit breaker functionality."""
        circuit_breaker = IntegratedCircuitBreaker(failure_threshold=2, recovery_time_seconds=1)
        
        # Initially circuit should be closed
        assert circuit_breaker.is_open("test_service") is False
        
        # Record failures
        circuit_breaker.record_failure("test_service")
        assert circuit_breaker.is_open("test_service") is False
        
        # Second failure should open the circuit
        circuit_breaker.record_failure("test_service")
        assert circuit_breaker.is_open("test_service") is True
        
        # Wait for recovery time
        import time
        time.sleep(1.1)
        
        # Circuit should be in half-open state (allowing a test request)
        assert circuit_breaker.is_open("test_service") is False
        
        # Record success to fully close circuit
        circuit_breaker.record_success("test_service")
        assert circuit_breaker.is_open("test_service") is False
    
    async def test_error_handler_retry(self):
        """Test error handler retry strategy."""
        error_handler = IntegratedErrorHandler()
        
        # Mock task that fails once then succeeds
        class RetryableTask(OrchestratorTask):
            fail_count = 0
            
            async def execute(self, context):
                if self.fail_count == 0:
                    self.fail_count += 1
                    raise asyncio.TimeoutError("Timeout")
                return TaskResult(success=True, data={"result": "success"})
        
        # Create task and context
        task = RetryableTask("retry_task")
        context = {}
        
        # Handle error
        result = await error_handler.handle_error(
            asyncio.TimeoutError("Timeout"),
            task,
            context
        )
        
        # Check result - should succeed after retry
        assert result.success is True
        assert result.data["result"] == "success"
    
    async def test_partial_results_handler(self):
        """Test partial results handler."""
        # Create successful and failed results
        successful_results = {
            "task1": {"score": 80, "data": "result1"},
            "task2": {"score": 90, "data": "result2"}
        }
        
        # Create failed tasks
        failed_tasks = [
            MagicMock(name="task3", id="task3"),
            MagicMock(name="task4", id="task4")
        ]
        
        # Create context
        context = {"operation_type": "analyzing_resume"}
        
        # Get assembled result
        result = PartialResultsHandler.assemble_best_result(
            successful_results, failed_tasks, context
        )
        
        # Check result
        assert result["success"] is True
        assert result["is_partial"] is True
        assert len(result["failed_components"]) == 2
        assert len(result["successful_components"]) == 2


# Test IntegratedSectionAnalyzer
class TestSectionAnalyzer:
    """Tests for the section analyzer integration."""
    
    @pytest.fixture
    def mock_base_analyzer(self):
        """Create a mock base analyzer."""
        from app.services.section_analyzers.base import BaseSectionAnalyzer, SectionType
        
        mock = MagicMock(spec=BaseSectionAnalyzer)
        mock.section_type = SectionType.EXPERIENCE
        mock.analyze = MagicMock(return_value={"score": 85, "recommendations": []})
        
        return mock
    
    async def test_integrated_analyzer(self, mock_base_analyzer):
        """Test integrated section analyzer."""
        # Create integrated analyzer
        analyzer = IntegratedSectionAnalyzer(mock_base_analyzer)
        
        # Check properties
        assert analyzer.section_type == SectionType.EXPERIENCE
        
        # Test analyze method
        result = await analyzer.analyze(
            section_content="Test content",
            job_requirements={"keywords": {"python": 0.9}}
        )
        
        # Check result
        assert result["score"] == 85
        assert "recommendations" in result
        
        # Verify base analyzer was called correctly
        mock_base_analyzer.analyze.assert_called_once()
    
    async def test_analyzer_factory(self):
        """Test section analyzer factory."""
        # Create analyzer for each section type
        for section_type in SectionType:
            analyzer = SectionAnalyzerFactory.create_analyzer(section_type)
            
            # Check type
            assert isinstance(analyzer, SectionAnalyzer)
            assert analyzer.section_type == section_type


# Test RequirementsExtractor
class TestRequirementsExtractor:
    """Tests for the requirements extractor integration."""
    
    async def test_mock_extractor(self):
        """Test mock requirements extractor."""
        extractor = MockRequirementsExtractor()
        
        # Test extract method
        job_description = """
        We are looking for a Python developer with 5+ years of experience.
        Required skills: Python, Django, PostgreSQL, REST APIs.
        Must have good communication skills and be able to work in a team.
        """
        
        result = await extractor.extract(job_description)
        
        # Check result structure
        assert "keywords" in result
        assert "categories" in result
        assert len(result["keywords"]) > 0
        assert len(result["categories"]) > 0
    
    async def test_categorize(self):
        """Test requirement categorization."""
        extractor = MockRequirementsExtractor()
        
        # Test with sample requirements
        requirements = [
            "5+ years of Python experience",
            "Bachelor's degree in Computer Science",
            "Experience with Django framework",
            "Strong communication skills"
        ]
        
        categories = await extractor.categorize(requirements)
        
        # Check categories
        assert len(categories) > 0
        assert sum(len(reqs) for reqs in categories.values()) == len(requirements)


# Test ContentChunkingService
class TestContentChunking:
    """Tests for the content chunking service."""
    
    @pytest.fixture
    def chunker(self):
        """Create a content chunker for testing."""
        return IntegratedContentChunker(default_max_chunk_size=100)
    
    def test_chunk_content_small(self, chunker):
        """Test chunking small content."""
        content = "This is a small test content."
        
        # Should return a single chunk
        chunks = chunker.chunk_content(content)
        assert len(chunks) == 1
        assert chunks[0] == content
    
    def test_chunk_content_large(self, chunker):
        """Test chunking large content."""
        # Create content larger than chunk size
        content = " ".join(["word"] * 50) + "\n\n" + " ".join(["another"] * 50)
        
        # Should return multiple chunks
        chunks = chunker.chunk_content(content)
        assert len(chunks) > 1
        assert sum(len(chunk) for chunk in chunks) >= len(content)
    
    def test_chunk_by_section_type(self, chunker):
        """Test chunking with different section types."""
        # Create section-specific content
        experience_content = "Company A (2018-2020)\nSenior Developer\n- Did stuff\n\nCompany B (2020-Present)\nLead Developer\n- Did more stuff"
        
        # Test experience section chunking
        exp_chunks = chunker.chunk_content(experience_content, section_type=SectionType.EXPERIENCE)
        
        # Should identify job entries
        assert len(exp_chunks) == 2
    
    def test_combine_results(self, chunker):
        """Test combining results from multiple chunks."""
        # Create sample results
        chunk_results = [
            {"score": 80, "keywords": ["python", "django"]},
            {"score": 90, "keywords": ["react", "node"]}
        ]
        
        # Combine results
        combined = chunker.combine_results(chunk_results)
        
        # Check combined result
        assert "score" in combined
        assert combined["score"] == 85.0  # Average
        assert "keywords" in combined
        assert len(combined["keywords"]) == 4  # Combined lists