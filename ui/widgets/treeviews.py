# ui/widgets/treeviews.py

"""
ui/widgets/treeviews.py

Custom tree and table widgets.
"""

from __future__ import annotations

from typing import Optional, Dict

from ..qt_imports import (
    QTreeWidget, QTreeWidgetItem, QTableWidget, QTableWidgetItem, Qt
)


class BlendshapeTree(QTreeWidget):
    """Tree view for blendshape assets."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabels(["Name", "Type", "Weight"])
        self.setSelectionMode(self.ExtendedSelection)

    def add_target(self, name: str, typ: str = "target", weight: float = 0.0) -> QTreeWidgetItem:
        item = QTreeWidgetItem([name, typ, f"{weight:.2f}"])
        self.addTopLevelItem(item)
        return item


class HierarchyTree(QTreeWidget):
    """Tree view for rig hierarchy."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabels(["Node"])
        self.setSelectionMode(self.ExtendedSelection)

    def add_node(self, name: str, parent_item: Optional[QTreeWidgetItem] = None) -> QTreeWidgetItem:
        item = QTreeWidgetItem([name])
        if parent_item:
            parent_item.addChild(item)
        else:
            self.addTopLevelItem(item)
        return item


class WeightTable(QTableWidget):
    """Table for weight editing."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(2)
        self.setHorizontalHeaderLabels(["Target", "Weight"])
        self.setSelectionBehavior(self.SelectRows)

    def add_row(self, target: str, weight: float = 0.0) -> int:
        row = self.rowCount()
        self.insertRow(row)
        self.setItem(row, 0, QTableWidgetItem(target))
        weight_item = QTableWidgetItem(f"{weight:.2f}")
        weight_item.setFlags(weight_item.flags() | Qt.ItemIsEditable)
        self.setItem(row, 1, weight_item)
        return row

    def get_weights(self) -> Dict[str, float]:
        """Return a dict of target -> weight."""
        weights = {}
        for row in range(self.rowCount()):
            target = self.item(row, 0).text()
            weight_str = self.item(row, 1).text()
            try:
                weight = float(weight_str)
            except ValueError:
                weight = 0.0
            weights[target] = weight
        return weights