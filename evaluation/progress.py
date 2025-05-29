# ABOUTME: Progress tracking system for evaluation runs with ETA calculations
# ABOUTME: Provides real-time progress updates and estimated time remaining
"""
Progress Tracking

Real-time progress tracking for evaluation runs with ETA calculations and
customizable progress callbacks.
"""

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
import threading


@dataclass
class EvaluationProgress:
    """Current progress state of an evaluation run."""
    
    total_cases: int
    total_evaluators: int
    completed_evaluations: int = 0
    
    # Per-case progress
    cases_completed: Set[str] = field(default_factory=set)
    cases_in_progress: Set[str] = field(default_factory=set)
    
    # Per-evaluator progress
    evaluator_progress: Dict[str, int] = field(default_factory=dict)
    
    # Timing
    start_time: float = field(default_factory=time.time)
    evaluation_times: deque = field(default_factory=lambda: deque(maxlen=100))
    
    @property
    def total_evaluations(self) -> int:
        """Total number of evaluations to perform."""
        return self.total_cases * self.total_evaluators
    
    @property
    def progress_percentage(self) -> float:
        """Current progress as a percentage."""
        if self.total_evaluations == 0:
            return 0.0
        return (self.completed_evaluations / self.total_evaluations) * 100
    
    @property
    def elapsed_time(self) -> float:
        """Elapsed time in seconds."""
        return time.time() - self.start_time
    
    def get_eta(self) -> Optional[timedelta]:
        """
        Calculate estimated time remaining.
        
        Returns:
            Estimated time remaining or None if not enough data
        """
        if not self.evaluation_times or self.completed_evaluations == 0:
            return None
        
        # Use moving average of recent evaluation times
        avg_eval_time = sum(self.evaluation_times) / len(self.evaluation_times)
        remaining_evaluations = self.total_evaluations - self.completed_evaluations
        
        eta_seconds = avg_eval_time * remaining_evaluations
        return timedelta(seconds=eta_seconds)
    
    def format_progress(self) -> str:
        """Format progress as a human-readable string."""
        eta = self.get_eta()
        eta_str = f"ETA: {str(eta).split('.')[0]}" if eta else "ETA: calculating..."
        
        return (
            f"Progress: {self.completed_evaluations}/{self.total_evaluations} "
            f"({self.progress_percentage:.1f}%) - {eta_str}"
        )


class ProgressTracker:
    """Tracks progress of evaluation runs with thread-safe updates."""
    
    def __init__(
        self,
        total_cases: int,
        total_evaluators: int,
        show_eta: bool = True,
        update_callback=None
    ):
        """
        Initialize progress tracker.
        
        Args:
            total_cases: Total number of test cases
            total_evaluators: Total number of evaluators
            show_eta: Whether to calculate and show ETA
            update_callback: Optional callback for progress updates
        """
        self.progress = EvaluationProgress(
            total_cases=total_cases,
            total_evaluators=total_evaluators
        )
        self.show_eta = show_eta
        self.update_callback = update_callback
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Track evaluation times for ETA calculation
        self._eval_start_times: Dict[Tuple[str, str], float] = {}
    
    def start_evaluation(self, case_id: str, evaluator_name: str):
        """
        Mark the start of an evaluation.
        
        Args:
            case_id: ID of the test case
            evaluator_name: Name of the evaluator
        """
        with self._lock:
            key = (case_id, evaluator_name)
            self._eval_start_times[key] = time.time()
            self.progress.cases_in_progress.add(case_id)
    
    def update(self, case_id: str, evaluator_name: str, success: bool = True):
        """
        Update progress for a completed evaluation.
        
        Args:
            case_id: ID of the test case
            evaluator_name: Name of the evaluator
            success: Whether the evaluation was successful
        """
        with self._lock:
            # Calculate evaluation time
            key = (case_id, evaluator_name)
            if key in self._eval_start_times:
                eval_time = time.time() - self._eval_start_times[key]
                self.progress.evaluation_times.append(eval_time)
                del self._eval_start_times[key]
            
            # Update progress
            self.progress.completed_evaluations += 1
            
            # Update evaluator-specific progress
            if evaluator_name not in self.progress.evaluator_progress:
                self.progress.evaluator_progress[evaluator_name] = 0
            self.progress.evaluator_progress[evaluator_name] += 1
            
            # Check if all evaluations for this case are complete
            evaluations_for_case = sum(
                1 for k in self._eval_start_times.keys() if k[0] == case_id
            )
            if evaluations_for_case == 0:
                self.progress.cases_completed.add(case_id)
                self.progress.cases_in_progress.discard(case_id)
        
        # Trigger callback if provided
        if self.update_callback:
            self.update_callback(self.get_progress_info())
    
    def get_progress_info(self) -> Dict[str, any]:
        """
        Get current progress information.
        
        Returns:
            Dictionary with progress details
        """
        with self._lock:
            eta = self.progress.get_eta() if self.show_eta else None
            
            return {
                "completed": self.progress.completed_evaluations,
                "total": self.progress.total_evaluations,
                "percentage": self.progress.progress_percentage,
                "cases_completed": len(self.progress.cases_completed),
                "total_cases": self.progress.total_cases,
                "elapsed_time": self.progress.elapsed_time,
                "eta": eta.total_seconds() if eta else None,
                "eta_formatted": str(eta).split('.')[0] if eta else None,
                "evaluator_progress": dict(self.progress.evaluator_progress),
                "formatted": self.progress.format_progress()
            }
    
    def print_progress(self):
        """Print current progress to console."""
        info = self.get_progress_info()
        print(f"\r{info['formatted']}", end='', flush=True)
    
    def get_summary(self) -> str:
        """
        Get a summary of the evaluation run.
        
        Returns:
            Summary string
        """
        with self._lock:
            elapsed = timedelta(seconds=self.progress.elapsed_time)
            avg_time = (
                self.progress.elapsed_time / self.progress.completed_evaluations
                if self.progress.completed_evaluations > 0 else 0
            )
            
            summary = [
                f"Evaluation Summary:",
                f"- Total evaluations: {self.progress.completed_evaluations}/{self.progress.total_evaluations}",
                f"- Cases completed: {len(self.progress.cases_completed)}/{self.progress.total_cases}",
                f"- Total time: {str(elapsed).split('.')[0]}",
                f"- Average time per evaluation: {avg_time:.2f}s"
            ]
            
            # Add per-evaluator breakdown
            if self.progress.evaluator_progress:
                summary.append("\nPer-evaluator breakdown:")
                for name, count in self.progress.evaluator_progress.items():
                    percentage = (count / self.progress.total_cases) * 100
                    summary.append(f"  - {name}: {count} ({percentage:.1f}%)")
            
            return "\n".join(summary)


class ConsoleProgressBar:
    """Simple console progress bar for evaluation tracking."""
    
    def __init__(self, tracker: ProgressTracker, update_interval: float = 1.0):
        """
        Initialize console progress bar.
        
        Args:
            tracker: Progress tracker instance
            update_interval: Seconds between updates
        """
        self.tracker = tracker
        self.update_interval = update_interval
        self._stop_event = threading.Event()
        self._thread = None
    
    def start(self):
        """Start displaying progress."""
        self._thread = threading.Thread(target=self._update_loop)
        self._thread.start()
    
    def stop(self):
        """Stop displaying progress."""
        self._stop_event.set()
        if self._thread:
            self._thread.join()
        print()  # New line after progress
    
    def _update_loop(self):
        """Update loop for console display."""
        while not self._stop_event.is_set():
            self.tracker.print_progress()
            self._stop_event.wait(self.update_interval)