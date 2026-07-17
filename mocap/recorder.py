"""
mocap/recorder.py

Record facial motion data.

Records blendshape coefficients over time for playback and export.
Supports real-time recording with timestamps, frame rates, and metadata.

Features:
- Record blendshape frames with timestamps
- Support for various frame rates
- Automatic stop on max frames or duration
- Export to JSON format
- Import from JSON format
- Batch recording with callbacks
- Metadata storage (source, device, performer, etc.)

Author: Maya FaceIT Team
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Union

logger = logging.getLogger(__name__)

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"


# ---- Exceptions ----

class RecorderError(Exception):
    """Base exception for recorder operations."""
    pass


# ---- Data Models ----

@dataclass
class RecordingSettings:
    """
    Settings for mocap recording.
    """
    frame_rate: int = 60                  # Target frame rate (fps)
    max_frames: int = 36000               # Maximum frames (10 min at 60fps)
    max_duration: float = 600.0           # Maximum duration in seconds (10 min)
    auto_stop: bool = True                # Auto-stop when max reached
    stop_callback: Optional[Callable[[], None]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecordingData:
    """
    Recorded mocap data.
    """
    frames: List[Dict[str, float]] = field(default_factory=list)
    timestamps: List[float] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    frame_rate: int = 60
    source: str = "unknown"
    duration: float = 0.0


# ---- Mocap Recorder ----

class MocapRecorder:
    """
    Record facial motion data.

    Records blendshape coefficients with timestamps for playback.
    Supports live recording from any data source.

    Usage:
        recorder = MocapRecorder()
        recorder.start()
        # ... in loop:
        recorder.record_frame(blendshapes)
        # ... 
        recorder.stop()
        data = recorder.get_data()
        recorder.save_to_file("recording.json")
    """

    def __init__(self, settings: Optional[RecordingSettings] = None):
        """
        Initialize the recorder.

        Args:
            settings: Optional settings.
        """
        self.settings = settings or RecordingSettings()
        self._frames: List[Dict[str, float]] = []
        self._timestamps: List[float] = []
        self._recording = False
        self._start_time = 0.0
        self._frame_count = 0
        self._last_frame_time = 0.0

        # Metadata
        self._metadata = self.settings.metadata.copy()
        self._metadata["frame_rate"] = self.settings.frame_rate
        self._metadata["created"] = time.ctime()

        logger.debug("MocapRecorder initialized")

    # ---- Recording Control ----

    def start(self) -> None:
        """
        Start recording.

        Raises:
            RecorderError: If already recording.
        """
        if self._recording:
            raise RecorderError("Recording already in progress")

        self._frames = []
        self._timestamps = []
        self._start_time = time.time()
        self._last_frame_time = self._start_time
        self._frame_count = 0
        self._recording = True

        logger.info("Recording started")

    def stop(self) -> None:
        """
        Stop recording.

        Returns:
            RecordingData if recording was active.
        """
        if not self._recording:
            logger.warning("Recording not active")
            return

        self._recording = False
        logger.info(f"Recording stopped: {len(self._frames)} frames, {self._timestamps[-1] if self._timestamps else 0:.2f}s")

    def is_recording(self) -> bool:
        """Check if recording is active."""
        return self._recording

    def record_frame(self, coefficients: Dict[str, float]) -> None:
        """
        Record a single frame.

        Args:
            coefficients: Blendshape coefficient dict.
        """
        if not self._recording:
            logger.warning("Recording not active; frame ignored")
            return

        # Check max frames
        if self.settings.max_frames and len(self._frames) >= self.settings.max_frames:
            if self.settings.auto_stop:
                self.stop()
                if self.settings.stop_callback:
                    self.settings.stop_callback()
            return

        # Check max duration
        elapsed = time.time() - self._start_time
        if self.settings.max_duration and elapsed >= self.settings.max_duration:
            if self.settings.auto_stop:
                self.stop()
                if self.settings.stop_callback:
                    self.settings.stop_callback()
            return

        # Store frame
        self._frames.append(coefficients.copy())
        self._timestamps.append(elapsed)
        self._frame_count += 1
        self._last_frame_time = time.time()

    def record_from_callback(
        self,
        callback: Callable[[], Dict[str, float]],
        duration: Optional[float] = None,
        frame_rate: Optional[int] = None,
    ) -> None:
        """
        Record from a callback function that returns blendshapes.

        This is a blocking call that records frames at the specified rate.

        Args:
            callback: Function returning blendshape dict.
            duration: Duration in seconds (overrides max_duration).
            frame_rate: Frame rate (overrides settings).
        """
        fps = frame_rate or self.settings.frame_rate
        interval = 1.0 / fps
        max_duration = duration or self.settings.max_duration

        self.start()
        start_time = time.time()

        while self._recording:
            # Check duration
            elapsed = time.time() - start_time
            if max_duration and elapsed >= max_duration:
                break

            # Get frame
            try:
                coeffs = callback()
                if coeffs:
                    self.record_frame(coeffs)
            except Exception as e:
                logger.error(f"Callback error: {e}")

            # Wait for next frame
            time.sleep(interval)

        self.stop()

    # ---- Data Access ----

    def get_data(self) -> RecordingData:
        """
        Get the recorded data.

        Returns:
            RecordingData object.
        """
        duration = self._timestamps[-1] if self._timestamps else 0.0
        return RecordingData(
            frames=self._frames,
            timestamps=self._timestamps,
            metadata=self._metadata,
            frame_rate=self.settings.frame_rate,
            source=self._metadata.get("source", "unknown"),
            duration=duration,
        )

    def get_frames(self) -> List[Dict[str, float]]:
        """Get recorded frames."""
        return self._frames

    def get_timestamps(self) -> List[float]:
        """Get recorded timestamps."""
        return self._timestamps

    def get_frame_count(self) -> int:
        """Get number of recorded frames."""
        return len(self._frames)

    def get_duration(self) -> float:
        """Get recording duration in seconds."""
        if self._timestamps:
            return self._timestamps[-1]
        return 0.0

    # ---- File I/O ----

    def save_to_file(self, filepath: str) -> None:
        """
        Save recorded data to a JSON file.

        Args:
            filepath: Output file path.
        """
        data = self.get_data()
        output = {
            "metadata": data.metadata,
            "frame_rate": data.frame_rate,
            "source": data.source,
            "duration": data.duration,
            "timestamps": data.timestamps,
            "frames": data.frames,
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        logger.info(f"Recording saved to {filepath} ({len(data.frames)} frames)")

    def load_from_file(self, filepath: str) -> RecordingData:
        """
        Load recorded data from a JSON file.

        Args:
            filepath: Input file path.

        Returns:
            RecordingData object.
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return RecordingData(
            frames=data.get("frames", []),
            timestamps=data.get("timestamps", []),
            metadata=data.get("metadata", {}),
            frame_rate=data.get("frame_rate", 60),
            source=data.get("source", "unknown"),
            duration=data.get("duration", 0.0),
        )

    # ---- Utility ----

    def clear(self) -> None:
        """Clear recorded data without stopping recording."""
        self._frames = []
        self._timestamps = []
        self._frame_count = 0

    def set_metadata(self, key: str, value: Any) -> None:
        """Set metadata for the recording."""
        self._metadata[key] = value

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get recorder statistics.

        Returns:
            Dict with recording stats.
        """
        return {
            "recording": self._recording,
            "frame_count": self._frame_count,
            "duration": self.get_duration(),
            "max_frames": self.settings.max_frames,
            "max_duration": self.settings.max_duration,
            "frame_rate": self.settings.frame_rate,
            "start_time": self._start_time if self._recording else None,
        }


# ---- Convenience Functions ----

def save_recording(recording: RecordingData, filepath: str) -> None:
    """
    Save a RecordingData object to a file.

    Args:
        recording: RecordingData to save.
        filepath: Output file path.
    """
    output = {
        "metadata": recording.metadata,
        "frame_rate": recording.frame_rate,
        "source": recording.source,
        "duration": recording.duration,
        "timestamps": recording.timestamps,
        "frames": recording.frames,
    }
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)


def load_recording(filepath: str) -> RecordingData:
    """
    Load a RecordingData from a file.

    Args:
        filepath: Input file path.

    Returns:
        RecordingData object.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return RecordingData(
        frames=data.get("frames", []),
        timestamps=data.get("timestamps", []),
        metadata=data.get("metadata", {}),
        frame_rate=data.get("frame_rate", 60),
        source=data.get("source", "unknown"),
        duration=data.get("duration", 0.0),
    )


# ---- Public API ----

__all__ = [
    "MocapRecorder",
    "RecordingSettings",
    "RecordingData",
    "RecorderError",
    "save_recording",
    "load_recording",
]