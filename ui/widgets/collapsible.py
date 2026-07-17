# ui/widgets/collapsible.py

"""
ui/widgets/collapsible.py

Collapsible sections and groups.
"""

from __future__ import annotations

from typing import Optional

from ..qt_imports import QWidget, QVBoxLayout, QPushButton, QFrame, Signal


class CollapsibleSection(QWidget):
    """A collapsible section with header and content."""
    toggled = Signal(bool)

    def __init__(self, title: str, expanded: bool = True, parent=None):
        super().__init__(parent)
        self._expanded = expanded
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        self.header_btn = QPushButton(f"▶ {title}")
        self.header_btn.setFlat(True)
        self.header_btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 4px 8px;
                background: #3a3a3a;
                border: none;
                border-bottom: 1px solid #444;
            }
            QPushButton:hover {
                background: #4a4a4a;
            }
        """)
        self.header_btn.clicked.connect(self.toggle)
        layout.addWidget(self.header_btn)

        # Content
        self.content_frame = QFrame()
        self.content_frame.setStyleSheet("background: #2b2b2b; padding: 4px;")
        self.content_layout = QVBoxLayout(self.content_frame)
        self.content_layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(self.content_frame)

        self.set_expanded(expanded)

    def toggle(self) -> None:
        self.set_expanded(not self._expanded)

    def set_expanded(self, expanded: bool) -> None:
        self._expanded = expanded
        self.content_frame.setVisible(expanded)
        # Update arrow based on expanded state
        arrow = "▼" if expanded else "▶"
        self.header_btn.setText(f"{arrow} {self.header_btn.text().split(' ', 1)[-1]}")
        self.toggled.emit(expanded)

    def add_widget(self, widget: QWidget) -> None:
        self.content_layout.addWidget(widget)

    def is_expanded(self) -> bool:
        return self._expanded


class CollapsibleGroup(QWidget):
    """Group of collapsible sections."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

    def add_section(self, title: str, expanded: bool = True) -> CollapsibleSection:
        section = CollapsibleSection(title, expanded)
        self.layout.addWidget(section)
        return section