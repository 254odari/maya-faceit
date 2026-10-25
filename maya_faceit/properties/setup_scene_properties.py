# setup_scene_properties.py
# Maya Faceit Plugin - Setup Scene Properties
# Converted from Blender to Maya Python 3.11

"""
Setup scene properties for Faceit Maya plugin.
Defines properties for setup and vertex group management.
"""

import maya.cmds as cmds # type: ignore
from typing import List, Dict, Optional, Any
import json

from ..core import faceit_utils as futils


# ============================================================
# Faceit Objects Class
# ============================================================

class FaceitObjects:
    """Faceit objects class."""
    
    def __init__(self):
        self.name = ""
        self.obj_pointer = None
        self.part = ""
        self.warnings = ""
        self.modifiers = []
        self.active_mod_index = 0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'part': self.part,
            'warnings': self.warnings,
            'modifiers': self.modifiers,
            'active_mod_index': self.active_mod_index
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'FaceitObjects':
        """Create from dictionary."""
        item = cls()
        item.name = data.get('name', "")
        item.part = data.get('part', "")
        item.warnings = data.get('warnings', "")
        item.modifiers = data.get('modifiers', [])
        item.active_mod_index = data.get('active_mod_index', 0)
        return item


# ============================================================
# Faceit Vertex Groups Class
# ============================================================

class FaceitVertexGroups:
    """Faceit vertex groups class."""
    
    def __init__(self):
        self.name = ""
        self.is_drawn = False
        self.is_assigned = False
        self.is_masked = False
        self.mask_inverted = True
        self.assigned_to_objects = []
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'is_drawn': self.is_drawn,
            'is_assigned': self.is_assigned,
            'is_masked': self.is_masked,
            'mask_inverted': self.mask_inverted,
            'assigned_to_objects': self.assigned_to_objects
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'FaceitVertexGroups':
        """Create from dictionary."""
        item = cls()
        item.name = data.get('name', "")
        item.is_drawn = data.get('is_drawn', False)
        item.is_assigned = data.get('is_assigned', False)
        item.is_masked = data.get('is_masked', False)
        item.mask_inverted = data.get('mask_inverted', True)
        item.assigned_to_objects = data.get('assigned_to_objects', [])
        return item


# ============================================================
# Property Registration
# ============================================================

def register() -> None:
    """
    Register Faceit setup scene properties.
    """
    # Check if the core data node exists
    if not cmds.objExists("faceit_core_data"):
        cmds.createNode("transform", name="faceit_core_data")
    
    # Faceit objects
    if not cmds.attributeQuery("faceit_objects", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="faceit_objects", dt="string")
    
    if not cmds.attributeQuery("subscribed", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="subscribed", attributeType="bool", defaultValue=False)
    
    if not cmds.attributeQuery("face_index", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="face_index", attributeType="long", defaultValue=0)
    
    if not cmds.attributeQuery("show_warnings", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="show_warnings", attributeType="bool", defaultValue=False)
    
    # Vertex groups
    if not cmds.attributeQuery("vertex_groups", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="vertex_groups", dt="string")


def unregister() -> None:
    """
    Unregister Faceit setup scene properties.
    """
    if cmds.objExists("faceit_core_data"):
        attrs = [
            "faceit_objects",
            "subscribed",
            "face_index",
            "show_warnings",
            "vertex_groups"
        ]
        for attr in attrs:
            if cmds.attributeQuery(attr, node="faceit_core_data", exists=True):
                cmds.deleteAttr("faceit_core_data", attribute=attr)


# ============================================================
# Faceit Objects Storage
# ============================================================

def get_faceit_objects() -> List[FaceitObjects]:
    """Get Faceit objects as list."""
    if cmds.objExists("faceit_core_data"):
        if cmds.attributeQuery("faceit_objects", node="faceit_core_data", exists=True):
            data_str = cmds.getAttr("faceit_core_data.faceit_objects") or "[]"
            try:
                data = json.loads(data_str)
                return [FaceitObjects.from_dict(item) for item in data]
            except:
                return []
    return []


def set_faceit_objects(objects: List[FaceitObjects]) -> None:
    """Set Faceit objects from list."""
    if cmds.objExists("faceit_core_data"):
        if cmds.attributeQuery("faceit_objects", node="faceit_core_data", exists=True):
            data = [obj.to_dict() for obj in objects]
            cmds.setAttr("faceit_core_data.faceit_objects", json.dumps(data), type="string")


def get_vertex_groups() -> List[FaceitVertexGroups]:
    """Get Faceit vertex groups as list."""
    if cmds.objExists("faceit_core_data"):
        if cmds.attributeQuery("vertex_groups", node="faceit_core_data", exists=True):
            data_str = cmds.getAttr("faceit_core_data.vertex_groups") or "[]"
            try:
                data = json.loads(data_str)
                return [FaceitVertexGroups.from_dict(item) for item in data]
            except:
                return []
    return []


def set_vertex_groups(groups: List[FaceitVertexGroups]) -> None:
    """Set Faceit vertex groups from list."""
    if cmds.objExists("faceit_core_data"):
        if cmds.attributeQuery("vertex_groups", node="faceit_core_data", exists=True):
            data = [g.to_dict() for g in groups]
            cmds.setAttr("faceit_core_data.vertex_groups", json.dumps(data), type="string")