# -*- coding: utf-8 -*-
"""
maya_faceit.constants
~~~~~~~~~~~~~~~~~~~~~

Global constants for Maya FaceIT.
"""

import os
from pathlib import Path

# -----------------------------------------------------------------------------
# Application Paths
# -----------------------------------------------------------------------------

# Root directory of the plugin
PACKAGE_ROOT = Path(__file__).parent.resolve()

# User data directory
USER_DATA_DIR = Path(os.path.expanduser("~/.faceit"))
USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Configuration directory
CONFIG_DIR = USER_DATA_DIR / "config"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

# Cache directory
CACHE_DIR = USER_DATA_DIR / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Logs directory
LOGS_DIR = USER_DATA_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Preferences file
PREFERENCES_FILE = CONFIG_DIR / "preferences.json"

# Project files directory
PROJECTS_DIR = USER_DATA_DIR / "projects"
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

# Session file
SESSION_FILE = USER_DATA_DIR / "session.json"

# Temporary directory
TEMP_DIR = USER_DATA_DIR / "temp"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Plugin Metadata
# -----------------------------------------------------------------------------

PLUGIN_NAME = "Maya FaceIT"
PLUGIN_DESCRIPTION = "Facial rigging and animation toolkit for Maya"
PLUGIN_VENDOR = "Maya FaceIT Team"
PLUGIN_URL = "https://github.com/yourusername/maya_faceit"

# -----------------------------------------------------------------------------
# File Extensions
# -----------------------------------------------------------------------------

EXTENSIONS = {
    "layout": ".facepicker",
    "compressed": ".facepickerz",
    "backup": ".backup",
    "pose": ".facepose",
    "preset": ".facepreset",
    "project": ".faceproject",
    "config": ".json",
}

# -----------------------------------------------------------------------------
# UI Constants
# -----------------------------------------------------------------------------

UI_DEFAULT_WIDTH = 1024
UI_DEFAULT_HEIGHT = 768
UI_MIN_WIDTH = 400
UI_MIN_HEIGHT = 500
UI_WINDOW_TITLE = "Maya FaceIT"

# -----------------------------------------------------------------------------
# Color Constants (RGBA tuples 0-1)
# -----------------------------------------------------------------------------

COLORS = {
    "primary": (0.29, 0.56, 0.85, 1.0),
    "success": (0.3, 0.7, 0.3, 1.0),
    "warning": (0.94, 0.7, 0.2, 1.0),
    "error": (0.85, 0.29, 0.29, 1.0),
    "info": (0.2, 0.8, 0.8, 1.0),
    "background": (0.18, 0.18, 0.18, 1.0),
    "surface": (0.24, 0.24, 0.24, 1.0),
    "text": (0.88, 0.88, 0.88, 1.0),
    "text_dark": (0.1, 0.1, 0.1, 1.0),
}

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------

LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# -----------------------------------------------------------------------------
# Maya Specific
# -----------------------------------------------------------------------------

MAYA_CONTROL_TYPES = [
    "nurbsCurve",
    "nurbsSurface",
    "circle",
    "square",
    "triangle",
    "diamond",
    "cross",
    "arrow",
]

MAYA_DEFORMER_TYPES = [
    "cluster",
    "softMod",
    "wire",
    "blendShape",
    "skinCluster",
    "nonLinear",
    "sculpt",
]

MAYA_CONSTRAINT_TYPES = [
    "parentConstraint",
    "pointConstraint",
    "orientConstraint",
    "scaleConstraint",
    "aimConstraint",
    "matrixConstraint",
]

# -----------------------------------------------------------------------------
# Animation
# -----------------------------------------------------------------------------

DEFAULT_FPS = 24.0
DEFAULT_START_FRAME = 0
DEFAULT_END_FRAME = 120

# -----------------------------------------------------------------------------
# ARKit
# -----------------------------------------------------------------------------

ARKIT_BLENDSHAPES = [
    "browDownLeft", "browDownRight", "browInnerUp",
    "browOuterUpLeft", "browOuterUpRight",
    "cheekPuff", "cheekSquintLeft", "cheekSquintRight",
    "eyeBlinkLeft", "eyeBlinkRight",
    "eyeLookDownLeft", "eyeLookDownRight",
    "eyeLookInLeft", "eyeLookInRight",
    "eyeLookOutLeft", "eyeLookOutRight",
    "eyeLookUpLeft", "eyeLookUpRight",
    "eyeSquintLeft", "eyeSquintRight",
    "eyeWideLeft", "eyeWideRight",
    "jawForward", "jawLeft", "jawOpen", "jawRight",
    "mouthClose", "mouthDimpleLeft", "mouthDimpleRight",
    "mouthFrownLeft", "mouthFrownRight",
    "mouthFunnel", "mouthLeft", "mouthLowerDownLeft",
    "mouthLowerDownRight", "mouthPressLeft", "mouthPressRight",
    "mouthPucker", "mouthRight", "mouthRollLower",
    "mouthRollUpper", "mouthShrugLower", "mouthShrugUpper",
    "mouthSmileLeft", "mouthSmileRight",
    "mouthStretchLeft", "mouthStretchRight",
    "mouthUpperUpLeft", "mouthUpperUpRight",
    "noseSneerLeft", "noseSneerRight",
    "tongueOut",
]

FACS_AUS = [
    "AU1", "AU2", "AU4", "AU5", "AU6", "AU7", "AU9", "AU10",
    "AU11", "AU12", "AU13", "AU14", "AU15", "AU16", "AU17",
    "AU18", "AU20", "AU22", "AU23", "AU24", "AU25", "AU26",
    "AU27", "AU28", "AU30", "AU31", "AU33", "AU34", "AU35",
    "AU36", "AU38", "AU39", "AU43", "AU44", "AU45", "AU46",
]

# -----------------------------------------------------------------------------
# Export Formats
# -----------------------------------------------------------------------------

EXPORT_FORMATS = [
    "fbx",
    "usd",
    "abc",
    "json",
    "ma",
    "mb",
]

# -----------------------------------------------------------------------------
# Default Values
# -----------------------------------------------------------------------------

DEFAULT_GRID_SIZE = 10.0
DEFAULT_ZOOM_LEVEL = 1.0
DEFAULT_TOLERANCE = 0.0001
DEFAULT_MERGE_DISTANCE = 0.001

# -----------------------------------------------------------------------------
# Limits
# -----------------------------------------------------------------------------

MAX_VERTICES_FOR_OPTIMIZATION = 50000
MAX_INFLUENCES = 8
MAX_ITERATIONS = 100
MIN_ITERATIONS = 1

__all__ = [
    # Paths
    "PACKAGE_ROOT",
    "USER_DATA_DIR",
    "CONFIG_DIR",
    "CACHE_DIR",
    "LOGS_DIR",
    "PREFERENCES_FILE",
    "PROJECTS_DIR",
    "SESSION_FILE",
    "TEMP_DIR",
    # Metadata
    "PLUGIN_NAME",
    "PLUGIN_DESCRIPTION",
    "PLUGIN_VENDOR",
    "PLUGIN_URL",
    # Extensions
    "EXTENSIONS",
    # UI
    "UI_DEFAULT_WIDTH",
    "UI_DEFAULT_HEIGHT",
    "UI_MIN_WIDTH",
    "UI_MIN_HEIGHT",
    "UI_WINDOW_TITLE",
    # Colors
    "COLORS",
    # Logging
    "LOG_LEVEL",
    "LOG_FORMAT",
    "LOG_DATE_FORMAT",
    # Maya
    "MAYA_CONTROL_TYPES",
    "MAYA_DEFORMER_TYPES",
    "MAYA_CONSTRAINT_TYPES",
    # Animation
    "DEFAULT_FPS",
    "DEFAULT_START_FRAME",
    "DEFAULT_END_FRAME",
    # ARKit
    "ARKIT_BLENDSHAPES",
    "FACS_AUS",
    # Export
    "EXPORT_FORMATS",
    # Defaults
    "DEFAULT_GRID_SIZE",
    "DEFAULT_ZOOM_LEVEL",
    "DEFAULT_TOLERANCE",
    "DEFAULT_MERGE_DISTANCE",
    # Limits
    "MAX_VERTICES_FOR_OPTIMIZATION",
    "MAX_INFLUENCES",
    "MAX_ITERATIONS",
    "MIN_ITERATIONS",
]