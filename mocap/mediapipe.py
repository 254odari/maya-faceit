"""
mocap/mediapipe.py

MediaPipe face landmark detection and tracking.

Integrates MediaPipe Tasks API for real-time face tracking and
blendshape extraction. Provides a high-level interface for using
MediaPipe in the Faceit mocap pipeline.

Features:
- Face landmark detection (478 points)
- Blendshape coefficient extraction (ARKit format)
- Real-time tracking from camera, video, or images
- Configurable detection parameters
- Integration with retargeting and filtering

Author: Maya FaceIT Team
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Any, List, Tuple, Union, Callable, Generator

# Try importing MediaPipe
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
    from mediapipe.tasks.python.vision.core import image as mp_image
    HAS_MEDIAPIPE = True
except ImportError:
    HAS_MEDIAPIPE = False

# For image processing
try:
    import cv2
    import numpy as np
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False

logger = logging.getLogger(__name__)

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"


# ---- Exceptions ----

class MediaPipeError(Exception):
    """Base exception for MediaPipe operations."""
    pass


# ---- Data Models ----

@dataclass
class MediaPipeSettings:
    """
    Settings for MediaPipe tracker.
    """
    model_path: Optional[str] = None          # Path to face_landmarker.task
    num_faces: int = 1                        # Maximum number of faces
    min_detection_confidence: float = 0.5     # Face detection confidence
    min_face_presence_confidence: float = 0.5 # Face presence confidence
    min_tracking_confidence: float = 0.5      # Tracking confidence
    output_blendshapes: bool = True           # Extract blendshapes
    output_transformation_matrix: bool = False # Extract transformation matrix
    output_face_geometry: bool = False        # Output face geometry (mesh)
    image_format: str = "RGB"                 # 'RGB' or 'BGR'
    source_type: str = "image"                # 'image', 'video', 'camera'


@dataclass
class MediaPipeResult:
    """
    MediaPipe detection result.
    """
    success: bool
    landmarks: List[List[Tuple[float, float, float]]] = field(default_factory=list)
    blendshapes: Dict[str, float] = field(default_factory=dict)
    transformation_matrix: Optional[List[List[float]]] = None
    face_geometry: Optional[Any] = None
    message: str = ""
    elapsed_time: float = 0.0
    face_count: int = 0


# ---- MediaPipe Tracker ----

class MediaPipeTracker:
    """
    MediaPipe face landmark tracker.

    Uses the MediaPipe Tasks API for face landmark detection and
    blendshape extraction. Provides real-time tracking from various sources.

    Usage:
        tracker = MediaPipeTracker()
        tracker.initialize()
        result = tracker.process_image(image_array)
        if result.success:
            print(result.blendshapes)
        tracker.close()
    """

    def __init__(self, settings: Optional[MediaPipeSettings] = None):
        """
        Initialize the MediaPipe tracker.

        Args:
            settings: Optional settings.
        """
        if not HAS_MEDIAPIPE:
            raise MediaPipeError(
                "MediaPipe is not installed. Please install:\n"
                "pip install mediapipe"
            )

        self.settings = settings or MediaPipeSettings()
        self._landmarker: Optional[FaceLandmarker] = None
        self._initialized = False
        self._last_result: Optional[MediaPipeResult] = None
        self._frame_count = 0

        logger.debug("MediaPipeTracker initialized")

    # ---- Lifecycle ----

    def initialize(self, model_path: Optional[str] = None) -> bool:
        """
        Initialize the MediaPipe landmarker.

        Args:
            model_path: Optional path to the model file.

        Returns:
            True if initialization succeeded.
        """
        if self._initialized:
            return True

        try:
            # Use provided path or settings
            if model_path is None:
                model_path = self.settings.model_path

            # If no model path, try to find default
            if not model_path:
                model_path = self._find_default_model()

            if not model_path:
                raise MediaPipeError(
                    "Face landmarker model not found. Please download from:\n"
                    "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task\n"
                    "and specify the path in settings.model_path or pass to initialize()."
                )

            # Create options
            base_options = BaseOptions(model_asset_path=model_path)

            options = FaceLandmarkerOptions(
                base_options=base_options,
                num_faces=self.settings.num_faces,
                min_face_detection_confidence=self.settings.min_detection_confidence,
                min_face_presence_confidence=self.settings.min_face_presence_confidence,
                min_tracking_confidence=self.settings.min_tracking_confidence,
                output_face_blendshapes=self.settings.output_blendshapes,
                output_facial_transformation_matrixes=self.settings.output_transformation_matrix,
            )

            self._landmarker = FaceLandmarker.create_from_options(options)
            self._initialized = True
            logger.info("MediaPipe tracker initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize MediaPipe: {e}")
            return False

    def _find_default_model(self) -> Optional[str]:
        """
        Try to find the default model in common locations.

        Returns:
            Path to model or None.
        """
        import os
        from pathlib import Path

        possible_paths = [
            # Bundled with the package
            Path(__file__).parent / "models" / "face_landmarker.task",
            # Current working directory
            Path(os.getcwd()) / "face_landmarker.task",
            # User home directory
            Path.home() / "face_landmarker.task",
            # Maya preferences
            Path(os.environ.get("MAYA_APP_DIR", "")) / "maya_faceit" / "models" / "face_landmarker.task",
        ]

        for p in possible_paths:
            if p.exists():
                return str(p)

        return None

    def close(self) -> None:
        """Close the landmarker and release resources."""
        if self._landmarker:
            self._landmarker.close()
            self._landmarker = None
            self._initialized = False
            logger.debug("MediaPipe tracker closed")

    def is_initialized(self) -> bool:
        """Check if the tracker is initialized."""
        return self._initialized

    # ---- Processing Methods ----

    def process_image(self, image_array: Any) -> MediaPipeResult:
        """
        Process an image and return landmarks and blendshapes.

        Args:
            image_array: NumPy array (BGR or RGB).

        Returns:
            MediaPipeResult.
        """
        if not self._initialized:
            if not self.initialize():
                return MediaPipeResult(
                    success=False,
                    message="MediaPipe failed to initialize."
                )

        if not HAS_OPENCV:
            return MediaPipeResult(
                success=False,
                message="OpenCV is required for image processing."
            )

        try:
            # Ensure image is in the correct format (RGB for MediaPipe)
            if len(image_array.shape) == 3 and image_array.shape[2] == 3:
                if self.settings.image_format.upper() == "BGR":
                    rgb = cv2.cvtColor(image_array, cv2.COLOR_BGR2RGB)
                else:
                    rgb = image_array
            else:
                rgb = image_array

            # Create MediaPipe Image
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

            start = time.perf_counter()
            result: FaceLandmarkerResult = self._landmarker.detect(mp_img)
            elapsed = time.perf_counter() - start

            if not result.face_landmarks:
                return MediaPipeResult(
                    success=False,
                    message="No face detected.",
                    elapsed_time=elapsed,
                )

            # Extract landmarks
            landmarks = []
            for face in result.face_landmarks:
                face_lms = [(lm.x, lm.y, lm.z) for lm in face]
                landmarks.append(face_lms)

            # Extract blendshapes
            blendshapes = {}
            if self.settings.output_blendshapes and result.face_blendshapes:
                for bs in result.face_blendshapes[0]:
                    blendshapes[bs.category_name] = bs.score

            # Extract transformation matrix
            matrix = None
            if self.settings.output_transformation_matrix and result.facial_transformation_matrixes:
                matrix = result.facial_transformation_matrixes[0]

            # Extract face geometry if requested
            geometry = None
            if self.settings.output_face_geometry:
                # Placeholder - MediaPipe doesn't directly output geometry
                # Could convert landmarks to a mesh
                geometry = landmarks  # Use landmarks as geometry

            self._frame_count += 1
            result_obj = MediaPipeResult(
                success=True,
                landmarks=landmarks,
                blendshapes=blendshapes,
                transformation_matrix=matrix,
                face_geometry=geometry,
                message="Detection successful.",
                elapsed_time=elapsed,
                face_count=len(result.face_landmarks),
            )

            self._last_result = result_obj
            return result_obj

        except Exception as e:
            logger.error(f"MediaPipe process error: {e}")
            return MediaPipeResult(
                success=False,
                message=f"Processing error: {e}",
            )

    def process_video_frame(self, frame: Any) -> MediaPipeResult:
        """
        Process a video frame (wrapper for process_image).

        Args:
            frame: Video frame (NumPy array).

        Returns:
            MediaPipeResult.
        """
        return self.process_image(frame)

    def process_from_file(self, filepath: str) -> MediaPipeResult:
        """
        Process an image from a file.

        Args:
            filepath: Path to image file.

        Returns:
            MediaPipeResult.
        """
        if not HAS_OPENCV:
            return MediaPipeResult(
                success=False,
                message="OpenCV is required for file processing."
            )

        try:
            image = cv2.imread(filepath)
            if image is None:
                return MediaPipeResult(
                    success=False,
                    message=f"Failed to load image: {filepath}"
                )
            return self.process_image(image)
        except Exception as e:
            return MediaPipeResult(
                success=False,
                message=f"Error processing file: {e}"
            )

    def process_from_camera(self, camera_id: int = 0) -> Generator[MediaPipeResult, None, None]:
        """
        Process a live camera feed.

        Args:
            camera_id: Camera device ID.

        Yields:
            MediaPipeResult for each frame.
        """
        if not HAS_OPENCV:
            raise MediaPipeError("OpenCV is required for camera processing.")

        cap = cv2.VideoCapture(camera_id)
        if not cap.isOpened():
            raise MediaPipeError(f"Failed to open camera {camera_id}")

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                result = self.process_image(frame)
                yield result
                # Small delay to prevent CPU overload
                time.sleep(0.01)
        finally:
            cap.release()

    # ---- Accessor Methods ----

    def get_last_result(self) -> Optional[MediaPipeResult]:
        """Return the last detection result."""
        return self._last_result

    def get_blendshapes(self) -> Dict[str, float]:
        """Return the last blendshape coefficients."""
        if self._last_result and self._last_result.success:
            return self._last_result.blendshapes
        return {}

    def get_landmarks(self) -> List[List[Tuple[float, float, float]]]:
        """Return the last detected landmarks."""
        if self._last_result and self._last_result.success:
            return self._last_result.landmarks
        return []

    def get_face_count(self) -> int:
        """Return the number of faces detected in the last frame."""
        if self._last_result and self._last_result.success:
            return self._last_result.face_count
        return 0

    def get_elapsed_time(self) -> float:
        """Return the elapsed time of the last detection."""
        if self._last_result:
            return self._last_result.elapsed_time
        return 0.0

    # ---- Statistics ----

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get tracker statistics.

        Returns:
            Dict with frame count, detection stats, etc.
        """
        return {
            "initialized": self._initialized,
            "frame_count": self._frame_count,
            "last_detection_time": self._last_result.elapsed_time if self._last_result else None,
            "last_face_count": self.get_face_count(),
            "last_success": self._last_result.success if self._last_result else False,
        }

    # ---- Context Manager ----

    def __enter__(self):
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        self.close()


# ---- Convenience Functions ----

def blendshapes_to_arkit(blendshapes: Dict[str, float]) -> Dict[str, float]:
    """
    Convert MediaPipe blendshapes to ARKit format.

    MediaPipe already outputs ARKit-style blendshapes, but this ensures
    compatibility.

    Args:
        blendshapes: MediaPipe blendshape dictionary.

    Returns:
        ARKit blendshape dictionary.
    """
    # MediaPipe uses the same names as ARKit
    return blendshapes.copy()


def blendshapes_to_faceit(blendshapes: Dict[str, float]) -> Dict[str, float]:
    """
    Convert MediaPipe blendshapes to Faceit format.

    Faceit uses the same ARKit blendshape names, so this is a direct mapping.

    Args:
        blendshapes: MediaPipe blendshape dictionary.

        Returns:
            Faceit blendshape dictionary.
    """
    return blendshapes.copy()


# ---- Public API ----

__all__ = [
    "MediaPipeTracker",
    "MediaPipeSettings",
    "MediaPipeResult",
    "MediaPipeError",
    "blendshapes_to_arkit",
    "blendshapes_to_faceit",
]