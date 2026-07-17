# ui/dialogs/preferences.py

"""
ui/dialogs/preferences.py

Global preferences dialog.
"""

from __future__ import annotations

from ..qt_imports import (
    QDialog, QTabWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFormLayout, QLineEdit, QCheckBox, QComboBox, QWidget
)


class PreferencesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.resize(600, 450)

        layout = QVBoxLayout(self)

        # Tab widget
        tabs = QTabWidget()

        # General tab
        general = QWidget()
        g_form = QFormLayout(general)
        self.language_combo = QComboBox()
        self.language_combo.addItems(["English", "Chinese", "Japanese"])
        self.auto_save_check = QCheckBox()
        self.auto_save_check.setChecked(True)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light", "High Contrast"])
        g_form.addRow("Language:", self.language_combo)
        g_form.addRow("Auto-save:", self.auto_save_check)
        g_form.addRow("Theme:", self.theme_combo)
        tabs.addTab(general, "General")

        # Blendshapes tab
        bs = QWidget()
        bs_form = QFormLayout(bs)
        self.weight_range = QComboBox()
        self.weight_range.addItems(["0–1", "-1–1"])
        self.auto_normalize = QCheckBox()
        self.auto_normalize.setChecked(True)
        bs_form.addRow("Default Weight Range:", self.weight_range)
        bs_form.addRow("Auto-normalize:", self.auto_normalize)
        tabs.addTab(bs, "Blendshapes")

        # ARKit tab
        arkit = QWidget()
        a_form = QFormLayout(arkit)
        self.arkit_preset = QComboBox()
        self.arkit_preset.addItems(["Apple ARKit", "MetaHuman", "Custom"])
        a_form.addRow("Mapping Preset:", self.arkit_preset)
        tabs.addTab(arkit, "ARKit")

        # Mocap tab
        mocap = QWidget()
        m_form = QFormLayout(mocap)
        self.mocap_device = QComboBox()
        self.mocap_device.addItems(["LiveLink", "MediaPipe", "FaceCap"])
        self.mocap_port = QLineEdit("8080")
        m_form.addRow("Default Device:", self.mocap_device)
        m_form.addRow("Port:", self.mocap_port)
        tabs.addTab(mocap, "Mocap")

        layout.addWidget(tabs)

        # Buttons
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self._apply)
        btn_layout.addStretch()
        btn_layout.addWidget(apply_btn)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _apply(self):
        # Save settings
        pass

    def accept(self):
        self._apply()
        super().accept()