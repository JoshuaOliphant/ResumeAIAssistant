# ABOUTME: Configuration classes for TestRunner and evaluation orchestration
# ABOUTME: Defines settings for parallel execution, timeouts, and progress tracking
"""
TestRunner Configuration

Configuration classes and settings for the evaluation test runner, including
parallelism settings, timeouts, and progress tracking options.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Callable
from enum import Enum


class ParallelismStrategy(str, Enum):
    """Strategy for parallel execution of evaluations."""
    
    NONE = "none"                # Sequential execution
    ASYNCIO = "asyncio"          # Asyncio-based concurrency for I/O-bound tasks
    THREAD_POOL = "thread_pool"  # Thread pool for CPU-bound tasks
    ADAPTIVE = "adaptive"        # Automatically choose based on evaluator type


@dataclass
class RetryConfig:
    """Configuration for retry logic."""
    
    max_attempts: int = 3
    initial_delay: float = 1.0  # seconds
    max_delay: float = 60.0     # seconds
    exponential_base: float = 2.0
    jitter: bool = True         # Add random jitter to prevent thundering herd


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker pattern."""
    
    failure_threshold: int = 5   # Number of failures before opening circuit
    recovery_timeout: float = 60.0  # Seconds before attempting recovery
    expected_exception_types: List[type] = field(default_factory=lambda: [Exception])


@dataclass
class ProgressConfig:
    """Configuration for progress tracking."""
    
    enabled: bool = True
    update_interval: float = 1.0  # Seconds between progress updates
    show_eta: bool = True
    show_per_evaluator_progress: bool = True
    callback: Optional[Callable[[Dict[str, Any]], None]] = None


@dataclass
class ResourceLimits:
    """Resource limits for evaluation execution."""
    
    max_concurrent_evaluations: int = 10
    max_tokens_per_minute: Optional[int] = None
    max_api_calls_per_minute: Optional[int] = None
    evaluation_timeout: float = 300.0  # seconds per evaluation
    batch_timeout: float = 3600.0     # seconds for entire batch


@dataclass
class TestRunnerConfig:
    """Main configuration for TestRunner."""
    
    # Parallelism settings
    parallelism_strategy: ParallelismStrategy = ParallelismStrategy.ADAPTIVE
    max_workers: int = 4
    
    # Resource limits
    resource_limits: ResourceLimits = field(default_factory=ResourceLimits)
    
    # Error handling
    retry_config: RetryConfig = field(default_factory=RetryConfig)
    circuit_breaker_config: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    fail_fast: bool = False  # Stop on first failure
    
    # Progress tracking
    progress_config: ProgressConfig = field(default_factory=ProgressConfig)
    
    # Logging and debugging
    verbose: bool = False
    debug: bool = False
    log_failed_cases: bool = True
    save_intermediate_results: bool = True
    
    # Output options
    output_format: str = "json"  # json, yaml, markdown
    include_raw_outputs: bool = False
    aggregate_scores: bool = True
    
    def validate(self) -> None:
        """Validate configuration settings."""
        if self.max_workers < 1:
            raise ValueError("max_workers must be at least 1")
        
        if self.resource_limits.max_concurrent_evaluations < 1:
            raise ValueError("max_concurrent_evaluations must be at least 1")
        
        if self.resource_limits.evaluation_timeout <= 0:
            raise ValueError("evaluation_timeout must be positive")
        
        if self.retry_config.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")


def get_default_config() -> TestRunnerConfig:
    """Get default TestRunner configuration."""
    return TestRunnerConfig()


def get_fast_config() -> TestRunnerConfig:
    """Get configuration optimized for speed."""
    config = TestRunnerConfig()
    config.parallelism_strategy = ParallelismStrategy.ASYNCIO
    config.max_workers = 10
    config.resource_limits.max_concurrent_evaluations = 20
    config.retry_config.max_attempts = 1
    config.progress_config.update_interval = 5.0
    return config


def get_conservative_config() -> TestRunnerConfig:
    """Get configuration for conservative/safe execution."""
    config = TestRunnerConfig()
    config.parallelism_strategy = ParallelismStrategy.NONE
    config.max_workers = 1
    config.resource_limits.max_concurrent_evaluations = 1
    config.resource_limits.evaluation_timeout = 600.0
    config.retry_config.max_attempts = 5
    config.fail_fast = True
    return config