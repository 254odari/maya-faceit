# ui/models/blendshape_model.py

"""
ui/models/blendshape_model.py

Blendshape data models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class BlendshapeTarget:
    """A single blendshape target."""
    name: str
    target_mesh: str
    weight: float = 0.0
    locked: bool = False
    is_mirrored: bool = False
    source: str = "user"  # 'user', 'generated', 'imported'
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BlendshapeModel:
    """Represents the blendshape system."""
    base_mesh: str = ""
    targets: List[BlendshapeTarget] = field(default_factory=list)
    node_name: Optional[str] = None

    def add_target(self, target: BlendshapeTarget) -> None:
        self.targets.append(target)

    def remove_target(self, name: str) -> None:
        self.targets = [t for t in self.targets if t.name != name]

    def get_target(self, name: str) -> Optional[BlendshapeTarget]:
        for t in self.targets:
            if t.name == name:
                return t
        return None

    def get_weights(self) -> Dict[str, float]:
        return {t.name: t.weight for t in self.targets}

    def set_weight(self, name: str, weight: float) -> bool:
        target = self.get_target(name)
        if target:
            target.weight = weight
            return True
        return False

    def get_statistics(self) -> Dict[str, int]:
        return {
            "total": len(self.targets),
            "active": sum(1 for t in self.targets if t.weight > 0.01),
            "locked": sum(1 for t in self.targets if t.locked),
            "mirrored": sum(1 for t in self.targets if t.is_mirrored),
        }