"""
ui/pages/tools.py

Utility tools: mirror, normalize, optimize, bake.
"""

from __future__ import annotations

from .. import QT_BINDING
if QT_BINDING:
    from PySide2 import QtWidgets, QtCore, QtGui
    from PySide2.QtWidgets import QWidget, QVBoxLayout, QPushButton, QGroupBox, QFormLayout, QCheckBox, QComboBox
else:
    QWidget = object


class ToolsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        # Mirror group
        mirror_group = QGroupBox("Mirror")
        mirror_layout = QFormLayout(mirror_group)
        self.mirror_dir = QComboBox()
        self.mirror_dir.addItems(["Left→Right", "Right→Left"])
        self.mirror_weights = QCheckBox("Mirror Weights")
        mirror_layout.addRow("Direction:", self.mirror_dir)
        mirror_layout.addRow("", self.mirror_weights)
        mirror_btn = QPushButton("Mirror Selected")
        mirror_btn.clicked.connect(self._mirror)
        mirror_layout.addRow(mirror_btn)
        layout.addWidget(mirror_group)

        # Normalize group
        norm_group = QGroupBox("Normalize")
        norm_layout = QFormLayout(norm_group)
        self.norm_range = QComboBox()
        self.norm_range.addItems(["0–1", "-1–1"])
        norm_layout.addRow("Range:", self.norm_range)
        norm_btn = QPushButton("Normalize")
        norm_btn.clicked.connect(self._normalize)
        norm_layout.addRow(norm_btn)
        layout.addWidget(norm_group)

        # Optimize group
        opt_group = QGroupBox("Optimize")
        opt_layout = QFormLayout(opt_group)
        self.opt_level = QComboBox()
        self.opt_level.addItems(["Low", "Medium", "High"])
        opt_layout.addRow("Level:", self.opt_level)
        opt_btn = QPushButton("Optimize")
        opt_btn.clicked.connect(self._optimize)
        opt_layout.addRow(opt_btn)
        layout.addWidget(opt_group)

        layout.addStretch()

    def _mirror(self): pass
    def _normalize(self): pass
    def _optimize(self): pass