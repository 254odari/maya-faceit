# ui/widgets/search.py

"""
ui/widgets/search.py

Search and filter widgets.
"""

from __future__ import annotations

from typing import List, Optional

from ..qt_imports import QWidget, QHBoxLayout, QLineEdit, QPushButton, QComboBox, Signal


class SearchBox(QWidget):
    """Search box with text input and clear button."""
    text_changed = Signal(str)

    def __init__(self, placeholder: str = "Search...", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText(placeholder)
        self.edit.textChanged.connect(self.text_changed.emit)
        self.clear_btn = QPushButton("✕")
        self.clear_btn.setFixedSize(20, 20)
        self.clear_btn.clicked.connect(self.clear)
        layout.addWidget(self.edit)
        layout.addWidget(self.clear_btn)

    def clear(self) -> None:
        self.edit.clear()
        self.edit.setFocus()

    def text(self) -> str:
        return self.edit.text()


class FilterWidget(QWidget):
    """Filter widget with search and category dropdown."""
    filter_changed = Signal(str, str)  # text, category

    def __init__(self, categories: Optional[List[str]] = None, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.search = SearchBox()
        self.search.text_changed.connect(self._on_filter)
        self.category = QComboBox()
        self.category.addItem("All Categories")
        if categories:
            self.category.addItems(categories)
        self.category.currentTextChanged.connect(self._on_filter)
        layout.addWidget(self.search, 1)
        layout.addWidget(self.category)

    def _on_filter(self) -> None:
        self.filter_changed.emit(self.search.text(), self.category.currentText())

    def get_text(self) -> str:
        return self.search.text()

    def get_category(self) -> str:
        return self.category.currentText()