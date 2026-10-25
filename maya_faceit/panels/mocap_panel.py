# mocap_panel.py
# Maya Faceit Plugin - Mocap Panel
# Converted from Blender to Maya Python 3.11

"""
Mocap panel for Faceit Maya plugin.
Handles motion capture import and live animation UI.
"""

import maya.cmds as cmds
from typing import List, Dict, Optional, Any

from .ui import FACEIT_PT_Base, FACEIT_PT_BaseSub
from . import draw_utils


class FACEIT_PT_BaseMocap(FACEIT_PT_Base):
    """Base mocap panel."""
    UI_TABS = ('MOCAP',)


class FACEIT_PT_MocapUtils(FACEIT_PT_BaseMocap):
    """Mocap Utils panel."""
    
    bl_label = 'Other Tools and Utilities'
    bl_idname = 'FACEIT_PT_MocapUtils'
    faceit_predecessor = 'FACEIT_PT_MocapOSC'
    
    def poll(self, context: Any = None) -> bool:
        """Check if the panel should be shown."""
        return True
    
    def draw(self, layout: Any) -> None:
        """Draw the panel."""
        layout.text("Other Tools and Utilities")
        layout.text("Reset expressions and head pose")


class FACEIT_PT_MocapKeyframesOps(FACEIT_PT_BaseSub):
    """Mocap Keyframes Ops panel."""
    
    bl_label = 'Manipulate Keyframes'
    bl_idname = 'FACEIT_PT_MocapKeyframesOps'
    bl_parent_id = 'FACEIT_PT_MocapUtils'
    faceit_predecessor = 'FACEIT_PT_MocapMotionTargets'
    
    def draw(self, layout: Any) -> None:
        """Draw the panel."""
        layout.text("Manipulate Keyframes")
        layout.text("Add zero keyframe, remove frame range")


class FACEIT_PT_MocapMotionTargets(FACEIT_PT_BaseSub):
    """Mocap Motion Targets panel."""
    
    bl_label = 'Head Setup'
    bl_idname = 'FACEIT_PT_MocapMotionTargets'
    bl_parent_id = 'FACEIT_PT_MocapUtils'
    faceit_predecessor = 'FACEIT_PT_MocapAction'
    
    def poll(self, context: Any = None) -> bool:
        """Check if the panel should be shown."""
        return True
    
    def draw(self, layout: Any) -> None:
        """Draw the panel."""
        layout.text("Head Setup")
        draw_utils.draw_head_targets_layout(layout)


class FACEIT_PT_MocapAction(FACEIT_PT_BaseSub):
    """Mocap Action panel."""
    
    bl_label = 'Active Action'
    bl_idname = 'FACEIT_PT_MocapAction'
    bl_parent_id = 'FACEIT_PT_MocapUtils'
    
    def poll(self, context: Any = None) -> bool:
        """Check if the panel should be shown."""
        return True
    
    def draw(self, layout: Any) -> None:
        """Draw the panel."""
        layout.text("Active Action")
        layout.text("Manage mocap actions")


class FACEIT_PT_MocapImporters(FACEIT_PT_BaseMocap):
    """Mocap Importers panel."""
    
    bl_label = 'Import (Recorded)'
    bl_idname = 'FACEIT_PT_MocapImporters'
    
    def poll(self, context: Any = None) -> bool:
        """Check if the panel should be shown."""
        return True
    
    def draw(self, layout: Any) -> None:
        """Draw the panel."""
        layout.text("Import (Recorded)")
        layout.text("Import from FaceCap, Epic, A2F")


class FACEIT_PT_MocapA2F(FACEIT_PT_BaseSub):
    """Mocap A2F panel."""
    
    bl_label = 'Audio2Face'
    bl_idname = 'FACEIT_PT_MocapA2F'
    bl_parent_id = 'FACEIT_PT_MocapImporters'
    faceit_predecessor = 'FACEIT_PT_MocapEpic'
    
    def poll(self, context: Any = None) -> bool:
        """Check if the panel should be shown."""
        return True
    
    def draw(self, layout: Any) -> None:
        """Draw the panel."""
        layout.text("Audio2Face")
        layout.text("Import A2F JSON data")


class FACEIT_PT_MocapFaceCap(FACEIT_PT_BaseSub):
    """Mocap FaceCap panel."""
    
    bl_label = 'Face Cap'
    bl_idname = 'FACEIT_PT_MocapFaceCap'
    bl_parent_id = 'FACEIT_PT_MocapImporters'
    
    def poll(self, context: Any = None) -> bool:
        """Check if the panel should be shown."""
        return True
    
    def draw(self, layout: Any) -> None:
        """Draw the panel."""
        layout.text("Face Cap")
        layout.text("Import FaceCap TXT data")


class FACEIT_PT_MocapEpic(FACEIT_PT_BaseSub):
    """Mocap Epic panel."""
    
    bl_label = 'Live Link Face'
    bl_idname = 'FACEIT_PT_MocapEpic'
    bl_parent_id = 'FACEIT_PT_MocapImporters'
    faceit_predecessor = 'FACEIT_PT_MocapFaceCap'
    
    def poll(self, context: Any = None) -> bool:
        """Check if the panel should be shown."""
        return True
    
    def draw(self, layout: Any) -> None:
        """Draw the panel."""
        layout.text("Live Link Face")
        layout.text("Import Epic CSV data")


class FACEIT_PT_MocapOSC(FACEIT_PT_BaseMocap):
    """Mocap OSC panel."""
    
    bl_label = 'OSC (Live)'
    bl_idname = 'FACEIT_PT_MocapOSC'
    faceit_predecessor = 'FACEIT_PT_MocapImporters'
    
    def poll(self, context: Any = None) -> bool:
        """Check if the panel should be shown."""
        return True
    
    def draw(self, layout: Any) -> None:
        """Draw the panel."""
        layout.text("OSC (Live)")
        layout.text("Live OSC motion capture")