# ui/panels/inspector_panel.py

"""
ui/panels/inspector_panel.py

Inspector – shows details of selected object.
"""

from __future__ import annotations

from ..qt_imports import (
    QWidget, QVBoxLayout, QLabel, QFormLayout, QLineEdit, QDoubleSpinBox, QCheckBox
)


class InspectorPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        self.object_label = QLabel("No selection")
        layout.addWidget(self.object_label)

        form = QFormLayout()
        self.name_edit = QLineEdit()
        self.type_label = QLabel("Unknown")
        self.weight_spin = QDoubleSpinBox()
        self.weight_spin.setRange(0.0, 1.0)
        self.weight_spin.setSingleStep(0.01)
        self.locked_check = QCheckBox()

        form.addRow("Name:", self.name_edit)
        form.addRow("Type:", self.type_label)
        form.addRow("Weight:", self.weight_spin)
        form.addRow("Locked:", self.locked_check)

        layout.addLayout(form)
        layout.addStretch()

        # Sample data
        self.name_edit.setText("jaw_ctrl")
        self.type_label.setText("Controller")
        self.weight_spin.setValue(0.5)