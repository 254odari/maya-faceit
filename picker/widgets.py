"""
maya_faceit.picker.widgets

Widget Framework for the Facial Control Picker.

This module provides a complete custom graphics framework built on
PySide6 QGraphicsScene/QGraphicsItem, optimized for Maya facial animation.
All interactive elements in the picker derive from these classes.

Author: Maya FaceIT Team
"""

from __future__ import annotations
import os
import logging
import math
import json
import hashlib
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Optional, Dict, List, Any, Callable, Tuple, Union, Set

# Qt imports
try:
    from PySide6 import QtCore, QtGui, QtWidgets # type: ignore
    from PySide6.QtCore import Qt, Signal, Slot, QObject, QTimer, QPropertyAnimation, QEasingCurve, QPointF, QRectF # type: ignore
    from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QPixmap, QImage, QPainterPath, QTransform # type: ignore
    from shiboken6 import wrapInstance # type: ignore
except ImportError:
    try:
        from PySide2 import QtCore, QtGui, QtWidgets # type: ignore
        from PySide2.QtCore import Qt, Signal, Slot, QObject, QTimer, QPropertyAnimation, QEasingCurve, QPointF, QRectF # type: ignore
        from PySide2.QtGui import QPainter, QPen, QBrush, QColor, QPixmap, QImage, QPainterPath, QTransform # type: ignore
        from shiboken2 import wrapInstance # type: ignore
    except ImportError:
        raise ImportError("No Qt binding found (PySide6 or PySide2).")

# Maya imports
try:
    import maya.cmds as cmds # type: ignore
except ImportError:
    cmds = None

logger = logging.getLogger(__name__)

# ============================================================================
# Part 1: Foundation
# ============================================================================

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"

# ============================================================================
# Part 2: Constants & Enumerations
# ============================================================================

class WidgetType(Enum):
    """Types of picker widgets."""
    BUTTON = "button"
    CIRCLE = "circle"
    RECTANGLE = "rectangle"
    POLYGON = "polygon"
    SLIDER = "slider"
    JOYSTICK = "joystick"
    IMAGE = "image"
    TEXT = "text"
    ICON = "icon"
    REGION = "region"
    BACKGROUND = "background"
    SELECTION = "selection"


class WidgetState(Enum):
    """State of a widget."""
    NORMAL = "normal"
    HOVER = "hover"
    PRESSED = "pressed"
    SELECTED = "selected"
    LOCKED = "locked"
    DISABLED = "disabled"
    HIDDEN = "hidden"
    FAVORITE = "favorite"
    PINNED = "pinned"


class WidgetAlignment(Enum):
    """Alignment for text and content."""
    LEFT = "left"
    RIGHT = "right"
    TOP = "top"
    BOTTOM = "bottom"
    CENTER = "center"
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"


class SliderOrientation(Enum):
    """Slider orientation."""
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    RADIAL = "radial"


class AnimationType(Enum):
    """Animation types for widgets."""
    NONE = "none"
    FADE = "fade"
    SCALE = "scale"
    PULSE = "pulse"
    GLOW = "glow"
    HIGHLIGHT = "highlight"
    SELECTION_FLASH = "selection_flash"
    HOVER_GLOW = "hover_glow"


# ============================================================================
# Part 3: Widget Data Models
# ============================================================================

@dataclass
class WidgetStyle:
    """Style definition for a widget."""
    fill_color: Tuple[int, int, int] = (80, 80, 80)
    fill_color_hover: Tuple[int, int, int] = (120, 120, 120)
    fill_color_pressed: Tuple[int, int, int] = (100, 100, 150)
    fill_color_selected: Tuple[int, int, int] = (200, 200, 50)
    fill_color_locked: Tuple[int, int, int] = (60, 60, 60)
    fill_color_disabled: Tuple[int, int, int] = (40, 40, 40)
    border_color: Tuple[int, int, int] = (0, 0, 0)
    border_color_hover: Tuple[int, int, int] = (100, 100, 200)
    border_color_selected: Tuple[int, int, int] = (255, 255, 100)
    border_width: float = 1.0
    corner_radius: float = 4.0
    text_color: Tuple[int, int, int] = (255, 255, 255)
    text_color_hover: Tuple[int, int, int] = (255, 255, 255)
    text_color_selected: Tuple[int, int, int] = (0, 0, 0)
    font_family: str = "Segoe UI"
    font_size: int = 10
    font_weight: int = 400
    opacity: float = 1.0
    opacity_hover: float = 1.0
    opacity_selected: float = 1.0
    opacity_disabled: float = 0.5
    shadow_enabled: bool = False
    shadow_color: Tuple[int, int, int] = (0, 0, 0, 50)
    shadow_offset: Tuple[float, float] = (2.0, 2.0)
    shadow_blur: float = 4.0
    glow_enabled: bool = False
    glow_color: Tuple[int, int, int] = (100, 100, 255)
    glow_radius: float = 10.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fill_color": self.fill_color,
            "fill_color_hover": self.fill_color_hover,
            "fill_color_pressed": self.fill_color_pressed,
            "fill_color_selected": self.fill_color_selected,
            "fill_color_locked": self.fill_color_locked,
            "fill_color_disabled": self.fill_color_disabled,
            "border_color": self.border_color,
            "border_color_hover": self.border_color_hover,
            "border_color_selected": self.border_color_selected,
            "border_width": self.border_width,
            "corner_radius": self.corner_radius,
            "text_color": self.text_color,
            "text_color_hover": self.text_color_hover,
            "text_color_selected": self.text_color_selected,
            "font_family": self.font_family,
            "font_size": self.font_size,
            "font_weight": self.font_weight,
            "opacity": self.opacity,
            "opacity_hover": self.opacity_hover,
            "opacity_selected": self.opacity_selected,
            "opacity_disabled": self.opacity_disabled,
            "shadow_enabled": self.shadow_enabled,
            "shadow_color": self.shadow_color,
            "shadow_offset": self.shadow_offset,
            "shadow_blur": self.shadow_blur,
            "glow_enabled": self.glow_enabled,
            "glow_color": self.glow_color,
            "glow_radius": self.glow_radius,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WidgetStyle':
        return cls(**data)


@dataclass
class WidgetGeometry:
    """Geometry of a widget."""
    x: float = 0.0
    y: float = 0.0
    width: float = 50.0
    height: float = 50.0
    rotation: float = 0.0
    scale: float = 1.0

    @property
    def center(self) -> Tuple[float, float]:
        return (self.x + self.width / 2, self.y + self.height / 2)

    @property
    def rect(self) -> QRectF:
        return QRectF(self.x, self.y, self.width, self.height)

    def contains(self, px: float, py: float) -> bool:
        return self.x <= px <= self.x + self.width and self.y <= py <= self.y + self.height

    def to_dict(self) -> Dict[str, Any]:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "rotation": self.rotation,
            "scale": self.scale,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WidgetGeometry':
        return cls(**data)


@dataclass
class WidgetBinding:
    """Binding to a Maya controller."""
    controller_name: str = ""
    attribute: str = ""
    channel: str = ""
    mapping: Optional[Dict[str, float]] = None
    multiplier: float = 1.0
    offset: float = 0.0
    clamp_min: Optional[float] = None
    clamp_max: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "controller_name": self.controller_name,
            "attribute": self.attribute,
            "channel": self.channel,
            "mapping": self.mapping,
            "multiplier": self.multiplier,
            "offset": self.offset,
            "clamp_min": self.clamp_min,
            "clamp_max": self.clamp_max,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WidgetBinding':
        return cls(**data)


@dataclass
class WidgetAnimation:
    """Animation definition for a widget."""
    animation_type: AnimationType = AnimationType.NONE
    duration: int = 300  # ms
    easing: str = "in_out_quad"
    start_value: float = 0.0
    end_value: float = 1.0
    loop: bool = False
    auto_start: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "animation_type": self.animation_type.value,
            "duration": self.duration,
            "easing": self.easing,
            "start_value": self.start_value,
            "end_value": self.end_value,
            "loop": self.loop,
            "auto_start": self.auto_start,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WidgetAnimation':
        return cls(**data)


@dataclass
class WidgetMetadata:
    """Metadata for a widget."""
    id: str = ""
    name: str = ""
    description: str = ""
    tags: List[str] = field(default_factory=list)
    version: str = "1.0"
    author: str = "unknown"
    created: str = ""
    modified: str = ""
    custom_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "tags": self.tags,
            "version": self.version,
            "author": self.author,
            "created": self.created,
            "modified": self.modified,
            "custom_data": self.custom_data,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WidgetMetadata':
        return cls(**data)


# ============================================================================
# Part 4: Base Widget Classes
# ============================================================================

class PickerWidget(QtWidgets.QGraphicsObject):
    """
    Base class for all picker widgets.

    This is the foundation of the widget framework.
    All visual elements derive from this class.
    """

    # Signals
    clicked = Signal(object)
    double_clicked = Signal(object)
    hover_entered = Signal(object)
    hover_left = Signal(object)
    pressed = Signal(object)
    released = Signal(object)
    moved = Signal(object)
    resized = Signal(object)
    state_changed = Signal(WidgetState, WidgetState)

    def __init__(
        self,
        parent: Optional[QtWidgets.QGraphicsItem] = None,
        geometry: Optional[WidgetGeometry] = None,
        style: Optional[WidgetStyle] = None,
        binding: Optional[WidgetBinding] = None,
        metadata: Optional[WidgetMetadata] = None,
    ):
        super().__init__(parent)

        # --- Core Properties ---
        self._geometry = geometry or WidgetGeometry()
        self._style = style or WidgetStyle()
        self._binding = binding or WidgetBinding()
        self._metadata = metadata or WidgetMetadata()
        self._state = WidgetState.NORMAL
        self._widget_type = WidgetType.BUTTON
        self._enabled = True
        self._visible = True
        self._selectable = True
        self._movable = False
        self._resizable = False
        self._locked = False
        self._selected = False
        self._hover = False
        self._pressed_state = False

        # --- Animation ---
        self._animations: Dict[str, QPropertyAnimation] = {}
        self._default_animation = WidgetAnimation()

        # --- Caching ---
        self._bounding_rect_cache = None
        self._shape_cache = None
        self._pixmap_cache = None

        # --- Flags ---
        self.setFlags(
            QtWidgets.QGraphicsItem.ItemIsSelectable |
            QtWidgets.QGraphicsItem.ItemIsMovable |
            QtWidgets.QGraphicsItem.ItemSendsGeometryChanges |
            QtWidgets.QGraphicsItem.ItemSendsScenePositionChanges
        )
        self.setAcceptHoverEvents(True)
        self.setCacheMode(QtWidgets.QGraphicsItem.DeviceCoordinateCache)

        # --- Connection to Maya ---
        self._maya_value = 0.0
        self._maya_connection = None

        # --- Init ---
        self._init_animations()

    # ========================================================================
    # Geometry
    # ========================================================================

    def set_geometry(self, geometry: WidgetGeometry) -> None:
        self._geometry = geometry
        self.update_geometry()
        self.resized.emit(self)

    def get_geometry(self) -> WidgetGeometry:
        return self._geometry

    def set_position(self, x: float, y: float) -> None:
        self._geometry.x = x
        self._geometry.y = y
        self.setPos(x, y)

    def set_size(self, width: float, height: float) -> None:
        self._geometry.width = width
        self._geometry.height = height
        self.prepareGeometryChange()
        self._bounding_rect_cache = None
        self._shape_cache = None
        self.resized.emit(self)

    def get_center(self) -> QPointF:
        return QPointF(
            self._geometry.x + self._geometry.width / 2,
            self._geometry.y + self._geometry.height / 2
        )

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self._geometry.width, self._geometry.height)

    def shape(self) -> QPainterPath:
        if self._shape_cache is None:
            path = QPainterPath()
            path.addRect(self.boundingRect())
            self._shape_cache = path
        return self._shape_cache

    # ========================================================================
    # Style
    # ========================================================================

    def set_style(self, style: WidgetStyle) -> None:
        self._style = style
        self.update()

    def get_style(self) -> WidgetStyle:
        return self._style

    def set_color(self, r: int, g: int, b: int) -> None:
        self._style.fill_color = (r, g, b)
        self.update()

    def set_border_color(self, r: int, g: int, b: int) -> None:
        self._style.border_color = (r, g, b)
        self.update()

    def set_text_color(self, r: int, g: int, b: int) -> None:
        self._style.text_color = (r, g, b)
        self.update()

    def set_opacity(self, opacity: float) -> None:
        self._style.opacity = max(0.0, min(1.0, opacity))
        self.update()

    # ========================================================================
    # State
    # ========================================================================

    def set_state(self, state: WidgetState) -> None:
        old_state = self._state
        if old_state != state:
            self._state = state
            self.state_changed.emit(old_state, state)
            self.update()

    def get_state(self) -> WidgetState:
        return self._state

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        if not enabled:
            self.set_state(WidgetState.DISABLED)
        else:
            self.set_state(WidgetState.NORMAL)

    def is_enabled(self) -> bool:
        return self._enabled

    def set_visible(self, visible: bool) -> None:
        self._visible = visible
        self.setVisible(visible)

    def is_visible(self) -> bool:
        return self._visible

    def set_selectable(self, selectable: bool) -> None:
        self._selectable = selectable
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, selectable)

    def set_movable(self, movable: bool) -> None:
        self._movable = movable
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, movable)

    def set_locked(self, locked: bool) -> None:
        self._locked = locked
        if locked:
            self.set_state(WidgetState.LOCKED)
        else:
            self.set_state(WidgetState.NORMAL)

    def is_locked(self) -> bool:
        return self._locked

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        if selected:
            self.set_state(WidgetState.SELECTED)
        else:
            self.set_state(WidgetState.NORMAL)

    def is_selected(self) -> bool:
        return self._selected

    # ========================================================================
    # Binding
    # ========================================================================

    def set_binding(self, binding: WidgetBinding) -> None:
        self._binding = binding
        self._connect_to_maya()

    def get_binding(self) -> WidgetBinding:
        return self._binding

    def set_controller(self, controller_name: str) -> None:
        self._binding.controller_name = controller_name
        self._connect_to_maya()

    def get_controller(self) -> str:
        return self._binding.controller_name

    def _connect_to_maya(self) -> None:
        """Connect to Maya controller attribute."""
        if not cmds or not self._binding.controller_name:
            return
        # We'll use a simple connection; in production we'd use callbacks
        if cmds.objExists(self._binding.controller_name):
            # Store the connection for updates
            pass

    def update_from_maya(self) -> None:
        """Update widget state from Maya controller value."""
        if not cmds or not self._binding.controller_name:
            return
        if cmds.objExists(self._binding.controller_name):
            # Get value from controller
            pass

    def apply_to_maya(self) -> None:
        """Apply widget state to Maya controller."""
        if not cmds or not self._binding.controller_name:
            return
        if cmds.objExists(self._binding.controller_name):
            # Set value on controller
            pass

    # ========================================================================
    # Animation
    # ========================================================================

    def _init_animations(self) -> None:
        """Initialize animation system."""
        # Fade animation
        self._fade_animation = QPropertyAnimation(self, b"opacity")
        self._fade_animation.setDuration(300)
        self._fade_animation.setEasingCurve(QEasingCurve.InOutQuad)

        # Scale animation
        self._scale_animation = QPropertyAnimation(self, b"scale")
        self._scale_animation.setDuration(300)
        self._scale_animation.setEasingCurve(QEasingCurve.InOutQuad)

    def animate(self, animation_type: AnimationType, duration: int = 300) -> None:
        """Animate the widget."""
        if animation_type == AnimationType.FADE:
            self._fade_animation.setDuration(duration)
            self._fade_animation.setStartValue(self._style.opacity)
            self._fade_animation.setEndValue(0.0 if self._style.opacity > 0.5 else 1.0)
            self._fade_animation.start()
        elif animation_type == AnimationType.SCALE:
            self._scale_animation.setDuration(duration)
            self._scale_animation.setStartValue(self._geometry.scale)
            self._scale_animation.setEndValue(self._geometry.scale * 1.2)
            self._scale_animation.start()
        elif animation_type == AnimationType.PULSE:
            # Implement pulse using timer
            pass
        elif animation_type == AnimationType.GLOW:
            self._style.glow_enabled = True
            self.update()

    def stop_animations(self) -> None:
        """Stop all animations."""
        self._fade_animation.stop()
        self._scale_animation.stop()

    # ========================================================================
    # Painting
    # ========================================================================

    def paint(self, painter: QPainter, option: QtWidgets.QStyleOptionGraphicsItem, widget: Optional[QtWidgets.QWidget] = None) -> None:
        """Paint the widget (override in subclasses)."""
        # This is a stub; subclasses should implement their own painting
        rect = self.boundingRect()

        # Get colors based on state
        fill_color = self._get_fill_color()
        border_color = self._get_border_color()
        text_color = self._get_text_color()
        opacity = self._get_opacity()

        # Set painter properties
        painter.setOpacity(opacity)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw shadow if enabled
        if self._style.shadow_enabled:
            shadow = QColor(*self._style.shadow_color)
            painter.setPen(Qt.NoPen)
            painter.setBrush(shadow)
            shadow_rect = rect.translated(self._style.shadow_offset[0], self._style.shadow_offset[1])
            painter.drawRoundedRect(shadow_rect, self._style.corner_radius, self._style.corner_radius)

        # Draw fill
        painter.setPen(QPen(QColor(*border_color), self._style.border_width))
        painter.setBrush(QBrush(QColor(*fill_color)))
        painter.drawRoundedRect(rect, self._style.corner_radius, self._style.corner_radius)

        # Draw glow if enabled
        if self._style.glow_enabled:
            glow_color = QColor(*self._style.glow_color)
            glow_color.setAlpha(80)
            glow_rect = rect.adjusted(-self._style.glow_radius, -self._style.glow_radius,
                                      self._style.glow_radius, self._style.glow_radius)
            painter.setPen(Qt.NoPen)
            painter.setBrush(glow_color)
            painter.drawRoundedRect(glow_rect, self._style.corner_radius + self._style.glow_radius,
                                    self._style.corner_radius + self._style.glow_radius)

        # Draw label text (if any)
        if hasattr(self, '_label') and self._label:
            painter.setPen(QPen(QColor(*text_color)))
            font = QtGui.QFont(self._style.font_family, self._style.font_size, self._style.font_weight)
            painter.setFont(font)
            painter.drawText(rect, Qt.AlignCenter, self._label)

    def _get_fill_color(self) -> Tuple[int, int, int]:
        """Get fill color based on state."""
        if self._state == WidgetState.HOVER:
            return self._style.fill_color_hover
        elif self._state == WidgetState.PRESSED:
            return self._style.fill_color_pressed
        elif self._state == WidgetState.SELECTED:
            return self._style.fill_color_selected
        elif self._state == WidgetState.LOCKED:
            return self._style.fill_color_locked
        elif self._state == WidgetState.DISABLED:
            return self._style.fill_color_disabled
        return self._style.fill_color

    def _get_border_color(self) -> Tuple[int, int, int]:
        """Get border color based on state."""
        if self._state == WidgetState.HOVER:
            return self._style.border_color_hover
        elif self._state == WidgetState.SELECTED:
            return self._style.border_color_selected
        return self._style.border_color

    def _get_text_color(self) -> Tuple[int, int, int]:
        """Get text color based on state."""
        if self._state == WidgetState.SELECTED:
            return self._style.text_color_selected
        elif self._state == WidgetState.HOVER:
            return self._style.text_color_hover
        return self._style.text_color

    def _get_opacity(self) -> float:
        """Get opacity based on state."""
        if self._state == WidgetState.DISABLED:
            return self._style.opacity_disabled
        elif self._state == WidgetState.SELECTED:
            return self._style.opacity_selected
        elif self._state == WidgetState.HOVER:
            return self._style.opacity_hover
        return self._style.opacity

    # ========================================================================
    # Events
    # ========================================================================

    def mousePressEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        """Handle mouse press."""
        if not self._enabled or self._locked:
            return
        if event.button() == Qt.LeftButton:
            self._pressed_state = True
            self.set_state(WidgetState.PRESSED)
            self.pressed.emit(self)
            event.accept()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        """Handle mouse release."""
        if not self._enabled or self._locked:
            return
        if event.button() == Qt.LeftButton and self._pressed_state:
            self._pressed_state = False
            if self._state == WidgetState.PRESSED:
                self.set_state(WidgetState.HOVER if self._hover else WidgetState.NORMAL)
            self.released.emit(self)
            if self.contains(event.pos()):
                self.clicked.emit(self)
            event.accept()
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        """Handle double click."""
        if not self._enabled or self._locked:
            return
        if event.button() == Qt.LeftButton:
            self.double_clicked.emit(self)
            event.accept()
        super().mouseDoubleClickEvent(event)

    def hoverEnterEvent(self, event: QtWidgets.QGraphicsSceneHoverEvent) -> None:
        """Handle hover enter."""
        if not self._enabled or self._locked:
            return
        self._hover = True
        if self._state != WidgetState.PRESSED:
            self.set_state(WidgetState.HOVER)
        self.hover_entered.emit(self)

        # Start hover animation if enabled
        if self._style.glow_enabled:
            self._style.glow_enabled = True
            self.update()

        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event: QtWidgets.QGraphicsSceneHoverEvent) -> None:
        """Handle hover leave."""
        self._hover = False
        if self._state == WidgetState.HOVER:
            self.set_state(WidgetState.NORMAL)
        self.hover_left.emit(self)

        # Stop glow animation if no selection
        if not self._selected:
            self._style.glow_enabled = False
            self.update()

        super().hoverLeaveEvent(event)

    def contains(self, point: QPointF) -> bool:
        """Check if point is within the widget."""
        return self.boundingRect().contains(point)

    # ========================================================================
    # Utility
    # ========================================================================

    def to_dict(self) -> Dict[str, Any]:
        """Serialize widget to dict."""
        return {
            "type": self._widget_type.value,
            "geometry": self._geometry.to_dict(),
            "style": self._style.to_dict(),
            "binding": self._binding.to_dict(),
            "metadata": self._metadata.to_dict(),
            "state": self._state.value,
            "enabled": self._enabled,
            "visible": self._visible,
            "locked": self._locked,
            "selected": self._selected,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PickerWidget':
        """Deserialize widget from dict."""
        widget = cls()
        if "geometry" in data:
            widget._geometry = WidgetGeometry.from_dict(data["geometry"])
        if "style" in data:
            widget._style = WidgetStyle.from_dict(data["style"])
        if "binding" in data:
            widget._binding = WidgetBinding.from_dict(data["binding"])
        if "metadata" in data:
            widget._metadata = WidgetMetadata.from_dict(data["metadata"])
        if "enabled" in data:
            widget._enabled = data["enabled"]
        if "visible" in data:
            widget._visible = data["visible"]
            widget.setVisible(widget._visible)
        if "locked" in data:
            widget._locked = data["locked"]
        return widget

    def clone(self) -> 'PickerWidget':
        """Create a copy of the widget."""
        data = self.to_dict()
        return self.from_dict(data)


# ============================================================================
# Part 5: Selection Widgets
# ============================================================================

class SelectionWidget(PickerWidget):
    """Base class for selection widgets."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._widget_type = WidgetType.SELECTION
        self._style.fill_color = (100, 100, 200, 80)
        self._style.border_color = (100, 100, 255)
        self._style.border_width = 1.5
        self._style.corner_radius = 2.0
        self.set_selectable(False)
        self.set_movable(False)


class SelectionRectangle(SelectionWidget):
    """Rectangle selection widget."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._widget_type = WidgetType.RECTANGLE


class SelectionCircle(SelectionWidget):
    """Circle selection widget."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._widget_type = WidgetType.CIRCLE

    def paint(self, painter: QPainter, option: QtWidgets.QStyleOptionGraphicsItem, widget: Optional[QtWidgets.QWidget] = None) -> None:
        """Paint circle selection."""
        rect = self.boundingRect()
        center = rect.center()
        radius = min(rect.width(), rect.height()) / 2

        fill_color = self._get_fill_color()
        border_color = self._get_border_color()
        opacity = self._get_opacity()

        painter.setOpacity(opacity)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw shadow if enabled
        if self._style.shadow_enabled:
            shadow = QColor(*self._style.shadow_color)
            painter.setPen(Qt.NoPen)
            painter.setBrush(shadow)
            shadow_center = center + QPointF(self._style.shadow_offset[0], self._style.shadow_offset[1])
            painter.drawEllipse(shadow_center, radius, radius)

        # Draw fill
        painter.setPen(QPen(QColor(*border_color), self._style.border_width))
        painter.setBrush(QBrush(QColor(*fill_color)))
        painter.drawEllipse(center, radius, radius)

        # Draw glow if enabled
        if self._style.glow_enabled:
            glow_color = QColor(*self._style.glow_color)
            glow_color.setAlpha(80)
            glow_radius = radius + self._style.glow_radius
            painter.setPen(Qt.NoPen)
            painter.setBrush(glow_color)
            painter.drawEllipse(center, glow_radius, glow_radius)

        # Draw label
        if hasattr(self, '_label') and self._label:
            painter.setPen(QPen(QColor(*self._get_text_color())))
            font = QtGui.QFont(self._style.font_family, self._style.font_size, self._style.font_weight)
            painter.setFont(font)
            painter.drawText(rect, Qt.AlignCenter, self._label)


# ============================================================================
# Part 6: Controller Widgets
# ============================================================================

class ControllerWidget(PickerWidget):
    """
    Widget that represents a Maya controller.

    This is the most important widget type in the picker.
    Each instance links directly to a Maya controller node.
    """

    def __init__(
        self,
        controller_name: str = "",
        label: str = "",
        icon_path: str = "",
        **kwargs
    ):
        super().__init__(**kwargs)
        self._widget_type = WidgetType.BUTTON
        self._controller_name = controller_name
        self._label = label
        self._icon_path = icon_path
        self._icon = None
        self._default_color = self._style.fill_color

        if controller_name:
            self._binding.controller_name = controller_name

        if icon_path:
            self._load_icon(icon_path)

        # Set default style for controllers
        self._style.corner_radius = 8.0
        self._style.border_width = 2.0

    def _load_icon(self, icon_path: str) -> None:
        """Load icon from file."""
        if os.path.exists(icon_path):
            self._icon = QPixmap(icon_path)
            # Scale icon to fit widget
            if self._icon:
                size = min(self._geometry.width, self._geometry.height) * 0.6
                self._icon = self._icon.scaled(int(size), int(size), Qt.KeepAspectRatio, Qt.SmoothTransformation)

    def set_controller(self, controller_name: str) -> None:
        """Set the Maya controller name."""
        self._controller_name = controller_name
        self._binding.controller_name = controller_name
        self._connect_to_maya()

    def get_controller(self) -> str:
        return self._controller_name

    def set_label(self, label: str) -> None:
        self._label = label
        self.update()

    def set_icon(self, icon_path: str) -> None:
        self._icon_path = icon_path
        self._load_icon(icon_path)
        self.update()

    def paint(self, painter: QPainter, option: QtWidgets.QStyleOptionGraphicsItem, widget: Optional[QtWidgets.QWidget] = None) -> None:
        """Paint controller widget."""
        rect = self.boundingRect()
        fill_color = self._get_fill_color()
        border_color = self._get_border_color()
        text_color = self._get_text_color()
        opacity = self._get_opacity()

        painter.setOpacity(opacity)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw shadow if enabled
        if self._style.shadow_enabled:
            shadow = QColor(*self._style.shadow_color)
            painter.setPen(Qt.NoPen)
            painter.setBrush(shadow)
            shadow_rect = rect.translated(self._style.shadow_offset[0], self._style.shadow_offset[1])
            painter.drawRoundedRect(shadow_rect, self._style.corner_radius, self._style.corner_radius)

        # Draw background
        painter.setPen(QPen(QColor(*border_color), self._style.border_width))
        painter.setBrush(QBrush(QColor(*fill_color)))
        painter.drawRoundedRect(rect, self._style.corner_radius, self._style.corner_radius)

        # Draw glow if enabled
        if self._style.glow_enabled:
            glow_color = QColor(*self._style.glow_color)
            glow_color.setAlpha(80)
            glow_rect = rect.adjusted(-self._style.glow_radius, -self._style.glow_radius,
                                      self._style.glow_radius, self._style.glow_radius)
            painter.setPen(Qt.NoPen)
            painter.setBrush(glow_color)
            painter.drawRoundedRect(glow_rect, self._style.corner_radius + self._style.glow_radius,
                                    self._style.corner_radius + self._style.glow_radius)

        # Draw icon
        if self._icon:
            icon_rect = QRectF(
                (rect.width() - self._icon.width()) / 2,
                (rect.height() - self._icon.height()) / 2 - 5,
                self._icon.width(),
                self._icon.height()
            )
            painter.drawPixmap(icon_rect.topLeft(), self._icon)

        # Draw label
        if self._label:
            painter.setPen(QPen(QColor(*text_color)))
            font = QtGui.QFont(self._style.font_family, self._style.font_size, self._style.font_weight)
            painter.setFont(font)
            label_rect = rect.adjusted(5, rect.height() - 20, -5, -5)
            painter.drawText(label_rect, Qt.AlignCenter, self._label)

    def update_from_maya(self) -> None:
        """Update widget from Maya controller."""
        if not cmds or not self._controller_name:
            return
        if cmds.objExists(self._controller_name):
            # Get the controller's selection state or value
            # For selection, we'll update the selected state
            selected = cmds.select(self._controller_name, q=True, replace=True)
            # We'll use this to check if the controller is selected
            pass

    def select_in_maya(self) -> None:
        """Select this controller in Maya."""
        if cmds and self._controller_name and cmds.objExists(self._controller_name):
            cmds.select(self._controller_name, replace=True)

    def frame_in_maya(self) -> None:
        """Frame this controller in Maya viewport."""
        if cmds and self._controller_name and cmds.objExists(self._controller_name):
            cmds.select(self._controller_name, replace=True)
            cmds.viewFit()


class EyeWidget(ControllerWidget):
    """Eye controller widget."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._widget_type = WidgetType.CIRCLE
        self._style.corner_radius = 999


class BrowWidget(ControllerWidget):
    """Brow controller widget."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._widget_type = WidgetType.RECTANGLE
        self._style.corner_radius = 4.0


class JawWidget(ControllerWidget):
    """Jaw controller widget."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._widget_type = WidgetType.RECTANGLE
        self._style.corner_radius = 6.0
        self._style.fill_color = (200, 180, 50)


class LipWidget(ControllerWidget):
    """Lip controller widget."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._widget_type = WidgetType.RECTANGLE
        self._style.corner_radius = 10.0
        self._style.fill_color = (200, 100, 80)


class TongueWidget(ControllerWidget):
    """Tongue controller widget."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._widget_type = WidgetType.RECTANGLE
        self._style.corner_radius = 4.0
        self._style.fill_color = (150, 80, 150)


class CheekWidget(ControllerWidget):
    """Cheek controller widget."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._widget_type = WidgetType.CIRCLE
        self._style.corner_radius = 999
        self._style.fill_color = (200, 150, 100)


class NoseWidget(ControllerWidget):
    """Nose controller widget."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._widget_type = WidgetType.RECTANGLE
        self._style.corner_radius = 4.0
        self._style.fill_color = (150, 120, 100)


# ============================================================================
# Part 7: Slider Widgets
# ============================================================================

class SliderWidget(PickerWidget):
    """
    Slider widget for controlling values.
    """

    def __init__(
        self,
        label: str = "",
        min_value: float = 0.0,
        max_value: float = 1.0,
        default_value: float = 0.0,
        orientation: SliderOrientation = SliderOrientation.HORIZONTAL,
        **kwargs
    ):
        super().__init__(**kwargs)
        self._widget_type = WidgetType.SLIDER
        self._label = label
        self._min = min_value
        self._max = max_value
        self._value = default_value
        self._orientation = orientation
        self._dragging = False
        self._drag_start = 0.0
        self._value_at_drag_start = 0.0

        # Slider appearance
        self._track_color = (60, 60, 60)
        self._track_height = 6.0
        self._handle_color = (200, 200, 200)
        self._handle_radius = 8.0
        self._handle_dragging_color = (220, 220, 255)

        # Set size based on orientation
        if orientation == SliderOrientation.HORIZONTAL:
            self._geometry.width = 100.0
            self._geometry.height = 30.0
        elif orientation == SliderOrientation.VERTICAL:
            self._geometry.width = 30.0
            self._geometry.height = 100.0

        self._style.corner_radius = 2.0

    def set_value(self, value: float) -> None:
        """Set the slider value."""
        self._value = max(self._min, min(self._max, value))
        self.update()

    def get_value(self) -> float:
        return self._value

    def set_range(self, min_val: float, max_val: float) -> None:
        self._min = min_val
        self._max = max_val
        if self._value < min_val:
            self._value = min_val
        elif self._value > max_val:
            self._value = max_val
        self.update()

    def paint(self, painter: QPainter, option: QtWidgets.QStyleOptionGraphicsItem, widget: Optional[QtWidgets.QWidget] = None) -> None:
        """Paint slider widget."""
        rect = self.boundingRect()
        opacity = self._get_opacity()

        painter.setOpacity(opacity)
        painter.setRenderHint(QPainter.Antialiasing)

        if self._orientation == SliderOrientation.HORIZONTAL:
            self._paint_horizontal(painter, rect)
        elif self._orientation == SliderOrientation.VERTICAL:
            self._paint_vertical(painter, rect)
        elif self._orientation == SliderOrientation.RADIAL:
            self._paint_radial(painter, rect)

        # Draw label
        if self._label:
            painter.setPen(QPen(QColor(*self._get_text_color())))
            font = QtGui.QFont(self._style.font_family, 9, 400)
            painter.setFont(font)
            label_rect = rect.adjusted(5, 2, -5, -2)
            painter.drawText(label_rect, Qt.AlignTop | Qt.AlignHCenter, self._label)

    def _paint_horizontal(self, painter: QPainter, rect: QRectF) -> None:
        """Paint horizontal slider."""
        track_rect = QRectF(
            rect.left() + 15,
            rect.center().y() - self._track_height / 2,
            rect.width() - 30,
            self._track_height
        )

        # Draw track
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(*self._track_color))
        painter.drawRoundedRect(track_rect, self._track_height / 2, self._track_height / 2)

        # Draw progress
        if self._max > self._min:
            progress = (self._value - self._min) / (self._max - self._min)
            progress_rect = QRectF(
                track_rect.left(),
                track_rect.top(),
                track_rect.width() * progress,
                track_rect.height()
            )
            painter.setBrush(QColor(*self._style.fill_color_selected))
            painter.drawRoundedRect(progress_rect, self._track_height / 2, self._track_height / 2)

        # Draw handle
        handle_x = track_rect.left() + progress * track_rect.width()
        handle_color = self._handle_dragging_color if self._dragging else self._handle_color
        painter.setBrush(QColor(*handle_color))
        painter.setPen(QPen(QColor(0, 0, 0), 1))
        painter.drawEllipse(QPointF(handle_x, track_rect.center().y()), self._handle_radius, self._handle_radius)

        # Draw value text
        painter.setPen(QPen(QColor(200, 200, 200)))
        painter.setFont(QtGui.QFont("Arial", 8))
        value_text = f"{self._value:.2f}"
        painter.drawText(
            QRectF(track_rect.right() + 5, track_rect.top(), 40, track_rect.height()),
            Qt.AlignLeft | Qt.AlignVCenter,
            value_text
        )

    def _paint_vertical(self, painter: QPainter, rect: QRectF) -> None:
        """Paint vertical slider."""
        track_rect = QRectF(
            rect.center().x() - self._track_height / 2,
            rect.top() + 15,
            self._track_height,
            rect.height() - 30
        )

        # Draw track
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(*self._track_color))
        painter.drawRoundedRect(track_rect, self._track_height / 2, self._track_height / 2)

        # Draw progress
        if self._max > self._min:
            progress = (self._value - self._min) / (self._max - self._min)
            progress_rect = QRectF(
                track_rect.left(),
                track_rect.bottom() - track_rect.height() * progress,
                track_rect.width(),
                track_rect.height() * progress
            )
            painter.setBrush(QColor(*self._style.fill_color_selected))
            painter.drawRoundedRect(progress_rect, self._track_height / 2, self._track_height / 2)

        # Draw handle
        handle_y = track_rect.bottom() - progress * track_rect.height()
        handle_color = self._handle_dragging_color if self._dragging else self._handle_color
        painter.setBrush(QColor(*handle_color))
        painter.setPen(QPen(QColor(0, 0, 0), 1))
        painter.drawEllipse(QPointF(track_rect.center().x(), handle_y), self._handle_radius, self._handle_radius)

    def _paint_radial(self, painter: QPainter, rect: QRectF) -> None:
        """Paint radial slider."""
        center = rect.center()
        radius = min(rect.width(), rect.height()) / 2 - 10

        # Draw arc
        painter.setPen(QPen(QColor(*self._track_color), 6))
        painter.drawEllipse(center, radius, radius)

        # Draw progress arc
        if self._max > self._min:
            progress = (self._value - self._min) / (self._max - self._min)
            start_angle = 90 * 16
            span_angle = -progress * 360 * 16
            painter.setPen(QPen(QColor(*self._style.fill_color_selected), 6))
            painter.drawArc(
                QRectF(center.x() - radius, center.y() - radius, radius * 2, radius * 2),
                start_angle, int(span_angle)
            )

        # Draw handle
        angle = -progress * 2 * math.pi + math.pi / 2
        handle_x = center.x() + radius * math.cos(angle)
        handle_y = center.y() - radius * math.sin(angle)
        painter.setBrush(QColor(*self._handle_color))
        painter.setPen(QPen(QColor(0, 0, 0), 1))
        painter.drawEllipse(QPointF(handle_x, handle_y), self._handle_radius, self._handle_radius)

    def mousePressEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        """Handle mouse press for slider."""
        if not self._enabled or self._locked:
            return
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_start = event.pos().x() if self._orientation == SliderOrientation.HORIZONTAL else event.pos().y()
            self._value_at_drag_start = self._value
            self.set_state(WidgetState.PRESSED)
            self._update_from_mouse(event.pos())
            event.accept()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        """Handle mouse move for slider."""
        if self._dragging:
            self._update_from_mouse(event.pos())
            event.accept()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        """Handle mouse release for slider."""
        if self._dragging:
            self._dragging = False
            self.set_state(WidgetState.HOVER if self._hover else WidgetState.NORMAL)
            event.accept()
        super().mouseReleaseEvent(event)

    def _update_from_mouse(self, pos: QPointF) -> None:
        """Update value from mouse position."""
        rect = self.boundingRect()
        if self._orientation == SliderOrientation.HORIZONTAL:
            track_rect = QRectF(rect.left() + 15, rect.center().y() - self._track_height / 2,
                                rect.width() - 30, self._track_height)
            t = (pos.x() - track_rect.left()) / track_rect.width()
        elif self._orientation == SliderOrientation.VERTICAL:
            track_rect = QRectF(rect.center().x() - self._track_height / 2, rect.top() + 15,
                                self._track_height, rect.height() - 30)
            t = 1.0 - (pos.y() - track_rect.top()) / track_rect.height()
        else:
            t = 0.0
        t = max(0.0, min(1.0, t))
        self.set_value(self._min + t * (self._max - self._min))
        self.update()


# ============================================================================
# Part 8: Joystick Widgets
# ============================================================================

class JoystickWidget(PickerWidget):
    """
    2D joystick widget for controlling two axes.
    """

    def __init__(
        self,
        label: str = "",
        x_controller: str = "",
        y_controller: str = "",
        **kwargs
    ):
        super().__init__(**kwargs)
        self._widget_type = WidgetType.JOYSTICK
        self._label = label
        self._x_controller = x_controller
        self._y_controller = y_controller
        self._value_x = 0.0
        self._value_y = 0.0
        self._dragging = False

        # Set size
        self._geometry.width = 80.0
        self._geometry.height = 80.0

        self._style.corner_radius = 999  # Circle

    def set_value(self, x: float, y: float) -> None:
        """Set joystick values."""
        self._value_x = max(-1.0, min(1.0, x))
        self._value_y = max(-1.0, min(1.0, y))
        self.update()

    def get_value(self) -> Tuple[float, float]:
        return (self._value_x, self._value_y)

    def paint(self, painter: QPainter, option: QtWidgets.QStyleOptionGraphicsItem, widget: Optional[QtWidgets.QWidget] = None) -> None:
        """Paint joystick widget."""
        rect = self.boundingRect()
        center = rect.center()
        radius = min(rect.width(), rect.height()) / 2 - 10
        opacity = self._get_opacity()

        painter.setOpacity(opacity)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw background circle
        painter.setPen(QPen(QColor(*self._style.border_color), 1))
        painter.setBrush(QBrush(QColor(*self._get_fill_color())))
        painter.drawEllipse(center, radius, radius)

        # Draw cross lines
        painter.setPen(QPen(QColor(80, 80, 80), 1, Qt.DashLine))
        painter.drawLine(center.x() - radius, center.y(), center.x() + radius, center.y())
        painter.drawLine(center.x(), center.y() - radius, center.x(), center.y() + radius)

        # Draw center dot
        painter.setBrush(QColor(80, 80, 80))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(center, 4, 4)

        # Draw handle
        handle_x = center.x() + self._value_x * radius * 0.8
        handle_y = center.y() - self._value_y * radius * 0.8
        painter.setBrush(QColor(200, 200, 200))
        painter.setPen(QPen(QColor(0, 0, 0), 1))
        painter.drawEllipse(QPointF(handle_x, handle_y), 10, 10)

        # Draw label
        if self._label:
            painter.setPen(QPen(QColor(*self._get_text_color())))
            font = QtGui.QFont(self._style.font_family, 9, 400)
            painter.setFont(font)
            label_rect = rect.adjusted(5, rect.height() - 25, -5, -5)
            painter.drawText(label_rect, Qt.AlignCenter, self._label)

    def mousePressEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        """Handle mouse press for joystick."""
        if not self._enabled or self._locked:
            return
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self.set_state(WidgetState.PRESSED)
            self._update_from_mouse(event.pos())
            event.accept()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        """Handle mouse move for joystick."""
        if self._dragging:
            self._update_from_mouse(event.pos())
            event.accept()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        """Handle mouse release for joystick."""
        if self._dragging:
            self._dragging = False
            self.set_value(0.0, 0.0)
            self.set_state(WidgetState.HOVER if self._hover else WidgetState.NORMAL)
            event.accept()
        super().mouseReleaseEvent(event)

    def _update_from_mouse(self, pos: QPointF) -> None:
        """Update value from mouse position."""
        rect = self.boundingRect()
        center = rect.center()
        radius = min(rect.width(), rect.height()) / 2 - 10
        dx = pos.x() - center.x()
        dy = -(pos.y() - center.y())
        max_dist = radius * 0.8
        dist = math.sqrt(dx * dx + dy * dy)
        if dist > max_dist:
            dx = dx / dist * max_dist
            dy = dy / dist * max_dist
        self._value_x = dx / max_dist
        self._value_y = dy / max_dist
        self.update()


# ============================================================================
# Part 9: Image Widgets
# ============================================================================

class ImageWidget(PickerWidget):
    """
    Widget that displays an image.
    """

    def __init__(self, image_path: str = "", **kwargs):
        super().__init__(**kwargs)
        self._widget_type = WidgetType.IMAGE
        self._image_path = image_path
        self._pixmap = None
        self._aspect_ratio = True

        if image_path:
            self.load_image(image_path)

        # Set default size to fit image
        if self._pixmap:
            self._geometry.width = self._pixmap.width()
            self._geometry.height = self._pixmap.height()

        self._style.corner_radius = 0.0
        self._style.border_width = 0.0
        self.set_selectable(False)
        self.set_movable(False)

    def load_image(self, image_path: str) -> None:
        """Load image from path."""
        self._image_path = image_path
        if os.path.exists(image_path):
            self._pixmap = QPixmap(image_path)
            if self._aspect_ratio and self._pixmap:
                # Scale to fit widget
                self._pixmap = self._pixmap.scaled(
                    int(self._geometry.width),
                    int(self._geometry.height),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
            self.update()
        else:
            logger.warning(f"Image not found: {image_path}")

    def set_aspect_ratio(self, enabled: bool) -> None:
        self._aspect_ratio = enabled
        if self._pixmap:
            self.load_image(self._image_path)

    def paint(self, painter: QPainter, option: QtWidgets.QStyleOptionGraphicsItem, widget: Optional[QtWidgets.QWidget] = None) -> None:
        """Paint image widget."""
        if not self._pixmap:
            return

        rect = self.boundingRect()
        opacity = self._get_opacity()

        painter.setOpacity(opacity)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        # Draw image centered
        x = (rect.width() - self._pixmap.width()) / 2
        y = (rect.height() - self._pixmap.height()) / 2
        painter.drawPixmap(QPointF(x, y), self._pixmap)

        # Draw border if enabled
        if self._style.border_width > 0:
            painter.setPen(QPen(QColor(*self._style.border_color), self._style.border_width))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(rect)


# ============================================================================
# Part 10: Label Widgets
# ============================================================================

class LabelWidget(PickerWidget):
    """
    Widget that displays text.
    """

    def __init__(self, text: str = "", alignment: WidgetAlignment = WidgetAlignment.CENTER, **kwargs):
        super().__init__(**kwargs)
        self._widget_type = WidgetType.TEXT
        self._text = text
        self._alignment = alignment

        # Set default size based on text
        self._geometry.width = 100.0
        self._geometry.height = 30.0

        self._style.corner_radius = 0.0
        self._style.border_width = 0.0
        self.set_selectable(False)
        self.set_movable(False)

    def set_text(self, text: str) -> None:
        self._text = text
        self.update()

    def get_text(self) -> str:
        return self._text

    def set_alignment(self, alignment: WidgetAlignment) -> None:
        self._alignment = alignment
        self.update()

    def paint(self, painter: QPainter, option: QtWidgets.QStyleOptionGraphicsItem, widget: Optional[QtWidgets.QWidget] = None) -> None:
        """Paint label widget."""
        rect = self.boundingRect()
        opacity = self._get_opacity()

        painter.setOpacity(opacity)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw text
        painter.setPen(QPen(QColor(*self._get_text_color())))
        font = QtGui.QFont(self._style.font_family, self._style.font_size, self._style.font_weight)
        painter.setFont(font)

        # Alignment
        align_flags = Qt.AlignCenter
        if self._alignment == WidgetAlignment.LEFT:
            align_flags = Qt.AlignLeft | Qt.AlignVCenter
        elif self._alignment == WidgetAlignment.RIGHT:
            align_flags = Qt.AlignRight | Qt.AlignVCenter
        elif self._alignment == WidgetAlignment.TOP:
            align_flags = Qt.AlignTop | Qt.AlignHCenter
        elif self._alignment == WidgetAlignment.BOTTOM:
            align_flags = Qt.AlignBottom | Qt.AlignHCenter
        elif self._alignment == WidgetAlignment.TOP_LEFT:
            align_flags = Qt.AlignTop | Qt.AlignLeft
        elif self._alignment == WidgetAlignment.TOP_RIGHT:
            align_flags = Qt.AlignTop | Qt.AlignRight
        elif self._alignment == WidgetAlignment.BOTTOM_LEFT:
            align_flags = Qt.AlignBottom | Qt.AlignLeft
        elif self._alignment == WidgetAlignment.BOTTOM_RIGHT:
            align_flags = Qt.AlignBottom | Qt.AlignRight

        painter.drawText(rect, align_flags, self._text)


# ============================================================================
# Part 11: Region Widgets
# ============================================================================

class RegionWidget(PickerWidget):
    """
    Widget that represents a facial region for group selection.
    """

    def __init__(self, region_name: str = "", points: Optional[List[Tuple[float, float]]] = None, **kwargs):
        super().__init__(**kwargs)
        self._widget_type = WidgetType.REGION
        self._region_name = region_name
        self._points = points or []
        self._polygon = None

        if self._points:
            self._build_polygon()

        self._style.corner_radius = 0.0
        self._style.fill_color = (80, 80, 120, 80)
        self._style.fill_color_hover = (100, 100, 160, 100)
        self._style.fill_color_selected = (150, 150, 200, 120)
        self._style.border_color = (100, 100, 200)
        self._style.border_width = 1.5
        self.set_selectable(False)
        self.set_movable(False)

    def set_region(self, region_name: str) -> None:
        self._region_name = region_name
        self.update()

    def set_points(self, points: List[Tuple[float, float]]) -> None:
        self._points = points
        self._build_polygon()
        self.update()

    def _build_polygon(self) -> None:
        """Build polygon from points."""
        if not self._points:
            return
        self._polygon = QPainterPath()
        self._polygon.moveTo(self._points[0][0], self._points[0][1])
        for x, y in self._points[1:]:
            self._polygon.lineTo(x, y)
        self._polygon.closeSubpath()

    def contains(self, point: QPointF) -> bool:
        """Check if point is inside the region."""
        if self._polygon:
            return self._polygon.contains(point)
        return super().contains(point)

    def shape(self) -> QPainterPath:
        if self._polygon:
            return self._polygon
        return super().shape()

    def paint(self, painter: QPainter, option: QtWidgets.QStyleOptionGraphicsItem, widget: Optional[QtWidgets.QWidget] = None) -> None:
        """Paint region widget."""
        if not self._polygon:
            return

        opacity = self._get_opacity()
        fill_color = self._get_fill_color()
        border_color = self._get_border_color()

        painter.setOpacity(opacity)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw fill
        painter.setPen(QPen(QColor(*border_color), self._style.border_width))
        painter.setBrush(QBrush(QColor(*fill_color)))
        painter.drawPath(self._polygon)

        # Draw region name
        if self._region_name:
            center = self._polygon.boundingRect().center()
            painter.setPen(QPen(QColor(*self._get_text_color())))
            font = QtGui.QFont(self._style.font_family, 10, 600)
            painter.setFont(font)
            painter.drawText(center, self._region_name)


# ============================================================================
# Part 12: Widget Styling (already in dataclasses)
# ============================================================================

# ============================================================================
# Part 13: Interaction System (built into base classes)
# ============================================================================

# ============================================================================
# Part 14: Widget Animation (built into base classes)
# ============================================================================

# ============================================================================
# Part 15: Validation
# ============================================================================

class WidgetValidator:
    """
    Validates widgets for integrity and correctness.
    """

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate(self, widget: PickerWidget) -> bool:
        """Validate a single widget."""
        self.errors.clear()
        self.warnings.clear()

        # Check geometry
        if widget._geometry.width <= 0 or widget._geometry.height <= 0:
            self.errors.append("Invalid geometry: width or height <= 0")

        # Check binding
        if widget._binding.controller_name and not cmds.objExists(widget._binding.controller_name):
            self.warnings.append(f"Controller '{widget._binding.controller_name}' does not exist")

        # Check metadata
        if not widget._metadata.id:
            self.warnings.append("Widget has no ID")

        return len(self.errors) == 0


# ============================================================================
# Part 16: Utilities
# ============================================================================

class WidgetUtils:
    """Utility functions for widgets."""

    @staticmethod
    def generate_id() -> str:
        """Generate a unique widget ID."""
        import uuid
        return str(uuid.uuid4())[:8]

    @staticmethod
    def hash_widget(widget: PickerWidget) -> str:
        """Generate a hash for a widget."""
        data = widget.to_dict()
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.md5(json_str.encode()).hexdigest()

    @staticmethod
    def widget_bounds(widgets: List[PickerWidget]) -> QRectF:
        """Get bounding rect of multiple widgets."""
        if not widgets:
            return QRectF()
        rect = widgets[0].boundingRect().translated(widgets[0].pos())
        for w in widgets[1:]:
            rect = rect.united(w.boundingRect().translated(w.pos()))
        return rect

    @staticmethod
    def center_widgets(widgets: List[PickerWidget]) -> QPointF:
        """Get center of multiple widgets."""
        rect = WidgetUtils.widget_bounds(widgets)
        return rect.center()

    @staticmethod
    def snap_to_grid(pos: QPointF, grid_size: float) -> QPointF:
        """Snap position to grid."""
        x = round(pos.x() / grid_size) * grid_size
        y = round(pos.y() / grid_size) * grid_size
        return QPointF(x, y)

    @staticmethod
    def distance(p1: QPointF, p2: QPointF) -> float:
        """Distance between two points."""
        return math.sqrt((p1.x() - p2.x()) ** 2 + (p1.y() - p2.y()) ** 2)

    @staticmethod
    def interpolate_color(c1: Tuple[int, int, int], c2: Tuple[int, int, int], t: float) -> Tuple[int, int, int]:
        """Interpolate between two colors."""
        r = int(c1[0] + (c2[0] - c1[0]) * t)
        g = int(c1[1] + (c2[1] - c1[1]) * t)
        b = int(c1[2] + (c2[2] - c1[2]) * t)
        return (r, g, b)

    @staticmethod
    def color_to_qcolor(color: Tuple[int, int, int], alpha: int = 255) -> QColor:
        """Convert tuple color to QColor."""
        if len(color) == 4:
            return QColor(color[0], color[1], color[2], color[3])
        return QColor(color[0], color[1], color[2], alpha)


# ============================================================================
# Part 17: Public API
# ============================================================================

__all__ = [
    # Enums
    "WidgetType",
    "WidgetState",
    "WidgetAlignment",
    "SliderOrientation",
    "AnimationType",

    # Data Models
    "WidgetStyle",
    "WidgetGeometry",
    "WidgetBinding",
    "WidgetAnimation",
    "WidgetMetadata",

    # Base Widgets
    "PickerWidget",

    # Selection Widgets
    "SelectionWidget",
    "SelectionRectangle",
    "SelectionCircle",

    # Controller Widgets
    "ControllerWidget",
    "EyeWidget",
    "BrowWidget",
    "JawWidget",
    "LipWidget",
    "TongueWidget",
    "CheekWidget",
    "NoseWidget",

    # Slider Widgets
    "SliderWidget",

    # Joystick Widgets
    "JoystickWidget",

    # Image & Label Widgets
    "ImageWidget",
    "LabelWidget",

    # Region Widgets
    "RegionWidget",

    # Validation
    "WidgetValidator",

    # Utilities
    "WidgetUtils",
]