"""
mocap/iphone.py

iPhone TrueDepth camera capture.

Captures facial data from iPhone via USB or network.

This module provides a unified interface for capturing facial data from
iPhone TrueDepth camera using various methods:
- Live Link Face (UDP)
- FaceCap (network)
- Native ARKit capture (via USB)

It integrates with the LiveLinkReceiver and FaceCapProcessor to provide
a seamless capture experience.

Author: Maya FaceIT Team
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Any, List, Union, Callable

# Import submodules
try:
    from .livelink import LiveLinkReceiver, LiveLinkSettings, LiveLinkData
    from .facecap import FaceCapProcessor, FaceCapSettings, FaceCapData
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False
    # Fallback for development
    class LiveLinkReceiver: pass
    class LiveLinkSettings: pass
    class LiveLinkData: pass
    class FaceCapProcessor: pass
    class FaceCapSettings: pass
    class FaceCapData: pass

logger = logging.getLogger(__name__)

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"


# ---- Exceptions ----

class iPhoneError(Exception):
    """Base exception for iPhone capture operations."""
    pass


# ---- Data Models ----

@dataclass
class iPhoneSettings:
    """
    Settings for iPhone capture.
    """
    source: str = "live_link"              # 'live_link', 'facecap', 'arkit'
    ip_address: Optional[str] = None       # IP address for network capture
    port: int = 11111                      # UDP port (for Live Link)
    frame_rate: int = 60                   # Target frame rate
    auto_start: bool = True                # Auto-start capture on init
    buffer_size: int = 100                 # Frame buffer size
    apply_callback: Optional[Callable[[Dict[str, float]], None]] = None


@dataclass
class iPhoneFrame:
    """
    iPhone capture frame.
    """
    timestamp: float
    blendshapes: Dict[str, float]
    head_pose: Optional[Dict[str, float]] = None
    frame_number: int = 0
    source: str = "iPhone"
    raw_data: Optional[Any] = None


# ---- iPhone Capture ----

class iPhoneCapture:
    """
    iPhone TrueDepth capture interface.

    Wraps Live Link and FaceCap integration for iPhone capture.
    Provides a unified API for capturing facial data from iPhone.

    Usage:
        capture = iPhoneCapture()
        capture.start()
        frame = capture.get_frame()
        if frame:
            print(frame.blendshapes)
        capture.stop()
    """

    def __init__(self, settings: Optional[iPhoneSettings] = None):
        """
        Initialize the iPhone capture.

        Args:
            settings: Optional settings.
        """
        self.settings = settings or iPhoneSettings()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        self._frame_buffer: List[iPhoneFrame] = []
        self._latest_frame: Optional[iPhoneFrame] = None
        self._frame_count = 0

        # Initialize source-specific components
        self._livelink: Optional[LiveLinkReceiver] = None
        self._facecap: Optional[FaceCapProcessor] = None

        # Callbacks
        self._callbacks: List[Callable[[iPhoneFrame], None]] = []

        logger.debug(f"iPhoneCapture initialized with source: {self.settings.source}")

        if self.settings.auto_start:
            self.start()

    # ---- Lifecycle ----

    def start(self) -> None:
        """Start iPhone capture."""
        if self._running:
            logger.warning("iPhone capture already running")
            return

        self._running = True

        if self.settings.source == "live_link":
            self._start_livelink()
        elif self.settings.source == "facecap":
            self._start_facecap()
        else:
            logger.warning(f"Unsupported source: {self.settings.source}")

        # Start frame collection thread
        self._thread = threading.Thread(target=self._collect_loop, daemon=True)
        self._thread.start()

        logger.info(f"iPhone capture started (source: {self.settings.source})")

    def stop(self) -> None:
        """Stop iPhone capture."""
        if not self._running:
            return

        self._running = False

        if self._livelink:
            self._livelink.stop()
            self._livelink = None

        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

        logger.info("iPhone capture stopped")

    def is_running(self) -> bool:
        """Check if capture is running."""
        return self._running

    # ---- Source Initialization ----

    def _start_livelink(self) -> None:
        """Start Live Link receiver."""
        settings = LiveLinkSettings(
            port=self.settings.port,
            auto_apply=False,
        )
        self._livelink = LiveLinkReceiver(settings)

        # Add callback to process Live Link data
        self._livelink.add_callback(self._on_livelink_data)
        self._livelink.start()
        logger.info(f"Live Link receiver started on port {self.settings.port}")

    def _start_facecap(self) -> None:
        """Initialize FaceCap processor."""
        settings = FaceCapSettings()
        self._facecap = FaceCapProcessor(settings)
        logger.info("FaceCap processor initialized")

    # ---- Data Collection ----

    def _collect_loop(self) -> None:
        """Main collection loop."""
        while self._running:
            time.sleep(0.005)  # Small delay to prevent CPU overload

    def _on_livelink_data(self, data: LiveLinkData) -> None:
        """
        Process Live Link data and convert to iPhoneFrame.

        Args:
            data: LiveLinkData from receiver.
        """
        frame = iPhoneFrame(
            timestamp=data.timestamp,
            blendshapes=data.blendshapes,
            head_pose={
                "pitch": data.head_rotation[0] if data.head_rotation else 0.0,
                "yaw": data.head_rotation[1] if data.head_rotation else 0.0,
                "roll": data.head_rotation[2] if data.head_rotation else 0.0,
            } if data.head_rotation else None,
            frame_number=data.frame_number,
            source="LiveLink",
            raw_data=data.raw_data,
        )
        self._add_frame(frame)

    def _add_frame(self, frame: iPhoneFrame) -> None:
        """
        Add a frame to the buffer and notify callbacks.

        Args:
            frame: iPhoneFrame to add.
        """
        with self._lock:
            self._frame_buffer.append(frame)
            if len(self._frame_buffer) > self.settings.buffer_size:
                self._frame_buffer.pop(0)
            self._latest_frame = frame
            self._frame_count += 1

        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(frame)
            except Exception as e:
                logger.error(f"iPhone callback error: {e}")

        # Apply callback if set
        if self.settings.apply_callback:
            try:
                self.settings.apply_callback(frame.blendshapes)
            except Exception as e:
                logger.error(f"Apply callback error: {e}")

    # ---- Accessor Methods ----

    def get_frame(self) -> Optional[iPhoneFrame]:
        """
        Get the latest frame.

        Returns:
            iPhoneFrame or None.
        """
        with self._lock:
            return self._latest_frame

    def get_blendshapes(self) -> Dict[str, float]:
        """
        Get the latest blendshapes.

        Returns:
            Dict of blendshape coefficients.
        """
        frame = self.get_frame()
        if frame:
            return frame.blendshapes
        return {}

    def get_head_pose(self) -> Optional[Dict[str, float]]:
        """
        Get the latest head pose.

        Returns:
            Dict with pitch, yaw, roll.
        """
        frame = self.get_frame()
        if frame:
            return frame.head_pose
        return None

    def get_frames(self, count: int = 10) -> List[iPhoneFrame]:
        """
        Get the last N frames.

        Args:
            count: Number of frames to retrieve.

        Returns:
            List of iPhoneFrame objects.
        """
        with self._lock:
            return self._frame_buffer[-count:]

    def get_frame_count(self) -> int:
        """Get total frames captured."""
        return self._frame_count

    # ---- Callback Management ----

    def add_callback(self, callback: Callable[[iPhoneFrame], None]) -> None:
        """Add a callback for new frames."""
        with self._lock:
            if callback not in self._callbacks:
                self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[iPhoneFrame], None]) -> None:
        """Remove a callback."""
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)

    def clear_callbacks(self) -> None:
        """Remove all callbacks."""
        with self._lock:
            self._callbacks.clear()

    def set_apply_callback(self, callback: Callable[[Dict[str, float]], None]) -> None:
        """Set the apply callback."""
        self.settings.apply_callback = callback

    # ---- Statistics ----

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get capture statistics.

        Returns:
            Dict with capture stats.
        """
        with self._lock:
            return {
                "running": self._running,
                "source": self.settings.source,
                "frame_count": self._frame_count,
                "buffer_size": len(self._frame_buffer),
                "latest_frame_time": self._latest_frame.timestamp if self._latest_frame else None,
                "callback_count": len(self._callbacks),
                "port": self.settings.port,
            }

    # ---- Context Manager ----

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def __del__(self):
        self.stop()


# ---- Convenience Functions ----

def create_iphone_capture(
    source: str = "live_link",
    port: int = 11111,
    apply_callback: Optional[Callable[[Dict[str, float]], None]] = None,
) -> iPhoneCapture:
    """
    Create an iPhoneCapture instance with common settings.

    Args:
        source: 'live_link' or 'facecap'.
        port: UDP port for Live Link.
        apply_callback: Callback for applying blendshapes.

    Returns:
        iPhoneCapture instance.
    """
    settings = iPhoneSettings(
        source=source,
        port=port,
        apply_callback=apply_callback,
        auto_start=True,
    )
    return iPhoneCapture(settings)


# ---- Public API ----

__all__ = [
    "iPhoneCapture",
    "iPhoneSettings",
    "iPhoneFrame",
    "iPhoneError",
    "create_iphone_capture",
]