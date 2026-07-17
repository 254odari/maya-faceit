# ui/dialogs/bake_dialog.py

"""
ui/dialogs/bake_dialog.py

Bake animation/weights dialog.
"""

from __future__ import annotations

from ..qt_imports import (
    QDialog, QVBoxLayout, QFormLayout, QSpinBox, QCheckBox,
    QPushButton, QHBoxLayout
)


class BakeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bake Options")
        self.resize(400, 250)

        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.start_frame = QSpinBox()
        self.start_frame.setRange(1, 10000)
        self.start_frame.setValue(1)
        self.end_frame = QSpinBox()
        self.end_frame.setRange(1, 10000)
        self.end_frame.setValue(100)
        self.bake_weights = QCheckBox("Bake Weights")
        self.bake_weights.setChecked(True)
        self.bake_transforms = QCheckBox("Bake Transforms")
        self.bake_transforms.setChecked(False)
        self.bake_blendshapes = QCheckBox("Bake Blendshapes")
        self.bake_blendshapes.setChecked(True)

        form.addRow("Start Frame:", self.start_frame)
        form.addRow("End Frame:", self.end_frame)
        form.addRow("", self.bake_weights)
        form.addRow("", self.bake_transforms)
        form.addRow("", self.bake_blendshapes)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("Bake")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)