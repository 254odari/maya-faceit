"""
maya_faceit.landmark.detector

Abstract facial landmark detector interface.

Defines the common API implemented by all landmark
detectors used by Maya Faceit.

Target
------
Maya 2026
Python 3.11
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ------------------------------------------------------------
# Enums
# ------------------------------------------------------------

class DetectionSource(Enum):
    """Supported landmark input sources."""

    IMAGE = "image"
    CAMERA = "camera"
    VIDEO = "video"
    MESH = "mesh"


class DetectorStatus(Enum):
    """Detector runtime state."""

    IDLE = "idle"
    READY = "ready"
    RUNNING = "running"
    FAILED = "failed"


# ------------------------------------------------------------
# Data Classes
# ------------------------------------------------------------

@dataclass(slots=True, frozen=True)
class LandmarkPoint:
    """Single detected landmark."""

    index: int

    x: float

    y: float

    z: float

    visibility: float = 1.0

    confidence: float = 1.0


@dataclass(slots=True)
class DetectionResult:
    """Result returned by every detector."""

    success: bool = False

    detector: str = ""

    source: DetectionSource = DetectionSource.IMAGE

    landmark_count: int = 0

    landmarks: list[LandmarkPoint] = field(default_factory=list)

    elapsed_time: float = 0.0

    message: str = ""


# ------------------------------------------------------------
# Abstract Detector
# ------------------------------------------------------------

class LandmarkDetector(ABC):
    """
    Base class for all landmark detectors.
    """

    NAME = "Base Detector"

    VERSION = "1.0"

    LANDMARK_COUNT = 0

    def __init__(self):

        self.status = DetectorStatus.IDLE

    # -----------------------------------------------------

    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize detector resources.
        """
        raise NotImplementedError

    # -----------------------------------------------------

    @abstractmethod
    def shutdown(self):
        """
        Release detector resources.
        """
        raise NotImplementedError

    # -----------------------------------------------------

    @abstractmethod
    def detect(
        self,
        source: Any,
    ) -> DetectionResult:
        """
        Detect landmarks from the supplied source.
        """
        raise NotImplementedError

    # -----------------------------------------------------

    @abstractmethod
    def supports(
        self,
        source: DetectionSource,
    ) -> bool:
        """
        Returns True if the detector supports the
        specified source type.
        """
        raise NotImplementedError

    # -----------------------------------------------------

    @property
    def ready(self) -> bool:

        return self.status == DetectorStatus.READY

    # -----------------------------------------------------

    @property
    def running(self) -> bool:

        return self.status == DetectorStatus.RUNNING


# ------------------------------------------------------------
# Detector Manager
# ------------------------------------------------------------

class DetectorManager:
    """
    Registry for landmark detectors.
    """

    def __init__(self):

        self._detectors: dict[str, LandmarkDetector] = {}

        self._active: str | None = None

    # -----------------------------------------------------

    def register(
        self,
        detector: LandmarkDetector,
    ):

        self._detectors[detector.NAME] = detector

        if self._active is None:

            self._active = detector.NAME

    # -----------------------------------------------------

    def unregister(
        self,
        name: str,
    ):

        self._detectors.pop(name, None)

        if self._active == name:

            self._active = None

    # -----------------------------------------------------

    def activate(
        self,
        name: str,
    ) -> bool:

        if name not in self._detectors:

            return False

        self._active = name

        return True

    # -----------------------------------------------------

    @property
    def active(self) -> LandmarkDetector | None:

        if self._active is None:

            return None

        return self._detectors[self._active]

    # -----------------------------------------------------

    def detect(
        self,
        source: Any,
    ) -> DetectionResult:

        detector = self.active

        if detector is None:

            return DetectionResult(
                success=False,
                message="No active landmark detector."
            )

        return detector.detect(source)

    # -----------------------------------------------------

    def available(self) -> list[str]:

        return sorted(self._detectors.keys())

    # -----------------------------------------------------

    def clear(self):

        self._detectors.clear()

        self._active = None


# ------------------------------------------------------------
# Singleton
# ------------------------------------------------------------

landmark_detector = DetectorManager()