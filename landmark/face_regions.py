"""
maya_faceit.landmark.face_regions

Semantic facial region manager.

Provides named facial regions that are shared across
landmark detection, rigging, auto fitting,
visualization, blendshape generation, ARKit mapping,
and motion capture.

Target
------
Maya 2026
Python 3.11
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .landmark_database import (
    Landmark,
    landmark_database,
)


# ------------------------------------------------------------
# Data Classes
# ------------------------------------------------------------

@dataclass(slots=True)
class FaceRegion:

    name: str

    landmark_names: list[str] = field(default_factory=list)

    side: str = "center"

    color: tuple[float, float, float] = (1.0, 1.0, 1.0)

    enabled: bool = True


# ------------------------------------------------------------
# Manager
# ------------------------------------------------------------

class FaceRegions:
    """
    Facial region manager.
    """

    def __init__(self):

        self._regions: dict[str, FaceRegion] = {}

        self._build_defaults()

    # -----------------------------------------------------

    def _build_defaults(self):

        self.register(
            FaceRegion(
                "Forehead",
                side="center",
                color=(0.95, 0.70, 0.20),
            )
        )

        self.register(
            FaceRegion(
                "Left Brow",
                side="left",
                color=(0.20, 0.70, 1.00),
            )
        )

        self.register(
            FaceRegion(
                "Right Brow",
                side="right",
                color=(0.20, 0.70, 1.00),
            )
        )

        self.register(
            FaceRegion(
                "Left Eye",
                side="left",
                color=(0.00, 1.00, 0.00),
            )
        )

        self.register(
            FaceRegion(
                "Right Eye",
                side="right",
                color=(0.00, 1.00, 0.00),
            )
        )

        self.register(
            FaceRegion(
                "Left Eyelid",
                side="left",
                color=(0.30, 0.90, 0.30),
            )
        )

        self.register(
            FaceRegion(
                "Right Eyelid",
                side="right",
                color=(0.30, 0.90, 0.30),
            )
        )

        self.register(
            FaceRegion(
                "Nose",
                side="center",
                color=(1.00, 0.80, 0.20),
            )
        )

        self.register(
            FaceRegion(
                "Left Cheek",
                side="left",
                color=(1.00, 0.50, 0.50),
            )
        )

        self.register(
            FaceRegion(
                "Right Cheek",
                side="right",
                color=(1.00, 0.50, 0.50),
            )
        )

        self.register(
            FaceRegion(
                "Upper Lip",
                side="center",
                color=(1.00, 0.20, 0.50),
            )
        )

        self.register(
            FaceRegion(
                "Lower Lip",
                side="center",
                color=(1.00, 0.20, 0.70),
            )
        )

        self.register(
            FaceRegion(
                "Mouth",
                side="center",
                color=(1.00, 0.00, 0.00),
            )
        )

        self.register(
            FaceRegion(
                "Jaw",
                side="center",
                color=(0.70, 0.70, 0.70),
            )
        )

        self.register(
            FaceRegion(
                "Chin",
                side="center",
                color=(0.60, 0.60, 0.60),
            )
        )

        self.register(
            FaceRegion(
                "Left Ear",
                side="left",
                color=(0.70, 0.40, 0.80),
            )
        )

        self.register(
            FaceRegion(
                "Right Ear",
                side="right",
                color=(0.70, 0.40, 0.80),
            )
        )

        self.register(
            FaceRegion(
                "Neck",
                side="center",
                color=(0.50, 0.50, 1.00),
            )
        )

        self.register(
            FaceRegion(
                "Tongue",
                side="center",
                color=(1.00, 0.20, 0.20),
            )
        )

    # -----------------------------------------------------

    def register(self, region: FaceRegion):

        self._regions[region.name] = region

    # -----------------------------------------------------

    def remove(self, name: str):

        self._regions.pop(name, None)

    # -----------------------------------------------------

    def get(self, name: str) -> FaceRegion | None:

        return self._regions.get(name)

    # -----------------------------------------------------

    def names(self) -> list[str]:

        return sorted(self._regions.keys())

    # -----------------------------------------------------

    def exists(self, name: str) -> bool:

        return name in self._regions

    # -----------------------------------------------------

    def landmarks(self, name: str) -> list[Landmark]:

        region = self.get(name)

        if region is None:

            return []

        result: list[Landmark] = []

        for landmark_name in region.landmark_names:

            landmark = landmark_database.get_by_name(
                landmark_name
            )

            if landmark:

                result.append(landmark)

        return result

    # -----------------------------------------------------

    def by_side(self, side: str) -> list[FaceRegion]:

        return [

            region

            for region in self._regions.values()

            if region.side == side

        ]

    # -----------------------------------------------------

    def serialize(self):

        return {

            name: {

                "side": region.side,

                "color": region.color,

                "enabled": region.enabled,

                "landmarks": region.landmark_names,

            }

            for name, region in self._regions.items()

        }

    # -----------------------------------------------------

    def clear(self):

        self._regions.clear()

        self._build_defaults()


# ------------------------------------------------------------
# Singleton
# ------------------------------------------------------------

face_regions = FaceRegions()