"""
profiler.py

RuntimeProfiler - performance profiling and metrics collection.
"""

import time
from statistics import mean
from typing import Optional, Dict, Any

from .models import PerformanceSnapshot, RuntimeMetrics


class RuntimeProfiler:
    """Runtime performance profiler."""

    def __init__(self):
        self.enabled = True
        self.metrics = RuntimeMetrics()
        self.start_time = time.time()

    def capture(self, manager) -> PerformanceSnapshot:
        session = manager.session
        stats = session.statistics
        snapshot = PerformanceSnapshot(
            timestamp=time.time(),
            fps=stats.fps,
            average_latency=stats.average_latency,
            maximum_latency=stats.maximum_latency,
            average_processing_time=stats.average_processing_time,
            queue_size=session.queue_size(),
            queue_usage=session.queue_usage(),
            processed_frames=stats.processed_frames,
            dropped_frames=stats.dropped_frames,
            callback_count=stats.callback_count,
        )
        self.metrics.add_snapshot(snapshot)
        return snapshot

    def reset(self) -> None:
        self.metrics.clear()
        self.start_time = time.time()

    def summary(self) -> Dict[str, Any]:
        return {
            "runtime": time.time() - self.start_time,
            "samples": len(self.metrics.snapshots),
            "average_fps": self.metrics.average_fps,
            "peak_fps": self.metrics.peak_fps,
            "minimum_fps": self.metrics.minimum_fps,
            "average_latency": self.metrics.average_latency,
            "average_processing": self.metrics.average_processing,
        }