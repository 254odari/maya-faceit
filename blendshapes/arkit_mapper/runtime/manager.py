"""
manager.py

RuntimeManager - processing pipeline, thread control, dispatch.
"""

import time
import threading
from typing import Any, Callable, Dict, List, Optional

from .enums import RuntimeEvent, RuntimeState
from .models import RuntimeFrame, ProcessedFrame, RuntimeConfig
from .session import RuntimeSession


class RuntimeManager:
    """
    Main runtime manager.

    Owns the runtime session, frame processing pipeline,
    worker thread, and output dispatch.
    """

    def __init__(
        self,
        converter=None,
        config: Optional[RuntimeConfig] = None,
    ):
        self._converter = converter
        self._config = config or RuntimeConfig()
        self._session: Optional[RuntimeSession] = None
        self._thread: Optional[threading.Thread] = None
        self._callbacks: Dict[RuntimeEvent, List[Callable]] = {e: [] for e in RuntimeEvent}
        self._running = False
        self._initialized = False
        self._shutdown = False
        self._last_update = 0.0
        self._lock = threading.RLock()

        # Profiler & diagnostics (lazy init)
        self._profiler = None
        self._diagnostics = None

    # ============================================================
    # Properties
    # ============================================================

    @property
    def session(self) -> Optional[RuntimeSession]:
        return self._session

    @property
    def converter(self):
        return self._converter

    @property
    def config(self) -> RuntimeConfig:
        return self._config

    @property
    def running(self) -> bool:
        return self._running

    @property
    def initialized(self) -> bool:
        return self._initialized

    @property
    def shutdown(self) -> bool:
        return self._shutdown

    # ============================================================
    # Lifecycle
    # ============================================================

    def initialize(self) -> None:
        if self._initialized:
            return
        if self._converter is None:
            raise RuntimeError("Converter not provided.")
        self._session = RuntimeSession(config=self._config)
        self._session.initialize(self._converter)
        self._initialized = True
        self._emit(RuntimeEvent.INITIALIZED, self._session)

    def start(self) -> bool:
        with self._lock:
            if self._running:
                return True
            if self._shutdown:
                raise RuntimeError("Runtime has been shut down.")
            if not self._initialized:
                self.initialize()
            if self._session is None:
                raise RuntimeError("Runtime session not initialized.")
            self._session.start()
            self._running = True
            self._last_update = time.time()
            if self._config.threaded:
                self._create_worker_thread()
            self._emit(RuntimeEvent.STARTED, self._session)
            return True

    def stop(self) -> None:
        with self._lock:
            if not self._running:
                return
            self._running = False
            if self._session is not None:
                self._session.stop()
            self._stop_worker_thread()
            self._emit(RuntimeEvent.STOPPED, self._session)

    def pause(self) -> None:
        if self._session is not None:
            self._session.pause()
            self._emit(RuntimeEvent.PAUSED, self._session)

    def resume(self) -> None:
        if self._session is not None:
            self._session.resume()
            self._emit(RuntimeEvent.RESUMED, self._session)

    def restart(self) -> None:
        self.stop()
        if self._session is not None:
            self._session.restart()
        self.start()

    def shutdown(self) -> None:
        with self._lock:
            if self._shutdown:
                return
            self.stop()
            self._shutdown = True
            self._initialized = False
            if self._session is not None:
                self._session.shutdown()
            self._thread = None

    # ============================================================
    # Worker Thread
    # ============================================================

    def _create_worker_thread(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, name="ARKitRuntime", daemon=True)
        self._thread.start()

    def _stop_worker_thread(self) -> None:
        if self._thread is None:
            return
        if self._thread.is_alive() and self._thread is not threading.current_thread():
            self._thread.join(timeout=2.0)
        self._thread = None

    def worker_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def join(self, timeout: Optional[float] = None) -> None:
        if self._thread is None:
            return
        if self._thread.is_alive() and self._thread is not threading.current_thread():
            self._thread.join(timeout=timeout)

    # ============================================================
    # Main Loop
    # ============================================================

    def _run(self) -> None:
        while self._running:
            try:
                if self._session is None or self._shutdown:
                    break
                if self._session.paused:
                    time.sleep(0.01)
                    continue
                self._runtime_update()
            except Exception as exc:
                self.handle_runtime_error(exc)
                time.sleep(0.01)
        self._running = False

    def _runtime_update(self) -> None:
        if self._session is None:
            return
        self._drop_expired_frames()
        frame = self._session.next_frame()
        if frame is None:
            self._idle()
            return
        frame = self.preprocess_frame(frame)
        processed = self.process_frame(frame)
        if processed is None:
            return
        processed = self.smooth_frame(processed)
        processed = self.postprocess_frame(processed)
        self.dispatch_frame(processed)
        self._frame_sync()

    def _idle(self) -> None:
        time.sleep(0.001)

    def _frame_sync(self) -> None:
        """Maintain target frame rate."""
        # Placeholder: sleep to maintain FPS if needed

    # ============================================================
    # Processing Pipeline
    # ============================================================

    def process_frame(self, frame: RuntimeFrame) -> Optional[ProcessedFrame]:
        if not self._running or self._session is None or self._converter is None:
            return None

        self._emit(RuntimeEvent.FRAME_RECEIVED, frame)

        if not self._validate_frame(frame):
            self._session.statistics.dropped_frames += 1
            self._emit(RuntimeEvent.FRAME_DROPPED, frame)
            return None

        start_time = time.perf_counter()
        mapping_result = self._converter.convert_frame(frame.coefficients)
        processing_time = time.perf_counter() - start_time
        latency_ms = (time.time() - frame.timestamp) * 1000.0

        processed = ProcessedFrame(
            runtime_frame=frame,
            mapping_result=mapping_result,
            processing_time=processing_time,
            latency_ms=latency_ms,
        )

        self._session.push_processed_frame(processed)
        self._update_processing_statistics(processed)
        self._emit(RuntimeEvent.FRAME_PROCESSED, processed)

        return processed

    def process_next_frame(self) -> Optional[ProcessedFrame]:
        if self._session is None:
            return None
        frame = self._session.next_frame()
        if frame is None:
            return None
        return self.process_frame(frame)

    def process_available_frames(self, limit: Optional[int] = None) -> int:
        if self._session is None:
            return 0
        processed = 0
        while self._session.frame_available():
            if limit is not None and processed >= limit:
                break
            result = self.process_next_frame()
            if result is None:
                break
            processed += 1
        return processed

    def process_coefficients(self, coefficients: Dict) -> Optional[ProcessedFrame]:
        frame = RuntimeFrame(coefficients=self._normalize_coefficients(coefficients))
        return self.process_frame(frame)

    def process_batch(self, frames) -> List[ProcessedFrame]:
        results = []
        for frame in frames:
            processed = self.process_frame(frame)
            if processed is not None:
                results.append(processed)
        return results

    def update(self) -> bool:
        if not self._running or self._session is None:
            return False
        before = self.processed_frame_count()
        self._runtime_update()
        after = self.processed_frame_count()
        return after > before

    def update_until_empty(self) -> int:
        if self._session is None:
            return 0
        processed = 0
        while self._session.frame_available():
            if self.update():
                processed += 1
            else:
                break
        return processed

    # ============================================================
    # Frame Validation & Utilities
    # ============================================================

    def _validate_frame(self, frame: RuntimeFrame) -> bool:
        if frame is None or self._converter is None:
            return False
        if not frame.coefficients or frame.timestamp <= 0.0:
            return False
        return True

    def frame_latency(self, frame: RuntimeFrame) -> float:
        return (time.time() - frame.timestamp) * 1000.0

    def frame_expired(self, frame: RuntimeFrame) -> bool:
        return self.frame_latency(frame) > 250.0  # MAX_LATENCY_MS

    def _drop_expired_frames(self) -> int:
        if self._session is None:
            return 0
        dropped = 0
        kept = []
        while self._session.frame_available():
            frame = self._session.next_frame()
            if frame is None:
                break
            if self.frame_expired(frame):
                dropped += 1
                self._session.statistics.dropped_frames += 1
                self._emit(RuntimeEvent.FRAME_DROPPED, frame)
            else:
                kept.append(frame)
        for frame in kept:
            self._session.submit_frame(frame)
        return dropped

    def _normalize_coefficients(self, coefficients: Dict) -> Dict:
        filtered = {}
        for channel, value in coefficients.items():
            if value is None:
                continue
            filtered[channel] = min(1.0, max(0.0, float(value)))
        return filtered

    def latest_processed_frame(self) -> Optional[ProcessedFrame]:
        if self._session is None:
            return None
        return self._session.latest_frame()

    def processed_frame_count(self) -> int:
        if self._session is None:
            return 0
        return self._session.processed_count()

    # ============================================================
    # Processing Hooks
    # ============================================================

    def preprocess_frame(self, frame: RuntimeFrame) -> RuntimeFrame:
        return frame

    def postprocess_frame(self, frame: ProcessedFrame) -> ProcessedFrame:
        return frame

    def smooth_frame(self, frame: ProcessedFrame) -> ProcessedFrame:
        if not self._config.smoothing_enabled:
            return frame
        # Placeholder for smoothing
        return frame

    # ============================================================
    # Dispatch
    # ============================================================

    def dispatch_frame(self, frame: ProcessedFrame) -> bool:
        if frame is None:
            return False
        try:
            self._emit(RuntimeEvent.FRAME_PROCESSED, frame)
            return True
        except Exception as exc:
            self.handle_runtime_error(exc)
            return False

    def dispatch_latest_frame(self) -> bool:
        frame = self.latest_processed_frame()
        if frame is None:
            return False
        return self.dispatch_frame(frame)

    # ============================================================
    # Statistics & Processing Metrics
    # ============================================================

    def _update_processing_statistics(self, frame: ProcessedFrame) -> None:
        if self._session is None:
            return
        stats = self._session.statistics
        count = max(1, stats.processed_frames)
        stats.average_processing_time = ((stats.average_processing_time * (count - 1)) + frame.processing_time) / count
        stats.average_latency = ((stats.average_latency * (count - 1)) + frame.latency_ms) / count
        stats.maximum_latency = max(stats.maximum_latency, frame.latency_ms)
        now = time.time()
        if self._last_update > 0.0:
            delta = now - self._last_update
            if delta > 0.0:
                stats.fps = 1.0 / delta
        self._last_update = now

    def average_processing_time(self) -> float:
        if self._session is None:
            return 0.0
        return self._session.statistics.average_processing_time

    def average_latency(self) -> float:
        if self._session is None:
            return 0.0
        return self._session.statistics.average_latency

    def current_fps(self) -> float:
        if self._session is None:
            return 0.0
        return self._session.statistics.fps

    def processing_report(self) -> Dict[str, Any]:
        if self._session is None:
            return {}
        stats = self._session.statistics
        return {
            "fps": stats.fps,
            "received": stats.received_frames,
            "processed": stats.processed_frames,
            "dropped": stats.dropped_frames,
            "average_latency_ms": stats.average_latency,
            "maximum_latency_ms": stats.maximum_latency,
            "average_processing_time": stats.average_processing_time,
            "queue": self._session.queue_report() if hasattr(self._session, 'queue_report') else {},
        }

    def reset_processing_statistics(self) -> None:
        if self._session is not None:
            self._session.reset_statistics()
        self._last_update = 0.0

    # ============================================================
    # Events & Callbacks
    # ============================================================

    def _emit(self, event: RuntimeEvent, *args, **kwargs) -> None:
        for cb in self._callbacks.get(event, []):
            try:
                cb(*args, **kwargs)
            except Exception as exc:
                self.handle_runtime_error(exc)
        if self._session is not None:
            self._session.emit(event, *args, **kwargs)

    def register_callback(self, event: RuntimeEvent, callback: Callable) -> None:
        self._callbacks[event].append(callback)

    def unregister_callback(self, event: RuntimeEvent, callback: Callable) -> bool:
        callbacks = self._callbacks.get(event, [])
        try:
            callbacks.remove(callback)
            return True
        except ValueError:
            return False

    def clear_callbacks(self) -> None:
        for event in RuntimeEvent:
            self._callbacks[event].clear()

    def callback_count(self) -> int:
        return sum(len(callbacks) for callbacks in self._callbacks.values())

    # ============================================================
    # Error Handling
    # ============================================================

    def handle_runtime_error(self, error: Exception) -> None:
        if self._session is not None:
            self._session.statistics.errors += 1
        try:
            self._emit(RuntimeEvent.ERROR, error)
        except Exception:
            pass

    def recover(self) -> bool:
        if self._session is None:
            return False
        try:
            self._session.reset()
            if self._converter is not None:
                self._session.initialize(self._converter)
            return True
        except Exception:
            return False

    # ============================================================
    # Status & Diagnostics
    # ============================================================

    def idle(self) -> bool:
        if self._session is None:
            return True
        return not self._session.frame_available()

    def busy(self) -> bool:
        return not self.idle()

    def queue_backlog(self) -> int:
        if self._session is None:
            return 0
        return self._session.queue_size()

    def runtime_load(self) -> float:
        if self._session is None:
            return 0.0
        return self._session.queue_usage()

    def runtime_state(self) -> RuntimeState:
        if self._session is None:
            return RuntimeState.CREATED
        return self._session.state

    def runtime_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "threaded": self._config.threaded,
            "idle": self.idle(),
            "busy": self.busy(),
            "queue_backlog": self.queue_backlog(),
            "runtime_load": self.runtime_load(),
            "worker_alive": self.worker_alive(),
            "state": self.runtime_state().value,
        }

    def diagnostics(self) -> Dict[str, Any]:
        session = self._session
        return {
            "initialized": self._initialized,
            "running": self._running,
            "shutdown": self._shutdown,
            "uptime": self.uptime(),
            "callbacks": self.callback_count(),
            "converter": self._converter is not None,
            "session": session.summary() if session else None,
            "processing": self.processing_report(),
        }

    def health_check(self) -> Dict[str, bool]:
        return {
            "initialized": self._initialized,
            "converter": self._converter is not None,
            "session": self._session is not None,
            "running": self._running,
            "thread": self._thread is not None,
            "queue": self._session is not None and not self._session.queue_full(),
        }

    def heartbeat(self) -> Dict[str, Any]:
        session = self._session
        return {
            "timestamp": time.time(),
            "running": self._running,
            "initialized": self._initialized,
            "shutdown": self._shutdown,
            "worker_alive": self.worker_alive(),
            "state": session.state.value if session else None,
            "queue": session.queue_size() if session else 0,
            "processed": session.statistics.processed_frames if session else 0,
            "fps": session.statistics.fps if session else 0.0,
        }

    def runtime_summary(self) -> Dict[str, Any]:
        return {
            "version": "1.0.0",
            "uptime": self.uptime(),
            "heartbeat": self.heartbeat(),
            "diagnostics": self.diagnostics(),
            "processing": self.processing_report(),
            "health": self.health_check(),
        }

    def uptime(self) -> float:
        if self._session is None:
            return 0.0
        return self._session.uptime

    # ============================================================
    # Profiling
    # ============================================================

    def enable_profiler(self):
        if not hasattr(self, "_profiler") or self._profiler is None:
            from .profiler import RuntimeProfiler
            self._profiler = RuntimeProfiler()
        self._profiler.enabled = True

    def disable_profiler(self):
        if hasattr(self, "_profiler") and self._profiler is not None:
            self._profiler.enabled = False

    def profiler_enabled(self):
        return hasattr(self, "_profiler") and self._profiler is not None and self._profiler.enabled

    def capture_metrics(self):
        if not self.profiler_enabled():
            return None
        return self._profiler.capture(self)

    def profiler_summary(self):
        if not self.profiler_enabled():
            return {}
        return self._profiler.summary()

    def reset_profiler(self):
        if self.profiler_enabled():
            self._profiler.reset()

    # ============================================================
    # Diagnostics
    # ============================================================

    def enable_diagnostics(self):
        if not hasattr(self, "_diagnostics") or self._diagnostics is None:
            from .diagnostics import RuntimeDiagnostics
            self._diagnostics = RuntimeDiagnostics()
        self._diagnostics.enabled = True

    def diagnostics_enabled(self):
        return hasattr(self, "_diagnostics") and self._diagnostics is not None and self._diagnostics.enabled

    def record_runtime_event(self, event: RuntimeEvent, message: str = "", data: Optional[Dict] = None):
        if self.diagnostics_enabled():
            self._diagnostics.record_event(event, source=self.__class__.__name__, message=message, data=data)

    def record_runtime_error(self, exc: Exception):
        if self.diagnostics_enabled():
            self._diagnostics.record_error(exc)

    def diagnostics_summary(self):
        if not self.diagnostics_enabled():
            return {}
        return self._diagnostics.summary()

    def clear_diagnostics(self):
        if self.diagnostics_enabled():
            self._diagnostics.clear()

    # ============================================================
    # Context Manager
    # ============================================================

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.graceful_shutdown()
        return False