# ui.py
# Maya Faceit Plugin - UI Base
# Converted from Blender to Maya Python 3.11

"""
Base UI classes for Faceit Maya plugin.
Provides base panel classes and main panel.
"""

import maya.cmds as cmds # type: ignore
import maya.api.OpenMaya as om2 # type: ignore
from typing import List, Dict, Optional, Any


# ============================================================
# Base Panel Classes
# ============================================================

class FACEIT_PT_Base:
    """Base class for Faceit panels."""
    
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'FACEIT'
    bl_label = 'Base'
    bl_options = {'DEFAULT_CLOSED'}
    
    faceit_predecessor = 'FACEIT_PT_MainPanel'
    UI_TABS = ('SETUP',)
    UI_WORKSPACES = ('ALL', 'RIG', 'MOCAP')
    
    def poll(self, context: Any = None) -> bool:
        """Check if the panel should be shown."""
        # In Maya, we'd check workspace and pin state
        return True
    
    def draw_header_preset(self, layout: Any) -> None:
        """Draw the header preset."""
        # In Maya, we'd draw pin button
        pass
    
    def draw(self, layout: Any) -> None:
        """Draw the panel content."""
        pass


class FACEIT_PT_BaseSub:
    """Base class for sub-panels."""
    
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'FACEIT'
    bl_label = 'Base Sub'
    bl_options = {'DEFAULT_CLOSED'}
    bl_parent_id = ''
    faceit_predecessor = ''
    
    def poll(self, context: Any = None) -> bool:
        """Check if the panel should be shown."""
        return True
    
    def draw(self, layout: Any) -> None:
        """Draw the panel content."""
        pass


# ============================================================
# Main Panel
# ============================================================

class FACEIT_PT_MainPanel:
    """Main Faceit panel."""
    
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'FACEIT'
    bl_label = 'FaceIt'
    bl_idname = 'FACEIT_PT_MainPanel'
    bl_order = 0
    
    def draw(self, layout: Any) -> None:
        """Draw the main panel."""
        # In Maya, we'd draw workspace selector and tabs
        # This is a placeholder
        layout.text("FaceIt Panel")


# ============================================================
# Maya UI Integration
# ============================================================

def register_panels() -> None:
    """
    Register all Faceit panels with Maya.
    """
    # In Maya, we'd create UI elements using PySide2
    print("Faceit panels registered")


def unregister_panels() -> None:
    """
    Unregister all Faceit panels.
    """
    print("Faceit panels unregistered")