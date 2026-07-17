# ui/panels/output_panel.py

"""
ui/panels/output_panel.py

Output panel – shows command results.
"""

from __future__ import annotations

from ..qt_imports import QWidget, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout


class OutputPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setStyleSheet("font-family: monospace;")
        layout.addWidget(self.output_text)

        controls = QHBoxLayout()
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.output_text.clear)
        controls.addWidget(clear_btn)
        controls.addStretch()
        layout.addLayout(controls)

    def write(self, text: str):
        self.output_text.append(text)