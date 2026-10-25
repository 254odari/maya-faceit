# control_rig_operators.py
# Maya Faceit Plugin - Control Rig Operators
# Converted from Blender to Maya Python 3.11

"""
Control rig operators for Faceit Maya plugin.
Handles control rig updates and management.
"""

import maya.cmds as cmds
from typing import List, Dict, Optional, Any

from ..core import faceit_utils as futils
from ..core import shape_key_utils
from . import control_rig_data as ctrl_data
from . import control_rig_utils as ctrl_utils


class UpdateControlRig:
    """Update the active Faceit control rig object."""
    
    name = "UpdateControlRig"
    label = "Update Control Rig"
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        ctrl_rig = futils.get_faceit_control_armature()
        if ctrl_rig:
            # Check version
            if cmds.attributeQuery("ctrl_rig_version", node=ctrl_rig, exists=True):
                version = cmds.getAttr(f"{ctrl_rig}.ctrl_rig_version")
                return version < ctrl_data.CNTRL_RIG_VERSION
        return False
    
    def execute(self) -> bool:
        """Execute the operator."""
        c_rig = futils.get_faceit_control_armature()
        
        if not c_rig:
            cmds.warning("No control rig found")
            return False
        
        # Show the rig
        cmds.setAttr(f"{c_rig}.visibility", 1)
        
        # Get current version
        version = cmds.getAttr(f"{c_rig}.ctrl_rig_version") if cmds.attributeQuery("ctrl_rig_version", node=c_rig, exists=True) else 1.0
        
        if version <= 1.2:
            # Update target objects and shapes
            ctrl_utils.populate_control_rig_target_objects_from_scene(c_rig)
            ctrl_utils.populate_control_rig_target_shapes_from_scene(c_rig, update=True)
        
        # Update version
        cmds.setAttr(f"{c_rig}.ctrl_rig_version", ctrl_data.CNTRL_RIG_VERSION)
        
        # Setup drivers
        try:
            self._setup_control_drivers(c_rig)
        except:
            print("Wasn't able to connect the drivers.")
        
        return True
    
    def _setup_control_drivers(self, c_rig: str) -> None:
        """Setup control drivers."""
        # In Maya, we'd create connections
        pass


class LoadCrigSettingsFromScene:
    """Populates the Control Rig Objects and Target Shapes based on the active scene settings."""
    
    name = "LoadCrigSettingsFromScene"
    label = "Load to Control Rig"
    
    def __init__(self):
        self.load_target_objects = True
        self.load_arkit_target_shapes = True
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        ctrl_rig = futils.get_faceit_control_armature()
        return ctrl_rig is not None
    
    def execute(self) -> bool:
        """Execute the operator."""
        c_rig = futils.get_faceit_control_armature()
        
        if not c_rig:
            cmds.warning("No control rig found")
            return False
        
        # Show the rig
        cmds.setAttr(f"{c_rig}.visibility", 1)
        
        if self.load_target_objects:
            faceit_objects = futils.get_faceit_objects_list()
            if faceit_objects:
                ctrl_utils.populate_control_rig_target_objects_from_scene(c_rig)
            else:
                cmds.warning("Didn't find any registered objects to load as control rig target objects.")
        
        if self.load_arkit_target_shapes:
            # Check if ARKit shapes exist in scene
            # In Maya, we'd check from scene data
            ctrl_utils.populate_control_rig_target_shapes_from_scene(c_rig, populate_amplify_values=True)
        
        return True


class LoadFaceitSettingsFromCRig:
    """Populates the Faceit Objects and ARKit Target Shapes based on objects driven by active control rig."""
    
    name = "LoadFaceitSettingsFromCRig"
    label = "Load to Scene"
    
    def __init__(self):
        self.auto_sync = False
        self.load_target_objects = True
        self.load_arkit_target_shapes = True
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        ctrl_rig = futils.get_faceit_control_armature()
        return ctrl_rig is not None
    
    def execute(self) -> bool:
        """Execute the operator."""
        c_rig = futils.get_faceit_control_armature()
        
        if not c_rig:
            cmds.warning("No control rig found")
            return False
        
        # Show the rig
        cmds.setAttr(f"{c_rig}.visibility", 1)
        
        # Get target objects from control rig
        target_objects = ctrl_utils.get_crig_objects_list(c_rig)
        
        if self.load_target_objects:
            if target_objects:
                # Clear existing faceit objects
                # In Maya, we'd update the faceit_objects list
                pass
            else:
                cmds.warning("Can't find target objects. Please update the Control Rig first.")
                return False
        
        if self.load_arkit_target_shapes:
            # Load ARKit target shapes from control rig
            pass
        
        return True


class SetAmplify:
    """Set an amplify value for all target shapes."""
    
    name = "SetAmplify"
    label = "Set Amplify Value"
    
    def __init__(self):
        self.amplify_value = 1.0
        self.regions = 'VISIBLE'
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        ctrl_rig = futils.get_faceit_control_armature()
        return ctrl_rig is not None
    
    def execute(self) -> bool:
        """Execute the operator."""
        c_rig = futils.get_faceit_control_armature()
        
        if not c_rig:
            cmds.warning("No control rig found")
            return False
        
        # In Maya, we'd update the amplify values on the control rig
        # This would be stored in custom attributes
        
        return True


class SelectBoneFromSourceShape:
    """Select the bone that drives the target shapes for this ARKit source shape."""
    
    name = "SelectBoneFromSourceShape"
    label = "Select Bone"
    
    def __init__(self, expression: str = ""):
        self.expression = expression
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        ctrl_rig = futils.get_faceit_control_armature()
        if ctrl_rig:
            return cmds.getAttr(f"{ctrl_rig}.visibility")
        return False
    
    def execute(self) -> bool:
        """Execute the operator."""
        c_rig = futils.get_faceit_control_armature()
        
        if not c_rig:
            cmds.warning("Control Rig not found in scene")
            return False
        
        # Get bone name from driver dict
        bone_name = None
        dr_dict = ctrl_data.control_rig_drivers_dict.get(self.expression)
        
        if dr_dict:
            bone_name, _, _ = ctrl_data.get_bone_settings_from_driver_dict(dr_dict)
        
        if not bone_name:
            cmds.warning(f"The expression {self.expression} could not be found in driven ARKit shapes.")
            return False
        
        if not cmds.objExists(bone_name):
            cmds.warning(f"Bone {bone_name} not found")
            return False
        
        # Select the bone
        cmds.select(bone_name)
        
        return True


class ControlRigSetSliderRanges:
    """Set the slider ranges on all controllers."""
    
    name = "ControlRigSetSliderRanges"
    label = "Set Ranges for Control Rig"
    
    def __init__(self):
        self.new_range = 'ALL'
        self.reconnect = True
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        ctrl_rig = futils.get_faceit_control_armature()
        return ctrl_rig is not None
    
    def execute(self) -> bool:
        """Execute the operator."""
        c_rig = futils.get_faceit_control_armature()
        
        if not c_rig:
            cmds.warning("The control rig has to be generated first.")
            return False
        
        # Remove existing drivers
        self._remove_control_drivers(c_rig)
        
        # Set slider ranges
        # In Maya, we'd update constraint limits
        for bone in cmds.ls(type='joint'):
            if 'slider' in bone:
                # Update limit constraints
                pass
        
        if self.reconnect:
            self._setup_control_drivers(c_rig)
        
        return True
    
    def _remove_control_drivers(self, c_rig: str) -> None:
        """Remove control drivers."""
        # In Maya, we'd remove driver connections
        pass
    
    def _setup_control_drivers(self, c_rig: str) -> None:
        """Setup control drivers."""
        # In Maya, we'd create driver connections
        pass


class ConstrainToBodyRig:
    """Set child of constraint for the active bone in a selected armature."""
    
    name = "ConstrainToBodyRig"
    label = "Set Child Of"
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        c_rig = futils.get_faceit_control_armature()
        if c_rig:
            selection = cmds.ls(selection=True, type='joint')
            if selection:
                return True
        return False
    
    def execute(self) -> bool:
        """Execute the operator."""
        c_rig = futils.get_faceit_control_armature()
        
        if not c_rig:
            cmds.warning("No control rig found")
            return False
        
        selection = cmds.ls(selection=True, type='joint')
        
        if not selection:
            cmds.warning("A bone needs to be selected as target!")
            return False
        
        target_bone = selection[0]
        target_rig = cmds.listRelatives(target_bone, parent=True, type='transform')[0] if cmds.listRelatives(target_bone, parent=True, type='transform') else None
        
        if not target_rig:
            cmds.warning("Could not find the target rig.")
            return False
        
        # Create child-of constraint
        cmds.parentConstraint(target_bone, c_rig, maintainOffset=True)
        
        return True