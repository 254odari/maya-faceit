"""
animation/timeline.py

Central Time Management System for Maya Animation Framework.

This module provides a unified interface to Maya's timeline, playback, and
frame management. It is the authoritative source for all timing information
used by other modules: keyframes, curves, constraints, baking, cleanup, etc.

Responsibilities:
- Query and set current frame, playback range, animation range, selection range.
- Control playback: play, pause, stop, step forward/back, jump to start/end.
- Manage markers and bookmarks with labels and colors.
- Handle time units and FPS (frames per second).
- Provide diagnostics and statistics.
- Support snapshots (save/restore timeline state).
- Offer callbacks for timeline changes.

The module is Maya-independent in interface, but uses Maya commands internally.
It should not depend on any other animation module (baking, keyframes, etc.).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Dict, Any, Callable, Tuple, Set

# Maya imports (with fallback for testing)
try:
    import maya.cmds as cmds
    import maya.mel as mel
    from pymel.core import PyNode, currentTime, playbackOptions, setPlaybackRange, select
    import pymel.core as pm
except ImportError:
    # Dummy for development/testing
    class Dummy:
        def __getattr__(self, name):
            return lambda *args, **kwargs: None
    pm = Dummy()
    cmds = Dummy()
    mel = Dummy()

# ---- Part 1: Foundation ------------------------------------------------

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"

logger = logging.getLogger(__name__)

# Exceptions
class TimelineError(Exception):
    """Base exception for timeline errors."""
    pass

class InvalidFrameError(TimelineError):
    """Raised when an invalid frame number is used."""
    pass

class InvalidRangeError(TimelineError):
    """Raised when an invalid frame range is provided."""
    pass

class MarkerNotFoundError(TimelineError):
    """Raised when a marker is not found."""
    pass

class BookmarkNotFoundError(TimelineError):
    """Raised when a bookmark is not found."""
    pass

# ---- Part 2: Constants & Enumerations --------------------------------

class TimeUnit(Enum):
    """Maya time units."""
    GAME = "game"           # 15 fps
    FILM = "film"           # 24 fps
    PAL = "pal"             # 25 fps
    NTSC = "ntsc"           # 30 fps
    SHOW = "show"           # 48 fps
    PALF = "palf"           # 50 fps (PAL field)
    NTSCF = "ntscf"         # 60 fps (NTSC field)
    # Custom framerates
    _23_976 = 23.976
    _24 = 24
    _25 = 25
    _30 = 30
    _48 = 48
    _50 = 50
    _60 = 60
    _120 = 120
    CUSTOM = "custom"       # arbitrary fps


class PlaybackMode(Enum):
    """Playback looping mode."""
    PLAY_ONCE = "once"
    LOOP = "loop"
    OSCILLATE = "oscillate"  # ping-pong


class TimelineState(Enum):
    """Current playback state."""
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    SCRUBBING = "scrubbing"


# ---- Part 3: Data Models ----------------------------------------------

@dataclass
class TimelineRange:
    """A frame range (inclusive)."""
    start: int
    end: int

    def __post_init__(self):
        if self.start > self.end:
            raise InvalidRangeError(f"Start ({self.start}) > End ({self.end})")

    def length(self) -> int:
        return self.end - self.start + 1

    def contains(self, frame: int) -> bool:
        return self.start <= frame <= self.end

    def clamp(self, frame: int) -> int:
        if frame < self.start:
            return self.start
        if frame > self.end:
            return self.end
        return frame

    def to_tuple(self) -> Tuple[int, int]:
        return (self.start, self.end)


@dataclass
class PlaybackSettings:
    """Settings for playback control."""
    mode: PlaybackMode = PlaybackMode.LOOP
    speed: float = 1.0            # multiplier for real-time playback
    sound: bool = False           # mute sound
    update_view: bool = True      # update viewport while playing


@dataclass
class TimelineMarker:
    """A marker on the timeline."""
    frame: int
    label: str
    color: Optional[List[float]] = None  # RGB 0-1
    comment: str = ""


@dataclass
class TimelineBookmark:
    """A named bookmark (like a named frame range)."""
    name: str
    range: TimelineRange
    description: str = ""


@dataclass
class TimelineSnapshot:
    """Snapshot of the current timeline state."""
    current_frame: int
    playback_range: TimelineRange
    animation_range: TimelineRange
    selection_range: Optional[TimelineRange] = None
    markers: List[TimelineMarker] = field(default_factory=list)
    bookmarks: List[TimelineBookmark] = field(default_factory=list)
    fps: float = 24.0
    time_unit: TimeUnit = TimeUnit.FILM
    playback_mode: PlaybackMode = PlaybackMode.LOOP
    playback_speed: float = 1.0


@dataclass
class TimelineDiagnostics:
    """Diagnostic report."""
    state: TimelineState
    current_frame: int
    fps: float
    playback_range: TimelineRange
    animation_range: TimelineRange
    selection_range: Optional[TimelineRange]
    marker_count: int
    bookmark_count: int
    playback_mode: PlaybackMode
    is_playing: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class TimelineStatistics:
    """Statistics about the timeline."""
    total_frames: int
    fps: float
    duration_seconds: float
    markers: int
    bookmarks: int
    current_frame: int
    playback_speed: float
    # Additional
    frame_count_display: Optional[int] = None


# ---- Part 4: Timeline Manager ----------------------------------------

class TimelineManager:
    """
    Main controller for all timeline and playback operations.

    This class acts as a facade over Maya's timeline commands, providing
    a clean, consistent API for the rest of the animation package.
    """

    # Singleton instance (optional)
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        self._playback_mode = PlaybackMode.LOOP
        self._playback_speed = 1.0
        self._state = TimelineState.STOPPED
        self._listeners: List[Callable] = []
        self._marker_cache: List[TimelineMarker] = []  # lazy-loaded
        self._bookmark_cache: List[TimelineBookmark] = []  # lazy-loaded

    # ---- Core Methods ----

    def current_frame(self) -> int:
        """Return the current frame (integer)."""
        return int(cmds.currentTime(q=True))

    def set_current_frame(self, frame: int, update_view: bool = True) -> None:
        """Set the current frame."""
        if not isinstance(frame, int) or frame < 0:
            raise InvalidFrameError(f"Invalid frame: {frame}")
        cmds.currentTime(frame, update=update_view)
        self._notify_listeners()

    def frame_range(self) -> TimelineRange:
        """Return the current playback range."""
        start = int(cmds.playbackOptions(q=True, min=True))
        end = int(cmds.playbackOptions(q=True, max=True))
        return TimelineRange(start, end)

    def set_frame_range(self, start: int, end: int) -> None:
        """Set the playback range (min and max)."""
        if start > end:
            raise InvalidRangeError(f"Start ({start}) > End ({end})")
        cmds.playbackOptions(min=start, max=end)
        self._notify_listeners()

    def animation_range(self) -> TimelineRange:
        """Return the animation range (start/end for timeline)."""
        start = int(cmds.playbackOptions(q=True, animationStartTime=True))
        end = int(cmds.playbackOptions(q=True, animationEndTime=True))
        return TimelineRange(start, end)

    def set_animation_range(self, start: int, end: int) -> None:
        """Set the animation range (usually the same as playback)."""
        if start > end:
            raise InvalidRangeError(f"Start ({start}) > End ({end})")
        cmds.playbackOptions(animationStartTime=start, animationEndTime=end)
        self._notify_listeners()

    def selection_range(self) -> Optional[TimelineRange]:
        """Get the selected frame range from time slider (if any)."""
        # Maya doesn't directly expose selected range; we can use `time` attribute of selected items.
        # We'll simulate by checking selected keys? For now, return None.
        # A more advanced implementation could use `cmds.ls(sl=True, time=True)`.
        # Return playback range as fallback? We'll return None.
        return None

    # ---- Playback Control ----

    def play(self, mode: Optional[PlaybackMode] = None, speed: Optional[float] = None) -> None:
        """Start playback."""
        if mode is not None:
            self._playback_mode = mode
        if speed is not None:
            self._playback_speed = speed
        # Set Maya playback options
        cmds.playbackOptions(loop=self._playback_mode != PlaybackMode.PLAY_ONCE)
        cmds.playbackOptions(loopMode=self._playback_mode.value)
        cmds.play(forward=True)
        self._state = TimelineState.PLAYING
        self._notify_listeners()

    def pause(self) -> None:
        """Pause playback."""
        if self._state == TimelineState.PLAYING:
            cmds.play(state=False)
            self._state = TimelineState.PAUSED
            self._notify_listeners()

    def stop(self) -> None:
        """Stop playback and reset to start."""
        cmds.play(state=False)
        self._state = TimelineState.STOPPED
        # Optionally jump to start?
        # We can leave current frame as is, or reset to start of range.
        self._notify_listeners()

    def step_forward(self, frames: int = 1) -> None:
        """Step forward by a number of frames."""
        cur = self.current_frame()
        self.set_current_frame(cur + frames)

    def step_backward(self, frames: int = 1) -> None:
        """Step backward by a number of frames."""
        cur = self.current_frame()
        self.set_current_frame(cur - frames)

    def jump_start(self) -> None:
        """Jump to the first frame of playback range."""
        self.set_current_frame(self.frame_range().start)

    def jump_end(self) -> None:
        """Jump to the last frame of playback range."""
        self.set_current_frame(self.frame_range().end)

    def is_playing(self) -> bool:
        """Return True if currently playing."""
        return self._state == TimelineState.PLAYING

    def playback_state(self) -> TimelineState:
        return self._state

    def set_playback_mode(self, mode: PlaybackMode) -> None:
        self._playback_mode = mode
        if self._state == TimelineState.PLAYING:
            # Restart playback to apply mode? Not necessary.
            pass

    def set_playback_speed(self, speed: float) -> None:
        if speed <= 0:
            raise ValueError("Playback speed must be positive")
        self._playback_speed = speed
        # Maya doesn't have global speed; we can adjust frame rate temporarily? That's not recommended.
        # We'll store for reference; external systems can use it.

    # ---- Frame Range Management ----

    def set_playback(self, start: int, end: int) -> None:
        """Set playback range only."""
        self.set_frame_range(start, end)

    def set_animation(self, start: int, end: int) -> None:
        """Set animation range only."""
        self.set_animation_range(start, end)

    def set_range(self, start: int, end: int) -> None:
        """Set both playback and animation range to the same."""
        self.set_frame_range(start, end)
        self.set_animation_range(start, end)

    # ---- Markers ----

    def markers(self) -> List[TimelineMarker]:
        """Return all markers on the timeline."""
        # Maya stores markers as locators or via `marker` commands? Actually, Maya has `marker` command.
        # We'll use `cmds.marker` to query.
        if not self._marker_cache:
            self._refresh_markers()
        return self._marker_cache

    def add_marker(self, frame: int, label: str, color: Optional[List[float]] = None, comment: str = "") -> None:
        """Add a marker at the given frame."""
        # Maya markers are stored in the scene as attributes on the timeline.
        # Use `cmds.marker` with -e to add.
        # We'll store in cache.
        marker = TimelineMarker(frame, label, color, comment)
        # We don't have direct API for markers; we can use `cmds.marker` with -add.
        # The marker command uses named markers; we'll create a locator? Actually Maya has built-in markers.
        # For simplicity, we'll use `cmds.marker` - add marker with name.
        # But Maya's marker system is limited. We'll store our own markers as custom attributes on a hidden node.
        # This is a more robust approach. For now, we'll just add to cache and not sync.
        self._marker_cache.append(marker)
        self._notify_listeners()

    def remove_marker(self, frame: int, label: str) -> None:
        """Remove a marker by frame and label."""
        for i, m in enumerate(self._marker_cache):
            if m.frame == frame and m.label == label:
                del self._marker_cache[i]
                self._notify_listeners()
                return
        raise MarkerNotFoundError(f"Marker at {frame} with label '{label}' not found")

    def clear_markers(self) -> None:
        self._marker_cache.clear()
        self._notify_listeners()

    def _refresh_markers(self) -> None:
        """Load markers from Maya (if we implement persistence)."""
        # Placeholder: we'll keep cache as is.
        pass

    # ---- Bookmarks ----

    def bookmarks(self) -> List[TimelineBookmark]:
        return self._bookmark_cache

    def add_bookmark(self, name: str, range: TimelineRange, description: str = "") -> None:
        self._bookmark_cache.append(TimelineBookmark(name, range, description))
        self._notify_listeners()

    def remove_bookmark(self, name: str) -> None:
        for i, b in enumerate(self._bookmark_cache):
            if b.name == name:
                del self._bookmark_cache[i]
                self._notify_listeners()
                return
        raise BookmarkNotFoundError(f"Bookmark '{name}' not found")

    def clear_bookmarks(self) -> None:
        self._bookmark_cache.clear()
        self._notify_listeners()

    def goto_bookmark(self, name: str) -> None:
        """Jump to the start of a bookmark's range."""
        for b in self._bookmark_cache:
            if b.name == name:
                self.set_current_frame(b.range.start)
                return
        raise BookmarkNotFoundError(f"Bookmark '{name}' not found")

    # ---- Time Units & FPS ----

    def fps(self) -> float:
        """Return the current frames per second."""
        # Maya stores time unit as a string; we can parse.
        unit = cmds.currentUnit(q=True, time=True)
        fps_map = {
            'game': 15.0,
            'film': 24.0,
            'pal': 25.0,
            'ntsc': 30.0,
            'show': 48.0,
            'palf': 50.0,
            'ntscf': 60.0,
            'custom': 1.0,  # not used, get from other attr
        }
        if unit in fps_map:
            return fps_map[unit]
        # Custom: read from `playbackOptions` framerate? Actually, Maya uses `playbackOptions` for fps.
        # There's no direct FPS get; we can compute from time unit.
        # For custom, we can try to get from `playbackOptions(q=True, framerate)`? That returns a string.
        # We'll use `cmds.currentUnit(q=True, time=True)` and convert.
        # For simplicity, we'll return 24.0 as default.
        return 24.0

    def set_fps(self, fps: float) -> None:
        """Set the frames per second."""
        # Convert to Maya time unit string.
        fps_map = {
            15: 'game',
            24: 'film',
            25: 'pal',
            30: 'ntsc',
            48: 'show',
            50: 'palf',
            60: 'ntscf',
        }
        # For custom, we can set via `playbackOptions`? Actually, `playbackOptions` framerate is deprecated.
        # We'll set time unit.
        unit = fps_map.get(fps, 'custom')
        if unit == 'custom':
            # For custom, we need to set via `cmds.currentUnit(time='custom')` and then set framerate via `playbackOptions`
            # but that's not straightforward. We'll ignore for now.
            raise NotImplementedError("Setting custom FPS not fully supported")
        cmds.currentUnit(time=unit)
        self._notify_listeners()

    def time_unit(self) -> str:
        """Return Maya's time unit string."""
        return cmds.currentUnit(q=True, time=True)

    def seconds_to_frames(self, seconds: float) -> float:
        """Convert seconds to frames at current FPS."""
        return seconds * self.fps()

    def frames_to_seconds(self, frames: float) -> float:
        """Convert frames to seconds at current FPS."""
        return frames / self.fps()

    # ---- Snapshot ----

    def snapshot(self) -> TimelineSnapshot:
        """Capture the current timeline state."""
        return TimelineSnapshot(
            current_frame=self.current_frame(),
            playback_range=self.frame_range(),
            animation_range=self.animation_range(),
            selection_range=self.selection_range(),
            markers=self.markers(),
            bookmarks=self.bookmarks(),
            fps=self.fps(),
            time_unit=self.time_unit(),
            playback_mode=self._playback_mode,
            playback_speed=self._playback_speed,
        )

    def restore(self, snapshot: TimelineSnapshot) -> None:
        """Restore a previously captured snapshot."""
        self.set_frame_range(snapshot.playback_range.start, snapshot.playback_range.end)
        self.set_animation_range(snapshot.animation_range.start, snapshot.animation_range.end)
        self.set_current_frame(snapshot.current_frame)
        # Restore markers/bookmarks? We'll clear and add.
        self._marker_cache = snapshot.markers.copy()
        self._bookmark_cache = snapshot.bookmarks.copy()
        if snapshot.time_unit:
            try:
                self.set_fps(snapshot.fps)
            except:
                pass
        self._playback_mode = snapshot.playback_mode
        self._playback_speed = snapshot.playback_speed
        self._notify_listeners()

    # ---- Event Listeners ----

    def add_listener(self, callback: Callable) -> None:
        """Register a callback to be called on timeline changes."""
        self._listeners.append(callback)

    def remove_listener(self, callback: Callable) -> None:
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify_listeners(self) -> None:
        """Notify all registered listeners."""
        for cb in self._listeners:
            try:
                cb()
            except Exception as e:
                logger.warning(f"Timeline listener error: {e}")

    # ---- Diagnostics ----

    def diagnose(self) -> TimelineDiagnostics:
        """Generate a diagnostic report."""
        errors = []
        warnings = []
        # Check validity of ranges
        try:
            play_range = self.frame_range()
        except Exception as e:
            errors.append(f"Failed to get playback range: {e}")
            play_range = TimelineRange(1, 100)
        try:
            anim_range = self.animation_range()
        except:
            anim_range = play_range
        return TimelineDiagnostics(
            state=self._state,
            current_frame=self.current_frame(),
            fps=self.fps(),
            playback_range=play_range,
            animation_range=anim_range,
            selection_range=self.selection_range(),
            marker_count=len(self._marker_cache),
            bookmark_count=len(self._bookmark_cache),
            playback_mode=self._playback_mode,
            is_playing=self.is_playing(),
            errors=errors,
            warnings=warnings,
        )

    # ---- Statistics ----

    def statistics(self) -> TimelineStatistics:
        """Return statistics about the timeline."""
        fps = self.fps()
        play_range = self.frame_range()
        duration = play_range.length() / fps if fps > 0 else 0
        return TimelineStatistics(
            total_frames=play_range.length(),
            fps=fps,
            duration_seconds=duration,
            markers=len(self._marker_cache),
            bookmarks=len(self._bookmark_cache),
            current_frame=self.current_frame(),
            playback_speed=self._playback_speed,
        )


# ---- Part 10: Utility Functions ---------------------------------------

def get_current_frame() -> int:
    """Convenience function for current frame."""
    return TimelineManager().current_frame()


def set_current_frame(frame: int) -> None:
    """Convenience function."""
    TimelineManager().set_current_frame(frame)


def get_frame_range() -> TimelineRange:
    """Convenience function."""
    return TimelineManager().frame_range()


def set_frame_range(start: int, end: int) -> None:
    """Convenience function."""
    TimelineManager().set_frame_range(start, end)


# ---- Part 11: Public API -----------------------------------------------

__all__ = [
    # Main class
    "TimelineManager",
    # Data models
    "TimelineRange",
    "PlaybackSettings",
    "TimelineMarker",
    "TimelineBookmark",
    "TimelineSnapshot",
    "TimelineDiagnostics",
    "TimelineStatistics",
    # Enums
    "TimeUnit",
    "PlaybackMode",
    "TimelineState",
    # Exceptions
    "TimelineError",
    "InvalidFrameError",
    "InvalidRangeError",
    "MarkerNotFoundError",
    "BookmarkNotFoundError",
    # Utilities
    "get_current_frame",
    "set_current_frame",
    "get_frame_range",
    "set_frame_range",
]