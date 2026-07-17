# ui/panels/__init__.py

"""
ui/panels/__init__.py

All dockable panels.
"""

from .scene_panel import ScenePanel
from .hierarchy_panel import HierarchyPanel
from .inspector_panel import InspectorPanel
from .property_panel import PropertyPanel
from .preview_panel import PreviewPanel
from .log_panel import LogPanel
from .output_panel import OutputPanel
from .progress_panel import ProgressPanel
from .statistics_panel import StatisticsPanel
from .validation_panel import ValidationPanel
from .history_panel import HistoryPanel
from .console_panel import ConsolePanel

__all__ = [
    "ScenePanel",
    "HierarchyPanel",
    "InspectorPanel",
    "PropertyPanel",
    "PreviewPanel",
    "LogPanel",
    "OutputPanel",
    "ProgressPanel",
    "StatisticsPanel",
    "ValidationPanel",
    "HistoryPanel",
    "ConsolePanel",
]