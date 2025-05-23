"""
Unified interfaces for the ResumeAIAssistant components.

This module defines the standard interfaces for integration between:
1. Micro-Task Orchestration Framework 
2. Resume Section Analyzer Framework
3. Key Requirements Extractor
4. Smart Request Chunking System

These interfaces ensure consistent behavior and interoperability between components.
"""

from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Union, Callable, Awaitable
import asyncio
from pydantic import BaseModel


class Priority(Enum):
    """Priority levels for tasks and requests."""
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3


class TaskStatus(Enum):
    """Status tracking for tasks."""
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


class TaskResult(BaseModel):
    """Base model for task execution results."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    class Config:
        arbitrary_types_allowed = True


class Task(ABC):
    """Base interface for all tasks in the system."""
    
    def __init__(self, name: str, priority: Priority = Priority.MEDIUM):
        self.id: str = f"{name}-{id(self)}"
        self.name: str = name
        self.priority: Priority = priority
        self.status: TaskStatus = TaskStatus.PENDING
        self.result: Optional[TaskResult] = None
        self.dependencies: List[str] = []
        
    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> TaskResult:
        """Execute the task and return result."""
        pass
    
    def add_dependency(self, task_name: str) -> None:
        """Add a dependency to this task."""
        if task_name not in self.dependencies:
            self.dependencies.append(task_name)


class TaskOrchestrator(ABC):
    """Interface for task orchestration."""
    
    @abstractmethod
    async def add_task(self, task: Task, dependencies: Optional[List[str]] = None) -> None:
        """Add a task to the orchestrator with optional dependencies."""
        pass
    
    @abstractmethod
    async def execute_all(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, TaskResult]:
        """Execute all tasks respecting dependencies and return results."""
        pass
    
    @abstractmethod
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a task if possible."""
        pass
    
    @abstractmethod
    async def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """Get the current status of a task."""
        pass


class ProgressTracker(ABC):
    """Interface for tracking task progress."""
    
    @abstractmethod
    async def initialize(self, task_count: int, operation_id: str) -> None:
        """Initialize tracker with expected task count."""
        pass
    
    @abstractmethod
    async def update_progress(self, task_id: str, percent_complete: float, 
                             status: str = None, message: str = None) -> None:
        """Update progress for a specific task."""
        pass
    
    @abstractmethod
    async def complete_task(self, task_id: str, success: bool = True, 
                           message: str = None) -> None:
        """Mark a task as complete."""
        pass
    
    @abstractmethod
    async def get_overall_progress(self) -> Dict[str, Any]:
        """Get the overall progress of all tasks."""
        pass


class ErrorHandler(ABC):
    """Interface for error handling and recovery."""
    
    @abstractmethod
    async def handle_error(self, error: Exception, task: Task, 
                          context: Dict[str, Any]) -> TaskResult:
        """Handle error with appropriate recovery strategy."""
        pass
    
    @abstractmethod
    def register_recovery_strategy(self, error_type: type, 
                                 strategy: Callable[[Exception, Task, Dict[str, Any]], 
                                                  Awaitable[TaskResult]]) -> None:
        """Register a recovery strategy for a specific error type."""
        pass


class CircuitBreaker(ABC):
    """Interface for circuit breaker pattern implementation."""
    
    @abstractmethod
    def is_open(self, service_name: str) -> bool:
        """Check if circuit is open for the service."""
        pass
    
    @abstractmethod
    def record_success(self, service_name: str) -> None:
        """Record a successful call to the service."""
        pass
    
    @abstractmethod
    def record_failure(self, service_name: str) -> None:
        """Record a failed call to the service."""
        pass


class SectionType(Enum):
    """Types of resume sections."""
    SUMMARY = "summary"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    SKILLS = "skills"
    ACHIEVEMENTS = "achievements"
    PROJECTS = "projects"
    OTHER = "other"


class SectionAnalyzer(ABC):
    """Interface for resume section analyzers."""
    
    @property
    @abstractmethod
    def section_type(self) -> SectionType:
        """The type of section this analyzer handles."""
        pass
    
    @abstractmethod
    async def analyze(self, section_content: str, 
                     job_requirements: Dict[str, Any],
                     context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analyze a resume section and return results."""
        pass


class RequirementsExtractor(ABC):
    """Interface for key requirements extraction."""
    
    @abstractmethod
    async def extract(self, job_description: str, 
                     context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Extract key requirements from a job description."""
        pass
    
    @abstractmethod
    async def categorize(self, requirements: List[str]) -> Dict[str, List[str]]:
        """Categorize requirements into types."""
        pass


class ContentChunkingService(ABC):
    """Interface for content chunking service."""
    
    @abstractmethod
    def chunk_content(self, content: str, section_type: Optional[SectionType] = None,
                     max_chunk_size: Optional[int] = None) -> List[str]:
        """Chunk content intelligently based on type and size limits."""
        pass
    
    @abstractmethod
    def combine_results(self, chunk_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Combine results from multiple chunks into a single result."""
        pass
