from contextlib import contextmanager
from typing import Any, Dict, List
import psutil
import os
import time

class PerformanceMonitor:
    """Collects execution time and memory usage metrics."""

    def __init__(self) -> None:
        self.records: List[Dict[str, Any]] = []

    def start(self) -> None:
        self._start_time = time.perf_counter()
        self._start_mem = psutil.Process(os.getpid()).memory_info().rss

    def stop(self, name: str) -> None:
        duration = time.perf_counter() - self._start_time
        end_mem = psutil.Process(os.getpid()).memory_info().rss
        self.records.append({
            "name": name,
            "duration": duration,
            "memory": max(0, end_mem - self._start_mem)
        })

    def summary(self) -> Dict[str, Any]:
        if not self.records:
            return {"count": 0, "average_time": 0.0, "average_memory": 0}
        total_time = sum(r["duration"] for r in self.records)
        total_mem = sum(r["memory"] for r in self.records)
        count = len(self.records)
        return {
            "count": count,
            "average_time": total_time / count,
            "average_memory": total_mem / count
        }

@contextmanager
def monitor(name: str, perf: PerformanceMonitor):
    perf.start()
    try:
        yield
    finally:
        perf.stop(name)
