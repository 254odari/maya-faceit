# ui/models/arkit_model.py

"""
ui/models/arkit_model.py

ARKit mapping data model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any


@dataclass
class ARKitChannel:
    """An ARKit channel and its mapping."""
    channel: str
    target: Optional[str] = None
    is_mapped: bool = False
    source: str = "user"  # 'user', 'auto'

    def to_dict(self) -> Dict[str, Any]:
        return {
            "channel": self.channel,
            "target": self.target,
            "is_mapped": self.is_mapped,
            "source": self.source,
        }


@dataclass
class ARKitModel:
    """Represents the ARKit 52 mapping."""
    channels: List[ARKitChannel] = field(default_factory=list)
    base_mesh: Optional[str] = None
    preset: str = "Apple ARKit"

    def __post_init__(self):
        if not self.channels:
            # Initialize with all 52 ARKit channels
            arkit_channels = [
                "EyeBlink_L", "EyeBlink_R", "EyeSquint_L", "EyeSquint_R",
                "EyeWide_L", "EyeWide_R", "EyeLookDown_L", "EyeLookDown_R",
                "EyeLookIn_L", "EyeLookIn_R", "EyeLookOut_L", "EyeLookOut_R",
                "EyeLookUp_L", "EyeLookUp_R", "BrowDown_L", "BrowDown_R",
                "BrowInnerUp", "BrowOuterUp_L", "BrowOuterUp_R", "CheekPuff",
                "CheekSquint_L", "CheekSquint_R", "JawOpen", "JawForward",
                "JawLeft", "JawRight", "MouthFunnel", "MouthPucker",
                "MouthLeft", "MouthRight", "MouthRollUpper", "MouthRollLower",
                "MouthShrugUpper", "MouthShrugLower", "MouthClose",
                "MouthSmile_L", "MouthSmile_R", "MouthFrown_L", "MouthFrown_R",
                "MouthDimple_L", "MouthDimple_R", "MouthUpperUp_L", "MouthUpperUp_R",
                "MouthLowerDown_L", "MouthLowerDown_R", "MouthPress_L", "MouthPress_R",
                "MouthStretch_L", "MouthStretch_R", "TongueOut", "NoseSneer_L", "NoseSneer_R"
            ]
            self.channels = [ARKitChannel(channel=ch) for ch in arkit_channels]

    def map_channel(self, channel: str, target: str) -> bool:
        for ch in self.channels:
            if ch.channel == channel:
                ch.target = target
                ch.is_mapped = True
                return True
        return False

    def get_mapping(self) -> Dict[str, str]:
        return {ch.channel: ch.target for ch in self.channels if ch.is_mapped and ch.target}

    def get_coverage(self) -> Dict[str, int]:
        mapped = sum(1 for ch in self.channels if ch.is_mapped)
        total = len(self.channels)
        return {"total": total, "mapped": mapped, "missing": total - mapped}