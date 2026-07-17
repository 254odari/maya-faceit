# ui/panels/hierarchy_panel.py

"""
ui/panels/hierarchy_panel.py

Hierarchy panel – shows rig hierarchy.
"""

from __future__ import annotations

from ..qt_imports import QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem


class HierarchyPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Node"])
        layout.addWidget(self.tree)

        # Sample hierarchy
        root = QTreeWidgetItem(["Root"])
        child1 = QTreeWidgetItem(["Jaw"])
        child2 = QTreeWidgetItem(["Eye_L"])
        child3 = QTreeWidgetItem(["Eye_R"])
        root.addChild(child1)
        root.addChild(child2)
        root.addChild(child3)
        self.tree.addTopLevelItem(root)
        root.setExpanded(True)