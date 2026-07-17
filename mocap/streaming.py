"""
mocap/streaming.py

Real-time streaming to Maya.

Streams facial data in real-time to Maya blendshapes from various sources:
- Live Link Face (iPhone)
- MediaPipe (webcam)
- FaceCap
- Custom sources via callbacks

Features:
- Thread-safe streaming
- Automatic application to blendshape node
- Smoothing and filtering pipeline
- Callback support for custom processing
- Statistics and performance monitoring
- Start/stop control
- Multiple source support

Author: Maya FaceIT Team
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Callable, List, Any, Union

# Maya imports
try:
    import maya.cmds as cmds
    HAS_MAYA = True
except ImportError:
    HAS_MAYA = False
    # Dummy for testing
    class DummyCmds:
        def __getattr__(self, name):
            return lambda *args, **kwargs: None
    cmds = DummyCmds()

# Import dependencies
try:
    from .smoothing import SmoothingFilter, SmoothingSettings
    from .filters import FilterChain, FilterBase, create_standard_chain
    from .livelink import LiveLinkReceiver, LiveLinkData
    from .mediapipe import MediaPipeTracker, MediaPipeResult
    from .iphone import iPhoneCapture, iPhoneFrame
    from .retarget import RetargetEngine, RetargetSettings
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False
    # Fallback for development
    class SmoothingFilter:
        def smooth(self, data): return data
    class SmoothingSettings: pass
    class FilterChain:
        def apply(self, data): return data
    def create_standard_chain(): return FilterChain()
    class LiveLinkReceiver: pass
    class LiveLinkData: pass
    class MediaPipeTracker: pass
    class MediaPipeResult: pass
    class iPhoneCapture: pass
    class iPhoneFrame: pass
    class RetargetEngine:
        def retarget(self, data, source_type=None): 
            from dataclasses import dataclass
            @dataclass
            class Result:
                success: bool
                mapped_coefficients: dict
            return Result(True, data)
    class RetargetSettings: pass

logger = logging.getLogger(__name__)

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"


# ---- Exceptions ----

class StreamError(Exception):
    """Base exception for streaming operations."""
    pass


# ---- Data Models ----

@dataclass
class StreamSettings:
    """
    Settings for streaming.
    """
    source_type: str = "livelink"           # 'livelink', 'mediapipe', 'facecap', 'custom'
    apply_to_rig: bool = True               # Auto-apply to rig
    blendshape_node: Optional[str] = None   # Target blendshape node
    apply_callback: Optional[Callable[[Dict[str, float]], None]] = None
    smoothing: bool = True                  # Apply smoothing
    smoothing_window: int = 5               # Smoothing window size
    filter_chain: Optional[FilterChain] = None  # Custom filter chain
    retarget: bool = True                   # Apply retargeting
    retarget_settings: Optional[RetargetSettings] = None
    source_type_for_retarget: str = "arkit" # Source type for retargeting
    frame_rate: int = 60                    # Target frame rate
    auto_start: bool = True                 # Auto-start streaming
    verbose_logging: bool = False           # Log each frame

    # Live Link specific
    livelink_port: int = 11111

    # MediaPipe specific
    mediapipe_model_path: Optional[str] = None
    mediapipe_num_faces: int = 1

    # iPhone specific
    iphone_source: str = "live_link"


@dataclass
class StreamStatistics:
    """
    Streaming statistics.
    """
    frames_processed: int = 0
    frames_applied: int = 0
    errors: int = 0
    average_fps: float = 0.0
    last_frame_time: float = 0.0
    source_type: str = "unknown"
    running: bool = False
    start_time: float = 0.0
    elapsed_time: float = 0.0


# ---- Mocap Streamer ----

class MocapStreamer:
    """
    Real-time streaming of facial data.

    Streams data from various sources to the Maya rig.

    Usage:
        streamer = MocapStreamer(blendshape_node="face_BS")
        streamer.set_apply_callback(my_callback)
        streamer.start()
        # ... streaming ...
        streamer.stop()
    """

    def __init__(self, settings: Optional[StreamSettings] = None):
        """
        Initialize the streamer.

        Args:
            settings: Optional settings.
        """
        if not HAS_MAYA:
            raise StreamError("Maya is not available for streaming")

        self.settings = settings or StreamSettings()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()

        # Source specific components
        self._livelink: Optional[LiveLinkReceiver] = None
        self._mediapipe: Optional[MediaPipeTracker] = None
        self._iphone: Optional[iPhoneCapture] = None
        self._retarget_engine = RetargetEngine(self.settings.retarget_settings)

        # Processing pipeline
        self._smoother: Optional[SmoothingFilter] = None
        self._filter_chain: Optional[FilterChain] = None

        # Callbacks
        self._pre_callbacks: List[Callable[[Dict[str, float]], Dict[str, float]]] = []
        self._post_callbacks: List[Callable[[Dict[str, float]], None]] = []

        # Statistics
        self._stats = StreamStatistics()
        self._frame_times: List[float] = []
        self._last_frame_time = 0.0
        self._frame_count = 0

        # Initialize processing pipeline
        self._init_pipeline()

        logger.debug(f"MocapStreamer initialized with source: {self.settings.source_type}")

        if self.settings.auto_start:
            self.start()

    # ---- Initialization ----

    def _init_pipeline(self) -> None:
        """Initialize the processing pipeline."""
        # Smoothing
        if self.settings.smoothing:
            smoothing_settings = SmoothingSettings(
                window_size=self.settings.smoothing_window,
                method="moving_average",
            )
            self._smoother = SmoothingFilter(smoothing_settings)

        # Filter chain
        if self.settings.filter_chain:
            self._filter_chain = self.settings.filter_chain
        else:
            # Default chain
            self._filter_chain = create_standard_chain()

    # ---- Lifecycle ----

    def start(self) -> None:
        """Start streaming."""
        if self._running:
            logger.warning("Streamer already running")
            return

        self._running = True
        self._stats.start_time = time.time()
        self._stats.running = True
        self._stats.source_type = self.settings.source_type

        # Start source-specific components
        if self.settings.source_type == "livelink":
            self._start_livelink()
        elif self.settings.source_type == "mediapipe":
            self._start_mediapipe()
        elif self.settings.source_type == "facecap":
            self._start_iphone()
        elif self.settings.source_type == "iphone":
            self._start_iphone()
        else:
            # Custom source - user must call send_data()
            logger.info("Custom source selected; use send_data() to push frames")

        # Start processing thread
        self._thread = threading.Thread(target=self._stream_loop, daemon=True)
        self._thread.start()

        logger.info(f"Streaming started (source: {self.settings.source_type})")

    def stop(self) -> None:
        """Stop streaming."""
        if not self._running:
            return

        self._running = False

        # Stop source components
        if self._livelink:
            self._livelink.stop()
            self._livelink = None

        if self._mediapipe:
            self._mediapipe.close()
            self._mediapipe = None

        if self._iphone:
            self._iphone.stop()
            self._iphone = None

        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

        self._stats.running = False
        self._stats.elapsed_time = time.time() - self._stats.start_time

        logger.info("Streaming stopped")

    def is_running(self) -> bool:
        """Check if streaming is active."""
        return self._running

    # ---- Source Start ----

    def _start_livelink(self) -> None:
        """Start Live Link receiver."""
        from .livelink import LiveLinkReceiver, LiveLinkSettings

        settings = LiveLinkSettings(
            port=self.settings.livelink_port,
            auto_apply=False,
        )
        self._livelink = LiveLinkReceiver(settings)
        self._livelink.add_callback(self._on_source_data)
        self._livelink.start()
        logger.info(f"Live Link receiver started on port {self.settings.livelink_port}")

    def _start_mediapipe(self) -> None:
        """Start MediaPipe tracker."""
        from .mediapipe import MediaPipeTracker, MediaPipeSettings

        settings = MediaPipeSettings(
            model_path=self.settings.mediapipe_model_path,
            num_faces=self.settings.mediapipe_num_faces,
            output_blendshapes=True,
        )
        self._mediapipe = MediaPipeTracker(settings)
        if not self._mediapipe.initialize():
            raise StreamError("Failed to initialize MediaPipe tracker")

        # MediaPipe runs in a separate loop; we'll poll it in the main loop
        logger.info("MediaPipe tracker initialized")

    def _start_iphone(self) -> None:
        """Start iPhone capture."""
        from .iphone import iPhoneCapture, iPhoneSettings

        settings = iPhoneSettings(
            source=self.settings.iphone_source,
            port=self.settings.livelink_port,
            apply_callback=self._on_source_data,
        )
        self._iphone = iPhoneCapture(settings)
        self._iphone.start()
        logger.info("iPhone capture started")

    # ---- Source Data Callback ----

    def _on_source_data(self, data: Dict[str, float]) -> None:
        """
        Callback from source (LiveLink, iPhone).

        Args:
            data: Blendshape coefficients.
        """
        if self.settings.verbose_logging:
            logger.debug(f"Source data received: {len(data)} channels")

        self._process_data(data)

    # ---- Processing Pipeline ----

    def _process_data(self, data: Dict[str, float]) -> None:
        """
        Process incoming data through the pipeline.

        Args:
            data: Raw coefficients.
        """
        if not data:
            return

        self._frame_count += 1

        # Pre-processing callbacks
        for callback in self._pre_callbacks:
            try:
                data = callback(data)
            except Exception as e:
                logger.error(f"Pre-callback error: {e}")
                self._stats.errors += 1

        # Retargeting
        if self.settings.retarget:
            try:
                result = self._retarget_engine.retarget(
                    data,
                    source_type=self.settings.source_type_for_retarget,
                )
                if result.success:
                    data = result.mapped_coefficients
                else:
                    logger.warning(f"Retargeting failed: {result.errors}")
            except Exception as e:
                logger.error(f"Retargeting error: {e}")
                self._stats.errors += 1

        # Smoothing
        if self.settings.smoothing and self._smoother:
            try:
                data = self._smoother.smooth(data)
            except Exception as e:
                logger.error(f"Smoothing error: {e}")
                self._stats.errors += 1

        # Filter chain
        if self._filter_chain:
            try:
                data = self._filter_chain.apply(data)
            except Exception as e:
                logger.error(f"Filter chain error: {e}")
                self._stats.errors += 1

        # Apply to rig
        if self.settings.apply_to_rig:
            self._apply_to_rig(data)

        # Post-processing callbacks
        for callback in self._post_callbacks:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Post-callback error: {e}")
                self._stats.errors += 1

        # Update statistics
        self._stats.frames_processed += 1
        self._stats.frames_applied += 1 if self.settings.apply_to_rig else 0
        self._stats.last_frame_time = time.time()

        # Track FPS
        current_time = time.time()
        if self._last_frame_time > 0:
            self._frame_times.append(current_time - self._last_frame_time)
            if len(self._frame_times) > 60:
                self._frame_times.pop(0)
        self._last_frame_time = current_time

        # Update average FPS
        if self._frame_times:
            self._stats.average_fps = 1.0 / (sum(self._frame_times) / len(self._frame_times))

    def send_data(self, data: Dict[str, float]) -> None:
        """
        Send data from a custom source.

        Args:
            data: Blendshape coefficients.
        """
        if not self._running:
            logger.warning("Streamer not running; data ignored")
            return
        self._process_data(data)

    # ---- Apply to Rig ----

    def _apply_to_rig(self, coefficients: Dict[str, float]) -> None:
        """
        Apply coefficients to the rig.

        Args:
            coefficients: Blendshape coefficients.
        """
        # Use custom callback if provided
        if self.settings.apply_callback:
            try:
                self.settings.apply_callback(coefficients)
            except Exception as e:
                logger.error(f"Apply callback error: {e}")
            return

        # Use blendshape node
        node = self.settings.blendshape_node
        if not node:
            logger.debug("No blendshape node specified for streaming")
            return

        if not cmds.objExists(node):
            logger.warning(f"Blendshape node '{node}' not found")
            return

        for target, value in coefficients.items():
            attr = f"{node}.{target}"
            if cmds.objExists(attr):
                # Clamp value for safety
                if value < 0.0:
                    value = 0.0
                elif value > 1.0:
                    value = 1.0
                try:
                    cmds.setAttr(attr, value)
                except Exception as e:
                    logger.error(f"Failed to set {attr}: {e}")

    # ---- Stream Loop ----

    def _stream_loop(self) -> None:
        """
        Main streaming loop.

        For MediaPipe, this polls the tracker. For other sources,
        the loop just keeps the thread alive.
        """
        while self._running:
            # Handle MediaPipe (polling)
            if self.settings.source_type == "mediapipe" and self._mediapipe:
                # MediaPipe requires frames from camera; we need to implement camera capture
                # For now, we'll just sleep and let the user call send_data()
                # This is a placeholder; actual implementation would use OpenCV to capture frames
                time.sleep(0.01)
            else:
                # For other sources, just sleep
                time.sleep(0.005)

    # ---- Callbacks ----

    def add_pre_callback(self, callback: Callable[[Dict[str, float]], Dict[str, float]]) -> None:
        """
        Add a callback before processing.

        Args:
            callback: Function that takes coefficients and returns modified coefficients.
        """
        self._pre_callbacks.append(callback)

    def add_post_callback(self, callback: Callable[[Dict[str, float]], None]) -> None:
        """
        Add a callback after processing.

        Args:
            callback: Function called with coefficients.
        """
        self._post_callbacks.append(callback)

    def remove_pre_callback(self, callback: Callable[[Dict[str, float]], Dict[str, float]]) -> None:
        """Remove a pre-callback."""
        if callback in self._pre_callbacks:
            self._pre_callbacks.remove(callback)

    def remove_post_callback(self, callback: Callable[[Dict[str, float]], None]) -> None:
        """Remove a post-callback."""
        if callback in self._post_callbacks:
            self._post_callbacks.remove(callback)

    def clear_callbacks(self) -> None:
        """Clear all callbacks."""
        self._pre_callbacks = []
        self._post_callbacks = []

    def set_apply_callback(self, callback: Callable[[Dict[str, float]], None]) -> None:
        """Set the apply callback for rig application."""
        self.settings.apply_callback = callback

    # ---- Settings ----

    def set_blendshape_node(self, node: str) -> None:
        """Set the target blendshape node."""
        self.settings.blendshape_node = node

    def enable_smoothing(self, enabled: bool = True) -> None:
        """Enable or disable smoothing."""
        self.settings.smoothing = enabled
        if enabled and not self._smoother:
            self._init_pipeline()

    def set_smoothing_window(self, window: int) -> None:
        """Set the smoothing window size."""
        self.settings.smoothing_window = window
        if self._smoother:
            self._smoother.set_settings(SmoothingSettings(window_size=window))

    def set_filter_chain(self, chain: FilterChain) -> None:
        """Set the filter chain."""
        self._filter_chain = chain
        self.settings.filter_chain = chain

    # ---- Statistics ----

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get streaming statistics.

        Returns:
            Dict with streaming stats.
        """
        with self._lock:
            stats = {
                "running": self._running,
                "source_type": self.settings.source_type,
                "frames_processed": self._stats.frames_processed,
                "frames_applied": self._stats.frames_applied,
                "errors": self._stats.errors,
                "average_fps": self._stats.average_fps,
                "elapsed_time": time.time() - self._stats.start_time if self._stats.start_time > 0 else 0,
                "blendshape_node": self.settings.blendshape_node,
                "smoothing_enabled": self.settings.smoothing,
                "retarget_enabled": self.settings.retarget,
                "callback_count": len(self._pre_callbacks) + len(self._post_callbacks),
            }
            return stats

    def reset_statistics(self) -> None:
        """Reset statistics."""
        with self._lock:
            self._stats = StreamStatistics()
            self._frame_times = []
            self._frame_count = 0

    # ---- Context Manager ----

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def __del__(self):
        self.stop()


# ---- Convenience Functions ----

def create_livelink_streamer(
    blendshape_node: str,
    port: int = 11111,
    smoothing: bool = True,
    smoothing_window: int = 5,
) -> MocapStreamer:
    """
    Create a streamer for Live Link Face.

    Args:
        blendshape_node: Target blendshape node.
        port: UDP port.
        smoothing: Enable smoothing.
        smoothing_window: Smoothing window size.

    Returns:
        MocapStreamer instance.
    """
    settings = StreamSettings(
        source_type="livelink",
        blendshape_node=blendshape_node,
        livelink_port=port,
        smoothing=smoothing,
        smoothing_window=smoothing_window,
    )
    return MocapStreamer(settings)


def create_mediapipe_streamer(
    blendshape_node: str,
    model_path: Optional[str] = None,
    smoothing: bool = True,
    smoothing_window: int = 5,
) -> MocapStreamer:
    """
    Create a streamer for MediaPipe.

    Args:
        blendshape_node: Target blendshape node.
        model_path: Path to face_landmarker.task.
        smoothing: Enable smoothing.
        smoothing_window: Smoothing window size.

    Returns:
        MocapStreamer instance.
    """
    settings = StreamSettings(
        source_type="mediapipe",
        blendshape_node=blendshape_node,
        mediapipe_model_path=model_path,
        smoothing=smoothing,
        smoothing_window=smoothing_window,
    )
    return MocapStreamer(settings)


def create_iphone_streamer(
    blendshape_node: str,
    source: str = "live_link",
    port: int = 11111,
    smoothing: bool = True,
    smoothing_window: int = 5,
) -> MocapStreamer:
    """
    Create a streamer for iPhone capture.

    Args:
        blendshape_node: Target blendshape node.
        source: 'live_link' or 'facecap'.
        port: UDP port.
        smoothing: Enable smoothing.
        smoothing_window: Smoothing window size.

    Returns:
        MocapStreamer instance.
    """
    settings = StreamSettings(
        source_type="iphone",
        blendshape_node=blendshape_node,
        iphone_source=source,
        livelink_port=port,
        smoothing=smoothing,
        smoothing_window=smoothing_window,
    )
    return MocapStreamer(settings)


# ---- Public API ----

__all__ = [
    "MocapStreamer",
    "StreamSettings",
    "StreamStatistics",
    "StreamError",
    "create_livelink_streamer",
    "create_mediapipe_streamer",
    "create_iphone_streamer",
]