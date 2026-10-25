# mocap_base.py
# Maya Faceit Plugin - Mocap Base
# Converted from Blender to Maya Python 3.11

"""
Mocap base classes for Faceit Maya plugin.
Provides base functionality for motion capture import and animation.
"""

import maya.cmds as cmds # type: ignore
import maya.api.OpenMaya as om2 # type: ignore
import math
import numpy as np
from typing import List, Dict, Optional, Tuple, Any


# ============================================================
# Constants
# ============================================================

CHANNELS_ROTATION_MODE_DICT = {
    'EULER': 3,
    'AXIS_ANGLE': 4,
    'QUATERNION': 4
}

CHANNELS_FACECAP_TO_BLENDER = {
    0: 1,
    1: 2,
    2: 1,
}

FACECAP_SCALE_TO_BLENDER = 0.01


# ============================================================
# Mocap Base Class
# ============================================================

class MocapBase:
    """
    Store mocap values and general functions for live, recording, loading of animations.
    """
    
    def __init__(self):
        self.fps = 24
        self.objects = None
        self.source_shape_reference = []
        self.retarget_shapes = None
        self.target_shapes_dict = {}
        self.use_region_filter = False
        self.active_regions_dict = {}
        self.animate_shapes = False
        self.flip_animation = False
        
        # Head Transform animation
        self.head_obj = None
        self.head_bone = None
        self.initial_head_rotation = None
        self.initial_location_offset = None
        self.head_rotation_mode = 'EULER'
        self.head_rotation_data_path = 'rotation_euler'
        self.head_location_multiplier = 1.0
        self.scene_scale_multiplier = 0.01
        
        self.source_rotation_units = 'DEG'
        self.animate_head_rotation = False
        self.animate_head_location = False
        self.animate_eyes = False
        self.dynamic_sk_ranges = True
        
        # For Recording
        self.animation_timestamps = []
        self.sk_animation_lists = []
        self.head_rot_animation_lists = []
        self.head_loc_animation_lists = []
        self.eye_L_animation_lists = []
        self.eye_R_animation_lists = []
        
        self.sk_action = None
        self.head_action = None
        
        self._initialize_mocap_settings()
        self.fps = self._get_scene_frame_rate()
    
    def _initialize_mocap_settings(self):
        """Initialize mocap settings - to be overridden by subclasses."""
        pass
    
    def _get_scene_frame_rate(self) -> float:
        """Get the scene frame rate."""
        # In Maya, get from playback options
        return cmds.playbackOptions(query=True, maxTime=True) or 24.0
    
    def set_face_regions_dict(self, active_regions_dict: Dict[str, bool]):
        """Set active face regions."""
        self.active_regions_dict = active_regions_dict
    
    def set_use_region_filter(self, use_region_filter: bool):
        """Set whether to use region filtering."""
        self.use_region_filter = use_region_filter
    
    def set_rotation_units(self, unit: str):
        """Set rotation units (DEG or RAD)."""
        self.source_rotation_units = unit
    
    def set_sk_action(self, action: str):
        """Set the shape key action."""
        self.sk_action = action
    
    def set_scene_frame_rate(self, fps: float):
        """Set the scene frame rate."""
        self.fps = fps
    
    def set_head_action(self, action: str):
        """Set the head action."""
        self.head_action = action
    
    def set_source_shape_reference(self, source_shape_list: List[str]):
        """Set the source shape reference list."""
        self.source_shape_reference = source_shape_list
    
    def set_shape_targets(self, objects: List[str] = None, retarget_shapes: List[Dict] = None):
        """Set shape targets for animation."""
        if not objects or not retarget_shapes:
            self.animate_shapes = False
            return
        
        self.objects = objects
        self.retarget_shapes = retarget_shapes
        self.target_shapes_dict = {}
        
        # Store references to the shape keys themselves
        for shape_item in retarget_shapes:
            shape_name = shape_item.get('name', '')
            self.target_shapes_dict[shape_name] = []
            
            if self.use_region_filter:
                region = shape_item.get('region', 'other').lower()
                if not self.active_regions_dict.get(region, True):
                    continue
            
            target_shapes = shape_item.get('target_shapes', [])
            
            if self.flip_animation:
                if 'Left' in shape_name:
                    mirror_name = shape_name.replace('Left', 'Right')
                    for item in retarget_shapes:
                        if item.get('name') == mirror_name:
                            target_shapes = item.get('target_shapes', [])
                            break
                elif 'Right' in shape_name:
                    mirror_name = shape_name.replace('Right', 'Left')
                    for item in retarget_shapes:
                        if item.get('name') == mirror_name:
                            target_shapes = item.get('target_shapes', [])
                            break
            
            for obj in objects:
                if not cmds.objExists(obj):
                    continue
                
                if not self._has_shape_keys(obj):
                    continue
                
                blend_node = self._get_blend_shape_node(obj)
                if blend_node:
                    for ts in target_shapes:
                        if isinstance(ts, dict):
                            ts_name = ts.get('name', '')
                        else:
                            ts_name = ts
                        
                        if cmds.attributeQuery(ts_name, node=blend_node, exists=True):
                            self.target_shapes_dict[shape_name].append(ts_name)
    
    def _has_shape_keys(self, obj: str) -> bool:
        """Check if an object has shape keys."""
        if not cmds.objExists(obj):
            return False
        
        history = cmds.listHistory(obj, pruneDagObjects=True, interestLevel=2) or []
        for node in history:
            if cmds.nodeType(node) == 'blendShape':
                return True
        
        return False
    
    def _get_blend_shape_node(self, obj: str) -> Optional[str]:
        """Get the blend shape node on an object."""
        if not cmds.objExists(obj):
            return None
        
        history = cmds.listHistory(obj, pruneDagObjects=True, interestLevel=2) or []
        for node in history:
            if cmds.nodeType(node) == 'blendShape':
                return node
        
        return None
    
    def normalizeAngle(self, angle: float) -> float:
        """Normalize angle to [-pi, pi]."""
        while angle > np.pi:
            angle -= 2.0 * np.pi
        while angle < -np.pi:
            angle += 2.0 * np.pi
        return angle
    
    def set_head_targets(
        self,
        head_obj: str,
        head_bone_name: str = "",
        head_loc_mult: float = 1.0
    ) -> None:
        """Set the head target objects."""
        self.head_obj = head_obj
        self.head_bone = None
        self.initial_head_rotation = None
        head_rot_mode = 'EULER'
        
        if head_obj and cmds.objExists(head_obj):
            # Get head rotation mode
            if cmds.attributeQuery("rotateOrder", node=head_obj, exists=True):
                head_rot_mode = 'EULER'
            
            if cmds.nodeType(head_obj) == 'joint':
                if head_bone_name:
                    self.head_bone = head_bone_name
                    # Get initial head rotation
                    if cmds.attributeQuery("rotate", node=head_bone_name, exists=True):
                        rot = cmds.getAttr(f"{head_bone_name}.rotate")[0]
                        self.initial_head_rotation = self._euler_to_quaternion(rot)
                    head_rot_mode = 'EULER'
            else:
                # Object mode
                if cmds.attributeQuery("rotateOrder", node=head_obj, exists=True):
                    head_rot_mode = 'EULER'
        else:
            self.animate_head_location = False
            self.animate_head_rotation = False
            return
        
        self.head_rotation_data_path = "rotation_" + head_rot_mode.lower()
        self.head_location_multiplier = head_loc_mult * FACECAP_SCALE_TO_BLENDER
        self.head_rotation_mode = head_rot_mode
    
    def _euler_to_quaternion(self, euler: List[float]) -> om2.MQuaternion:
        """Convert Euler angles to quaternion."""
        return om2.MQuaternion(euler[0], euler[1], euler[2])
    
    def flip_euler_rotation(self, e: List[float]) -> List[float]:
        """Flip Euler rotation."""
        return [-e[0], -e[1], -e[2]]
    
    def deg_to_rad(self, e: List[float]) -> List[float]:
        """Convert degrees to radians."""
        return [math.radians(v) for v in e]
    
    def _rotation_to_blender(self, value: List[float]) -> Any:
        """Bring the rotation into the correct format and orientation."""
        if len(value) < 3:
            return None
        
        # To Blender world coordinates (swap y and z and invert y)
        rot = [value[0], -value[1], -value[2]]
        
        # In Maya, we'd set rotation directly
        if self.source_rotation_units == 'DEG':
            rot = self.deg_to_rad(rot)
        
        if self.flip_animation:
            rot = self.flip_euler_rotation(rot)
        
        return rot
    
    def _location_to_blender(self, value: List[float]) -> List[float]:
        """Convert location to Blender coordinates."""
        if not self.head_bone:
            loc = [value[0], -value[1], -value[2]]
        else:
            loc = value[:]
        
        if self.flip_animation:
            loc[0] *= -1
        
        loc = [v * self.head_location_multiplier for v in loc]
        return loc
    
    def _get_initial_location_offset(self, value: List[float]):
        """Calculate the location offset from the first incoming location value."""
        offset = [0, 0, 0]
        if self.head_obj and cmds.objExists(self.head_obj):
            pos = cmds.xform(self.head_obj, query=True, worldSpace=True, translation=True)
            if pos:
                loc = self._location_to_blender(value)
                offset = [pos[0] - loc[0], pos[1] - loc[1], pos[2] - loc[2]]
        
        self.initial_location_offset = offset
    
    def _anim_values_to_keyframes(self, curve: str, frames: List[float], anim_values: List[float]) -> None:
        """Convert animation values to keyframes."""
        if not curve or not frames or not anim_values:
            return
        
        for frame, value in zip(frames, anim_values):
            cmds.setKeyframe(curve, t=frame, v=value)
    
    def parse_animation_data(self, data: Any, frame_start: int = 0, record_frame_rate: float = 1000.0):
        """Parse and populate the animation data into animation lists."""
        pass
    
    def clear_animation_targets(self):
        """Clear animation targets."""
        self.animate_shapes = False
        self.objects = []
        self.target_shapes_dict = {}
        self.head_obj = None
        self.head_bone = None
        self.head_action = None
    
    def clear_animation_data(self):
        """Clear animation data."""
        self.animation_timestamps = []
        self.sk_animation_lists = []
        self.head_rot_animation_lists = []
        self.head_loc_animation_lists = []
    
    def recording_to_keyframes(self) -> bool:
        """Convert recorded data to keyframes."""
        keyframes_added = False
        
        # Shape Key animation
        if self.animate_shapes and self.sk_animation_lists:
            # In Maya, we'd create animation curves on the blend shape node
            for i, name in enumerate(self.source_shape_reference):
                shape_keys = self.target_shapes_dict.get(name, [])
                if not shape_keys:
                    continue
                
                try:
                    anim_values = [row[i] for row in self.sk_animation_lists]
                except IndexError:
                    continue
                
                # Get amplify value
                amplify = 1.0
                if self.retarget_shapes:
                    for item in self.retarget_shapes:
                        if item.get('name') == name:
                            amplify = item.get('amplify', 1.0)
                            break
                
                anim_values = [v * amplify for v in anim_values]
                
                for sk_name in shape_keys:
                    # Find the blend shape node
                    for obj in self.objects:
                        if not cmds.objExists(obj):
                            continue
                        
                        blend_node = self._get_blend_shape_node(obj)
                        if blend_node and cmds.attributeQuery(sk_name, node=blend_node, exists=True):
                            # Set keyframes
                            for frame, value in zip(self.animation_timestamps, anim_values):
                                cmds.setKeyframe(blend_node, attribute=sk_name, t=frame, v=value)
                            keyframes_added = True
        
        # Head Transform Animation
        if (self.animate_head_location or self.animate_head_rotation) and self.head_obj:
            target = self.head_bone if self.head_bone else self.head_obj
            
            # Head Rotation
            if self.animate_head_rotation and self.head_rot_animation_lists:
                for i in range(3):
                    anim_values = [row[i] for row in self.head_rot_animation_lists]
                    attr = f"rotate{['X', 'Y', 'Z'][i]}"
                    
                    for frame, value in zip(self.animation_timestamps, anim_values):
                        cmds.setKeyframe(target, attribute=attr, t=frame, v=value)
                    keyframes_added = True
            
            # Head Location
            if self.animate_head_location and self.head_loc_animation_lists:
                offset = self.initial_location_offset or [0, 0, 0]
                for i in range(3):
                    anim_values = [row[i] + offset[i] for row in self.head_loc_animation_lists]
                    attr = f"translate{['X', 'Y', 'Z'][i]}"
                    
                    for frame, value in zip(self.animation_timestamps, anim_values):
                        cmds.setKeyframe(target, attribute=attr, t=frame, v=value)
                    keyframes_added = True
        
        return keyframes_added


# ============================================================
# Mocap Importer Base Class
# ============================================================

class MocapImporterBase:
    """Base class for importing raw mocap data from text or csv files."""
    
    def __init__(self):
        self.new_action_name = ""
        self.new_action_exists = False
        self.overwrite_method = 'REPLACE'
        self.bake_to_control_rig = False
        self.frame_start = 0
        self.use_region_filter = False
        self.set_scene_frame_range = True
        self.audio_filename = ""
        self.load_audio_file = False
        self.remove_audio_tracks_with_same_name = True
        self.animate_head_rotation = True
        self.animate_head_location = False
        self.animate_shapes = True
        self.flip_animation = False
        
        self.can_load_audio = False
        self.engine_settings_prop_name = "faceit_face_cap_mocap_settings"
        self.target_shapes_prop_name = "faceit_arkit_retarget_shapes"
        self.engine_settings = None
        self.record_frame_rate = 1000
        self.filename = ""
        self.can_bake_control_rig = True
        self.can_import_head_location = True
        self.can_import_head_rotation = True
    
    def _get_engine_specific_settings(self, context: Any):
        """Get engine-specific settings."""
        # In Maya, we'd get from scene data
        pass
    
    def _get_mocap_importer(self) -> MocapBase:
        """Get the mocap importer instance."""
        return MocapBase()
    
    def _get_engine_target_shapes(self, scene: Any):
        """Get engine target shapes."""
        # In Maya, we'd get from scene data
        return []
    
    def _get_engine_target_objects(self, scene: Any):
        """Get engine target objects."""
        # In Maya, we'd get from scene data
        return []
    
    def _get_raw_animation_data(self) -> Any:
        """Return the raw animation data."""
        return None
    
    def _check_file_path(self, filename: str) -> bool:
        """Check if a file path is valid."""
        if not filename:
            return False
        import os
        return os.path.exists(filename) and os.path.isfile(filename)
    
    def _get_clean_filename(self, filename: str) -> str:
        """Get clean filename without path and extension."""
        if not filename:
            return ""
        import os
        return os.path.splitext(os.path.basename(filename))[0]
    
    def _get_action(self, action_name: str, replace: bool = False) -> Optional[str]:
        """Get an action by name, create if it doesn't exist."""
        if cmds.objExists(action_name):
            if replace:
                cmds.delete(action_name)
            else:
                return action_name
        
        # Create new action (animCurve)
        action = cmds.createNode("animCurveUA", name=action_name)
        return action
    
    def _load_new_audio_file(self, scene: Any, start_frame_mocap: float, audio_file: str):
        """Load audio file into the sequencer."""
        # In Maya, we'd use the audio system
        pass
    
    def _get_audio_file(self) -> Optional[str]:
        """Get the audio file path."""
        if self.load_audio_file:
            return self.engine_settings.get('audio_filename', '') if self.engine_settings else None
        return None
    
    def execute(self, context: Any) -> str:
        """Execute the operator."""
        # This would be implemented by subclasses
        return {'FINISHED'}