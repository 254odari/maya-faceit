# ui/widgets/color_picker.py

"""
ui/widgets/color_picker.py

Color picker widgets.
"""

from __future__ import annotations

from typing import Optional

from ..qt_imports import QPushButton, QColorDialog, QWidget, QColor, Signal


class ColorPickerButton(QPushButton):
    """Button that opens a color dialog."""
    color_changed = Signal(QColor)

    def __init__(self, color: Optional[QColor] = None, parent=None):
        if color is None:
            color = QColor("#4a90d9")
        super().__init__(parent)
        self._color = color
        self.setFixedSize(24, 24)
        self.setStyleSheet("border: 1px solid #555; border-radius: 2px;")
        self.clicked.connect(self._pick_color)
        self._update_color()

    def _update_color(self) -> None:
        self.setStyleSheet(f"background: {self._color.name()}; border: 1px solid #555; border-radius: 2px;")

    def _pick_color(self) -> None:
        color = QColorDialog.getColor(self._color, self, "Choose Color")
        if color.isValid():
            self._color = color
            self._update_color()
            self.color_changed.emit(color)

    def get_color(self) -> QColor:
        return self._color


class ColorSwatch(QWidget):
    """A small color swatch display."""
    def __init__(self, color: Optional[QColor] = None, parent=None):
        super().__init__(parent)
        if color is None:
            color = QColor("#4a90d9")
        self._color = color
        self.setFixedSize(20, 20)
        self.setStyleSheet(f"background: {color.name()}; border: 1px solid #555; border-radius: 2px;")

    def set_color(self, color: QColor) -> None:
        self._color = color
        self.setStyleSheet(f"background: {color.name()}; border: 1px solid #555; border-radius: 2px;")