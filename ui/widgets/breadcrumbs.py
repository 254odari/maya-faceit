# ui/widgets/breadcrumbs.py

"""
ui/widgets/breadcrumbs.py

Breadcrumb navigation bar.
"""

from __future__ import annotations

from typing import List

from ..qt_imports import QWidget, QHBoxLayout, QPushButton, QLabel, Signal


class BreadcrumbBar(QWidget):
    """Breadcrumb navigation bar."""
    crumb_clicked = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(2)
        self._crumbs: List[str] = []

    def set_crumbs(self, crumbs: List[str]) -> None:
        """Set the breadcrumb list."""
        self.clear()
        self._crumbs = crumbs
        for i, crumb in enumerate(crumbs):
            if i > 0:
                sep = QLabel("›")
                sep.setStyleSheet("color: #666;")
                self.layout.addWidget(sep)
            btn = QPushButton(crumb)
            btn.setFlat(True)
            btn.setStyleSheet("""
                QPushButton {
                    color: #4a90d9;
                    text-decoration: underline;
                    padding: 0 2px;
                }
                QPushButton:hover {
                    color: #5a9fe9;
                }
            """)
            btn.clicked.connect(lambda checked, c=crumb: self.crumb_clicked.emit(c))
            self.layout.addWidget(btn)

    def clear(self) -> None:
        """Clear all crumbs."""
        while self.layout.count():
            child = self.layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self._crumbs = []

    def add_crumb(self, crumb: str) -> None:
        """Append a crumb."""
        self._crumbs.append(crumb)
        self.set_crumbs(self._crumbs)