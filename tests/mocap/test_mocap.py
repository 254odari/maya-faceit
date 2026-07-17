# -*- coding: utf-8 -*-
"""
tests/mocap/test_mocap.py

Tests for motion capture processing.
"""

from maya_faceit.mayafaceit.lib._pytest import pytest
from maya_faceit.mocap import MocapRecorder, LiveLinkReceiver, MediaPipeTracker


class TestMocapRecorder:
    """Test recording functionality."""

    def test_record_start_stop(self):
        recorder = MocapRecorder()
        recorder.start_recording("test_session")
        assert recorder.is_recording
        recorder.stop_recording()
        assert not recorder.is_recording

    def test_save_recording(self, temp_dir):
        recorder = MocapRecorder()
        recorder.start_recording("test_session")
        # Add some frames
        recorder.save(str(temp_dir / "recording.json"))
        assert (temp_dir / "recording.json").exists()


class TestLiveLinkReceiver:
    """Test LiveLink receiver."""

    def test_connect(self):
        receiver = LiveLinkReceiver()
        # Mock connection
        success = receiver.connect("127.0.0.1", 8080)
        assert success


class TestMediaPipeTracker:
    """Test MediaPipe tracker."""

    def test_detect_blendshapes(self):
        tracker = MediaPipeTracker()
        # Mock image
        result = tracker.detect("path/to/image")
        assert result is not None