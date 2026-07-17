# ui/widgets/picker_canvas.py

"""
ui/widgets/picker_canvas.py

Canvas widget for expression picker (interactive grid of shapes).
"""

from __future__ import annotations

from typing import List, Tuple, Optional

from ..qt_imports import (
    QWidget, QPainter, QColor, QBrush, QPen, QFont, Qt,
    QRectF, QPointF, Signal
)


class PickerCanvas(QWidget):
    """A canvas that displays clickable expression buttons."""
    item_clicked = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(300, 200)
        self._expressions: List[Tuple[str, str]] = [
            ("Smile", "#4a90d9"),
            ("Frown", "#d94a4a"),
            ("Surprise", "#d9b84a"),
            ("Anger", "#8b3a8b"),
            ("Squint", "#3a8b8b"),
            ("Blink", "#8b8b3a"),
        ]
        self.setMouseTracking(True)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()
        cols = 3
        rows = (len(self._expressions) + cols - 1) // cols
        w = rect.width() / cols
        h = rect.height() / rows
        for i, (name, color) in enumerate(self._expressions):
            x = (i % cols) * w
            y = (i // cols) * h
            painter.setBrush(QBrush(QColor(color)))
            painter.setPen(QPen(QColor("#555"), 1))
            painter.drawRoundedRect(QRectF(x + 4, y + 4, w - 8, h - 8), 5, 5)
            painter.setPen(QPen(Qt.white))
            painter.setFont(QFont("Segoe UI", 9))
            painter.drawText(QRectF(x, y, w, h), Qt.AlignCenter, name)

    def mousePressEvent(self, event) -> None:
        pos = event.pos()
        cols = 3
        rect = self.rect()
        w = rect.width() / cols
        h = rect.height() / ((len(self._expressions) + cols - 1) // cols)
        col = int(pos.x() // w)
        row = int(pos.y() // h)
        idx = row * cols + col
        if 0 <= idx < len(self._expressions):
            name, color = self._expressions[idx]
            self.item_clicked.emit(name)

    def add_expression(self, name: str, color: str = "#4a90d9") -> None:
        """Add an expression to the picker."""
        self._expressions.append((name, color))
        self.update()