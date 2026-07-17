# ui/models/project_model.py

"""
ui/models/project_model.py

Project data model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import datetime

# Type-only imports to avoid circular references
if TYPE_CHECKING:
    from .rig_model import RigModel
    from .blendshape_model import BlendshapeTarget


@dataclass
class ProjectModel:
    """Represents a FaceIT project."""
    name: str
    path: str
    template: str = "Default"
    fps: int = 60
    created: str = field(default_factory=lambda: datetime.now().isoformat())
    modified: str = field(default_factory=lambda: datetime.now().isoformat())
    rig: Optional['RigModel'] = None
    blendshape_targets: List['BlendshapeTarget'] = field(default_factory=list)
    arkit_mapping: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "path": self.path,
            "template": self.template,
            "fps": self.fps,
            "created": self.created,
            "modified": self.modified,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ProjectModel:
        return cls(
            name=data["name"],
            path=data["path"],
            template=data.get("template", "Default"),
            fps=data.get("fps", 60),
            created=data.get("created", datetime.now().isoformat()),
            modified=data.get("modified", datetime.now().isoformat()),
            metadata=data.get("metadata", {}),
        )