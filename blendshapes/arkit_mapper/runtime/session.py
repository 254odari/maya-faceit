"""
session.py

RuntimeSession - lifecycle, queue, callbacks, statistics.
"""

import time
import threading
from queue import Queue
from typing import Any, Callable, Dict, List, Optional

from .enums import RuntimeEvent, RuntimePriority, RuntimeState, RuntimeMode
from .models import (
    RuntimeSession,
    RuntimeFrame,
    ProcessedFrame,
    RuntimeCallback,
    RuntimeConfig,
    MAX_FRAME_QUEUE,
    DEFAULT_TIMEOUT,
)


class RuntimeSession:
    """
    Represents one runtime session.
    """

    def __init__(
        self,
        name: str = "ARKit Runtime",
        config: Optional[RuntimeConfig] = None,
    ):
        self._session = RuntimeSession(
            name=name,
            configuration=config or RuntimeConfig(),
        )
        self._session.frame_queue = Queue(self._session.configuration.max_queue_size)

    # ============================================================
    # Session Properties
    # ============================================================

    @property
    def session_id(self) -> str:
        return self._session.session_id

    @property
    def state(self) -> RuntimeState:
        return self._session.state

    @property
    def mode(self) -> RuntimeMode:
        return self._session.mode

    @property
    def running(self) -> bool:
        return self._session.state == RuntimeState.RUNNING

    @property
    def paused(self) -> bool:
        return self._session.state == RuntimeState.PAUSED

    @property
    def stopped(self) -> bool:
        return self._session.state == RuntimeState.STOPPED

    @property
    def active(self) -> bool:
        return self._session.state in (RuntimeState.RUNNING, RuntimeState.PAUSED)

    @property
    def uptime(self) -> float:
        if self._session.started_at <= 0.0:
            return 0.0
        if self._session.state == RuntimeState.STOPPED:
            return max(0.0, self._session.stopped_at - self._session.started_at)
        return max(0.0, time.time() - self._session.started_at)

    @property
    def converter(self):
        return self._session.converter

    @property
    def configuration(self) -> RuntimeConfig:
        return self._session.configuration

    @property
    def statistics(self):
        return self._session.statistics

    # ============================================================
    # Lifecycle
    # ============================================================

    def initialize(self, converter) -> None:
        if self._session.state not in (RuntimeState.CREATED, RuntimeState.STOPPED):
            raise RuntimeError(f"Cannot initialize from state '{self._session.state.value}'.")
        self._session.converter = converter
        self._session.statistics.reset()
        self._session.statistics.session_start = time.time()
        self._session.stop_event.clear()
        self._session.state = RuntimeState.INITIALIZED

    def start(self) -> None:
        if self._session.state == RuntimeState.RUNNING:
            return
        if self._session.state not in (RuntimeState.INITIALIZED, RuntimeState.PAUSED, RuntimeState.STOPPED):
            raise RuntimeError(f"Cannot start from '{self._session.state.value}'.")
        self._session.started_at = time.time()
        self._session.statistics.session_start = self._session.started_at
        self._session.stop_event.clear()
        self._session.state = RuntimeState.STARTING
        self._session.state = RuntimeState.RUNNING

    def stop(self) -> None:
        if self._session.state in (RuntimeState.STOPPED, RuntimeState.SHUTDOWN):
            return
        self._session.state = RuntimeState.STOPPING
        self._session.stop_event.set()
        if self._session.thread and self._session.thread.is_alive():
            self._session.thread.join(timeout=2.0)
        self._session.thread = None
        self._session.stopped_at = time.time()
        self._session.statistics.session_end = self._session.stopped_at
        self._session.state = RuntimeState.STOPPED

    def pause(self) -> None:
        if self._session.state == RuntimeState.RUNNING:
            self._session.state = RuntimeState.PAUSED

    def resume(self) -> None:
        if self._session.state == RuntimeState.PAUSED:
            self._session.state = RuntimeState.RUNNING

    def restart(self) -> None:
        converter = self._session.converter
        self.stop()
        self.clear_queue()
        self._session.statistics.reset()
        self._session.stop_event.clear()
        self._session.converter = converter
        self._session.state = RuntimeState.INITIALIZED
        self.start()

    def shutdown(self) -> None:
        if self._session.state == RuntimeState.SHUTDOWN:
            return
        self.stop()
        self.clear_queue()
        self._session.callbacks.clear()
        self._session.converter = None
        self._session.state = RuntimeState.SHUTDOWN

    def reset(self) -> None:
        self.stop()
        self.clear_queue()
        self.clear_processed_frames()
        self._session.callbacks.clear()
        self._session.statistics.reset()
        self._session.started_at = 0.0
        self._session.stopped_at = 0.0
        self._session.stop_event.clear()
        self._session.state = RuntimeState.CREATED

    # ============================================================
    # Queue Management
    # ============================================================

    def submit_frame(self, frame: RuntimeFrame, block: bool = False, timeout: Optional[float] = None) -> bool:
        if self._session.state not in (RuntimeState.RUNNING, RuntimeState.PAUSED):
            return False
        timeout = timeout or self._session.configuration.timeout
        try:
            self._session.frame_queue.put(frame, block=block, timeout=timeout)
            self._session.statistics.received_frames += 1
            return True
        except Exception:
            self._session.statistics.dropped_frames += 1
            return False

    def next_frame(self, block: bool = False, timeout: Optional[float] = None) -> Optional[RuntimeFrame]:
        timeout = timeout or self._session.configuration.timeout
        try:
            return self._session.frame_queue.get(block=block, timeout=timeout)
        except Exception:
            return None

    def frame_available(self) -> bool:
        return not self._session.frame_queue.empty()

    def queue_size(self) -> int:
        return self._session.frame_queue.qsize()

    def queue_empty(self) -> bool:
        return self._session.frame_queue.empty()

    def queue_full(self) -> bool:
        return self._session.frame_queue.full()

    def queue_capacity(self) -> int:
        return self._session.configuration.max_queue_size

    def queue_usage(self) -> float:
        capacity = self.queue_capacity()
        if capacity <= 0:
            return 0.0
        return (self.queue_size() / capacity) * 100.0

    def clear_queue(self) -> None:
        while not self._session.frame_queue.empty():
            try:
                self._session.frame_queue.get_nowait()
            except Exception:
                break

    def flush_queue(self) -> List[RuntimeFrame]:
        frames = []
        while not self._session.frame_queue.empty():
            try:
                frames.append(self._session.frame_queue.get_nowait())
            except Exception:
                break
        return frames

    def push_processed_frame(self, frame: ProcessedFrame) -> None:
        self._session.processed_frames.append(frame)
        self._session.statistics.processed_frames += 1

    def latest_frame(self) -> Optional[ProcessedFrame]:
        if not self._session.processed_frames:
            return None
        return self._session.processed_frames[-1]

    def processed_frame(self, index: int) -> Optional[ProcessedFrame]:
        try:
            return self._session.processed_frames[index]
        except IndexError:
            return None

    def processed_count(self) -> int:
        return len(self._session.processed_frames)

    def clear_processed_frames(self) -> None:
        self._session.processed_frames.clear()

    # ============================================================
    # Callbacks
    # ============================================================

    def register_callback(
        self,
        event: RuntimeEvent,
        callback: Callable[..., Any],
        priority: RuntimePriority = RuntimePriority.NORMAL,
        enabled: bool = True,
        once: bool = False,
    ) -> RuntimeCallback:
        entry = RuntimeCallback(
            event=event,
            callback=callback,
            priority=priority,
            enabled=enabled,
            once=once,
        )
        self._session.callbacks.append(entry)
        self._session.callbacks.sort(key=lambda c: c.priority, reverse=True)
        return entry

    def unregister_callback(self, callback: RuntimeCallback) -> bool:
        try:
            self._session.callbacks.remove(callback)
            return True
        except ValueError:
            return False

    def clear_callbacks(self) -> None:
        self._session.callbacks.clear()

    def callback_count(self) -> int:
        return len(self._session.callbacks)

    def callbacks_for_event(self, event: RuntimeEvent) -> List[RuntimeCallback]:
        return [c for c in self._session.callbacks if c.event == event]

    def emit(self, event: RuntimeEvent, *args, **kwargs) -> None:
        expired = []
        for callback in self._session.callbacks:
            if callback.event != event or not callback.enabled:
                continue
            try:
                callback.callback(*args, **kwargs)
                self._session.statistics.callback_count += 1
            except Exception:
                self._session.statistics.errors += 1
            if callback.once:
                expired.append(callback)
        for callback in expired:
            self.unregister_callback(callback)

    # ============================================================
    # Statistics
    # ============================================================

    def statistics_report(self) -> Dict[str, Any]:
        stats = self._session.statistics
        return {
            "session_id": self._session.session_id,
            "name": self._session.name,
            "mode": self._session.mode.value,
            "state": self._session.state.value,
            "uptime": self.uptime,
            "received_frames": stats.received_frames,
            "processed_frames": stats.processed_frames,
            "dropped_frames": stats.dropped_frames,
            "playback_frames": stats.playback_frames,
            "recorded_frames": stats.recorded_frames,
            "callbacks": self.callback_count(),
            "callback_calls": stats.callback_count,
            "errors": stats.errors,
            "queue_size": self.queue_size(),
            "fps": stats.fps,
            "average_latency": stats.average_latency,
            "maximum_latency": stats.maximum_latency,
            "average_processing_time": stats.average_processing_time,
        }

    def reset_statistics(self) -> None:
        self._session.statistics.reset()

    def summary(self) -> Dict[str, Any]:
        return {
            "id": self._session.session_id,
            "name": self._session.name,
            "mode": self._session.mode.value,
            "state": self._session.state.value,
            "running": self.running,
            "paused": self.paused,
            "uptime": self.uptime,
            "queued_frames": self.queue_size(),
            "processed_frames": self.processed_count(),
        }

    def __len__(self) -> int:
        return self.queue_size()

    def __iter__(self):
        return iter(self._session.processed_frames)

    def __contains__(self, frame_id: str) -> bool:
        return any(frame.runtime_frame.frame_id == frame_id for frame in self._session.processed_frames)

    def __str__(self) -> str:
        return f"{self._session.name} [{self._session.state.value}] Frames={self._session.statistics.processed_frames} FPS={self._session.statistics.fps:.2f}"