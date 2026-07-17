"""
maya_faceit.landmark.landmark_mapper

Maps detector landmarks into Maya Faceit's semantic
landmark representation.

Target
------
Maya 2026
Python 3.11
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .detector import (
    DetectionResult,
    LandmarkPoint,
)

from .landmark_database import (
    Landmark,
    landmark_database,
)

from .face_regions import (
    FaceRegion,
    face_regions,
)


# ------------------------------------------------------------
# Data
# ------------------------------------------------------------

@dataclass(slots=True)
class MappedLandmark:

    index: int

    name: str

    region: str

    side: str

    x: float

    y: float

    z: float

    confidence: float

    visibility: float


@dataclass(slots=True)
class MappingResult:

    success: bool = False

    detector: str = ""

    mapped: dict[int, MappedLandmark] = field(
        default_factory=dict
    )

    message: str = ""


# ------------------------------------------------------------
# Mapper
# ------------------------------------------------------------

class LandmarkMapper:
    """
    Converts detector landmarks into semantic
    Maya Faceit landmarks.
    """

    def __init__(self):

        self._last: MappingResult | None = None

    # -----------------------------------------------------

    def map(
        self,
        detection: DetectionResult,
    ) -> MappingResult:

        result = MappingResult()

        result.detector = detection.detector

        if not detection.success:

            result.message = detection.message

            return result

        for point in detection.landmarks:

            info = landmark_database.get(point.index)

            if info is None:
                continue

            mapped = MappedLandmark(

                index=info.index,

                name=info.name,

                region=info.region,

                side=info.side,

                x=point.x,

                y=point.y,

                z=point.z,

                confidence=point.confidence,

                visibility=point.visibility,

            )

            result.mapped[mapped.index] = mapped

        result.success = True

        self._last = result

        return result

    # -----------------------------------------------------

    def landmark(
        self,
        index: int,
    ) -> MappedLandmark | None:

        if self._last is None:
            return None

        return self._last.mapped.get(index)

    # -----------------------------------------------------

    def by_name(
        self,
        name: str,
    ) -> MappedLandmark | None:

        if self._last is None:
            return None

        info = landmark_database.get_by_name(name)

        if info is None:
            return None

        return self.landmark(info.index)

    # -----------------------------------------------------

    def by_region(
        self,
        region_name: str,
    ) -> list[MappedLandmark]:

        if self._last is None:
            return []

        return [

            lm

            for lm in self._last.mapped.values()

            if lm.region == region_name

        ]

    # -----------------------------------------------------

    def by_side(
        self,
        side: str,
    ) -> list[MappedLandmark]:

        if self._last is None:
            return []

        return [

            lm

            for lm in self._last.mapped.values()

            if lm.side == side

        ]

    # -----------------------------------------------------

    def mirror(
        self,
        index: int,
    ) -> MappedLandmark | None:

        if self._last is None:
            return None

        info = landmark_database.mirror(index)

        if info is None:
            return None

        return self.landmark(info.index)

    # -----------------------------------------------------

    def region_names(self) -> list[str]:

        return face_regions.names()

    # -----------------------------------------------------

    def statistics(self) -> dict:

        if self._last is None:

            return {}

        regions = {}

        for region in face_regions.names():

            regions[region] = len(

                self.by_region(region)

            )

        return {

            "mapped": len(self._last.mapped),

            "regions": regions,

        }

    # -----------------------------------------------------

    def serialize(self) -> dict:

        if self._last is None:

            return {}

        return {

            index: {

                "name": lm.name,

                "region": lm.region,

                "side": lm.side,

                "x": lm.x,

                "y": lm.y,

                "z": lm.z,

                "confidence": lm.confidence,

                "visibility": lm.visibility,

            }

            for index, lm in self._last.mapped.items()

        }

    # -----------------------------------------------------

    def clear(self):

        self._last = None


# ------------------------------------------------------------
# Singleton
# ------------------------------------------------------------

landmark_mapper = LandmarkMapper()