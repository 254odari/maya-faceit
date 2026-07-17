"""
cache/landmark_cache.py

Facial Landmark Cache System for Maya FaceIT.

This module caches all detected facial landmarks and derived facial feature
information so expensive landmark detection (MediaPipe, OpenSeeFace, ARKit, etc.)
only runs when necessary.

Responsibilities:
- Store and retrieve facial landmarks by frame or timestamp.
- Cache landmarks from various sources (MediaPipe, ARKit, custom).
- Organize landmarks into facial regions (eyes, mouth, brows, etc.).
- Cache head pose (pitch, yaw, roll, forward vector).
- Maintain tracking history for smoothing and prediction.
- Track confidence scores per landmark and region.
- Validate landmark data integrity and consistency.
- Provide statistics and diagnostics.

Dependencies:
- cache_base.py: BaseCache class.
- cache_utils.py: Key generation and utilities.
- cache_statistics.py: Statistics dataclass.
- landmark/ (future): Landmark definitions and mappings.
- arkit/ (future): ARKit-specific landmarks.

The module uses Maya's Python API and threading for thread safety.
"""

from __future__ import annotations

import copy
import logging
import math
import threading
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Dict, Any, Set, Tuple, Union, Callable, Iterator

# Import base cache and utilities (with fallback)
try:
    from .cache_base import BaseCache, CacheSettings, CacheEntry, CacheMetadata, CacheStatus
    from .cache_utils import get_cache_key, hash_data, validate_cache_key, sanitize_key
    from .cache_statistics import CacheStatistics
except ImportError:
    # Minimal fallback
    class BaseCache:
        def __init__(self, name, cache_type, settings=None):
            self.name = name
            self.cache_type = cache_type
            self._storage = {}
            self._lock = threading.RLock()
        def store(self, key, value): pass
        def get(self, key): return None
        def delete(self, key): pass
        def clear(self): pass
        def contains(self, key): return False
        def size(self): return 0
        def statistics(self): return CacheStatistics()
        def memory_usage(self): return 0.0
    class CacheSettings: pass
    class CacheEntry: pass
    class CacheMetadata: pass
    class CacheStatus: pass
    def get_cache_key(*args, **kwargs): return str(args)
    def hash_data(data): return str(hash(str(data)))
    def validate_cache_key(key): return isinstance(key, str) and len(key) > 0
    def sanitize_key(key): return key.strip()
    class CacheStatistics:
        def __init__(self):
            self.hits = 0
            self.misses = 0
            self.hit_rate = 0.0
            self.memory_usage_mb = 0.0
            self.total_entries = 0
            self.by_type = {}
            self.invalidations = 0
            self.evictions = 0

logger = logging.getLogger(__name__)

# ---- Part 2: Constants & Enumerations --------------------------------

class LandmarkSource(Enum):
    """Source of landmark data."""
    MEDIAPIPE = "mediapipe"
    ARKIT = "arkit"
    OPENSEEFACE = "openseeface"
    CUSTOM = "custom"


class LandmarkSpace(Enum):
    """Coordinate space for landmarks."""
    WORLD = "world"
    OBJECT = "object"
    IMAGE = "image"
    NORMALIZED = "normalized"


class TrackingState(Enum):
    """State of face tracking."""
    NOT_TRACKED = "not_tracked"
    TRACKING = "tracking"
    LOST = "lost"
    RECOVERING = "recovering"


class FacialRegion(Enum):
    """Facial regions for grouping landmarks."""
    FACE = "face"
    LEFT_EYE = "left_eye"
    RIGHT_EYE = "right_eye"
    LEFT_IRIS = "left_iris"
    RIGHT_IRIS = "right_iris"
    NOSE = "nose"
    MOUTH = "mouth"
    UPPER_LIP = "upper_lip"
    LOWER_LIP = "lower_lip"
    JAW = "jaw"
    LEFT_BROW = "left_brow"
    RIGHT_BROW = "right_brow"
    FOREHEAD = "forehead"
    LEFT_EYEBROW = "left_eyebrow"
    RIGHT_EYEBROW = "right_eyebrow"


# ---- Part 3: Data Models ----------------------------------------------

@dataclass
class LandmarkPoint:
    """A single facial landmark point."""
    index: int
    x: float
    y: float
    z: float = 0.0
    confidence: float = 1.0
    visible: bool = True

    def to_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)

    def distance_to(self, other: "LandmarkPoint") -> float:
        dx = self.x - other.x
        dy = self.y - other.y
        dz = self.z - other.z
        return math.sqrt(dx*dx + dy*dy + dz*dz)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "confidence": self.confidence,
            "visible": self.visible,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LandmarkPoint":
        return cls(
            index=data["index"],
            x=data["x"],
            y=data["y"],
            z=data.get("z", 0.0),
            confidence=data.get("confidence", 1.0),
            visible=data.get("visible", True),
        )


@dataclass
class LandmarkFrame:
    """A complete set of landmarks for a single frame."""
    frame_number: int
    timestamp: float
    source: LandmarkSource
    landmarks: List[LandmarkPoint]
    confidence: float = 1.0
    tracking_state: TrackingState = TrackingState.TRACKING
    head_pose: Optional["HeadPoseData"] = None
    bounding_box: Optional[Tuple[float, float, float, float]] = None  # (x, y, w, h) in image space
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_landmark(self, index: int) -> Optional[LandmarkPoint]:
        for lm in self.landmarks:
            if lm.index == index:
                return lm
        return None

    def get_region(self, region: FacialRegion) -> List[LandmarkPoint]:
        # Placeholder: region mapping would be defined elsewhere.
        # For now, return all landmarks.
        return self.landmarks[:]


@dataclass
class HeadPoseData:
    """Head pose information."""
    pitch: float  # degrees
    yaw: float    # degrees
    roll: float   # degrees
    forward_vector: Tuple[float, float, float] = (0.0, 0.0, 1.0)
    up_vector: Tuple[float, float, float] = (0.0, 1.0, 0.0)
    translation: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation_matrix: Optional[List[List[float]]] = None
    confidence: float = 1.0


@dataclass
class FacialRegionData:
    """Data for a specific facial region."""
    region: FacialRegion
    landmarks: List[LandmarkPoint]
    center: Optional[LandmarkPoint] = None
    confidence: float = 1.0
    bounding_box: Optional[Tuple[float, float, float, float]] = None


@dataclass
class TrackingHistory:
    """History of tracking states and confidence over time."""
    frames: List[LandmarkFrame] = field(default_factory=list)
    max_length: int = 100
    smoothing_window: int = 5

    def add_frame(self, frame: LandmarkFrame) -> None:
        self.frames.append(frame)
        if len(self.frames) > self.max_length:
            self.frames.pop(0)

    def get_latest(self) -> Optional[LandmarkFrame]:
        return self.frames[-1] if self.frames else None

    def get_at(self, index: int) -> Optional[LandmarkFrame]:
        if 0 <= index < len(self.frames):
            return self.frames[index]
        return None

    def get_smoothed(self, window: Optional[int] = None) -> Optional[LandmarkFrame]:
        """Return a smoothed version of the latest frame using moving average."""
        if not self.frames:
            return None
        if window is None:
            window = self.smoothing_window
        window = min(window, len(self.frames))
        if window == 1:
            return self.frames[-1]
        # Average landmarks across the window
        latest = self.frames[-1]
        # We'll compute average positions for each landmark index
        landmark_dict: Dict[int, List[LandmarkPoint]] = {}
        for i in range(-window, 0):
            frame = self.frames[i]
            for lm in frame.landmarks:
                if lm.index not in landmark_dict:
                    landmark_dict[lm.index] = []
                landmark_dict[lm.index].append(lm)
        averaged = []
        for idx, points in landmark_dict.items():
            if not points:
                continue
            avg_x = sum(p.x for p in points) / len(points)
            avg_y = sum(p.y for p in points) / len(points)
            avg_z = sum(p.z for p in points) / len(points)
            avg_conf = sum(p.confidence for p in points) / len(points)
            # Use the latest visibility
            vis = points[-1].visible
            averaged.append(LandmarkPoint(
                index=idx,
                x=avg_x,
                y=avg_y,
                z=avg_z,
                confidence=avg_conf,
                visible=vis
            ))
        # Create a new frame with averaged landmarks
        smoothed_frame = LandmarkFrame(
            frame_number=latest.frame_number,
            timestamp=latest.timestamp,
            source=latest.source,
            landmarks=averaged,
            confidence=latest.confidence,
            tracking_state=latest.tracking_state,
            head_pose=latest.head_pose,
            bounding_box=latest.bounding_box,
            metadata=latest.metadata.copy()
        )
        return smoothed_frame


@dataclass
class LandmarkStatistics:
    """Statistics for landmark cache."""
    total_frames: int = 0
    total_landmarks: int = 0
    by_source: Dict[str, int] = field(default_factory=dict)
    average_confidence: float = 0.0
    tracking_state_counts: Dict[str, int] = field(default_factory=dict)
    cache_hits: int = 0
    cache_misses: int = 0
    hit_rate: float = 0.0


@dataclass
class LandmarkReport:
    """Diagnostic report."""
    success: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    statistics: Optional[LandmarkStatistics] = None
    details: Dict[str, Any] = field(default_factory=dict)


# ---- Part 4: Landmark Cache Manager -----------------------------------

class LandmarkCache(BaseCache):
    """
    Facial Landmark Cache.

    Stores detected facial landmarks, regions, head pose, tracking history,
    and confidence scores for efficient reuse across the plugin.
    """

    def __init__(self, name: str = "landmark_cache", settings: Optional[CacheSettings] = None):
        super().__init__(name=name, cache_type="landmark", settings=settings)

        # Frame storage: key = frame_number or timestamp, value = LandmarkFrame
        self._frames: Dict[int, LandmarkFrame] = {}  # frame_number -> LandmarkFrame
        self._frame_by_timestamp: Dict[float, LandmarkFrame] = {}  # timestamp -> LandmarkFrame

        # Region storage: key = region name, value = facial region data for latest frame
        self._regions: Dict[str, FacialRegionData] = {}

        # Head pose for latest frame
        self._latest_head_pose: Optional[HeadPoseData] = None

        # Tracking history
        self._history = TrackingHistory()

        # Confidence cache: frame_number -> dict of landmark index -> confidence
        self._confidence_cache: Dict[int, Dict[int, float]] = {}

        # Mapping cache: source -> internal -> arkit, etc. (future)
        self._mapping_cache: Dict[str, Any] = {}

        self._lock = threading.RLock()

    # ---- Core Operations ----

    def store_landmarks(self, frame: LandmarkFrame) -> None:
        """
        Store a landmark frame in the cache.

        Args:
            frame: LandmarkFrame object.
        """
        with self._lock:
            # Store by frame number
            self._frames[frame.frame_number] = frame
            # Store by timestamp
            self._frame_by_timestamp[frame.timestamp] = frame
            # Update latest head pose
            if frame.head_pose:
                self._latest_head_pose = frame.head_pose
            # Update history
            self._history.add_frame(frame)
            # Update confidence cache
            conf_dict = {lm.index: lm.confidence for lm in frame.landmarks}
            self._confidence_cache[frame.frame_number] = conf_dict

            # Update regions (lazy, compute on demand)
            # We'll clear region cache and let get_region recompute
            self._regions.clear()

            # Store in base cache for general lookup
            key = f"frame_{frame.frame_number}"
            self.store(key, frame)

            # Update statistics
            # (will be computed on demand)

            logger.debug(f"LandmarkCache: stored frame {frame.frame_number} ({len(frame.landmarks)} landmarks)")

    def get_landmarks(self, frame_number: int) -> Optional[LandmarkFrame]:
        """
        Retrieve a landmark frame by frame number.
        """
        with self._lock:
            # Check base cache first
            key = f"frame_{frame_number}"
            frame = self.get(key)
            if frame:
                # Update hit statistics
                self._update_hit()
                return frame
            # If not in base cache, check internal dict
            frame = self._frames.get(frame_number)
            if frame:
                # Cache it in base cache for future
                self.store(key, frame)
                self._update_hit()
            else:
                self._update_miss()
            return frame

    def get_latest_landmarks(self) -> Optional[LandmarkFrame]:
        """Return the most recent landmarks."""
        with self._lock:
            return self._history.get_latest()

    def get_landmarks_by_timestamp(self, timestamp: float) -> Optional[LandmarkFrame]:
        """Retrieve landmarks by timestamp."""
        with self._lock:
            return self._frame_by_timestamp.get(timestamp)

    def get_region(self, region: FacialRegion) -> Optional[FacialRegionData]:
        """
        Get landmarks for a specific facial region from the latest frame.
        """
        with self._lock:
            # Check if we have cached region data
            region_key = region.value
            if region_key in self._regions:
                return self._regions[region_key]

            # Get latest frame
            latest = self._history.get_latest()
            if not latest:
                return None

            # Extract landmarks for this region
            # This requires a mapping from landmark indices to regions.
            # For now, we'll assume a simple mapping based on known indices.
            # In production, we would use a proper region mapping.
            region_landmarks = self._extract_region_landmarks(latest.landmarks, region)
            if not region_landmarks:
                return None

            # Compute center
            center = None
            if region_landmarks:
                cx = sum(lm.x for lm in region_landmarks) / len(region_landmarks)
                cy = sum(lm.y for lm in region_landmarks) / len(region_landmarks)
                cz = sum(lm.z for lm in region_landmarks) / len(region_landmarks)
                # Find closest landmark to center
                min_dist = float('inf')
                for lm in region_landmarks:
                    dist = math.sqrt((lm.x-cx)**2 + (lm.y-cy)**2 + (lm.z-cz)**2)
                    if dist < min_dist:
                        min_dist = dist
                        center = lm

            region_data = FacialRegionData(
                region=region,
                landmarks=region_landmarks,
                center=center,
                confidence=latest.confidence,
                bounding_box=latest.bounding_box
            )
            self._regions[region_key] = region_data
            return region_data

    def get_head_pose(self) -> Optional[HeadPoseData]:
        """Return the latest head pose."""
        with self._lock:
            return self._latest_head_pose

    def get_tracking_history(self) -> TrackingHistory:
        """Return the tracking history."""
        return self._history

    def get_smoothed_landmarks(self, window: int = 5) -> Optional[LandmarkFrame]:
        """Return a smoothed version of the latest frame."""
        with self._lock:
            return self._history.get_smoothed(window)

    def invalidate_frame(self, frame_number: int) -> None:
        """Invalidate a specific frame."""
        with self._lock:
            key = f"frame_{frame_number}"
            self.delete(key)
            self._frames.pop(frame_number, None)
            # Remove from timestamp dict
            for ts, frame in list(self._frame_by_timestamp.items()):
                if frame.frame_number == frame_number:
                    del self._frame_by_timestamp[ts]
                    break
            self._confidence_cache.pop(frame_number, None)
            # Remove from history (if present)
            self._history.frames = [f for f in self._history.frames if f.frame_number != frame_number]
            # Clear region cache (may need to recompute)
            self._regions.clear()
            if self._latest_head_pose and self._frames:
                # Update latest head pose from most recent frame
                latest = self._history.get_latest()
                if latest:
                    self._latest_head_pose = latest.head_pose
                else:
                    self._latest_head_pose = None

    def invalidate_all(self) -> None:
        """Clear all landmark data from the cache."""
        with self._lock:
            self.clear()
            self._frames.clear()
            self._frame_by_timestamp.clear()
            self._regions.clear()
            self._latest_head_pose = None
            self._history = TrackingHistory()
            self._confidence_cache.clear()
            self._mapping_cache.clear()

    # ---- Helper Methods ----

    def _extract_region_landmarks(self, landmarks: List[LandmarkPoint], region: FacialRegion) -> List[LandmarkPoint]:
        """
        Extract landmarks for a specific facial region.
        This is a placeholder; production would use a proper mapping.
        """
        # MediaPipe 468 landmarks typical indices (simplified)
        # For demonstration, we'll use a simple mapping.
        region_indices = {
            FacialRegion.FACE: list(range(0, 468)),
            FacialRegion.LEFT_EYE: [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246],
            FacialRegion.RIGHT_EYE: [263, 249, 390, 373, 374, 380, 381, 382, 362, 398, 384, 385, 386, 387, 388, 466],
            FacialRegion.LEFT_IRIS: [468, 469, 470, 471, 472, 473],
            FacialRegion.RIGHT_IRIS: [474, 475, 476, 477, 478, 479],
            FacialRegion.NOSE: [1, 2, 98, 327, 4, 5, 6, 8, 94, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 211, 212, 213, 214, 215, 216, 217, 218, 219, 220, 221, 222, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 234, 235, 236, 237, 238, 239, 240, 241, 242, 243, 244, 245],
            FacialRegion.MOUTH: [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95, 78, 62, 76, 150, 152, 185, 40, 39, 37, 0, 267, 269, 270, 409, 415, 310, 311, 312, 13, 82, 81, 80, 191, 14, 87, 178, 88, 95, 78, 62, 76, 150, 152, 185, 40, 39, 37, 0, 267, 269, 270, 409, 415, 310, 311, 312, 13, 82, 81, 80, 191],
            FacialRegion.UPPER_LIP: [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95, 78, 62, 76, 150, 152, 185, 40, 39, 37, 0, 267, 269, 270, 409, 415, 310, 311, 312, 13, 82, 81, 80, 191],
            FacialRegion.LOWER_LIP: [14, 87, 178, 88, 95, 78, 62, 76, 150, 152, 185, 40, 39, 37, 0, 267, 269, 270, 409, 415, 310, 311, 312, 13, 82, 81, 80, 191],
            FacialRegion.JAW: [0, 4, 5, 6, 8, 10, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 211, 212, 213, 214, 215, 216, 217, 218, 219, 220, 221, 222, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 234, 235, 236, 237, 238, 239, 240, 241, 242, 243, 244, 245],
            FacialRegion.LEFT_BROW: [46, 53, 52, 65, 55, 70, 63, 105, 66, 107, 67, 109, 69, 108, 72, 142, 73, 143, 74, 144, 75, 145, 76, 146, 77, 147, 78, 148, 79, 149, 80, 150, 81, 151, 82, 152, 83, 153, 84, 154, 85, 155, 86, 156, 87, 157, 88, 158, 89, 159, 90, 160, 91, 161, 92, 162, 93, 163, 94, 164, 95, 165, 96, 166, 97, 167, 98, 168, 99, 169, 100, 170, 101, 171, 102, 172, 103, 173, 104, 174, 105, 175, 106, 176, 107, 177, 108, 178, 109, 179, 110, 180, 111, 181, 112, 182, 113, 183, 114, 184, 115, 185, 116, 186, 117, 187, 118, 188, 119, 189, 120, 190, 121, 191, 122, 192, 123, 193, 124, 194, 125, 195, 126, 196, 127, 197, 128, 198, 129, 199, 130, 200, 131, 201, 132, 202, 133, 203, 134, 204, 135, 205, 136, 206, 137, 207, 138, 208, 139, 209, 140, 210, 141, 211, 142, 212, 143, 213, 144, 214, 145, 215, 146, 216, 147, 217, 148, 218, 149, 219, 150, 220, 151, 221, 152, 222, 153, 223, 154, 224, 155, 225, 156, 226, 157, 227, 158, 228, 159, 229, 160, 230, 161, 231, 162, 232, 163, 233, 164, 234, 165, 235, 166, 236, 167, 237, 168, 238, 169, 239, 170, 240, 171, 241, 172, 242, 173, 243, 174, 244, 175, 245],
            FacialRegion.RIGHT_BROW: [276, 283, 282, 295, 285, 300, 293, 334, 296, 335, 299, 337, 339, 303, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362, 363, 364, 365, 366, 367, 368, 369, 370, 371, 372, 373, 374, 375, 376, 377, 378, 379, 380, 381, 382, 383, 384, 385, 386, 387, 388, 389, 390, 391, 392, 393, 394, 395, 396, 397, 398, 399, 400, 401, 402, 403, 404, 405, 406, 407, 408, 409, 410, 411, 412, 413, 414, 415, 416, 417, 418, 419, 420, 421, 422, 423, 424, 425, 426, 427, 428, 429, 430, 431, 432, 433, 434, 435, 436, 437, 438, 439, 440, 441, 442, 443, 444, 445, 446, 447, 448, 449, 450, 451, 452, 453, 454, 455, 456, 457, 458, 459, 460, 461, 462, 463, 464, 465, 466, 467],
        }
        indices = region_indices.get(region, [])
        if not indices:
            return []
        # Filter landmarks by index
        return [lm for lm in landmarks if lm.index in indices]

    def _update_hit(self):
        if self._statistics:
            self._statistics.hits += 1

    def _update_miss(self):
        if self._statistics:
            self._statistics.misses += 1

    # ---- Statistics ----

    def statistics(self) -> CacheStatistics:
        """Return cache statistics with landmark-specific data."""
        stats = super().statistics()
        # Augment with our own counts
        stats.total_entries = len(self._frames)
        stats.by_type["frames"] = len(self._frames)
        stats.by_type["history_length"] = len(self._history.frames)
        stats.by_type["regions"] = len(self._regions)
        return stats

    def get_landmark_statistics(self) -> LandmarkStatistics:
        """Return detailed landmark statistics."""
        with self._lock:
            lm_stats = LandmarkStatistics()
            lm_stats.total_frames = len(self._frames)
            total_lm = sum(len(f.landmarks) for f in self._frames.values())
            lm_stats.total_landmarks = total_lm
            # By source
            source_counts = {}
            for f in self._frames.values():
                src = f.source.value
                source_counts[src] = source_counts.get(src, 0) + 1
            lm_stats.by_source = source_counts
            # Confidence
            conf_sum = 0
            conf_count = 0
            for f in self._frames.values():
                for lm in f.landmarks:
                    conf_sum += lm.confidence
                    conf_count += 1
            if conf_count > 0:
                lm_stats.average_confidence = conf_sum / conf_count
            # Tracking state counts
            state_counts = {}
            for f in self._frames.values():
                state = f.tracking_state.value
                state_counts[state] = state_counts.get(state, 0) + 1
            lm_stats.tracking_state_counts = state_counts
            # Cache hits/misses
            if self._statistics:
                lm_stats.cache_hits = self._statistics.hits
                lm_stats.cache_misses = self._statistics.misses
                total = lm_stats.cache_hits + lm_stats.cache_misses
                if total > 0:
                    lm_stats.hit_rate = lm_stats.cache_hits / total
            return lm_stats

    # ---- Validation ----

    def validate_frame(self, frame: LandmarkFrame) -> List[str]:
        """Validate a frame's data integrity."""
        errors = []
        if not frame.landmarks:
            errors.append("No landmarks in frame")
        # Check indices unique
        indices = [lm.index for lm in frame.landmarks]
        if len(set(indices)) != len(indices):
            errors.append("Duplicate landmark indices found")
        # Check confidence range
        for lm in frame.landmarks:
            if lm.confidence < 0 or lm.confidence > 1:
                errors.append(f"Landmark {lm.index} confidence out of range: {lm.confidence}")
        return errors

    def validate_all(self) -> LandmarkReport:
        """Validate all cached frames."""
        report = LandmarkReport(success=True)
        for frame in self._frames.values():
            errors = self.validate_frame(frame)
            if errors:
                report.errors.extend([f"Frame {frame.frame_number}: {e}" for e in errors])
                report.success = False
        # Check consistency
        if not self._frames and self._history.frames:
            report.warnings.append("History has frames but internal storage is empty (inconsistent)")
        # Statistics
        report.statistics = self.get_landmark_statistics()
        return report

    # ---- Utilities ----

    def clear(self) -> None:
        """Clear all cached data."""
        with self._lock:
            super().clear()
            self._frames.clear()
            self._frame_by_timestamp.clear()
            self._regions.clear()
            self._latest_head_pose = None
            self._history = TrackingHistory()
            self._confidence_cache.clear()
            self._mapping_cache.clear()

    def prune(self, max_frames: int) -> int:
        """Remove old frames to keep the cache size under max_frames."""
        with self._lock:
            if len(self._frames) <= max_frames:
                return 0
            # Sort by frame number and keep the most recent
            sorted_frames = sorted(self._frames.items(), key=lambda x: x[0])
            to_remove = len(self._frames) - max_frames
            removed = 0
            for frame_num, frame in sorted_frames[:to_remove]:
                self.invalidate_frame(frame_num)
                removed += 1
            return removed


# ---- Part 13: Utilities -----------------------------------------------

def convert_landmark_space(
    landmark: LandmarkPoint,
    from_space: LandmarkSpace,
    to_space: LandmarkSpace,
    image_width: int = 1,
    image_height: int = 1
) -> LandmarkPoint:
    """
    Convert a landmark from one coordinate space to another.
    """
    if from_space == to_space:
        return landmark

    x, y, z = landmark.x, landmark.y, landmark.z
    # Simplified conversions
    if from_space == LandmarkSpace.NORMALIZED and to_space == LandmarkSpace.IMAGE:
        x = x * image_width
        y = y * image_height
    elif from_space == LandmarkSpace.IMAGE and to_space == LandmarkSpace.NORMALIZED:
        x = x / image_width if image_width > 0 else 0
        y = y / image_height if image_height > 0 else 0
    # Add other conversions as needed
    return LandmarkPoint(
        index=landmark.index,
        x=x,
        y=y,
        z=z,
        confidence=landmark.confidence,
        visible=landmark.visible
    )


def interpolate_landmarks(
    frame_a: LandmarkFrame,
    frame_b: LandmarkFrame,
    t: float
) -> LandmarkFrame:
    """
    Interpolate between two landmark frames.
    """
    if t <= 0:
        return frame_a
    if t >= 1:
        return frame_b
    # Ensure same landmark count
    if len(frame_a.landmarks) != len(frame_b.landmarks):
        raise ValueError("Landmark frames must have same number of landmarks")

    # Interpolate each landmark
    interp_landmarks = []
    for lm_a, lm_b in zip(frame_a.landmarks, frame_b.landmarks):
        if lm_a.index != lm_b.index:
            # Fallback: use average?
            # For simplicity, we assume same index order
            pass
        x = lm_a.x + (lm_b.x - lm_a.x) * t
        y = lm_a.y + (lm_b.y - lm_a.y) * t
        z = lm_a.z + (lm_b.z - lm_a.z) * t
        conf = lm_a.confidence + (lm_b.confidence - lm_a.confidence) * t
        interp_landmarks.append(LandmarkPoint(
            index=lm_a.index,
            x=x,
            y=y,
            z=z,
            confidence=conf,
            visible=lm_a.visible and lm_b.visible
        ))

    # Interpolate head pose if both have it
    head_pose = None
    if frame_a.head_pose and frame_b.head_pose:
        # Interpolate Euler angles carefully
        pitch = frame_a.head_pose.pitch + (frame_b.head_pose.pitch - frame_a.head_pose.pitch) * t
        yaw = frame_a.head_pose.yaw + (frame_b.head_pose.yaw - frame_a.head_pose.yaw) * t
        roll = frame_a.head_pose.roll + (frame_b.head_pose.roll - frame_a.head_pose.roll) * t
        # Interpolate vectors
        fwd = (
            frame_a.head_pose.forward_vector[0] + (frame_b.head_pose.forward_vector[0] - frame_a.head_pose.forward_vector[0]) * t,
            frame_a.head_pose.forward_vector[1] + (frame_b.head_pose.forward_vector[1] - frame_a.head_pose.forward_vector[1]) * t,
            frame_a.head_pose.forward_vector[2] + (frame_b.head_pose.forward_vector[2] - frame_a.head_pose.forward_vector[2]) * t,
        )
        up = (
            frame_a.head_pose.up_vector[0] + (frame_b.head_pose.up_vector[0] - frame_a.head_pose.up_vector[0]) * t,
            frame_a.head_pose.up_vector[1] + (frame_b.head_pose.up_vector[1] - frame_a.head_pose.up_vector[1]) * t,
            frame_a.head_pose.up_vector[2] + (frame_b.head_pose.up_vector[2] - frame_a.head_pose.up_vector[2]) * t,
        )
        trans = (
            frame_a.head_pose.translation[0] + (frame_b.head_pose.translation[0] - frame_a.head_pose.translation[0]) * t,
            frame_a.head_pose.translation[1] + (frame_b.head_pose.translation[1] - frame_a.head_pose.translation[1]) * t,
            frame_a.head_pose.translation[2] + (frame_b.head_pose.translation[2] - frame_a.head_pose.translation[2]) * t,
        )
        head_pose = HeadPoseData(
            pitch=pitch,
            yaw=yaw,
            roll=roll,
            forward_vector=fwd,
            up_vector=up,
            translation=trans,
            confidence=(frame_a.head_pose.confidence + frame_b.head_pose.confidence) * 0.5
        )

    # Create interpolated frame
    interp_frame = LandmarkFrame(
        frame_number=frame_a.frame_number,  # Not meaningful; could use average
        timestamp=(frame_a.timestamp + frame_b.timestamp) * 0.5,
        source=frame_a.source,
        landmarks=interp_landmarks,
        confidence=(frame_a.confidence + frame_b.confidence) * 0.5,
        tracking_state=frame_a.tracking_state,  # Could infer
        head_pose=head_pose,
        bounding_box=frame_a.bounding_box,  # Could interpolate
        metadata=frame_a.metadata.copy()
    )
    return interp_frame


# ---- Part 14: Public API -----------------------------------------------

__all__ = [
    "LandmarkCache",
    "LandmarkFrame",
    "LandmarkPoint",
    "LandmarkStatistics",
    "LandmarkReport",
    "HeadPoseData",
    "FacialRegionData",
    "TrackingHistory",
    "LandmarkSource",
    "LandmarkSpace",
    "TrackingState",
    "FacialRegion",
    "convert_landmark_space",
    "interpolate_landmarks",
]