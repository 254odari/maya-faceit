# ui/panels/log_panel.py

"""
ui/panels/log_panel.py

Log panel – shows system logs.
"""

from __future__ import annotations

from ..qt_imports import QWidget, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout


class LogPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("font-family: monospace;")
        layout.addWidget(self.log_text)

        # Sample log
        self.log_text.append("INFO: FaceIT initialized")
        self.log_text.append("INFO: Scene scanned (2 meshes, 1 blendshape)")

        controls = QHBoxLayout()
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.log_text.clear)
        controls.addWidget(clear_btn)
        controls.addStretch()
        layout.addLayout(controls)

    def append(self, msg: str):
        self.log_text.append(msg)