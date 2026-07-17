"""
ui/pages/rig.py

Rig building and configuration.
"""

from __future__ import annotations

from .. import QT_BINDING
if QT_BINDING:
    from PySide2 import QtWidgets, QtCore, QtGui
    from PySide2.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QComboBox, QLineEdit, QPushButton, QLabel, QCheckBox
else:
    QWidget = object


class RigPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.template_combo = QComboBox()
        self.template_combo.addItems(["Face Rig v1", "Face Rig v2", "Full Body"])

        self.mesh_edit = QLineEdit()
        self.mesh_edit.setPlaceholderText("Select mesh...")

        self.joint_prefix_edit = QLineEdit("face_")

        self.mirror_check = QCheckBox("Enable Mirroring")
        self.mirror_check.setChecked(True)

        form.addRow("Rig Template:", self.template_combo)
        form.addRow("Base Mesh:", self.mesh_edit)
        form.addRow("Joint Prefix:", self.joint_prefix_edit)
        form.addRow("", self.mirror_check)

        layout.addLayout(form)

        build_btn = QPushButton("Build Rig")
        build_btn.clicked.connect(self._build)
        layout.addWidget(build_btn)

        # Statistics placeholder
        stats = QLabel("Rig Statistics: Not built")
        layout.addWidget(stats)

        layout.addStretch()

    def _build(self):
        pass