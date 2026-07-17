"""
ui/pages/blendshapes.py

Blendshape creation, editing, and library.
"""

from __future__ import annotations

from .. import QT_BINDING
if QT_BINDING:
    from PySide2 import QtWidgets, QtCore, QtGui
    from PySide2.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, QLabel, QDoubleSpinBox
else:
    QWidget = object


class BlendshapesPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        # Target list
        self.target_list = QListWidget()
        self.target_list.addItems(["Smile", "Frown", "EyeBlink_L", "EyeBlink_R", "MouthOpen"])
        layout.addWidget(self.target_list)

        # Controls
        controls = QHBoxLayout()
        self.weight_spin = QDoubleSpinBox()
        self.weight_spin.setRange(0.0, 1.0)
        self.weight_spin.setSingleStep(0.01)
        controls.addWidget(QLabel("Weight:"))
        controls.addWidget(self.weight_spin)
        layout.addLayout(controls)

        # Buttons
        btn_layout = QHBoxLayout()
        create_btn = QPushButton("Create Target")
        create_btn.clicked.connect(self._create)
        mirror_btn = QPushButton("Mirror")
        mirror_btn.clicked.connect(self._mirror)
        optimize_btn = QPushButton("Optimize")
        optimize_btn.clicked.connect(self._optimize)
        btn_layout.addWidget(create_btn)
        btn_layout.addWidget(mirror_btn)
        btn_layout.addWidget(optimize_btn)
        layout.addLayout(btn_layout)

        layout.addStretch()

    def _create(self): pass
    def _mirror(self): pass
    def _optimize(self): pass