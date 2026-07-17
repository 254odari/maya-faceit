"""
maya_faceit/blendshapes/arkit_mapper/runtime/_init_.py

Real-time runtime manager for facial animation.

This module owns the runtime execution of the facial animation system.
It sits above ARKitConverter and is responsible for:

    • Live Link Face
    • MediaPipe
    • Audio2Face
    • Webcam streams
    • Recorded playback
    • Frame scheduling
    • Runtime statistics
    • Callback events
    • Smoothing
    • Recording
    • Maya communication

Unlike converter.py, this module is stateful and owns
the lifetime of an animation session.
"""

from .enums import (
    RuntimeMode,
    RuntimeState,
    RuntimeEvent,
    RuntimePriority,
    FrameSource,
)
from .models import (
    RuntimeFrame,
    ProcessedFrame,
    RuntimeStatistics,
    RuntimeCallback,
    RuntimeConfig,
    RuntimeSession,
    PerformanceSnapshot,
    RuntimeMetrics,
    RuntimeEventRecord,
    RuntimeErrorRecord,
)
from .session import RuntimeSession
from .manager import RuntimeManager
from .diagnostics import RuntimeDiagnostics
from .profiler import RuntimeProfiler
from .singleton import (
    get_runtime,
    set_runtime,
    reset_runtime,
    shutdown_runtime,
    runtime_exists,
)

__all__ = [
    # Enums
    "RuntimeMode",
    "RuntimeState",
    "RuntimeEvent",
    "RuntimePriority",
    "FrameSource",
    # Models
    "RuntimeFrame",
    "ProcessedFrame",
    "RuntimeStatistics",
    "RuntimeCallback",
    "RuntimeConfig",
    "RuntimeSession",
    "PerformanceSnapshot",
    "RuntimeMetrics",
    "RuntimeEventRecord",
    "RuntimeErrorRecord",
    # Core
    "RuntimeSession",
    "RuntimeManager",
    # Diagnostics & Profiling
    "RuntimeDiagnostics",
    "RuntimeProfiler",
    # Singleton
    "get_runtime",
    "set_runtime",
    "reset_runtime",
    "shutdown_runtime",
    "runtime_exists",
]