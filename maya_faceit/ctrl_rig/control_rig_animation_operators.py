# control_rig_animation_operators.py
# Maya Faceit Plugin - Control Rig Animation Operators
# Converted from Blender to Maya Python 3.11

"""
Control rig animation operators for Faceit Maya plugin.
Handles baking between shape keys and control rig.
"""

import maya.cmds as cmds
import maya.api.OpenMaya as om2
import time
import numpy as np
from typing import List, Dict, Optional, Any

from ..core import faceit_utils as futils
from ..core import fc_dr_utils
from ..core import retarget_list_utils
from ..core import shape_key_utils
from . import control_rig_data as ctrl_data
from . import control_rig_utils

CRIG_ACTION_SUFFIX = '_control_rig'


class BakeShapeKeysToControlRig:
    """Bake a Shape Key Action to the Control Rig."""
    
    name = "BakeShapeKeysToControlRig"
    label = "Bake Shape Key Action to Control Rig"
    
    def __init__(self):
        self.resample_fcurves = False
        self.new_action_name = ""
        self.compensate_amplify_values = False
        self.compensate_arkit_amplify_values = True
        self.ignore_use_animation = False
        self.show_advanced_settings = False
        self.use_mocap_action = True
        self.frame_start = 0
        self.overwrite_method = 'REPLACE'
    
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
        
        # Get target objects
        target_objects = control_rig_utils.get_crig_objects_list(c_rig)
        
        if not target_objects:
            cmds.warning("No target objects found")
            return False
        
        # Get shape key action
        sk_action = self._get_shape_key_action()
        
        if not sk_action:
            cmds.warning("Couldn't find a suitable action.")
            return False
        
        # Get control rig action
        c_rig_action = self._get_or_create_crig_action(c_rig)
        
        if not c_rig_action:
            cmds.warning("Couldn't create control rig action")
            return False
        
        # Get crig targets
        crig_targets = self._get_crig_targets(c_rig)
        
        # Process each shape key
        bone_motion_data = {}
        
        for shape_item_name, shape_item_data in crig_targets.items():
            if not self.ignore_use_animation:
                if not shape_item_data.get('use_animation', True):
                    continue
            
            target_shapes = shape_item_data.get('target_shapes', [])
            
            for target_shape in target_shapes:
                target_name = target_shape.get('name', '')
                
                if not target_name:
                    continue
                
                # Find the fcurve for this shape key
                fc = self._find_fcurve(sk_action, target_name)
                
                if not fc:
                    continue
                
                # Get keyframe data
                kf_data = self._get_keyframe_data(fc)
                
                # Get bone animation data
                dp, array_index, max_range, min_range, value_range, main_dir, bone_name = ctrl_data.get_bone_animation_data(
                    shape_item_name, c_rig
                )
                
                # Scale to new range
                amp_factor = 1.0
                if self.compensate_amplify_values:
                    amp_factor *= shape_item_data.get('amplify', 1.0)
                
                scaled_kf_data = self._scale_to_new_range(
                    kf_data, min_range, max_range, 0, 1, value_range, main_dir,
                    is_scale='scale' in dp, amplify_compensation=amp_factor
                )
                
                # Add to motion data
                self._populate_motion_data(
                    bone_motion_data, dp, array_index, scaled_kf_data,
                    is_scale='scale' in dp
                )
        
        # Apply motion data to control rig action
        for key, motion_data in bone_motion_data.items():
            data = motion_data['kf_data']
            data_copy = np.copy(data)
            data_copy[:, 0] += self.frame_start
            
            dp = motion_data['data_path']
            array_index = motion_data['array_index']
            
            # Create or get fcurve
            fc = self._get_or_create_fcurve(c_rig_action, dp, array_index)
            
            # Populate keyframes
            self._populate_keyframes(fc, data_copy)
        
        return True
    
    def _get_shape_key_action(self) -> Optional[str]:
        """Get the shape key action."""
        # In Maya, we'd get this from the scene
        # For now, return None
        return None
    
    def _get_or_create_crig_action(self, c_rig: str) -> Optional[str]:
        """Get or create control rig action."""
        # Get current action
        if cmds.attributeQuery("currentAction", node=c_rig, exists=True):
            action = cmds.getAttr(f"{c_rig}.currentAction") or ""
            if action and cmds.objExists(action):
                if self.overwrite_method == 'REPLACE':
                    cmds.delete(action)
                else:
                    return action
        
        # Create new action
        if not self.new_action_name:
            self.new_action_name = f"{c_rig}{CRIG_ACTION_SUFFIX}"
        
        action = cmds.createNode("animCurveUA", name=self.new_action_name)
        cmds.setAttr(f"{c_rig}.currentAction", action, type="string")
        
        return action
    
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
    
    def _find_fcurve(self, action: str, target_name: str) -> Optional[str]:
        """Find an fcurve for a shape key."""
        if not action or not cmds.objExists(action):
            return None
        
        curves = cmds.listAnimCurves(action) or []
        for curve in curves:
            attr = cmds.getAttr(f"{curve}.attributeName") or ""
            if target_name in attr:
                return curve
        
        return None
    
    def _get_keyframe_data(self, curve: str) -> np.ndarray:
        """Get keyframe data from an fcurve."""
        if not cmds.objExists(curve):
            return np.array([])
        
        keyframes = cmds.keyframe(curve, query=True, timeChange=True) or []
        values = cmds.keyframe(curve, query=True, valueChange=True) or []
        
        if not keyframes:
            return np.array([])
        
        return np.array(list(zip(keyframes, values)))
    
    def _scale_to_new_range(
        self,
        kf_data: np.ndarray,
        min_range: float,
        max_range: float,
        sk_min: float,
        sk_max: float,
        range_type: str,
        main_dir: int = 1,
        is_scale: bool = False,
        amplify_compensation: float = 1.0
    ) -> np.ndarray:
        """Scale keyframe data to a new range."""
        if kf_data.size == 0:
            return kf_data
        
        frames = kf_data[:, 0]
        data = kf_data[:, 1]
        data /= amplify_compensation
        
        if range_type == 'pos':
            data = np.clip(data, 0, max_range)
        elif range_type == 'neg':
            max_range = min_range
            data = np.clip(data, max_range, 0)
        elif range_type == 'all':
            if main_dir == -1:
                max_range = min_range
        
        if is_scale:
            min_range = 1
        else:
            min_range = 0
        
        sk_min = 0
        
        # Scale data
        scaled_data = ((sk_max - sk_min) * (data - min_range) / (max_range - min_range)) + sk_min
        
        return np.vstack((frames, scaled_data)).T
    
    def _populate_motion_data(
        self,
        motion_data: Dict,
        dp: str,
        array_index: int,
        kf_data: np.ndarray,
        is_scale: bool = False
    ) -> None:
        """Populate motion data dictionary."""
        key = f"{dp}_{array_index}"
        
        if key in motion_data:
            motion_data[key]['kf_data'][:, 1] += kf_data[:, 1]
        else:
            motion_data[key] = {
                'data_path': dp,
                'array_index': array_index,
                'kf_data': kf_data,
            }
    
    def _get_or_create_fcurve(self, action: str, dp: str, array_index: int) -> Optional[str]:
        """Get or create an fcurve."""
        if not action or not cmds.objExists(action):
            return None
        
        # Find existing curve
        curves = cmds.listAnimCurves(action) or []
        for curve in curves:
            attr = cmds.getAttr(f"{curve}.attributeName") or ""
            idx = cmds.getAttr(f"{curve}.arrayIndex") or 0
            if attr == dp and idx == array_index:
                return curve
        
        # Create new curve
        curve = cmds.createNode("animCurveUA", name=f"{action}_{dp.replace('.', '_')}")
        cmds.connectAttr(f"{curve}.output", f"{action}.{dp}")
        cmds.setAttr(f"{curve}.arrayIndex", array_index)
        
        return curve
    
    def _populate_keyframes(self, curve: str, data: np.ndarray) -> bool:
        """Populate keyframes on an fcurve."""
        if not curve or data.size == 0:
            return False
        
        for frame, value in data:
            cmds.setKeyframe(curve, t=frame, v=value)
        
        return True


class BakeControlRigToShapeKeys:
    """Bake the animation from the control rig to the target shapes."""
    
    name = "BakeControlRigToShapeKeys"
    label = "Bake Control Rig Action to Shape Keys"
    
    def __init__(self):
        self.c_rig_operation = 'DISCONNECT'
        self.bake_method = 'FAST'
        self.action_source = ""
        self.action_target = 'ACTIVE'
        self.new_action_name = 'controls_action'
        self.new_action_exists = False
        self.active_action_name = ""
        self.overwrite_method = 'REPLACE'
        self.resample_fcurves = False
        self.copy_fcurve_properties = False
        self.copy_fcurve_modifiers = False
        self.copy_fcurve_handles = False
        self.compensate_amplify_values = True
        self.ignore_use_animation = False
        self.show_advanced_settings = False
        self.frame_start = 0
    
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
        
        # Get target objects
        target_objects = control_rig_utils.get_crig_objects_list(c_rig)
        
        if not target_objects:
            cmds.warning("No target objects found")
            return False
        
        # Get control rig action
        rig_action = self._get_crig_action(c_rig)
        
        if not rig_action:
            cmds.warning("No control rig action found")
            return False
        
        # Get or create shape key action
        sk_action = self._get_or_create_sk_action()
        
        if not sk_action:
            cmds.warning("Couldn't create shape key action")
            return False
        
        # Get crig targets
        crig_targets = self._get_crig_targets(c_rig)
        
        # Process each target
        for shape_item_name, shape_item_data in crig_targets.items():
            if not self.ignore_use_animation:
                if not shape_item_data.get('use_animation', True):
                    continue
            
            # Get bone animation data
            dp, array_index, max_range, min_range, value_range, main_dir, bone_name = ctrl_data.get_bone_animation_data(
                shape_item_name, c_rig
            )
            
            # Get bone fcurve
            bone_fcurve = self._find_fcurve(rig_action, dp, array_index)
            
            if not bone_fcurve:
                continue
            
            # Get keyframe data
            kf_data = self._get_keyframe_data(bone_fcurve)
            
            # Apply amplification
            amp_factor = 1.0
            if self.compensate_amplify_values:
                amp_factor *= shape_item_data.get('amplify', 1.0)
            
            # Scale to shape key range
            sk_min = 0
            sk_max = 1
            is_scale = 'scale' in dp
            
            scaled_kf_data = self._scale_to_new_range(
                kf_data, min_range, max_range, sk_min, sk_max, value_range, main_dir,
                is_scale=is_scale, compensate_amplify=amp_factor
            )
            
            # Apply to shape key action
            target_shapes = shape_item_data.get('target_shapes', [])
            for target_shape in target_shapes:
                target_name = target_shape.get('name', '')
                if not target_name:
                    continue
                
                # Create fcurve for this shape key
                sk_dp = f'key_blocks["{target_name}"].value'
                sk_fcurve = self._get_or_create_fcurve(sk_action, sk_dp, -1)
                
                # Populate keyframes
                self._populate_keyframes(sk_fcurve, scaled_kf_data)
        
        # Remove drivers
        self._remove_control_drivers(c_rig)
        
        # Post-bake operation
        self._after_bake_operation(c_rig, self.c_rig_operation)
        
        return True
    
    def _get_crig_action(self, c_rig: str) -> Optional[str]:
        """Get the control rig action."""
        if cmds.attributeQuery("currentAction", node=c_rig, exists=True):
            action = cmds.getAttr(f"{c_rig}.currentAction") or ""
            if action and cmds.objExists(action):
                return action
        return None
    
    def _get_or_create_sk_action(self) -> Optional[str]:
        """Get or create a shape key action."""
        # Check if action exists
        if self.new_action_name and cmds.objExists(self.new_action_name):
            if self.overwrite_method == 'REPLACE':
                cmds.delete(self.new_action_name)
            else:
                return self.new_action_name
        
        # Create new action
        if not self.new_action_name:
            self.new_action_name = 'mocap_action'
        
        action = cmds.createNode("animCurveUA", name=self.new_action_name)
        return action
    
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
    
    def _find_fcurve(self, action: str, dp: str, array_index: int) -> Optional[str]:
        """Find an fcurve."""
        if not action or not cmds.objExists(action):
            return None
        
        curves = cmds.listAnimCurves(action) or []
        for curve in curves:
            attr = cmds.getAttr(f"{curve}.attributeName") or ""
            idx = cmds.getAttr(f"{curve}.arrayIndex") or 0
            if attr == dp and idx == array_index:
                return curve
        
        return None
    
    def _get_keyframe_data(self, curve: str) -> np.ndarray:
        """Get keyframe data from an fcurve."""
        if not cmds.objExists(curve):
            return np.array([])
        
        keyframes = cmds.keyframe(curve, query=True, timeChange=True) or []
        values = cmds.keyframe(curve, query=True, valueChange=True) or []
        
        if not keyframes:
            return np.array([])
        
        return np.array(list(zip(keyframes, values)))
    
    def _scale_to_new_range(
        self,
        kf_data: np.ndarray,
        min_range: float,
        max_range: float,
        sk_min: float,
        sk_max: float,
        range_type: str,
        main_dir: int = 1,
        is_scale: bool = False,
        compensate_amplify: float = 1.0
    ) -> np.ndarray:
        """Scale keyframe data to a new range."""
        if kf_data.size == 0:
            return kf_data
        
        frames = kf_data[:, 0]
        data = kf_data[:, 1]
        
        if range_type == 'pos':
            data = np.clip(data, 0, max_range)
        elif range_type == 'neg':
            max_range = min_range
            data = np.clip(data, max_range, 0)
        elif range_type == 'all':
            if main_dir == -1:
                max_range = min_range
        
        if is_scale:
            min_range = 1
        else:
            min_range = 0
        
        sk_min = 0
        
        data *= compensate_amplify
        
        scaled_data = ((sk_max - sk_min) * (data - min_range) / (max_range - min_range)) + sk_min
        
        return np.vstack((frames, scaled_data)).T
    
    def _get_or_create_fcurve(self, action: str, dp: str, array_index: int) -> Optional[str]:
        """Get or create an fcurve."""
        if not action or not cmds.objExists(action):
            return None
        
        # Find existing curve
        curves = cmds.listAnimCurves(action) or []
        for curve in curves:
            attr = cmds.getAttr(f"{curve}.attributeName") or ""
            idx = cmds.getAttr(f"{curve}.arrayIndex") or 0
            if attr == dp and idx == array_index:
                return curve
        
        # Create new curve
        curve = cmds.createNode("animCurveUA", name=f"{action}_{dp.replace('.', '_')}")
        cmds.connectAttr(f"{curve}.output", f"{action}.{dp}")
        cmds.setAttr(f"{curve}.arrayIndex", array_index)
        
        return curve
    
    def _populate_keyframes(self, curve: str, data: np.ndarray) -> bool:
        """Populate keyframes on an fcurve."""
        if not curve or data.size == 0:
            return False
        
        for frame, value in data:
            cmds.setKeyframe(curve, t=frame, v=value)
        
        return True
    
    def _remove_control_drivers(self, c_rig: str) -> None:
        """Remove control drivers."""
        # Get target objects
        crig_objects = control_rig_utils.get_crig_objects_list(c_rig)
        
        for obj in crig_objects:
            if not cmds.objExists(obj):
                continue
            
            if shape_key_utils.has_shape_keys(obj):
                history = cmds.listHistory(obj, pruneDagObjects=True, interestLevel=2) or []
                for node in history:
                    if cmds.nodeType(node) == 'blendShape':
                        # Remove all driver connections
                        targets = cmds.listAttr(f"{node}.weight", multi=True) or []
                        for target in targets:
                            if target.startswith('weight'):
                                continue
                            connections = cmds.listConnections(f"{node}.{target}", source=True, destination=False) or []
                            for conn in connections:
                                if cmds.nodeType(conn) == 'animCurve':
                                    cmds.delete(conn)
    
    def _after_bake_operation(self, c_rig: str, operation: str) -> None:
        """Perform post-bake operation."""
        if operation == 'REMOVE':
            cmds.delete(c_rig)
        elif operation == 'HIDE':
            cmds.setAttr(f"{c_rig}.visibility", 0)
        else:
            # DISCONNECT - drivers already removed
            pass