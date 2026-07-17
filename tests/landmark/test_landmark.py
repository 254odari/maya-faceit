# -*- coding: utf-8 -*-
"""
tests/landmark/test_landmark.py

Tests for landmark detection and mapping.
"""

from maya_faceit.mayafaceit.lib._pytest import pytest
from maya_faceit.landmark import landmark_detector, landmark_mapper


class TestLandmarkDetector:
    """Test landmark detection."""

    def test_detect_face(self):
        # Need sample image or mesh
        landmarks = landmark_detector.detect_face("path/to/image")
        assert landmarks is not None

    def test_mediapipe_detection(self):
        # Use mock MediaPipe
        result = landmark_detector.detect_mediapipe("path/to/image")
        assert result is not None


class TestLandmarkMapper:
    """Test landmark mapping to mesh."""

    def test_map_landmarks_to_mesh(self, sample_mesh_data):
        # Mock landmarks
        landmarks = {"left_eye": (0.1, 0.2, 0)}
        mapped = landmark_mapper.map_to_mesh(landmarks, sample_mesh_data)
        assert "left_eye" in mapped