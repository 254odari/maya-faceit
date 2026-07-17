"""
ui/pages/expressions.py

Expression library and blending.
"""

from __future__ import annotations

from .. import QT_BINDING
if QT_BINDING:
    from PySide2 import QtWidgets, QtCore, QtGui
    from PySide2.QtWidgets import QWidget, QVBoxLayout, QListWidget, QPushButton, QHBoxLayout, QLabel, QDoubleSpinBox
else:
    QWidget = object


class ExpressionsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        self.expr_list = QListWidget()
        self.expr_list.addItems(["Happy", "Sad", "Angry", "Surprised", "Squint"])
        layout.addWidget(self.expr_list)

        controls = QHBoxLayout()
        self.blend_spin = QDoubleSpinBox()
        self.blend_spin.setRange(0.0, 1.0)
        controls.addWidget(QLabel("Blend:"))
        controls.addWidget(self.blend_spin)
        layout.addLayout(controls)

        btn_layout = QHBoxLayout()
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self._apply)
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(apply_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

        layout.addStretch()

    def _apply(self): pass
    def _save(self): pass