"""
Enhanced Parallel Processing Architecture for Resume Customization.

This module extends the existing parallel processing architecture with:
1. Advanced task scheduling with adaptive prioritization
2. Request batching for similar tasks
3. Circuit breaker pattern for API failure handling
4. Enhanced error recovery mechanisms
5. Performance metrics tracking
"""

import asyncio
import time
import uuid
import re
import math
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple, Callable, Union, Set, TypeVar
import logging
import logfire
from datetime import datetime, timedelta
from collections import defaultdict, deque

from pydantic import BaseModel, Field

from app.core.config import settings
from app.schemas.customize import CustomizationLevel, CustomizationPlan, RecommendationItem
from app.services.parallel_processor import (
    ParallelProcessor,
    ParallelTaskScheduler,
    ParallelTask,
    ResumeSegmenter,
    ResultsAggregator,
    TaskPriority,
    TaskStatus,
    SectionType
)
from app.core.parallel_config import (
    MAX_CONCURRENT_TASKS,
    TASK_TIMEOUT_SECONDS,
    SECTION_WEIGHTS,
    JOB_TYPE_WEIGHTS
)

# Type variable for generic functions
T = TypeVar('T')

# Define circuit breaker states
class CircuitState(str, Enum):
    """Circuit breaker states for API failure handling."""
    CLOSED = "closed"      # Normal operation, requests go through
    OPEN = "open"          # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing recovery, allowing limited requests

class CircuitBreaker:
    """
    Circuit breaker pattern implementation for API failure handling.
    
    The circuit breaker prevents cascading failures by temporarily stopping
    requests to a failing service until it recovers.
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        half_open_max_calls: int = 2
    ):
        """
        Initialize the circuit breaker.
        
        Args:
            name: Name of the protected service/API
            failure_threshold: Number of failures before opening the circuit
            recovery_timeout: Seconds to wait before attempting recovery
            half_open_max_calls: Maximum calls to allow in half-open state
        """
        self.name = name
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.half_open_calls = 0
        self.last_failure_time = None
        self.success_count = 0
        
    def is_allowed(self) -> bool:
        """
        Check if a request is allowed based on circuit state.
        
        Returns:
            True if the request is allowed, False otherwise
        """
        now = time.time()
        
        if self.state == CircuitState.CLOSED:
            return True
        
        elif self.state == CircuitState.OPEN:
            # Check if recovery timeout has elapsed
            if self.last_failure_time and now - self.last_failure_time >= self.recovery_timeout:
                logfire.info(
                    f"Circuit for {self.name} transitioning from OPEN to HALF_OPEN",
                    circuit=self.name,
                    previous_state=self.state,
                    new_state=CircuitState.HALF_OPEN,
                    seconds_since_failure=round(now - self.last_failure_time, 2)
                )
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                return True
            return False
            
        elif self.state == CircuitState.HALF_OPEN:
            # Allow limited requests in half-open state
            if self.half_open_calls < self.half_open_max_calls:
                self.half_open_calls += 1
                return True
            return False
            
        return True
    
    def record_success(self):
        """Record a successful API call."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            
            # If enough successful requests in half-open state, close the circuit
            if self.success_count >= self.half_open_max_calls:
                logfire.info(
                    f"Circuit for {self.name} transitioning from HALF_OPEN to CLOSED",
                    circuit=self.name,
                    previous_state=self.state,
                    new_state=CircuitState.CLOSED,
                    successful_tests=self.success_count
                )
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
        
        # Reset failure count on success in closed state
        elif self.state == CircuitState.CLOSED:
            self.failure_count = max(0, self.failure_count - 1)  # Gradually decrease failure count
            
    def record_failure(self):
        """Record a failed API call."""
        now = time.time()
        self.last_failure_time = now
        
        if self.state == CircuitState.CLOSED:
            self.failure_count += 1
            
            # If threshold reached, open the circuit
            if self.failure_count >= self.failure_threshold:
                logfire.info(
                    f"Circuit for {self.name} transitioning from CLOSED to OPEN",
                    circuit=self.name,
                    previous_state=self.state,
                    new_state=CircuitState.OPEN,
                    failure_count=self.failure_count,
                    failure_threshold=self.failure_threshold
                )
                self.state = CircuitState.OPEN
                
        elif self.state == CircuitState.HALF_OPEN:
            # If failure in half-open state, go back to open
            logfire.info(
                f"Circuit for {self.name} transitioning from HALF_OPEN back to OPEN",
                circuit=self.name,
                previous_state=self.state,
                new_state=CircuitState.OPEN,
                half_open_calls=self.half_open_calls
            )
            self.state = CircuitState.OPEN
            self.half_open_calls = 0
            self.success_count = 0

class PerformanceMetrics:
    """
    Tracks performance metrics for optimization and monitoring.
    
    This class collects metrics about task execution times, success rates,
    and other statistics to inform future optimization decisions.
    """
    
    def __init__(self, window_size: int = 100):
        """
        Initialize performance metrics tracker.
        
        Args:
            window_size: Number of recent executions to track for statistics
        """
        self.execution_times = defaultdict(lambda: deque(maxlen=window_size))
        self.success_rates = defaultdict(lambda: deque(maxlen=window_size))
        self.error_counts = defaultdict(int)
        self.execution_counts = defaultdict(int)
        self.last_execution = {}
        
    def record_execution(
        self,
        task_type: str,
        model: str,
        section_type: Optional[str],
        duration: float,
        success: bool,
        error_type: Optional[str] = None
    ):
        """
        Record a task execution for metrics tracking.
        
        Args:
            task_type: Type of task executed (e.g., "evaluate", "optimize")
            model: Model used for the task
            section_type: Type of resume section processed
            duration: Duration of the task in seconds
            success: Whether the task succeeded
            error_type: Type of error if the task failed
        """
        # Record execution time
        self.execution_times[task_type].append(duration)
        
        # Record success/failure
        self.success_rates[task_type].append(1.0 if success else 0.0)
        
        # Update counts
        self.execution_counts[task_type] += 1
        
        # Record last execution time
        self.last_execution[task_type] = time.time()
        
        # Record error if applicable
        if not success and error_type:
            key = f"{task_type}:{error_type}"
            self.error_counts[key] += 1
            
        # Additional metrics for section-specific tasks
        if section_type:
            section_key = f"{task_type}:{section_type}"
            self.execution_times[section_key].append(duration)
            self.success_rates[section_key].append(1.0 if success else 0.0)
            self.execution_counts[section_key] += 1
            
        # Additional metrics for model-specific tasks
        model_key = f"{task_type}:{model}"
        self.execution_times[model_key].append(duration)
        self.success_rates[model_key].append(1.0 if success else 0.0)
        self.execution_counts[model_key] += 1
    
    def get_average_duration(self, task_type: str) -> Optional[float]:
        """
        Get the average execution duration for a task type.
        
        Args:
            task_type: Type of task
            
        Returns:
            Average duration in seconds, or None if no data
        """
        times = self.execution_times.get(task_type)
        if not times:
            return None
        return sum(times) / len(times) if times else None
    
    def get_success_rate(self, task_type: str) -> Optional[float]:
        """
        Get the success rate for a task type.
        
        Args:
            task_type: Type of task
            
        Returns:
            Success rate (0.0-1.0), or None if no data
        """
        rates = self.success_rates.get(task_type)
        if not rates:
            return None
        return sum(rates) / len(rates) if rates else None
    
    def get_execution_count(self, task_type: str) -> int:
        """
        Get the number of executions for a task type.
        
        Args:
            task_type: Type of task
            
        Returns:
            Number of executions
        """
        return self.execution_counts.get(task_type, 0)
    
    def get_error_rate(self, task_type: str) -> Optional[float]:
        """
        Get the error rate for a task type.
        
        Args:
            task_type: Type of task
            
        Returns:
            Error rate (0.0-1.0), or None if no data
        """
        success_rate = self.get_success_rate(task_type)
        if success_rate is None:
            return None
        return 1.0 - success_rate
    
    def get_recent_errors(self, task_type: str) -> Dict[str, int]:
        """
        Get recent error counts by type for a task.
        
        Args:
            task_type: Type of task
            
        Returns:
            Dictionary mapping error types to counts
        """
        result = {}
        prefix = f"{task_type}:"
        for key, count in self.error_counts.items():
            if key.startswith(prefix):
                error_type = key[len(prefix):]
                result[error_type] = count
        return result

class BatchedTask(BaseModel):
    """Definition of a batch of similar tasks for parallel processing."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    tasks: List[ParallelTask] = []
    func: Optional[Callable] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[Exception] = None
    
    class Config:
        arbitrary_types_allowed = True

class EnhancedTaskScheduler(ParallelTaskScheduler):
    """
    Enhanced task scheduler with batching, circuit breakers, and adaptive prioritization.
    
    This extends the base ParallelTaskScheduler with:
    1. Batch processing of similar tasks
    2. Circuit breakers for API failure handling
    3. Dynamic task prioritization based on performance metrics
    4. More sophisticated error recovery
    """
    
    def __init__(
        self,
        max_concurrent_tasks: int = MAX_CONCURRENT_TASKS,
        batch_similar_tasks: bool = True
    ):
        """
        Initialize the enhanced task scheduler.
        
        Args:
            max_concurrent_tasks: Maximum number of tasks to run concurrently
            batch_similar_tasks: Whether to batch similar tasks together
        """
        super().__init__(max_concurrent_tasks)
        self.batch_similar_tasks = batch_similar_tasks
        self.batched_tasks: Dict[str, BatchedTask] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.metrics = PerformanceMetrics()
        
        # Initialize circuit breakers for each provider
        for provider in ["anthropic", "openai", "google"]:
            self.circuit_breakers[provider] = CircuitBreaker(
                name=provider,
                failure_threshold=5,
                recovery_timeout=60,
                half_open_max_calls=2
            )
        
    def add_task_with_retry(
        self,
        task: ParallelTask,
        retry_options: Dict[str, Any] = None
    ) -> str:
        """
        Add a task with retry options to the scheduler.
        
        Args:
            task: The parallel task to add
            retry_options: Options for retrying the task if it fails
            
        Returns:
            The task ID
        """
        # Add retry options to the task
        if retry_options:
            task.kwargs["retry_options"] = retry_options
            
        return self.add_task(task)
    
    def batch_similar_tasks(self) -> List[BatchedTask]:
        """
        Group similar tasks into batches for more efficient processing.
        
        Returns:
            List of batched tasks created
        """
        # Only process pending tasks
        pending_tasks = [task for task_id, task in self.tasks.items() 
                        if task.status == TaskStatus.PENDING]
        
        if not pending_tasks:
            return []
        
        # Group tasks by similarity (section type, function, etc.)
        grouped_tasks = defaultdict(list)
        
        for task in pending_tasks:
            # Skip tasks with dependencies for now
            if task.depends_on:
                continue
                
            # Create a grouping key based on task properties
            key_parts = [
                task.name.split('_')[0] if '_' in task.name else task.name,  # Base task type
                str(task.section_type) if task.section_type else "unknown",  # Section type
                str(task.priority)  # Priority level
            ]
            key = ":".join(key_parts)
            
            grouped_tasks[key].append(task)
        
        # Create batched tasks for groups of sufficient size
        batched_tasks_created = []
        min_batch_size = 2  # Minimum number of tasks to batch
        
        for key, tasks in grouped_tasks.items():
            if len(tasks) >= min_batch_size:
                # Create a batched task
                batched_task = BatchedTask(
                    name=f"batch_{key}",
                    priority=tasks[0].priority,  # Use priority of first task
                    tasks=tasks,
                    func=self.execute_batch
                )
                
                # Add the batched task to the scheduler
                self.batched_tasks[batched_task.id] = batched_task
                batched_tasks_created.append(batched_task)
                
                # Mark original tasks as being processed in a batch
                for task in tasks:
                    task.status = TaskStatus.PENDING
                    task.kwargs["batched_in"] = batched_task.id
        
        logfire.info(
            "Batched similar tasks",
            batch_count=len(batched_tasks_created),
            total_tasks_batched=sum(len(batch.tasks) for batch in batched_tasks_created)
        )
        
        return batched_tasks_created
    
    async def execute_batch(self, batch_id: str) -> Dict[str, Any]:
        """
        Execute a batch of similar tasks.
        
        Args:
            batch_id: ID of the batch to execute
            
        Returns:
            Dictionary mapping task IDs to their results
        """
        # Get the batch
        batch = self.batched_tasks.get(batch_id)
        if not batch:
            raise ValueError(f"Batch {batch_id} not found")
            
        if not batch.tasks:
            return {}
            
        batch.start_time = time.time()
        batch.status = TaskStatus.RUNNING
        
        logfire.info(
            "Executing batch of tasks",
            batch_id=batch_id,
            task_count=len(batch.tasks),
            batch_name=batch.name
        )
        
        # Organize tasks by function to call
        tasks_by_func = defaultdict(list)
        for task in batch.tasks:
            if task.func:
                func_name = task.func.__name__
                tasks_by_func[func_name].append(task)
        
        # Execute each group of tasks
        batch_results = {}
        
        for func_name, tasks in tasks_by_func.items():
            # Prepare arguments for the batch
            func = tasks[0].func  # All tasks in this group have the same function
            
            try:
                # Check for any provider-specific circuit breakers
                provider = None
                for task in tasks:
                    # Extract provider from kwargs if available
                    if task.kwargs and "model_config" in task.kwargs:
                        model = task.kwargs["model_config"].get("model", "")
                        if "anthropic" in model:
                            provider = "anthropic"
                        elif "openai" in model:
                            provider = "openai"
                        elif "google" in model or "gemini" in model:
                            provider = "google"
                        break
                
                # If a provider is identified, check its circuit breaker
                if provider and provider in self.circuit_breakers:
                    breaker = self.circuit_breakers[provider]
                    if not breaker.is_allowed():
                        logfire.warning(
                            f"Circuit breaker for {provider} is open, skipping batch",
                            batch_id=batch_id,
                            provider=provider,
                            task_count=len(tasks)
                        )
                        raise ValueError(f"Circuit breaker for {provider} is open")
                
                # Run the batch-aware version of the function if it exists
                if hasattr(func, "batch_execute") and callable(getattr(func, "batch_execute")):
                    # Extract all task arguments
                    batch_args = [task.args for task in tasks]
                    batch_kwargs = [task.kwargs for task in tasks]
                    
                    batch_method = getattr(func, "batch_execute")
                    results = await batch_method(batch_args, batch_kwargs)
                    
                    # Map results back to tasks
                    for i, task in enumerate(tasks):
                        result = results[i] if i < len(results) else None
                        task.result = result
                        task.status = TaskStatus.COMPLETED
                        task.end_time = time.time()
                        batch_results[task.id] = result
                        self.completed_tasks.add(task.id)
                        
                        # Record success in circuit breaker if applicable
                        if provider and provider in self.circuit_breakers:
                            self.circuit_breakers[provider].record_success()
                        
                        # Record metrics
                        if task.start_time:
                            duration = task.end_time - task.start_time
                            self.metrics.record_execution(
                                task_type=task.name,
                                model=task.kwargs.get("model_config", {}).get("model", "unknown") if task.kwargs else "unknown",
                                section_type=str(task.section_type) if task.section_type else None,
                                duration=duration,
                                success=True
                            )
                else:
                    # Fall back to executing tasks individually
                    for task in tasks:
                        try:
                            task.start_time = time.time()
                            result = await task.func(*task.args, **task.kwargs)
                            task.result = result
                            task.status = TaskStatus.COMPLETED
                            task.end_time = time.time()
                            batch_results[task.id] = result
                            self.completed_tasks.add(task.id)
                            
                            # Record success in circuit breaker if applicable
                            if provider and provider in self.circuit_breakers:
                                self.circuit_breakers[provider].record_success()
                            
                            # Record metrics
                            duration = task.end_time - task.start_time
                            self.metrics.record_execution(
                                task_type=task.name,
                                model=task.kwargs.get("model_config", {}).get("model", "unknown") if task.kwargs else "unknown",
                                section_type=str(task.section_type) if task.section_type else None,
                                duration=duration,
                                success=True
                            )
                        except Exception as e:
                            task.status = TaskStatus.FAILED
                            task.error = e
                            task.end_time = time.time()
                            self.failed_tasks.add(task.id)
                            
                            # Record failure in circuit breaker if applicable
                            if provider and provider in self.circuit_breakers:
                                self.circuit_breakers[provider].record_failure()
                            
                            # Record metrics
                            if task.start_time:
                                duration = task.end_time - task.start_time
                                self.metrics.record_execution(
                                    task_type=task.name,
                                    model=task.kwargs.get("model_config", {}).get("model", "unknown") if task.kwargs else "unknown",
                                    section_type=str(task.section_type) if task.section_type else None,
                                    duration=duration,
                                    success=False,
                                    error_type=type(e).__name__
                                )
                            
                            logfire.error(
                                f"Error executing task {task.id} in batch {batch_id}",
                                error=str(e),
                                error_type=type(e).__name__,
                                task_id=task.id,
                                batch_id=batch_id
                            )
            
            except Exception as e:
                # Handle errors at the batch level
                logfire.error(
                    f"Error executing batch {batch_id}",
                    error=str(e),
                    error_type=type(e).__name__,
                    batch_id=batch_id,
                    task_count=len(tasks)
                )
                
                # Mark all tasks in the batch as failed
                for task in tasks:
                    task.status = TaskStatus.FAILED
                    task.error = e
                    task.end_time = time.time()
                    self.failed_tasks.add(task.id)
                
                # Record failure in circuit breaker if applicable
                if provider and provider in self.circuit_breakers:
                    self.circuit_breakers[provider].record_failure()
        
        batch.status = TaskStatus.COMPLETED
        batch.end_time = time.time()
        batch.result = batch_results
        
        return batch_results
    
    async def execute_task_with_circuit_breaker(
        self,
        task: ParallelTask,
        provider: Optional[str] = None
    ) -> Any:
        """
        Execute a task with circuit breaker pattern for API failure handling.
        
        Args:
            task: The task to execute
            provider: Optional provider name for circuit breaker
            
        Returns:
            The result of the task execution
        """
        # Extract provider from task if not specified
        if not provider and task.kwargs and "model_config" in task.kwargs:
            model = task.kwargs["model_config"].get("model", "")
            if "anthropic" in model:
                provider = "anthropic"
            elif "openai" in model:
                provider = "openai"
            elif "google" in model or "gemini" in model:
                provider = "google"
            else:
                # Extract provider from the model format (provider:model_name)
                parts = model.split(":")
                if len(parts) > 1:
                    provider = parts[0]
        
        # Ensure provider is tracked in circuit breakers
        if provider and provider not in self.circuit_breakers:
            self.circuit_breakers[provider] = CircuitBreaker(
                name=provider,
                failure_threshold=5,
                recovery_timeout=60,
                half_open_max_calls=2
            )
            
        # Check circuit breaker if provider is identified
        if provider and provider in self.circuit_breakers:
            breaker = self.circuit_breakers[provider]
            if not breaker.is_allowed():
                logfire.warning(
                    f"Circuit breaker for {provider} is open, task execution rejected",
                    task_id=task.id,
                    task_name=task.name,
                    provider=provider
                )
                raise ValueError(f"Circuit breaker for {provider} is open")
        
        try:
            # Execute the task
            task.start_time = time.time()
            result = await super().execute_task(task)
            
            # Record success in circuit breaker if applicable
            if provider and provider in self.circuit_breakers:
                self.circuit_breakers[provider].record_success()
                
            # Record metrics
            duration = time.time() - task.start_time
            self.metrics.record_execution(
                task_type=task.name,
                model=task.kwargs.get("model_config", {}).get("model", "unknown") if task.kwargs else "unknown",
                section_type=str(task.section_type) if task.section_type else None,
                duration=duration,
                success=True
            )
            
            return result
            
        except Exception as e:
            # Record failure in circuit breaker if applicable
            if provider and provider in self.circuit_breakers:
                self.circuit_breakers[provider].record_failure()
                
            # Record metrics
            if task.start_time:
                duration = time.time() - task.start_time
                self.metrics.record_execution(
                    task_type=task.name,
                    model=task.kwargs.get("model_config", {}).get("model", "unknown") if task.kwargs else "unknown",
                    section_type=str(task.section_type) if task.section_type else None,
                    duration=duration,
                    success=False,
                    error_type=type(e).__name__
                )
            
            # Attempt recovery based on error type and retry options
            recovery_result = await self.attempt_recovery(task, e)
            if recovery_result:
                return recovery_result
                
            # If no recovery, re-raise the error
            raise e
    
    async def attempt_recovery(
        self,
        task: ParallelTask,
        error: Exception
    ) -> Optional[Any]:
        """
        Attempt to recover from a task failure.
        
        Args:
            task: The failed task
            error: The exception that caused the failure
            
        Returns:
            Recovered result if successful, None otherwise
        """
        # Check if the task has retry options
        retry_options = task.kwargs.get("retry_options", {})
        max_retries = retry_options.get("max_retries", 1)
        retry_count = retry_options.get("retry_count", 0)
        
        # Check if we should retry
        if retry_count < max_retries:
            # Update retry count
            retry_options["retry_count"] = retry_count + 1
            task.kwargs["retry_options"] = retry_options
            
            # Calculate backoff delay
            delay = 0.5 * (2 ** retry_count)  # Exponential backoff
            
            logfire.info(
                f"Retrying task {task.id} after failure (attempt {retry_count + 1}/{max_retries})",
                task_id=task.id,
                task_name=task.name,
                retry_count=retry_count + 1,
                max_retries=max_retries,
                delay=delay,
                error=str(error),
                error_type=type(error).__name__
            )
            
            # Wait for backoff period
            await asyncio.sleep(delay)
            
            # Reset task status
            task.status = TaskStatus.PENDING
            task.error = None
            
            # Check if we should use a fallback model
            # Look for various error types that indicate we should try a fallback
            error_type = type(error).__name__
            error_str = str(error).lower()
            
            # List of error indicators that suggest we should try a fallback model
            fallback_indicators = [
                "timeout", "rate limit", "capacity", "overloaded", 
                "too many requests", "retry", "throttle", "quota", 
                "server error", "service unavailable", "busy", "limit exceeded"
            ]
            
            # Check if any of the indicators are present in the error
            should_use_fallback = (
                "TimeoutError" in error_type or 
                "RateLimitError" in error_type or
                any(indicator in error_str for indicator in fallback_indicators)
            )
            
            if should_use_fallback:
                # Try a fallback model if available
                model_config = task.kwargs.get("model_config", {})
                fallbacks = model_config.get("fallback_config", [])
                
                if fallbacks:
                    # Use the first fallback model
                    fallback_model = fallbacks[0]
                    original_model = model_config.get("model", "unknown")
                    
                    logfire.info(
                        f"Using fallback model {fallback_model} for task {task.id}",
                        task_id=task.id,
                        task_name=task.name,
                        original_model=original_model,
                        fallback_model=fallback_model,
                        error_type=error_type,
                        error=str(error)
                    )
                    
                    # Update model configuration
                    model_config["model"] = fallback_model
                    # Remove used fallback from list
                    model_config["fallback_config"] = fallbacks[1:]
                    task.kwargs["model_config"] = model_config
            
            # Execute the task again
            try:
                return await self.execute_task(task)
            except Exception as retry_error:
                logfire.error(
                    f"Retry attempt {retry_count + 1}/{max_retries} failed for task {task.id}",
                    task_id=task.id,
                    task_name=task.name,
                    retry_count=retry_count + 1,
                    max_retries=max_retries,
                    error=str(retry_error),
                    error_type=type(retry_error).__name__
                )
                return None
                
        return None
    
    def adjust_priorities(self):
        """
        Dynamically adjust task priorities based on waiting time and importance.
        
        This method increases the priority of tasks that have been waiting too long
        and ensures critical tasks are executed first.
        """
        # Only adjust priorities of pending tasks
        pending_tasks = [task for task_id, task in self.tasks.items() 
                        if task.status == TaskStatus.PENDING]
        
        if not pending_tasks:
            return
        
        current_time = time.time()
        
        # Define the maximum wait time for each priority level
        max_wait_seconds = {
            TaskPriority.CRITICAL: 5,    # Critical tasks shouldn't wait more than 5 seconds
            TaskPriority.HIGH: 15,       # High priority tasks: max 15 seconds
            TaskPriority.MEDIUM: 30,     # Medium priority tasks: max 30 seconds
            TaskPriority.LOW: 60         # Low priority tasks: max 60 seconds
        }
        
        # Calculate task age and adjust priorities
        for task in pending_tasks:
            # Skip tasks with dependencies - they should wait for dependencies regardless
            if task.depends_on:
                continue
                
            # Calculate how long the task has been waiting
            if not hasattr(task, "created_time"):
                task.created_time = current_time
            
            wait_time = current_time - task.created_time
            max_wait = max_wait_seconds.get(task.priority, 30)
            
            # Increase priority if waiting too long
            if wait_time > max_wait:
                # Increase the priority by one level
                if task.priority == TaskPriority.LOW:
                    task.priority = TaskPriority.MEDIUM
                    logfire.info(
                        f"Increased priority of task {task.id} from LOW to MEDIUM due to wait time",
                        task_id=task.id,
                        task_name=task.name,
                        wait_time=round(wait_time, 2),
                        max_wait=max_wait
                    )
                elif task.priority == TaskPriority.MEDIUM:
                    task.priority = TaskPriority.HIGH
                    logfire.info(
                        f"Increased priority of task {task.id} from MEDIUM to HIGH due to wait time",
                        task_id=task.id,
                        task_name=task.name,
                        wait_time=round(wait_time, 2),
                        max_wait=max_wait
                    )
    
    async def execute_all(self) -> Dict[str, Any]:
        """
        Execute all pending tasks respecting dependencies and concurrency limits.
        Uses enhanced features like batching and dynamic prioritization.
        
        Returns:
            Dictionary mapping task IDs to results
        """
        start_time = time.time()
        logfire.info("Starting execution of all tasks with enhanced scheduler")
        
        # Batch similar tasks if enabled
        if self.batch_similar_tasks:
            batched_tasks = self.batch_similar_tasks()
            
            # Add batched tasks to the scheduler
            for batch in batched_tasks:
                self.add_task(ParallelTask(
                    id=batch.id,
                    name=batch.name,
                    priority=batch.priority,
                    func=self.execute_batch,
                    args=[batch.id]
                ))
        
        results = {}
        pending_tasks = {task_id for task_id, task in self.tasks.items() 
                        if task.status == TaskStatus.PENDING}
        
        # Main execution loop
        while pending_tasks:
            # Adjust priorities based on waiting time
            self.adjust_priorities()
            
            # Get tasks that are ready to run
            ready_tasks = self.get_ready_tasks()
            
            if not ready_tasks:
                # If no tasks are ready but we have pending tasks, 
                # we might have a dependency cycle
                if self.running_tasks:
                    # Wait for some running tasks to complete
                    await asyncio.sleep(0.1)
                    continue
                else:
                    # We have a dependency cycle or all remaining tasks have failed dependencies
                    logfire.info(
                        "Dependency issue detected - remaining tasks cannot be run",
                        pending_tasks=list(pending_tasks),
                        level="warning"
                    )
                    break
            
            # Start as many ready tasks as allowed by concurrency limit
            available_slots = self.max_concurrent_tasks - len(self.running_tasks)
            tasks_to_start = ready_tasks[:available_slots]
            
            if tasks_to_start:
                # Create task coroutines with circuit breaker
                coros = []
                for task in tasks_to_start:
                    # Check if this task is in a batch
                    if task.kwargs and "batched_in" in task.kwargs:
                        # Skip, will be handled by the batch task
                        continue
                        
                    # Extract provider if available
                    provider = None
                    if task.kwargs and "model_config" in task.kwargs:
                        model = task.kwargs["model_config"].get("model", "")
                        if "anthropic" in model:
                            provider = "anthropic"
                        elif "openai" in model:
                            provider = "openai"
                        elif "google" in model or "gemini" in model:
                            provider = "google"
                    
                    # Create coroutine with circuit breaker
                    coro = self.run_task_with_semaphore(task, provider)
                    coros.append(coro)
                
                # Start tasks with proper tracking and cleanup
                pending_asyncio_tasks = []
                for coro in coros:
                    task = asyncio.create_task(coro)
                    pending_asyncio_tasks.append(task)
                
                # Give the tasks a chance to start and update their status
                await asyncio.sleep(0.01)
                
                # Clean up completed tasks to prevent resource leaks
                for task in pending_asyncio_tasks[:]:
                    if task.done():
                        try:
                            # Retrieve result to prevent unhandled exceptions
                            task.result()
                        except Exception:
                            # Exceptions are already handled in execute_task
                            pass
                        pending_asyncio_tasks.remove(task)
                
                # Update pending tasks
                pending_tasks = {task_id for task_id, task in self.tasks.items() 
                               if task.status == TaskStatus.PENDING}
            else:
                # Wait for some running tasks to complete before checking again
                await asyncio.sleep(0.1)
                
                # Update pending tasks after wait
                pending_tasks = {task_id for task_id, task in self.tasks.items() 
                               if task.status == TaskStatus.PENDING}
        
        # Wait for all running tasks to complete
        while self.running_tasks:
            await asyncio.sleep(0.1)
            
        # Collect results
        for task_id, task in self.tasks.items():
            if task.status == TaskStatus.COMPLETED:
                results[task_id] = task.result
                
        # Collect results from batched tasks
        for batch_id, batch in self.batched_tasks.items():
            if batch.result:
                results.update(batch.result)
                
        duration = time.time() - start_time
        logfire.info(
            "All tasks execution completed with enhanced scheduler",
            completed_count=len(self.completed_tasks),
            failed_count=len(self.failed_tasks),
            batch_count=len(self.batched_tasks),
            total_duration_seconds=round(duration, 2)
        )
        
        return results
    
    async def run_task_with_semaphore(
        self,
        task: ParallelTask,
        provider: Optional[str] = None
    ) -> Any:
        """
        Run a task with the concurrency semaphore and circuit breaker.
        
        Args:
            task: The task to run
            provider: Optional provider name for circuit breaker
            
        Returns:
            The result of the task
        """
        async with self.semaphore:
            return await self.execute_task_with_circuit_breaker(task, provider)

class EnhancedResumeSegmenter(ResumeSegmenter):
    """
    Enhanced resume segmenter with more granular section detection.
    
    This extends the base ResumeSegmenter with:
    1. Subsection segmentation for more granular parallel processing
    2. ML-based section detection for improved accuracy
    """
    
    @staticmethod
    def identify_subsections(section_content: str) -> Dict[str, str]:
        """
        Further break down large sections into logical subsections.
        
        Args:
            section_content: Content of a section
            
        Returns:
            Dictionary mapping subsection names to their content
        """
        # Only process sections over a certain size
        if len(section_content) < 1000:
            return {f"main": section_content}
            
        subsections = {}
        
        # Split by natural paragraph breaks
        paragraphs = re.split(r'\n\s*\n', section_content)
        
        # Check if we have enough paragraphs to split
        if len(paragraphs) <= 2:
            return {f"main": section_content}
            
        # Check for subheadings or bullet points
        bullet_pattern = re.compile(r'^[-•*]\s+(.+)$', re.MULTILINE)
        bullet_matches = bullet_pattern.findall(section_content)
        
        # If we have bullet points, split by them
        if len(bullet_matches) >= 3:
            # Split by bullet points
            parts = re.split(r'(^[-•*]\s+.+$)', section_content, flags=re.MULTILINE)
            
            # Group the heading with its content
            current_group = "intro"
            current_content = ""
            subsection_count = 0
            
            for part in parts:
                if bullet_pattern.match(part):
                    # This is a new bullet point, start a new subsection
                    if current_content:
                        subsections[f"subsection_{subsection_count}_{current_group}"] = current_content
                        subsection_count += 1
                    
                    # Extract title from bullet point
                    title = part.strip('- •*').strip()
                    current_group = title[:20].lower().replace(' ', '_')
                    current_content = part
                else:
                    # This is content, add to current group
                    current_content += part
            
            # Add the last group
            if current_content:
                subsections[f"subsection_{subsection_count}_{current_group}"] = current_content
        else:
            # Split by paragraphs into roughly equal parts
            chunk_size = max(1, len(paragraphs) // 3)
            for i in range(0, len(paragraphs), chunk_size):
                chunk = paragraphs[i:i+chunk_size]
                chunk_content = '\n\n'.join(chunk)
                subsections[f"subsection_{i//chunk_size}"] = chunk_content
                
        return subsections
    
    @staticmethod
    def detect_section_importance(section_type: SectionType, content: str) -> float:
        """
        Detect the importance of a section based on its type and content.
        
        Args:
            section_type: Type of section
            content: Section content
            
        Returns:
            Importance score (0.0-2.0)
        """
        # Base importance from section weights
        base_importance = SECTION_WEIGHTS.get(section_type.value, 1.0)
        
        # Adjust based on content length
        length_factor = min(2.0, max(0.5, len(content) / 500))
        
        # Adjust based on keyword density
        keyword_density = 1.0
        
        # Experience section importance increases with job titles and dates
        if section_type == SectionType.EXPERIENCE:
            # Check for job titles and dates
            job_title_pattern = re.compile(r'(senior|lead|principal|director|manager|engineer|developer|analyst|consultant)', re.IGNORECASE)
            date_pattern = re.compile(r'(\d{4}[-–—]\d{4}|\d{4}[-–—]present|\d{4}[-–—]current|\d{4}[-–—]now)', re.IGNORECASE)
            
            job_titles = len(job_title_pattern.findall(content))
            dates = len(date_pattern.findall(content))
            
            experience_factor = min(2.0, max(1.0, (job_titles + dates) / 5))
            keyword_density *= experience_factor
        
        # Skills section importance increases with relevant tech keywords
        elif section_type == SectionType.SKILLS:
            # Check for technical keywords
            tech_keyword_pattern = re.compile(r'(python|javascript|react|node|aws|azure|docker|kubernetes|sql|nosql|database|cloud|devops|machine learning|ai)', re.IGNORECASE)
            
            tech_keywords = len(tech_keyword_pattern.findall(content))
            skills_factor = min(2.0, max(1.0, tech_keywords / 10))
            keyword_density *= skills_factor
        
        # Calculate final importance
        importance = base_importance * length_factor * keyword_density
        
        return min(2.0, max(0.5, importance))

class SequentialConsistencyPass:
    """
    Ensures consistency across independently processed sections.
    
    This class provides a sequential final pass over the optimized sections
    to ensure consistent terminology, style, and references across the resume.
    """
    
    async def process(
        self,
        sections: Dict[SectionType, str],
        optimized_sections: Dict[SectionType, str],
        job_description: str,
        model_config: Dict[str, Any]
    ) -> Dict[SectionType, str]:
        """
        Process all sections sequentially to ensure consistency.
        
        Args:
            sections: Original section content
            optimized_sections: Individually optimized section content
            job_description: Job description text
            model_config: Model configuration
            
        Returns:
            Dictionary mapping section types to consistent optimized content
        """
        # This implementation would call a consistency-checking LLM
        # For now, we'll implement a simplified version
        
        # Start with the optimized sections
        consistent_sections = optimized_sections.copy()
        
        # Extract terminology and phrases from job description
        job_terms = self._extract_key_terminology(job_description)
        
        # Check for consistency issues
        term_usage = self._analyze_term_usage(optimized_sections, job_terms)
        
        # Fix inconsistent terminology
        if term_usage["inconsistent_terms"]:
            consistent_sections = await self._standardize_terminology(
                consistent_sections,
                term_usage["inconsistent_terms"],
                term_usage["preferred_forms"],
                model_config
            )
            
        return consistent_sections
    
    def _extract_key_terminology(self, content: str) -> List[str]:
        """
        Extract key terminology from content.
        
        Args:
            content: Text to extract terminology from
            
        Returns:
            List of key terms
        """
        # Simple extraction based on common patterns
        # In a real implementation, this would use more sophisticated NLP
        
        # Look for terms in ALL CAPS or "quoted phrases"
        caps_pattern = re.compile(r'\b[A-Z]{2,}[A-Z0-9]*\b')
        quotes_pattern = re.compile(r'"([^"]+)"')
        
        caps_terms = caps_pattern.findall(content)
        quoted_terms = quotes_pattern.findall(content)
        
        # Keywords often appear in specific contexts
        keyword_pattern = re.compile(r'(skills?|technolog(y|ies)|experience|knowledge) (in|with|of) ([^.,:;]+)', re.IGNORECASE)
        matches = keyword_pattern.findall(content)
        context_terms = []
        for match in matches:
            terms = match[3].split(',')
            for term in terms:
                context_terms.append(term.strip())
        
        # Combine all extractions
        all_terms = caps_terms + quoted_terms + context_terms
        
        # Clean and deduplicate terms
        cleaned_terms = []
        for term in all_terms:
            term = term.strip()
            if len(term) > 2 and term not in cleaned_terms:
                cleaned_terms.append(term)
                
        return cleaned_terms
    
    def _analyze_term_usage(
        self,
        sections: Dict[SectionType, str],
        key_terms: List[str]
    ) -> Dict[str, Any]:
        """
        Analyze term usage consistency across sections.
        
        Args:
            sections: Section content
            key_terms: Key terminology from job description
            
        Returns:
            Dictionary with analysis results
        """
        # Combine all section content
        all_content = '\n\n'.join([content for content in sections.values()])
        
        # Find variations of key terms
        inconsistent_terms = {}
        preferred_forms = {}
        
        for term in key_terms:
            # Look for variations (case insensitive, hyphenation differences, etc.)
            term_lower = term.lower()
            term_pattern = re.compile(term, re.IGNORECASE)
            matches = term_pattern.findall(all_content)
            
            # If multiple forms of the same term exist
            if len(matches) >= 2:
                unique_forms = list(set(matches))
                if len(unique_forms) > 1:
                    # Found inconsistent usage
                    inconsistent_terms[term_lower] = unique_forms
                    
                    # Determine preferred form (usually the one matching job description)
                    matched_job_desc = [form for form in unique_forms if form in key_terms]
                    if matched_job_desc:
                        preferred_forms[term_lower] = matched_job_desc[0]
                    else:
                        # Default to most common form
                        form_counts = {form: matches.count(form) for form in unique_forms}
                        preferred_forms[term_lower] = max(form_counts, key=form_counts.get)
        
        return {
            "inconsistent_terms": inconsistent_terms,
            "preferred_forms": preferred_forms
        }
    
    async def _standardize_terminology(
        self,
        sections: Dict[SectionType, str],
        inconsistent_terms: Dict[str, List[str]],
        preferred_forms: Dict[str, str],
        model_config: Dict[str, Any]
    ) -> Dict[SectionType, str]:
        """
        Standardize terminology across sections.
        
        Args:
            sections: Section content
            inconsistent_terms: Terms with inconsistent usage
            preferred_forms: Preferred form for each term
            model_config: Model configuration
            
        Returns:
            Dictionary with standardized sections
        """
        # In a real implementation, this would use an LLM to intelligently 
        # standardize terminology. For now, we'll implement a simple replacement.
        standardized_sections = {}
        
        for section_type, content in sections.items():
            standardized_content = content
            
            # Standardize each inconsistent term
            for term_lower, forms in inconsistent_terms.items():
                if term_lower in preferred_forms:
                    preferred = preferred_forms[term_lower]
                    
                    # Replace all non-preferred forms with the preferred form
                    for form in forms:
                        if form != preferred:
                            # Use regex to ensure we match whole words only
                            pattern = re.compile(r'\b' + re.escape(form) + r'\b')
                            standardized_content = pattern.sub(preferred, standardized_content)
            
            standardized_sections[section_type] = standardized_content
            
        return standardized_sections

class ProcessingCache:
    """
    Cache for storing intermediate processing results.
    
    This class provides a simple time-based cache for storing and retrieving
    intermediate processing results to avoid redundant processing.
    """
    
    def __init__(self, max_size: int = 100, ttl_seconds: int = 3600):
        """
        Initialize the processing cache.
        
        Args:
            max_size: Maximum number of items to store
            ttl_seconds: Time-to-live in seconds for cache entries
        """
        self.cache = {}
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.access_times = {}
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache if it exists and is not expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        if key not in self.cache:
            return None
            
        # Check TTL
        current_time = time.time()
        entry = self.cache[key]
        timestamp = entry.get("timestamp", 0)
        
        if current_time - timestamp > self.ttl_seconds:
            # Expired
            del self.cache[key]
            del self.access_times[key]
            return None
            
        # Update access time
        self.access_times[key] = current_time
        
        return entry.get("value")
    
    def set(self, key: str, value: Any) -> None:
        """
        Store a value in the cache with current timestamp.
        
        Args:
            key: Cache key
            value: Value to store
        """
        # Check if cache is full and evict least recently used item if needed
        if len(self.cache) >= self.max_size and key not in self.cache:
            # Find least recently used item if access_times is not empty
            if self.access_times:
                lru_key = min(self.access_times, key=self.access_times.get)
                if lru_key in self.cache:
                    del self.cache[lru_key]
                if lru_key in self.access_times:
                    del self.access_times[lru_key]
        
        current_time = time.time()
        # Store value with timestamp
        self.cache[key] = {
            "value": value,
            "timestamp": current_time
        }
        self.access_times[key] = current_time
    
    def generate_key(
        self,
        section_type: SectionType,
        content: str,
        task: str,
        model: str = "any"
    ) -> str:
        """
        Generate a unique cache key based on content hash and metadata.
        
        Args:
            section_type: Type of section
            content: Section content
            task: Task name
            model: Model name
            
        Returns:
            Cache key string
        """
        # Generate content hash
        import hashlib
        content_hash = hashlib.md5(content.encode()).hexdigest()
        
        # Create key with metadata
        key_parts = [
            task,
            section_type.value if isinstance(section_type, SectionType) else str(section_type),
            model,
            content_hash
        ]
        
        return ":".join(key_parts)

class EnhancedParallelProcessor(ParallelProcessor):
    """
    Enhanced parallel processor with advanced features.
    
    This class extends the base ParallelProcessor with:
    1. Enhanced task scheduling with batching and circuit breakers
    2. Improved section segmentation for more granular processing
    3. Sequential consistency pass for better results
    4. Caching layer for improved performance
    """
    
    def __init__(self):
        """Initialize the enhanced parallel processor."""
        # Don't call super().__init__() as we're replacing the scheduler
        self.scheduler = EnhancedTaskScheduler()
        self.segmenter = EnhancedResumeSegmenter
        self.aggregator = ResultsAggregator
        self.consistency_pass = SequentialConsistencyPass()
        self.cache = ProcessingCache()
    
    async def process_resume_analysis(
        self, 
        resume_content: str, 
        job_description: str,
        section_analysis_func: Callable,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Process resume analysis in parallel across sections with enhanced features.
        
        Args:
            resume_content: The full resume content
            job_description: The job description text
            section_analysis_func: Function to analyze each section
            **kwargs: Additional arguments to pass to the analysis function
            
        Returns:
            Aggregated analysis results
        """
        start_time = time.time()
        logfire.info(
            "Starting enhanced parallel resume analysis",
            resume_length=len(resume_content),
            job_description_length=len(job_description)
        )
        
        # Check cache for similar analysis results
        cache_key = f"analysis:{len(resume_content)}:{len(job_description)}:{hash(resume_content[:1000])}"
        cached_result = self.cache.get(cache_key)
        if cached_result:
            logfire.info(
                "Retrieved analysis results from cache",
                cache_key=cache_key,
                cache_hit=True
            )
            return cached_result
        
        # Identify sections in the resume
        sections = self.segmenter.identify_sections(resume_content)
        
        # Further break down large sections into subsections for more granular processing
        enhanced_sections = {}
        for section_type, section_content in sections.items():
            # Only split large sections
            if len(section_content) > 2000:
                subsections = self.segmenter.identify_subsections(section_content)
                for subsection_name, subsection_content in subsections.items():
                    # Create a combined name for tracking
                    enhanced_name = f"{section_type.value}_{subsection_name}"
                    enhanced_sections[enhanced_name] = {
                        "content": subsection_content,
                        "parent_type": section_type,
                        "subsection": True
                    }
            else:
                enhanced_sections[section_type.value] = {
                    "content": section_content,
                    "parent_type": section_type,
                    "subsection": False
                }
        
        # Calculate importance of each section
        for section_name, section_data in enhanced_sections.items():
            if isinstance(section_data["parent_type"], SectionType):
                importance = self.segmenter.detect_section_importance(
                    section_data["parent_type"],
                    section_data["content"]
                )
                section_data["importance"] = importance
            else:
                section_data["importance"] = 1.0
        
        # Clear existing tasks and prepare new ones
        self.scheduler = EnhancedTaskScheduler()
        section_tasks = {}
        
        # Create analysis tasks for each section/subsection
        for section_name, section_data in enhanced_sections.items():
            section_content = section_data["content"]
            parent_type = section_data["parent_type"]
            importance = section_data["importance"]
            
            # Get cache key for this specific section
            section_cache_key = self.cache.generate_key(
                parent_type,
                section_content,
                "analysis",
                kwargs.get("model_config", {}).get("model", "any") if kwargs else "any"
            )
            
            # Check cache for section-specific results
            cached_section_result = self.cache.get(section_cache_key)
            if cached_section_result:
                # Use cached result
                section_tasks[section_name] = f"cached:{section_cache_key}"
                logfire.info(
                    f"Using cached analysis for section {section_name}",
                    section_name=section_name,
                    cache_key=section_cache_key
                )
                continue
            
            # Determine task priority based on importance
            if importance >= 1.5:
                priority = TaskPriority.HIGH
            elif importance >= 1.0:
                priority = TaskPriority.MEDIUM
            else:
                priority = TaskPriority.LOW
                
            # Additional parameters for tracking
            tracking_kwargs = kwargs.copy()
            tracking_kwargs["section_name"] = section_name
            tracking_kwargs["section_cache_key"] = section_cache_key
            
            # Create the task
            task = ParallelTask(
                name=f"analyze_{section_name}",
                section_type=parent_type,
                priority=priority,
                func=section_analysis_func,
                args=[section_content, job_description],
                kwargs=tracking_kwargs
            )
            
            # Add additional retry options
            retry_options = {
                "max_retries": 2,
                "retry_count": 0
            }
            task_id = self.scheduler.add_task_with_retry(task, retry_options)
            section_tasks[section_name] = task_id
        
        # Execute all tasks and wait for completion
        results = await self.scheduler.execute_all()
        
        # Process cached results
        for section_name, task_id in section_tasks.items():
            if isinstance(task_id, str) and task_id.startswith("cached:"):
                # Extract cache key
                cache_key = task_id[7:]
                cached_result = self.cache.get(cache_key)
                if cached_result:
                    results[section_name] = cached_result
        
        # Store results in cache for future use
        for section_name, task_id in section_tasks.items():
            if not isinstance(task_id, str) and task_id in results:
                # Get the section cache key from the kwargs
                task = self.scheduler.tasks.get(task_id)
                if task and task.kwargs and "section_cache_key" in task.kwargs:
                    section_cache_key = task.kwargs["section_cache_key"]
                    self.cache.set(section_cache_key, results[task_id])
        
        # Map results back to section types
        section_results = {}
        for section_name, task_id in section_tasks.items():
            if section_name in results:
                result = results[section_name]
            elif not isinstance(task_id, str) and task_id in results:
                result = results[task_id]
            else:
                continue
                
            # Find the parent section type
            parent_type = enhanced_sections[section_name]["parent_type"]
            
            # Group results by parent section type
            if parent_type not in section_results:
                section_results[parent_type] = []
                
            section_results[parent_type].append(result)
        
        # Merge subsection results for each section
        merged_results = {}
        for section_type, subsection_results in section_results.items():
            if len(subsection_results) == 1:
                # Only one result, no need to merge
                merged_results[section_type] = subsection_results[0]
            else:
                # Merge multiple subsection results
                merged = self._merge_subsection_results(subsection_results)
                merged_results[section_type] = merged
        
        # Aggregate results from all sections
        aggregated_results = await self.aggregator.aggregate_section_analyses(merged_results)
        
        # Store in cache
        self.cache.set(cache_key, aggregated_results)
        
        duration = time.time() - start_time
        logfire.info(
            "Enhanced parallel resume analysis completed",
            duration_seconds=round(duration, 2),
            processed_sections=len(merged_results),
            match_score=aggregated_results.get("match_score", 0)
        )
        
        return aggregated_results
    
    def _merge_subsection_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge results from multiple subsections into a single result.
        
        Args:
            results: List of subsection results
            
        Returns:
            Merged result dictionary
        """
        if not results:
            return {}
            
        if len(results) == 1:
            return results[0]
            
        # Start with the first result as base
        merged = results[0].copy()
        
        # Merge lists
        for list_key in ["matching_keywords", "missing_keywords", "improvements", "section_scores"]:
            if list_key not in merged:
                merged[list_key] = []
            else:
                merged[list_key] = list(merged[list_key])
            
            # Add items from other results
            for result in results[1:]:
                if list_key in result:
                    merged[list_key].extend(result[list_key])
                    
            # Remove duplicates while preserving order
            seen = set()
            if isinstance(merged[list_key], list):
                unique_items = []
                for item in merged[list_key]:
                    # Convert dict to tuple of items for hashing
                    if isinstance(item, dict):
                        item_key = tuple(sorted(item.items()))
                    else:
                        item_key = item
                        
                    if item_key not in seen:
                        seen.add(item_key)
                        unique_items.append(item)
                        
                merged[list_key] = unique_items
        
        # Calculate average match score
        if "match_score" in merged:
            scores = [r.get("match_score", 0) for r in results]
            valid_scores = [s for s in scores if s > 0]
            if valid_scores:
                merged["match_score"] = sum(valid_scores) / len(valid_scores)
        
        return merged
    
    async def process_optimization_plan(
        self,
        resume_content: str,
        job_description: str,
        evaluation: Dict[str, Any],
        section_optimization_func: Callable,
        **kwargs
    ) -> CustomizationPlan:
        """
        Process optimization plan generation in parallel across sections with enhanced features.
        
        Args:
            resume_content: The full resume content
            job_description: The job description text
            evaluation: Evaluation dictionary from the evaluation stage
            section_optimization_func: Function to generate optimization plan for each section
            **kwargs: Additional arguments to pass to the optimization function
            
        Returns:
            Aggregated CustomizationPlan
        """
        start_time = time.time()
        logfire.info(
            "Starting enhanced parallel optimization plan generation",
            resume_length=len(resume_content),
            job_description_length=len(job_description)
        )
        
        # Identify sections in the resume
        sections = self.segmenter.identify_sections(resume_content)
        
        # Further break down large sections into subsections for more granular processing
        enhanced_sections = {}
        for section_type, section_content in sections.items():
            # Only split large sections with complex optimizations
            if len(section_content) > 3000:
                subsections = self.segmenter.identify_subsections(section_content)
                for subsection_name, subsection_content in subsections.items():
                    # Create a combined name for tracking
                    enhanced_name = f"{section_type.value}_{subsection_name}"
                    enhanced_sections[enhanced_name] = {
                        "content": subsection_content,
                        "parent_type": section_type,
                        "subsection": True,
                        "original_section": section_type
                    }
            else:
                enhanced_sections[section_type.value] = {
                    "content": section_content,
                    "parent_type": section_type,
                    "subsection": False,
                    "original_section": section_type
                }
        
        # Extract section evaluations from the evaluation if available
        section_evaluations = {}
        if "section_evaluations" in evaluation:
            for section_eval in evaluation["section_evaluations"]:
                section_name = section_eval.get("section", "").lower()
                for section_type in SectionType:
                    if section_name == section_type.value or section_name in self.segmenter.SECTION_PATTERNS.get(section_type, []):
                        section_evaluations[section_type] = section_eval
                        break
        
        # Calculate importance of each section
        for section_name, section_data in enhanced_sections.items():
            if isinstance(section_data["parent_type"], SectionType):
                importance = self.segmenter.detect_section_importance(
                    section_data["parent_type"],
                    section_data["content"]
                )
                section_data["importance"] = importance
            else:
                section_data["importance"] = 1.0
        
        # Clear existing tasks and prepare new ones
        self.scheduler = EnhancedTaskScheduler()
        section_tasks = {}
        
        # Create optimization tasks for each section/subsection
        for section_name, section_data in enhanced_sections.items():
            section_content = section_data["content"]
            parent_type = section_data["parent_type"]
            original_section = section_data["original_section"]
            importance = section_data["importance"]
            
            # Get section-specific evaluation if available
            section_eval = section_evaluations.get(original_section, {})
            
            # Get cache key for this specific section
            section_cache_key = self.cache.generate_key(
                parent_type,
                section_content,
                "optimization",
                kwargs.get("model_config", {}).get("model", "any") if kwargs else "any"
            )
            
            # Check cache for section-specific results
            cached_section_result = self.cache.get(section_cache_key)
            if cached_section_result:
                # Use cached result
                section_tasks[section_name] = f"cached:{section_cache_key}"
                logfire.info(
                    f"Using cached optimization plan for section {section_name}",
                    section_name=section_name,
                    cache_key=section_cache_key
                )
                continue
            
            # Determine task priority based on importance
            if importance >= 1.5:
                priority = TaskPriority.HIGH
            elif importance >= 1.0:
                priority = TaskPriority.MEDIUM
            else:
                priority = TaskPriority.LOW
                
            # Skip empty or very short sections
            if not section_content or len(section_content) < 50:
                # Create minimal empty plan for empty sections
                empty_plan = {
                    "section_type": parent_type,
                    "summary": f"The {parent_type} section is too short or empty to optimize.",
                    "recommendations": [],
                    "keywords_to_add": [],
                    "formatting_suggestions": []
                }
                section_tasks[section_name] = f"empty:{section_name}"
                self.cache.set(section_cache_key, empty_plan)
                continue
                
            # Additional parameters for tracking
            tracking_kwargs = kwargs.copy()
            tracking_kwargs["section_name"] = section_name
            tracking_kwargs["section_cache_key"] = section_cache_key
            
            # Create a task for this section
            task = ParallelTask(
                name=f"optimize_{section_name}",
                section_type=parent_type,
                priority=priority,
                func=section_optimization_func,
                args=[section_content, job_description, section_eval],
                kwargs=tracking_kwargs
            )
            
            # Add additional retry options
            retry_options = {
                "max_retries": 2,
                "retry_count": 0
            }
            task_id = self.scheduler.add_task_with_retry(task, retry_options)
            section_tasks[section_name] = task_id
        
        # Execute all tasks and wait for completion
        results = await self.scheduler.execute_all()
        
        # Process cached and empty results
        for section_name, task_id in section_tasks.items():
            if isinstance(task_id, str):
                if task_id.startswith("cached:"):
                    # Extract cache key
                    cache_key = task_id[7:]
                    cached_result = self.cache.get(cache_key)
                    if cached_result:
                        results[section_name] = cached_result
                elif task_id.startswith("empty:"):
                    # Create minimal empty plan
                    parent_type = enhanced_sections[section_name]["parent_type"]
                    empty_plan = {
                        "section_type": parent_type,
                        "summary": f"The {parent_type} section is too short or empty to optimize.",
                        "recommendations": [],
                        "keywords_to_add": [],
                        "formatting_suggestions": []
                    }
                    results[section_name] = empty_plan
        
        # Store results in cache for future use
        for section_name, task_id in section_tasks.items():
            if not isinstance(task_id, str) and task_id in results:
                # Get the section cache key from the kwargs
                task = self.scheduler.tasks.get(task_id)
                if task and task.kwargs and "section_cache_key" in task.kwargs:
                    section_cache_key = task.kwargs["section_cache_key"]
                    self.cache.set(section_cache_key, results[task_id])
        
        # Map results back to section types
        section_results = {}
        optimized_sections = {}
        
        for section_name, task_id in section_tasks.items():
            if section_name in results:
                result = results[section_name]
            elif not isinstance(task_id, str) and task_id in results:
                result = results[task_id]
            else:
                continue
                
            # Find the parent section type
            parent_type = enhanced_sections[section_name]["parent_type"]
            is_subsection = enhanced_sections[section_name]["subsection"]
            original_section = enhanced_sections[section_name]["original_section"]
            
            # Group results by original section type
            if original_section not in section_results:
                section_results[original_section] = []
                
            section_results[original_section].append(result)
            
            # Store the content for consistency pass
            if "optimized_content" in result:
                if original_section not in optimized_sections:
                    optimized_sections[original_section] = {}
                    
                if is_subsection:
                    optimized_sections[original_section][section_name] = result["optimized_content"]
                else:
                    optimized_sections[original_section] = result["optimized_content"]
        
        # Merge subsection results for each section
        merged_results = {}
        for section_type, subsection_results in section_results.items():
            if len(subsection_results) == 1:
                # Only one result, no need to merge
                merged_results[section_type] = subsection_results[0]
            else:
                # Merge multiple subsection results
                merged = self._merge_optimization_results(subsection_results)
                merged_results[section_type] = merged
        
        # Run the sequential consistency pass if optimized content is available
        if optimized_sections:
            # Prepare for consistency pass
            flat_optimized_sections = {}
            for section_type, content in optimized_sections.items():
                if isinstance(content, dict):
                    # Merge subsection contents
                    flat_optimized_sections[section_type] = "\n\n".join(content.values())
                else:
                    flat_optimized_sections[section_type] = content
                    
            # Run consistency pass
            consistent_sections = await self.consistency_pass.process(
                sections,
                flat_optimized_sections,
                job_description,
                kwargs.get("model_config", {})
            )
            
            # Update the merged results with consistent content
            for section_type, content in consistent_sections.items():
                if section_type in merged_results:
                    merged_results[section_type]["optimized_content"] = content
        
        # Aggregate optimization plans from all sections
        aggregated_plan = await self.aggregator.aggregate_optimization_plans(merged_results)
        
        duration = time.time() - start_time
        logfire.info(
            "Enhanced parallel optimization plan generation completed",
            duration_seconds=round(duration, 2),
            processed_sections=len(merged_results),
            recommendation_count=len(aggregated_plan.recommendations)
        )
        
        return aggregated_plan
    
    def _merge_optimization_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge optimization results from multiple subsections into a single result.
        
        Args:
            results: List of subsection optimization results
            
        Returns:
            Merged optimization result dictionary
        """
        if not results:
            return {}
            
        if len(results) == 1:
            return results[0]
            
        # Start with the first result as base
        merged = results[0].copy()
        
        # Merge summary and job analysis
        summary_parts = []
        job_analysis_parts = []
        
        for result in results:
            if "summary" in result and result["summary"]:
                summary_parts.append(result["summary"])
                
            if "job_analysis" in result and result["job_analysis"]:
                job_analysis_parts.append(result["job_analysis"])
        
        # Combine summaries and analyses
        if summary_parts:
            merged["summary"] = "\n".join(summary_parts)
            
        if job_analysis_parts:
            merged["job_analysis"] = max(job_analysis_parts, key=len)
        
        # Merge recommendations, keywords, and formatting suggestions
        for list_key in ["recommendations", "keywords_to_add", "formatting_suggestions"]:
            merged[list_key] = list(merged.get(list_key, []))
            
            # Add items from other results
            for result in results[1:]:
                if list_key in result:
                    merged[list_key].extend(result[list_key])
                    
            # Remove duplicates
            if list_key == "recommendations":
                # For recommendations, use a more complex deduplication
                unique_recs = []
                seen_hashes = set()
                
                for rec in merged[list_key]:
                    # Create a hash based on what, before_text, and after_text
                    rec_hash = None
                    
                    if isinstance(rec, dict):
                        what = rec.get("what", "")
                        before = rec.get("before_text", "")[:50]
                        after = rec.get("after_text", "")[:50]
                        rec_hash = hash(f"{what}:{before}:{after}")
                    elif hasattr(rec, "what") and hasattr(rec, "before_text") and hasattr(rec, "after_text"):
                        what = rec.what
                        before = rec.before_text[:50] if rec.before_text else ""
                        after = rec.after_text[:50] if rec.after_text else ""
                        rec_hash = hash(f"{what}:{before}:{after}")
                    
                    if rec_hash and rec_hash not in seen_hashes:
                        seen_hashes.add(rec_hash)
                        unique_recs.append(rec)
                        
                merged[list_key] = unique_recs
            else:
                # For other lists, simple deduplication
                if merged[list_key] and isinstance(merged[list_key][0], str):
                    merged[list_key] = list(set(merged[list_key]))
                else:
                    # Complex objects - deduplicate based on string representation
                    seen = set()
                    unique_items = []
                    for item in merged[list_key]:
                        item_str = str(item)
                        if item_str not in seen:
                            seen.add(item_str)
                            unique_items.append(item)
                            
                    merged[list_key] = unique_items
        
        # Merge optimized content if available
        if any("optimized_content" in result for result in results):
            # Combine optimized content from all subsections
            optimized_parts = []
            
            for result in results:
                if "optimized_content" in result and result["optimized_content"]:
                    optimized_parts.append(result["optimized_content"])
                    
            if optimized_parts:
                merged["optimized_content"] = "\n\n".join(optimized_parts)
        
        return merged

# Factory function for easy instantiation
def get_enhanced_parallel_processor() -> EnhancedParallelProcessor:
    """
    Create an instance of the enhanced parallel processor.
    
    Returns:
        Initialized EnhancedParallelProcessor
    """
    return EnhancedParallelProcessor()