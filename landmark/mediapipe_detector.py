"""
maya_faceit.landmark.mediapipe_detector

MediaPipe Face Landmarker using the Tasks API.

Converts MediaPipe face landmarks, blendshapes, and transformation matrices
into Maya Faceit's standard DetectionResult format.

Target
------
Maya 2026
Python 3.11
MediaPipe Tasks API (0.10.35+)
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any, Optional

import cv2
import numpy as np

# MediaPipe Tasks API imports (from the bundled package)
try:
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import BaseOptions
    from mediapipe.tasks.python.vision import face_landmarker
    from mediapipe.tasks.python.vision.face_landmarker import (
        FaceLandmarker,
        FaceLandmarkerOptions,
        FaceLandmarkerResult,
    )
    HAS_MEDIAPIPE = True
except ImportError as e:
    HAS_MEDIAPIPE = False
    _MP_IMPORT_ERROR = str(e)

from .detector import (
    LandmarkDetector,
    LandmarkPoint,
    DetectionResult,
    DetectionSource,
    DetectorStatus,
)

# Default model file name (bundled in the package)
DEFAULT_MODEL_NAME = "face_landmarker.task"
BUNDLED_MODEL_PATH = Path(__file__).parent / "models" / DEFAULT_MODEL_NAME


class MediaPipeDetector(LandmarkDetector):
    """
    MediaPipe Face Landmarker using the Tasks API.

    Supports:
        - 478 face landmarks (normalized image coordinates)
        - ARKit-style blendshape coefficients (52 blendshapes)
        - Facial transformation matrix (4x4)
        - Image, video, and live stream modes (though currently only image mode is implemented)
    """

    NAME = "MediaPipe (Tasks API)"
    VERSION = mp.__version__ if HAS_MEDIAPIPE else "unknown"
    LANDMARK_COUNT = 478

    def __init__(
        self,
        *,
        model_path: Optional[str] = None,
        num_faces: int = 1,
        min_face_detection_confidence: float = 0.5,
        min_face_presence_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
        output_face_blendshapes: bool = True,
        output_facial_transformation_matrixes: bool = True,
    ):
        """
        Initialize the MediaPipe detector.

        Args:
            model_path: Path to the face_landmarker.task model file.
                       If None, uses the bundled model (if found).
            num_faces: Maximum number of faces to detect.
            min_face_detection_confidence: Confidence threshold for face detection.
            min_face_presence_confidence: Confidence threshold for face presence.
            min_tracking_confidence: Confidence threshold for tracking.
            output_face_blendshapes: Whether to output ARKit blendshape coefficients.
            output_facial_transformation_matrixes: Whether to output the 4x4 transformation matrix.
        """
        if not HAS_MEDIAPIPE:
            raise ImportError(
                "MediaPipe Tasks API not installed or not found.\n"
                f"Error: {_MP_IMPORT_ERROR}\n"
                "Please ensure mediapipe is installed in the Maya Python environment."
            )

        super().__init__()

        self.num_faces = num_faces
        self.min_face_detection_confidence = min_face_detection_confidence
        self.min_face_presence_confidence = min_face_presence_confidence
        self.min_tracking_confidence = min_tracking_confidence
        self.output_face_blendshapes = output_face_blendshapes
        self.output_facial_transformation_matrixes = output_facial_transformation_matrixes

        # Locate the model file
        self.model_path = self._find_model(model_path)
        self._landmarker: Optional[FaceLandmarker] = None

        # Status
        self.status = DetectorStatus.IDLE

    # ---------------------------------------------------------

    def _find_model(self, provided_path: Optional[str]) -> str:
        """
        Locate the face_landmarker.task model file.

        Search order:
            1. Provided path (if given and exists)
            2. Bundled model in the package's 'models' directory
            3. Current working directory
            4. User's home directory (~/face_landmarker.task)

        Raises:
            FileNotFoundError: If no valid model file is found.
        """
        search_paths = []

        # 1. Provided path
        if provided_path and os.path.exists(provided_path):
            return provided_path

        # 2. Bundled model
        if BUNDLED_MODEL_PATH.exists():
            return str(BUNDLED_MODEL_PATH)

        # 3. Current working directory
        cwd_model = Path.cwd() / DEFAULT_MODEL_NAME
        if cwd_model.exists():
            return str(cwd_model)

        # 4. Home directory
        home_model = Path.home() / DEFAULT_MODEL_NAME
        if home_model.exists():
            return str(home_model)

        # If not found, raise an error with instructions
        raise FileNotFoundError(
            f"Face landmarker model file '{DEFAULT_MODEL_NAME}' not found.\n"
            "Download it from:\n"
            "  https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task\n"
            "and place it in one of these locations:\n"
            f"  - {BUNDLED_MODEL_PATH}\n"
            "  - Current working directory\n"
            "  - ~/face_landmarker.task\n"
            "Or specify the path explicitly via `model_path`."
        )

    # ---------------------------------------------------------

    def initialize(self) -> bool:
        """Initialize the FaceLandmarker."""
        if self._landmarker is not None:
            self.status = DetectorStatus.READY
            return True

        try:
            # Create the FaceLandmarker options
            base_options = BaseOptions(model_asset_path=self.model_path)
            options = FaceLandmarkerOptions(
                base_options=base_options,
                num_faces=self.num_faces,
                min_face_detection_confidence=self.min_face_detection_confidence,
                min_face_presence_confidence=self.min_face_presence_confidence,
                min_tracking_confidence=self.min_tracking_confidence,
                output_face_blendshapes=self.output_face_blendshapes,
                output_facial_transformation_matrixes=self.output_facial_transformation_matrixes,
            )

            self._landmarker = FaceLandmarker.create_from_options(options)
            self.status = DetectorStatus.READY
            return True

        except Exception as e:
            self.status = DetectorStatus.ERROR
            self._last_error = str(e)
            return False

    # ---------------------------------------------------------

    def shutdown(self):
        """Close the FaceLandmarker and release resources."""
        if self._landmarker:
            self._landmarker.close()
            self._landmarker = None
        self.status = DetectorStatus.IDLE

    # ---------------------------------------------------------

    def supports(self, source: DetectionSource) -> bool:
        """Check if the detector supports the given source type."""
        return source in {
            DetectionSource.IMAGE,
            DetectionSource.VIDEO,
            DetectionSource.CAMERA,
        }

    # ---------------------------------------------------------

    def detect(self, source: Any) -> DetectionResult:
        """
        Detect face landmarks from an image source.

        Args:
            source: Path to image (str), numpy array (BGR), or cv2 image.

        Returns:
            DetectionResult containing landmarks, blendshapes, and matrix.
        """
        if self._landmarker is None:
            if not self.initialize():
                return DetectionResult(
                    success=False,
                    detector=self.NAME,
                    message=f"Failed to initialize MediaPipe: {self._last_error}",
                )

        # Load the image
        image = self._load_image(source)
        if image is None:
            return DetectionResult(
                success=False,
                detector=self.NAME,
                message="Unable to load image.",
            )

        # Convert BGR to RGB (MediaPipe expects RGB)
        if len(image.shape) == 3 and image.shape[2] == 3:
            rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            rgb = image  # assume already RGB or grayscale (not recommended)

        # Wrap in MediaPipe Image
        try:
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        except Exception as e:
            return DetectionResult(
                success=False,
                detector=self.NAME,
                message=f"Failed to create MediaPipe Image: {e}",
            )

        self.status = DetectorStatus.RUNNING
        start = time.perf_counter()

        try:
            result: FaceLandmarkerResult = self._landmarker.detect(mp_image)
        except Exception as e:
            self.status = DetectorStatus.READY
            return DetectionResult(
                success=False,
                detector=self.NAME,
                message=f"Detection error: {e}",
            )

        elapsed = time.perf_counter() - start
        self.status = DetectorStatus.READY

        # Check for detection
        if not result.face_landmarks:
            return DetectionResult(
                success=False,
                detector=self.NAME,
                elapsed_time=elapsed,
                message="No face detected.",
            )

        # Use the first face
        face_landmarks = result.face_landmarks[0]

        # Convert landmarks to LandmarkPoint list
        landmarks: list[LandmarkPoint] = []
        for index, lm in enumerate(face_landmarks):
            landmarks.append(
                LandmarkPoint(
                    index=index,
                    x=lm.x,
                    y=lm.y,
                    z=lm.z,
                    visibility=1.0,
                    confidence=1.0,
                )
            )

        # Extract blendshapes (ARKit coefficients)
        blendshapes = {}
        if result.face_blendshapes and len(result.face_blendshapes) > 0:
            for bs in result.face_blendshapes[0]:
                blendshapes[bs.category_name] = bs.score

        # Extract facial transformation matrix (4x4)
        matrix = None
        if result.facial_transformation_matrixes and len(result.facial_transformation_matrixes) > 0:
            matrix = result.facial_transformation_matrixes[0]

        # Build the result
        detection_result = DetectionResult(
            success=True,
            detector=self.NAME,
            source=DetectionSource.IMAGE,
            landmark_count=len(landmarks),
            landmarks=landmarks,
            blendshapes=blendshapes,
            matrix=matrix,
            elapsed_time=elapsed,
            message="Detection successful.",
        )

        return detection_result

    # ---------------------------------------------------------

    @staticmethod
    def _load_image(source: Any) -> Optional[np.ndarray]:
        """
        Load an image from various source types.

        Args:
            source: Path (str), numpy array, or cv2 image.

        Returns:
            BGR numpy array, or None if loading fails.
        """
        if isinstance(source, np.ndarray):
            return source

        if isinstance(source, str):
            path = Path(source)
            if not path.exists():
                return None
            img = cv2.imread(str(path))
            return img if img is not None else None

        return None


# ------------------------------------------------------------
# Singleton
# ------------------------------------------------------------

mediapipe_detector = MediaPipeDetector()