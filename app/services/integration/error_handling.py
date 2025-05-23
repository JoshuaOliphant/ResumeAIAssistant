"""
Error Handling and Recovery for ResumeAIAssistant.

This module implements error handling and recovery mechanisms for the integrated
components, including circuit breakers, fallback strategies, and partial result handling.
"""

import time
import asyncio
import threading
from typing import Dict, Any, Optional, Callable, Awaitable, List, Type
import logging
import logfire

from app.services.integration.interfaces import ErrorHandler, Task, TaskResult, CircuitBreaker


class ServiceStatus:
    """Tracks the status of external services for circuit breaking."""
    UP = "up"
    DOWN = "down"
    DEGRADED = "degraded"


class IntegratedCircuitBreaker(CircuitBreaker):
    """Implementation of the CircuitBreaker interface for service protection."""
    
    def __init__(self, failure_threshold: int = 3, recovery_time_seconds: int = 60):
        """
        Initialize the circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_time_seconds: Time to wait before allowing retry
        """
        self.failure_threshold = failure_threshold
        self.recovery_time_seconds = recovery_time_seconds
        self.service_status: Dict[str, str] = {}
        self.failure_counts: Dict[str, int] = {}
        self.last_failure_time: Dict[str, float] = {}
        self._lock = threading.Lock()
        
    def is_open(self, service_name: str) -> bool:
        """
        Check if circuit is open for the service.
        
        Args:
            service_name: Name of the service to check
            
        Returns:
            True if circuit is open (requests should not be allowed)
        """
        with self._lock:
            if service_name not in self.service_status:
                self.service_status[service_name] = ServiceStatus.UP
                self.failure_counts[service_name] = 0
                return False
                
            # Check if circuit is open
            if self.service_status[service_name] == ServiceStatus.DOWN:
                # Check if recovery time has elapsed
                last_failure = self.last_failure_time.get(service_name, 0)
                time_since_failure = time.time() - last_failure
                
                if time_since_failure >= self.recovery_time_seconds:
                    # Allow a single request to test recovery
                    self.service_status[service_name] = ServiceStatus.DEGRADED
                    logfire.info(
                        f"Circuit for {service_name} switched from OPEN to HALF-OPEN after recovery time",
                        service=service_name,
                        time_since_failure=time_since_failure
                    )
                    return False
                else:
                    # Circuit is still open
                    return True
            else:
                # Circuit is closed or degraded
                return False
    
    def record_success(self, service_name: str) -> None:
        """
        Record a successful call to the service.
        
        Args:
            service_name: Name of the service
        """
        with self._lock:
            if service_name not in self.service_status:
                self.service_status[service_name] = ServiceStatus.UP
                self.failure_counts[service_name] = 0
                return
                
            # If service was degraded, fully restore it after success
            if self.service_status[service_name] == ServiceStatus.DEGRADED:
                self.service_status[service_name] = ServiceStatus.UP
                self.failure_counts[service_name] = 0
                logfire.info(
                    f"Circuit for {service_name} restored to CLOSED after successful call",
                    service=service_name
                )
            
            # Reset failure count for this service
            self.failure_counts[service_name] = 0
    
    def record_failure(self, service_name: str) -> None:
        """
        Record a failed call to the service.
        
        Args:
            service_name: Name of the service
        """
        with self._lock:
            if service_name not in self.service_status:
                self.service_status[service_name] = ServiceStatus.UP
                self.failure_counts[service_name] = 1
                self.last_failure_time[service_name] = time.time()
                return
                
            # Increment failure count
            self.failure_counts[service_name] += 1
            self.last_failure_time[service_name] = time.time()
            
            # Check if threshold reached
            if self.failure_counts[service_name] >= self.failure_threshold:
                # If service was up or degraded, trip the circuit
                if self.service_status[service_name] != ServiceStatus.DOWN:
                    old_status = self.service_status[service_name]
                    self.service_status[service_name] = ServiceStatus.DOWN
                    logfire.warning(
                        f"Circuit breaker for {service_name} OPENED after {self.failure_counts[service_name]} failures",
                        service=service_name,
                        failure_count=self.failure_counts[service_name],
                        previous_status=old_status
                    )


class RecoveryStrategy:
    """Base class for recovery strategies."""
    
    async def handle(self, error: Exception, task: Task, context: Dict[str, Any]) -> TaskResult:
        """
        Handle error with recovery strategy.
        
        Args:
            error: The error that occurred
            task: The task that failed
            context: Task execution context
            
        Returns:
            Task result after recovery
        """
        raise NotImplementedError("Recovery strategies must implement handle method")


class RetryStrategy(RecoveryStrategy):
    """Recovery strategy that retries the task."""
    
    def __init__(self, max_retries: int = 3, backoff_factor: float = 1.5):
        """
        Initialize retry strategy.
        
        Args:
            max_retries: Maximum number of retry attempts
            backoff_factor: Factor to increase wait time between retries
        """
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
    
    async def handle(self, error: Exception, task: Task, context: Dict[str, Any]) -> TaskResult:
        """
        Handle error by retrying the task.
        
        Args:
            error: The error that occurred
            task: The task that failed
            context: Task execution context
            
        Returns:
            Task result after recovery attempts
        """
        # Add retry count to context if not already present
        if "retry_count" not in context:
            context["retry_count"] = 0
            
        # Check if we've exceeded max retries
        if context["retry_count"] >= self.max_retries:
            logfire.warning(
                f"Task {task.name} failed after {self.max_retries} retries",
                task_id=task.id,
                error=str(error)
            )
            return TaskResult(
                success=False,
                error=f"Failed after {self.max_retries} retries: {str(error)}"
            )
            
        # Increment retry count
        context["retry_count"] += 1
        current_retry = context["retry_count"]
        
        # Calculate backoff time
        wait_time = self.backoff_factor ** (current_retry - 1)
        
        logfire.info(
            f"Retrying task {task.name} (attempt {current_retry}/{self.max_retries}) after {wait_time}s",
            task_id=task.id,
            retry_count=current_retry,
            wait_time=wait_time
        )
        
        # Wait before retry
        await asyncio.sleep(wait_time)
        
        # Retry the task
        try:
            return await task.execute(context)
        except Exception as retry_error:
            # Recursive retry
            return await self.handle(retry_error, task, context)


class FallbackStrategy(RecoveryStrategy):
    """Recovery strategy that uses a fallback implementation."""
    
    def __init__(self, fallback_function: Callable[[Task, Dict[str, Any]], Awaitable[TaskResult]]):
        """
        Initialize fallback strategy.
        
        Args:
            fallback_function: Function to call as fallback
        """
        self.fallback_function = fallback_function
    
    async def handle(self, error: Exception, task: Task, context: Dict[str, Any]) -> TaskResult:
        """
        Handle error by using fallback implementation.
        
        Args:
            error: The error that occurred
            task: The task that failed
            context: Task execution context
            
        Returns:
            Task result from fallback
        """
        logfire.info(
            f"Using fallback for task {task.name}",
            task_id=task.id,
            original_error=str(error)
        )
        
        # Add original error to context
        context["original_error"] = str(error)
        
        try:
            # Call fallback function
            return await self.fallback_function(task, context)
        except Exception as fallback_error:
            # Fallback also failed
            logfire.error(
                f"Fallback for task {task.name} also failed",
                task_id=task.id,
                original_error=str(error),
                fallback_error=str(fallback_error)
            )
            
            return TaskResult(
                success=False,
                error=f"Both primary and fallback failed: {str(fallback_error)}"
            )


class PartialResultsStrategy(RecoveryStrategy):
    """Recovery strategy that returns partial results."""
    
    async def handle(self, error: Exception, task: Task, context: Dict[str, Any]) -> TaskResult:
        """
        Handle error by constructing partial results.
        
        Args:
            error: The error that occurred
            task: The task that failed
            context: Task execution context
            
        Returns:
            Task result with partial data
        """
        logfire.info(
            f"Constructing partial results for task {task.name}",
            task_id=task.id,
            error=str(error)
        )
        
        # Create partial results based on task type
        partial_results = self._generate_partial_results(task, context)
        
        return TaskResult(
            success=True,  # Mark as successful but with partial data
            data=partial_results,
            error=f"Partial results due to: {str(error)}"
        )
    
    def _generate_partial_results(self, task: Task, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate partial results based on task type and available context.
        
        Args:
            task: The task that failed
            context: Task execution context
            
        Returns:
            Partial results dictionary
        """
        # Default partial results (override in subclasses for specific tasks)
        partial = {
            "is_partial": True,
            "task_id": task.id,
            "task_name": task.name
        }
        
        # Try to extract useful information from context
        if "input" in context:
            partial["input_summary"] = str(context["input"])[:100] + "..."
            
        return partial


class IntegratedErrorHandler(ErrorHandler):
    """Implementation of the ErrorHandler interface for error recovery."""
    
    def __init__(self):
        """Initialize the error handler."""
        self.recovery_strategies: Dict[type, RecoveryStrategy] = {}
        self.circuit_breaker = IntegratedCircuitBreaker()
        
        # Register default strategies
        self._register_default_strategies()
    
    async def handle_error(self, error: Exception, task: Task, 
                          context: Dict[str, Any]) -> TaskResult:
        """
        Handle error with appropriate recovery strategy.
        
        Args:
            error: The error that occurred
            task: The task that failed
            context: Task execution context
            
        Returns:
            Task result after recovery attempt
        """
        # Find the most specific strategy that applies
        strategy = self._find_strategy(type(error))
        
        if strategy:
            # Apply recovery strategy
            return await strategy.handle(error, task, context)
        else:
            # No specific strategy, return error result
            return TaskResult(
                success=False,
                error=str(error)
            )
    
    def register_recovery_strategy(self, error_type: type, 
                                  strategy: Callable[[Exception, Task, Dict[str, Any]], 
                                                   Awaitable[TaskResult]]) -> None:
        """
        Register a recovery strategy for a specific error type.
        
        Args:
            error_type: Type of error to handle
            strategy: Strategy function
        """
        # Create strategy wrapper if needed
        if not isinstance(strategy, RecoveryStrategy):
            async def strategy_wrapper(err: Exception, tsk: Task, ctx: Dict[str, Any]) -> TaskResult:
                return await strategy(err, tsk, ctx)
                
            wrapped_strategy = type("CustomStrategy", (RecoveryStrategy,), {"handle": strategy_wrapper})()
            self.recovery_strategies[error_type] = wrapped_strategy
        else:
            self.recovery_strategies[error_type] = strategy
    
    def _register_default_strategies(self) -> None:
        """Register default recovery strategies."""
        # Timeout errors get retry strategy
        self.recovery_strategies[asyncio.TimeoutError] = RetryStrategy(max_retries=2)
        
        # Connection errors get retry with longer backoff
        self.recovery_strategies[ConnectionError] = RetryStrategy(max_retries=3, backoff_factor=2.0)
        
        # General exceptions get partial results strategy
        self.recovery_strategies[Exception] = PartialResultsStrategy()
    
    def _find_strategy(self, error_type: Type[Exception]) -> Optional[RecoveryStrategy]:
        """
        Find the most specific strategy for an error type.
        
        Args:
            error_type: Type of error to handle
            
        Returns:
            Recovery strategy or None if no matching strategy
        """
        # Check for exact match
        if error_type in self.recovery_strategies:
            return self.recovery_strategies[error_type]
            
        # Check for parent class matches (most specific first)
        for registered_type, strategy in self.recovery_strategies.items():
            if issubclass(error_type, registered_type):
                return strategy
                
        # No match found
        return None


class PartialResultsHandler:
    """Utility for handling partial results when some tasks fail."""
    
    @staticmethod
    def assemble_best_result(successful_results: Dict[str, Any], 
                            failed_tasks: List[Task], 
                            context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create the best possible result from partial successes.
        
        Args:
            successful_results: Results from successful tasks
            failed_tasks: List of failed tasks
            context: Execution context
            
        Returns:
            Assembled result with best available data
        """
        # Start with a base structure
        result = {
            "success": True,
            "is_partial": True,
            "failed_components": [task.name for task in failed_tasks],
            "successful_components": list(successful_results.keys()),
            "results": successful_results
        }
        
        # Try to provide a useful overall result depending on the specific case
        # This logic would need customization for different types of operations
        
        # Example: If we're analyzing a resume and some sections failed
        if "analyzing_resume" in context.get("operation_type", ""):
            # Include results for successful sections
            result["section_results"] = {
                name: data for name, data in successful_results.items()
                if name.startswith("analyze_")
            }
            
            # Provide a partial match score based on available data
            scores = [
                data.get("score", 0) for name, data in successful_results.items()
                if name.startswith("analyze_") and isinstance(data, dict)
            ]
            
            if scores:
                result["match_score"] = sum(scores) / len(scores)
            else:
                result["match_score"] = 0
        
        return result
