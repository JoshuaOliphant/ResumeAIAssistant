"""
Smart Request Handler for optimizing API request processing.

This module provides intelligent request handling capabilities to enhance
the performance, reliability, and cost-effectiveness of API requests by:

1. Request Prioritization: Automatically prioritize requests based on importance
2. Context-Aware Model Selection: Choose optimal model based on request context
3. Request Batching: Combine similar requests to reduce API calls
4. Timeout Management: Intelligent timeout settings based on request complexity
5. Resource Optimization: Distributing requests based on system load
6. Failure Recovery: Automatic recovery mechanisms for failed requests
"""

import asyncio
import time
import json
import logfire
import uuid
import threading
from enum import Enum
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Union, Tuple, Set
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp

from app.core.config import settings
from app.services.model_optimizer import (
    TaskImportance, 
    CircuitBreaker, 
    record_model_failure,
    track_token_usage
)
from app.services.thinking_budget import TaskComplexity, get_task_complexity_from_content
from app.core.parallel_config import TASK_TIMEOUT_SECONDS

# Default request timeout values based on complexity
REQUEST_TIMEOUT_MAPPING = {
    TaskComplexity.SIMPLE: 15,      # 15 seconds for simple requests
    TaskComplexity.MODERATE: 30,    # 30 seconds for moderate requests
    TaskComplexity.COMPLEX: 45,     # 45 seconds for complex requests
    TaskComplexity.VERY_COMPLEX: 60, # 60 seconds for very complex requests
    TaskComplexity.CRITICAL: 90,    # 90 seconds for critical requests
}

# Request priority mapping
class RequestPriority(int, Enum):
    """Priority levels for API requests"""
    CRITICAL = 1  # User-facing requests that block UI
    HIGH = 2      # Important requests that affect user experience
    MEDIUM = 3    # Standard requests
    LOW = 4       # Background or non-critical requests
    
# Request status for tracking
class RequestStatus(str, Enum):
    """Status of request processing"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"

# Circuit breaker for request rate limiting
request_circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_time_seconds=60)
request_circuit_breaker_lock = threading.Lock()

# Request tracking store
class RequestTracker:
    """Track and manage API requests for optimization and monitoring"""
    
    def __init__(self):
        self.requests: Dict[str, Dict[str, Any]] = {}
        self.active_requests_count: Dict[str, int] = {}  # endpoint -> count
        self.endpoint_timeouts: Dict[str, Dict[TaskComplexity, int]] = {}  # endpoint -> complexity -> timeout
        self.rate_limits: Dict[str, int] = {}  # endpoint -> requests per minute
        self.endpoint_failures: Dict[str, int] = {}  # endpoint -> failure count
        self._lock = threading.Lock()
        
    def register_request(
        self, 
        request_id: str, 
        endpoint: str, 
        priority: RequestPriority = RequestPriority.MEDIUM,
        complexity: TaskComplexity = TaskComplexity.MODERATE
    ) -> None:
        """
        Register a new request for tracking
        
        Args:
            request_id: Unique ID for the request
            endpoint: API endpoint being called
            priority: Priority level for the request
            complexity: Complexity level of the request
        """
        with self._lock:
            self.requests[request_id] = {
                "endpoint": endpoint,
                "start_time": time.time(),
                "status": RequestStatus.PENDING,
                "priority": priority,
                "complexity": complexity,
                "timeout": REQUEST_TIMEOUT_MAPPING.get(complexity, 30),
                "end_time": None,
                "duration": None,
                "error": None
            }
            
            # Increment active request count for this endpoint
            if endpoint in self.active_requests_count:
                self.active_requests_count[endpoint] += 1
            else:
                self.active_requests_count[endpoint] = 1
                
    def update_request_status(
        self, 
        request_id: str, 
        status: RequestStatus,
        error: Optional[str] = None
    ) -> None:
        """
        Update the status of a request
        
        Args:
            request_id: ID of the request to update
            status: New status of the request
            error: Optional error message if request failed
        """
        with self._lock:
            if request_id in self.requests:
                self.requests[request_id]["status"] = status
                
                if status in [RequestStatus.COMPLETED, RequestStatus.FAILED, RequestStatus.TIMEOUT]:
                    # Record end time and duration
                    self.requests[request_id]["end_time"] = time.time()
                    self.requests[request_id]["duration"] = (
                        self.requests[request_id]["end_time"] - 
                        self.requests[request_id]["start_time"]
                    )
                    
                    # Decrement active request count
                    endpoint = self.requests[request_id]["endpoint"]
                    if endpoint in self.active_requests_count and self.active_requests_count[endpoint] > 0:
                        self.active_requests_count[endpoint] -= 1
                
                if error:
                    self.requests[request_id]["error"] = error
                    
                    # Update endpoint failure tracking
                    endpoint = self.requests[request_id]["endpoint"]
                    if endpoint in self.endpoint_failures:
                        self.endpoint_failures[endpoint] += 1
                    else:
                        self.endpoint_failures[endpoint] = 1
    
    def get_request(self, request_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific request
        
        Args:
            request_id: ID of the request
            
        Returns:
            Dictionary with request information or None if not found
        """
        with self._lock:
            return self.requests.get(request_id)
    
    def get_active_requests_count(self, endpoint: str) -> int:
        """
        Get the count of active requests for an endpoint
        
        Args:
            endpoint: API endpoint
            
        Returns:
            Count of active requests
        """
        with self._lock:
            return self.active_requests_count.get(endpoint, 0)
    
    def get_endpoint_statistics(self, endpoint: str) -> Dict[str, Any]:
        """
        Get statistics for a specific endpoint
        
        Args:
            endpoint: API endpoint
            
        Returns:
            Dictionary with endpoint statistics
        """
        with self._lock:
            # Filter requests for this endpoint
            endpoint_requests = [r for r in self.requests.values() if r["endpoint"] == endpoint]
            
            # Calculate statistics
            total_requests = len(endpoint_requests)
            completed_requests = len([r for r in endpoint_requests if r["status"] == RequestStatus.COMPLETED])
            failed_requests = len([r for r in endpoint_requests if r["status"] == RequestStatus.FAILED])
            active_requests = self.active_requests_count.get(endpoint, 0)
            
            # Calculate average duration for completed requests
            durations = [r["duration"] for r in endpoint_requests if r["duration"] is not None]
            avg_duration = sum(durations) / len(durations) if durations else 0
            
            # Get failures count
            failures = self.endpoint_failures.get(endpoint, 0)
            
            return {
                "endpoint": endpoint,
                "total_requests": total_requests,
                "completed_requests": completed_requests,
                "failed_requests": failed_requests,
                "active_requests": active_requests,
                "avg_duration": avg_duration,
                "failure_count": failures,
                "success_rate": (completed_requests / total_requests) * 100 if total_requests > 0 else 0
            }
    
    def clear_old_requests(self, max_age_hours: int = 24) -> int:
        """
        Clear requests older than the specified age
        
        Args:
            max_age_hours: Maximum age in hours for requests to keep
            
        Returns:
            Number of requests cleared
        """
        with self._lock:
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            to_remove = []
            for request_id, request_data in self.requests.items():
                # Check if request has ended and is older than max age
                if (
                    request_data["end_time"] is not None and 
                    (current_time - request_data["end_time"]) > max_age_seconds
                ):
                    to_remove.append(request_id)
            
            # Remove old requests
            for request_id in to_remove:
                del self.requests[request_id]
                
            return len(to_remove)
    
    def should_throttle_request(self, endpoint: str) -> bool:
        """
        Check if requests to an endpoint should be throttled
        
        Args:
            endpoint: API endpoint
            
        Returns:
            True if request should be throttled, False otherwise
        """
        with self._lock:
            # Check if endpoint has exceeded failure threshold
            failure_count = self.endpoint_failures.get(endpoint, 0)
            if failure_count >= 5:  # Throttle after 5 failures
                return True
                
            # Check current active requests against limit
            active = self.active_requests_count.get(endpoint, 0)
            limit = settings.MAX_CONCURRENT_TASKS if hasattr(settings, 'MAX_CONCURRENT_TASKS') else 5
            return active >= limit
    
    def optimize_request_timeout(self, endpoint: str, complexity: TaskComplexity) -> int:
        """
        Dynamically optimize request timeout based on historical performance
        
        Args:
            endpoint: API endpoint
            complexity: Request complexity
            
        Returns:
            Optimized timeout in seconds
        """
        with self._lock:
            # Get all completed requests for this endpoint
            endpoint_requests = [
                r for r in self.requests.values() 
                if r["endpoint"] == endpoint and 
                r["status"] == RequestStatus.COMPLETED and
                r["complexity"] == complexity and
                r["duration"] is not None
            ]
            
            if not endpoint_requests:
                # No historical data, use default
                return REQUEST_TIMEOUT_MAPPING.get(complexity, 30)
            
            # Calculate 95th percentile duration
            durations = sorted([r["duration"] for r in endpoint_requests])
            p95_index = int(len(durations) * 0.95)
            p95_duration = durations[p95_index] if p95_index < len(durations) else durations[-1]
            
            # Add 50% buffer to p95 duration
            optimized_timeout = p95_duration * 1.5
            
            # Ensure within reasonable bounds (min 5s, max 120s)
            optimized_timeout = max(5, min(optimized_timeout, 120))
            
            # Update stored timeout for this endpoint and complexity
            if endpoint not in self.endpoint_timeouts:
                self.endpoint_timeouts[endpoint] = {}
            self.endpoint_timeouts[endpoint][complexity] = int(optimized_timeout)
            
            return int(optimized_timeout)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get overall request statistics
        
        Returns:
            Dictionary with request statistics
        """
        with self._lock:
            # Calculate overall statistics
            total_requests = len(self.requests)
            completed_requests = len([r for r in self.requests.values() if r["status"] == RequestStatus.COMPLETED])
            failed_requests = len([r for r in self.requests.values() if r["status"] == RequestStatus.FAILED])
            active_requests = sum(self.active_requests_count.values())
            
            # Get statistics by endpoint
            endpoint_stats = {}
            all_endpoints = set([r["endpoint"] for r in self.requests.values()])
            for endpoint in all_endpoints:
                endpoint_stats[endpoint] = self.get_endpoint_statistics(endpoint)
            
            # Calculate response time percentiles for completed requests
            durations = [r["duration"] for r in self.requests.values() if r["duration"] is not None]
            
            # Return statistics
            return {
                "total_requests": total_requests,
                "completed_requests": completed_requests,
                "failed_requests": failed_requests,
                "active_requests": active_requests,
                "success_rate": (completed_requests / total_requests) * 100 if total_requests > 0 else 0,
                "endpoints": endpoint_stats,
                "response_times": {
                    "min": min(durations) if durations else 0,
                    "max": max(durations) if durations else 0,
                    "avg": sum(durations) / len(durations) if durations else 0,
                    "p50": sorted(durations)[len(durations) // 2] if durations else 0,
                    "p95": sorted(durations)[int(len(durations) * 0.95)] if durations and int(len(durations) * 0.95) < len(durations) else 0,
                    "p99": sorted(durations)[int(len(durations) * 0.99)] if durations and int(len(durations) * 0.99) < len(durations) else 0
                }
            }

# Global tracker instance
request_tracker = RequestTracker()

# Request queue for prioritization
class RequestQueue:
    """Queue for prioritizing and batching requests"""
    
    def __init__(self, max_size: int = 1000, max_batch_size: int = 5):
        self.max_size = max_size
        self.max_batch_size = max_batch_size
        self.queues: Dict[RequestPriority, Dict[str, List[Dict[str, Any]]]] = {
            priority: {} for priority in RequestPriority
        }
        self._lock = threading.Lock()
        self._not_empty = threading.Condition(self._lock)
        self._executor = None
        self._running = False
        
    def add_request(
        self, 
        request_id: str, 
        endpoint: str, 
        payload: Dict[str, Any],
        priority: RequestPriority = RequestPriority.MEDIUM
    ) -> bool:
        """
        Add a request to the queue
        
        Args:
            request_id: Unique ID for the request
            endpoint: API endpoint
            payload: Request payload
            priority: Priority level
            
        Returns:
            True if request was added, False if queue is full
        """
        with self._lock:
            # Initialize endpoint queue if it doesn't exist
            if endpoint not in self.queues[priority]:
                self.queues[priority][endpoint] = []
            
            # Check if queue is full
            total_requests = sum(len(queue) for pq in self.queues.values() for queue in pq.values())
            if total_requests >= self.max_size:
                return False
            
            # Add request to queue
            self.queues[priority][endpoint].append({
                "request_id": request_id,
                "payload": payload,
                "added_time": time.time()
            })
            
            # Notify that queue is not empty
            self._not_empty.notify()
            
            return True
            
    def get_next_batch(
        self, 
        endpoint: Optional[str] = None,
        max_wait_time: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Get the next batch of requests to process
        
        Args:
            endpoint: Optional endpoint to get requests for
            max_wait_time: Maximum time in seconds to wait for batch formation
            
        Returns:
            List of requests to process as a batch
        """
        with self._not_empty:
            # Wait until queue is not empty or max wait time is reached
            if self._is_empty():
                self._not_empty.wait(timeout=max_wait_time)
            
            # Get requests in priority order
            batch = []
            for priority in sorted(RequestPriority):
                if endpoint:
                    # Get requests for specific endpoint
                    if endpoint in self.queues[priority]:
                        requests = self.queues[priority][endpoint]
                        batch.extend(requests[:self.max_batch_size - len(batch)])
                        self.queues[priority][endpoint] = requests[self.max_batch_size - len(batch):]
                        
                        if len(batch) >= self.max_batch_size:
                            break
                else:
                    # Get requests for any endpoint
                    for ep, requests in self.queues[priority].items():
                        if requests:
                            # Take as many as possible from this endpoint without exceeding batch size
                            to_take = min(len(requests), self.max_batch_size - len(batch))
                            batch.extend(requests[:to_take])
                            self.queues[priority][ep] = requests[to_take:]
                            
                            if len(batch) >= self.max_batch_size:
                                break
                
                if len(batch) >= self.max_batch_size:
                    break
            
            return batch
    
    def _is_empty(self) -> bool:
        """Check if all queues are empty"""
        for priority_queue in self.queues.values():
            for endpoint_queue in priority_queue.values():
                if endpoint_queue:
                    return False
        return True
    
    def start_processing(
        self,
        process_func: Callable[[List[Dict[str, Any]]], None]
    ) -> None:
        """
        Start background processing of queued requests
        
        Args:
            process_func: Function to process batches of requests
        """
        if self._running:
            return
            
        self._running = True
        
        def _process_queue():
            while self._running:
                batch = self.get_next_batch()
                if batch:
                    try:
                        process_func(batch)
                    except Exception as e:
                        logfire.error(
                            "Error processing request batch", 
                            error=str(e),
                            batch_size=len(batch)
                        )
                else:
                    # Sleep briefly if queue is empty
                    time.sleep(0.1)
        
        # Start processing thread
        import threading
        self._executor = threading.Thread(target=_process_queue, daemon=True)
        self._executor.start()
    
    def stop_processing(self) -> None:
        """Stop background processing"""
        self._running = False
        if self._executor:
            self._executor.join(timeout=1.0)
            self._executor = None

# Global queue instance
request_queue = RequestQueue()

# Request middleware
class SmartRequestMiddleware(BaseHTTPMiddleware):
    """Middleware for smart request handling"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        
    async def dispatch(self, request: Request, call_next) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())
        
        # Extract endpoint path
        endpoint = request.url.path
        
        # Check if we should handle this request with smart handling
        if not self._should_use_smart_handling(endpoint):
            # Skip smart handling for this endpoint
            return await call_next(request)
        
        # Extract API segment for circuit breaker checks
        provider = endpoint.split('/')[2] if len(endpoint.split('/')) > 2 else endpoint
        
        # Check if circuit breaker is open for this endpoint
        with request_circuit_breaker_lock:
            circuit_open = request_circuit_breaker.is_circuit_open(provider)
        
        if circuit_open:
            # Circuit breaker is open, return 503 Service Unavailable
            return Response(
                content=json.dumps({
                    "detail": "Service temporarily unavailable, please try again later",
                    "request_id": request_id
                }),
                status_code=503,
                media_type="application/json"
            )
        
        # Check if we should throttle this endpoint
        if request_tracker.should_throttle_request(endpoint):
            # Return 429 Too Many Requests
            return Response(
                content=json.dumps({
                    "detail": "Too many requests or endpoint experiencing failures, please try again later",
                    "request_id": request_id
                }),
                status_code=429,
                media_type="application/json"
            )
        
        # Analyze request to determine complexity and priority
        complexity, priority = self._analyze_request(request)
        
        # Register request for tracking
        request_tracker.register_request(
            request_id=request_id,
            endpoint=endpoint,
            priority=priority,
            complexity=complexity
        )
        
        # Set optimized timeout
        timeout = request_tracker.optimize_request_timeout(endpoint, complexity)
        
        try:
            # Process request with timeout
            return await asyncio.wait_for(
                self._process_request(request, request_id, call_next),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            # Handle timeout
            request_tracker.update_request_status(
                request_id=request_id,
                status=RequestStatus.TIMEOUT,
                error="Request timed out"
            )
            
            # Record failure in circuit breaker
            with request_circuit_breaker_lock:
                request_circuit_breaker.record_failure(provider)
            
            return Response(
                content=json.dumps({
                    "detail": "Request timed out",
                    "request_id": request_id,
                    "timeout": timeout
                }),
                status_code=408,
                media_type="application/json"
            )
        except Exception as e:
            # Handle other errors
            request_tracker.update_request_status(
                request_id=request_id,
                status=RequestStatus.FAILED,
                error=str(e)
            )
            
            # Record failure in circuit breaker
            with request_circuit_breaker_lock:
                request_circuit_breaker.record_failure(provider)
            
            # Log error
            logfire.error(
                "Error processing request",
                request_id=request_id,
                endpoint=endpoint,
                error=str(e)
            )
            
            # Return error response
            return Response(
                content=json.dumps({
                    "detail": "Internal server error",
                    "request_id": request_id
                }),
                status_code=500,
                media_type="application/json"
            )
    
    def _should_use_smart_handling(self, endpoint: str) -> bool:
        """
        Determine if an endpoint should use smart request handling
        
        Args:
            endpoint: API endpoint path
            
        Returns:
            True if endpoint should use smart handling
        """
        # Skip for static files, health checks, etc.
        if endpoint.startswith(("/static/", "/health", "/metrics", "/docs")):
            return False
            
        # Apply smart handling for specific API endpoints
        smart_endpoints = [
            "/api/v1/ats/analyze", 
            "/api/v1/ats/analyze-and-plan",
            "/api/v1/customize/plan",
            "/api/v1/customize/parallel",
            "/api/v1/cover-letter"
        ]
        
        # Check exact matches
        if endpoint in smart_endpoints:
            return True
            
        # Check prefixes
        for smart_endpoint in smart_endpoints:
            if endpoint.startswith(smart_endpoint):
                return True
                
        # Default to true for other API endpoints
        if endpoint.startswith("/api/v1/"):
            return True
            
        return False
    
    def _analyze_request(self, request: Request) -> Tuple[TaskComplexity, RequestPriority]:
        """
        Analyze request to determine complexity and priority
        
        Args:
            request: The HTTP request
            
        Returns:
            Tuple of (complexity, priority)
        """
        # Default values
        complexity = TaskComplexity.MODERATE
        priority = RequestPriority.MEDIUM
        
        # Analysis based on endpoint
        endpoint = request.url.path
        
        # Critical endpoints (user-facing with long processing)
        if endpoint in ["/api/v1/customize/", "/api/v1/cover-letter/generate"]:
            complexity = TaskComplexity.CRITICAL
            priority = RequestPriority.CRITICAL
            
        # Complex endpoints (user-facing with moderate processing)
        elif endpoint in ["/api/v1/ats/analyze-and-plan", "/api/v1/customize/plan"]:
            complexity = TaskComplexity.COMPLEX
            priority = RequestPriority.HIGH
            
        # Simple endpoints (fast processing)
        elif endpoint in ["/api/v1/ats/analyze", "/api/v1/stats"]:
            complexity = TaskComplexity.SIMPLE
            priority = RequestPriority.MEDIUM
        
        # Adjust based on request method
        if request.method == "GET":
            # GET requests are typically simpler
            # Convert to complexity level one step lower if possible
            complexity_values = list(TaskComplexity)
            current_index = complexity_values.index(complexity)
            if current_index > 0:  # If not already at the lowest complexity
                complexity = complexity_values[current_index - 1]
        
        return complexity, priority
    
    async def _process_request(self, request: Request, request_id: str, call_next) -> Response:
        """
        Process request with tracking and enhanced handling
        
        Args:
            request: The HTTP request
            request_id: Unique ID for the request
            call_next: Function to call the next middleware
            
        Returns:
            HTTP response
        """
        # Update request status to processing
        request_tracker.update_request_status(
            request_id=request_id,
            status=RequestStatus.PROCESSING
        )
        
        # Add request ID to response headers
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        
        # Update request status to completed
        request_tracker.update_request_status(
            request_id=request_id,
            status=RequestStatus.COMPLETED
        )
        
        # Record success in circuit breaker for this endpoint
        endpoint = request.url.path
        provider = endpoint.split('/')[2] if len(endpoint.split('/')) > 2 else endpoint  # Extract API segment as "provider"
        with request_circuit_breaker_lock:
            request_circuit_breaker.record_success(provider)
        
        return response

# Decorator for adding smart request handling to individual API functions
def smart_request(
    complexity: Optional[TaskComplexity] = None,
    priority: Optional[RequestPriority] = None,
    timeout: Optional[int] = None
):
    """
    Decorator to add smart request handling to API functions
    
    Args:
        complexity: Override complexity level for the request
        priority: Override priority level for the request
        timeout: Override timeout in seconds
        
    Returns:
        Decorated function
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Generate request ID if not provided
            request_id = kwargs.pop("request_id", str(uuid.uuid4()))
            
            # Get endpoint from function name
            endpoint = func.__name__
            
            # Extract provider for circuit breaker
            provider = endpoint  # Use function name as provider ID for decorator
            
            # Check if circuit breaker is open
            with request_circuit_breaker_lock:
                circuit_open = request_circuit_breaker.is_circuit_open(provider)
            
            if circuit_open:
                # Circuit breaker is open, fail early
                logfire.warning(
                    "Circuit breaker open for endpoint",
                    endpoint=endpoint,
                    provider=provider,
                    request_id=request_id
                )
                raise HTTPException(
                    status_code=503,
                    detail={
                        "message": "Service temporarily unavailable, please try again later",
                        "request_id": request_id
                    }
                )
            
            # Determine complexity and priority if not provided
            _complexity = complexity
            _priority = priority
            
            if _complexity is None:
                # Try to determine complexity from request content
                content = None
                for arg in args:
                    if hasattr(arg, "model_dump"):
                        content = str(arg.model_dump())
                        break
                
                if content:
                    _complexity, _ = get_task_complexity_from_content(content)
                else:
                    _complexity = TaskComplexity.MODERATE
            
            if _priority is None:
                _priority = RequestPriority.MEDIUM
            
            # Register request for tracking
            request_tracker.register_request(
                request_id=request_id,
                endpoint=endpoint,
                priority=_priority,
                complexity=_complexity
            )
            
            # Determine timeout
            _timeout = timeout
            if _timeout is None:
                _timeout = request_tracker.optimize_request_timeout(endpoint, _complexity)
            
            try:
                # Process request with timeout
                result = await asyncio.wait_for(func(*args, **kwargs), timeout=_timeout)
                
                # Update request status to completed
                request_tracker.update_request_status(
                    request_id=request_id,
                    status=RequestStatus.COMPLETED
                )
                
                # Record success in circuit breaker
                with request_circuit_breaker_lock:
                    request_circuit_breaker.record_success(provider)
                
                # Add request ID to return value if possible
                if isinstance(result, dict):
                    result["request_id"] = request_id
                
                return result
                
            except asyncio.TimeoutError:
                # Handle timeout
                request_tracker.update_request_status(
                    request_id=request_id,
                    status=RequestStatus.TIMEOUT,
                    error="Request timed out"
                )
                
                # Record failure in circuit breaker
                with request_circuit_breaker_lock:
                    request_circuit_breaker.record_failure(provider)
                
                logfire.error(
                    "Request timed out",
                    request_id=request_id,
                    endpoint=endpoint,
                    timeout=_timeout
                )
                
                raise HTTPException(
                    status_code=408,
                    detail={
                        "message": "Request timed out",
                        "request_id": request_id,
                        "timeout": _timeout
                    }
                )
                
            except Exception as e:
                # Handle other errors
                request_tracker.update_request_status(
                    request_id=request_id,
                    status=RequestStatus.FAILED,
                    error=str(e)
                )
                
                # Record failure in circuit breaker
                with request_circuit_breaker_lock:
                    request_circuit_breaker.record_failure(provider)
                
                logfire.error(
                    "Error processing request",
                    request_id=request_id,
                    endpoint=endpoint,
                    error=str(e)
                )
                
                # Re-raise the exception for FastAPI to handle
                raise
        
        return wrapper
    
    return decorator

# Setup functions
def setup_smart_request_handling(app):
    """
    Setup smart request handling middleware
    
    Args:
        app: FastAPI application
    """
    # Add middleware
    app.add_middleware(SmartRequestMiddleware)
    
    # Clean up old requests periodically
    import threading
    
    def _clean_old_requests():
        while True:
            try:
                # Sleep for 1 hour
                time.sleep(3600)
                
                # Clear old requests
                cleared = request_tracker.clear_old_requests()
                if cleared > 0:
                    logfire.info(f"Cleared {cleared} old requests")
            except Exception as e:
                logfire.error(f"Error cleaning old requests: {str(e)}")
    
    # Start cleanup thread
    cleanup_thread = threading.Thread(target=_clean_old_requests, daemon=True)
    cleanup_thread.start()
    
    logfire.info("Smart request handling initialized")

# API to get request statistics
async def get_request_statistics() -> Dict[str, Any]:
    """
    Get statistics about request handling
    
    Returns:
        Dictionary with request statistics
    """
    return request_tracker.get_statistics()

# API to get status of a specific request
async def get_request_status(request_id: str) -> Dict[str, Any]:
    """
    Get status of a specific request
    
    Args:
        request_id: ID of the request
        
    Returns:
        Dictionary with request status
    """
    request_data = request_tracker.get_request(request_id)
    if not request_data:
        raise HTTPException(status_code=404, detail=f"Request {request_id} not found")
    
    return request_data
