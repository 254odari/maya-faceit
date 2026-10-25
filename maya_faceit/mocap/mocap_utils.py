# mocap_utils.py
# Maya Faceit Plugin - Mocap Utilities
# Converted from Blender to Maya Python 3.11

"""
Mocap utilities for Faceit Maya plugin.
Provides utility functions for motion capture operations.
"""

import maya.cmds as cmds # type: ignore
import numpy as np
from datetime import datetime
from typing import List, Optional


def get_current_timestamp() -> str:
    """Return the current timestamp as a string."""
    timeObj = datetime.now()
    return timeObj.strftime("%H:%M:%S.%f")


def get_scene_frame_rate() -> float:
    """Return the current framerate."""
    # In Maya, get from playback options
    return cmds.playbackOptions(query=True, maxTime=True) or 24.0


def add_zero_keyframe(curves: List[str], frame: int) -> None:
    """Add a zero keyframe to the specified curves."""
    for curve in curves:
        if cmds.objExists(curve):
            cmds.setKeyframe(curve, t=frame, v=0.0)


def remove_frame_range(action: str, curves: List[str], frame_start: int, frame_end: int) -> None:
    """Remove all keyframes from curves between frame_start and frame_end."""
    if not cmds.objExists(action):
        return
    
    for curve in curves:
        if not cmds.objExists(curve):
            continue
        
        # Get keyframes
        keyframes = cmds.keyframe(curve, query=True, timeChange=True) or []
        
        for t in keyframes:
            if frame_start <= t <= frame_end:
                cmds.cutKey(curve, time=(t, t))


def get_action(action_name: str) -> Optional[str]:
    """Get an action by name, create it if it does not exist."""
    if cmds.objExists(action_name):
        return action_name
    
    # Create new action (animCurve)
    action = cmds.createNode("animCurveUA", name=action_name)
    return action