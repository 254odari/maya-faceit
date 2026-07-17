# ui/widgets/inspectors.py

"""
ui/widgets/inspectors.py

Inspector widgets for editing properties.
"""

from __future__ import annotations

from typing import Any

from ..qt_imports import (
    QWidget, QFormLayout, QLineEdit, QDoubleSpinBox,
    QCheckBox, QComboBox, QLabel, QPushButton
)


class TargetInspector(QWidget):
    """Inspector for a blendshape target."""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QFormLayout(self)
        self.name_edit = QLineEdit()
        self.weight_spin = QDoubleSpinBox()
        self.weight_spin.setRange(0.0, 1.0)
        self.weight_spin.setSingleStep(0.01)
        self.locked_check = QCheckBox()
        self.source_label = QLabel("user")
        layout.addRow("Name:", self.name_edit)
        layout.addRow("Weight:", self.weight_spin)
        layout.addRow("Locked:", self.locked_check)
        layout.addRow("Source:", self.source_label)


class ControllerInspector(QWidget):
    """Inspector for a rig controller."""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QFormLayout(self)
        self.name_edit = QLineEdit()
        self.shape_combo = QComboBox()
        self.shape_combo.addItems(["circle", "square", "triangle", "diamond"])
        self.radius_spin = QDoubleSpinBox()
        self.radius_spin.setRange(0.1, 10.0)
        self.radius_spin.setValue(2.5)
        self.color_btn = QPushButton("Choose Color")
        layout.addRow("Name:", self.name_edit)
        layout.addRow("Shape:", self.shape_combo)
        layout.addRow("Radius:", self.radius_spin)
        layout.addRow("Color:", self.color_btn)


class PropertyInspector(QWidget):
    """Generic property inspector with key-value pairs."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QFormLayout(self)
        self._fields = {}

    def add_property(self, label: str, value: str = "") -> QLineEdit:
        """Add a property field."""
        edit = QLineEdit(value)
        self.layout.addRow(label, edit)
        self._fields[label] = edit
        return edit

    def add_float_property(self, label: str, value: float = 0.0,
                           min_val: float = 0.0, max_val: float = 1.0) -> QDoubleSpinBox:
        """Add a float property with spinbox."""
        spin = QDoubleSpinBox()
        spin.setRange(min_val, max_val)
        spin.setValue(value)
        self.layout.addRow(label, spin)
        self._fields[label] = spin
        return spin

    def get_value(self, label: str) -> Any:
        """Get the value of a property."""
        field = self._fields.get(label)
        if field:
            if isinstance(field, QLineEdit):
                return field.text()
            elif isinstance(field, QDoubleSpinBox):
                return field.value()
        return None