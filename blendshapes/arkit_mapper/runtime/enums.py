"""
enums.py

Enumerations for the runtime system.
"""

from enum import Enum, IntEnum


class RuntimeMode(str, Enum):
    """Runtime operating mode."""

    LIVE = "live"
    PLAYBACK = "playback"
    RECORD = "record"
    SIMULATION = "simulation"
    OFFLINE = "offline"


class RuntimeState(str, Enum):
    """Runtime lifecycle state."""

    CREATED = "created"
    INITIALIZED = "initialized"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    SHUTDOWN = "shutdown"
    ERROR = "error"


class RuntimeEvent(str, Enum):
    """Events emitted by the runtime."""

    INITIALIZED = "initialized"
    STARTED = "started"
    STOPPED = "stopped"
    PAUSED = "paused"
    RESUMED = "resumed"
    FRAME_RECEIVED = "frame_received"
    FRAME_PROCESSED = "frame_processed"
    FRAME_DROPPED = "frame_dropped"
    RECORDING_STARTED = "recording_started"
    RECORDING_STOPPED = "recording_stopped"
    PLAYBACK_STARTED = "playback_started"
    PLAYBACK_FINISHED = "playback_finished"
    ERROR = "error"


class RuntimePriority(IntEnum):
    """Update priority for callback ordering."""

    LOW = 0
    NORMAL = 10
    HIGH = 20
    CRITICAL = 100


class FrameSource(str, Enum):
    """Source of incoming facial data."""

    ARKIT = "arkit"
    MEDIAPIPE = "mediapipe"
    AUDIO2FACE = "audio2face"
    FACS = "facs"
    PLAYBACK = "playback"
    CUSTOM = "custom"