"""
ui/pages/picker.py

Expression picker with interactive canvas.
"""

from __future__ import annotations

from .. import QT_BINDING
if QT_BINDING:
    from PySide2 import QtWidgets, QtCore, QtGui
    from PySide2.QtWidgets import QWidget, QVBoxLayout
else:
    QWidget = object

from ..widgets import PickerCanvas


class PickerPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.canvas = PickerCanvas()
        layout.addWidget(self.canvas)