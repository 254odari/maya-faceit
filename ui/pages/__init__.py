"""
ui/pages/__init__.py

All workspace pages.
"""

from .dashboard import DashboardPage
from .project import ProjectPage
from .rig import RigPage
from .landmarks import LandmarksPage
from .blendshapes import BlendshapesPage
from .arkit import ARKitPage
from .mocap import MocapPage
from .animation import AnimationPage
from .expressions import ExpressionsPage
from .picker import PickerPage
from .tools import ToolsPage
from .export import ExportPage
from .validation import ValidationPage
from .settings import SettingsPage
from .about import AboutPage

__all__ = [
    "DashboardPage",
    "ProjectPage",
    "RigPage",
    "LandmarksPage",
    "BlendshapesPage",
    "ARKitPage",
    "MocapPage",
    "AnimationPage",
    "ExpressionsPage",
    "PickerPage",
    "ToolsPage",
    "ExportPage",
    "ValidationPage",
    "SettingsPage",
    "AboutPage",
]