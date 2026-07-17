"""
mocap/livelink.py

Live Link Face receiver for Apple ARKit.

Receives live facial animation data from Apple's Live Link Face app
via UDP, processes the ARKit coefficients, and applies them to the rig.

Features:
- UDP server receiving Live Link data
- JSON and binary format support
- Automatic parsing of blendshape coefficients
- Callback system for frame processing
- Auto-apply to rig with configurable callback
- Thread-safe operation

Live Link Face app sends data in either JSON or binary format.
This receiver handles both and extracts the blendshape coefficients.

Author: Maya FaceIT Team
"""

from __future__ import annotations

import json
import logging
import socket
import struct
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Callable, List, Any, Union

logger = logging.getLogger(__name__)

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"


# ---- Exceptions ----

class LiveLinkError(Exception):
    """Base exception for Live Link operations."""
    pass


# ---- Data Models ----

@dataclass
class LiveLinkSettings:
    """
    Settings for Live Link receiver.
    """
    port: int = 11111                    # UDP port (default: 11111)
    buffer_size: int = 65536             # UDP receive buffer size
    reconnect_delay: float = 1.0         # Delay between reconnect attempts (seconds)
    timeout: float = 5.0                 # Socket timeout (seconds)
    auto_apply: bool = True              # Automatically apply to rig
    apply_callback: Optional[Callable[[Dict[str, float]], None]] = None
    parse_binary: bool = True            # Attempt to parse binary format
    parse_json: bool = True              # Attempt to parse JSON format
    verbose_logging: bool = False        # Log all received frames


@dataclass
class LiveLinkData:
    """
    Live Link frame data.
    """
    timestamp: float                     # Receive timestamp
    frame_number: int                    # Frame number from Live Link
    blendshapes: Dict[str, float]        # ARKit blendshape coefficients
    head_rotation: Optional[List[float]] = None  # Head rotation (quaternion)
    head_translation: Optional[List[float]] = None  # Head translation (position)
    source: str = "LiveLink"             # Source identifier
    raw_data: Optional[Any] = None       # Raw data for debugging


# ---- Live Link Receiver ----

class LiveLinkReceiver:
    """
    Receive and process Live Link Face data.

    Listens for UDP packets from the Live Link Face app on iOS.
    Supports both JSON and binary data formats.

    Usage:
        receiver = LiveLinkReceiver()
        receiver.add_callback(my_callback)
        receiver.start()
        # ... receive data ...
        receiver.stop()
    """

    def __init__(self, settings: Optional[LiveLinkSettings] = None):
        """
        Initialize the Live Link receiver.

        Args:
            settings: Optional settings.
        """
        self.settings = settings or LiveLinkSettings()
        self._socket: Optional[socket.socket] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_data: Optional[LiveLinkData] = None
        self._lock = threading.RLock()
        self._callbacks: List[Callable[[LiveLinkData], None]] = []
        self._frame_count = 0

        logger.info(f"LiveLinkReceiver initialized on port {self.settings.port}")

    # ---- Lifecycle ----

    def start(self) -> None:
        """
        Start the Live Link receiver.

        Creates a UDP socket and starts the receive thread.
        """
        if self._running:
            logger.warning("Live Link receiver already running")
            return

        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._socket.settimeout(self.settings.timeout)
            self._socket.bind(('0.0.0.0', self.settings.port))

            self._running = True
            self._thread = threading.Thread(target=self._receive_loop, daemon=True)
            self._thread.start()

            logger.info(f"Live Link receiver started on port {self.settings.port}")

        except socket.error as e:
            raise LiveLinkError(f"Failed to start Live Link receiver: {e}")

    def stop(self) -> None:
        """
        Stop the Live Link receiver.

        Closes the socket and stops the receive thread.
        """
        if not self._running:
            return

        self._running = False

        if self._socket:
            try:
                self._socket.close()
            except:
                pass
            self._socket = None

        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

        logger.info("Live Link receiver stopped")

    def is_running(self) -> bool:
        """Check if the receiver is running."""
        return self._running

    # ---- Callback Management ----

    def add_callback(self, callback: Callable[[LiveLinkData], None]) -> None:
        """
        Add a callback for received data.

        Args:
            callback: Function called with LiveLinkData when a frame is received.
        """
        with self._lock:
            if callback not in self._callbacks:
                self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[LiveLinkData], None]) -> None:
        """
        Remove a callback.

        Args:
            callback: Callback to remove.
        """
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)

    def clear_callbacks(self) -> None:
        """Remove all callbacks."""
        with self._lock:
            self._callbacks.clear()

    def get_last_data(self) -> Optional[LiveLinkData]:
        """
        Get the last received data frame.

        Returns:
            LiveLinkData or None if no data received.
        """
        with self._lock:
            return self._last_data

    # ---- Main Receive Loop ----

    def _receive_loop(self) -> None:
        """Main receive loop running in a separate thread."""
        while self._running:
            try:
                data, addr = self._socket.recvfrom(self.settings.buffer_size)
                self._process_data(data, addr)
            except socket.timeout:
                continue
            except ConnectionError:
                logger.warning("Live Link connection lost, waiting...")
                time.sleep(self.settings.reconnect_delay)
            except Exception as e:
                logger.error(f"Live Link receive error: {e}")
                time.sleep(self.settings.reconnect_delay)

    # ---- Data Processing ----

    def _process_data(self, data: bytes, addr: tuple) -> None:
        """
        Process received data packet.

        Args:
            data: Raw UDP data.
            addr: Sender address.
        """
        try:
            # Try to parse JSON first
            if self.settings.parse_json:
                json_data = self._parse_json(data)
                if json_data:
                    self._handle_parsed_data(json_data, data, addr)
                    return

            # Try to parse binary if JSON failed
            if self.settings.parse_binary:
                binary_data = self._parse_binary(data)
                if binary_data:
                    self._handle_parsed_data(binary_data, data, addr)
                    return

            # If both fail, log warning
            if self.settings.verbose_logging:
                logger.debug(f"Unrecognized Live Link data format: {len(data)} bytes")

        except Exception as e:
            logger.error(f"Error processing Live Link data: {e}")

    def _parse_json(self, data: bytes) -> Optional[Dict[str, Any]]:
        """
        Parse JSON data from Live Link.

        Live Link sends JSON with a "blendshapes" or "BlendShapes" field.
        """
        try:
            text = data.decode('utf-8')
            json_data = json.loads(text)
            return json_data
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

    def _parse_binary(self, data: bytes) -> Optional[Dict[str, Any]]:
        """
        Parse binary format from Live Link.

        Binary format is more compact and used by default in Live Link Face.
        Format: [version (1 byte)] [frame number (4 bytes)] [blendshape count (2 bytes)] [blendshape data...]
        """
        try:
            if len(data) < 7:
                return None

            # Check version byte (0 or 1)
            version = data[0]
            if version > 1:
                return None

            # Parse frame number
            frame_num = struct.unpack('<I', data[1:5])[0]

            # Parse blendshape count
            count = struct.unpack('<H', data[5:7])[0]

            if len(data) < 7 + count * 8:
                return None

            # Parse blendshapes
            blendshapes = {}
            offset = 7
            for i in range(count):
                # Each blend: [id (2 bytes)] [value (4 bytes float)]
                if offset + 6 > len(data):
                    break
                shape_id = struct.unpack('<H', data[offset:offset+2])[0]
                value = struct.unpack('<f', data[offset+2:offset+6])[0]
                # Map ID to name using ARKit ID mapping
                name = self._get_blendshape_name(shape_id)
                if name:
                    blendshapes[name] = value
                offset += 6

            return {
                "frame": frame_num,
                "blendshapes": blendshapes,
                "version": version,
            }

        except Exception as e:
            logger.debug(f"Binary parse error: {e}")
            return None

    def _get_blendshape_name(self, shape_id: int) -> str:
        """
        Map ARKit blendshape ID to name.

        ARKit has a fixed mapping of IDs to blendshape names.
        """
        # ARKit blendshape ID to name mapping (simplified)
        # Full mapping would be all 52 shapes
        arkit_id_map = {
            0: "browDownLeft",
            1: "browDownRight",
            2: "browInnerUp",
            3: "browOuterUpLeft",
            4: "browOuterUpRight",
            5: "cheekPuff",
            6: "cheekSquintLeft",
            7: "cheekSquintRight",
            8: "eyeBlinkLeft",
            9: "eyeBlinkRight",
            10: "eyeLookDownLeft",
            11: "eyeLookDownRight",
            12: "eyeLookInLeft",
            13: "eyeLookInRight",
            14: "eyeLookOutLeft",
            15: "eyeLookOutRight",
            16: "eyeLookUpLeft",
            17: "eyeLookUpRight",
            18: "eyeSquintLeft",
            19: "eyeSquintRight",
            20: "eyeWideLeft",
            21: "eyeWideRight",
            22: "jawForward",
            23: "jawLeft",
            24: "jawOpen",
            25: "jawRight",
            26: "mouthClose",
            27: "mouthDimpleLeft",
            28: "mouthDimpleRight",
            29: "mouthFrownLeft",
            30: "mouthFrownRight",
            31: "mouthFunnel",
            32: "mouthLeft",
            33: "mouthLowerDownLeft",
            34: "mouthLowerDownRight",
            35: "mouthPressLeft",
            36: "mouthPressRight",
            37: "mouthPucker",
            38: "mouthRight",
            39: "mouthRollLower",
            40: "mouthRollUpper",
            41: "mouthShrugLower",
            42: "mouthShrugUpper",
            43: "mouthSmileLeft",
            44: "mouthSmileRight",
            45: "mouthStretchLeft",
            46: "mouthStretchRight",
            47: "mouthUpperUpLeft",
            48: "mouthUpperUpRight",
            49: "noseSneerLeft",
            50: "noseSneerRight",
            51: "tongueOut",
        }
        return arkit_id_map.get(shape_id, f"Unknown_{shape_id}")

    def _handle_parsed_data(
        self,
        parsed: Dict[str, Any],
        raw_data: bytes,
        addr: tuple
    ) -> None:
        """
        Handle parsed Live Link data.

        Args:
            parsed: Parsed dictionary from JSON or binary.
            raw_data: Raw bytes for debugging.
            addr: Sender address.
        """
        # Extract blendshapes
        blendshapes = parsed.get("blendshapes") or parsed.get("BlendShapes")
        if not blendshapes and "blendshapeCoefficients" in parsed:
            blendshapes = parsed["blendshapeCoefficients"]

        if not blendshapes:
            logger.debug("No blendshape data in Live Link frame")
            return

        # Convert to floats and filter
        filtered = {}
        for k, v in blendshapes.items():
            try:
                val = float(v)
                if 0.0 <= val <= 1.0:
                    filtered[k] = val
            except (ValueError, TypeError):
                continue

        if not filtered:
            return

        # Create frame data
        frame_data = LiveLinkData(
            timestamp=time.time(),
            frame_number=parsed.get("frame", self._frame_count),
            blendshapes=filtered,
            head_rotation=parsed.get("headRotation"),
            head_translation=parsed.get("headTranslation"),
            raw_data=raw_data if self.settings.verbose_logging else None,
        )
        self._frame_count += 1

        # Store last data
        with self._lock:
            self._last_data = frame_data

        # Log if verbose
        if self.settings.verbose_logging:
            logger.debug(f"LiveLink frame {frame_data.frame_number}: {len(filtered)} blendshapes")

        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(frame_data)
            except Exception as e:
                logger.error(f"Live Link callback error: {e}")

        # Auto-apply if configured
        if self.settings.auto_apply and self.settings.apply_callback:
            try:
                self.settings.apply_callback(filtered)
            except Exception as e:
                logger.error(f"Auto-apply error: {e}")

    # ---- Utility Methods ----

    def set_apply_callback(self, callback: Callable[[Dict[str, float]], None]) -> None:
        """
        Set the callback for applying data to the rig.

        Args:
            callback: Function called with blendshape coefficients.
        """
        self.settings.apply_callback = callback

    def enable_auto_apply(self, enabled: bool = True) -> None:
        """
        Enable or disable automatic application.

        Args:
            enabled: True to enable, False to disable.
        """
        self.settings.auto_apply = enabled

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get receiver statistics.

        Returns:
            Dict with frame count, last frame time, etc.
        """
        return {
            "running": self._running,
            "frame_count": self._frame_count,
            "last_frame_time": self._last_data.timestamp if self._last_data else None,
            "last_frame_number": self._last_data.frame_number if self._last_data else None,
            "callback_count": len(self._callbacks),
            "port": self.settings.port,
        }

    # ---- Context Manager ----

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def __del__(self):
        self.stop()


# ---- Public API ----

__all__ = [
    "LiveLinkReceiver",
    "LiveLinkSettings",
    "LiveLinkData",
    "LiveLinkError",
]