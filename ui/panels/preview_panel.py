# ui/panels/preview_panel.py

"""
ui/panels/preview_panel.py

Preview panel – 3D viewer placeholder.
"""

from __future__ import annotations

from ..qt_imports import Qt, QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout


class PreviewPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        # Placeholder for 3D view
        self.view_label = QLabel("3D Preview")
        self.view_label.setAlignment(Qt.AlignCenter)
        self.view_label.setStyleSheet("background-color: #1a1a1a; border: 1px solid #444;")
        self.view_label.setMinimumHeight(200)
        layout.addWidget(self.view_label)

        # Controls
        controls = QHBoxLayout()
        for text in ["Fit", "Orbit", "Zoom"]:
            btn = QPushButton(text)
            btn.clicked.connect(self._view_action)
            controls.addWidget(btn)
        layout.addLayout(controls)

    def _view_action(self):
        pass