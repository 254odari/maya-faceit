# ui/panels/progress_panel.py

"""
ui/panels/progress_panel.py

Progress panel – shows ongoing operations.
"""

from __future__ import annotations

from ..qt_imports import QWidget, QVBoxLayout, QProgressBar, QLabel, QPushButton


class ProgressPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        self.label = QLabel("No active tasks")
        layout.addWidget(self.label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel)
        layout.addWidget(self.cancel_btn)

    def start_task(self, task_name: str):
        self.label.setText(task_name)
        self.progress.setValue(0)
        self.cancel_btn.setEnabled(True)

    def update_progress(self, value: int):
        self.progress.setValue(value)

    def finish_task(self):
        self.label.setText("Completed")
        self.cancel_btn.setEnabled(False)

    def _cancel(self):
        pass