# mocap_importers.py
# Maya Faceit Plugin - Mocap Importers
# Converted from Blender to Maya Python 3.11

"""
Mocap importers for Faceit Maya plugin.
Handles importing motion capture data from various sources.
"""

import maya.cmds as cmds # type: ignore
import csv
import json
from typing import List, Dict, Optional, Any

from .mocap_base import MocapBase
from ..core.faceit_data import get_face_cap_shape_data, get_epic_shape_data, get_a2f_shape_data


class FaceCapImporter(MocapBase):
    """FaceCap motion capture importer."""
    
    def _initialize_mocap_settings(self):
        """Initialize FaceCap-specific settings."""
        self.set_rotation_units('DEG')
        self.set_source_shape_reference(list(get_face_cap_shape_data().keys()))
    
    def parse_animation_data(self, data: str, frame_start: int = 0, record_frame_rate: float = 1000.0):
        """Parse FaceCap CSV data."""
        self.clear_animation_data()
        
        with open(data, 'r') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if not row:
                    continue
                if row[0] != 'k':
                    continue
                
                # Nano seconds since last frame
                current_frame = frame_start + (float(row[1]) / record_frame_rate) * self.fps
                self.animation_timestamps.append(current_frame)
                
                if self.animate_head_rotation:
                    self.head_rot_animation_lists.append([float(v) for v in row[5:8]])
                
                if self.animate_head_location:
                    self.head_loc_animation_lists.append([float(v) for v in row[2:5]])
                
                if self.animate_shapes:
                    self.sk_animation_lists.append([float(v) for v in row[12:]])
        
        # Initialize the first frame location offset
        if self.animate_head_location and self.head_loc_animation_lists:
            self._get_initial_location_offset(self.head_loc_animation_lists[0])


class A2FMocapImporter(MocapBase):
    """Audio2Face motion capture importer."""
    
    def _initialize_mocap_settings(self):
        """Initialize A2F-specific settings."""
        self.set_source_shape_reference(list(get_a2f_shape_data().keys()))
    
    def parse_animation_data(self, data: str, frame_start: int = 0, record_frame_rate: float = 60.0):
        """Parse A2F JSON data."""
        self.clear_animation_data()
        
        with open(data, 'r') as f:
            data = json.load(f)
            for i, shape_key_values in enumerate(data.get('weightMat', [])):
                if shape_key_values is None:
                    continue
                
                current_frame = frame_start + i * self.fps / record_frame_rate
                self.animation_timestamps.append(current_frame)
                
                if self.animate_shapes:
                    self.sk_animation_lists.append([float(v) for v in shape_key_values])


class EpicMocapImporter(MocapBase):
    """Epic Games Live Link Face motion capture importer."""
    
    def _initialize_mocap_settings(self):
        """Initialize Epic-specific settings."""
        self.set_rotation_units('RAD')
        self.set_source_shape_reference(list(get_epic_shape_data().keys()))
    
    def parse_animation_data(self, data: str, frame_start: int = 0, record_frame_rate: float = 60.0):
        """Parse Epic CSV data."""
        self.clear_animation_data()
        first_frame = None
        
        with open(data, 'r') as csvfile:
            reader = csv.reader(csvfile)
            for i, row in enumerate(reader):
                if not row:
                    continue
                if i == 0:
                    continue
                if float(row[1]) == 0:
                    continue
                
                if first_frame is None:
                    first_frame = self._convert_timecode_to_frames(
                        row[0], self.fps, recorded_framerate=record_frame_rate
                    ) - frame_start
                
                self.animation_timestamps.append(
                    self._convert_timecode_to_frames(
                        row[0], self.fps, recorded_framerate=record_frame_rate
                    ) - first_frame
                )
                
                if self.animate_shapes:
                    self.sk_animation_lists.append([float(v) for v in row[2:54]])
                
                if self.animate_head_rotation:
                    head_rot = [
                        -float(row[55]),
                        -float(row[54]),
                        -float(row[56])
                    ]
                    self.head_rot_animation_lists.append(head_rot)
    
    def _convert_timecode_to_frames(
        self,
        timecode: str,
        framerate: float,
        start: str = None,
        recorded_framerate: float = 60.0
    ) -> float:
        """Convert SMPTE timecode to frames."""
        def _seconds(value):
            if isinstance(value, str):
                parts = value.split(':')
                return (float(parts[0]) * 3600 + 
                       float(parts[1]) * 60 + 
                       float(parts[2]) + 
                       float(parts[3]) / recorded_framerate)
            elif isinstance(value, (int, float)):
                return value / framerate
            return 0
        
        def _frames(seconds):
            return seconds * framerate
        
        return _frames(_seconds(timecode) - _seconds(start))


class OSCLiveAnimator(MocapBase):
    """Animate target values live from OSC data."""
    
    def _initialize_mocap_settings(self):
        """Initialize OSC-specific settings."""
        self.set_source_shape_reference(list(get_face_cap_shape_data().keys()))
    
    def init_new_recording(self):
        """Initialize new recording state."""
        self.initial_location_offset = None
        self.head_bone = None
        self.head_action = None
        self.head_obj = None
    
    def process_data(self, data: tuple):
        """Process incoming OSC data."""
        _timestamp, address, params = data
        
        if self.animate_shapes and address == '/W':
            value = params[1]
            name = self.source_shape_reference[params[0]]
            self._set_shape_key_values(name, value)
        elif self.animate_head_rotation and address == '/HR':
            self._set_head_rotation(params)
        elif self.animate_head_location and address == '/HT':
            if not self.initial_location_offset:
                self._get_initial_location_offset(params)
            else:
                self._set_head_location(params)
    
    def _set_shape_key_values(self, name: str, value: float):
        """Set shape key values on all registered objects."""
        target_shapes = self.target_shapes_dict.get(name, [])
        amplify = 1.0
        
        for item in self.retarget_shapes:
            if item.get('name') == name:
                amplify = item.get('amplify', 1.0)
                break
        
        val = value * amplify
        
        for sk_name in target_shapes:
            for obj in self.objects:
                if not cmds.objExists(obj):
                    continue
                
                blend_node = self._get_blend_shape_node(obj)
                if blend_node and cmds.attributeQuery(sk_name, node=blend_node, exists=True):
                    cmds.setAttr(f"{blend_node}.{sk_name}", val)
    
    def _set_head_rotation(self, value: List[float]):
        """Set head rotation."""
        if not self.head_obj:
            return
        
        new_rot = self._rotation_to_blender(value)
        if new_rot is None:
            return
        
        target = self.head_bone if self.head_bone else self.head_obj
        
        if self.head_rotation_mode == 'EULER':
            attrs = ['rotateX', 'rotateY', 'rotateZ']
            for i, attr in enumerate(attrs):
                if i < len(new_rot):
                    cmds.setAttr(f"{target}.{attr}", new_rot[i])
    
    def _set_head_location(self, value: List[float]):
        """Set head location."""
        if not self.head_obj:
            return
        
        new_loc = self._location_to_blender(value)
        offset = self.initial_location_offset or [0, 0, 0]
        
        target = self.head_bone if self.head_bone else self.head_obj
        
        attrs = ['translateX', 'translateY', 'translateZ']
        for i, attr in enumerate(attrs):
            if i < len(new_loc):
                cmds.setAttr(f"{target}.{attr}", new_loc[i] + offset[i])
    
    def parse_animation_data(self, data: List[tuple], frame_start: int = 0, record_frame_rate: float = 1000.0):
        """Parse recorded OSC messages into animation data."""
        if not data:
            return
        
        self.clear_animation_data()
        shape_key_values = []
        timestamp = None
        first_timestamp = None
        shape_idx = 0
        last_shape_idx = 0
        missing_frames = []
        
        for frame_data in data:
            _time, _address, _value = frame_data
            
            if first_timestamp is None:
                first_timestamp = _time
            
            if _address == "/W":
                shape_idx = _value[0]
                if shape_idx < last_shape_idx:
                    if len(shape_key_values) == len(self.source_shape_reference):
                        self.animation_timestamps.append(timestamp)
                        self.sk_animation_lists.append([v[1] for v in shape_key_values])
                    else:
                        missing_frames.append(len(self.animation_timestamps))
                    
                    timestamp = None
                    shape_key_values = []
                
                if timestamp is None:
                    timestamp = (_time - first_timestamp) * self.fps + frame_start
                
                shape_key_values.append(_value)
            
            last_shape_idx = shape_idx
        
        # Process head data
        hr = [x[2] for x in data if x[1] == "/HR"]
        ht = [x[2] for x in data if x[1] == "/HT"]
        
        self.head_rot_animation_lists = [x for i, x in enumerate(hr) if i not in missing_frames]
        self.head_loc_animation_lists = [x for i, x in enumerate(ht) if i not in missing_frames]