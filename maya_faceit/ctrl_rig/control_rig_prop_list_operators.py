# control_rig_prop_list_operators.py
# Maya Faceit Plugin - Control Rig Property List Operators
# Converted from Blender to Maya Python 3.11

"""
Control rig property list operators for Faceit Maya plugin.
Handles control rig target objects and shapes management.
"""

import maya.cmds as cmds
from typing import List, Dict, Optional, Any

from ..core import faceit_utils as futils
from ..core import shape_key_utils
from ..core.retarget_list_base import (
    EditTargetShapeBase,
    RemoveTargetShapeBase,
    ResetRegionsOperatorBase,
    SetDefaultRegionsBase,
)
from . import control_rig_utils as ctrl_utils


class ResetCtrlRigRegions(ResetRegionsOperatorBase):
    """Reset control rig regions."""
    
    name = "ResetCtrlRigRegions"
    label = "Reset Ctrl Rig Regions"
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        ctrl_rig = futils.get_faceit_control_armature()
        return ctrl_rig is not None


class SetDefaultCrigRegions(SetDefaultRegionsBase):
    """Set default control rig regions."""
    
    name = "SetDefaultCrigRegions"
    label = "Set Default Ctrl Rig Regions"
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        ctrl_rig = futils.get_faceit_control_armature()
        return ctrl_rig is not None


class RemoveCrigTargetObject:
    """Remove object from target objects of active control rig."""
    
    name = "RemoveCrigTargetObject"
    label = "Remove Target Object"
    
    def __init__(self):
        self.prompt = False
        self.clear_vertex_groups = False
        self.remove_item = ''
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        ctrl_rig = futils.get_faceit_control_armature()
        if ctrl_rig:
            if cmds.attributeQuery("faceit_crig_objects", node=ctrl_rig, exists=True):
                objects_str = cmds.getAttr(f"{ctrl_rig}.faceit_crig_objects") or ""
                return bool(objects_str)
        return False
    
    def execute(self) -> bool:
        """Execute the operator."""
        c_rig = futils.get_faceit_control_armature()
        
        if not c_rig:
            cmds.warning("No control rig found")
            return False
        
        # Get current objects
        objects_str = cmds.getAttr(f"{c_rig}.faceit_crig_objects") or ""
        objects = objects_str.split(',') if objects_str else []
        
        if self.remove_item and self.remove_item in objects:
            objects.remove(self.remove_item)
            cmds.setAttr(f"{c_rig}.faceit_crig_objects", ",".join(objects), type="string")
            return True
        
        return False


class AddCrigTargetObject:
    """Register the selected Object as target for the active control rig."""
    
    name = "AddCrigTargetObject"
    label = "Add Control Rig Target Object"
    
    def __init__(self):
        self.facial_part = ''
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        obj = cmds.ls(selection=True, type='transform')
        ctrl_rig = futils.get_faceit_control_armature()
        
        if obj and ctrl_rig:
            # Check if selected is a mesh
            shapes = cmds.listRelatives(obj[0], shapes=True, type='mesh')
            if shapes:
                return True
        return False
    
    def execute(self) -> bool:
        """Execute the operator."""
        c_rig = futils.get_faceit_control_armature()
        
        if not c_rig:
            cmds.warning("No control rig found")
            return False
        
        selection = cmds.ls(selection=True, type='transform')
        
        if not selection:
            cmds.warning("No objects selected")
            return False
        
        # Get current objects
        objects_str = cmds.getAttr(f"{c_rig}.faceit_crig_objects") or ""
        objects = objects_str.split(',') if objects_str else []
        
        for obj in selection:
            # Check if it's a mesh
            shapes = cmds.listRelatives(obj, shapes=True, type='mesh')
            if shapes:
                if obj not in objects:
                    objects.append(obj)
        
        cmds.setAttr(f"{c_rig}.faceit_crig_objects", ",".join(objects), type="string")
        
        return True


class EditCrigTargetShape(EditTargetShapeBase):
    """Edit control rig target shape."""
    
    name = "EditCrigTargetShape"
    label = "Edit Ctrl Rig Target Shape"
    
    new_target_shape = ""
    
    @staticmethod
    def get_retarget_shapes():
        """Get the retarget list property group."""
        ctrl_rig = futils.get_faceit_control_armature()
        if ctrl_rig:
            if cmds.attributeQuery("faceit_crig_targets", node=ctrl_rig, exists=True):
                targets_str = cmds.getAttr(f"{ctrl_rig}.faceit_crig_targets") or "{}"
                try:
                    import json
                    return json.loads(targets_str)
                except:
                    return {}
        return {}
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        ctrl_rig = futils.get_faceit_control_armature()
        if ctrl_rig:
            if cmds.attributeQuery("faceit_crig_objects", node=ctrl_rig, exists=True):
                objects_str = cmds.getAttr(f"{ctrl_rig}.faceit_crig_objects") or ""
                return bool(objects_str)
        return False


class RemoveCrigTargetShape(RemoveTargetShapeBase):
    """Remove control rig target shape."""
    
    name = "RemoveCrigTargetShape"
    label = "Remove Ctrl Rig Target Shape"
    
    @staticmethod
    def get_retarget_shapes():
        """Get the retarget list property group."""
        ctrl_rig = futils.get_faceit_control_armature()
        if ctrl_rig:
            if cmds.attributeQuery("faceit_crig_targets", node=ctrl_rig, exists=True):
                targets_str = cmds.getAttr(f"{ctrl_rig}.faceit_crig_targets") or "{}"
                try:
                    import json
                    return json.loads(targets_str)
                except:
                    return {}
        return {}
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        ctrl_rig = futils.get_faceit_control_armature()
        return ctrl_rig is not None