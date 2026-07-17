# ui/panels/console_panel.py

"""
ui/panels/console_panel.py

Console panel – interactive Python console.
"""

from __future__ import annotations

from .. import QT_BINDING
if QT_BINDING:
    from PySide2 import QtWidgets, QtCore, QtGui
    from PySide2.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLineEdit, QHBoxLayout
    from PySide2.QtCore import Qt
else:
    QWidget = object


class ConsolePanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setStyleSheet("font-family: monospace;")
        layout.addWidget(self.output)

        self.input = QLineEdit()
        self.input.setPlaceholderText("Enter Python command...")
        self.input.returnPressed.connect(self._execute)
        layout.addWidget(self.input)

        # Sample output
        self.output.append(">>> print('Hello FaceIT')")
        self.output.append("Hello FaceIT")

    def _execute(self):
        cmd = self.input.text()
        self.output.append(f">>> {cmd}")
        # In a real implementation, execute in Maya's Python context
        try:
            result = eval(cmd)
            if result is not None:
                self.output.append(str(result))
        except Exception as e:
            self.output.append(f"Error: {e}")
        self.input.clear()