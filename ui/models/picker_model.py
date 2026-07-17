# ui/models/picker_model.py

"""
ui/models/picker_model.py

Expression picker data model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum


class PickerItemType(Enum):
    """Type of picker item."""
    EXPRESSION = "expression"
    VISEME = "viseme"
    CUSTOM = "custom"


@dataclass
class PickerItem:
    """An item in the picker (expression/viseme)."""
    name: str
    item_type: PickerItemType = PickerItemType.EXPRESSION
    targets: Dict[str, float] = field(default_factory=dict)  # target -> weight
    icon: Optional[str] = None
    color: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "item_type": self.item_type.value,
            "targets": self.targets,
            "icon": self.icon,
            "color": self.color,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PickerItem:
        return cls(
            name=data["name"],
            item_type=PickerItemType(data.get("item_type", "expression")),
            targets=data.get("targets", {}),
            icon=data.get("icon"),
            color=data.get("color"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class PickerModel:
    """Represents the expression picker state."""
    items: List[PickerItem] = field(default_factory=list)
    selected_item: Optional[str] = None

    def add_item(self, item: PickerItem) -> None:
        """Add a picker item."""
        self.items.append(item)

    def remove_item(self, name: str) -> None:
        """Remove an item by name."""
        self.items = [i for i in self.items if i.name != name]

    def get_item(self, name: str) -> Optional[PickerItem]:
        """Get an item by name."""
        for item in self.items:
            if item.name == name:
                return item
        return None

    def get_expression_names(self) -> List[str]:
        """Return a list of all expression names."""
        return [i.name for i in self.items]

    def clear(self) -> None:
        """Clear all items."""
        self.items.clear()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the picker model to a dictionary."""
        return {
            "items": [item.to_dict() for item in self.items],
            "selected_item": self.selected_item,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PickerModel:
        """Deserialize a picker model from a dictionary."""
        model = cls()
        model.items = [PickerItem.from_dict(item) for item in data.get("items", [])]
        model.selected_item = data.get("selected_item")
        return model