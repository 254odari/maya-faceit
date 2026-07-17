# ui/dialogs/symmetry_dialog.py

"""
ui/dialogs/symmetry_dialog.py

Symmetry detection and fixing dialog.
"""

from __future__ import annotations

from ..qt_imports import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QCheckBox,
    QPushButton, QHBoxLayout, QDoubleSpinBox
)


class SymmetryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Symmetry Tools")
        self.resize(400, 250)

        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.axis_combo = QComboBox()
        self.axis_combo.addItems(["X", "Y", "Z"])
        self.tolerance_spin = QDoubleSpinBox()
        self.tolerance_spin.setRange(0.001, 1.0)
        self.tolerance_spin.setSingleStep(0.01)
        self.tolerance_spin.setValue(0.01)
        self.fix_mesh_check = QCheckBox("Fix Mesh Symmetry")
        self.fix_mesh_check.setChecked(True)
        self.fix_weights_check = QCheckBox("Fix Weight Symmetry")
        self.fix_weights_check.setChecked(True)

        form.addRow("Axis:", self.axis_combo)
        form.addRow("Tolerance:", self.tolerance_spin)
        form.addRow("", self.fix_mesh_check)
        form.addRow("", self.fix_weights_check)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("Apply")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)