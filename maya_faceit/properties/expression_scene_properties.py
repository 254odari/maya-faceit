# expression_scene_properties.py
# Maya Faceit Plugin - Expression Scene Properties
# Converted from Blender to Maya Python 3.11

"""
Expression scene properties for Faceit Maya plugin.
Defines properties for expression management.
"""

import maya.cmds as cmds # type: ignore
from typing import List, Dict, Optional, Any
import json

from ..core import faceit_utils as futils
from ..core import shape_key_utils


# ============================================================
# Expression Property Class
# ============================================================

class FaceitExpressions:
    """Properties stored in each expression item."""
    
    def __init__(self):
        self.name = ""
        self.side = "N"
        self.frame = 0
        self.index = 0
        self.mirror_name = ""
        self.corr_shape_key = False
        self.procedural = "NONE"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'side': self.side,
            'frame': self.frame,
            'index': self.index,
            'mirror_name': self.mirror_name,
            'corr_shape_key': self.corr_shape_key,
            'procedural': self.procedural
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'FaceitExpressions':
        """Create from dictionary."""
        expr = cls()
        expr.name = data.get('name', "")
        expr.side = data.get('side', "N")
        expr.frame = data.get('frame', 0)
        expr.index = data.get('index', 0)
        expr.mirror_name = data.get('mirror_name', "")
        expr.corr_shape_key = data.get('corr_shape_key', False)
        expr.procedural = data.get('procedural', "NONE")
        return expr


# ============================================================
# Procedural Expression Items
# ============================================================

PROCEDURAL_EXPRESSION_ITEMS = [
    ('NONE', 'None', 'Not a procedural expression'),
    ('EYEBLINKS', 'EyeBlinks', 'Eye blink expressions (can affect L R or N)'),
    ('MOUTHCLOSE', 'MouthClose', 'Jaw open, mouth closed')
]


# ============================================================
# Property Registration
# ============================================================

def register() -> None:
    """
    Register Faceit expression scene properties.
    """
    # Check if the core data node exists
    if not cmds.objExists("faceit_core_data"):
        cmds.createNode("transform", name="faceit_core_data")
    
    # Add properties
    if not cmds.attributeQuery("expression_list_index", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="expression_list_index", attributeType="long", defaultValue=0)
    
    if not cmds.attributeQuery("expression_list", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="expression_list", dt="string")
    
    if not cmds.attributeQuery("use_corrective_shapes", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="use_corrective_shapes", attributeType="bool", defaultValue=True)
    
    if not cmds.attributeQuery("try_mirror_corrective_shapes", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="try_mirror_corrective_shapes", attributeType="bool", defaultValue=True)
    
    if not cmds.attributeQuery("corrective_sk_mirror_method", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="corrective_sk_mirror_method", attributeType="long", defaultValue=0)
    
    if not cmds.attributeQuery("corrective_sk_mirror_affect_only_selected", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="corrective_sk_mirror_affect_only_selected", attributeType="bool", defaultValue=False)
    
    if not cmds.attributeQuery("corrective_shape_keys_edit_mode", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="corrective_shape_keys_edit_mode", attributeType="long", defaultValue=0)
    
    if not cmds.attributeQuery("use_auto_mirror_x", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="use_auto_mirror_x", attributeType="bool", defaultValue=True)


def unregister() -> None:
    """
    Unregister Faceit expression scene properties.
    """
    if cmds.objExists("faceit_core_data"):
        attrs = [
            "expression_list_index",
            "expression_list",
            "use_corrective_shapes",
            "try_mirror_corrective_shapes",
            "corrective_sk_mirror_method",
            "corrective_sk_mirror_affect_only_selected",
            "corrective_shape_keys_edit_mode",
            "use_auto_mirror_x"
        ]
        for attr in attrs:
            if cmds.attributeQuery(attr, node="faceit_core_data", exists=True):
                cmds.deleteAttr("faceit_core_data", attribute=attr)


# ============================================================
# Expression List Storage
# ============================================================

def get_expression_list() -> List[FaceitExpressions]:
    """Get expression list as list of FaceitExpressions objects."""
    if cmds.objExists("faceit_core_data"):
        if cmds.attributeQuery("expression_list", node="faceit_core_data", exists=True):
            data_str = cmds.getAttr("faceit_core_data.expression_list") or "[]"
            try:
                data = json.loads(data_str)
                return [FaceitExpressions.from_dict(item) for item in data]
            except:
                return []
    return []


def set_expression_list(expressions: List[FaceitExpressions]) -> None:
    """Set expression list from list of FaceitExpressions objects."""
    if cmds.objExists("faceit_core_data"):
        if cmds.attributeQuery("expression_list", node="faceit_core_data", exists=True):
            data = [expr.to_dict() for expr in expressions]
            cmds.setAttr("faceit_core_data.expression_list", json.dumps(data), type="string")


def get_expression_list_index() -> int:
    """Get the current expression list index."""
    if cmds.objExists("faceit_core_data"):
        if cmds.attributeQuery("expression_list_index", node="faceit_core_data", exists=True):
            return cmds.getAttr("faceit_core_data.expression_list_index")
    return 0


def set_expression_list_index(index: int) -> None:
    """Set the current expression list index."""
    if cmds.objExists("faceit_core_data"):
        if cmds.attributeQuery("expression_list_index", node="faceit_core_data", exists=True):
            cmds.setAttr("faceit_core_data.expression_list_index", index)