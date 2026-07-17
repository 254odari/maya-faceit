"""
maya_faceit.landmark.symmetry

Landmark symmetry utilities.

Provides mirroring, validation, averaging, and
symmetry analysis for mapped facial landmarks.

Target
------
Maya 2026
Python 3.11
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math

from .landmark_mapper import (
    MappingResult,
    MappedLandmark,
)

from .landmark_database import (
    landmark_database,
)


# ------------------------------------------------------------
# Enums
# ------------------------------------------------------------

class MirrorPlane(Enum):

    X = "X"

    Y = "Y"

    Z = "Z"


# ------------------------------------------------------------
# Data
# ------------------------------------------------------------

@dataclass(slots=True)
class SymmetryReport:

    valid: bool = False

    mirrored_pairs: int = 0

    center_points: int = 0

    missing_pairs: int = 0

    average_error: float = 0.0

    max_error: float = 0.0

    message: str = ""


# ------------------------------------------------------------
# Manager
# ------------------------------------------------------------

class LandmarkSymmetry:
    """
    Landmark symmetry manager.
    """

    def __init__(self):

        self._last: SymmetryReport | None = None

    # -----------------------------------------------------

    def mirror(
        self,
        mapping: MappingResult,
        plane: MirrorPlane = MirrorPlane.X,
    ) -> MappingResult:
        """
        Return a mirrored copy of the mapping.
        """

        result = MappingResult(
            success=mapping.success,
            detector=mapping.detector,
            message=mapping.message,
        )

        if not mapping.success:
            return result

        for index, landmark in mapping.mapped.items():

            mirror = landmark_database.mirror(index)

            if mirror is None:

                result.mapped[index] = landmark

                continue

            mirrored = mapping.mapped.get(mirror.index)

            if mirrored is None:

                result.mapped[index] = landmark

                continue

            x = mirrored.x
            y = mirrored.y
            z = mirrored.z

            if plane == MirrorPlane.X:
                x = 1.0 - x
            elif plane == MirrorPlane.Y:
                y = 1.0 - y
            elif plane == MirrorPlane.Z:
                z = -z

            result.mapped[index] = MappedLandmark(
                index=index,
                name=landmark.name,
                region=landmark.region,
                side=landmark.side,
                x=x,
                y=y,
                z=z,
                confidence=mirrored.confidence,
                visibility=mirrored.visibility,
            )

        return result

    # -----------------------------------------------------

    def validate(
        self,
        mapping: MappingResult,
    ) -> SymmetryReport:

        report = SymmetryReport()

        if not mapping.success:

            report.message = "Invalid mapping."

            self._last = report

            return report

        errors = []

        for index, landmark in mapping.mapped.items():

            mirror = landmark_database.mirror(index)

            if mirror is None:

                report.center_points += 1

                continue

            mirrored = mapping.mapped.get(mirror.index)

            if mirrored is None:

                report.missing_pairs += 1

                continue

            report.mirrored_pairs += 1

            error = abs(landmark.x - (1.0 - mirrored.x))

            errors.append(error)

        if errors:

            report.average_error = sum(errors) / len(errors)

            report.max_error = max(errors)

        report.valid = report.missing_pairs == 0

        report.message = "Validation complete."

        self._last = report

        return report

    # -----------------------------------------------------

    def average(
        self,
        mapping: MappingResult,
    ) -> MappingResult:
        """
        Average left/right landmark positions.
        """

        result = self.mirror(mapping)

        for index, landmark in result.mapped.items():

            mirror = landmark_database.mirror(index)

            if mirror is None:

                continue

            opposite = result.mapped.get(mirror.index)

            if opposite is None:

                continue

            avg_x = (landmark.x + (1.0 - opposite.x)) * 0.5
            avg_y = (landmark.y + opposite.y) * 0.5
            avg_z = (landmark.z + opposite.z) * 0.5

            landmark.x = avg_x
            landmark.y = avg_y
            landmark.z = avg_z

        return result

    # -----------------------------------------------------

    def symmetry_score(
        self,
        mapping: MappingResult,
    ) -> float:

        report = self.validate(mapping)

        if report.mirrored_pairs == 0:

            return 0.0

        score = 100.0 - report.average_error * 100.0

        return max(0.0, min(score, 100.0))

    # -----------------------------------------------------

    def serialize(self):

        if self._last is None:

            return {}

        return {
            "valid": self._last.valid,
            "mirrored_pairs": self._last.mirrored_pairs,
            "center_points": self._last.center_points,
            "missing_pairs": self._last.missing_pairs,
            "average_error": self._last.average_error,
            "max_error": self._last.max_error,
            "message": self._last.message,
        }

    # -----------------------------------------------------

    def clear(self):

        self._last = None


# ------------------------------------------------------------
# Singleton
# ------------------------------------------------------------

landmark_symmetry = LandmarkSymmetry()