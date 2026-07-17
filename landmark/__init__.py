"""
maya_faceit.landmark

Landmark detection and processing package.

This package provides the complete facial landmark
pipeline used by Maya Faceit, including:

- Face detection
- MediaPipe integration
- Landmark mapping
- Facial region definitions
- Mesh alignment
- Auto fitting
- Symmetry tools
- Viewport visualization

Target
------
Maya 2026
Python 3.11
"""

from __future__ import annotations

# ------------------------------------------------------------
# Version
# ------------------------------------------------------------

__version__ = "1.0.0"

# ------------------------------------------------------------
# Public Modules
# ------------------------------------------------------------

from .detector import (
    LandmarkDetector,
    landmark_detector,
)

from .mediapipe_detector import (
    MediaPipeDetector,
    mediapipe_detector,
)

from .landmark_mapper import (
    LandmarkMapper,
    landmark_mapper,
)

from .landmark_database import (
    LandmarkDatabase,
    landmark_database,
)

from .face_regions import (
    FaceRegions,
    face_regions,
)

from .alignment import (
    LandmarkAlignment,
    landmark_alignment,
)

from .auto_fit import (
    AutoFit,
    auto_fit,
)

from .symmetry import (
    LandmarkSymmetry,
    landmark_symmetry,
)

from .visualization import (
    LandmarkVisualization,
    landmark_visualization,
)

# ------------------------------------------------------------
# Package API
# ------------------------------------------------------------

__all__ = [

    # Detector
    "LandmarkDetector",
    "landmark_detector",

    # MediaPipe
    "MediaPipeDetector",
    "mediapipe_detector",

    # Mapping
    "LandmarkMapper",
    "landmark_mapper",

    # Database
    "LandmarkDatabase",
    "landmark_database",

    # Regions
    "FaceRegions",
    "face_regions",

    # Alignment
    "LandmarkAlignment",
    "landmark_alignment",

    # Auto Fit
    "AutoFit",
    "auto_fit",

    # Symmetry
    "LandmarkSymmetry",
    "landmark_symmetry",

    # Visualization
    "LandmarkVisualization",
    "landmark_visualization",
]