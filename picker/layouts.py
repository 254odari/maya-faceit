"""
maya_faceit.picker.layouts

Layout Engine for the Facial Control Picker.

This module manages the design, arrangement, loading, saving, and validation
of facial picker layouts. It defines where widgets appear on the picker canvas.

Author: Maya FaceIT Team
"""

from __future__ import annotations

import copy
import json
import logging
import math
import os
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Optional, Dict, List, Any, Callable, Tuple, Union, Set

# Qt imports
try:
    from PySide6 import QtCore, QtGui, QtWidgets # type: ignore
    from PySide6.QtCore import Qt, QRectF, QPointF # type: ignore
except ImportError:
    try:
        from PySide2 import QtCore, QtGui, QtWidgets # type: ignore
        from PySide2.QtCore import Qt, QRectF, QPointF # type: ignore
    except ImportError:
        raise ImportError("No Qt binding found (PySide6 or PySide2).")

# Local imports
try:
    from .widgets import (
        PickerWidget,
        ControllerWidget,
        WidgetType,
        WidgetGeometry,
        WidgetStyle,
        WidgetBinding,
        WidgetMetadata,
        WidgetUtils,
        EyeWidget,
        BrowWidget,
        JawWidget,
        LipWidget,
        TongueWidget,
        CheekWidget,
        NoseWidget,
        SliderWidget,
        JoystickWidget,
        ImageWidget,
        LabelWidget,
        RegionWidget,
    )
except ImportError:
    # Fallback for development
    class PickerWidget:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
    ControllerWidget = PickerWidget
    WidgetType = None
    class WidgetGeometry:
        def __init__(self, x=0, y=0, width=50, height=50):
            self.x = x
            self.y = y
            self.width = width
            self.height = height
    class WidgetStyle: pass
    class WidgetBinding: pass
    class WidgetMetadata: pass
    class WidgetUtils:
        @staticmethod
        def generate_id():
            import uuid
            return str(uuid.uuid4())[:8]
    EyeWidget = BrowWidget = JawWidget = LipWidget = TongueWidget = CheekWidget = NoseWidget = ControllerWidget
    SliderWidget = JoystickWidget = ImageWidget = LabelWidget = RegionWidget = ControllerWidget

logger = logging.getLogger(__name__)

# ============================================================================
# Part 1: Foundation
# ============================================================================

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"

# ============================================================================
# Part 2: Constants & Enumerations
# ============================================================================

class LayoutType(Enum):
    """Types of picker layouts."""
    HUMAN = "human"
    ARKIT52 = "arkit52"
    FACS = "facs"
    METAHUMAN = "metahuman"
    CREATURE = "creature"
    STYLIZED = "stylized"
    MINIMAL = "minimal"
    STUDIO = "studio"
    ANIMATOR = "animator"
    CUSTOM = "custom"


class LayoutOrientation(Enum):
    """Layout orientation and aspect ratio."""
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"
    SQUARE = "square"
    FREEFORM = "freeform"


class LayoutMode(Enum):
    """Layout interaction mode."""
    VIEW = "view"
    EDIT = "edit"
    LOCKED = "locked"
    TEMPLATE = "template"


class RegionType(Enum):
    """Facial regions."""
    EYES = "eyes"
    BROWS = "brows"
    NOSE = "nose"
    CHEEKS = "cheeks"
    MOUTH = "mouth"
    JAW = "jaw"
    TONGUE = "tongue"
    NECK = "neck"
    FOREHEAD = "forehead"
    EYELIDS = "eyelids"
    EARS = "ears"
    WHOLE_FACE = "whole_face"
    CUSTOM = "custom"


class PlacementType(Enum):
    """Widget placement strategies."""
    ABSOLUTE = "absolute"
    RELATIVE = "relative"
    ANCHORED = "anchored"
    GRID = "grid"
    RADIAL = "radial"
    SYMMETRIC = "symmetric"


class ScalingMode(Enum):
    """Responsive scaling modes."""
    FILL = "fill"
    FIT = "fit"
    STRETCH = "stretch"
    FIT_WIDTH = "fit_width"
    FIT_HEIGHT = "fit_height"
    CENTER = "center"
    NONE = "none"


# ============================================================================
# Part 3: Data Models
# ============================================================================

@dataclass
class WidgetPlacement:
    """
    Placement of a widget in a layout.
    """
    widget_id: str
    widget_type: str
    x: float
    y: float
    width: float = 50.0
    height: float = 50.0
    rotation: float = 0.0
    scale: float = 1.0
    z_order: int = 0
    locked: bool = False
    visible: bool = True
    region: str = "General"
    binding: Optional[Dict[str, Any]] = None
    style: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    anchor: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "widget_id": self.widget_id,
            "widget_type": self.widget_type,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "rotation": self.rotation,
            "scale": self.scale,
            "z_order": self.z_order,
            "locked": self.locked,
            "visible": self.visible,
            "region": self.region,
            "binding": self.binding,
            "style": self.style,
            "metadata": self.metadata,
            "anchor": self.anchor,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WidgetPlacement':
        return cls(
            widget_id=data["widget_id"],
            widget_type=data["widget_type"],
            x=data["x"],
            y=data["y"],
            width=data.get("width", 50.0),
            height=data.get("height", 50.0),
            rotation=data.get("rotation", 0.0),
            scale=data.get("scale", 1.0),
            z_order=data.get("z_order", 0),
            locked=data.get("locked", False),
            visible=data.get("visible", True),
            region=data.get("region", "General"),
            binding=data.get("binding"),
            style=data.get("style"),
            metadata=data.get("metadata"),
            anchor=data.get("anchor"),
        )


@dataclass
class LayoutPage:
    """
    A page within a layout (for multi-page pickers).
    """
    name: str
    placements: List[WidgetPlacement] = field(default_factory=list)
    background_image: Optional[str] = None
    background_color: Optional[Tuple[int, int, int]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "placements": [p.to_dict() for p in self.placements],
            "background_image": self.background_image,
            "background_color": self.background_color,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LayoutPage':
        page = cls(
            name=data["name"],
            background_image=data.get("background_image"),
            background_color=tuple(data["background_color"]) if data.get("background_color") else None,
            metadata=data.get("metadata", {}),
        )
        for pdata in data.get("placements", []):
            page.placements.append(WidgetPlacement.from_dict(pdata))
        return page


@dataclass
class LayoutRegion:
    """
    A logical region grouping multiple widgets.
    """
    name: str
    region_type: RegionType
    widget_ids: List[str] = field(default_factory=list)
    color: Optional[Tuple[int, int, int]] = None
    bounds: Optional[Tuple[float, float, float, float]] = None  # x, y, width, height
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "region_type": self.region_type.value,
            "widget_ids": self.widget_ids,
            "color": self.color,
            "bounds": self.bounds,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LayoutRegion':
        return cls(
            name=data["name"],
            region_type=RegionType(data["region_type"]),
            widget_ids=data.get("widget_ids", []),
            color=tuple(data["color"]) if data.get("color") else None,
            bounds=tuple(data["bounds"]) if data.get("bounds") else None,
            metadata=data.get("metadata", {}),
        )


@dataclass
class LayoutTemplate:
    """
    A reusable layout template.
    """
    name: str
    description: str = ""
    layout_type: LayoutType = LayoutType.CUSTOM
    canvas_width: float = 1024.0
    canvas_height: float = 1024.0
    orientation: LayoutOrientation = LayoutOrientation.SQUARE
    regions: List[LayoutRegion] = field(default_factory=list)
    pages: List[LayoutPage] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "layout_type": self.layout_type.value,
            "canvas_width": self.canvas_width,
            "canvas_height": self.canvas_height,
            "orientation": self.orientation.value,
            "regions": [r.to_dict() for r in self.regions],
            "pages": [p.to_dict() for p in self.pages],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LayoutTemplate':
        template = cls(
            name=data["name"],
            description=data.get("description", ""),
            layout_type=LayoutType(data["layout_type"]),
            canvas_width=data["canvas_width"],
            canvas_height=data["canvas_height"],
            orientation=LayoutOrientation(data["orientation"]),
            metadata=data.get("metadata", {}),
        )
        for rdata in data.get("regions", []):
            template.regions.append(LayoutRegion.from_dict(rdata))
        for pdata in data.get("pages", []):
            template.pages.append(LayoutPage.from_dict(pdata))
        return template


@dataclass
class PickerLayout:
    """
    Complete picker layout.
    """
    name: str
    template: Optional[LayoutTemplate] = None
    canvas_width: float = 1024.0
    canvas_height: float = 1024.0
    orientation: LayoutOrientation = LayoutOrientation.SQUARE
    pages: List[LayoutPage] = field(default_factory=list)
    current_page_index: int = 0
    regions: List[LayoutRegion] = field(default_factory=list)
    scale: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def current_page(self) -> Optional[LayoutPage]:
        if 0 <= self.current_page_index < len(self.pages):
            return self.pages[self.current_page_index]
        return None

    def add_page(self, page: LayoutPage) -> None:
        self.pages.append(page)

    def remove_page(self, index: int) -> None:
        if 0 <= index < len(self.pages):
            self.pages.pop(index)
            if self.current_page_index >= len(self.pages):
                self.current_page_index = len(self.pages) - 1

    def set_current_page(self, index: int) -> None:
        if 0 <= index < len(self.pages):
            self.current_page_index = index

    def add_region(self, region: LayoutRegion) -> None:
        self.regions.append(region)

    def remove_region(self, index: int) -> None:
        if 0 <= index < len(self.regions):
            self.regions.pop(index)

    def get_region(self, name: str) -> Optional[LayoutRegion]:
        for region in self.regions:
            if region.name == name:
                return region
        return None

    def get_page(self, name: str) -> Optional[LayoutPage]:
        for page in self.pages:
            if page.name == name:
                return page
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "template": self.template.to_dict() if self.template else None,
            "canvas_width": self.canvas_width,
            "canvas_height": self.canvas_height,
            "orientation": self.orientation.value,
            "pages": [p.to_dict() for p in self.pages],
            "current_page_index": self.current_page_index,
            "regions": [r.to_dict() for r in self.regions],
            "scale": self.scale,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PickerLayout':
        layout = cls(
            name=data["name"],
            template=LayoutTemplate.from_dict(data["template"]) if data.get("template") else None,
            canvas_width=data["canvas_width"],
            canvas_height=data["canvas_height"],
            orientation=LayoutOrientation(data["orientation"]),
            current_page_index=data.get("current_page_index", 0),
            scale=data.get("scale", 1.0),
            metadata=data.get("metadata", {}),
        )
        for pdata in data.get("pages", []):
            layout.pages.append(LayoutPage.from_dict(pdata))
        for rdata in data.get("regions", []):
            layout.regions.append(LayoutRegion.from_dict(rdata))
        return layout


@dataclass
class LayoutValidation:
    """Validation result for a layout."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LayoutReport:
    """Diagnostic report for a layout."""
    widget_count: int = 0
    region_count: int = 0
    page_count: int = 0
    canvas_width: float = 0.0
    canvas_height: float = 0.0
    overlaps: int = 0
    missing_bindings: int = 0
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# Part 4: Layout Manager
# ============================================================================

class LayoutManager:
    """
    Main controller for all layout operations.

    This class manages loading, saving, creating, editing, and validating
    picker layouts. It serves as the central interface for the layout system.
    """

    def __init__(self, parent=None):
        self._parent = parent
        self._layouts: Dict[str, PickerLayout] = {}
        self._active_layout: Optional[str] = None
        self._template_cache: Dict[str, LayoutTemplate] = {}
        self._mode: LayoutMode = LayoutMode.VIEW
        self._grid_size: float = 10.0
        self._snap_to_grid: bool = False
        self._dirty = False

        # Initialize built-in layouts and templates
        self._init_builtin_templates()
        self._init_builtin_layouts()

    # ========================================================================
    # Layout Management
    # ========================================================================

    def create_layout(self, name: str, template_name: Optional[str] = None) -> PickerLayout:
        """Create a new layout."""
        if name in self._layouts:
            raise ValueError(f"Layout '{name}' already exists.")

        if template_name and template_name in self._template_cache:
            template = self._template_cache[template_name]
            layout = PickerLayout(
                name=name,
                template=template,
                canvas_width=template.canvas_width,
                canvas_height=template.canvas_height,
                orientation=template.orientation,
            )
            # Copy pages from template
            for page in template.pages:
                layout.pages.append(copy.deepcopy(page))
            for region in template.regions:
                layout.regions.append(copy.deepcopy(region))
        else:
            layout = PickerLayout(name=name)
            # Add a default page
            layout.pages.append(LayoutPage(name="Main"))

        self._layouts[name] = layout
        self._active_layout = name
        self._dirty = True
        logger.info(f"Created layout: {name}")
        return layout

    def load_layout(self, name: str) -> Optional[PickerLayout]:
        """Load a layout by name."""
        if name not in self._layouts:
            logger.warning(f"Layout '{name}' not found.")
            return None
        self._active_layout = name
        return self._layouts[name]

    def save_layout(self, name: str) -> bool:
        """Save a layout (mark as clean)."""
        if name not in self._layouts:
            logger.warning(f"Layout '{name}' not found.")
            return False
        self._dirty = False
        logger.info(f"Saved layout: {name}")
        return True

    def delete_layout(self, name: str) -> None:
        """Delete a layout."""
        if name not in self._layouts:
            raise ValueError(f"Layout '{name}' not found.")
        del self._layouts[name]
        if self._active_layout == name:
            self._active_layout = next(iter(self._layouts)) if self._layouts else None
        logger.info(f"Deleted layout: {name}")

    def duplicate_layout(self, name: str, new_name: str) -> PickerLayout:
        """Duplicate a layout."""
        if name not in self._layouts:
            raise ValueError(f"Layout '{name}' not found.")
        if new_name in self._layouts:
            raise ValueError(f"Layout '{new_name}' already exists.")
        layout = self._layouts[name]
        new_layout = copy.deepcopy(layout)
        new_layout.name = new_name
        self._layouts[new_name] = new_layout
        self._dirty = True
        logger.info(f"Duplicated layout '{name}' to '{new_name}'")
        return new_layout

    def rename_layout(self, old_name: str, new_name: str) -> None:
        """Rename a layout."""
        if old_name not in self._layouts:
            raise ValueError(f"Layout '{old_name}' not found.")
        if new_name in self._layouts:
            raise ValueError(f"Layout '{new_name}' already exists.")
        layout = self._layouts.pop(old_name)
        layout.name = new_name
        self._layouts[new_name] = layout
        if self._active_layout == old_name:
            self._active_layout = new_name
        self._dirty = True

    def list_layouts(self) -> List[str]:
        """List all layout names."""
        return list(self._layouts.keys())

    def get_active_layout(self) -> Optional[PickerLayout]:
        """Get the active layout."""
        if self._active_layout:
            return self._layouts.get(self._active_layout)
        return None

    def set_active_layout(self, name: str) -> None:
        """Set the active layout."""
        if name not in self._layouts:
            raise ValueError(f"Layout '{name}' not found.")
        self._active_layout = name

    def is_dirty(self) -> bool:
        """Check if the layout has unsaved changes."""
        return self._dirty

    def clear(self) -> None:
        """Clear all layouts."""
        self._layouts.clear()
        self._active_layout = None
        self._dirty = False

    # ========================================================================
    # Built-in Layouts
    # ========================================================================

    def _init_builtin_templates(self) -> None:
        """Initialize built-in layout templates."""
        # Human Face Template
        human_template = LayoutTemplate(
            name="Human",
            description="Standard human facial layout",
            layout_type=LayoutType.HUMAN,
            canvas_width=1024,
            canvas_height=1024,
            orientation=LayoutOrientation.SQUARE,
        )
        self._template_cache["Human"] = human_template

        # ARKit52 Template
        arkit_template = LayoutTemplate(
            name="ARKit52",
            description="Apple ARKit 52 blendshape layout",
            layout_type=LayoutType.ARKIT52,
            canvas_width=1200,
            canvas_height=800,
            orientation=LayoutOrientation.LANDSCAPE,
        )
        self._template_cache["ARKit52"] = arkit_template

        # MetaHuman Template
        metahuman_template = LayoutTemplate(
            name="MetaHuman",
            description="MetaHuman facial layout",
            layout_type=LayoutType.METAHUMAN,
            canvas_width=1024,
            canvas_height=1024,
            orientation=LayoutOrientation.SQUARE,
        )
        self._template_cache["MetaHuman"] = metahuman_template

        # Minimal Template
        minimal_template = LayoutTemplate(
            name="Minimal",
            description="Minimal clean layout",
            layout_type=LayoutType.MINIMAL,
            canvas_width=800,
            canvas_height=800,
            orientation=LayoutOrientation.SQUARE,
        )
        self._template_cache["Minimal"] = minimal_template

        # Animator Template
        animator_template = LayoutTemplate(
            name="Animator",
            description="Animator-friendly layout with large controls",
            layout_type=LayoutType.ANIMATOR,
            canvas_width=1024,
            canvas_height=768,
            orientation=LayoutOrientation.LANDSCAPE,
        )
        self._template_cache["Animator"] = animator_template

        # Creature Template
        creature_template = LayoutTemplate(
            name="Creature",
            description="Creature/non-human facial layout",
            layout_type=LayoutType.CREATURE,
            canvas_width=1024,
            canvas_height=1024,
            orientation=LayoutOrientation.SQUARE,
        )
        self._template_cache["Creature"] = creature_template

    def _init_builtin_layouts(self) -> None:
        """Initialize built-in layouts with actual widget placements."""
        # Human Face Layout
        human_layout = self._build_human_layout()
        self._layouts["Human Face"] = human_layout

        # ARKit52 Layout
        arkit_layout = self._build_arkit_layout()
        self._layouts["ARKit52"] = arkit_layout

        # MetaHuman Layout
        metahuman_layout = self._build_metahuman_layout()
        self._layouts["MetaHuman"] = metahuman_layout

        # Minimal Layout
        minimal_layout = self._build_minimal_layout()
        self._layouts["Minimal"] = minimal_layout

        # Animator Layout
        animator_layout = self._build_animator_layout()
        self._layouts["Animator"] = animator_layout

        # Eyes Only Layout
        eyes_layout = self._build_eyes_only_layout()
        self._layouts["Eyes Only"] = eyes_layout

        # Mouth Only Layout
        mouth_layout = self._build_mouth_only_layout()
        self._layouts["Mouth Only"] = mouth_layout

        self._active_layout = "Human Face"

    def _build_human_layout(self) -> PickerLayout:
        """Build the Human Face layout."""
        layout = PickerLayout(name="Human Face", canvas_width=1024, canvas_height=1024)
        page = LayoutPage(name="Main")

        # Define human face widget placements
        # Eyes (symmetrical)
        page.placements.extend([
            WidgetPlacement(
                widget_id=WidgetUtils.generate_id(),
                widget_type="EyeWidget",
                x=250, y=320, width=80, height=80,
                region="Eyes",
                binding={"controller_name": "L_eye_ctrl"},
                metadata={"side": "left", "label": "L Eye"}
            ),
            WidgetPlacement(
                widget_id=WidgetUtils.generate_id(),
                widget_type="EyeWidget",
                x=694, y=320, width=80, height=80,
                region="Eyes",
                binding={"controller_name": "R_eye_ctrl"},
                metadata={"side": "right", "label": "R Eye"}
            ),
        ])

        # Brows
        page.placements.extend([
            WidgetPlacement(
                widget_id=WidgetUtils.generate_id(),
                widget_type="BrowWidget",
                x=230, y=220, width=70, height=50,
                region="Brows",
                binding={"controller_name": "L_brow_ctrl"},
                metadata={"side": "left", "label": "L Brow"}
            ),
            WidgetPlacement(
                widget_id=WidgetUtils.generate_id(),
                widget_type="BrowWidget",
                x=724, y=220, width=70, height=50,
                region="Brows",
                binding={"controller_name": "R_brow_ctrl"},
                metadata={"side": "right", "label": "R Brow"}
            ),
            WidgetPlacement(
                widget_id=WidgetUtils.generate_id(),
                widget_type="BrowWidget",
                x=477, y=240, width=70, height=40,
                region="Brows",
                binding={"controller_name": "C_brow_ctrl"},
                metadata={"side": "center", "label": "C Brow"}
            ),
        ])

        # Eyes Lids
        page.placements.extend([
            WidgetPlacement(
                widget_id=WidgetUtils.generate_id(),
                widget_type="ControllerWidget",
                x=235, y=400, width=60, height=40,
                region="Eyelids",
                binding={"controller_name": "L_eyelid_ctrl"},
                metadata={"label": "L Lid"}
            ),
            WidgetPlacement(
                widget_id=WidgetUtils.generate_id(),
                widget_type="ControllerWidget",
                x=729, y=400, width=60, height=40,
                region="Eyelids",
                binding={"controller_name": "R_eyelid_ctrl"},
                metadata={"label": "R Lid"}
            ),
        ])

        # Nose
        page.placements.append(
            WidgetPlacement(
                widget_id=WidgetUtils.generate_id(),
                widget_type="NoseWidget",
                x=472, y=450, width=80, height=80,
                region="Nose",
                binding={"controller_name": "C_nose_ctrl"},
                metadata={"label": "Nose"}
            )
        )

        # Cheeks
        page.placements.extend([
            WidgetPlacement(
                widget_id=WidgetUtils.generate_id(),
                widget_type="CheekWidget",
                x=200, y=530, width=70, height=70,
                region="Cheeks",
                binding={"controller_name": "L_cheek_ctrl"},
                metadata={"side": "left", "label": "L Cheek"}
            ),
            WidgetPlacement(
                widget_id=WidgetUtils.generate_id(),
                widget_type="CheekWidget",
                x=754, y=530, width=70, height=70,
                region="Cheeks",
                binding={"controller_name": "R_cheek_ctrl"},
                metadata={"side": "right", "label": "R Cheek"}
            ),
        ])

        # Mouth
        page.placements.extend([
            WidgetPlacement(
                widget_id=WidgetUtils.generate_id(),
                widget_type="LipWidget",
                x=402, y=620, width=220, height=60,
                region="Mouth",
                binding={"controller_name": "C_mouth_ctrl"},
                metadata={"label": "Mouth"}
            ),
            WidgetPlacement(
                widget_id=WidgetUtils.generate_id(),
                widget_type="ControllerWidget",
                x=290, y=630, width=60, height=40,
                region="Mouth",
                binding={"controller_name": "L_lip_corner_ctrl"},
                metadata={"side": "left", "label": "L Corner"}
            ),
            WidgetPlacement(
                widget_id=WidgetUtils.generate_id(),
                widget_type="ControllerWidget",
                x=674, y=630, width=60, height=40,
                region="Mouth",
                binding={"controller_name": "R_lip_corner_ctrl"},
                metadata={"side": "right", "label": "R Corner"}
            ),
        ])

        # Jaw
        page.placements.append(
            WidgetPlacement(
                widget_id=WidgetUtils.generate_id(),
                widget_type="JawWidget",
                x=442, y=760, width=140, height=100,
                region="Jaw",
                binding={"controller_name": "C_jaw_ctrl"},
                metadata={"label": "Jaw"}
            )
        )

        # Jaw side controls
        page.placements.extend([
            WidgetPlacement(
                widget_id=WidgetUtils.generate_id(),
                widget_type="ControllerWidget",
                x=340, y=800, width=60, height=40,
                region="Jaw",
                binding={"controller_name": "L_jaw_side_ctrl"},
                metadata={"side": "left", "label": "L Jaw"}
            ),
            WidgetPlacement(
                widget_id=WidgetUtils.generate_id(),
                widget_type="ControllerWidget",
                x=624, y=800, width=60, height=40,
                region="Jaw",
                binding={"controller_name": "R_jaw_side_ctrl"},
                metadata={"side": "right", "label": "R Jaw"}
            ),
        ])

        # Tongue
        page.placements.append(
            WidgetPlacement(
                widget_id=WidgetUtils.generate_id(),
                widget_type="TongueWidget",
                x=452, y=630, width=120, height=60,
                region="Tongue",
                binding={"controller_name": "C_tongue_ctrl"},
                metadata={"label": "Tongue"}
            )
        )

        # Neck
        page.placements.append(
            WidgetPlacement(
                widget_id=WidgetUtils.generate_id(),
                widget_type="ControllerWidget",
                x=457, y=880, width=110, height=80,
                region="Neck",
                binding={"controller_name": "C_neck_ctrl"},
                metadata={"label": "Neck"}
            )
        )

        # Sliders for expressions
        page.placements.extend([
            WidgetPlacement(
                widget_id=WidgetUtils.generate_id(),
                widget_type="SliderWidget",
                x=50, y=50, width=150, height=30,
                region="Whole Face",
                binding={"controller_name": "C_expression_slider"},
                metadata={"label": "Smile", "min": 0, "max": 1}
            ),
            WidgetPlacement(
                widget_id=WidgetUtils.generate_id(),
                widget_type="SliderWidget",
                x=50, y=90, width=150, height=30,
                region="Whole Face",
                binding={"controller_name": "C_expression_slider"},
                metadata={"label": "Blink", "min": 0, "max": 1}
            ),
            WidgetPlacement(
                widget_id=WidgetUtils.generate_id(),
                widget_type="SliderWidget",
                x=50, y=130, width=150, height=30,
                region="Whole Face",
                binding={"controller_name": "C_expression_slider"},
                metadata={"label": "Jaw", "min": 0, "max": 1}
            ),
        ])

        # Master controls
        page.placements.extend([
            WidgetPlacement(
                widget_id=WidgetUtils.generate_id(),
                widget_type="ControllerWidget",
                x=850, y=50, width=80, height=80,
                region="Whole Face",
                binding={"controller_name": "C_master_ctrl"},
                metadata={"label": "Master"}
            ),
            WidgetPlacement(
                widget_id=WidgetUtils.generate_id(),
                widget_type="ControllerWidget",
                x=850, y=160, width=60, height=60,
                region="Whole Face",
                binding={"controller_name": "C_rig_ctrl"},
                metadata={"label": "Rig"}
            ),
        ])

        layout.pages.append(page)
        return layout

    def _build_arkit_layout(self) -> PickerLayout:
        """Build the ARKit52 layout."""
        layout = PickerLayout(name="ARKit52", canvas_width=1200, canvas_height=800, orientation=LayoutOrientation.LANDSCAPE)
        page = LayoutPage(name="ARKit52")

        # ARKit 52 blendshape positions (organized by region)
        # We'll use a grid layout for ARKit channels
        arkit_channels = [
            "browDownLeft", "browDownRight", "browInnerUp",
            "browOuterUpLeft", "browOuterUpRight",
            "cheekPuff", "cheekSquintLeft", "cheekSquintRight",
            "eyeBlinkLeft", "eyeBlinkRight",
            "eyeLookDownLeft", "eyeLookDownRight",
            "eyeLookInLeft", "eyeLookInRight",
            "eyeLookOutLeft", "eyeLookOutRight",
            "eyeLookUpLeft", "eyeLookUpRight",
            "eyeSquintLeft", "eyeSquintRight",
            "eyeWideLeft", "eyeWideRight",
            "jawForward", "jawLeft", "jawOpen", "jawRight",
            "mouthClose", "mouthDimpleLeft", "mouthDimpleRight",
            "mouthFrownLeft", "mouthFrownRight",
            "mouthFunnel", "mouthLeft", "mouthLowerDownLeft",
            "mouthLowerDownRight", "mouthPressLeft", "mouthPressRight",
            "mouthPucker", "mouthRight", "mouthRollLower",
            "mouthRollUpper", "mouthShrugLower", "mouthShrugUpper",
            "mouthSmileLeft", "mouthSmileRight",
            "mouthStretchLeft", "mouthStretchRight",
            "mouthUpperUpLeft", "mouthUpperUpRight",
            "noseSneerLeft", "noseSneerRight",
            "tongueOut"
        ]

        # Grid layout: 13 columns x 4 rows
        cols = 13
        spacing_x = 85
        spacing_y = 70
        start_x = 40
        start_y = 40

        for i, channel in enumerate(arkit_channels):
            row = i // cols
            col = i % cols
            x = start_x + col * spacing_x
            y = start_y + row * spacing_y

            # Determine region based on channel name
            region = "ARKit"
            if "brow" in channel:
                region = "Brows"
            elif "eye" in channel:
                region = "Eyes"
            elif "jaw" in channel:
                region = "Jaw"
            elif "mouth" in channel or "lip" in channel:
                region = "Mouth"
            elif "nose" in channel:
                region = "Nose"
            elif "cheek" in channel:
                region = "Cheeks"
            elif "tongue" in channel:
                region = "Tongue"

            page.placements.append(
                WidgetPlacement(
                    widget_id=WidgetUtils.generate_id(),
                    widget_type="ControllerWidget",
                    x=x, y=y, width=60, height=50,
                    region=region,
                    binding={"controller_name": channel},
                    metadata={"label": channel, "arkit": True}
                )
            )

        layout.pages.append(page)
        return layout

    def _build_metahuman_layout(self) -> PickerLayout:
        """Build the MetaHuman layout."""
        # Similar to Human but with MetaHuman-specific naming
        layout = PickerLayout(name="MetaHuman", canvas_width=1024, canvas_height=1024)
        page = LayoutPage(name="MetaHuman")

        # Use human layout but with different controller naming
        # For brevity, we'll use the human layout with a prefix
        human_layout = self._build_human_layout()
        for placement in human_layout.pages[0].placements:
            # Modify controller names for MetaHuman naming convention
            if placement.binding and "controller_name" in placement.binding:
                name = placement.binding["controller_name"]
                # MetaHuman uses "Face" prefix
                if name.startswith("L_"):
                    placement.binding["controller_name"] = f"Face_L_{name[2:]}"
                elif name.startswith("R_"):
                    placement.binding["controller_name"] = f"Face_R_{name[2:]}"
                elif name.startswith("C_"):
                    placement.binding["controller_name"] = f"Face_{name[2:]}"
                else:
                    placement.binding["controller_name"] = f"Face_{name}"
            page.placements.append(placement)

        layout.pages.append(page)
        return layout

    def _build_minimal_layout(self) -> PickerLayout:
        """Build a minimal layout with essential controls."""
        layout = PickerLayout(name="Minimal", canvas_width=800, canvas_height=800)
        page = LayoutPage(name="Main")

        # Only the most essential controls
        placements = [
            (400, 300, 120, 120, "EyeWidget", "L_eye_ctrl", "L Eye", "Eyes"),
            (400, 300, 120, 120, "EyeWidget", "R_eye_ctrl", "R Eye", "Eyes"),
            (400, 200, 100, 60, "BrowWidget", "C_brow_ctrl", "Brow", "Brows"),
            (400, 450, 140, 80, "JawWidget", "C_jaw_ctrl", "Jaw", "Jaw"),
            (400, 550, 160, 60, "LipWidget", "C_mouth_ctrl", "Mouth", "Mouth"),
        ]

        for x, y, w, h, wtype, ctrl, label, region in placements:
            page.placements.append(
                WidgetPlacement(
                    widget_id=WidgetUtils.generate_id(),
                    widget_type=wtype,
                    x=x - w/2, y=y - h/2, width=w, height=h,
                    region=region,
                    binding={"controller_name": ctrl},
                    metadata={"label": label}
                )
            )

        layout.pages.append(page)
        return layout

    def _build_animator_layout(self) -> PickerLayout:
        """Build an animator-friendly layout with large controls."""
        layout = PickerLayout(name="Animator", canvas_width=1024, canvas_height=768, orientation=LayoutOrientation.LANDSCAPE)
        page = LayoutPage(name="Main")

        # Larger controls, spaced for easy selection
        # Similar to human layout but with bigger widgets
        human_layout = self._build_human_layout()
        for placement in human_layout.pages[0].placements:
            # Increase size by 30%
            placement.width *= 1.3
            placement.height *= 1.3
            placement.x -= placement.width * 0.15
            placement.y -= placement.height * 0.15
            page.placements.append(placement)

        layout.pages.append(page)
        return layout

    def _build_eyes_only_layout(self) -> PickerLayout:
        """Build an eyes-only layout."""
        layout = PickerLayout(name="Eyes Only", canvas_width=600, canvas_height=600)
        page = LayoutPage(name="Eyes")

        placements = [
            (150, 300, 120, 120, "EyeWidget", "L_eye_ctrl", "L Eye", "Eyes"),
            (450, 300, 120, 120, "EyeWidget", "R_eye_ctrl", "R Eye", "Eyes"),
            (150, 120, 80, 60, "BrowWidget", "L_brow_ctrl", "L Brow", "Brows"),
            (450, 120, 80, 60, "BrowWidget", "R_brow_ctrl", "R Brow", "Brows"),
            (300, 120, 80, 60, "BrowWidget", "C_brow_ctrl", "C Brow", "Brows"),
            (150, 450, 80, 60, "ControllerWidget", "L_eyelid_ctrl", "L Lid", "Eyelids"),
            (450, 450, 80, 60, "ControllerWidget", "R_eyelid_ctrl", "R Lid", "Eyelids"),
        ]

        for x, y, w, h, wtype, ctrl, label, region in placements:
            page.placements.append(
                WidgetPlacement(
                    widget_id=WidgetUtils.generate_id(),
                    widget_type=wtype,
                    x=x - w/2, y=y - h/2, width=w, height=h,
                    region=region,
                    binding={"controller_name": ctrl},
                    metadata={"label": label}
                )
            )

        layout.pages.append(page)
        return layout

    def _build_mouth_only_layout(self) -> PickerLayout:
        """Build a mouth-only layout."""
        layout = PickerLayout(name="Mouth Only", canvas_width=600, canvas_height=600)
        page = LayoutPage(name="Mouth")

        placements = [
            (300, 300, 180, 70, "LipWidget", "C_mouth_ctrl", "Mouth", "Mouth"),
            (140, 310, 80, 50, "ControllerWidget", "L_lip_corner_ctrl", "L Corner", "Mouth"),
            (460, 310, 80, 50, "ControllerWidget", "R_lip_corner_ctrl", "R Corner", "Mouth"),
            (300, 420, 120, 80, "JawWidget", "C_jaw_ctrl", "Jaw", "Jaw"),
            (300, 200, 100, 50, "ControllerWidget", "C_lip_upper_ctrl", "Upper", "Mouth"),
            (300, 390, 100, 50, "ControllerWidget", "C_lip_lower_ctrl", "Lower", "Mouth"),
        ]

        for x, y, w, h, wtype, ctrl, label, region in placements:
            page.placements.append(
                WidgetPlacement(
                    widget_id=WidgetUtils.generate_id(),
                    widget_type=wtype,
                    x=x - w/2, y=y - h/2, width=w, height=h,
                    region=region,
                    binding={"controller_name": ctrl},
                    metadata={"label": label}
                )
            )

        layout.pages.append(page)
        return layout

    # ========================================================================
    # Widget Placement
    # ========================================================================

    def add_widget_to_layout(
        self,
        layout_name: str,
        widget_data: Dict[str, Any],
        page_index: int = 0,
        x: Optional[float] = None,
        y: Optional[float] = None,
    ) -> Optional[WidgetPlacement]:
        """Add a widget to a layout."""
        layout = self.get_layout(layout_name)
        if not layout:
            return None

        if page_index >= len(layout.pages):
            return None

        page = layout.pages[page_index]
        widget_id = widget_data.get("widget_id", WidgetUtils.generate_id())

        # Determine position if not provided
        if x is None:
            x = layout.canvas_width / 2
        if y is None:
            y = layout.canvas_height / 2

        placement = WidgetPlacement(
            widget_id=widget_id,
            widget_type=widget_data.get("widget_type", "ControllerWidget"),
            x=x,
            y=y,
            width=widget_data.get("width", 60.0),
            height=widget_data.get("height", 60.0),
            region=widget_data.get("region", "General"),
            binding=widget_data.get("binding"),
            style=widget_data.get("style"),
            metadata=widget_data.get("metadata"),
        )
        page.placements.append(placement)
        self._dirty = True
        return placement

    def remove_widget_from_layout(
        self,
        layout_name: str,
        widget_id: str,
        page_index: int = 0,
    ) -> bool:
        """Remove a widget from a layout."""
        layout = self.get_layout(layout_name)
        if not layout:
            return False

        if page_index >= len(layout.pages):
            return False

        page = layout.pages[page_index]
        for i, placement in enumerate(page.placements):
            if placement.widget_id == widget_id:
                page.placements.pop(i)
                self._dirty = True
                return True
        return False

    def get_widget_placement(
        self,
        layout_name: str,
        widget_id: str,
        page_index: int = 0,
    ) -> Optional[WidgetPlacement]:
        """Get a widget's placement in a layout."""
        layout = self.get_layout(layout_name)
        if not layout:
            return None

        if page_index >= len(layout.pages):
            return None

        page = layout.pages[page_index]
        for placement in page.placements:
            if placement.widget_id == widget_id:
                return placement
        return None

    def move_widget(
        self,
        layout_name: str,
        widget_id: str,
        x: float,
        y: float,
        page_index: int = 0,
    ) -> bool:
        """Move a widget to a new position."""
        placement = self.get_widget_placement(layout_name, widget_id, page_index)
        if not placement:
            return False
        placement.x = x
        placement.y = y
        self._dirty = True
        return True

    def resize_widget(
        self,
        layout_name: str,
        widget_id: str,
        width: float,
        height: float,
        page_index: int = 0,
    ) -> bool:
        """Resize a widget."""
        placement = self.get_widget_placement(layout_name, widget_id, page_index)
        if not placement:
            return False
        placement.width = width
        placement.height = height
        self._dirty = True
        return True

    def align_widgets(
        self,
        layout_name: str,
        widget_ids: List[str],
        alignment: str,  # 'left', 'right', 'top', 'bottom', 'center', 'center_h', 'center_v'
        page_index: int = 0,
    ) -> bool:
        """Align multiple widgets."""
        layout = self.get_layout(layout_name)
        if not layout:
            return False

        if page_index >= len(layout.pages):
            return False

        page = layout.pages[page_index]
        placements = [p for p in page.placements if p.widget_id in widget_ids]
        if len(placements) < 2:
            return False

        # Calculate bounds
        min_x = min(p.x for p in placements)
        max_x = max(p.x + p.width for p in placements)
        min_y = min(p.y for p in placements)
        max_y = max(p.y + p.height for p in placements)
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2

        for placement in placements:
            if alignment == 'left':
                placement.x = min_x
            elif alignment == 'right':
                placement.x = max_x - placement.width
            elif alignment == 'top':
                placement.y = min_y
            elif alignment == 'bottom':
                placement.y = max_y - placement.height
            elif alignment == 'center':
                placement.x = center_x - placement.width / 2
                placement.y = center_y - placement.height / 2
            elif alignment == 'center_h':
                placement.x = center_x - placement.width / 2
            elif alignment == 'center_v':
                placement.y = center_y - placement.height / 2

        self._dirty = True
        return True

    def distribute_widgets(
        self,
        layout_name: str,
        widget_ids: List[str],
        direction: str,  # 'horizontal', 'vertical'
        spacing: float = 20.0,
        page_index: int = 0,
    ) -> bool:
        """Distribute widgets evenly."""
        layout = self.get_layout(layout_name)
        if not layout:
            return False

        if page_index >= len(layout.pages):
            return False

        page = layout.pages[page_index]
        placements = [p for p in page.placements if p.widget_id in widget_ids]
        if len(placements) < 2:
            return False

        # Sort by position
        if direction == 'horizontal':
            placements.sort(key=lambda p: p.x)
            total_width = sum(p.width for p in placements)
            start_x = placements[0].x
            end_x = placements[-1].x + placements[-1].width
            available = end_x - start_x - total_width
            if len(placements) > 1:
                gap = available / (len(placements) - 1)
                current_x = start_x
                for i, p in enumerate(placements):
                    p.x = current_x
                    current_x += p.width + gap
        else:  # vertical
            placements.sort(key=lambda p: p.y)
            total_height = sum(p.height for p in placements)
            start_y = placements[0].y
            end_y = placements[-1].y + placements[-1].height
            available = end_y - start_y - total_height
            if len(placements) > 1:
                gap = available / (len(placements) - 1)
                current_y = start_y
                for i, p in enumerate(placements):
                    p.y = current_y
                    current_y += p.height + gap

        self._dirty = True
        return True

    # ========================================================================
    # Regions
    # ========================================================================

    def add_region(self, layout_name: str, region: LayoutRegion) -> None:
        """Add a region to a layout."""
        layout = self.get_layout(layout_name)
        if not layout:
            raise ValueError(f"Layout '{layout_name}' not found.")
        layout.regions.append(region)
        self._dirty = True

    def remove_region(self, layout_name: str, region_name: str) -> bool:
        """Remove a region from a layout."""
        layout = self.get_layout(layout_name)
        if not layout:
            return False
        for i, region in enumerate(layout.regions):
            if region.name == region_name:
                layout.regions.pop(i)
                self._dirty = True
                return True
        return False

    def assign_to_region(
        self,
        layout_name: str,
        widget_ids: List[str],
        region_name: str,
        page_index: int = 0,
    ) -> bool:
        """Assign widgets to a region."""
        layout = self.get_layout(layout_name)
        if not layout:
            return False

        if page_index >= len(layout.pages):
            return False

        page = layout.pages[page_index]
        for placement in page.placements:
            if placement.widget_id in widget_ids:
                placement.region = region_name

        self._dirty = True
        return True

    def get_widgets_in_region(
        self,
        layout_name: str,
        region_name: str,
        page_index: int = 0,
    ) -> List[WidgetPlacement]:
        """Get all widgets in a region."""
        layout = self.get_layout(layout_name)
        if not layout:
            return []

        if page_index >= len(layout.pages):
            return []

        page = layout.pages[page_index]
        return [p for p in page.placements if p.region == region_name]

    # ========================================================================
    # Responsive Scaling
    # ========================================================================

    def scale_layout(
        self,
        layout_name: str,
        scale_factor: float,
        preserve_aspect: bool = True,
    ) -> None:
        """Scale the entire layout."""
        layout = self.get_layout(layout_name)
        if not layout:
            return

        new_width = layout.canvas_width * scale_factor
        new_height = layout.canvas_height * scale_factor

        if preserve_aspect:
            # Use the smaller scale to maintain aspect ratio
            aspect = layout.canvas_width / layout.canvas_height
            if new_width / new_height > aspect:
                new_width = new_height * aspect
            else:
                new_height = new_width / aspect

        # Scale all placements
        scale_x = new_width / layout.canvas_width
        scale_y = new_height / layout.canvas_height

        for page in layout.pages:
            for placement in page.placements:
                placement.x *= scale_x
                placement.y *= scale_y
                placement.width *= scale_x
                placement.height *= scale_y

        layout.canvas_width = new_width
        layout.canvas_height = new_height
        layout.scale *= scale_factor
        self._dirty = True

    def fit_layout_to_size(
        self,
        layout_name: str,
        target_width: float,
        target_height: float,
        mode: ScalingMode = ScalingMode.FIT,
    ) -> None:
        """Fit a layout to a target size."""
        layout = self.get_layout(layout_name)
        if not layout:
            return

        if mode == ScalingMode.NONE:
            return

        width_ratio = target_width / layout.canvas_width
        height_ratio = target_height / layout.canvas_height

        if mode == ScalingMode.FIT:
            scale = min(width_ratio, height_ratio)
        elif mode == ScalingMode.FILL:
            scale = max(width_ratio, height_ratio)
        elif mode == ScalingMode.STRETCH:
            scale_x = width_ratio
            scale_y = height_ratio
            self._scale_layout_custom(layout, scale_x, scale_y)
            return
        elif mode == ScalingMode.FIT_WIDTH:
            scale = width_ratio
        elif mode == ScalingMode.FIT_HEIGHT:
            scale = height_ratio
        else:
            scale = 1.0

        self._scale_layout_custom(layout, scale, scale)

    def _scale_layout_custom(self, layout: PickerLayout, scale_x: float, scale_y: float) -> None:
        """Scale a layout with custom x and y scales."""
        for page in layout.pages:
            for placement in page.placements:
                placement.x *= scale_x
                placement.y *= scale_y
                placement.width *= scale_x
                placement.height *= scale_y

        layout.canvas_width *= scale_x
        layout.canvas_height *= scale_y
        layout.scale *= (scale_x + scale_y) / 2
        self._dirty = True

    # ========================================================================
    # Auto Layout Generation
    # ========================================================================

    def generate_from_rig(
        self,
        rig_data: Dict[str, Any],
        layout_name: str = "Generated",
        template_name: str = "Human",
    ) -> PickerLayout:
        """
        Generate a layout from rig data.

        Args:
            rig_data: Dict with 'controllers' list of controller names.
            layout_name: Name for the generated layout.
            template_name: Template to use as base.

        Returns:
            Generated PickerLayout.
        """
        layout = self.create_layout(layout_name, template_name)
        if not layout:
            raise ValueError(f"Failed to create layout '{layout_name}'.")

        # Get the main page
        if not layout.pages:
            layout.pages.append(LayoutPage(name="Main"))
        page = layout.pages[0]

        # Place controllers in a grid
        controllers = rig_data.get("controllers", [])
        cols = 10
        spacing_x = 80
        spacing_y = 70
        start_x = 40
        start_y = 40

        for i, ctrl in enumerate(controllers):
            row = i // cols
            col = i % cols
            x = start_x + col * spacing_x
            y = start_y + row * spacing_y

            # Determine widget type based on name
            widget_type = "ControllerWidget"
            if "eye" in ctrl.lower():
                widget_type = "EyeWidget"
            elif "brow" in ctrl.lower():
                widget_type = "BrowWidget"
            elif "jaw" in ctrl.lower():
                widget_type = "JawWidget"
            elif "lip" in ctrl.lower() or "mouth" in ctrl.lower():
                widget_type = "LipWidget"
            elif "cheek" in ctrl.lower():
                widget_type = "CheekWidget"
            elif "nose" in ctrl.lower():
                widget_type = "NoseWidget"
            elif "tongue" in ctrl.lower():
                widget_type = "TongueWidget"

            page.placements.append(
                WidgetPlacement(
                    widget_id=WidgetUtils.generate_id(),
                    widget_type=widget_type,
                    x=x, y=y, width=50, height=50,
                    binding={"controller_name": ctrl},
                    metadata={"label": ctrl}
                )
            )

        self._dirty = True
        return layout

    def generate_from_arkit(self, layout_name: str = "ARKit Generated") -> PickerLayout:
        """Generate a layout from ARKit channel list."""
        arkit_layout = self._build_arkit_layout()
        arkit_layout.name = layout_name
        self._layouts[layout_name] = arkit_layout
        self._dirty = True
        return arkit_layout

    # ========================================================================
    # Layout Templates
    # ========================================================================

    def get_template(self, name: str) -> Optional[LayoutTemplate]:
        """Get a layout template."""
        return self._template_cache.get(name)

    def list_templates(self) -> List[str]:
        """List all available templates."""
        return list(self._template_cache.keys())

    def register_template(self, template: LayoutTemplate) -> None:
        """Register a new template."""
        self._template_cache[template.name] = template

    def create_layout_from_template(
        self,
        template_name: str,
        layout_name: str,
    ) -> Optional[PickerLayout]:
        """Create a new layout from a template."""
        template = self.get_template(template_name)
        if not template:
            return None

        if layout_name in self._layouts:
            raise ValueError(f"Layout '{layout_name}' already exists.")

        layout = PickerLayout(
            name=layout_name,
            template=template,
            canvas_width=template.canvas_width,
            canvas_height=template.canvas_height,
            orientation=template.orientation,
        )
        for page in template.pages:
            layout.pages.append(copy.deepcopy(page))
        for region in template.regions:
            layout.regions.append(copy.deepcopy(region))

        self._layouts[layout_name] = layout
        self._dirty = True
        return layout

    # ========================================================================
    # Layout Validation
    # ========================================================================

    def validate_layout(self, name: str) -> LayoutValidation:
        """Validate a layout."""
        layout = self.get_layout(name)
        if not layout:
            return LayoutValidation(is_valid=False, errors=[f"Layout '{name}' not found."])

        validation = LayoutValidation(is_valid=True)

        # Validate each page
        for page_idx, page in enumerate(layout.pages):
            # Check for duplicate widget IDs
            ids = set()
            for placement in page.placements:
                if placement.widget_id in ids:
                    validation.warnings.append(f"Duplicate widget ID: {placement.widget_id} on page {page_idx}")
                ids.add(placement.widget_id)

            # Check for widgets outside canvas
            for placement in page.placements:
                if placement.x < 0 or placement.y < 0:
                    validation.warnings.append(f"Widget {placement.widget_id} is outside canvas (x={placement.x}, y={placement.y})")
                if placement.x + placement.width > layout.canvas_width:
                    validation.warnings.append(f"Widget {placement.widget_id} extends beyond canvas width")
                if placement.y + placement.height > layout.canvas_height:
                    validation.warnings.append(f"Widget {placement.widget_id} extends beyond canvas height")

            # Check for overlapping widgets (simple check)
            placements = page.placements
            for i in range(len(placements)):
                for j in range(i + 1, len(placements)):
                    p1 = placements[i]
                    p2 = placements[j]
                    if (p1.x < p2.x + p2.width and
                        p1.x + p1.width > p2.x and
                        p1.y < p2.y + p2.height and
                        p1.y + p1.height > p2.y):
                        validation.warnings.append(f"Widgets {p1.widget_id} and {p2.widget_id} overlap")

        if validation.warnings:
            validation.is_valid = False

        return validation

    # ========================================================================
    # Diagnostics
    # ========================================================================

    def get_layout_report(self, name: str) -> Optional[LayoutReport]:
        """Get a diagnostic report for a layout."""
        layout = self.get_layout(name)
        if not layout:
            return None

        report = LayoutReport(
            canvas_width=layout.canvas_width,
            canvas_height=layout.canvas_height,
            region_count=len(layout.regions),
            page_count=len(layout.pages),
        )

        widget_count = 0
        overlaps = 0
        missing_bindings = 0

        for page in layout.pages:
            placements = page.placements
            widget_count += len(placements)

            # Check for overlaps
            for i in range(len(placements)):
                for j in range(i + 1, len(placements)):
                    p1 = placements[i]
                    p2 = placements[j]
                    if (p1.x < p2.x + p2.width and
                        p1.x + p1.width > p2.x and
                        p1.y < p2.y + p2.height and
                        p1.y + p1.height > p2.y):
                        overlaps += 1

            # Check for missing bindings
            for placement in placements:
                if not placement.binding or not placement.binding.get("controller_name"):
                    missing_bindings += 1

        report.widget_count = widget_count
        report.overlaps = overlaps
        report.missing_bindings = missing_bindings

        return report

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def get_layout(self, name: str) -> Optional[PickerLayout]:
        """Get a layout by name."""
        return self._layouts.get(name)

    def get_layout_by_index(self, index: int) -> Optional[PickerLayout]:
        """Get a layout by index."""
        keys = list(self._layouts.keys())
        if 0 <= index < len(keys):
            return self._layouts[keys[index]]
        return None

    def get_page_count(self, layout_name: str) -> int:
        """Get the number of pages in a layout."""
        layout = self.get_layout(layout_name)
        if not layout:
            return 0
        return len(layout.pages)

    def get_widget_count(self, layout_name: str, page_index: int = 0) -> int:
        """Get the number of widgets on a page."""
        layout = self.get_layout(layout_name)
        if not layout:
            return 0
        if page_index >= len(layout.pages):
            return 0
        return len(layout.pages[page_index].placements)

    def get_regions(self, layout_name: str) -> List[LayoutRegion]:
        """Get all regions in a layout."""
        layout = self.get_layout(layout_name)
        if not layout:
            return []
        return layout.regions

    def get_region_names(self, layout_name: str) -> List[str]:
        """Get all region names in a layout."""
        return [r.name for r in self.get_regions(layout_name)]

    def set_mode(self, mode: LayoutMode) -> None:
        """Set the layout mode."""
        self._mode = mode

    def get_mode(self) -> LayoutMode:
        """Get the current layout mode."""
        return self._mode

    def set_grid_size(self, size: float) -> None:
        """Set the grid size for snapping."""
        self._grid_size = max(1.0, size)

    def get_grid_size(self) -> float:
        """Get the current grid size."""
        return self._grid_size

    def set_snap_to_grid(self, enabled: bool) -> None:
        """Enable or disable snap to grid."""
        self._snap_to_grid = enabled

    def is_snap_to_grid(self) -> bool:
        """Check if snap to grid is enabled."""
        return self._snap_to_grid

    def snap_position(self, x: float, y: float) -> Tuple[float, float]:
        """Snap a position to the grid."""
        if not self._snap_to_grid:
            return (x, y)
        grid = self._grid_size
        return (round(x / grid) * grid, round(y / grid) * grid)

    # ========================================================================
    # Serialization
    # ========================================================================

    def to_json(self, layout_name: str) -> str:
        """Serialize a layout to JSON."""
        layout = self.get_layout(layout_name)
        if not layout:
            return "{}"
        return json.dumps(layout.to_dict(), indent=2)

    def from_json(self, json_str: str) -> Optional[PickerLayout]:
        """Deserialize a layout from JSON."""
        try:
            data = json.loads(json_str)
            layout = PickerLayout.from_dict(data)
            self._layouts[layout.name] = layout
            self._dirty = True
            return layout
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse layout JSON: {e}")
            return None

    def save_to_file(self, layout_name: str, filepath: str) -> bool:
        """Save a layout to a file."""
        layout = self.get_layout(layout_name)
        if not layout:
            return False
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(layout.to_dict(), f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to save layout: {e}")
            return False

    def load_from_file(self, filepath: str) -> Optional[PickerLayout]:
        """Load a layout from a file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            layout = PickerLayout.from_dict(data)
            self._layouts[layout.name] = layout
            self._dirty = True
            return layout
        except Exception as e:
            logger.error(f"Failed to load layout: {e}")
            return None

    def export_to_json(self, layout_name: str) -> str:
        """Export a layout to JSON string (alias for to_json)."""
        return self.to_json(layout_name)

    def import_from_json(self, json_str: str) -> Optional[PickerLayout]:
        """Import a layout from JSON string (alias for from_json)."""
        return self.from_json(json_str)


# ============================================================================
# Part 15: Public API
# ============================================================================

__all__ = [
    # Layout Manager
    "LayoutManager",
    # Data Models
    "PickerLayout",
    "LayoutPage",
    "LayoutRegion",
    "LayoutTemplate",
    "WidgetPlacement",
    "LayoutValidation",
    "LayoutReport",
    # Enums
    "LayoutType",
    "LayoutOrientation",
    "LayoutMode",
    "RegionType",
    "PlacementType",
    "ScalingMode",
    # Exceptions
    "LayoutError",
]

# ============================================================================
# End of layouts.py
# ============================================================================