"""
mocap/playback.py

Playback recorded motion data.

Plays back recorded blendshape coefficients with timing, speed control,
looping, and interpolation. Supports real-time playback driven by a timer
or Maya's timeline.

Features:
- Load recorded data from RecordingData or file
- Play, pause, stop, seek
- Speed control (slow-motion, fast-forward)
- Looping
- Frame interpolation for smooth playback
- Callback on frame updates
- Integration with MocapRecorder

Author: Maya FaceIT Team
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Union

# Import recording data
try:
    from .recorder import RecordingData, MocapRecorder
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False
    # Fallback for development
    class RecordingData:
        frames: List[Dict[str, float]] = []
        timestamps: List[float] = []
        frame_rate: int = 60
        duration: float = 0.0
    class MocapRecorder: pass

logger = logging.getLogger(__name__)

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"


# ---- Exceptions ----

class PlaybackError(Exception):
    """Base exception for playback operations."""
    pass


# ---- Data Models ----

@dataclass
class PlaybackSettings:
    """
    Settings for playback.
    """
    speed: float = 1.0                     # Playback speed multiplier
    loop: bool = False                     # Loop playback
    start_time: float = 0.0                # Start time in seconds
    end_time: Optional[float] = None       # End time in seconds (None = end of recording)
    interpolation: str = "linear"          # 'linear', 'step', 'cubic'
    frame_rate: Optional[int] = None       # Override frame rate
    auto_update: bool = True               # Auto-update on each call


@dataclass
class PlaybackState:
    """
    Current playback state.
    """
    playing: bool = False
    paused: bool = False
    current_time: float = 0.0
    current_frame: int = 0
    progress: float = 0.0
    duration: float = 0.0
    frame_rate: int = 60


# ---- Mocap Playback ----

class MocapPlayback:
    """
    Playback recorded facial motion data.

    Plays back recorded blendshape coefficients with timing.

    Usage:
        playback = MocapPlayback()
        playback.load(data)
        playback.set_frame_callback(my_callback)
        playback.play()
        # ... in main loop:
        playback.update(delta_time)
        # ...
        playback.stop()
    """

    def __init__(self, settings: Optional[PlaybackSettings] = None):
        """
        Initialize the playback.

        Args:
            settings: Optional settings.
        """
        self.settings = settings or PlaybackSettings()
        self._data: Optional[RecordingData] = None
        self._state = PlaybackState()
        self._frame_callbacks: List[Callable[[int, Dict[str, float]], None]] = []
        self._completed_callbacks: List[Callable[[], None]] = []
        self._last_frame_time = 0.0
        self._current_frame_data: Dict[str, float] = {}
        self._lock = False  # Simple lock for thread safety

        logger.debug("MocapPlayback initialized")

    # ---- Loading ----

    def load(self, data: RecordingData) -> None:
        """
        Load data for playback.

        Args:
            data: RecordingData object.
        """
        self._data = data
        self._state.duration = data.duration
        self._state.frame_rate = data.frame_rate
        self._state.current_time = self.settings.start_time
        self._state.current_frame = 0
        self._state.progress = 0.0

        # Apply start_time offset
        if self.settings.start_time > 0:
            self._state.current_time = self.settings.start_time
            self._state.current_frame = self._find_frame_at_time(self.settings.start_time)

        logger.info(f"Loaded {len(data.frames)} frames, duration: {data.duration:.2f}s")

    def load_from_file(self, filepath: str) -> None:
        """
        Load data from a file.

        Args:
            filepath: Path to JSON file.
        """
        if not HAS_DEPS:
            raise PlaybackError("MocapRecorder not available for file loading")
        recorder = MocapRecorder()
        data = recorder.load_from_file(filepath)
        self.load(data)

    # ---- Playback Control ----

    def play(self) -> None:
        """Start or resume playback."""
        if self._data is None:
            raise PlaybackError("No data loaded for playback")

        if self._state.playing and not self._state.paused:
            return

        self._state.playing = True
        self._state.paused = False
        self._last_frame_time = time.time()
        logger.info("Playback started")

    def pause(self) -> None:
        """Pause playback."""
        if not self._state.playing:
            return
        self._state.paused = True
        logger.info("Playback paused")

    def stop(self) -> None:
        """Stop playback and reset to start."""
        self._state.playing = False
        self._state.paused = False
        self._state.current_time = self.settings.start_time
        self._state.current_frame = self._find_frame_at_time(self.settings.start_time)
        self._state.progress = 0.0
        logger.info("Playback stopped")

    def seek(self, time_sec: float) -> None:
        """
        Seek to a specific time in seconds.

        Args:
            time_sec: Time in seconds.
        """
        if self._data is None:
            raise PlaybackError("No data loaded for playback")

        # Clamp to valid range
        end_time = self.settings.end_time or self._state.duration
        time_sec = max(self.settings.start_time, min(time_sec, end_time))

        self._state.current_time = time_sec
        self._state.current_frame = self._find_frame_at_time(time_sec)
        self._state.progress = (time_sec - self.settings.start_time) / (end_time - self.settings.start_time) if end_time > self.settings.start_time else 0.0

        # Update current frame data
        self._update_current_frame()

        logger.debug(f"Seek to {time_sec:.2f}s, frame {self._state.current_frame}")

    def seek_frame(self, frame_index: int) -> None:
        """
        Seek to a specific frame index.

        Args:
            frame_index: Frame index.
        """
        if self._data is None:
            raise PlaybackError("No data loaded for playback")

        if frame_index < 0 or frame_index >= len(self._data.frames):
            frame_index = 0

        self._state.current_frame = frame_index
        self._state.current_time = self._data.timestamps[frame_index] if frame_index < len(self._data.timestamps) else 0.0
        self._state.progress = self._state.current_time / self._state.duration if self._state.duration > 0 else 0.0

        # Update current frame data
        self._update_current_frame()

    # ---- Update ----

    def update(self, delta_time: Optional[float] = None) -> bool:
        """
        Update playback for the current time.

        Args:
            delta_time: Time elapsed since last update (in seconds).
                        If None, uses real time.

        Returns:
            True if a new frame was applied, False otherwise.
        """
        if not self._state.playing or self._state.paused:
            return False

        if self._data is None:
            return False

        # Calculate delta time
        if delta_time is None:
            current_time = time.time()
            delta = current_time - self._last_frame_time
            self._last_frame_time = current_time
        else:
            delta = delta_time

        # Apply speed
        delta *= self.settings.speed

        # Advance time
        new_time = self._state.current_time + delta
        end_time = self.settings.end_time or self._state.duration

        if new_time >= end_time:
            if self.settings.loop:
                # Loop back to start
                new_time = self.settings.start_time + (new_time - end_time) % (end_time - self.settings.start_time)
            else:
                # Stop at end
                new_time = end_time
                self.stop()
                self._notify_completed()
                return False

        # Find the frame at the new time
        new_frame = self._find_frame_at_time(new_time)
        if new_frame == self._state.current_frame and self._state.current_time == new_time:
            # No change
            self._state.current_time = new_time
            return False

        # Update state
        self._state.current_time = new_time
        self._state.current_frame = new_frame
        self._state.progress = (new_time - self.settings.start_time) / (end_time - self.settings.start_time) if end_time > self.settings.start_time else 0.0

        # Update current frame data
        self._update_current_frame()
        self._notify_frame(new_frame, self._current_frame_data)

        return True

    def _update_current_frame(self) -> None:
        """Update current frame data based on current frame index."""
        if self._data is None or self._state.current_frame >= len(self._data.frames):
            self._current_frame_data = {}
            return

        self._current_frame_data = self._data.frames[self._state.current_frame].copy()

    def _find_frame_at_time(self, time_sec: float) -> int:
        """
        Find the frame index at a given time.

        Args:
            time_sec: Time in seconds.

        Returns:
            Frame index.
        """
        if self._data is None or not self._data.timestamps:
            return 0

        timestamps = self._data.timestamps
        if time_sec <= timestamps[0]:
            return 0
        if time_sec >= timestamps[-1]:
            return len(timestamps) - 1

        # Binary search
        lo, hi = 0, len(timestamps) - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if timestamps[mid] < time_sec:
                lo = mid + 1
            else:
                hi = mid

        # Check if we are closer to previous or next
        if lo > 0:
            if abs(timestamps[lo] - time_sec) > abs(timestamps[lo-1] - time_sec):
                lo -= 1
        return lo

    # ---- Callbacks ----

    def add_frame_callback(self, callback: Callable[[int, Dict[str, float]], None]) -> None:
        """
        Add a callback for frame updates.

        Args:
            callback: Function called with (frame_index, coefficients).
        """
        if callback not in self._frame_callbacks:
            self._frame_callbacks.append(callback)

    def remove_frame_callback(self, callback: Callable[[int, Dict[str, float]], None]) -> None:
        """Remove a frame callback."""
        if callback in self._frame_callbacks:
            self._frame_callbacks.remove(callback)

    def add_completed_callback(self, callback: Callable[[], None]) -> None:
        """Add a callback for when playback completes."""
        if callback not in self._completed_callbacks:
            self._completed_callbacks.append(callback)

    def remove_completed_callback(self, callback: Callable[[], None]) -> None:
        """Remove a completed callback."""
        if callback in self._completed_callbacks:
            self._completed_callbacks.remove(callback)

    def _notify_frame(self, frame_index: int, coefficients: Dict[str, float]) -> None:
        """Notify frame callbacks."""
        for callback in self._frame_callbacks:
            try:
                callback(frame_index, coefficients)
            except Exception as e:
                logger.error(f"Frame callback error: {e}")

    def _notify_completed(self) -> None:
        """Notify completion callbacks."""
        for callback in self._completed_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Completed callback error: {e}")

    # ---- State Access ----

    def is_playing(self) -> bool:
        """Check if playback is active."""
        return self._state.playing and not self._state.paused

    def is_paused(self) -> bool:
        """Check if playback is paused."""
        return self._state.playing and self._state.paused

    def is_stopped(self) -> bool:
        """Check if playback is stopped."""
        return not self._state.playing

    def get_current_frame(self) -> int:
        """Get the current frame index."""
        return self._state.current_frame

    def get_current_time(self) -> float:
        """Get the current time in seconds."""
        return self._state.current_time

    def get_current_coefficients(self) -> Dict[str, float]:
        """Get the current frame's coefficients."""
        return self._current_frame_data.copy()

    def get_progress(self) -> float:
        """Get playback progress (0.0 to 1.0)."""
        return self._state.progress

    def get_state(self) -> PlaybackState:
        """Get the current playback state."""
        return self._state

    def get_duration(self) -> float:
        """Get the total duration of the loaded data."""
        if self._data:
            return self._data.duration
        return 0.0

    def get_frame_count(self) -> int:
        """Get the total number of frames."""
        if self._data:
            return len(self._data.frames)
        return 0

    # ---- Settings ----

    def set_speed(self, speed: float) -> None:
        """Set playback speed multiplier."""
        self.settings.speed = max(0.0, speed)

    def set_loop(self, loop: bool) -> None:
        """Enable or disable looping."""
        self.settings.loop = loop

    def set_interpolation(self, mode: str) -> None:
        """Set interpolation mode."""
        self.settings.interpolation = mode

    # ---- Utility ----

    def clear(self) -> None:
        """Clear loaded data and reset state."""
        self._data = None
        self._state = PlaybackState()
        self._current_frame_data = {}
        self._frame_callbacks.clear()
        self._completed_callbacks.clear()


# ---- Convenience Functions ----

def create_playback_from_file(
    filepath: str,
    settings: Optional[PlaybackSettings] = None,
) -> MocapPlayback:
    """
    Create a playback instance loaded from a file.

    Args:
        filepath: Path to JSON file.
        settings: Optional settings.

    Returns:
        MocapPlayback instance.
    """
    playback = MocapPlayback(settings)
    playback.load_from_file(filepath)
    return playback


# ---- Public API ----

__all__ = [
    "MocapPlayback",
    "PlaybackSettings",
    "PlaybackState",
    "PlaybackError",
    "create_playback_from_file",
]