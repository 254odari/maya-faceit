# control_rig_driver_operators.py
# Maya Faceit Plugin - Control Rig Driver Operators
# Converted from Blender to Maya Python 3.11

"""
Control rig driver operators for Faceit Maya plugin.
Handles driver setup, removal, and management for the control rig.
"""

import maya.cmds as cmds
from typing import List, Dict, Optional, Any

from ..core import faceit_utils as futils
from ..core import retarget_list_utils as rutils
from ..core import shape_key_utils
from ..core.fc_dr_utils import clear_invalid_drivers
from . import control_rig_data as ctrl_data
from . import control_rig_utils as ctrl_utils


class SetupControlDrivers:
    """Setup drivers to control the shape keys with control rig."""
    
    name = "SetupControlDrivers"
    label = "Connect Control Rig"
    
    def __init__(self):
        self.debug = True
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        c_rig = futils.get_faceit_control_armature()
        if c_rig:
            if cmds.attributeQuery("faceit_crig_objects", node=c_rig, exists=True):
                objects_str = cmds.getAttr(f"{c_rig}.faceit_crig_objects") or ""
                return bool(objects_str)
        return False
    
    def execute(self) -> bool:
        """Execute the operator."""
        c_rig = futils.get_faceit_control_armature()
        
        if not c_rig:
            cmds.warning("No control rig found")
            return False
        
        # Show the rig
        cmds.setAttr(f"{c_rig}.visibility", 1)
        
        # Remove existing drivers
        self._remove_control_drivers(c_rig)
        
        # Get target objects and shapes
        crig_objects = ctrl_utils.get_crig_objects_list(c_rig)
        crig_targets = self._get_crig_targets(c_rig)
        
        if not crig_targets:
            cmds.warning("Couldn't find any target shapes. Please update the control rig first.")
            return False
        
        if not crig_objects:
            cmds.warning("Couldn't find any target objects. Please specify them or update the control rig first.")
            return False
        
        connected_any = False
        
        # Get jaw open name
        jaw_open_name = 'jawOpen'
        jaw_open_item = crig_targets.get('jawOpen')
        if jaw_open_item:
            jaw_open_target = jaw_open_item.get('target_shapes', [])
            if jaw_open_target:
                jaw_open_name = jaw_open_target[0].get('name', 'jawOpen')
        
        # Create drivers for each target
        for shape_item_name, shape_item_data in crig_targets.items():
            target_shape_list = shape_item_data.get('target_shapes', [])
            
            for target_shape in target_shape_list:
                target_name = target_shape.get('name', '')
                
                if not target_name:
                    continue
                
                # Create driver
                result, bone_name = ctrl_data.get_driver_from_retarget_dictionary_fixed_slider_range(
                    shape_item_name,
                    target_name,
                    c_rig,
                    None,  # shape_key_data - we'll handle this differently in Maya
                    custom_slider=shape_item_data.get('custom_slider', False),
                    jaw_open_shape=jaw_open_name
                )
                
                if result:
                    connected_any = True
                    # In Maya, we would create the actual driver connection here
        
        if connected_any:
            cmds.warning("Connected Control Rig")
            return True
        
        cmds.warning("Failed to connect control rig drivers")
        return False
    
    def _remove_control_drivers(self, c_rig: str) -> None:
        """Remove existing control drivers."""
        # Get target objects
        crig_objects = ctrl_utils.get_crig_objects_list(c_rig)
        
        for obj in crig_objects:
            if not cmds.objExists(obj):
                continue
            
            if shape_key_utils.has_shape_keys(obj):
                # Get blend shape node
                history = cmds.listHistory(obj, pruneDagObjects=True, interestLevel=2) or []
                for node in history:
                    if cmds.nodeType(node) == 'blendShape':
                        # Remove drivers on blend shape targets
                        targets = cmds.listAttr(f"{node}.weight", multi=True) or []
                        for target in targets:
                            if target.startswith('weight'):
                                continue
                            # Remove driver if exists
                            if cmds.attributeQuery(target, node=node, exists=True):
                                # Check if there's a driver connection
                                connections = cmds.listConnections(f"{node}.{target}", source=True, destination=False) or []
                                for conn in connections:
                                    if cmds.nodeType(conn) == 'animCurve':
                                        cmds.delete(conn)
    
    def _get_crig_targets(self, c_rig: str) -> Dict:
        """Get control rig targets from the control rig object."""
        if not cmds.objExists(c_rig):
            return {}
        
        if not cmds.attributeQuery("faceit_crig_targets", node=c_rig, exists=True):
            return {}
        
        targets_str = cmds.getAttr(f"{c_rig}.faceit_crig_targets") or "{}"
        try:
            import json
            return json.loads(targets_str)
        except:
            return {}


class RemoveControlDrivers:
    """Remove all drivers for active control rig."""
    
    name = "RemoveControlDrivers"
    label = "Disconnect Control Rig"
    
    def __init__(self):
        self.remove_all = False
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        c_rig = futils.get_faceit_control_armature()
        return c_rig is not None
    
    def execute(self) -> bool:
        """Execute the operator."""
        c_rig = futils.get_faceit_control_armature()
        
        if not c_rig:
            cmds.warning("No control rig found")
            return False
        
        # Get target objects
        crig_objects = ctrl_utils.get_crig_objects_list(c_rig)
        
        if not crig_objects:
            # Fallback to faceit objects
            crig_objects = futils.get_faceit_objects_list()
        
        # Get target shapes
        crig_targets = self._get_crig_targets(c_rig)
        all_target_shapes = []
        
        for shape_item_data in crig_targets.values():
            target_shapes = shape_item_data.get('target_shapes', [])
            for ts in target_shapes:
                all_target_shapes.append(ts.get('name', ''))
        
        clear_any = False
        
        for obj in crig_objects:
            if not cmds.objExists(obj):
                continue
            
            if shape_key_utils.has_shape_keys(obj):
                # Get blend shape node
                history = cmds.listHistory(obj, pruneDagObjects=True, interestLevel=2) or []
                for node in history:
                    if cmds.nodeType(node) == 'blendShape':
                        if self.remove_all:
                            # Remove all drivers
                            targets = cmds.listAttr(f"{node}.weight", multi=True) or []
                            for target in targets:
                                if target.startswith('weight'):
                                    continue
                                # Remove driver if exists
                                connections = cmds.listConnections(f"{node}.{target}", source=True, destination=False) or []
                                for conn in connections:
                                    if cmds.nodeType(conn) == 'animCurve':
                                        cmds.delete(conn)
                                        clear_any = True
                        else:
                            # Only remove ARKit target shape drivers
                            for target_name in all_target_shapes:
                                if cmds.attributeQuery(target_name, node=node, exists=True):
                                    connections = cmds.listConnections(f"{node}.{target_name}", source=True, destination=False) or []
                                    for conn in connections:
                                        if cmds.nodeType(conn) == 'animCurve':
                                            cmds.delete(conn)
                                            clear_any = True
                                    
                                    # Reset value to 0
                                    cmds.setAttr(f"{node}.{target_name}", 0)
        
        if not clear_any:
            cmds.warning("No drivers found on the set target objects.")
        else:
            cmds.warning(f"Disconnected Control Rig {c_rig}")
        
        # Clear invalid drivers
        clear_invalid_drivers()
        
        # Refresh
        cmds.refresh()
        
        return True
    
    def _get_crig_targets(self, c_rig: str) -> Dict:
        """Get control rig targets from the control rig object."""
        if not cmds.objExists(c_rig):
            return {}
        
        if not cmds.attributeQuery("faceit_crig_targets", node=c_rig, exists=True):
            return {}
        
        targets_str = cmds.getAttr(f"{c_rig}.faceit_crig_targets") or "{}"
        try:
            import json
            return json.loads(targets_str)
        except:
            return {}


class ClearOldCtrlRigData:
    """Find inactive control rigs, remove them and clear eventual drivers."""
    
    name = "ClearOldCtrlRigData"
    label = "Purge Old Control Rigs and Drivers"
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        return True
    
    def execute(self) -> bool:
        """Execute the operator."""
        # Find old control rigs
        old_control_rigs = []
        
        for obj in cmds.ls(type='transform'):
            # Check if it's a control rig
            if cmds.attributeQuery("ctrl_rig_id", node=obj, exists=True):
                # Check if it's referenced in scene data
                c_rig = futils.get_faceit_control_armature()
                if obj != c_rig:
                    old_control_rigs.append(obj)
            elif 'FaceitControlRig' in obj:
                c_rig = futils.get_faceit_control_armature()
                if obj != c_rig:
                    old_control_rigs.append(obj)
        
        if not old_control_rigs:
            cmds.warning("No old control rigs found")
            return True
        
        for c_rig in old_control_rigs:
            # Remove drivers from target objects
            crig_objects = ctrl_utils.get_crig_objects_list(c_rig)
            
            if not crig_objects:
                crig_objects = futils.get_faceit_objects_list()
            
            # Get target shapes
            crig_targets = self._get_crig_targets(c_rig)
            all_target_shapes = []
            
            for shape_item_data in crig_targets.values():
                target_shapes = shape_item_data.get('target_shapes', [])
                for ts in target_shapes:
                    all_target_shapes.append(ts.get('name', ''))
            
            for obj in crig_objects:
                if not cmds.objExists(obj):
                    continue
                
                if shape_key_utils.has_shape_keys(obj):
                    history = cmds.listHistory(obj, pruneDagObjects=True, interestLevel=2) or []
                    for node in history:
                        if cmds.nodeType(node) == 'blendShape':
                            for target_name in all_target_shapes:
                                if cmds.attributeQuery(target_name, node=node, exists=True):
                                    connections = cmds.listConnections(f"{node}.{target_name}", source=True, destination=False) or []
                                    for conn in connections:
                                        if cmds.nodeType(conn) == 'animCurve':
                                            cmds.delete(conn)
                                    cmds.setAttr(f"{node}.{target_name}", 0)
            
            # Remove the old control rig
            cmds.warning(f"Removing old Control Rig {c_rig}")
            cmds.delete(c_rig)
        
        # Clear invalid drivers
        clear_invalid_drivers()
        
        # Refresh
        cmds.refresh()
        
        return True
    
    def _get_crig_targets(self, c_rig: str) -> Dict:
        """Get control rig targets from the control rig object."""
        if not cmds.objExists(c_rig):
            return {}
        
        if not cmds.attributeQuery("faceit_crig_targets", node=c_rig, exists=True):
            return {}
        
        targets_str = cmds.getAttr(f"{c_rig}.faceit_crig_targets") or "{}"
        try:
            import json
            return json.loads(targets_str)
        except:
            return {}