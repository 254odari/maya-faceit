# ui/widgets/cards.py

"""
ui/widgets/cards.py

Card-style containers for information.
"""

from __future__ import annotations

from typing import Optional

from ..qt_imports import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame


class CardWidget(QFrame):
    """A card-style container with title and content."""
    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setStyleSheet("""
            CardWidget {
                background: #3a3a3a;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        if title:
            self.title_label = QLabel(title)
            self.title_label.setStyleSheet("font-weight: bold; color: #ddd;")
            layout.addWidget(self.title_label)

        self.content_layout = QVBoxLayout()
        layout.addLayout(self.content_layout)

    def add_widget(self, widget: QWidget) -> None:
        self.content_layout.addWidget(widget)


class StatCard(CardWidget):
    """Card for displaying a statistic with label and value."""
    def __init__(self, label: str, value: str, parent=None):
        super().__init__(parent=parent)
        self.label_label = QLabel(label)
        self.value_label = QLabel(value)
        self.value_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #4a90d9;")
        self.content_layout.addWidget(self.label_label)
        self.content_layout.addWidget(self.value_label)

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)


class InfoCard(CardWidget):
    """Card for displaying informational text."""
    def __init__(self, title: str, text: str, parent=None):
        super().__init__(title, parent)
        self.text_label = QLabel(text)
        self.text_label.setWordWrap(True)
        self.content_layout.addWidget(self.text_label)