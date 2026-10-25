# mocap_scene_properties.py
# Maya Faceit Plugin - Mocap Scene Properties
# Converted from Blender to Maya Python 3.11

"""
Mocap scene properties for Faceit Maya plugin.
Defines properties for motion capture functionality.
"""

import maya.cmds as cmds # type: ignore
from typing import Optional, Dict, Any
import json


# ============================================================
# Mocap Engine Properties Class
# ============================================================

class Mocap_Engine_Properties:
    """Mocap engine properties."""
    
    def __init__(self):
        self.filename = ""
        self.audio_filename = ""
        self.master_expanded = False
        self.file_import_expanded = False
        self.live_mode_expanded = False
        self.mocap_engine = ""
        self.indices_order = ""
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'filename': self.filename,
            'audio_filename': self.audio_filename,
            'master_expanded': self.master_expanded,
            'file_import_expanded': self.file_import_expanded,
            'live_mode_expanded': self.live_mode_expanded,
            'mocap_engine': self.mocap_engine,
            'indices_order': self.indices_order
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Mocap_Engine_Properties':
        """Create from dictionary."""
        props = cls()
        props.filename = data.get('filename', "")
        props.audio_filename = data.get('audio_filename', "")
        props.master_expanded = data.get('master_expanded', False)
        props.file_import_expanded = data.get('file_import_expanded', False)
        props.live_mode_expanded = data.get('live_mode_expanded', False)
        props.mocap_engine = data.get('mocap_engine', "")
        props.indices_order = data.get('indices_order', "")
        return props


# ============================================================
# Helper Functions
# ============================================================

def shapes_action_poll(action: str) -> bool:
    """Check if action is suitable for shape key animation."""
    if not cmds.objExists(action):
        return False
    curves = cmds.listAnimCurves(action) or []
    for curve in curves:
        attr = cmds.getAttr(f"{curve}.attributeName") or ""
        if 'key_block' in attr or 'weight' in attr:
            return True
    return True


def rig_action_poll(action: str) -> bool:
    """Check if action is suitable for rig animation."""
    if not cmds.objExists(action):
        return False
    curves = cmds.listAnimCurves(action) or []
    for curve in curves:
        attr = cmds.getAttr(f"{curve}.attributeName") or ""
        if 'pose.bones' in attr or 'joint' in attr:
            return True
    return False


def head_action_poll(action: str, head_obj: str = None) -> bool:
    """Check if action is suitable for head animation."""
    if not cmds.objExists(action):
        return False
    
    if action in ["faceit_shape_action", "overwrite_shape_action"]:
        return False
    
    if head_obj and cmds.objExists(head_obj):
        if cmds.nodeType(head_obj) == 'joint':
            return rig_action_poll(action)
    
    return True


# ============================================================
# Property Registration
# ============================================================

def register() -> None:
    """
    Register Faceit mocap scene properties.
    """
    # Check if the core data node exists
    if not cmds.objExists("faceit_core_data"):
        cmds.createNode("transform", name="faceit_core_data")
    
    # Mocap general
    if not cmds.attributeQuery("mocap_action", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="mocap_action", dt="string")
    
    if not cmds.attributeQuery("bake_sk_to_crig_action", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="bake_sk_to_crig_action", dt="string")
    
    if not cmds.attributeQuery("bake_crig_to_sk_action", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="bake_crig_to_sk_action", dt="string")
    
    if not cmds.attributeQuery("head_target_object", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="head_target_object", dt="string")
    
    if not cmds.attributeQuery("head_sub_target", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="head_sub_target", dt="string")
    
    if not cmds.attributeQuery("use_head_location_offset", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="use_head_location_offset", attributeType="bool", defaultValue=True)
    
    if not cmds.attributeQuery("head_action", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="head_action", dt="string")
    
    # Face Cap
    if not cmds.attributeQuery("face_cap_mocap_settings", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="face_cap_mocap_settings", dt="string")
    
    if not cmds.attributeQuery("record_face_cap", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="record_face_cap", attributeType="bool", defaultValue=False)
    
    # Epic / Live Link Face
    if not cmds.attributeQuery("epic_mocap_settings", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="epic_mocap_settings", dt="string")
    
    # Audio2Face
    if not cmds.attributeQuery("a2f_mocap_settings", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="a2f_mocap_settings", dt="string")
    
    # OSC
    if not cmds.attributeQuery("osc_address", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="osc_address", dt="string")
    
    if not cmds.attributeQuery("osc_port", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="osc_port", attributeType="long", defaultValue=9001)
    
    if not cmds.attributeQuery("osc_receiver_enabled", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="osc_receiver_enabled", attributeType="bool", defaultValue=False)
    
    if not cmds.attributeQuery("osc_animate_shapes", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="osc_animate_shapes", attributeType="bool", defaultValue=True)
    
    if not cmds.attributeQuery("osc_animate_head_rotation", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="osc_animate_head_rotation", attributeType="bool", defaultValue=True)
    
    if not cmds.attributeQuery("osc_animate_head_location", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="osc_animate_head_location", attributeType="bool", defaultValue=False)
    
    if not cmds.attributeQuery("osc_head_location_multiplier", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="osc_head_location_multiplier", attributeType="float", defaultValue=1.0)
    
    if not cmds.attributeQuery("osc_rotation_units", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="osc_rotation_units", attributeType="long", defaultValue=0)  # 0=DEG, 1=RAD
    
    if not cmds.attributeQuery("osc_face_regions", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="osc_face_regions", dt="string")
    
    if not cmds.attributeQuery("osc_use_region_filter", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="osc_use_region_filter", attributeType="bool", defaultValue=False)
    
    if not cmds.attributeQuery("osc_flip_animation", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="osc_flip_animation", attributeType="bool", defaultValue=False)
    
    if not cmds.attributeQuery("auto_disconnect_ctrl_rig", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="auto_disconnect_ctrl_rig", attributeType="bool", defaultValue=True)


def unregister() -> None:
    """
    Unregister Faceit mocap scene properties.
    """
    if cmds.objExists("faceit_core_data"):
        attrs = [
            "mocap_action",
            "bake_sk_to_crig_action",
            "bake_crig_to_sk_action",
            "head_target_object",
            "head_sub_target",
            "use_head_location_offset",
            "head_action",
            "face_cap_mocap_settings",
            "record_face_cap",
            "epic_mocap_settings",
            "a2f_mocap_settings",
            "osc_address",
            "osc_port",
            "osc_receiver_enabled",
            "osc_animate_shapes",
            "osc_animate_head_rotation",
            "osc_animate_head_location",
            "osc_head_location_multiplier",
            "osc_rotation_units",
            "osc_face_regions",
            "osc_use_region_filter",
            "osc_flip_animation",
            "auto_disconnect_ctrl_rig"
        ]
        for attr in attrs:
            if cmds.attributeQuery(attr, node="faceit_core_data", exists=True):
                cmds.deleteAttr("faceit_core_data", attribute=attr)


# ============================================================
# Mocap Settings Storage
# ============================================================

def get_mocap_engine_settings(engine: str) -> Mocap_Engine_Properties:
    """Get mocap engine settings."""
    attr_name = f"{engine.lower()}_mocap_settings"
    if cmds.objExists("faceit_core_data"):
        if cmds.attributeQuery(attr_name, node="faceit_core_data", exists=True):
            data_str = cmds.getAttr(f"faceit_core_data.{attr_name}") or "{}"
            try:
                data = json.loads(data_str)
                return Mocap_Engine_Properties.from_dict(data)
            except:
                pass
    return Mocap_Engine_Properties()


def set_mocap_engine_settings(engine: str, settings: Mocap_Engine_Properties) -> None:
    """Set mocap engine settings."""
    attr_name = f"{engine.lower()}_mocap_settings"
    if cmds.objExists("faceit_core_data"):
        if cmds.attributeQuery(attr_name, node="faceit_core_data", exists=True):
            cmds.setAttr(f"faceit_core_data.{attr_name}", json.dumps(settings.to_dict()), type="string")