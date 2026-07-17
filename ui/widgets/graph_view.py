# ui/widgets/graph_view.py

"""
ui/widgets/graph_view.py

Graph visualization widget.
"""

from __future__ import annotations

from typing import List, Tuple, Optional

from ..qt_imports import QWidget, QPainter, QPen, QBrush, QColor, Qt


class GraphView(QWidget):
    """Simple graph/curve view for displaying data."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(150)
        self.setStyleSheet("background: #1a1a1a; border: 1px solid #444;")
        self._data: List[Tuple[float, float]] = []
        self._x_range: Tuple[float, float] = (0.0, 1.0)
        self._y_range: Tuple[float, float] = (0.0, 1.0)

    def set_data(self, data: List[Tuple[float, float]]) -> None:
        """Set data points (list of (x, y) tuples)."""
        self._data = data
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()
        # Draw grid
        painter.setPen(QPen(QColor("#444"), 1))
        for i in range(1, 5):
            x = rect.left() + rect.width() * i / 5
            painter.drawLine(x, rect.top(), x, rect.bottom())
            y = rect.top() + rect.height() * i / 5
            painter.drawLine(rect.left(), y, rect.right(), y)
        # Draw data
        if self._data and len(self._data) > 1:
            painter.setPen(QPen(QColor("#4a90d9"), 2))
            x_range = self._x_range[1] - self._x_range[0]
            y_range = self._y_range[1] - self._y_range[0]
            prev_x = None
            prev_y = None
            for x, y in self._data:
                px = rect.left() + rect.width() * (x - self._x_range[0]) / x_range
                py = rect.bottom() - rect.height() * (y - self._y_range[0]) / y_range
                if prev_x is not None:
                    painter.drawLine(prev_x, prev_y, px, py)
                prev_x = px
                prev_y = py
            # Draw points
            painter.setPen(QPen(QColor("#4a90d9"), 4))
            for x, y in self._data:
                px = rect.left() + rect.width() * (x - self._x_range[0]) / x_range
                py = rect.bottom() - rect.height() * (y - self._y_range[0]) / y_range
                painter.drawPoint(px, py)