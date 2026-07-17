"""
ui/controllers/arkit_controller.py

Controller for ARKit 52 blendshape mapping.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ARKitController:
    """Handles ARKit mapping and generation."""

    def __init__(self):
        self._mapping: Dict[str, str] = {}  # ARKit channel -> target name

    def generate_all(self, base_mesh: str) -> List[str]:
        """Generate all 52 ARKit blendshapes."""
        logger.info(f"Generating ARKit library on {base_mesh}")
        # TODO: Call core generator
        generated = ["EyeBlink_L", "EyeBlink_R", "JawOpen", "MouthSmile_L", "MouthSmile_R"]
        for name in generated:
            self._mapping[name] = name
        return generated

    def map_channel(self, channel: str, target: str) -> None:
        """Map an ARKit channel to a target."""
        self._mapping[channel] = target
        logger.info(f"Mapped {channel} -> {target}")

    def get_mapping(self) -> Dict[str, str]:
        return self._mapping

    def get_coverage(self) -> dict:
        """Return coverage statistics."""
        total = 52
        mapped = len(self._mapping)
        return {"total": total, "mapped": mapped, "missing": total - mapped}

    def auto_map(self) -> Dict[str, str]:
        """Automatically map ARKit channels to existing targets."""
        # TODO: Use naming heuristics
        return self._mapping