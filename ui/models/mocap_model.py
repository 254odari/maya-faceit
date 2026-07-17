# ui/models/mocap_model.py

"""
ui/models/mocap_model.py

Motion capture data models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from enum import Enum


class MocapDeviceType(Enum):
    LIVELINK = "LiveLink"
    MEDIAPIPE = "MediaPipe"
    FACECAP = "FaceCap"
    OPTITRACK = "OptiTrack"


@dataclass
class MocapDevice:
    """A motion capture device."""
    name: str
    device_type: MocapDeviceType
    port: int = 8080
    connected: bool = False
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MocapRecording:
    """A recorded mocap session."""
    name: str
    start_time: float = 0.0
    end_time: float = 0.0
    frames: int = 0
    file_path: Optional[str] = None


@dataclass
class MocapModel:
    """Represents the mocap session state."""
    device: Optional[MocapDevice] = None
    is_recording: bool = False
    is_playing: bool = False
    recordings: List[MocapRecording] = field(default_factory=list)
    live_data: Dict[str, float] = field(default_factory=dict)  # channel -> value

    def set_device(self, device_type: MocapDeviceType, name: str = "") -> None:
        if not name:
            name = device_type.value
        self.device = MocapDevice(name=name, device_type=device_type)

    def start_recording(self, name: str) -> None:
        self.is_recording = True
        self.recordings.append(MocapRecording(name=name))

    def stop_recording(self) -> None:
        self.is_recording = False

    def get_device_list(self) -> List[str]:
        return [dev.value for dev in MocapDeviceType]

    def get_status(self) -> Dict[str, Any]:
        return {
            "connected": self.device.connected if self.device else False,
            "device": self.device.name if self.device else None,
            "recording": self.is_recording,
            "playing": self.is_playing,
        }