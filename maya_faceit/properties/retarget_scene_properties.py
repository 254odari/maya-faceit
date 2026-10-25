# retarget_scene_properties.py
# Maya Faceit Plugin - Retarget Scene Properties
# Converted from Blender to Maya Python 3.11

"""
Retarget scene properties for Faceit Maya plugin.
Defines properties for retargeting shapes.
"""

import maya.cmds as cmds # type: ignore
from typing import List, Dict, Optional, Any
import json


# ============================================================
# Retarget Shapes Class
# ============================================================

class RetargetShapes:
    """Retarget shapes class."""
    
    def __init__(self):
        self.name = ""
        self.display_name = ""
        self.target_shapes = []
        self.amplify = 1.0
        self.use_animation = True
        self.region = "other"
        self.slider_name = ""
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'display_name': self.display_name,
            'target_shapes': self.target_shapes,
            'amplify': self.amplify,
            'use_animation': self.use_animation,
            'region': self.region,
            'slider_name': self.slider_name
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'RetargetShapes':
        """Create from dictionary."""
        item = cls()
        item.name = data.get('name', "")
        item.display_name = data.get('display_name', item.name)
        item.target_shapes = data.get('target_shapes', [])
        item.amplify = data.get('amplify', 1.0)
        item.use_animation = data.get('use_animation', True)
        item.region = data.get('region', "other")
        item.slider_name = data.get('slider_name', "")
        return item


# ============================================================
# Property Registration
# ============================================================

def register() -> None:
    """
    Register Faceit retarget scene properties.
    """
    # Check if the core data node exists
    if not cmds.objExists("faceit_core_data"):
        cmds.createNode("transform", name="faceit_core_data")
    
    # ARKit retarget shapes
    if not cmds.attributeQuery("arkit_retarget_shapes", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="arkit_retarget_shapes", dt="string")
    
    if not cmds.attributeQuery("arkit_retarget_shapes_index", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="arkit_retarget_shapes_index", attributeType="long", defaultValue=0)
    
    # A2F retarget shapes
    if not cmds.attributeQuery("a2f_retarget_shapes", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="a2f_retarget_shapes", dt="string")
    
    if not cmds.attributeQuery("a2f_retarget_shapes_index", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="a2f_retarget_shapes_index", attributeType="long", defaultValue=0)
    
    # Face regions
    if not cmds.attributeQuery("face_regions", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="face_regions", dt="string")
    
    # Display retarget list
    if not cmds.attributeQuery("display_retarget_list", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="display_retarget_list", attributeType="long", defaultValue=0)  # 0=ARKIT, 1=A2F
    
    # Naming scheme
    if not cmds.attributeQuery("retargeting_naming_scheme", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="retargeting_naming_scheme", attributeType="long", defaultValue=0)  # 0=ARKIT, 1=FACECAP


def unregister() -> None:
    """
    Unregister Faceit retarget scene properties.
    """
    if cmds.objExists("faceit_core_data"):
        attrs = [
            "arkit_retarget_shapes",
            "arkit_retarget_shapes_index",
            "a2f_retarget_shapes",
            "a2f_retarget_shapes_index",
            "face_regions",
            "display_retarget_list",
            "retargeting_naming_scheme"
        ]
        for attr in attrs:
            if cmds.attributeQuery(attr, node="faceit_core_data", exists=True):
                cmds.deleteAttr("faceit_core_data", attribute=attr)


# ============================================================
# Retarget Shapes Storage
# ============================================================

def get_retarget_shapes(shape_type: str = "ARKIT") -> List[RetargetShapes]:
    """Get retarget shapes for a specific type."""
    attr_name = f"{shape_type.lower()}_retarget_shapes"
    if cmds.objExists("faceit_core_data"):
        if cmds.attributeQuery(attr_name, node="faceit_core_data", exists=True):
            data_str = cmds.getAttr(f"faceit_core_data.{attr_name}") or "[]"
            try:
                data = json.loads(data_str)
                return [RetargetShapes.from_dict(item) for item in data]
            except:
                return []
    return []


def set_retarget_shapes(shape_type: str, shapes: List[RetargetShapes]) -> None:
    """Set retarget shapes for a specific type."""
    attr_name = f"{shape_type.lower()}_retarget_shapes"
    if cmds.objExists("faceit_core_data"):
        if cmds.attributeQuery(attr_name, node="faceit_core_data", exists=True):
            data = [s.to_dict() for s in shapes]
            cmds.setAttr(f"faceit_core_data.{attr_name}", json.dumps(data), type="string")