"""
ui/controllers/mocap_controller.py

Controller for motion capture live drive.
"""

from __future__ import annotations

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class MocapController:
    """Handles mocap device connection and streaming."""

    def __init__(self):
        self._device: Optional[str] = None
        self._is_connected = False
        self._is_recording = False

    def connect_device(self, device: str) -> bool:
        """Connect to a mocap device."""
        logger.info(f"Connecting to {device}")
        # TODO: Core device connection
        self._device = device
        self._is_connected = True
        return True

    def disconnect(self) -> None:
        """Disconnect current device."""
        self._is_connected = False
        self._device = None
        logger.info("Disconnected")

    def start_recording(self) -> bool:
        """Start recording mocap data."""
        if not self._is_connected:
            logger.error("No device connected")
            return False
        self._is_recording = True
        logger.info("Recording started")
        return True

    def stop_recording(self) -> bool:
        """Stop recording and save data."""
        self._is_recording = False
        logger.info("Recording stopped")
        return True

    def play_recording(self) -> None:
        """Play back recorded data."""
        logger.info("Playing recording...")

    def get_available_devices(self) -> list:
        """Return list of available mocap devices."""
        return ["LiveLink", "MediaPipe", "FaceCap", "OptiTrack"]

    def get_status(self) -> dict:
        return {
            "connected": self._is_connected,
            "device": self._device,
            "recording": self._is_recording,
        }