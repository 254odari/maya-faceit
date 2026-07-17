"""
ui/application/status_bar.py

Status bar with project info, progress, and message display.
"""

from __future__ import annotations
import logging 
from ..qt_imports import QStatusBar, QLabel, QProgressBar, QTimer

logger = logging.getLogger(__name__)


class StatusBar(QStatusBar):
    """
    Custom status bar with project info, progress bar, and message area.

    Provides:
    - Project name display (left)
    - Progress bar (center)
    - Status messages (right)
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        # Left: project info
        self.project_label = QLabel("Project: None")
        self.addWidget(self.project_label)

        # Middle: progress bar (initially hidden)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setVisible(False)
        self.addWidget(self.progress_bar, 1)

        # Right: status message
        self.status_label = QLabel("Ready")
        self.addPermanentWidget(self.status_label)

    def show_message(self, msg: str, duration: int = 2000) -> None:
        """
        Show a temporary status message.

        Args:
            msg: Message text.
            duration: Time in milliseconds to display. If 0, stays indefinitely.
        """
        self.status_label.setText(msg)
        if duration > 0:
            QTimer.singleShot(duration, lambda: self.status_label.setText("Ready"))

    def set_project(self, project_name: str) -> None:
        """Set the current project name displayed on the left."""
        self.project_label.setText(f"Project: {project_name}")

    def show_progress(self, show: bool = True) -> None:
        """Show or hide the progress bar."""
        self.progress_bar.setVisible(show)

    def set_progress(self, value: int) -> None:
        """Set the progress bar value (0-100)."""
        self.progress_bar.setValue(value)

    def set_progress_range(self, min_val: int, max_val: int) -> None:
        """Set the progress bar range."""
        self.progress_bar.setRange(min_val, max_val)