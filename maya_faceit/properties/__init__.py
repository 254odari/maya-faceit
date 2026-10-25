# __init__.py
# Maya Faceit Plugin - Properties Module
# Version: 1.0.0

"""
Faceit Properties Module for Maya
=================================

This module provides scene and object properties for the Faceit plugin.

Main Components:
    - Scene properties for all Faceit functionality
    - Object properties for control rigs and targets
    - Collection properties for expressions, shapes, and modifiers
"""

__version__ = "1.0.0"
__author__ = "Faceit Team"

# ============================================================
# Module Imports
# ============================================================

from . import bind_scene_properties
from . import ctrl_rig_scene_properties
from . import expression_scene_properties
from . import fbx_retarget_scene_properties
from . import landmarks_scene_properties
from . import mocap_scene_properties
from . import retarget_scene_properties
from . import rig_scene_properties
from . import setup_scene_properties
from . import ui_scene_properties
from . import utils_scene_properties

# ============================================================
# Module Exports
# ============================================================

__all__ = [
    'bind_scene_properties',
    'ctrl_rig_scene_properties',
    'expression_scene_properties',
    'fbx_retarget_scene_properties',
    'landmarks_scene_properties',
    'mocap_scene_properties',
    'retarget_scene_properties',
    'rig_scene_properties',
    'setup_scene_properties',
    'ui_scene_properties',
    'utils_scene_properties',
]