# fbx_retarget_scene_properties.py
# Maya Faceit Plugin - FBX Retarget Scene Properties
# Converted from Blender to Maya Python 3.11

"""
FBX retarget scene properties for Faceit Maya plugin.
Defines properties for FBX retargeting.
"""

import maya.cmds as cmds # type: ignore
from typing import List, Dict, Optional, Any
import json

from ..core import faceit_utils as futils


# ============================================================
# Helper Functions
# ============================================================

def poll_is_obj_type_mesh(obj: str) -> bool:
    """Check if an object is a mesh."""
    if not cmds.objExists(obj):
        return False
    shapes = cmds.listRelatives(obj, shapes=True, type='mesh')
    return bool(shapes)


def poll_is_action_shape_key(action: str) -> bool:
    """Check if an action contains shape key curves."""
    if not cmds.objExists(action):
        return False
    curves = cmds.listAnimCurves(action) or []
    for curve in curves:
        attr = cmds.getAttr(f"{curve}.attributeName") or ""
        if 'key_block' in attr or 'weight' in attr:
            return True
    return False


# ============================================================
# Property Registration
# ============================================================

def register() -> None:
    """
    Register Faceit FBX retarget scene properties.
    """
    # Check if the core data node exists
    if not cmds.objExists("faceit_core_data"):
        cmds.createNode("transform", name="faceit_core_data")
    
    if not cmds.attributeQuery("fbx_retarget_mapping", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="fbx_retarget_mapping", dt="string")


def unregister() -> None:
    """
    Unregister Faceit FBX retarget scene properties.
    """
    if cmds.objExists("faceit_core_data"):
        if cmds.attributeQuery("fbx_retarget_mapping", node="faceit_core_data", exists=True):
            cmds.deleteAttr("faceit_core_data", attribute="fbx_retarget_mapping")


# ============================================================
# FBX Retarget Mapping Storage
# ============================================================

class FBXRetargetShapes:
    """FBX retarget shapes class."""
    
    def __init__(self):
        self.name = ""
        self.display_name = ""
        self.target_shapes = []
        self.amplify = 1.0
        self.use_animation = True
        self.region = "other"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'display_name': self.display_name,
            'target_shapes': self.target_shapes,
            'amplify': self.amplify,
            'use_animation': self.use_animation,
            'region': self.region
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'FBXRetargetShapes':
        """Create from dictionary."""
        item = cls()
        item.name = data.get('name', "")
        item.display_name = data.get('display_name', item.name)
        item.target_shapes = data.get('target_shapes', [])
        item.amplify = data.get('amplify', 1.0)
        item.use_animation = data.get('use_animation', True)
        item.region = data.get('region', "other")
        return item


def get_fbx_retarget_mapping() -> List[FBXRetargetShapes]:
    """Get FBX retarget mapping as list."""
    if cmds.objExists("faceit_core_data"):
        if cmds.attributeQuery("fbx_retarget_mapping", node="faceit_core_data", exists=True):
            data_str = cmds.getAttr("faceit_core_data.fbx_retarget_mapping") or "[]"
            try:
                data = json.loads(data_str)
                return [FBXRetargetShapes.from_dict(item) for item in data]
            except:
                return []
    return []


def set_fbx_retarget_mapping(mapping: List[FBXRetargetShapes]) -> None:
    """Set FBX retarget mapping from list."""
    if cmds.objExists("faceit_core_data"):
        if cmds.attributeQuery("fbx_retarget_mapping", node="faceit_core_data", exists=True):
            data = [item.to_dict() for item in mapping]
            cmds.setAttr("faceit_core_data.fbx_retarget_mapping", json.dumps(data), type="string")