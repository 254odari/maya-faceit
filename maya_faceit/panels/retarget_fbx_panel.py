# retarget_fbx_panel.py
# Maya Faceit Plugin - Retarget FBX Panel
# Converted from Blender to Maya Python 3.11

"""
Retarget FBX panel for Faceit Maya plugin.
Handles FBX retargeting UI.
"""

import maya.cmds as cmds
from typing import List, Dict, Optional, Any

from .ui import FACEIT_PT_BaseSub
from . import draw_utils


class FACEIT_PT_RetargetFBX(FACEIT_PT_BaseSub):
    """Retarget FBX panel."""
    
    bl_label = 'Shape Key Retargeter (FBX)'
    bl_idname = 'FACEIT_PT_RetargetFBX'
    bl_parent_id = 'FACEIT_PT_MocapUtils'
    faceit_predecessor = 'FACEIT_PT_MocapMotionTargets'
    
    def poll(self, context: Any = None) -> bool:
        """Check if the panel should be shown."""
        return True
    
    def draw(self, layout: Any) -> None:
        """Draw the panel."""
        layout.text("Shape Key Retargeter (FBX)")
        layout.text("Retarget FBX animation to shape keys")


class FACEIT_UL_FbxTargetShapesList:
    """FBX Target Shapes UI List."""
    
    def draw_item(self, layout: Any, item: Any, icon: str = '') -> None:
        """Draw a list item."""
        layout.text(item.name)


class FACEIT_OT_DrawFBXTargetShapesList:
    """Draw FBX Target Shapes List operator."""
    
    bl_idname = 'faceit.draw_fbx_target_shapes_list'


class FACEIT_UL_FBXRetargetList:
    """FBX Retarget List UI List."""
    
    def draw_item(self, layout: Any, item: Any, icon: str = '') -> None:
        """Draw a list item."""
        layout.text(item.name)