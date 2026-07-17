"""
models.py

Dataclasses for the runtime system.
"""

import time
import uuid
import threading
from collections import deque
from dataclasses import dataclass, field
from queue import Queue
from typing import Any, Callable, Deque, Dict, List, Optional

from .enums import (
    RuntimeMode,
    RuntimeState,
    RuntimeEvent,
    RuntimePriority,
    FrameSource,
)


# ============================================================
# Constants
# ============================================================

DEFAULT_FPS = 60
MAX_FRAME_QUEUE = 512
DEFAULT_TIMEOUT = 5.0
DEFAULT_FRAME_TIME = 1.0 / DEFAULT_FPS
MAX_LATENCY_MS = 250.0
DEFAULT_SESSION_NAME = "ARKit Runtime"
RUNTIME_VERSION = "1.0.0"


# ============================================================
# Runtime Frame
# ============================================================

@dataclass(slots=True)
class RuntimeFrame:
    """One frame entering the runtime."""

    coefficients: Dict[Any, float]  # ARKitChannel -> float
    timestamp: float = field(default_factory=time.time)
    frame_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source: FrameSource = FrameSource.ARKIT
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================
# Processed Frame
# ============================================================

@dataclass(slots=True)
class ProcessedFrame:
    """Frame after conversion."""

    runtime_frame: RuntimeFrame
    mapping_result: Any  # MappingResult
    processing_time: float = 0.0
    latency_ms: float = 0.0


# ============================================================
# Runtime Statistics
# ============================================================

@dataclass(slots=True)
class RuntimeStatistics:
    """Runtime performance statistics."""

    session_start: float = 0.0
    session_end: float = 0.0
    received_frames: int = 0
    processed_frames: int = 0
    dropped_frames: int = 0
    playback_frames: int = 0
    recorded_frames: int = 0
    callback_count: int = 0
    errors: int = 0
    average_latency: float = 0.0
    maximum_latency: float = 0.0
    average_processing_time: float = 0.0
    fps: float = DEFAULT_FPS

    def reset(self) -> None:
        self.session_start = 0.0
        self.session_end = 0.0
        self.received_frames = 0
        self.processed_frames = 0
        self.dropped_frames = 0
        self.playback_frames = 0
        self.recorded_frames = 0
        self.callback_count = 0
        self.errors = 0
        self.average_latency = 0.0
        self.maximum_latency = 0.0
        self.average_processing_time = 0.0
        self.fps = DEFAULT_FPS


# ============================================================
# Runtime Callback
# ============================================================

@dataclass(slots=True)
class RuntimeCallback:
    """Registered runtime callback."""

    event: RuntimeEvent
    callback: Callable[..., Any]
    priority: RuntimePriority = RuntimePriority.NORMAL
    enabled: bool = True
    once: bool = False


# ============================================================
# Runtime Configuration
# ============================================================

@dataclass(slots=True)
class RuntimeConfig:
    """Runtime configuration."""

    fps: int = DEFAULT_FPS
    max_queue_size: int = MAX_FRAME_QUEUE
    smoothing_enabled: bool = True
    recording_enabled: bool = False
    playback_enabled: bool = False
    profiling_enabled: bool = False
    threaded: bool = True
    auto_start: bool = False
    timeout: float = DEFAULT_TIMEOUT


# ============================================================
# Runtime Session
# ============================================================

@dataclass(slots=True)
class RuntimeSession:
    """Represents one runtime session."""

    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = DEFAULT_SESSION_NAME
    mode: RuntimeMode = RuntimeMode.LIVE
    state: RuntimeState = RuntimeState.CREATED
    started_at: float = 0.0
    stopped_at: float = 0.0
    converter: Optional[Any] = None  # ARKitConverter
    statistics: RuntimeStatistics = field(default_factory=RuntimeStatistics)
    configuration: RuntimeConfig = field(default_factory=RuntimeConfig)
    frame_queue: Queue = field(default_factory=lambda: Queue(MAX_FRAME_QUEUE))
    processed_frames: Deque[ProcessedFrame] = field(
        default_factory=lambda: deque(maxlen=MAX_FRAME_QUEUE)
    )
    callbacks: List[RuntimeCallback] = field(default_factory=list)
    thread: Optional[threading.Thread] = None
    stop_event: threading.Event = field(default_factory=threading.Event)


# ============================================================
# Performance Snapshot
# ============================================================

@dataclass(slots=True)
class PerformanceSnapshot:
    """Immutable snapshot of runtime performance."""

    timestamp: float
    fps: float
    average_latency: float
    maximum_latency: float
    average_processing_time: float
    queue_size: int
    queue_usage: float
    processed_frames: int
    dropped_frames: int
    callback_count: int
    memory_usage: float = 0.0
    cpu_usage: float = 0.0


# ============================================================
# Runtime Metrics
# ============================================================

@dataclass(slots=True)
class RuntimeMetrics:
    """Long-term runtime statistics for profiling."""

    snapshots: List[PerformanceSnapshot] = field(default_factory=list)
    frame_times: List[float] = field(default_factory=list)
    latencies: List[float] = field(default_factory=list)
    processing_times: List[float] = field(default_factory=list)
    fps_history: List[float] = field(default_factory=list)
    max_history: int = 10000

    def add_snapshot(self, snapshot: PerformanceSnapshot) -> None:
        self.snapshots.append(snapshot)
        self.frame_times.append(snapshot.timestamp)
        self.latencies.append(snapshot.average_latency)
        self.processing_times.append(snapshot.average_processing_time)
        self.fps_history.append(snapshot.fps)
        self._trim()

    def _trim(self) -> None:
        if len(self.snapshots) <= self.max_history:
            return
        self.snapshots.pop(0)
        self.frame_times.pop(0)
        self.latencies.pop(0)
        self.processing_times.pop(0)
        self.fps_history.pop(0)

    def clear(self) -> None:
        self.snapshots.clear()
        self.frame_times.clear()
        self.latencies.clear()
        self.processing_times.clear()
        self.fps_history.clear()


# ============================================================
# Runtime Event Record
# ============================================================

@dataclass(slots=True)
class RuntimeEventRecord:
    """Record of a runtime event."""

    timestamp: float
    event: RuntimeEvent
    source: str
    message: str = ""
    data: Optional[Dict[str, Any]] = None


# ============================================================
# Runtime Error Record
# ============================================================

@dataclass(slots=True)
class RuntimeErrorRecord:
    """Exception information."""

    timestamp: float
    exception_type: str
    message: str
    traceback_text: str