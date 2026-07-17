"""
ui/pages/settings.py

Application settings.
"""

from __future__ import annotations

from .. import QT_BINDING
if QT_BINDING:
    from PySide2 import QtWidgets, QtCore, QtGui
    from PySide2.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QFormLayout, QLineEdit, QCheckBox, QComboBox
else:
    QWidget = object


class SettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        tabs = QTabWidget()

        # General tab
        general = QWidget()
        g_form = QFormLayout(general)
        g_form.addRow("Language:", QComboBox())
        g_form.addRow("Auto-save:", QCheckBox())
        g_form.addRow("Theme:", QComboBox())
        tabs.addTab(general, "General")

        # Blendshape tab
        bs = QWidget()
        bs_form = QFormLayout(bs)
        bs_form.addRow("Default weight range:", QComboBox())
        bs_form.addRow("Auto-normalize:", QCheckBox())
        tabs.addTab(bs, "Blendshapes")

        # ARKit tab
        arkit = QWidget()
        a_form = QFormLayout(arkit)
        a_form.addRow("Mapping preset:", QComboBox())
        tabs.addTab(arkit, "ARKit")

        # Mocap tab
        mocap = QWidget()
        m_form = QFormLayout(mocap)
        m_form.addRow("Default device:", QComboBox())
        tabs.addTab(mocap, "Mocap")

        layout.addWidget(tabs)
        layout.addStretch()