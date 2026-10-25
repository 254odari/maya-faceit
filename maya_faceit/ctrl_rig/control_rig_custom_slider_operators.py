# control_rig_custom_slider_operators.py
# Maya Faceit Plugin - Control Rig Custom Slider Operators
# Converted from Blender to Maya Python 3.11

"""
Control rig custom slider operators for Faceit Maya plugin.
Handles creation and management of custom sliders.
"""

import maya.cmds as cmds
from typing import List, Dict, Optional, Any

from ..core import faceit_utils as futils
from ..core.faceit_data import get_face_region_items
from ..core.shape_key_utils import has_shape_keys
from . import custom_slider_utils
from .control_rig_data import get_driver_from_retarget_dictionary_fixed_slider_range
from .control_rig_utils import get_crig_objects_list


class SearchShapeKeys:
    """Invoke a search popup for all Shape Keys on registered objects."""
    
    name = "SearchShapeKeys"
    label = "Search Popup"
    
    def __init__(self):
        self.shape = ""
    
    def execute(self) -> bool:
        """Execute the operator."""
        # In Maya, we'd use a different UI for searching
        shapes = custom_slider_utils.get_custom_sliders_from_faceit_objects_enum()
        
        if shapes and len(shapes) > 1:
            # Show a dialog for selection
            # For now, just print available shapes
            print("Available shapes:", [s[0] for s in shapes if s[0] != "None"])
        else:
            cmds.warning("No shape keys found")
        
        return True


class SetupCustomController:
    """Setup Controllers for shapes that are not covered by the standard control rig."""
    
    name = "SetupCustomController"
    label = "Custom Controller"
    
    def __init__(self):
        self.new_slider = ""
        self.region = "other"
        self.driver_exists = False
        self.slider_range = "FULL"
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        ctrl_rig = futils.get_faceit_control_armature()
        if ctrl_rig:
            if cmds.attributeQuery("faceit_crig_objects", node=ctrl_rig, exists=True):
                objects_str = cmds.getAttr(f"{ctrl_rig}.faceit_crig_objects") or ""
                return bool(objects_str)
        return False
    
    def invoke(self) -> bool:
        """Invoke the operator."""
        # Check if driver already exists
        faceit_objects = futils.get_faceit_objects_list()
        for obj in faceit_objects:
            if has_shape_keys(obj):
                history = cmds.listHistory(obj, pruneDagObjects=True, interestLevel=2) or []
                for node in history:
                    if cmds.nodeType(node) == 'blendShape':
                        if cmds.attributeQuery(self.new_slider, node=node, exists=True):
                            # Check if there's a driver connection
                            connections = cmds.listConnections(f"{node}.{self.new_slider}", source=True, destination=False) or []
                            for conn in connections:
                                if cmds.nodeType(conn) == 'animCurve':
                                    self.driver_exists = True
                                    break
        
        return True
    
    def execute(self) -> bool:
        """Execute the operator."""
        c_rig = futils.get_faceit_control_armature()
        
        if not c_rig:
            cmds.warning("No Control Armature found.")
            return False
        
        # Get current targets
        crig_targets = self._get_crig_targets(c_rig)
        
        # Check if shape already exists in targets
        if self.new_slider not in crig_targets:
            crig_targets[self.new_slider] = {
                'name': self.new_slider,
                'amplify': 1.0,
                'region': self.region,
                'custom_slider': True,
                'target_shapes': [{'name': self.new_slider}]
            }
        
        # Generate the slider
        slider_range = 'full_range' if self.slider_range == 'FULL' else 'pos_range'
        bone_name = custom_slider_utils.generate_extra_sliders(
            None, self.new_slider, slider_range, c_rig, overwrite=True
        )
        
        if bone_name:
            # Save the slider name
            crig_targets[self.new_slider]['slider_name'] = bone_name
        
        # Connect drivers
        connected_any = False
        faceit_objects = futils.get_faceit_objects_list()
        
        for obj in faceit_objects:
            if has_shape_keys(obj):
                # Get shape keys
                history = cmds.listHistory(obj, pruneDagObjects=True, interestLevel=2) or []
                for node in history:
                    if cmds.nodeType(node) == 'blendShape':
                        # Create driver connection
                        # In Maya, we'd connect the bone to the blend shape weight
                        result, bone_name = get_driver_from_retarget_dictionary_fixed_slider_range(
                            self.new_slider,
                            self.new_slider,
                            c_rig,
                            node,
                            custom_slider=True,
                            current_range='all' if self.slider_range == 'FULL' else 'pos'
                        )
                        if result:
                            connected_any = True
        
        # Save targets
        self._save_crig_targets(c_rig, crig_targets)
        
        if connected_any:
            cmds.warning(f"Successfully created Custom Controller {self.new_slider}")
        else:
            cmds.warning(f"Wasn't able to connect any drivers for the new controller {self.new_slider}.")
        
        return True
    
    def _get_crig_targets(self, c_rig: str) -> Dict:
        """Get control rig targets."""
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
    
    def _save_crig_targets(self, c_rig: str, targets: Dict) -> bool:
        """Save control rig targets."""
        if not cmds.objExists(c_rig):
            return False
        
        if not cmds.attributeQuery("faceit_crig_targets", node=c_rig, exists=True):
            cmds.addAttr(c_rig, ln="faceit_crig_targets", dt="string")
        
        import json
        cmds.setAttr(f"{c_rig}.faceit_crig_targets", json.dumps(targets), type="string")
        
        return True


class RemoveCustomController:
    """Remove Custom Controllers from control rig and crig_targets."""
    
    name = "RemoveCustomController"
    label = "Remove Custom Controller"
    
    def __init__(self):
        self.custom_slider = ""
    
    def poll(self) -> bool:
        """Check if the operator can run."""
        ctrl_rig = futils.get_faceit_control_armature()
        if ctrl_rig:
            if cmds.attributeQuery("faceit_crig_objects", node=ctrl_rig, exists=True):
                objects_str = cmds.getAttr(f"{ctrl_rig}.faceit_crig_objects") or ""
                if objects_str:
                    # Check if there are custom sliders
                    targets = self._get_crig_targets(ctrl_rig)
                    for item_data in targets.values():
                        if item_data.get('custom_slider', False):
                            return True
        return False
    
    def execute(self) -> bool:
        """Execute the operator."""
        c_rig = futils.get_faceit_control_armature()
        
        if not c_rig:
            cmds.warning("No Control Armature found.")
            return False
        
        # Get current targets
        crig_targets = self._get_crig_targets(c_rig)
        
        # Find the custom slider
        if self.custom_slider not in crig_targets:
            cmds.warning(f"Custom Slider '{self.custom_slider}' not found.")
            return False
        
        # Remove drivers
        crig_objects = get_crig_objects_list(c_rig)
        
        for obj in crig_objects:
            if has_shape_keys(obj):
                history = cmds.listHistory(obj, pruneDagObjects=True, interestLevel=2) or []
                for node in history:
                    if cmds.nodeType(node) == 'blendShape':
                        # Remove driver connection
                        if cmds.attributeQuery(self.custom_slider, node=node, exists=True):
                            connections = cmds.listConnections(f"{node}.{self.custom_slider}", source=True, destination=False) or []
                            for conn in connections:
                                if cmds.nodeType(conn) == 'animCurve':
                                    cmds.delete(conn)
        
        # Remove bones
        remove_bones = custom_slider_utils.get_all_slider_bones(c_rig, filter_str=self.custom_slider)
        for bone_name in remove_bones:
            if cmds.objExists(bone_name):
                cmds.delete(bone_name)
        
        # Remove from targets
        del crig_targets[self.custom_slider]
        
        # Save targets
        self._save_crig_targets(c_rig, crig_targets)
        
        cmds.warning(f"Removed custom controller {self.custom_slider}")
        
        return True
    
    def _get_crig_targets(self, c_rig: str) -> Dict:
        """Get control rig targets."""
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
    
    def _save_crig_targets(self, c_rig: str, targets: Dict) -> bool:
        """Save control rig targets."""
        if not cmds.objExists(c_rig):
            return False
        
        if not cmds.attributeQuery("faceit_crig_targets", node=c_rig, exists=True):
            cmds.addAttr(c_rig, ln="faceit_crig_targets", dt="string")
        
        import json
        cmds.setAttr(f"{c_rig}.faceit_crig_targets", json.dumps(targets), type="string")
        
        return True