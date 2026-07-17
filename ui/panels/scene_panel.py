# ui/panels/scene_panel.py

"""
ui/panels/scene_panel.py

Scene panel – shows all objects in the Maya scene.
"""

from __future__ import annotations

from ..qt_imports import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QPushButton, QHBoxLayout
)


class ScenePanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Name", "Type"])
        layout.addWidget(self.tree)

        # Buttons
        btn_layout = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh)
        select_btn = QPushButton("Select in Maya")
        select_btn.clicked.connect(self._select)
        btn_layout.addWidget(refresh_btn)
        btn_layout.addWidget(select_btn)
        layout.addLayout(btn_layout)

        # Populate with sample data
        self._populate()

    def _populate(self):
        for name, typ in [("head_geo", "mesh"), ("jaw_ctrl", "controller")]:
            item = QTreeWidgetItem([name, typ])
            self.tree.addTopLevelItem(item)

    def _refresh(self):
        pass

    def _select(self):
        pass