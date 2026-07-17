# ============================================================================
# maya_faceit/picker/picker.py
# ============================================================================
"""
maya_faceit.picker.picker

Main Facial Control Picker application.

This module provides a comprehensive picker UI for selecting and manipulating
facial controls in Maya. It includes a 2D canvas with widgets, search/filter,
Maya selection sync, undo support, and customizable layouts.

Author: Maya FaceIT Team
"""

from __future__ import annotations

import json
import logging
import math
import os
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

# Maya imports
try:
    import maya.cmds as cmds # type: ignore
    import maya.mel as mel # type: ignore
    import maya.OpenMayaUI as omui # type: ignore
    from maya.api import OpenMaya as om # type: ignore
except ImportError:
    cmds = None
    mel = None
    omui = None
    om = None
from .layouts import PickerLayout
# Qt imports
try:
    from PySide6 import QtCore, QtGui, QtWidgets # type: ignore
    from PySide6.QtCore import Qt, Signal, Slot, QObject, QTimer, QMimeData # type: ignore
    from shiboken6 import wrapInstance # type: ignore
except ImportError:
    try:
        from PySide2 import QtCore, QtGui, QtWidgets # type: ignore
        from PySide2.QtCore import Qt, Signal, Slot, QObject, QTimer, QMimeData # type: ignore
        from shiboken2 import wrapInstance # type: ignore
    except ImportError:
        raise ImportError("No Qt binding found (PySide6 or PySide2).")

# ============================================================================
# Module Metadata
# ============================================================================

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"
PACKAGE = "maya_faceit.picker"

logger = logging.getLogger(PACKAGE)
logger.setLevel(logging.INFO)

# ============================================================================
# Exceptions
# ============================================================================

class PickerError(Exception):
    """Base exception for picker-related errors."""
    pass

class PickerInitError(PickerError):
    """Raised when picker initialisation fails."""
    pass

class PickerLayoutError(PickerError):
    """Raised when layout operations fail."""
    pass

class PickerWidgetError(PickerError):
    """Raised when widget operations fail."""
    pass

class PickerSyncError(PickerError):
    """Raised when Maya synchronisation fails."""
    pass

# ============================================================================
# Enumerations
# ============================================================================

class PickerMode(Enum):
    """Interaction mode for the picker."""
    SELECT = "select"
    EDIT = "edit"
    PAN = "pan"
    ZOOM = "zoom"

class SelectionMode(Enum):
    """Selection behaviour."""
    SINGLE = "single"
    MULTIPLE = "multiple"
    REGION = "region"
    HIERARCHY = "hierarchy"

class DisplayMode(Enum):
    """Display styles for the picker."""
    DEFAULT = "default"
    COMPACT = "compact"
    DEBUG = "debug"

class WidgetType(Enum):
    """Types of widgets in the picker."""
    BUTTON = "button"
    CIRCLE = "circle"
    SLIDER = "slider"
    JOYSTICK = "joystick"
    REGION = "region"
    LABEL = "label"
    IMAGE = "image"

class WidgetState(Enum):
    """Extended state for widgets."""
    NORMAL = "normal"
    LOCKED = "locked"
    HIDDEN = "hidden"
    FAVORITE = "favorite"
    PINNED = "pinned"
    INVALID = "invalid"

# ============================================================================
# Dataclasses
# ============================================================================

@dataclass
class PickerConfig:
    """Global picker configuration."""
    mode: PickerMode = PickerMode.SELECT
    selection_mode: SelectionMode = SelectionMode.SINGLE
    display_mode: DisplayMode = DisplayMode.DEFAULT
    auto_sync: bool = True
    show_help: bool = True
    snap_to_grid: bool = False
    grid_size: float = 10.0

@dataclass
class PickerSession:
    """Session state for the picker."""
    current_layout: str = ""
    current_character: str = ""
    selected_controls: List[str] = field(default_factory=list)
    zoom_level: float = 1.0
    pan_offset: Tuple[float, float] = (0.0, 0.0)
    widget_positions: Dict[str, Tuple[float, float]] = field(default_factory=dict)

@dataclass
class ControlInfo:
    """Information about a rig control."""
    name: str
    long_name: str = ""
    side: str = "C"  # L, R, C
    region: str = "General"
    widget_type: WidgetType = WidgetType.BUTTON
    color: Tuple[int, int, int] = (100, 100, 100)
    enabled: bool = True
    locked: bool = False
    custom_attrs: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WidgetUIState:
    """UI state for a widget."""
    locked: bool = False
    hidden: bool = False
    favorite: bool = False
    pinned: bool = False

# ============================================================================
# Base Interfaces
# ============================================================================

class PickerComponent(QObject):
    """Base interface for all picker components."""
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._enabled = True

    def enable(self) -> None:
        self._enabled = True
        self.on_enabled()

    def disable(self) -> None:
        self._enabled = False
        self.on_disabled()

    def is_enabled(self) -> bool:
        return self._enabled

    def on_enabled(self) -> None: pass
    def on_disabled(self) -> None: pass
    def refresh(self) -> None: pass

# ============================================================================
# Settings
# ============================================================================

class PickerSettings:
    """Singleton for picker settings."""
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        self.config = PickerConfig()
        self._load_from_preferences()

    def _load_from_preferences(self):
        # In production, load from Maya preferences
        pass

    def get(self) -> PickerConfig:
        return self.config

    def update(self, **kwargs) -> None:
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        self._save_to_preferences()

    def _save_to_preferences(self):
        pass

# ============================================================================
# Helper Functions
# ============================================================================

def get_picker_settings() -> PickerSettings:
    return PickerSettings()

def get_maya_main_window() -> Optional[QtWidgets.QWidget]:
    if omui is None:
        return None
    ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(int(ptr), QtWidgets.QWidget)

# ============================================================================
# Phase 3: PickerScene & PickerView
# ============================================================================

class PickerScene(QtWidgets.QGraphicsScene):
    """Custom graphics scene with grid, background, and snap."""
    def __init__(self, parent=None, grid_size=10.0, show_grid=True, snap_to_grid=False):
        super().__init__(parent)
        self._grid_size = grid_size
        self._show_grid = show_grid
        self._snap_to_grid = snap_to_grid
        self._background_image = None
        self._image_scale = 1.0
        self.setSceneRect(-2000, -2000, 4000, 4000)
        self._grid_color = QtGui.QColor(60, 60, 60)
        self._grid_pen = QtGui.QPen(self._grid_color, 0.5, Qt.DashLine)
        self._bg_color = QtGui.QColor(40, 40, 40)
        self.setItemIndexMethod(QtWidgets.QGraphicsScene.NoIndex)

    def set_grid_size(self, size: float): self._grid_size = max(1.0, size); self.update()
    def set_show_grid(self, show: bool): self._show_grid = show; self.update()
    def set_snap_to_grid(self, snap: bool): self._snap_to_grid = snap
    def set_background_image(self, image_path: str, scale: float = 1.0):
        if os.path.exists(image_path):
            self._background_image = QtGui.QPixmap(image_path)
            self._image_scale = scale
            self.update()
    def set_background_color(self, color: QtGui.QColor): self._bg_color = color; self.update()

    def drawBackground(self, painter: QtGui.QPainter, rect: QtCore.QRectF):
        painter.fillRect(rect, self._bg_color)
        if self._background_image:
            pixmap = self._background_image
            if self._image_scale != 1.0:
                pixmap = pixmap.scaled(pixmap.size() * self._image_scale, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            scene_rect = self.sceneRect()
            img_rect = pixmap.rect()
            x = (scene_rect.width() - img_rect.width()) / 2.0
            y = (scene_rect.height() - img_rect.height()) / 2.0
            painter.drawPixmap(x, y, pixmap)
        if self._show_grid:
            self._draw_grid(painter, rect)

    def _draw_grid(self, painter, rect):
        left = int(math.floor(rect.left() / self._grid_size)) * self._grid_size
        right = int(math.ceil(rect.right() / self._grid_size)) * self._grid_size
        top = int(math.floor(rect.top() / self._grid_size)) * self._grid_size
        bottom = int(math.ceil(rect.bottom() / self._grid_size)) * self._grid_size
        lines = []
        x = left
        while x <= right:
            lines.append(QtCore.QLineF(x, top, x, bottom))
            x += self._grid_size
        y = top
        while y <= bottom:
            lines.append(QtCore.QLineF(left, y, right, y))
            y += self._grid_size
        painter.setPen(self._grid_pen)
        painter.drawLines(lines)

    def snap_position(self, pos: QtCore.QPointF) -> QtCore.QPointF:
        if not self._snap_to_grid:
            return pos
        x = round(pos.x() / self._grid_size) * self._grid_size
        y = round(pos.y() / self._grid_size) * self._grid_size
        return QtCore.QPointF(x, y)

    def add_widget(self, widget: QtWidgets.QGraphicsItem):
        if self._snap_to_grid:
            pos = widget.pos()
            snapped = self.snap_position(pos)
            widget.setPos(snapped)
        self.addItem(widget)


class PickerView(QtWidgets.QGraphicsView):
    """Custom graphics view with zoom, pan, and wheel support."""
    def __init__(self, scene: PickerScene, parent=None):
        super().__init__(scene, parent)
        self._scene = scene
        self._zoom_factor = 1.1
        self._min_zoom = 0.1
        self._max_zoom = 10.0
        self._pan_active = False
        self._pan_start = QtCore.QPointF()
        self._pan_origin = QtCore.QPointF()

        self.setRenderHint(QtGui.QPainter.Antialiasing)
        self.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
        self.setDragMode(QtWidgets.QGraphicsView.RubberBandDrag)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setMouseTracking(True)

    def zoom_in(self, factor=None):
        factor = factor or self._zoom_factor
        self._zoom(factor)

    def zoom_out(self, factor=None):
        factor = factor or (1.0 / self._zoom_factor)
        self._zoom(factor)

    def _zoom(self, factor):
        new_scale = self.transform().m11() * factor
        if new_scale < self._min_zoom:
            factor = self._min_zoom / self.transform().m11()
        elif new_scale > self._max_zoom:
            factor = self._max_zoom / self.transform().m11()
        self.scale(factor, factor)

    def reset_zoom(self):
        self.resetTransform()

    def fit_scene(self):
        if self._scene.items():
            self.fitInView(self._scene.itemsBoundingRect(), Qt.KeepAspectRatio)
        else:
            self.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)

    def get_zoom_level(self):
        return self.transform().m11()

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self._pan_active = True
            self._pan_start = event.pos()
            self._pan_origin = QtCore.QPointF(self.horizontalScrollBar().value(), self.verticalScrollBar().value())
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._pan_active:
            delta = event.pos() - self._pan_start
            new_h = self._pan_origin.x() - delta.x()
            new_v = self._pan_origin.y() - delta.y()
            self.horizontalScrollBar().setValue(int(new_h))
            self.verticalScrollBar().setValue(int(new_v))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton and self._pan_active:
            self._pan_active = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_in()
            elif delta < 0:
                self.zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Plus or event.key() == Qt.Key_Equal:
            if event.modifiers() & Qt.ControlModifier:
                self.zoom_in()
                event.accept()
                return
        elif event.key() == Qt.Key_Minus:
            if event.modifiers() & Qt.ControlModifier:
                self.zoom_out()
                event.accept()
                return
        super().keyPressEvent(event)


# ============================================================================
# Phase 6: InteractivePickerView (extends PickerView)
# ============================================================================

class InteractivePickerView(PickerView):
    """Enhanced view with drag-and-drop, tooltips, context menus."""
    def __init__(self, scene: PickerScene, parent=None):
        super().__init__(scene, parent)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self._drag_start_pos = None
        self._drag_item = None
        self._drag_offset = None
        self._selection_modifiers = Qt.NoModifier
        self._tooltip_widget = None
        self._tooltip_timer = QtCore.QTimer(self)
        self._tooltip_timer.setSingleShot(True)
        self._tooltip_timer.timeout.connect(self._show_tooltip)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocus()

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            pos = event.pos()
            scene_pos = self.mapToScene(pos)
            item = self.scene.itemAt(scene_pos, QtGui.QTransform())
            if item and isinstance(item, PickerWidget):
                self._show_widget_context_menu(item, pos)
            else:
                self._show_scene_context_menu(pos)
            event.accept()
            return
        self._selection_modifiers = event.modifiers()
        if event.button() == Qt.LeftButton:
            pos = event.pos()
            scene_pos = self.mapToScene(pos)
            item = self.scene.itemAt(scene_pos, QtGui.QTransform())
            if item and isinstance(item, PickerWidget):
                picker = self.parent() if isinstance(self.parent(), FacePicker) else None
                if picker and picker.get_mode() == PickerMode.EDIT:
                    self._drag_start_pos = pos
                    self._drag_item = item
                    self._drag_offset = scene_pos - item.pos()
                    super().mousePressEvent(event)
                    return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        pos = event.pos()
        scene_pos = self.mapToScene(pos)
        item = self.scene.itemAt(scene_pos, QtGui.QTransform())
        if item and isinstance(item, PickerWidget):
            self._tooltip_widget = item
            self._tooltip_timer.start(800)
            if self._drag_start_pos and self._drag_item:
                self.setCursor(Qt.ClosedHandCursor)
            else:
                self.setCursor(Qt.PointingHandCursor)
        else:
            self._tooltip_timer.stop()
            self._tooltip_widget = None
            self.setCursor(Qt.ArrowCursor)
        if self._drag_start_pos and self._drag_item:
            if (event.pos() - self._drag_start_pos).manhattanLength() > QtWidgets.QApplication.startDragDistance():
                self._start_drag(self._drag_item)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_start_pos = None
        self._drag_item = None
        self._drag_offset = None
        self._tooltip_timer.stop()
        super().mouseReleaseEvent(event)

    def _start_drag(self, item):
        if not item:
            return
        drag = QtWidgets.QDrag(self)
        mime_data = QtCore.QMimeData()
        widget_data = {
            "type": item.__class__.__name__,
            "control_name": getattr(item, 'control_name', ''),
            "label": getattr(item, 'label', ''),
            "size": item._size if hasattr(item, '_size') else (50, 50),
            "color": item._color if hasattr(item, '_color') else (100, 100, 100),
        }
        mime_data.setData("application/x-picker-widget", json.dumps(widget_data).encode('utf-8'))
        drag.setMimeData(mime_data)
        pixmap = QtGui.QPixmap(int(item._size[0]), int(item._size[1]))
        pixmap.fill(Qt.transparent)
        painter = QtGui.QPainter(pixmap)
        item.paint(painter, None, None)
        painter.end()
        drag.setPixmap(pixmap)
        drag.setHotSpot(QtCore.QPoint(pixmap.width() // 2, pixmap.height() // 2))
        drag.exec_(Qt.CopyAction | Qt.MoveAction)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-picker-widget"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat("application/x-picker-widget"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if not event.mimeData().hasFormat("application/x-picker-widget"):
            return
        data = json.loads(event.mimeData().data("application/x-picker-widget").data().decode('utf-8'))
        scene_pos = self.mapToScene(event.pos())
        picker = self.parent() if isinstance(self.parent(), FacePicker) else None
        if picker:
            creation_data = {
                "control_name": data.get("control_name", ""),
                "label": data.get("label", ""),
                "type": WidgetType(data.get("type", "button").lower()),
                "size": data.get("size", (50, 50)),
                "color": data.get("color", (100, 100, 100)),
            }
            widget = picker._create_widget_from_data(creation_data)
            if widget:
                snapped_pos = picker.scene.snap_position(scene_pos)
                widget.setPos(snapped_pos)
                event.acceptProposedAction()
                return
        event.ignore()

    def _show_tooltip(self):
        if self._tooltip_widget:
            widget = self._tooltip_widget
            control_name = getattr(widget, 'control_name', '')
            label = getattr(widget, 'label', '')
            if control_name:
                tooltip_text = f"{label} ({control_name})" if label else control_name
                QtWidgets.QToolTip.showText(
                    self.mapToGlobal(self._tooltip_widget.pos().toPoint()),
                    tooltip_text, self
                )

    def _show_widget_context_menu(self, widget, pos):
        menu = QtWidgets.QMenu()
        edit_action = menu.addAction("Edit Widget")
        edit_action.triggered.connect(lambda: self._edit_widget(widget))
        menu.addSeparator()
        dup_action = menu.addAction("Duplicate Widget")
        dup_action.triggered.connect(lambda: self._duplicate_widget(widget))
        menu.addSeparator()
        del_action = menu.addAction("Delete Widget")
        del_action.triggered.connect(lambda: self._delete_widget(widget))
        menu.addSeparator()
        if hasattr(widget, 'control_name') and widget.control_name:
            select_action = menu.addAction("Select in Maya")
            select_action.triggered.connect(lambda: self._select_in_maya(widget.control_name))
            frame_action = menu.addAction("Frame in Maya")
            frame_action.triggered.connect(lambda: self._frame_in_maya(widget.control_name))
        # Add UI state toggles
        picker = self.parent() if isinstance(self.parent(), FacePicker) else None
        if picker:
            widget_id = widget.property("widget_id")
            if widget_id:
                menu.addSeparator()
                fav_action = menu.addAction("Toggle Favorite")
                fav_action.setCheckable(True)
                fav_action.setChecked(picker.widget_registry.is_favorite(widget_id))
                fav_action.triggered.connect(lambda: picker._toggle_favorite(widget))
                lock_action = menu.addAction("Toggle Locked")
                lock_action.setCheckable(True)
                state = picker.widget_registry.get_ui_state(widget_id)
                lock_action.setChecked(state.locked if state else False)
                lock_action.triggered.connect(lambda: picker._toggle_locked(widget))
                hide_action = menu.addAction("Toggle Hidden")
                hide_action.setCheckable(True)
                hide_action.setChecked(state.hidden if state else False)
                hide_action.triggered.connect(lambda: picker._toggle_hidden(widget))
        menu.exec_(self.mapToGlobal(pos))

    def _show_scene_context_menu(self, pos):
        menu = QtWidgets.QMenu()
        add_widget = menu.addAction("Add Widget...")
        add_widget.triggered.connect(self._add_widget)
        menu.addSeparator()
        fit_view = menu.addAction("Fit View")
        fit_view.triggered.connect(self.fit_scene)
        reset_view = menu.addAction("Reset View")
        reset_view.triggered.connect(self.reset_zoom)
        menu.exec_(self.mapToGlobal(pos))

    def _edit_widget(self, widget):
        picker = self.parent() if isinstance(self.parent(), FacePicker) else None
        if picker:
            picker._edit_widget_dialog(widget)

    def _duplicate_widget(self, widget):
        picker = self.parent() if isinstance(self.parent(), FacePicker) else None
        if picker:
            data = {
                "control_name": getattr(widget, 'control_name', ''),
                "label": getattr(widget, 'label', ''),
                "type": WidgetType(widget.__class__.__name__.replace("Picker", "").lower()),
                "size": widget._size if hasattr(widget, '_size') else (50, 50),
                "color": widget._color if hasattr(widget, '_color') else (100, 100, 100),
            }
            new_widget = picker._create_widget_from_data(data)
            if new_widget:
                pos = widget.pos() + QtCore.QPointF(20, 20)
                snapped_pos = picker.scene.snap_position(pos)
                new_widget.setPos(snapped_pos)

    def _delete_widget(self, widget):
        picker = self.parent() if isinstance(self.parent(), FacePicker) else None
        if picker:
            picker._delete_widget(widget)

    def _select_in_maya(self, control_name):
        if cmds and cmds.objExists(control_name):
            cmds.select(control_name, replace=True)

    def _frame_in_maya(self, control_name):
        if cmds and cmds.objExists(control_name):
            cmds.select(control_name, replace=True)
            cmds.viewFit()

    def _add_widget(self):
        picker = self.parent() if isinstance(self.parent(), FacePicker) else None
        if picker:
            picker._add_widget_dialog()

    def keyPressEvent(self, event):
        picker = self.parent() if isinstance(self.parent(), FacePicker) else None
        if not picker:
            super().keyPressEvent(event)
            return
        key = event.key()
        mods = event.modifiers()
        if key == Qt.Key_Delete or key == Qt.Key_Backspace:
            picker._delete_selected_widget()
            event.accept()
            return
        if key == Qt.Key_D and mods & Qt.ControlModifier:
            selected = picker.scene.selectedItems()
            for widget in selected:
                if isinstance(widget, PickerWidget):
                    self._duplicate_widget(widget)
            event.accept()
            return
        if key == Qt.Key_A and mods & Qt.ControlModifier:
            picker._select_all()
            event.accept()
            return
        if key == Qt.Key_Escape:
            picker.clear_selection()
            event.accept()
            return
        if key == Qt.Key_F and not (mods & Qt.ControlModifier):
            if picker._selected_controls:
                picker._frame_control_in_maya(picker._selected_controls[0])
            event.accept()
            return
        super().keyPressEvent(event)


# ============================================================================
# Phase 4: SelectionManager
# ============================================================================

class SelectionManager(QObject):
    selection_changed = Signal(list)
    selection_cleared = Signal()
    control_selected = Signal(str)
    control_deselected = Signal(str)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._selected_controls: List[str] = []
        self._selection_mode: SelectionMode = SelectionMode.SINGLE
        self._maya_sync_enabled: bool = True
        self._maya_callback = None
        self._block_sync = False
        self._register_maya_callback()

    def get_selected(self) -> List[str]:
        return self._selected_controls.copy()

    def is_selected(self, control_name: str) -> bool:
        return control_name in self._selected_controls

    def count(self) -> int:
        return len(self._selected_controls)

    def set_selection_mode(self, mode: SelectionMode):
        self._selection_mode = mode

    def get_selection_mode(self) -> SelectionMode:
        return self._selection_mode

    def select(self, control_names: Union[str, List[str]], add: bool = False):
        if isinstance(control_names, str):
            control_names = [control_names]
        if not add:
            self.clear()
        for name in control_names:
            if name not in self._selected_controls:
                self._selected_controls.append(name)
                self.control_selected.emit(name)
        self._update_selection_state()

    def deselect(self, control_names: Union[str, List[str]]):
        if isinstance(control_names, str):
            control_names = [control_names]
        for name in control_names:
            if name in self._selected_controls:
                self._selected_controls.remove(name)
                self.control_deselected.emit(name)
        self._update_selection_state()

    def clear(self):
        if self._selected_controls:
            self._selected_controls.clear()
            self.selection_cleared.emit()
            self._update_selection_state()

    def toggle(self, control_name: str):
        if self.is_selected(control_name):
            self.deselect(control_name)
        else:
            self.select(control_name, add=True)

    def enable_maya_sync(self, enabled: bool):
        self._maya_sync_enabled = enabled

    def sync_to_maya(self):
        if not self._maya_sync_enabled or self._block_sync:
            return
        if cmds is None:
            return
        if self._selected_controls:
            existing = [c for c in self._selected_controls if cmds.objExists(c)]
            if existing:
                cmds.select(existing, replace=True)
            else:
                cmds.select(clear=True)
        else:
            cmds.select(clear=True)

    def sync_from_maya(self):
        if not self._maya_sync_enabled or self._block_sync:
            return
        if cmds is None:
            return
        maya_selection = cmds.ls(selection=True, long=True)
        self._block_sync = True
        self.clear()
        if maya_selection:
            self.select(maya_selection, add=False)
        self._block_sync = False
        self._update_selection_state()

    def _register_maya_callback(self):
        if cmds is None:
            return
        try:
            import maya.api.OpenMaya as om2 # type: ignore
            self._maya_callback = om2.MEventMessage.addEventCallback(
                "SelectionChanged", self._on_maya_selection_changed
            )
        except Exception as e:
            logger.warning(f"Could not register Maya selection callback: {e}")

    def _on_maya_selection_changed(self, *args):
        self.sync_from_maya()

    def _update_selection_state(self):
        self.selection_changed.emit(self._selected_controls)
        self.sync_to_maya()

    def filter_by_region(self, region: str) -> List[str]:
        # Placeholder
        return self._selected_controls

    def filter_by_side(self, side: str) -> List[str]:
        if side not in ("L", "R", "C"):
            return self._selected_controls
        return [c for c in self._selected_controls if c.startswith(f"{side}_")]


# ============================================================================
# Phase 5 & 8: Widget Registry
# ============================================================================

class EnhancedWidgetRegistry(QObject):
    """Registry with UI state management."""
    def __init__(self):
        super().__init__()
        self._widgets: Dict[str, PickerWidget] = {}  # id -> widget
        self._control_to_widget: Dict[str, str] = {}  # control_name -> widget_id
        self._ui_states: Dict[str, WidgetUIState] = {}
        self._favorite_ids: Set[str] = set()
        self._pinned_ids: Set[str] = set()
        self._region_map: Dict[str, Set[str]] = {}
        self._id_counter = 0

    def generate_id(self) -> str:
        self._id_counter += 1
        return f"widget_{self._id_counter:04d}"

    def add(self, widget: PickerWidget) -> str:
        widget_id = self.generate_id()
        self._widgets[widget_id] = widget
        widget.setProperty("widget_id", widget_id)
        if hasattr(widget, 'control_name') and widget.control_name:
            self._control_to_widget[widget.control_name] = widget_id
        self._ui_states[widget_id] = WidgetUIState()
        # Determine region (simple heuristic)
        control_name = getattr(widget, 'control_name', '')
        if control_name:
            region = self._guess_region(control_name)
            self.set_region(widget_id, region)
        return widget_id

    def remove(self, widget_id: str) -> bool:
        if widget_id not in self._widgets:
            return False
        widget = self._widgets[widget_id]
        if hasattr(widget, 'control_name') and widget.control_name:
            if widget.control_name in self._control_to_widget:
                del self._control_to_widget[widget.control_name]
        del self._widgets[widget_id]
        if widget_id in self._ui_states:
            del self._ui_states[widget_id]
        self._favorite_ids.discard(widget_id)
        self._pinned_ids.discard(widget_id)
        for region, ids in self._region_map.items():
            if widget_id in ids:
                ids.remove(widget_id)
        return True

    def get(self, widget_id: str) -> Optional[PickerWidget]:
        return self._widgets.get(widget_id)

    def get_by_control(self, control_name: str) -> Optional[PickerWidget]:
        widget_id = self._control_to_widget.get(control_name)
        return self.get(widget_id) if widget_id else None

    def list_widgets(self) -> List[PickerWidget]:
        return list(self._widgets.values())

    def list_ids(self) -> List[str]:
        return list(self._widgets.keys())

    def count(self) -> int:
        return len(self._widgets)

    def clear(self):
        self._widgets.clear()
        self._control_to_widget.clear()
        self._ui_states.clear()
        self._favorite_ids.clear()
        self._pinned_ids.clear()
        self._region_map.clear()

    def get_ui_state(self, widget_id: str) -> Optional[WidgetUIState]:
        return self._ui_states.get(widget_id)

    def set_locked(self, widget_id: str, locked: bool):
        if widget_id in self._ui_states:
            self._ui_states[widget_id].locked = locked
            self._update_widget_appearance(widget_id)

    def set_hidden(self, widget_id: str, hidden: bool):
        if widget_id in self._ui_states:
            self._ui_states[widget_id].hidden = hidden
            widget = self.get(widget_id)
            if widget:
                widget.setVisible(not hidden)

    def toggle_favorite(self, widget_id: str) -> bool:
        if widget_id in self._favorite_ids:
            self._favorite_ids.remove(widget_id)
            return False
        else:
            self._favorite_ids.add(widget_id)
            return True

    def is_favorite(self, widget_id: str) -> bool:
        return widget_id in self._favorite_ids

    def toggle_pinned(self, widget_id: str) -> bool:
        if widget_id in self._pinned_ids:
            self._pinned_ids.remove(widget_id)
            return False
        else:
            self._pinned_ids.add(widget_id)
            return True

    def is_pinned(self, widget_id: str) -> bool:
        return widget_id in self._pinned_ids

    def get_favorites(self) -> List[PickerWidget]:
        return [self.get(wid) for wid in self._favorite_ids if self.get(wid)]

    def get_pinned(self) -> List[PickerWidget]:
        return [self.get(wid) for wid in self._pinned_ids if self.get(wid)]

    def set_region(self, widget_id: str, region: str):
        for r, ids in self._region_map.items():
            if widget_id in ids:
                ids.remove(widget_id)
        if region:
            self._region_map.setdefault(region, set()).add(widget_id)

    def get_widgets_by_region(self, region: str) -> List[PickerWidget]:
        return [self.get(wid) for wid in self._region_map.get(region, []) if self.get(wid)]

    def get_all_regions(self) -> List[str]:
        return sorted(self._region_map.keys())

    def _update_widget_appearance(self, widget_id: str):
        widget = self.get(widget_id)
        if not widget:
            return
        state = self.get_ui_state(widget_id)
        if not state:
            return
        if state.locked:
            # Visual indication for locked
            pass
        if state.hidden:
            widget.setVisible(False)
        else:
            widget.setVisible(True)
        # Favorites/pinned could change color, but we handle in picker.

    def _guess_region(self, control_name: str) -> str:
        regions = {
            'eye': 'Eyes',
            'brow': 'Brows',
            'lip': 'Mouth',
            'jaw': 'Jaw',
            'cheek': 'Cheeks',
            'nose': 'Nose',
            'ear': 'Ears',
            'tongue': 'Tongue',
            'neck': 'Neck',
            'forehead': 'Forehead',
            'lid': 'Eyelids',
        }
        control_lower = control_name.lower()
        for keyword, region in regions.items():
            if keyword in control_lower:
                return region
        return "General"

    def get_widget_data(self) -> List[Dict[str, Any]]:
        data = []
        for widget_id, widget in self._widgets.items():
            widget_data = {
                "id": widget_id,
                "type": widget.__class__.__name__,
                "control_name": getattr(widget, 'control_name', ''),
                "label": getattr(widget, 'label', ''),
                "x": widget.x(),
                "y": widget.y(),
                "width": widget._size[0] if hasattr(widget, '_size') else 50,
                "height": widget._size[1] if hasattr(widget, '_size') else 50,
                "color": widget._color if hasattr(widget, '_color') else (100, 100, 100),
            }
            if isinstance(widget, PickerSlider):
                widget_data["min"] = widget._min
                widget_data["max"] = widget._max
                widget_data["default"] = widget._value
                widget_data["orientation"] = "horizontal" if widget._orientation == Qt.Horizontal else "vertical"
            elif isinstance(widget, PickerJoystick):
                widget_data["control_name_x"] = widget.control_name_x
                widget_data["control_name_y"] = widget.control_name_y
            elif isinstance(widget, PickerRegion):
                widget_data["points"] = widget._points if hasattr(widget, '_points') else []
            data.append(widget_data)
        return data

    def restore_widgets(self, data: List[Dict[str, Any]]) -> List[PickerWidget]:
        restored = []
        for widget_data in data:
            widget_type = widget_data.get("type")
            control_name = widget_data.get("control_name", "")
            label = widget_data.get("label", "")
            x = widget_data.get("x", 0.0)
            y = widget_data.get("y", 0.0)
            width = widget_data.get("width", 50.0)
            height = widget_data.get("height", 50.0)
            color = tuple(widget_data.get("color", (100, 100, 100)))

            if widget_type == "PickerButton":
                widget = PickerButton(control_name=control_name, label=label, pos=(x, y), size=(width, height), color=color)
            elif widget_type == "PickerCircle":
                widget = PickerCircle(control_name=control_name, label=label, pos=(x, y), size=(width, height), color=color)
            elif widget_type == "PickerSlider":
                widget = PickerSlider(control_name=control_name, label=label, pos=(x, y), size=(width, height), color=color,
                                      min_value=widget_data.get("min", 0.0), max_value=widget_data.get("max", 1.0),
                                      default_value=widget_data.get("default", 0.0),
                                      orientation=Qt.Horizontal if widget_data.get("orientation") == "horizontal" else Qt.Vertical)
            elif widget_type == "PickerJoystick":
                widget = PickerJoystick(control_name_x=widget_data.get("control_name_x", ""),
                                        control_name_y=widget_data.get("control_name_y", ""),
                                        label=label, pos=(x, y), size=(width, height), color=color)
            elif widget_type == "PickerRegion":
                widget = PickerRegion(region_name=control_name, label=label, points=widget_data.get("points", []),
                                      pos=(x, y), size=(width, height), color=color)
            else:
                widget = PickerButton(control_name=control_name, label=label, pos=(x, y), size=(width, height), color=color)

            widget_id = widget_data.get("id")
            if widget_id:
                widget.setProperty("widget_id", widget_id)
                self._widgets[widget_id] = widget
                if hasattr(widget, 'control_name') and widget.control_name:
                    self._control_to_widget[widget.control_name] = widget_id
                self._ui_states[widget_id] = WidgetUIState()
            else:
                self.add(widget)
            restored.append(widget)
        return restored


# ============================================================================
# Phase 5: Widget Creation/Edit Dialogs
# ============================================================================

class CreateWidgetDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Picker Widget")
        self.setMinimumWidth(350)
        self._result = None
        self._color = (100, 100, 100)
        self._init_ui()

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        # Control name
        layout.addWidget(QtWidgets.QLabel("Control Name:"))
        self.control_line = QtWidgets.QLineEdit()
        self.control_line.setPlaceholderText("Enter Maya control name...")
        layout.addWidget(self.control_line)
        # Label
        layout.addWidget(QtWidgets.QLabel("Label:"))
        self.label_line = QtWidgets.QLineEdit()
        layout.addWidget(self.label_line)
        # Widget type
        layout.addWidget(QtWidgets.QLabel("Widget Type:"))
        self.type_combo = QtWidgets.QComboBox()
        self.type_combo.addItems([t.value.capitalize() for t in WidgetType])
        layout.addWidget(self.type_combo)
        # Size
        size_layout = QtWidgets.QHBoxLayout()
        size_layout.addWidget(QtWidgets.QLabel("Size:"))
        self.width_spin = QtWidgets.QSpinBox()
        self.width_spin.setRange(20, 200)
        self.width_spin.setValue(50)
        size_layout.addWidget(self.width_spin)
        size_layout.addWidget(QtWidgets.QLabel("x"))
        self.height_spin = QtWidgets.QSpinBox()
        self.height_spin.setRange(20, 200)
        self.height_spin.setValue(50)
        size_layout.addWidget(self.height_spin)
        layout.addLayout(size_layout)
        # Color
        color_layout = QtWidgets.QHBoxLayout()
        color_layout.addWidget(QtWidgets.QLabel("Color:"))
        self.color_button = QtWidgets.QPushButton("Choose Color...")
        self.color_button.clicked.connect(self._choose_color)
        color_layout.addWidget(self.color_button)
        self.color_preview = QtWidgets.QLabel()
        self.color_preview.setFixedSize(20, 20)
        self.color_preview.setStyleSheet(f"background-color: rgb({self._color[0]}, {self._color[1]}, {self._color[2]});")
        color_layout.addWidget(self.color_preview)
        layout.addLayout(color_layout)
        # Buttons
        btn_layout = QtWidgets.QHBoxLayout()
        ok_btn = QtWidgets.QPushButton("Create")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QtWidgets.QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _choose_color(self):
        color = QtWidgets.QColorDialog.getColor(QtGui.QColor(*self._color))
        if color.isValid():
            self._color = (color.red(), color.green(), color.blue())
            self.color_preview.setStyleSheet(f"background-color: rgb({self._color[0]}, {self._color[1]}, {self._color[2]});")

    def accept(self):
        self._result = {
            "control_name": self.control_line.text().strip(),
            "label": self.label_line.text().strip(),
            "type": WidgetType(self.type_combo.currentText().lower()),
            "size": (self.width_spin.value(), self.height_spin.value()),
            "color": self._color,
        }
        super().accept()

    def get_result(self):
        return self._result


class EditWidgetDialog(QtWidgets.QDialog):
    def __init__(self, widget: PickerWidget, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Picker Widget")
        self.setMinimumWidth(350)
        self._widget = widget
        self._result = None
        self._init_ui()

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        # Control (read-only)
        control_layout = QtWidgets.QHBoxLayout()
        control_layout.addWidget(QtWidgets.QLabel("Control:"))
        control_name = getattr(self._widget, 'control_name', '')
        control_layout.addWidget(QtWidgets.QLabel(control_name))
        layout.addLayout(control_layout)
        # Label
        label_layout = QtWidgets.QHBoxLayout()
        label_layout.addWidget(QtWidgets.QLabel("Label:"))
        self.label_line = QtWidgets.QLineEdit(getattr(self._widget, 'label', ''))
        label_layout.addWidget(self.label_line)
        layout.addLayout(label_layout)
        # Size
        size_layout = QtWidgets.QHBoxLayout()
        size_layout.addWidget(QtWidgets.QLabel("Size:"))
        self.width_spin = QtWidgets.QSpinBox()
        self.width_spin.setRange(20, 200)
        self.width_spin.setValue(int(self._widget._size[0] if hasattr(self._widget, '_size') else 50))
        size_layout.addWidget(self.width_spin)
        size_layout.addWidget(QtWidgets.QLabel("x"))
        self.height_spin = QtWidgets.QSpinBox()
        self.height_spin.setRange(20, 200)
        self.height_spin.setValue(int(self._widget._size[1] if hasattr(self._widget, '_size') else 50))
        size_layout.addWidget(self.height_spin)
        layout.addLayout(size_layout)
        # Color
        color_layout = QtWidgets.QHBoxLayout()
        color_layout.addWidget(QtWidgets.QLabel("Color:"))
        self.color_button = QtWidgets.QPushButton("Choose Color...")
        self.color_button.clicked.connect(self._choose_color)
        color_layout.addWidget(self.color_button)
        self.color_preview = QtWidgets.QLabel()
        color = self._widget._color if hasattr(self._widget, '_color') else (100, 100, 100)
        self.color_preview.setStyleSheet(f"background-color: rgb({color[0]}, {color[1]}, {color[2]});")
        color_layout.addWidget(self.color_preview)
        layout.addLayout(color_layout)
        # Buttons
        btn_layout = QtWidgets.QHBoxLayout()
        ok_btn = QtWidgets.QPushButton("Update")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QtWidgets.QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _choose_color(self):
        color = self._widget._color if hasattr(self._widget, '_color') else (100, 100, 100)
        new_color = QtWidgets.QColorDialog.getColor(QtGui.QColor(*color))
        if new_color.isValid():
            self.color_preview.setStyleSheet(f"background-color: rgb({new_color.red()}, {new_color.green()}, {new_color.blue()});")

    def accept(self):
        self._result = {
            "label": self.label_line.text(),
            "size": (self.width_spin.value(), self.height_spin.value()),
            "color": self.color_preview.palette().color(self.color_preview.backgroundRole()).getRgb()[:3],
        }
        super().accept()

    def get_result(self):
        return self._result


# ============================================================================
# Phase 7: ControllerResolver, MayaSelectionHandler, UndoManager
# ============================================================================

class ControllerResolver:
    def __init__(self):
        self._cache: Dict[str, str] = {}

    def resolve_control(self, name: str) -> Optional[str]:
        if not cmds:
            return None
        if name in self._cache:
            return self._cache[name]
        if cmds.objExists(name):
            full = cmds.ls(name, long=True)[0] if cmds.ls(name, long=True) else name
            self._cache[name] = full
            return full
        patterns = [name, f"{name}_CTRL", f"{name}_ctrl", f"CTRL_{name}", f"ctrl_{name}", f"{name}_JNT", f"{name}_jnt"]
        for p in patterns:
            if cmds.objExists(p):
                full = cmds.ls(p, long=True)[0] if cmds.ls(p, long=True) else p
                self._cache[name] = full
                return full
        namespaces = self._get_namespaces()
        for ns in namespaces:
            ns_name = f"{ns}:{name}"
            if cmds.objExists(ns_name):
                full = cmds.ls(ns_name, long=True)[0] if cmds.ls(ns_name, long=True) else ns_name
                self._cache[name] = full
                return full
            for p in patterns:
                ns_p = f"{ns}:{p}"
                if cmds.objExists(ns_p):
                    full = cmds.ls(ns_p, long=True)[0] if cmds.ls(ns_p, long=True) else ns_p
                    self._cache[name] = full
                    return full
        all_controls = cmds.ls(type='transform') + cmds.ls(type='joint')
        matches = [c for c in all_controls if c.endswith(name) or name in c]
        if len(matches) == 1:
            full = matches[0]
            self._cache[name] = full
            return full
        return None

    def _get_namespaces(self) -> List[str]:
        if not cmds:
            return []
        all_ns = cmds.namespaceInfo(listOnlyNamespaces=True, recurse=True) or []
        default = [':', 'UI', 'shared']
        return [ns for ns in all_ns if ns not in default]

    def get_side(self, control_name: str) -> str:
        if control_name.startswith('L_') or control_name.startswith('l_'):
            return 'L'
        elif control_name.startswith('R_') or control_name.startswith('r_'):
            return 'R'
        elif control_name.startswith('C_') or control_name.startswith('c_'):
            return 'C'
        if '_L_' in control_name or '_L' in control_name:
            return 'L'
        elif '_R_' in control_name or '_R' in control_name:
            return 'R'
        elif '_C_' in control_name or '_C' in control_name:
            return 'C'
        return 'C'

    def get_region(self, control_name: str) -> str:
        regions = {
            'eye': ['eye', 'Eyes'],
            'brow': ['brow', 'Brows'],
            'lip': ['lip', 'lips', 'Mouth'],
            'jaw': ['jaw', 'Jaw'],
            'cheek': ['cheek', 'Cheeks'],
            'nose': ['nose', 'Nose'],
            'ear': ['ear', 'Ears'],
            'tongue': ['tongue', 'Tongue'],
            'neck': ['neck', 'Neck'],
            'forehead': ['forehead', 'Forehead'],
            'eyelid': ['lid', 'Eyelids'],
        }
        control_lower = control_name.lower()
        for region, keywords in regions.items():
            for kw in keywords:
                if kw.lower() in control_lower:
                    return region.capitalize()
        return "General"


class MayaSelectionHandler(QObject):
    def __init__(self, picker: FacePicker):
        super().__init__(picker)
        self._picker = picker
        self._resolver = ControllerResolver()
        self._maya_callback = None
        self._block_sync = False
        self._enabled = True
        self._register_maya_callback()

    def _register_maya_callback(self):
        if cmds is None:
            return
        try:
            import maya.api.OpenMaya as om2 # type: ignore
            self._maya_callback = om2.MEventMessage.addEventCallback(
                "SelectionChanged", self._on_maya_selection_changed
            )
        except Exception as e:
            logger.warning(f"Could not register Maya selection callback: {e}")

    def _on_maya_selection_changed(self, *args):
        if self._block_sync or not self._enabled:
            return
        maya_selection = cmds.ls(selection=True, long=True)
        control_names = []
        for maya_obj in maya_selection:
            short_name = maya_obj.split('|')[-1]
            for widget in self._picker.widget_registry.list_widgets():
                if hasattr(widget, 'control_name'):
                    wc = widget.control_name
                    if short_name == wc or maya_obj == wc:
                        control_names.append(wc)
                        break
                    resolved = self._resolver.resolve_control(wc)
                    if resolved and (resolved == maya_obj or resolved.endswith(short_name)):
                        control_names.append(wc)
                        break
        if control_names:
            self._block_sync = True
            self._picker.selection_manager.clear()
            self._picker.selection_manager.select(control_names, add=False)
            self._block_sync = False
            self._picker._update_scene_selection(control_names)
            self._picker.control_selected.emit(control_names[0])

    def sync_to_maya(self):
        if not self._enabled or self._block_sync:
            return
        selected = self._picker.selection_manager.get_selected()
        if not selected:
            cmds.select(clear=True)
            return
        maya_objects = []
        for name in selected:
            resolved = self._resolver.resolve_control(name)
            if resolved:
                maya_objects.append(resolved)
        if maya_objects:
            cmds.select(maya_objects, replace=True)
        else:
            cmds.select(clear=True)

    def frame_control(self, control_name: str):
        if not cmds:
            return
        resolved = self._resolver.resolve_control(control_name)
        if resolved:
            cmds.select(resolved, replace=True)
            cmds.viewFit()

    def enable(self, enabled: bool):
        self._enabled = enabled

    def cleanup(self):
        if self._maya_callback:
            try:
                import maya.api.OpenMaya as om2 # type: ignore
                om2.MEventMessage.removeCallback(self._maya_callback)
            except:
                pass
            self._maya_callback = None


class UndoManager:
    def __init__(self, picker: FacePicker):
        self._picker = picker
        self._depth = 0
        self._open_chunk = False

    def begin_chunk(self, name: str = "Picker Operation"):
        if not cmds:
            return
        if self._depth == 0:
            cmds.undoInfo(openChunk=True, chunkName=name)
            self._open_chunk = True
        self._depth += 1

    def end_chunk(self):
        if not cmds:
            return
        if self._depth > 0:
            self._depth -= 1
        if self._depth == 0 and self._open_chunk:
            cmds.undoInfo(closeChunk=True)
            self._open_chunk = False

    def __enter__(self):
        self.begin_chunk()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_chunk()

    def undo(self):
        if cmds:
            cmds.undo()

    def redo(self):
        if cmds:
            cmds.redo()


# ============================================================================
# Phase 8: FilterManager, SearchBar, FilterPanel
# ============================================================================

class FilterManager(QObject):
    filter_changed = Signal()

    def __init__(self, registry: EnhancedWidgetRegistry):
        super().__init__()
        self._registry = registry
        self._search_text = ""
        self._active_regions: Set[str] = set()
        self._show_favorites_only = False
        self._show_hidden = False
        self._filter_locked = False

    def set_search_text(self, text: str):
        self._search_text = text.lower().strip()
        self.filter_changed.emit()

    def toggle_region(self, region: str):
        if region in self._active_regions:
            self._active_regions.remove(region)
        else:
            self._active_regions.add(region)
        self.filter_changed.emit()

    def set_active_regions(self, regions: List[str]):
        self._active_regions = set(regions)
        self.filter_changed.emit()

    def clear_regions(self):
        self._active_regions.clear()
        self.filter_changed.emit()

    def set_show_favorites_only(self, show: bool):
        self._show_favorites_only = show
        self.filter_changed.emit()

    def set_show_hidden(self, show: bool):
        self._show_hidden = show
        self.filter_changed.emit()

    def set_filter_locked(self, filter_locked: bool):
        self._filter_locked = filter_locked
        self.filter_changed.emit()

    def get_filtered_widgets(self) -> List[PickerWidget]:
        all_widgets = self._registry.list_widgets()
        filtered = []
        for widget in all_widgets:
            widget_id = widget.property("widget_id")
            if not widget_id:
                continue
            state = self._registry.get_ui_state(widget_id)
            if state and state.hidden and not self._show_hidden:
                continue
            if self._filter_locked and state and not state.locked:
                continue
            if self._show_favorites_only and not self._registry.is_favorite(widget_id):
                continue
            if self._search_text:
                control_name = getattr(widget, 'control_name', '').lower()
                label = getattr(widget, 'label', '').lower()
                if self._search_text not in control_name and self._search_text not in label:
                    continue
            if self._active_regions:
                region = self._registry._guess_region(getattr(widget, 'control_name', ''))
                if region not in self._active_regions:
                    continue
            filtered.append(widget)
        return filtered


class SearchBar(QtWidgets.QLineEdit):
    search_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Search controls...")
        self.setClearButtonEnabled(True)
        self.textChanged.connect(self.search_changed)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.clear()
        super().keyPressEvent(event)


class FilterPanel(QtWidgets.QDockWidget):
    def __init__(self, picker: FacePicker, parent=None):
        super().__init__("Filters", parent)
        self._picker = picker
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(container)
        self.search_bar = SearchBar()
        self.search_bar.search_changed.connect(self._on_search_changed)
        layout.addWidget(self.search_bar)
        region_group = QtWidgets.QGroupBox("Regions")
        region_layout = QtWidgets.QVBoxLayout(region_group)
        self.region_checkboxes: Dict[str, QtWidgets.QCheckBox] = {}
        layout.addWidget(region_group)
        options_group = QtWidgets.QGroupBox("Options")
        options_layout = QtWidgets.QVBoxLayout(options_group)
        self.favorites_check = QtWidgets.QCheckBox("Show Favorites Only")
        self.favorites_check.stateChanged.connect(self._on_favorites_toggle)
        options_layout.addWidget(self.favorites_check)
        self.hidden_check = QtWidgets.QCheckBox("Show Hidden")
        self.hidden_check.stateChanged.connect(self._on_hidden_toggle)
        options_layout.addWidget(self.hidden_check)
        self.locked_check = QtWidgets.QCheckBox("Show Locked Only")
        self.locked_check.stateChanged.connect(self._on_locked_toggle)
        options_layout.addWidget(self.locked_check)
        layout.addWidget(options_group)
        layout.addStretch()
        container.setLayout(layout)
        self.setWidget(container)
        self._update_regions()
        self.setFeatures(QtWidgets.QDockWidget.DockWidgetClosable |
                         QtWidgets.QDockWidget.DockWidgetMovable |
                         QtWidgets.QDockWidget.DockWidgetFloatable)

    def _update_regions(self):
        for cb in self.region_checkboxes.values():
            cb.deleteLater()
        self.region_checkboxes.clear()
        regions = self._picker.widget_registry.get_all_regions()
        if not regions:
            regions = ["General", "Eyes", "Mouth", "Brows", "Jaw", "Cheeks", "Nose", "Ears", "Tongue", "Neck", "Forehead", "Eyelids"]
        group = self.findChild(QtWidgets.QGroupBox, "Regions")
        layout = group.layout()
        for region in sorted(regions):
            cb = QtWidgets.QCheckBox(region)
            cb.stateChanged.connect(lambda state, r=region: self._on_region_toggle(r, state))
            layout.addWidget(cb)
            self.region_checkboxes[region] = cb

    def _on_region_toggle(self, region: str, state: int):
        if state == Qt.Checked:
            self._picker.filter_manager.toggle_region(region)
        else:
            self._picker.filter_manager.toggle_region(region)

    def _on_search_changed(self, text: str):
        self._picker.filter_manager.set_search_text(text)

    def _on_favorites_toggle(self, state: int):
        self._picker.filter_manager.set_show_favorites_only(state == Qt.Checked)

    def _on_hidden_toggle(self, state: int):
        self._picker.filter_manager.set_show_hidden(state == Qt.Checked)

    def _on_locked_toggle(self, state: int):
        self._picker.filter_manager.set_filter_locked(state == Qt.Checked)

    def refresh(self):
        self._update_regions()


# ============================================================================
# Phase 9: Runtime Services (EventBus, RefreshManager, UpdateManager, TimerManager, PerformanceOptimizer)
# ============================================================================

class EventBus(QObject):
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._listeners: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, callback: Callable):
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        if callback not in self._listeners[event_type]:
            self._listeners[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable):
        if event_type in self._listeners:
            if callback in self._listeners[event_type]:
                self._listeners[event_type].remove(callback)

    def publish(self, event_type: str, data: Any = None):
        if event_type in self._listeners:
            for callback in self._listeners[event_type]:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"Event callback error for {event_type}: {e}")


class RefreshManager(QObject):
    refresh_requested = Signal()

    def __init__(self, parent: Optional[QObject] = None, delay_ms: int = 100):
        super().__init__(parent)
        self._delay_ms = delay_ms
        self._cooldown_ms = 500
        self._last_refresh_time = 0
        self._timer = QtCore.QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_timer)
        self._pending = False

    def request_refresh(self):
        if not self._pending:
            self._pending = True
            self._timer.start(self._delay_ms)

    def _on_timer(self):
        now = time.time() * 1000
        if now - self._last_refresh_time < self._cooldown_ms:
            self._timer.start(self._cooldown_ms - (now - self._last_refresh_time))
            return
        self._last_refresh_time = now
        self._pending = False
        self.refresh_requested.emit()

    def cancel(self):
        self._timer.stop()
        self._pending = False


class UpdateManager(QObject):
    update_tick = Signal()

    def __init__(self, parent: Optional[QObject] = None, interval_ms: int = 200):
        super().__init__(parent)
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._interval_ms = interval_ms
        self._enabled = False
        self._tasks: List[Callable] = []

    def start(self):
        if not self._enabled:
            self._enabled = True
            self._timer.start(self._interval_ms)

    def stop(self):
        self._enabled = False
        self._timer.stop()

    def set_interval(self, interval_ms: int):
        self._interval_ms = interval_ms
        if self._enabled:
            self._timer.setInterval(interval_ms)

    def add_task(self, task: Callable):
        if task not in self._tasks:
            self._tasks.append(task)

    def remove_task(self, task: Callable):
        if task in self._tasks:
            self._tasks.remove(task)

    def _on_tick(self):
        for task in self._tasks:
            try:
                task()
            except Exception as e:
                logger.error(f"Update task error: {e}")
        self.update_tick.emit()


class TimerManager(QObject):
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._timers: Dict[str, QtCore.QTimer] = {}

    def create_timer(self, name: str, interval_ms: int, single_shot: bool = False) -> QtCore.QTimer:
        if name in self._timers:
            timer = self._timers[name]
            timer.setInterval(interval_ms)
            timer.setSingleShot(single_shot)
            return timer
        timer = QtCore.QTimer(self)
        timer.setInterval(interval_ms)
        timer.setSingleShot(single_shot)
        self._timers[name] = timer
        return timer

    def start_timer(self, name: str):
        if name in self._timers:
            self._timers[name].start()

    def stop_timer(self, name: str):
        if name in self._timers:
            self._timers[name].stop()

    def stop_all(self):
        for timer in self._timers.values():
            timer.stop()

    def connect_timer(self, name: str, slot: Callable):
        if name in self._timers:
            self._timers[name].timeout.connect(slot)

    def disconnect_timer(self, name: str, slot: Callable):
        if name in self._timers:
            self._timers[name].timeout.disconnect(slot)


class PerformanceOptimizer(QObject):
    def __init__(self, picker: FacePicker):
        super().__init__(picker)
        self._picker = picker
        self._cached_scene_items = None
        self._cache_valid = False

    def clear_cache(self):
        self._cached_scene_items = None
        self._cache_valid = False

    def get_cached_scene_items(self) -> List[QtWidgets.QGraphicsItem]:
        if not self._cache_valid:
            self._cached_scene_items = self._picker.scene.items()
            self._cache_valid = True
        return self._cached_scene_items

    def invalidate_cache(self):
        self._cache_valid = False

    def optimize_for_animation(self):
        if self._picker.update_manager:
            self._picker.update_manager.set_interval(500)

    def optimize_for_editing(self):
        if self._picker.update_manager:
            self._picker.update_manager.set_interval(100)


# ============================================================================
# Main FacePicker Class (merged from all phases)
# ============================================================================

# Import widgets from local module (assuming they exist in widgets.py)
from .widgets import PickerWidget, PickerButton, PickerCircle, PickerSlider, PickerJoystick, PickerRegion, PickerLabel

class FacePicker(QtWidgets.QMainWindow):
    # Signals
    control_selected = Signal(str)
    region_selected = Signal(str)
    picker_ready = Signal()
    layout_changed = Signal(str)
    mode_changed = Signal(PickerMode)

    def __init__(self, parent=None, name="FacePicker", load_default_layout=True):
        if parent is None:
            parent = get_maya_main_window()
        super().__init__(parent)

        self.setObjectName(name)
        self.setWindowTitle("Facial Control Picker")
        self.setMinimumSize(400, 500)
        self.resize(800, 700)

        # Internal state
        self._current_layout: Optional[PickerLayout] = None
        self._selected_controls: List[str] = []
        self._mode = PickerMode.SELECT
        self._is_docked = False
        self._initialized = False
        self._widgets: List[PickerWidget] = []

        # Settings
        self._settings = get_picker_settings()

        # Widget registry
        self.widget_registry = EnhancedWidgetRegistry()

        # Selection Manager
        self.selection_manager = SelectionManager(self)
        self.selection_manager.selection_changed.connect(self._on_selection_changed)
        self.selection_manager.control_selected.connect(self._on_control_selected)
        self.selection_manager.selection_cleared.connect(self._on_selection_cleared)

        # Maya Integration
        self.controller_resolver = ControllerResolver()
        self.maya_selection_handler = MayaSelectionHandler(self)
        self.undo_manager = UndoManager(self)

        # Filter Manager
        self.filter_manager = FilterManager(self.widget_registry)
        self.filter_manager.filter_changed.connect(self._apply_filters)

        # Runtime Services
        self.event_bus = EventBus(self)
        self.refresh_manager = RefreshManager(self, delay_ms=100)
        self.refresh_manager.refresh_requested.connect(self._on_refresh_requested)
        self.update_manager = UpdateManager(self, interval_ms=200)
        self.update_manager.add_task(self._background_update_task)
        self.timer_manager = TimerManager(self)
        self.performance_optimizer = PerformanceOptimizer(self)

        # Start updates
        self.update_manager.start()

        # Build UI
        self._build_menus()
        self._build_toolbar()
        self._build_status_bar()
        self._build_central_widget()
        self._build_dock_widgets()

        # Connect signals
        self._connect_signals()

        # Load default layout
        if load_default_layout:
            self._load_default_layout()

        # Apply theme
        self._apply_theme()

        # Restore geometry
        self._restore_geometry()

        self._initialized = True
        logger.info("FacePicker initialized successfully")

    # ------------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------------

    def _build_menus(self):
        menubar = self.menuBar()
        # File
        file_menu = menubar.addMenu("&File")
        file_menu.addAction("New Layout", self._new_layout, "Ctrl+N")
        file_menu.addAction("Open Layout...", self._open_layout, "Ctrl+O")
        file_menu.addAction("Save Layout", self._save_layout, "Ctrl+S")
        file_menu.addAction("Save Layout As...", self._save_layout_as, "Ctrl+Shift+S")
        file_menu.addSeparator()
        file_menu.addAction("Export Layout...", self._export_layout)
        file_menu.addAction("Import Layout...", self._import_layout)
        file_menu.addSeparator()
        file_menu.addAction("Close", self.close, "Ctrl+W")
        # Edit
        edit_menu = menubar.addMenu("&Edit")
        edit_menu.addAction("Undo", self.undo_manager.undo, "Ctrl+Z")
        edit_menu.addAction("Redo", self.undo_manager.redo, "Ctrl+Y")
        edit_menu.addSeparator()
        edit_menu.addAction("Select All", self._select_all, "Ctrl+A")
        edit_menu.addAction("Deselect All", self._deselect_all, "Ctrl+Shift+A")
        edit_menu.addSeparator()
        edit_menu.addAction("Lock Selection", self._lock_selection)
        edit_menu.addAction("Unlock Selection", self._unlock_selection)
        # View
        view_menu = menubar.addMenu("&View")
        view_menu.addAction("Zoom In", self._zoom_in, "Ctrl++")
        view_menu.addAction("Zoom Out", self._zoom_out, "Ctrl+-")
        view_menu.addAction("Fit View", self._fit_view, "A")
        view_menu.addAction("Reset View", self._reset_view, "Shift+A")
        view_menu.addSeparator()
        view_menu.addAction("Frame Selected in Maya", self._frame_selected_in_maya, "F")
        view_menu.addAction("Frame All Controls", self._frame_all_controls)
        view_menu.addSeparator()
        view_menu.addAction("Show Help", self._toggle_help)
        view_menu.addAction("Show Toolbar", self._toggle_toolbar)
        # Mode
        mode_menu = menubar.addMenu("&Mode")
        mode_group = QtWidgets.QActionGroup(self)
        for mode in PickerMode:
            action = mode_menu.addAction(mode.value.capitalize())
            action.setCheckable(True)
            action.setData(mode)
            action.triggered.connect(lambda checked, m=mode: self.set_mode(m))
            mode_group.addAction(action)
        for action in mode_group.actions():
            if action.data() == PickerMode.SELECT:
                action.setChecked(True)
        # Layout
        layout_menu = menubar.addMenu("&Layout")
        layout_menu.addAction("Load Built-in Layout...", self._load_builtin_layout)
        layout_menu.addSeparator()
        layout_menu.addAction("Add Widget", self._add_widget_dialog)
        layout_menu.addAction("Remove Widget", self._remove_widget)
        layout_menu.addAction("Edit Widget", self._edit_widget)
        # Help
        help_menu = menubar.addMenu("&Help")
        help_menu.addAction("Documentation", self._show_help)
        help_menu.addAction("About", self._show_about)

    def _build_toolbar(self):
        self.toolbar = self.addToolBar("Picker Tools")
        self.toolbar.setObjectName("PickerToolbar")
        self.toolbar.setMovable(False)
        self.toolbar.addWidget(QtWidgets.QLabel(" Layout: "))
        self.layout_combo = QtWidgets.QComboBox()
        self.layout_combo.setFixedWidth(120)
        self.layout_combo.addItems(["Full Face", "Eyes", "Mouth", "Brows", "Jaw"])
        self.layout_combo.currentTextChanged.connect(self._on_layout_combo_changed)
        self.toolbar.addWidget(self.layout_combo)
        self.toolbar.addSeparator()
        mode_group = QtWidgets.QActionGroup(self)
        self.mode_actions = {}
        for mode in [PickerMode.SELECT, PickerMode.PAN, PickerMode.ZOOM]:
            action = QtWidgets.QAction(mode.value.capitalize(), self)
            action.setCheckable(True)
            action.setData(mode)
            action.triggered.connect(lambda checked, m=mode: self.set_mode(m))
            self.toolbar.addAction(action)
            mode_group.addAction(action)
            self.mode_actions[mode] = action
        self.mode_actions[PickerMode.SELECT].setChecked(True)
        self.toolbar.addSeparator()
        zoom_in = QtWidgets.QAction("Zoom In", self)
        zoom_in.triggered.connect(self._zoom_in)
        self.toolbar.addAction(zoom_in)
        zoom_out = QtWidgets.QAction("Zoom Out", self)
        zoom_out.triggered.connect(self._zoom_out)
        self.toolbar.addAction(zoom_out)
        fit_view = QtWidgets.QAction("Fit", self)
        fit_view.setToolTip("Fit View")
        fit_view.triggered.connect(self._fit_view)
        self.toolbar.addAction(fit_view)
        self.toolbar.addSeparator()
        refresh = QtWidgets.QAction("Refresh", self)
        refresh.triggered.connect(self.refresh)
        self.toolbar.addAction(refresh)
        self.lock_action = QtWidgets.QAction("Lock", self)
        self.lock_action.setCheckable(True)
        self.lock_action.setToolTip("Lock/Unlock picker editing")
        self.lock_action.triggered.connect(self._toggle_lock)
        self.toolbar.addAction(self.lock_action)
        # Search bar
        self.search_bar = SearchBar()
        self.search_bar.setMaximumWidth(200)
        self.search_bar.search_changed.connect(self.filter_manager.set_search_text)
        self.toolbar.addWidget(self.search_bar)
        # Add/Edit/Delete actions
        add_action = QtWidgets.QAction("Add Widget", self)
        add_action.triggered.connect(self._add_widget_dialog)
        self.toolbar.addAction(add_action)
        self.edit_action = QtWidgets.QAction("Edit Widget", self)
        self.edit_action.triggered.connect(self._edit_selected_widget)
        self.edit_action.setEnabled(False)
        self.toolbar.addAction(self.edit_action)
        self.delete_action = QtWidgets.QAction("Delete Widget", self)
        self.delete_action.triggered.connect(self._delete_selected_widget)
        self.delete_action.setEnabled(False)
        self.toolbar.addAction(self.delete_action)

    def _build_status_bar(self):
        self.status_bar = QtWidgets.QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QtWidgets.QLabel("Ready")
        self.status_bar.addWidget(self.status_label)
        self.selection_label = QtWidgets.QLabel("Selected: 0")
        self.status_bar.addPermanentWidget(self.selection_label)
        self.mode_label = QtWidgets.QLabel("Mode: Select")
        self.status_bar.addPermanentWidget(self.mode_label)

    def _build_central_widget(self):
        settings = self._settings.get()
        self.scene = PickerScene(self, grid_size=settings.grid_size, show_grid=True, snap_to_grid=settings.snap_to_grid)
        self.view = InteractivePickerView(self.scene, self)
        self.setCentralWidget(self.view)

    def _build_dock_widgets(self):
        self.filter_panel = FilterPanel(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.filter_panel)

    def _connect_signals(self):
        self.scene.selectionChanged.connect(self._on_scene_selection_changed)
        self.layout_changed.connect(self.filter_panel.refresh)
        self.layout_changed.connect(self.performance_optimizer.invalidate_cache)

    def _apply_theme(self):
        from .themes import ThemeManager
        theme_mgr = ThemeManager()
        theme_mgr.apply_theme(self)

    def _restore_geometry(self):
        pass

    def _save_geometry(self):
        pass

    # ------------------------------------------------------------------------
    # Layout Management
    # ------------------------------------------------------------------------

    def _load_default_layout(self):
        from .layouts import build_layout
        layout = build_layout("Full Face")
        if layout:
            self.load_layout(layout)

    def load_layout(self, layout: PickerLayout):
        self.clear_layout()
        self._current_layout = layout
        self.widget_registry.clear()
        for widget in layout.widgets:
            self.scene.add_widget(widget)
            self._widgets.append(widget)
            self.widget_registry.add(widget)
            widget.clicked.connect(self._on_widget_clicked)
            widget.double_clicked.connect(self._on_widget_double_clicked)
        self._fit_view()
        self.layout_changed.emit(layout.name)
        self.picker_ready.emit()
        self._apply_filters()
        self.filter_panel.refresh()

    def clear_layout(self):
        for widget in self._widgets:
            self.scene.removeItem(widget)
        self._widgets.clear()
        self.widget_registry.clear()
        self._current_layout = None
        self._update_widget_actions()

    def _on_layout_combo_changed(self, name: str):
        from .layouts import build_layout
        layout = build_layout(name)
        if layout:
            self.load_layout(layout)
            self.status_label.setText(f"Loaded layout: {name}")

    # ------------------------------------------------------------------------
    # View Controls
    # ------------------------------------------------------------------------

    def _zoom_in(self):
        self.view.zoom_in()

    def _zoom_out(self):
        self.view.zoom_out()

    def _fit_view(self):
        self.view.fit_scene()

    def _reset_view(self):
        self.view.reset_zoom()
        self._fit_view()

    # ------------------------------------------------------------------------
    # Mode Management
    # ------------------------------------------------------------------------

    def set_mode(self, mode: PickerMode):
        self._mode = mode
        self.mode_label.setText(f"Mode: {mode.value.capitalize()}")
        for m, action in self.mode_actions.items():
            action.setChecked(m == mode)
        if mode == PickerMode.PAN:
            self.view.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
        elif mode == PickerMode.SELECT:
            self.view.setDragMode(QtWidgets.QGraphicsView.RubberBandDrag)
        else:
            self.view.setDragMode(QtWidgets.QGraphicsView.NoDrag)
        self.mode_changed.emit(mode)

    def get_mode(self) -> PickerMode:
        return self._mode

    # ------------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------------

    def _on_scene_selection_changed(self):
        selected_items = self.scene.selectedItems()
        control_names = []
        for item in selected_items:
            if hasattr(item, 'control_name') and item.control_name:
                control_names.append(item.control_name)
        self.selection_manager._block_sync = True
        self.selection_manager.clear()
        if control_names:
            self.selection_manager.select(control_names, add=False)
        self.selection_manager._block_sync = False
        self.selection_manager._update_selection_state()

    def _on_selection_changed(self, selected: List[str]):
        self._selected_controls = selected
        self.selection_label.setText(f"Selected: {len(selected)}")
        self.status_label.setText(f"Selected: {', '.join(selected[:3])}{'...' if len(selected) > 3 else ''}")
        self._update_scene_selection(selected)
        if selected:
            self.control_selected.emit(selected[0])
        self.maya_selection_handler.sync_to_maya()

    def _on_control_selected(self, control_name: str):
        pass

    def _on_selection_cleared(self):
        self.selection_label.setText("Selected: 0")
        self.status_label.setText("Ready")

    def _update_scene_selection(self, selected: List[str]):
        for widget in self._widgets:
            if hasattr(widget, 'control_name'):
                is_selected = widget.control_name in selected
                widget.setSelected(is_selected)
                if is_selected:
                    widget.set_color(200, 200, 50)
                else:
                    default_color = getattr(widget, '_default_color', (100, 100, 100))
                    widget.set_color(*default_color)

    def select_control(self, control_name: str):
        self.selection_manager.select(control_name, add=False)

    def select_controls(self, control_names: List[str], add: bool = False):
        self.selection_manager.select(control_names, add=add)

    def deselect_control(self, control_name: str):
        self.selection_manager.deselect(control_name)

    def clear_selection(self):
        self.selection_manager.clear()

    def toggle_control_selection(self, control_name: str):
        self.selection_manager.toggle(control_name)

    def get_selected_controls(self) -> List[str]:
        return self.selection_manager.get_selected()

    def select_region(self, region_name: str):
        region_widgets = self.widget_registry.get_widgets_by_region(region_name)
        control_names = [w.control_name for w in region_widgets if hasattr(w, 'control_name')]
        if control_names:
            self.select_controls(control_names)

    # ------------------------------------------------------------------------
    # Widget Management
    # ------------------------------------------------------------------------

    def _create_widget_from_data(self, data: Dict[str, Any]) -> Optional[PickerWidget]:
        control_name = data.get("control_name", "")
        label = data.get("label", "")
        widget_type = data.get("type", WidgetType.BUTTON)
        size = data.get("size", (50, 50))
        color = data.get("color", (100, 100, 100))

        if widget_type == WidgetType.BUTTON:
            widget = PickerButton(control_name=control_name, label=label, pos=(0, 0), size=size, color=color)
        elif widget_type == WidgetType.CIRCLE:
            widget = PickerCircle(control_name=control_name, label=label, pos=(0, 0), size=size, color=color)
        elif widget_type == WidgetType.SLIDER:
            widget = PickerSlider(control_name=control_name, label=label, pos=(0, 0), size=size, color=color,
                                  min_value=0.0, max_value=1.0, default_value=0.0)
        elif widget_type == WidgetType.JOYSTICK:
            widget = PickerJoystick(control_name_x=control_name, control_name_y="", label=label,
                                    pos=(0, 0), size=size, color=color)
        else:
            widget = PickerButton(control_name=control_name, label=label, pos=(0, 0), size=size, color=color)

        self.scene.add_widget(widget)
        self._widgets.append(widget)
        self.widget_registry.add(widget)
        widget.clicked.connect(self._on_widget_clicked)
        widget.double_clicked.connect(self._on_widget_double_clicked)
        widget.setAcceptHoverEvents(True)
        widget._default_color = color
        # Set region
        region = self.get_control_region(control_name) if control_name else "General"
        widget_id = widget.property("widget_id")
        if widget_id:
            self.widget_registry.set_region(widget_id, region)
        return widget

    def _add_widget_dialog(self):
        dialog = CreateWidgetDialog(self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            result = dialog.get_result()
            if result:
                widget = self._create_widget_from_data(result)
                if widget:
                    self._update_widget_actions()

    def _edit_selected_widget(self):
        selected = self.scene.selectedItems()
        if not selected:
            return
        widget = selected[0]
        if not isinstance(widget, PickerWidget):
            return
        self._edit_widget_dialog(widget)

    def _edit_widget_dialog(self, widget: PickerWidget):
        dialog = EditWidgetDialog(widget, self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            result = dialog.get_result()
            if result:
                self._apply_widget_edit(widget, result)

    def _apply_widget_edit(self, widget: PickerWidget, data: Dict[str, Any]):
        if "label" in data:
            widget.label = data["label"]
        if "size" in data:
            widget.set_size(data["size"][0], data["size"][1])
        if "color" in data:
            widget.set_color(*data["color"])
            widget._default_color = data["color"]
        widget.update()

    def _delete_selected_widget(self):
        selected = self.scene.selectedItems()
        if not selected:
            return
        reply = QtWidgets.QMessageBox.question(
            self, "Delete Widgets",
            f"Delete {len(selected)} selected widget(s)?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if reply != QtWidgets.QMessageBox.Yes:
            return
        for widget in selected:
            if isinstance(widget, PickerWidget):
                self._delete_widget(widget)

    def _delete_widget(self, widget: PickerWidget):
        widget_id = widget.property("widget_id")
        if widget_id:
            self.widget_registry.remove(widget_id)
        self.scene.removeItem(widget)
        if widget in self._widgets:
            self._widgets.remove(widget)
        self._update_widget_actions()

    def _update_widget_actions(self):
        selected = self.scene.selectedItems()
        has_selection = any(isinstance(w, PickerWidget) for w in selected)
        self.edit_action.setEnabled(has_selection)
        self.delete_action.setEnabled(has_selection)

    def _on_widget_clicked(self, widget: PickerWidget):
        if self._mode == PickerMode.SELECT:
            control_name = widget.control_name
            if control_name:
                modifiers = QtWidgets.QApplication.keyboardModifiers()
                if modifiers & Qt.ControlModifier:
                    self.toggle_control_selection(control_name)
                elif modifiers & Qt.ShiftModifier:
                    self.select_control(control_name)  # placeholder
                else:
                    self.select_control(control_name)

    def _on_widget_double_clicked(self, widget: PickerWidget):
        control_name = widget.control_name
        if control_name:
            self.maya_selection_handler.frame_control(control_name)

    def _toggle_favorite(self, widget: PickerWidget):
        widget_id = widget.property("widget_id")
        if not widget_id:
            return
        is_fav = self.widget_registry.toggle_favorite(widget_id)
        if is_fav:
            widget.set_color(255, 215, 0)
        else:
            default_color = getattr(widget, '_default_color', (100, 100, 100))
            widget.set_color(*default_color)
        widget.update()
        self._apply_filters()

    def _toggle_locked(self, widget: PickerWidget):
        widget_id = widget.property("widget_id")
        if not widget_id:
            return
        state = self.widget_registry.get_ui_state(widget_id)
        if state:
            state.locked = not state.locked
            self.widget_registry.set_locked(widget_id, state.locked)
            if state.locked:
                widget.set_color(128, 128, 128)
            else:
                default_color = getattr(widget, '_default_color', (100, 100, 100))
                widget.set_color(*default_color)
            widget.update()

    def _toggle_hidden(self, widget: PickerWidget):
        widget_id = widget.property("widget_id")
        if not widget_id:
            return
        state = self.widget_registry.get_ui_state(widget_id)
        if state:
            state.hidden = not state.hidden
            self.widget_registry.set_hidden(widget_id, state.hidden)
            self._apply_filters()

    # ------------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------------

    def _apply_filters(self):
        filtered = self.filter_manager.get_filtered_widgets()
        for widget in self._widgets:
            widget.setVisible(widget in filtered)

    # ------------------------------------------------------------------------
    # Maya Integration
    # ------------------------------------------------------------------------

    def _frame_selected_in_maya(self):
        selected = self.selection_manager.get_selected()
        if selected:
            self.maya_selection_handler.frame_control(selected[0])

    def _frame_all_controls(self):
        if cmds:
            controls = []
            for widget in self.widget_registry.list_widgets():
                if hasattr(widget, 'control_name') and widget.control_name:
                    resolved = self.controller_resolver.resolve_control(widget.control_name)
                    if resolved:
                        controls.append(resolved)
            if controls:
                cmds.select(controls, replace=True)
                cmds.viewFit()

    def _select_in_maya(self):
        self.maya_selection_handler.sync_to_maya()

    def resolve_control(self, name: str) -> Optional[str]:
        return self.controller_resolver.resolve_control(name)

    def get_control_side(self, name: str) -> str:
        return self.controller_resolver.get_side(name)

    def get_control_region(self, name: str) -> str:
        return self.controller_resolver.get_region(name)

    def validate_controls(self) -> Dict[str, bool]:
        result = {}
        for widget in self.widget_registry.list_widgets():
            if hasattr(widget, 'control_name') and widget.control_name:
                name = widget.control_name
                resolved = self.resolve_control(name)
                result[name] = resolved is not None
        return result

    def highlight_invalid_controls(self):
        for widget in self.widget_registry.list_widgets():
            if hasattr(widget, 'control_name') and widget.control_name:
                if not self.resolve_control(widget.control_name):
                    widget.set_color(255, 80, 80)
                    widget.update()

    def _frame_control_in_maya(self, control_name: str):
        self.maya_selection_handler.frame_control(control_name)

    # ------------------------------------------------------------------------
    # Refresh & Update
    # ------------------------------------------------------------------------

    def refresh(self):
        if self._current_layout:
            self.load_layout(self._current_layout)
        self.performance_optimizer.invalidate_cache()
        self._apply_filters()
        self.overlay_manager.update_overlays()
        self.event_bus.publish("picker_refreshed", None)

    def _on_refresh_requested(self):
        self.refresh()

    def _background_update_task(self):
        if not hasattr(self, '_update_counter'):
            self._update_counter = 0
        self._update_counter += 1
        if self._update_counter % 10 == 0:
            self._validate_controls_background()

    def _validate_controls_background(self):
        widgets = self.widget_registry.list_widgets()
        if not widgets:
            return
        if not hasattr(self, '_validate_index'):
            self._validate_index = 0
        start = self._validate_index
        end = min(start + 5, len(widgets))
        for i in range(start, end):
            widget = widgets[i]
            if hasattr(widget, 'control_name') and widget.control_name:
                resolved = self.resolve_control(widget.control_name)
                widget_id = widget.property("widget_id")
                if not resolved:
                    if widget_id:
                        state = self.widget_registry.get_ui_state(widget_id)
                        if state and not state.locked:
                            widget.set_color(255, 80, 80)
                            widget.update()
                else:
                    if widget_id:
                        default_color = getattr(widget, '_default_color', (100, 100, 100))
                        widget.set_color(*default_color)
                        widget.update()
        self._validate_index = (self._validate_index + 5) % len(widgets)

    # ------------------------------------------------------------------------
    # Menus Actions (stubs)
    # ------------------------------------------------------------------------

    def _new_layout(self): self.clear_layout(); self.status_label.setText("New layout created")
    def _open_layout(self): pass
    def _save_layout(self): self.save_current_layout()
    def _save_layout_as(self): pass
    def _export_layout(self): pass
    def _import_layout(self): pass
    def _undo(self): self.undo_manager.undo()
    def _redo(self): self.undo_manager.redo()
    def _select_all(self):
        for widget in self._widgets:
            widget.setSelected(True)
    def _deselect_all(self): self.scene.clearSelection()
    def _lock_selection(self): pass
    def _unlock_selection(self): pass
    def _toggle_help(self): pass
    def _toggle_toolbar(self): self.toolbar.setVisible(not self.toolbar.isVisible())
    def _load_builtin_layout(self): pass
    def _remove_widget(self): self._delete_selected_widget()
    def _edit_widget(self): self._edit_selected_widget()
    def _show_help(self):
        QtWidgets.QMessageBox.information(
            self, "Picker Help",
            "Facial Control Picker\n\nSelect controls by clicking.\n"
            "Use the toolbar to switch modes.\n"
            "Zoom with Ctrl+Mouse Wheel or toolbar buttons.\n"
            "Pan with Middle Mouse Button or Pan mode.\n"
            "Right-click for context menu."
        )
    def _show_about(self):
        QtWidgets.QMessageBox.about(
            self, "About FacePicker",
            f"Facial Control Picker\nVersion {__version__}\n\n"
            "A facial control picker for Maya Faceit.\n"
            "Author: Maya FaceIT Team"
        )
    def _toggle_lock(self, checked: bool):
        self.status_label.setText("Locked" if checked else "Unlocked")

    # ------------------------------------------------------------------------
    # Public API Methods
    # ------------------------------------------------------------------------

    def show(self):
        super().show()
        self.raise_()
        self.activateWindow()
        self.event_bus.publish("picker_shown", None)

    def hide(self):
        super().hide()
        self.event_bus.publish("picker_hidden", None)

    def toggle(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()

    def is_visible(self) -> bool:
        return self.isVisible()

    def load_layout_by_name(self, name: str) -> bool:
        from .layouts import build_layout
        layout = build_layout(name)
        if layout is None:
            logger.warning(f"Layout '{name}' not found.")
            return False
        self.load_layout(layout)
        return True

    def get_current_layout_name(self) -> Optional[str]:
        if self._current_layout:
            return self._current_layout.name
        return None

    def save_current_layout(self, filepath: Optional[str] = None) -> bool:
        from .serialization import save_picker
        if filepath is None:
            name = self.get_current_layout_name()
            if name:
                filepath = f"{name}.pklayout"
            else:
                filepath = "picker_layout.pklayout"
        return save_picker(self, filepath)

    def load_layout_from_file(self, filepath: str) -> bool:
        from .serialization import load_picker
        return load_picker(self, filepath)

    def frame_selection(self):
        selected = self.get_selected_controls()
        if selected:
            self.maya_selection_handler.frame_control(selected[0])
        else:
            self._frame_all_controls()

    def zoom_to_selection(self):
        selected_widgets = []
        for widget in self._widgets:
            if hasattr(widget, 'control_name') and widget.control_name in self.get_selected_controls():
                selected_widgets.append(widget)
        if selected_widgets:
            rect = QtCore.QRectF()
            for w in selected_widgets:
                rect = rect.united(w.sceneBoundingRect())
            self.view.fitInView(rect, Qt.KeepAspectRatio)

    def sync_with_maya(self):
        self.maya_selection_handler.sync_from_maya()

    def zoom_in(self, factor: float = 1.2):
        self.view.zoom_in(factor)

    def zoom_out(self, factor: float = 1.2):
        self.view.zoom_out(factor)

    def zoom_to_fit(self):
        self._fit_view()

    def reset_view(self):
        self._reset_view()

    def set_grid_visibility(self, visible: bool):
        self.scene.set_show_grid(visible)

    def set_snap_to_grid(self, enabled: bool):
        self.scene.set_snap_to_grid(enabled)

    def add_widget(self, control_name: str, label: str = "", widget_type: str = "button",
                   size: Tuple[int, int] = (50, 50), color: Tuple[int, int, int] = (100, 100, 100)) -> Optional[PickerWidget]:
        data = {
            "control_name": control_name,
            "label": label,
            "type": WidgetType(widget_type.lower()),
            "size": size,
            "color": color,
        }
        return self._create_widget_from_data(data)

    def remove_widget(self, widget: PickerWidget) -> bool:
        if widget in self._widgets:
            self._delete_widget(widget)
            return True
        return False

    def get_widget_by_control(self, control_name: str) -> Optional[PickerWidget]:
        return self.widget_registry.get_by_control(control_name)

    def get_all_widgets(self) -> List[PickerWidget]:
        return self.widget_registry.list_widgets()

    def lock_widget(self, widget: PickerWidget):
        widget_id = widget.property("widget_id")
        if widget_id:
            self.widget_registry.set_locked(widget_id, True)

    def unlock_widget(self, widget: PickerWidget):
        widget_id = widget.property("widget_id")
        if widget_id:
            self.widget_registry.set_locked(widget_id, False)

    def hide_widget(self, widget: PickerWidget):
        widget_id = widget.property("widget_id")
        if widget_id:
            self.widget_registry.set_hidden(widget_id, True)

    def show_widget(self, widget: PickerWidget):
        widget_id = widget.property("widget_id")
        if widget_id:
            self.widget_registry.set_hidden(widget_id, False)

    def toggle_favorite_widget(self, widget: PickerWidget) -> bool:
        widget_id = widget.property("widget_id")
        if widget_id:
            return self.widget_registry.toggle_favorite(widget_id)
        return False

    def is_favorite_widget(self, widget: PickerWidget) -> bool:
        widget_id = widget.property("widget_id")
        if widget_id:
            return self.widget_registry.is_favorite(widget_id)
        return False

    def get_favorite_widgets(self) -> List[PickerWidget]:
        return self.widget_registry.get_favorites()

    def save_session(self, filepath: Optional[str] = None) -> bool:
        return self.save_current_layout(filepath)

    def restore_session(self, filepath: str) -> bool:
        return self.load_layout_from_file(filepath)

    def load_character(self, character_name: str) -> bool:
        from .layouts import LayoutManager
        layout_mgr = LayoutManager()
        if character_name in layout_mgr.list_layouts():
            return self.load_layout_by_name(character_name)
        if self.load_layout_by_name(character_name):
            return True
        logger.warning(f"No layout found for character '{character_name}'")
        return False

    def shutdown(self):
        self.maya_selection_handler.cleanup()
        self.update_manager.stop()
        self.timer_manager.stop_all()
        self.performance_optimizer.clear_cache()
        self.close()

    def get_version(self) -> str:
        return __version__

    def get_statistics(self) -> Dict[str, Any]:
        return {
            "widgets": self.widget_registry.count(),
            "layout": self.get_current_layout_name(),
            "selected": len(self.get_selected_controls()),
            "visible": self.isVisible(),
            "zoom": self.view.get_zoom_level(),
            "mode": self.get_mode().value,
        }

    # ------------------------------------------------------------------------
    # Event Bus Helpers
    # ------------------------------------------------------------------------

    def emit_event(self, event_type: str, data: Any = None):
        self.event_bus.publish(event_type, data)

    def subscribe_event(self, event_type: str, callback: Callable):
        self.event_bus.subscribe(event_type, callback)

    def unsubscribe_event(self, event_type: str, callback: Callable):
        self.event_bus.unsubscribe(event_type, callback)

    # ------------------------------------------------------------------------
    # Performance
    # ------------------------------------------------------------------------

    def set_performance_mode(self, mode: str):
        if mode == "animation":
            self.performance_optimizer.optimize_for_animation()
        elif mode == "editing":
            self.performance_optimizer.optimize_for_editing()

    # ------------------------------------------------------------------------
    # Timers
    # ------------------------------------------------------------------------

    def create_timer(self, name: str, interval_ms: int, single_shot: bool = False) -> QtCore.QTimer:
        return self.timer_manager.create_timer(name, interval_ms, single_shot)

    def start_timer(self, name: str):
        self.timer_manager.start_timer(name)

    def stop_timer(self, name: str):
        self.timer_manager.stop_timer(name)

    def connect_timer(self, name: str, slot: Callable):
        self.timer_manager.connect_timer(name, slot)

    # ------------------------------------------------------------------------
    # Override closeEvent
    # ------------------------------------------------------------------------

    def closeEvent(self, event):
        self.maya_selection_handler.cleanup()
        self.update_manager.stop()
        self.timer_manager.stop_all()
        self._save_geometry()
        super().closeEvent(event)


# ============================================================================
# Global Picker Instance and Factory Functions
# ============================================================================

_picker_instance: Optional[FacePicker] = None

def get_picker() -> FacePicker:
    global _picker_instance
    if _picker_instance is None:
        _picker_instance = FacePicker()
    return _picker_instance

def create_picker(**kwargs) -> FacePicker:
    return FacePicker(**kwargs)

def show_picker():
    get_picker().show()

def hide_picker():
    get_picker().hide()

def toggle_picker():
    get_picker().toggle()


# ============================================================================
# Public API Exports
# ============================================================================

__all__ = [
    # Main class
    "FacePicker",
    # Singleton access
    "get_picker",
    "create_picker",
    # Convenience functions
    "show_picker",
    "hide_picker",
    "toggle_picker",
    # Exceptions
    "PickerError",
    "PickerInitError",
    "PickerLayoutError",
    "PickerWidgetError",
    "PickerSyncError",
    # Enums
    "PickerMode",
    "SelectionMode",
    "DisplayMode",
    "WidgetType",
    "WidgetState",
    # Dataclasses
    "PickerConfig",
    "PickerSession",
    "ControlInfo",
]