# ui/dialogs/project_settings.py

"""
ui/dialogs/project_settings.py

Project-specific settings dialog.
"""

from __future__ import annotations

from ..qt_imports import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QPushButton, QHBoxLayout, QSpinBox
)


class ProjectSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Project Settings")
        self.resize(500, 300)

        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.name_edit = QLineEdit("MyProject")
        self.path_edit = QLineEdit("C:/Projects/MyProject")
        self.template_combo = QComboBox()
        self.template_combo.addItems(["Default", "Cartoon", "Realistic", "Stylized"])
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(24, 120)
        self.fps_spin.setValue(60)

        form.addRow("Project Name:", self.name_edit)
        form.addRow("Path:", self.path_edit)
        form.addRow("Rig Template:", self.template_combo)
        form.addRow("FPS:", self.fps_spin)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("Save")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)