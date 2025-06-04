from contextlib import contextmanager
from typing import Any, Dict, List
import psutil
import os
import time

class PerformanceMonitor:
    """Collects execution time and memory usage metrics with error handling."""

    def __init__(self) -> None:
        self.records: List[Dict[str, Any]] = []
        self._start_time: float = 0.0
        self._start_mem: int = 0

    def start(self) -> None:
        """Start performance monitoring with error handling."""
        try:
            self._start_time = time.perf_counter()
            process = psutil.Process(os.getpid())
            self._start_mem = process.memory_info().rss
        except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
            # If we can't access process info, set to 0 and continue
            self._start_mem = 0
        except Exception:
            # For any other unexpected errors, set to 0 and continue
            self._start_mem = 0

    def stop(self, name: str) -> None:
        """Stop performance monitoring and record metrics."""
        try:
            duration = time.perf_counter() - self._start_time
            
            # Try to get current memory usage
            try:
                end_mem = psutil.Process(os.getpid()).memory_info().rss
                memory_diff = end_mem - self._start_mem
            except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
                # If we can't get memory info, record what we can
                end_mem = 0
                memory_diff = 0
            
            self.records.append({
                "name": name,
                "duration": duration,
                "memory_diff": memory_diff,
                "memory_end": end_mem,
                "memory_start": self._start_mem
            })
        except Exception:
            # If anything fails, record minimal info
            self.records.append({
                "name": name,
                "duration": 0.0,
                "memory_diff": 0,
                "memory_end": 0,
                "memory_start": 0,
                "error": True
            })

    def summary(self) -> Dict[str, Any]:
        """Generate performance summary with error handling."""
        if not self.records:
            return {
                "count": 0, 
                "average_time": 0.0, 
                "average_memory": 0,
                "total_time": 0.0,
                "max_time": 0.0,
                "min_time": 0.0,
                "errors": 0
            }
        
        valid_records = [r for r in self.records if not r.get("error", False)]
        error_count = len(self.records) - len(valid_records)
        
        if not valid_records:
            return {
                "count": len(self.records),
                "average_time": 0.0,
                "average_memory": 0,
                "total_time": 0.0,
                "max_time": 0.0,
                "min_time": 0.0,
                "errors": error_count
            }
        
        durations = [r["duration"] for r in valid_records]
        memory_diffs = [r["memory_diff"] for r in valid_records]
        
        total_time = sum(durations)
        total_mem = sum(memory_diffs)
        count = len(valid_records)
        
        return {
            "count": count,
            "average_time": total_time / count,
            "average_memory": total_mem / count,
            "total_time": total_time,
            "max_time": max(durations) if durations else 0.0,
            "min_time": min(durations) if durations else 0.0,
            "errors": error_count
        }

@contextmanager
def monitor(name: str, perf: PerformanceMonitor):
    """Context manager for scoped performance monitoring."""
    perf.start()
    try:
        yield
    finally:
        perf.stop(name)
