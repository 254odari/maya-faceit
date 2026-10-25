# bake_panel.py
# Maya Faceit Plugin - Bake Panel
# Converted from Blender to Maya Python 3.11

"""
Bake panel for Faceit Maya plugin.
Handles shape key baking and cleanup UI.
"""

import maya.cmds as cmds
from typing import List, Dict, Optional, Any

from .ui import FACEIT_PT_Base, FACEIT_PT_BaseSub
from . import draw_utils


class FACEIT_PT_BaseBake(FACEIT_PT_Base):
    """Base bake panel."""
    UI_TABS = ('BAKE',)


class FACEIT_PT_BakeExpressions(FACEIT_PT_BaseBake):
    """Bake Expressions panel."""
    
    bl_label = 'Bake Shape Keys'
    bl_options = set()
    bl_idname = 'FACEIT_PT_BakeExpressions'
    
    def poll(self, context: Any = None) -> bool:
        """Check if the panel should be shown."""
        return True
    
    def draw(self, layout: Any) -> None:
        """Draw the panel."""
        layout.text("Bake Shape Keys")
        layout.text("Bake expressions to shape keys")


class FACEIT_PT_ShapeKeyUtils(FACEIT_PT_BaseBake):
    """Shape Key Utils panel."""
    
    bl_label = 'Shape Key Utils'
    bl_idname = 'FACEIT_PT_ShapeKeyUtils'
    faceit_predecessor = 'FACEIT_PT_RigUtils'
    
    def poll(self, context: Any = None) -> bool:
        """Check if the panel should be shown."""
        return True
    
    def draw(self, layout: Any) -> None:
        """Draw the panel."""
        layout.text("Shape Key Utils")
        layout.text("Set shape key slider ranges")


class FACEIT_PT_RigUtils(FACEIT_PT_BaseBake):
    """Rig Utils panel."""
    
    bl_label = 'Rig Utils'
    bl_idname = 'FACEIT_PT_RigUtils'
    faceit_predecessor = 'FACEIT_PT_BakeExpressions'
    
    def poll(self, context: Any = None) -> bool:
        """Check if the panel should be shown."""
        return True
    
    def draw(self, layout: Any) -> None:
        """Draw the panel."""
        layout.text("Rig Utils")
        layout.text("Rig utilities and body rig join")


class FACEIT_PT_Other(FACEIT_PT_BaseBake):
    """Other Utils panel."""
    
    bl_label = 'Other Utils'
    bl_idname = 'FACEIT_PT_Other'
    faceit_predecessor = 'FACEIT_PT_ShapeKeyUtils'
    
    def poll(self, context: Any = None) -> bool:
        """Check if the panel should be shown."""
        return True
    
    def draw(self, layout: Any) -> None:
        """Draw the panel."""
        layout.text("Other Utils")
        layout.text("Apply modifiers and shape keys")


class FACEIT_PT_Finalize(FACEIT_PT_BaseBake):
    """Finalize panel."""
    
    bl_label = 'Clean Up (Destructive)'
    bl_idname = 'FACEIT_PT_Finalize'
    faceit_predecessor = 'FACEIT_PT_Other'
    
    def poll(self, context: Any = None) -> bool:
        """Check if the panel should be shown."""
        return True
    
    def draw(self, layout: Any) -> None:
        """Draw the panel."""
        layout.text("Clean Up (Destructive)")
        layout.text("Clean up Faceit data")


class FACE_OBJECTS_MODIFIERS_UL_list:
    """Face Objects Modifiers UI List."""
    
    def draw_item(self, layout: Any, item: Any, icon: str = '') -> None:
        """Draw a list item."""
        layout.text(item.name)


class BAKE_MODIFIERS_UL_list:
    """Bake Modifiers UI List."""
    
    def draw_item(self, layout: Any, item: Any, icon: str = '') -> None:
        """Draw a list item."""
        layout.text(item.name)