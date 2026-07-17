"""
core/pipeline/landmark_solver.py

Landmark solving engine for Maya Faceit.

Converts detected landmarks into normalized rig positions.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

from ..logging.logger import log
from ...exceptions import ValidationError


# ---------------------------------------------------------
# Data Classes
# ---------------------------------------------------------

@dataclass(slots=True)
class Landmark:
    """A single detected landmark."""
    id: int
    name: str
    position: Tuple[float, float, float]


@dataclass(slots=True)
class SolvedLandmarks:
    """Container for solved landmark data."""
    landmarks: Dict[int, Landmark]
    center: Tuple[float, float, float]
    width: float
    height: float
    depth: float
    normalized: bool = False


# ---------------------------------------------------------
# Solver
# ---------------------------------------------------------

class LandmarkSolver:
    """
    Solves landmark positions into a normalized facial coordinate system.
    """

    def __init__(self):
        self.landmarks: Dict[int, Landmark] = {}

    def solve(self, landmarks: List[Landmark]) -> SolvedLandmarks:
        """
        Process raw landmarks into a solved structure.

        Args:
            landmarks: List of detected landmarks.

        Returns:
            SolvedLandmarks with center, dimensions, and normalized data.
        """
        if not landmarks:
            raise ValidationError("No landmarks supplied.")

        self.landmarks = {lm.id: lm for lm in landmarks}

        center = self.compute_center()
        width, height, depth = self.compute_dimensions()

        log.info(f"Solved {len(landmarks)} landmarks.")
        log.debug(f"Center: {center}, Dimensions: {width}x{height}x{depth}")

        return SolvedLandmarks(
            landmarks=self.landmarks,
            center=center,
            width=width,
            height=height,
            depth=depth,
            normalized=False,
        )

    def compute_center(self) -> Tuple[float, float, float]:
        """Compute the centroid of all landmarks."""
        xs, ys, zs = [], [], []
        for lm in self.landmarks.values():
            x, y, z = lm.position
            xs.append(x)
            ys.append(y)
            zs.append(z)
        n = len(xs)
        return (sum(xs) / n, sum(ys) / n, sum(zs) / n)

    def compute_dimensions(self) -> Tuple[float, float, float]:
        """Compute width, height, depth from landmarks."""
        xs = [lm.position[0] for lm in self.landmarks.values()]
        ys = [lm.position[1] for lm in self.landmarks.values()]
        zs = [lm.position[2] for lm in self.landmarks.values()]
        width = max(xs) - min(xs)
        height = max(ys) - min(ys)
        depth = max(zs) - min(zs)
        return width, height, depth

    def normalize(self) -> None:
        """Normalize landmarks to center at origin."""
        center = self.compute_center()
        normalized = {}
        for idx, lm in self.landmarks.items():
            x = lm.position[0] - center[0]
            y = lm.position[1] - center[1]
            z = lm.position[2] - center[2]
            normalized[idx] = Landmark(
                id=lm.id,
                name=lm.name,
                position=(x, y, z),
            )
        self.landmarks = normalized
        log.debug("Landmarks normalized to center.")

    def mirror(self) -> Dict[int, Landmark]:
        """Mirror landmarks across the X-axis."""
        mirrored = {}
        for idx, lm in self.landmarks.items():
            x, y, z = lm.position
            mirrored[idx] = Landmark(
                id=lm.id,
                name=lm.name,
                position=(-x, y, z),
            )
        return mirrored

    def distance(self, a: int, b: int) -> float:
        """Compute distance between two landmarks."""
        p1 = self.landmarks[a].position
        p2 = self.landmarks[b].position
        return math.sqrt(
            (p1[0]-p2[0])**2 +
            (p1[1]-p2[1])**2 +
            (p1[2]-p2[2])**2
        )

    def region(self, ids: List[int]) -> List[Landmark]:
        """Get landmarks for a specific region by ID list."""
        return [
            self.landmarks[i]
            for i in ids
            if i in self.landmarks
        ]


# ---------------------------------------------------------
# Singleton
# ---------------------------------------------------------

landmark_solver = LandmarkSolver()