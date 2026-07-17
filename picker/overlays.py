# -*- coding: utf-8 -*-
"""
maya_faceit.picker.overlays
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Real-time visual overlay engine for the Face Picker canvas.

This module provides non-interactive visual layers that communicate state,
feedback, and debugging information without changing the layout itself.

Overlays are analogous to Maya's viewport overlays, specialized for facial
animation workflows. They render on top of widgets to show selection,
hover, animation state, ARKit tracking, blendshape activity, debug info,
guides, grids, and more.

Design patterns:
- Composite: OverlayManager owns multiple overlay layers.
- Observer: Overlays listen to state changes and update accordingly.
- Strategy: Different rendering strategies can be enabled independently.
- Layered: Overlays have priorities (BACKGROUND, NORMAL, TOPMOST).

Estimated implementation size: 4,650–7,320 lines.
"""

import abc
import logging
import math
import weakref
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from PySide6 import QtCore, QtGui, QtWidgets # type: ignore

# -----------------------------------------------------------------------------
# Part 1 — Foundation
# -----------------------------------------------------------------------------

MODULE_NAME = "maya_faceit.picker.overlays"
__version__ = "1.0.0"
__author__ = "FaceIt Team"

# Configure logger
logger = logging.getLogger(MODULE_NAME)
logger.addHandler(logging.NullHandler())

# Dummy imports for dependencies (replace with actual modules)
# from . import widgets, themes, commands, preferences
# from .logger import get_logger
# from .math_utils import *


# -----------------------------------------------------------------------------
# Qt Graphics Helpers (simplified)
# -----------------------------------------------------------------------------
def qcolor_from_hex(hex_color: str, alpha: int = 255) -> QtGui.QColor:
    """Convert a hex color string to QColor."""
    return QtGui.QColor(hex_color)


def qpen_from_style(style: Dict[str, Any]) -> QtGui.QPen:
    """Create a QPen from a style dictionary."""
    pen = QtGui.QPen()
    if "color" in style:
        pen.setColor(qcolor_from_hex(style["color"]))
    if "width" in style:
        pen.setWidth(style["width"])
    if "style" in style:
        pen.setStyle(getattr(QtCore.Qt, style["style"], QtCore.Qt.SolidLine))
    return pen


def qbrush_from_style(style: Dict[str, Any]) -> QtGui.QBrush:
    """Create a QBrush from a style dictionary."""
    brush = QtGui.QBrush()
    if "color" in style:
        brush.setColor(qcolor_from_hex(style["color"]))
    if "style" in style:
        brush.setStyle(getattr(QtCore.Qt, style["style"], QtCore.Qt.SolidPattern))
    return brush


# -----------------------------------------------------------------------------
# Overlay Registry (simple in-memory store)
# -----------------------------------------------------------------------------
_OVERLAY_REGISTRY: Dict[str, type] = {}


def register_overlay(name: str, overlay_cls: type) -> None:
    """Register an overlay class by name."""
    _OVERLAY_REGISTRY[name] = overlay_cls


def get_registered_overlay(name: str) -> Optional[type]:
    """Retrieve a registered overlay class."""
    return _OVERLAY_REGISTRY.get(name)


# -----------------------------------------------------------------------------
# Part 2 — Constants & Enumerations
# -----------------------------------------------------------------------------

class OverlayType(Enum):
    """Categorization of overlays for management and visibility toggling."""
    SELECTION = auto()
    HOVER = auto()
    REGION = auto()
    GRID = auto()
    GUIDES = auto()
    ANIMATION = auto()
    BLENDSHAPE = auto()
    ARKIT = auto()
    DEBUG = auto()
    WARNING = auto()
    STATUS = auto()
    LOCK = auto()
    PIN = auto()
    PERFORMANCE = auto()


class OverlayState(Enum):
    """State of an individual overlay."""
    VISIBLE = auto()
    HIDDEN = auto()
    LOCKED = auto()    # Visible but cannot be toggled off
    DISABLED = auto()  # Not rendered regardless of visibility


class OverlayPriority(Enum):
    """Rendering order. Higher priority renders on top."""
    BACKGROUND = 0
    LOW = 10
    NORMAL = 20
    HIGH = 30
    TOPMOST = 40


# -----------------------------------------------------------------------------
# Part 3 — Data Models (dataclasses)
# -----------------------------------------------------------------------------

@dataclass
class OverlayStyle:
    """Visual style attributes for an overlay."""
    fill_color: Optional[str] = None
    fill_alpha: float = 1.0
    outline_color: Optional[str] = None
    outline_width: float = 1.0
    outline_alpha: float = 1.0
    glow_color: Optional[str] = None
    glow_radius: float = 0.0
    glow_alpha: float = 1.0
    text_color: Optional[str] = None
    font_family: str = "Arial"
    font_size: int = 10
    font_bold: bool = False
    corner_radius: float = 0.0
    dash_pattern: Tuple[float, ...] = ()
    # Additional custom properties
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OverlayRegion:
    """Defines a rectangular region or shape for overlay drawing."""
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0
    shape: str = "rect"  # "rect", "ellipse", "polygon"
    points: List[Tuple[float, float]] = field(default_factory=list)


@dataclass
class OverlayIndicator:
    """A simple indicator (like a dot or icon) placed within an overlay."""
    position: Tuple[float, float] = (0.0, 0.0)
    color: str = "#ffffff"
    size: float = 6.0
    shape: str = "circle"  # "circle", "square", "triangle"
    label: str = ""


@dataclass
class OverlayStatistics:
    """Performance and rendering stats for debugging."""
    fps: float = 0.0
    update_time_ms: float = 0.0
    render_time_ms: float = 0.0
    overlay_count: int = 0
    visible_count: int = 0
    last_frame_duration: float = 0.0


@dataclass
class OverlayConfiguration:
    """Global configuration for the overlay system."""
    default_opacity: float = 0.8
    use_animations: bool = True
    animation_duration_ms: int = 200
    show_debug_labels: bool = False
    enable_gpu_acceleration: bool = True
    max_overlay_updates_per_second: int = 60
    layer_visibility: Dict[OverlayType, bool] = field(default_factory=dict)


@dataclass
class Overlay:
    """Base data structure for an overlay instance."""
    id: str
    type: OverlayType
    priority: OverlayPriority = OverlayPriority.NORMAL
    state: OverlayState = OverlayState.VISIBLE
    opacity: float = 0.8
    style: Optional[OverlayStyle] = None
    regions: List[OverlayRegion] = field(default_factory=list)
    indicators: List[OverlayIndicator] = field(default_factory=list)
    text: Optional[str] = None
    tooltip: Optional[str] = None
    widget_ref: Optional[weakref.ReferenceType] = None
    data: Dict[str, Any] = field(default_factory=dict)

    def is_visible(self) -> bool:
        """Check if overlay should be rendered."""
        return self.state == OverlayState.VISIBLE or self.state == OverlayState.LOCKED


# -----------------------------------------------------------------------------
# Part 14 — Utilities
# -----------------------------------------------------------------------------

def blend_colors(c1: QtGui.QColor, c2: QtGui.QColor, t: float) -> QtGui.QColor:
    """Linearly interpolate between two QColors."""
    r = int(c1.red() + (c2.red() - c1.red()) * t)
    g = int(c1.green() + (c2.green() - c1.green()) * t)
    b = int(c1.blue() + (c2.blue() - c1.blue()) * t)
    a = int(c1.alpha() + (c2.alpha() - c1.alpha()) * t)
    return QtGui.QColor(r, g, b, a)


def apply_opacity(color: QtGui.QColor, opacity: float) -> QtGui.QColor:
    """Apply global opacity to a QColor."""
    color = QtGui.QColor(color)
    color.setAlpha(int(color.alpha() * opacity))
    return color


def sort_overlays_by_priority(overlays: List['Overlay']) -> List['Overlay']:
    """Sort overlays by priority (ascending)."""
    return sorted(overlays, key=lambda o: o.priority.value)


def point_in_rect(point: Tuple[float, float], rect: QtCore.QRectF) -> bool:
    """Test if a point is inside a QRectF."""
    return rect.contains(point[0], point[1])


def point_in_ellipse(point: Tuple[float, float], center: Tuple[float, float], rx: float, ry: float) -> bool:
    """Test if a point is inside an ellipse."""
    x, y = point
    cx, cy = center
    return ((x - cx) ** 2 / (rx ** 2) + (y - cy) ** 2 / (ry ** 2)) <= 1


def get_region_bounds(region: OverlayRegion) -> QtCore.QRectF:
    """Convert an OverlayRegion to QRectF."""
    return QtCore.QRectF(region.x, region.y, region.width, region.height)


# -----------------------------------------------------------------------------
# Part 13 — Validation
# -----------------------------------------------------------------------------

@dataclass
class OverlayValidation:
    """Result of validating an overlay system state."""
    valid: bool = True
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


def validate_overlay_system(overlays: List[Overlay]) -> OverlayValidation:
    """Validate the consistency of overlays."""
    errors = []
    warnings = []
    ids = set()
    for overlay in overlays:
        if overlay.id in ids:
            errors.append(f"Duplicate overlay ID: {overlay.id}")
        ids.add(overlay.id)

        if overlay.priority not in OverlayPriority:
            warnings.append(f"Invalid priority for overlay {overlay.id}: {overlay.priority}")

        if overlay.type not in OverlayType:
            warnings.append(f"Invalid type for overlay {overlay.id}: {overlay.type}")

        if overlay.state not in OverlayState:
            warnings.append(f"Invalid state for overlay {overlay.id}: {overlay.state}")

        if overlay.widget_ref is not None and overlay.widget_ref() is None:
            warnings.append(f"Widget reference for overlay {overlay.id} is dead")

    return OverlayValidation(valid=len(errors) == 0, warnings=warnings, errors=errors)


# -----------------------------------------------------------------------------
# Part 4 — Overlay Manager (Main Controller)
# -----------------------------------------------------------------------------

class OverlayManager(QtCore.QObject):
    """
    Manages all overlays, coordinating updates, rendering, and visibility.
    Emits signals when overlays change.
    """

    overlay_added = QtCore.Signal(str)
    overlay_removed = QtCore.Signal(str)
    overlay_updated = QtCore.Signal(str)
    overlay_state_changed = QtCore.Signal(str, OverlayState)
    all_overlays_cleared = QtCore.Signal()

    def __init__(self, parent: Optional[QtCore.QObject] = None):
        super().__init__(parent)
        self._overlays: Dict[str, Overlay] = {}
        self._config = OverlayConfiguration()
        self._dirty = False
        self._update_timer = QtCore.QTimer(self)
        self._update_timer.setInterval(1000 // 60)  # 60 fps
        self._update_timer.timeout.connect(self._tick)
        self._statistics = OverlayStatistics()

    def _tick(self):
        """Internal timer tick to trigger updates if dirty."""
        if self._dirty:
            self._dirty = False
            self.render()

    # ---------- Public API ----------
    def show(self, overlay_id: str) -> bool:
        """Show an overlay."""
        overlay = self._overlays.get(overlay_id)
        if overlay and overlay.state != OverlayState.LOCKED:
            overlay.state = OverlayState.VISIBLE
            self.overlay_state_changed.emit(overlay_id, overlay.state)
            self._mark_dirty()
            return True
        return False

    def hide(self, overlay_id: str) -> bool:
        """Hide an overlay."""
        overlay = self._overlays.get(overlay_id)
        if overlay and overlay.state != OverlayState.LOCKED:
            overlay.state = OverlayState.HIDDEN
            self.overlay_state_changed.emit(overlay_id, overlay.state)
            self._mark_dirty()
            return True
        return False

    def toggle(self, overlay_id: str) -> bool:
        """Toggle visibility of an overlay."""
        overlay = self._overlays.get(overlay_id)
        if overlay and overlay.state != OverlayState.LOCKED:
            if overlay.state == OverlayState.VISIBLE:
                overlay.state = OverlayState.HIDDEN
            else:
                overlay.state = OverlayState.VISIBLE
            self.overlay_state_changed.emit(overlay_id, overlay.state)
            self._mark_dirty()
            return True
        return False

    def refresh(self):
        """Force a full update and render pass."""
        self._dirty = True
        self._tick()

    def register(self, overlay: Overlay) -> bool:
        """Register a new overlay. Replaces if ID exists."""
        if overlay.id in self._overlays:
            logger.warning(f"Overlay {overlay.id} already registered. Replacing.")
        self._overlays[overlay.id] = overlay
        self.overlay_added.emit(overlay.id)
        self._mark_dirty()
        return True

    def unregister(self, overlay_id: str) -> bool:
        """Remove an overlay."""
        if overlay_id in self._overlays:
            del self._overlays[overlay_id]
            self.overlay_removed.emit(overlay_id)
            self._mark_dirty()
            return True
        return False

    def clear(self):
        """Remove all overlays."""
        self._overlays.clear()
        self.all_overlays_cleared.emit()
        self._mark_dirty()

    def update(self, overlay_id: str, **kwargs):
        """Update attributes of an existing overlay."""
        overlay = self._overlays.get(overlay_id)
        if overlay:
            for key, value in kwargs.items():
                if hasattr(overlay, key):
                    setattr(overlay, key, value)
            self.overlay_updated.emit(overlay_id)
            self._mark_dirty()
            return True
        return False

    def render(self):
        """Perform the actual rendering of overlays."""
        # In a real Qt implementation, this would trigger a repaint of the graphics scene.
        # For this module, we simulate by updating internal state.
        self._statistics.render_time_ms = 0.0
        visible = [o for o in self._overlays.values() if o.is_visible()]
        sorted_visible = sort_overlays_by_priority(visible)
        self._statistics.visible_count = len(sorted_visible)
        self._statistics.overlay_count = len(self._overlays)
        # Emit a signal or call a callback to notify the view to repaint.
        # For now, we just log.
        logger.debug(f"Rendering {len(sorted_visible)} visible overlays")

    # ---------- Internal helpers ----------
    def _mark_dirty(self):
        """Mark the overlay system as dirty, scheduling an update."""
        self._dirty = True
        if not self._update_timer.isActive():
            self._update_timer.start()

    # ---------- Configuration ----------
    def set_configuration(self, config: OverlayConfiguration):
        self._config = config

    def get_configuration(self) -> OverlayConfiguration:
        return self._config

    # ---------- Statistics ----------
    def get_statistics(self) -> OverlayStatistics:
        return self._statistics


# -----------------------------------------------------------------------------
# Part 5 — Selection Overlays
# -----------------------------------------------------------------------------

class SelectionOverlay(Overlay):
    """Renders a glowing outline or fill around selected widgets."""

    def __init__(self, widget_ref: weakref.ReferenceType, color: str = "#00aaff",
                 glow: bool = True, outline: bool = True, fill: bool = False,
                 pulse: bool = True):
        style = OverlayStyle(
            outline_color=color,
            outline_width=2.0,
            glow_color=color,
            glow_radius=10.0,
            glow_alpha=0.5,
            fill_color=color if fill else None,
            fill_alpha=0.2,
        )
        super().__init__(
            id=f"selection_{id(widget_ref())}",
            type=OverlayType.SELECTION,
            priority=OverlayPriority.HIGH,
            state=OverlayState.VISIBLE,
            style=style,
            widget_ref=widget_ref,
            data={"pulse": pulse, "glow": glow, "outline": outline, "fill": fill}
        )


# -----------------------------------------------------------------------------
# Part 6 — Hover Overlays
# -----------------------------------------------------------------------------

class HoverOverlay(Overlay):
    """Highlights the widget under the mouse cursor."""

    def __init__(self, widget_ref: weakref.ReferenceType, color: str = "#ffaa00"):
        style = OverlayStyle(
            outline_color=color,
            outline_width=1.5,
            glow_color=color,
            glow_radius=5.0,
            glow_alpha=0.3,
            fill_alpha=0.0,
        )
        super().__init__(
            id=f"hover_{id(widget_ref())}",
            type=OverlayType.HOVER,
            priority=OverlayPriority.HIGH,
            state=OverlayState.VISIBLE,
            style=style,
            widget_ref=widget_ref,
        )


# -----------------------------------------------------------------------------
# Part 7 — Region Overlays
# -----------------------------------------------------------------------------

class RegionOverlay(Overlay):
    """Displays predefined facial regions with labels and boundaries."""

    def __init__(self, region_name: str, bounds: QtCore.QRectF,
                 color: str = "#88aaff", label: str = ""):
        region = OverlayRegion(
            x=bounds.x(), y=bounds.y(),
            width=bounds.width(), height=bounds.height(),
            shape="rect"
        )
        style = OverlayStyle(
            outline_color=color,
            outline_width=1.0,
            outline_alpha=0.6,
            fill_alpha=0.1,
            text_color=color,
            font_size=8,
            font_bold=True,
        )
        super().__init__(
            id=f"region_{region_name}",
            type=OverlayType.REGION,
            priority=OverlayPriority.LOW,
            state=OverlayState.VISIBLE,
            style=style,
            regions=[region],
            text=label or region_name,
        )


# -----------------------------------------------------------------------------
# Part 8 — Animation Overlays
# -----------------------------------------------------------------------------

class AnimationOverlay(Overlay):
    """
    Displays animation state indicators such as keyframes, driven status,
    and muted controls.
    """

    def __init__(self, widget_ref: weakref.ReferenceType, has_key: bool = False,
                 is_driven: bool = False, is_muted: bool = False,
                 key_color: str = "#ff0000", driven_color: str = "#00ff00",
                 muted_color: str = "#888888"):
        indicators = []
        if has_key:
            indicators.append(OverlayIndicator(
                position=(0, 0), color=key_color, size=8, shape="circle", label="K"
            ))
        if is_driven:
            indicators.append(OverlayIndicator(
                position=(10, 0), color=driven_color, size=6, shape="square", label="D"
            ))
        if is_muted:
            indicators.append(OverlayIndicator(
                position=(20, 0), color=muted_color, size=6, shape="triangle", label="M"
            ))
        super().__init__(
            id=f"anim_{id(widget_ref())}",
            type=OverlayType.ANIMATION,
            priority=OverlayPriority.HIGH,
            state=OverlayState.VISIBLE,
            indicators=indicators,
            widget_ref=widget_ref,
        )


# -----------------------------------------------------------------------------
# Part 9 — ARKit Overlays
# -----------------------------------------------------------------------------

class ARKitOverlay(Overlay):
    """
    Displays live ARKit tracking information, including blendshape weights,
    confidence, and landmark locations.
    """

    def __init__(self, widget_ref: weakref.ReferenceType,
                 blendshape_weights: Dict[str, float],
                 confidence: float = 0.0,
                 tracking_quality: str = "good"):
        indicators = []
        for i, (name, weight) in enumerate(list(blendshape_weights.items())[:3]):
            color = "#00ff00" if weight > 0.5 else "#ffaa00"
            indicators.append(OverlayIndicator(
                position=(0, i*12), color=color, size=6, shape="circle",
                label=f"{name}: {weight:.2f}"
            ))
        indicators.append(OverlayIndicator(
            position=(0, len(indicators)*12), color="#ffffff", size=4,
            shape="square", label=f"Conf: {confidence:.2f} | Qual: {tracking_quality}"
        ))
        style = OverlayStyle(
            text_color="#ffffff",
            font_size=9,
            font_bold=False,
            fill_color="#000000",
            fill_alpha=0.4,
            corner_radius=4,
        )
        super().__init__(
            id=f"arkit_{id(widget_ref())}",
            type=OverlayType.ARKIT,
            priority=OverlayPriority.HIGH,
            state=OverlayState.VISIBLE,
            style=style,
            indicators=indicators,
            widget_ref=widget_ref,
        )


# -----------------------------------------------------------------------------
# Part 10 — Blendshape Overlays
# -----------------------------------------------------------------------------

class BlendshapeOverlay(Overlay):
    """
    Visualizes blendshape activity with heatmap-like fills and weight labels.
    """

    def __init__(self, widget_ref: weakref.ReferenceType,
                 blendshape_name: str,
                 weight: float,
                 max_weight: float = 1.0,
                 color_positive: str = "#00ff88",
                 color_negative: str = "#ff4488"):
        normalized = weight / max_weight if max_weight != 0 else 0
        if normalized > 0:
            fill_color = color_positive
        else:
            fill_color = color_negative
        alpha = min(abs(normalized), 1.0) * 0.7
        style = OverlayStyle(
            fill_color=fill_color,
            fill_alpha=alpha,
            text_color="#ffffff",
            font_size=10,
            font_bold=True,
        )
        text = f"{blendshape_name}: {weight:.2f}"
        super().__init__(
            id=f"blendshape_{blendshape_name}",
            type=OverlayType.BLENDSHAPE,
            priority=OverlayPriority.HIGH,
            state=OverlayState.VISIBLE,
            style=style,
            text=text,
            widget_ref=widget_ref,
        )


# -----------------------------------------------------------------------------
# Part 11 — Debug Overlays
# -----------------------------------------------------------------------------

class DebugOverlay(Overlay):
    """
    Shows debugging information such as widget IDs, controller names,
    bounding boxes, FPS, update times, and warnings.
    """

    def __init__(self, widget_ref: weakref.ReferenceType,
                 debug_info: Dict[str, str]):
        lines = "\n".join(f"{k}: {v}" for k, v in debug_info.items())
        style = OverlayStyle(
            text_color="#ffff00",
            font_size=8,
            font_family="Courier",
            fill_color="#000000",
            fill_alpha=0.7,
            outline_color="#ff0000",
            outline_width=1,
        )
        super().__init__(
            id=f"debug_{id(widget_ref())}",
            type=OverlayType.DEBUG,
            priority=OverlayPriority.TOPMOST,
            state=OverlayState.VISIBLE,
            style=style,
            text=lines,
            widget_ref=widget_ref,
        )


# -----------------------------------------------------------------------------
# Part 12 — Guides & Grids
# -----------------------------------------------------------------------------

class GridOverlay(Overlay):
    """Renders a grid on the canvas for alignment."""

    def __init__(self, bounds: QtCore.QRectF, spacing: float = 20.0,
                 color: str = "#888888", show_center: bool = True):
        # We store grid parameters in regions/extra
        style = OverlayStyle(
            outline_color=color,
            outline_alpha=0.3,
            glow_color=color,
            glow_alpha=0.1,
        )
        super().__init__(
            id="grid",
            type=OverlayType.GRID,
            priority=OverlayPriority.BACKGROUND,
            state=OverlayState.VISIBLE,
            style=style,
            data={"spacing": spacing, "bounds": bounds, "show_center": show_center}
        )


class GuideOverlay(Overlay):
    """Shows alignment guides like center lines, rule of thirds, safe margins."""

    def __init__(self, bounds: QtCore.QRectF, guides: List[str],
                 color: str = "#44aaff"):
        style = OverlayStyle(
            outline_color=color,
            outline_alpha=0.5,
            dash_pattern=(5, 5),
        )
        super().__init__(
            id="guides",
            type=OverlayType.GUIDES,
            priority=OverlayPriority.LOW,
            state=OverlayState.VISIBLE,
            style=style,
            data={"bounds": bounds, "guides": guides}
        )


# -----------------------------------------------------------------------------
# Part 15 — Public API (global instance and convenience functions)
# -----------------------------------------------------------------------------

# Global overlay manager instance (singleton)
_global_manager: Optional[OverlayManager] = None


def get_overlay_manager() -> OverlayManager:
    """Get or create the global overlay manager."""
    global _global_manager
    if _global_manager is None:
        _global_manager = OverlayManager()
    return _global_manager


# Convenience functions for common operations
def show_overlay(overlay_id: str) -> bool:
    return get_overlay_manager().show(overlay_id)


def hide_overlay(overlay_id: str) -> bool:
    return get_overlay_manager().hide(overlay_id)


def toggle_overlay(overlay_id: str) -> bool:
    return get_overlay_manager().toggle(overlay_id)


def register_overlay_instance(overlay: Overlay) -> bool:
    return get_overlay_manager().register(overlay)


def refresh_overlays():
    get_overlay_manager().refresh()


# -----------------------------------------------------------------------------
# Example usage / self-test (if run standalone)
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    # Minimal test
    import sys

    app = QtWidgets.QApplication(sys.argv)

    mgr = get_overlay_manager()
    # Create a mock widget ref
    dummy_widget = QtWidgets.QWidget()
    ref = weakref.ref(dummy_widget)

    sel = SelectionOverlay(ref)
    mgr.register(sel)

    hover = HoverOverlay(ref)
    mgr.register(hover)

    grid = GridOverlay(QtCore.QRectF(0, 0, 500, 500))
    mgr.register(grid)

    # Print state
    print(f"Registered overlays: {mgr._overlays.keys()}")
    mgr.refresh()

    # Toggle grid
    mgr.toggle("grid")
    print("Grid toggled")

    # Cleanup
    app.exec()