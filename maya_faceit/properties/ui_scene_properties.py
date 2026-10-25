# ui_scene_properties.py
# Maya Faceit Plugin - UI Scene Properties
# Converted from Blender to Maya Python 3.11

"""
UI scene properties for Faceit Maya plugin.
Defines properties for UI workspace management.
"""

import maya.cmds as cmds # type: ignore
from typing import Dict, Any
import json


# ============================================================
# Workspace Tab Dictionary
# ============================================================

WORKSPACE_TAB_DICT = {
    'ALL': [
        ('SETUP', 'Setup', 'Setup Tab'),
        ('CREATE', 'Rig', 'Create Tab'),
        ('EXPRESSIONS', 'Expressions', 'Expressions Tab'),
        ('BAKE', 'Bake', 'Bake Tab'),
        ('SHAPES', 'Shapes', 'Target Shape Keys Settings'),
        ('CONTROL', 'Control', 'Control Rig'),
        ('MOCAP', 'Mocap', 'Motion Capture'),
    ],
    'RIG': [
        ('SETUP', 'Setup', 'Setup Tab'),
        ('CREATE', 'Rig', 'Create Tab'),
        ('EXPRESSIONS', 'Expressions', 'Expressions Tab'),
        ('BAKE', 'Bake', 'Bake Tab'),
    ],
    'MOCAP': [
        ('SETUP', 'Setup', 'Setup Tab'),
        ('SHAPES', 'Shapes', 'Target Shape Keys Settings'),
        ('CONTROL', 'Control', 'Control Rig'),
        ('MOCAP', 'Mocap', 'Motion Capture'),
    ]
}


# ============================================================
# Pin Panels Class
# ============================================================

class PinPanels:
    """Pin panels class."""
    
    def __init__(self):
        # Setup
        self.FACEIT_PT_SetupRegister = False
        self.FACEIT_PT_SetupVertexGroups = False
        self.FACEIT_PT_BodyRigSetup = False
        # Rigging
        self.FACEIT_PT_Rigging = False
        self.FACEIT_PT_Landmarks = False
        # Expressions
        self.FACEIT_PT_Expressions = False
        self.FACEIT_PT_ExpressionOptions = False
        # Bake
        self.FACEIT_PT_BakeExpressions = False
        self.FACEIT_PT_ShapeKeyUtils = False
        self.FACEIT_PT_Finalize = False
        self.FACEIT_PT_RigUtils = False
        self.FACEIT_PT_Other = False
        # Shapes
        self.FACEIT_PT_TargetShapeLists = False
        self.FACEIT_PT_RetargetShapesSetup = False
        # Control Rig
        self.FACEIT_PT_ControlRig = False
        self.FACEIT_PT_ControlRigSettings = False
        self.FACEIT_PT_ControlRigAnimation = False
        self.FACEIT_PT_ControlRigUtils = False
        self.FACEIT_PT_ControlRigTargetShapes = False
        self.FACEIT_PT_ControlRigTargetObjects = False
        # Mocap
        self.FACEIT_PT_MocapUtils = False
        self.FACEIT_PT_MocapImporters = False
        self.FACEIT_PT_MocapOSC = False
    
    def get_pin(self, panel_idname: str) -> bool:
        """Get pin state for a panel."""
        return getattr(self, panel_idname, False)
    
    def set_pin(self, panel_idname: str, value: bool) -> None:
        """Set pin state for a panel."""
        if hasattr(self, panel_idname):
            setattr(self, panel_idname, value)


# ============================================================
# Faceit Workspace Class
# ============================================================

class FaceitWorkspace:
    """Faceit workspace class."""
    
    def __init__(self):
        self.name = ""
        self.workspace = "ALL"
        self.active_tab = "SETUP"
        self.all_tab = "SETUP"
        self.rig_tab = "SETUP"
        self.mocap_tab = "SETUP"
        self.expand_ui = False


# ============================================================
# Property Registration
# ============================================================

def register() -> None:
    """
    Register Faceit UI scene properties.
    """
    # Check if the core data node exists
    if not cmds.objExists("faceit_core_data"):
        cmds.createNode("transform", name="faceit_core_data")
    
    # Workspace
    if not cmds.attributeQuery("workspace_data", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="workspace_data", dt="string")
    
    if not cmds.attributeQuery("expression_init_expand_ui", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="expression_init_expand_ui", attributeType="bool", defaultValue=True)
    
    # Pin panels
    if not cmds.attributeQuery("pin_panels", node="faceit_core_data", exists=True):
        cmds.addAttr("faceit_core_data", ln="pin_panels", dt="string")


def unregister() -> None:
    """
    Unregister Faceit UI scene properties.
    """
    if cmds.objExists("faceit_core_data"):
        attrs = ["workspace_data", "expression_init_expand_ui", "pin_panels"]
        for attr in attrs:
            if cmds.attributeQuery(attr, node="faceit_core_data", exists=True):
                cmds.deleteAttr("faceit_core_data", attribute=attr)


# ============================================================
# Workspace Storage
# ============================================================

def get_workspace_data() -> Dict[str, Any]:
    """Get workspace data as dictionary."""
    if cmds.objExists("faceit_core_data"):
        if cmds.attributeQuery("workspace_data", node="faceit_core_data", exists=True):
            data_str = cmds.getAttr("faceit_core_data.workspace_data") or "{}"
            try:
                return json.loads(data_str)
            except:
                return {}
    return {}


def set_workspace_data(data: Dict[str, Any]) -> None:
    """Set workspace data from dictionary."""
    if cmds.objExists("faceit_core_data"):
        if cmds.attributeQuery("workspace_data", node="faceit_core_data", exists=True):
            cmds.setAttr("faceit_core_data.workspace_data", json.dumps(data), type="string")


def get_pin_panels() -> PinPanels:
    """Get pin panels state."""
    if cmds.objExists("faceit_core_data"):
        if cmds.attributeQuery("pin_panels", node="faceit_core_data", exists=True):
            data_str = cmds.getAttr("faceit_core_data.pin_panels") or "{}"
            try:
                data = json.loads(data_str)
                panels = PinPanels()
                for key, value in data.items():
                    if hasattr(panels, key):
                        setattr(panels, key, value)
                return panels
            except:
                pass
    return PinPanels()


def set_pin_panels(panels: PinPanels) -> None:
    """Set pin panels state."""
    if cmds.objExists("faceit_core_data"):
        if cmds.attributeQuery("pin_panels", node="faceit_core_data", exists=True):
            data = {}
            for attr in dir(panels):
                if not attr.startswith('_') and not callable(getattr(panels, attr)):
                    data[attr] = getattr(panels, attr)
            cmds.setAttr("faceit_core_data.pin_panels", json.dumps(data), type="string")