"""
ui/application/notifications.py

Toast notification manager for displaying non‑intrusive messages.
"""

from __future__ import annotations

import logging

from ..qt_imports import Qt, QFrame, QVBoxLayout, QLabel, QTimer

logger = logging.getLogger(__name__)


class NotificationManager(QFrame):
    """
    Manager for in‑app toast notifications.

    Shows a floating message that auto‑hides after a timeout.
    Usage:
        mgr = NotificationManager(main_window)
        mgr.show_notification("Operation complete", duration=2000)
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.ToolTip)
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Plain)
        self.setStyleSheet("""
            QFrame {
                background: #333;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 8px;
                color: #eee;
            }
        """)
        self.hide()

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(8, 8, 8, 8)

    def show_notification(self, message: str, duration: int = 3000) -> None:
        """
        Show a notification that auto‑hides after duration ms.

        Args:
            message: The text to display.
            duration: Time in milliseconds before auto‑hide.
        """
        # Clear old messages
        while self._layout.count():
            child = self._layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        label = QLabel(message)
        label.setWordWrap(True)
        self._layout.addWidget(label)

        # Position near the top‑right of the parent
        if self.parent():
            parent_rect = self.parent().rect()
            self.move(parent_rect.right() - self.width() - 20, 20)

        self.show()
        self.raise_()
        self._timer.start(duration)

    def close(self) -> None:
        self.hide()
        self._timer.stop()