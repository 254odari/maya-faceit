# __init__.py
# Maya Faceit Plugin - Animation Module
# Version: 1.0.0

"""
Faceit Animation Module for Maya
================================

This module provides animation operators and utilities for the Faceit facial rigging system.
It handles expression management, procedural animation, and animation utilities.

Main Components:
    - Expression management (add, remove, move, mirror)
    - Procedural animation (eye blinks, mouth close)
    - Animation tools (amplify, reset, copy)
    - Export/Import expressions
    - Action management
"""

__version__ = "1.0.0"
__author__ = "Faceit Team"

# ============================================================
# Module Imports
# ============================================================
from typing import List, Tuple, Optional, Set, Dict
# Import core modules
from . import animate_operators
from . import animate_utils

# Import key classes for easy access
from .animate_operators import (
    AddExpressionItem,
    ResetBoneConstraints,
    MirrorCopyExpression,
    EmptyExpressionsFromBlendShapes,
    MoveExpressionItem,
    AppendActionToFaceitRig,
    ForceZeroFrames,
    ExportExpressionsToJson,
    ClearFaceitExpressions,
    RemoveExpressionItem,
    PoseAmplify,
    ResetExpression,
    ProceduralEyeBlinks,
    ProceduralMouthClose,
    NewAction,
    PopulateAction,
    SetBodyBindPose,
)

from .animate_utils import (
    get_rotation_mode,
    get_data_path_from_rotation_mode,
    get_rotation_mode_from_data_path,
)

# ============================================================
# Module Constants
# ============================================================

# Expression categories
EXPRESSION_CATEGORIES = {
    'eyeBlink': 'Eyes',
    'eyeSquint': 'Eyes',
    'eyeLook': 'Eyes',
    'brow': 'Brows',
    'mouth': 'Mouth',
    'jaw': 'Jaw',
    'cheek': 'Cheeks',
    'tongue': 'Tongue',
}

# ARKit 52 expression names
ARKIT_EXPRESSIONS = [
    "eyeBlink_L", "eyeBlink_R", "eyeSquint_L", "eyeSquint_R",
    "eyeLookDown_L", "eyeLookDown_R", "eyeLookIn_L", "eyeLookIn_R",
    "eyeLookOut_L", "eyeLookOut_R", "eyeLookUp_L", "eyeLookUp_R",
    "browDown_L", "browDown_R", "browInnerUp", "browOuterUp_L",
    "browOuterUp_R", "mouthFunnel", "mouthPucker", "mouthRollUpper",
    "mouthRollLower", "mouthShrugUpper", "mouthShrugLower",
    "mouthClose", "mouthSmile_L", "mouthSmile_R", "mouthFrown_L",
    "mouthFrown_R", "mouthDimple_L", "mouthDimple_R", "mouthUpperUp_L",
    "mouthUpperUp_R", "mouthLowerDown_L", "mouthLowerDown_R",
    "mouthPress_L", "mouthPress_R", "mouthStretch_L", "mouthStretch_R",
    "mouthLeft", "mouthRight", "jawOpen", "mouthO", "cheekPuff_L",
    "cheekPuff_R", "cheekSquint_L", "cheekSquint_R", "tongueOut"
]

# ============================================================
# Maya Plugin Registration
# ============================================================

def initialize_plugin():
    """
    Initialize the animation module when Maya starts.
    Called by the main Faceit plugin.
    """
    print(f"Faceit Animation Module v{__version__} initialized")
    
    # Register any custom attributes
    _register_custom_attributes()
    
    # Create any necessary scene data nodes
    _ensure_scene_data_nodes()


def uninitialize_plugin():
    """
    Clean up when Maya shuts down.
    Called by the main Faceit plugin.
    """
    print("Faceit Animation Module uninitialized")


def _register_custom_attributes():
    """Register custom attributes for Faceit animation data."""
    # Check if the Faceit data node exists
    if not cmds.objExists("faceit_animation_data"):
        # Create a transform node to store data
        cmds.createNode("transform", name="faceit_animation_data")
        
        # Add attributes for expression data
        cmds.addAttr("faceit_animation_data", ln="version", dt="string")
        cmds.setAttr("faceit_animation_data.version", __version__, type="string")
        
        cmds.addAttr("faceit_animation_data", ln="expression_names", dt="string")
        cmds.addAttr("faceit_animation_data", ln="expression_frames", dt="string")
        cmds.addAttr("faceit_animation_data", ln="expression_sides", dt="string")
        cmds.addAttr("faceit_animation_data", ln="expression_procedural", dt="string")
        cmds.addAttr("faceit_animation_data", ln="expression_mirror_names", dt="string")
        
        # Current selection index
        cmds.addAttr("faceit_animation_data", ln="current_index", attributeType="long", min=0, defaultValue=0)


def _ensure_scene_data_nodes():
    """Ensure necessary scene data nodes exist."""
    # This will create the animation data node if it doesn't exist
    if not cmds.objExists("faceit_animation_data"):
        _register_custom_attributes()


# ============================================================
# Maya Command Registration
# ============================================================

# Command dictionary for Maya
FACEIT_ANIMATION_COMMANDS = {
    "faceit_add_expression": {
        "function": animate_operators.faceit_add_expression,
        "doc": "Add a new expression to the Faceit system."
    },
    "faceit_append_expressions": {
        "function": animate_operators.faceit_append_expressions,
        "doc": "Load expressions from a .face file."
    },
    "faceit_clear_expressions": {
        "function": lambda **kwargs: ClearFaceitExpressions(**kwargs).execute(),
        "doc": "Clear all Faceit expressions."
    },
    "faceit_remove_expression": {
        "function": lambda **kwargs: RemoveExpressionItem(**kwargs).execute(),
        "doc": "Remove a specific expression."
    },
    "faceit_move_expression": {
        "function": lambda **kwargs: MoveExpressionItem(**kwargs).execute(),
        "doc": "Move an expression in the list."
    },
    "faceit_mirror_expression": {
        "function": lambda **kwargs: MirrorCopyExpression(**kwargs).execute(),
        "doc": "Mirror copy an expression."
    },
    "faceit_amplify_pose": {
        "function": lambda **kwargs: PoseAmplify(**kwargs).execute(),
        "doc": "Amplify or scale a pose."
    },
    "faceit_reset_expression": {
        "function": lambda **kwargs: ResetExpression(**kwargs).execute(),
        "doc": "Reset expression to original state."
    },
    "faceit_force_zero_frames": {
        "function": lambda: ForceZeroFrames().execute(),
        "doc": "Add zero keyframes between expressions."
    },
    "faceit_procedural_blinks": {
        "function": lambda **kwargs: ProceduralEyeBlinks(**kwargs).execute(),
        "doc": "Create procedural eye blink animation."
    },
    "faceit_procedural_mouth": {
        "function": lambda **kwargs: ProceduralMouthClose(**kwargs).execute(),
        "doc": "Create procedural mouth close animation."
    },
    "faceit_export_expressions": {
        "function": lambda **kwargs: ExportExpressionsToJson(**kwargs).execute(),
        "doc": "Export expressions to .face JSON format."
    },
    "faceit_new_action": {
        "function": lambda **kwargs: NewAction(**kwargs).execute(),
        "doc": "Create a new animation action."
    },
    "faceit_populate_action": {
        "function": lambda **kwargs: PopulateAction(**kwargs).execute(),
        "doc": "Populate action to all Faceit objects."
    },
    "faceit_set_bind_pose": {
        "function": lambda **kwargs: SetBodyBindPose(**kwargs).execute(),
        "doc": "Set the current pose as bind pose."
    },
    "faceit_reset_constraints": {
        "function": lambda: ResetBoneConstraints().execute(),
        "doc": "Reset all bone constraints to defaults."
    },
}


def register_commands():
    """Register all Faceit animation commands with Maya."""
    # In Maya, commands are typically registered via the command module
    # This is a placeholder for command registration
    
    # Create a menu item for each command
    _create_animation_menu()


def _create_animation_menu():
    """Create the Faceit animation menu in Maya."""
    # Check if the Faceit menu already exists
    if cmds.menu("faceitAnimationMenu", exists=True):
        return
    
    # Create the menu
    cmds.menu("faceitAnimationMenu", label="Faceit Animation", parent="MayaWindow")
    
    # Add submenus
    # Expression menu
    cmds.menuItem(label="Add Expression", command="faceit_add_expression()")
    cmds.menuItem(label="Remove Expression", command="faceit_remove_expression()")
    cmds.menuItem(label="Mirror Expression", command="faceit_mirror_expression()")
    cmds.menuItem(divider=True)
    
    # Procedural menu
    cmds.menuItem(label="Procedural Eye Blinks", command="faceit_procedural_blinks()")
    cmds.menuItem(label="Procedural Mouth Close", command="faceit_procedural_mouth()")
    cmds.menuItem(divider=True)
    
    # Animation tools
    cmds.menuItem(label="Amplify Pose", command="faceit_amplify_pose()")
    cmds.menuItem(label="Reset Expression", command="faceit_reset_expression()")
    cmds.menuItem(label="Force Zero Frames", command="faceit_force_zero_frames()")
    cmds.menuItem(divider=True)
    
    # Action management
    cmds.menuItem(label="New Action", command="faceit_new_action()")
    cmds.menuItem(label="Populate Action", command="faceit_populate_action()")
    cmds.menuItem(divider=True)
    
    # Import/Export
    cmds.menuItem(label="Export Expressions...", command="faceit_export_expressions()")
    cmds.menuItem(label="Append Expressions...", command="faceit_append_expressions()")
    cmds.menuItem(divider=True)
    
    # Utilities
    cmds.menuItem(label="Reset Constraints", command="faceit_reset_constraints()")
    cmds.menuItem(label="Set Bind Pose", command="faceit_set_bind_pose()")


# ============================================================
# Expression Data Management Functions
# ============================================================

def get_expression_data() -> Dict:
    """
    Get all expression data from the scene.
    
    Returns:
        Dictionary containing expression data
    """
    if not cmds.objExists("faceit_animation_data"):
        return {}
    
    data = {
        'names': cmds.getAttr("faceit_animation_data.expression_names") or "",
        'frames': cmds.getAttr("faceit_animation_data.expression_frames") or "",
        'sides': cmds.getAttr("faceit_animation_data.expression_sides") or "",
        'procedural': cmds.getAttr("faceit_animation_data.expression_procedural") or "",
        'mirror_names': cmds.getAttr("faceit_animation_data.expression_mirror_names") or "",
        'current_index': cmds.getAttr("faceit_animation_data.current_index") or 0,
    }
    
    # Parse strings to lists
    result = {}
    for key, value in data.items():
        if key in ['names', 'sides', 'procedural', 'mirror_names']:
            result[key] = value.split(',') if value else []
        elif key == 'frames':
            result[key] = [int(x) for x in value.split(',')] if value else []
        else:
            result[key] = value
    
    return result


def save_expression_data(data: Dict) -> bool:
    """
    Save expression data to the scene.
    
    Args:
        data: Dictionary containing expression data
        
    Returns:
        True if successful, False otherwise
    """
    if not cmds.objExists("faceit_animation_data"):
        _register_custom_attributes()
    
    try:
        # Convert lists to strings
        names_str = ','.join(data.get('names', []))
        frames_str = ','.join(str(x) for x in data.get('frames', []))
        sides_str = ','.join(data.get('sides', []))
        procedural_str = ','.join(data.get('procedural', []))
        mirror_names_str = ','.join(data.get('mirror_names', []))
        
        cmds.setAttr("faceit_animation_data.expression_names", names_str, type="string")
        cmds.setAttr("faceit_animation_data.expression_frames", frames_str, type="string")
        cmds.setAttr("faceit_animation_data.expression_sides", sides_str, type="string")
        cmds.setAttr("faceit_animation_data.expression_procedural", procedural_str, type="string")
        cmds.setAttr("faceit_animation_data.expression_mirror_names", mirror_names_str, type="string")
        
        if 'current_index' in data:
            cmds.setAttr("faceit_animation_data.current_index", data['current_index'])
        
        return True
    except Exception as e:
        cmds.warning(f"Failed to save expression data: {str(e)}")
        return False


def get_expression_frame(expression_name: str) -> int:
    """
    Get the frame number for an expression.
    
    Args:
        expression_name: Name of the expression
        
    Returns:
        Frame number, or -1 if not found
    """
    data = get_expression_data()
    names = data.get('names', [])
    frames = data.get('frames', [])
    
    for i, name in enumerate(names):
        if name == expression_name and i < len(frames):
            return frames[i]
    
    return -1


def get_expression_by_frame(frame: int) -> Optional[str]:
    """
    Get the expression name at a specific frame.
    
    Args:
        frame: Frame number
        
    Returns:
        Expression name, or None if not found
    """
    data = get_expression_data()
    names = data.get('names', [])
    frames = data.get('frames', [])
    
    for i, f in enumerate(frames):
        if f == frame and i < len(names):
            return names[i]
    
    return None


# ============================================================
# Side Detection Functions
# ============================================================

def get_side(expression_name: str) -> str:
    """
    Return the side (L/N/R) for the given expression name.
    
    Args:
        expression_name: Name of the expression
        
    Returns:
        'L', 'R', or 'N'
    """
    # Check for side indicators in the name
    left_indicators = ['_L', '_l', 'Left', 'LEFT', 'left']
    right_indicators = ['_R', '_r', 'Right', 'RIGHT', 'right']
    
    for indicator in left_indicators:
        if indicator in expression_name:
            return 'L'
    
    for indicator in right_indicators:
        if indicator in expression_name:
            return 'R'
    
    return 'N'


def poll_side_in_expression_name(side: str, expression_name: str) -> bool:
    """
    Check if the correct side is in the expression name.
    
    Args:
        side: 'L' or 'R'
        expression_name: Name of the expression
        
    Returns:
        True if side is found in name
    """
    if side == 'L':
        return any(x in expression_name for x in ['_L', '_l', 'Left'])
    elif side == 'R':
        return any(x in expression_name for x in ['_R', '_r', 'Right'])
    return False


def get_mirror_name(side: str, expression_name: str) -> str:
    """
    Get the mirror name for an expression.
    
    Args:
        side: 'L' or 'R'
        expression_name: Name of the expression
        
    Returns:
        Mirrored expression name
    """
    if side == 'L':
        # Replace left indicators with right
        for indicator in ['_L', '_l', 'Left', 'LEFT', 'left']:
            if indicator in expression_name:
                if indicator == '_L':
                    return expression_name.replace('_L', '_R')
                elif indicator == '_l':
                    return expression_name.replace('_l', '_r')
                elif indicator == 'Left':
                    return expression_name.replace('Left', 'Right')
                elif indicator == 'LEFT':
                    return expression_name.replace('LEFT', 'RIGHT')
                elif indicator == 'left':
                    return expression_name.replace('left', 'right')
    
    elif side == 'R':
        # Replace right indicators with left
        for indicator in ['_R', '_r', 'Right', 'RIGHT', 'right']:
            if indicator in expression_name:
                if indicator == '_R':
                    return expression_name.replace('_R', '_L')
                elif indicator == '_r':
                    return expression_name.replace('_r', '_l')
                elif indicator == 'Right':
                    return expression_name.replace('Right', 'Left')
                elif indicator == 'RIGHT':
                    return expression_name.replace('RIGHT', 'LEFT')
                elif indicator == 'right':
                    return expression_name.replace('right', 'left')
    
    return ''


# ============================================================
# Blend Shape Utilities
# ============================================================

def get_blendshape_names(mesh: str) -> List[str]:
    """
    Get all blend shape names from a mesh.
    
    Args:
        mesh: Mesh object name
        
    Returns:
        List of blend shape target names
    """
    if not cmds.objExists(mesh):
        return []
    
    # Find blendShape node
    history = cmds.listHistory(mesh, pruneDagObjects=True, interestLevel=2) or []
    for node in history:
        if cmds.nodeType(node) == 'blendShape':
            # Get the target names
            targets = cmds.listAttr(f"{node}.weight", multi=True) or []
            # Remove 'weight' prefix
            names = []
            for target in targets:
                if target.startswith('weight'):
                    names.append(target.replace('weight[', '').replace(']', ''))
            return names
    
    return []


def get_blendshape_weight(mesh: str, target_name: str) -> float:
    """
    Get the weight of a specific blend shape target.
    
    Args:
        mesh: Mesh object name
        target_name: Target name
        
    Returns:
        Weight value
    """
    if not cmds.objExists(mesh):
        return 0.0
    
    history = cmds.listHistory(mesh, pruneDagObjects=True, interestLevel=2) or []
    for node in history:
        if cmds.nodeType(node) == 'blendShape':
            # Try to find the target
            targets = cmds.listAttr(f"{node}.weight", multi=True) or []
            for target in targets:
                # Check if this target matches
                if target.endswith(f"targets[{target_name}]") or target_name in target:
                    return cmds.getAttr(f"{node}.{target}")
    
    return 0.0


def set_blendshape_weight(mesh: str, target_name: str, weight: float) -> bool:
    """
    Set the weight of a specific blend shape target.
    
    Args:
        mesh: Mesh object name
        target_name: Target name
        weight: Weight value (0.0 to 1.0)
        
    Returns:
        True if successful
    """
    if not cmds.objExists(mesh):
        return False
    
    history = cmds.listHistory(mesh, pruneDagObjects=True, interestLevel=2) or []
    for node in history:
        if cmds.nodeType(node) == 'blendShape':
            targets = cmds.listAttr(f"{node}.weight", multi=True) or []
            for target in targets:
                if target.endswith(f"targets[{target_name}]") or target_name in target:
                    cmds.setAttr(f"{node}.{target}", weight)
                    return True
    
    return False


# ============================================================
# Action Management Utilities
# ============================================================

def create_overwrite_animation(rig: str) -> str:
    """
    Create an overwrite animation action for the rig.
    
    Args:
        rig: Rig object name
        
    Returns:
        Action name
    """
    # Get or create shape action
    shape_action = "faceit_shape_action"
    if not cmds.objExists(shape_action):
        shape_action = cmds.createNode("animCurveUU", name=shape_action)
    
    # Create overwrite action
    overwrite_action = "overwrite_shape_action"
    if cmds.objExists(overwrite_action):
        cmds.delete(overwrite_action)
    
    # Duplicate the shape action
    overwrite_action = cmds.duplicate(shape_action, name=overwrite_action)[0]
    
    # Set as current action
    if cmds.objExists(rig):
        cmds.setAttr(f"{rig}.currentAction", overwrite_action, type="string")
    
    return overwrite_action


def add_expression_keyframes(rig: str, frame: int):
    """
    Add keyframes for all bones at a specific frame.
    
    Args:
        rig: Rig object name
        frame: Frame number
    """
    if not cmds.objExists(rig):
        return
    
    # Get all joints in the rig
    joints = cmds.ls(f"{rig}.bones", type='joint') or []
    
    for joint in joints:
        # Add translate keyframes
        for axis in ['X', 'Y', 'Z']:
            cmds.setKeyframe(joint, attribute=f"translate{axis}", t=frame, v=0)
        
        # Add rotate keyframes
        for axis in ['X', 'Y', 'Z']:
            cmds.setKeyframe(joint, attribute=f"rotate{axis}", t=frame, v=0)
        
        # Add scale keyframes
        for axis in ['X', 'Y', 'Z']:
            cmds.setKeyframe(joint, attribute=f"scale{axis}", t=frame, v=1)


def remove_all_animation_for_frame(action: str, frame: int):
    """
    Remove all keyframes at a specific frame from an action.
    
    Args:
        action: Action name
        frame: Frame number
    """
    if not cmds.objExists(action):
        return
    
    # Get all animation curves
    curves = cmds.listAnimCurves(action) or []
    
    for curve in curves:
        # Find keyframes at this frame
        keyframes = cmds.keyframe(curve, query=True, timeChange=True) or []
        for i, t in enumerate(keyframes):
            if int(t) == frame:
                cmds.keyframe(curve, edit=True, remove=True, time=(t,))


def remove_fcurve_from_action(action: str, data_path: str) -> bool:
    """
    Remove an fcurve from an action.
    
    Args:
        action: Action name
        data_path: Data path of the fcurve to remove
        
    Returns:
        True if successful
    """
    if not cmds.objExists(action):
        return False
    
    # Find the animation curve
    curves = cmds.listAnimCurves(action) or []
    for curve in curves:
        if cmds.getAttr(f"{curve}.attributeName") == data_path:
            cmds.delete(curve)
            return True
    
    return False


# ============================================================
# Keyframe Utilities
# ============================================================

def copy_keyframe(action: str, frame_from: int, frame_to: int, data_path_filter: List[str] = None):
    """
    Copy keyframes from one frame to another.
    
    Args:
        action: Action name
        frame_from: Source frame
        frame_to: Target frame
        data_path_filter: Filter by data path strings
    """
    if not cmds.objExists(action):
        return
    
    curves = cmds.listAnimCurves(action) or []
    
    for curve in curves:
        data_path = cmds.getAttr(f"{curve}.attributeName") or ""
        
        # Filter if needed
        if data_path_filter:
            if not any(d in data_path for d in data_path_filter):
                continue
        
        # Get keyframes at source frame
        keyframes = cmds.keyframe(curve, query=True, timeChange=True) or []
        values = cmds.keyframe(curve, query=True, valueChange=True) or []
        
        for i, t in enumerate(keyframes):
            if int(t) == frame_from and i < len(values):
                # Insert keyframe at target frame
                cmds.keyframe(curve, edit=True, absolute=True, t=(frame_to,), value=values[i])


def mirror_keyframe(action: str, frame_from: int, frame_to: int):
    """
    Mirror keyframes from one frame to another.
    
    Args:
        action: Action name
        frame_from: Source frame
        frame_to: Target frame
    """
    if not cmds.objExists(action):
        return
    
    curves = cmds.listAnimCurves(action) or []
    
    for curve in curves:
        data_path = cmds.getAttr(f"{curve}.attributeName") or ""
        
        # Get keyframes at source frame
        keyframes = cmds.keyframe(curve, query=True, timeChange=True) or []
        values = cmds.keyframe(curve, query=True, valueChange=True) or []
        
        for i, t in enumerate(keyframes):
            if int(t) == frame_from and i < len(values):
                # Mirror the value (negate for translate/rotate)
                value = values[i]
                if 'translate' in data_path or 'rotate' in data_path:
                    value = -value
                
                # Insert mirrored keyframe at target frame
                cmds.keyframe(curve, edit=True, absolute=True, t=(frame_to,), value=value)


# ============================================================
# Constraint Utilities
# ============================================================

def get_constraint_defaults() -> Dict[str, Dict[str, float]]:
    """
    Get default constraint influence values.
    
    Returns:
        Dictionary mapping bone names to constraint defaults
    """
    return {
        'lip.T.L.001': {"Copy Location": 0.25, "Copy Location.001": 0.5, "Copy Rotation": 1.0, "Copy Scale": 1.0},
        'lip.T.R.001': {"Copy Location": 0.25, "Copy Location.001": 0.5, "Copy Rotation": 1.0, "Copy Scale": 1.0},
        'lip.B.L.001': {"Copy Location": 0.25, "Copy Location.001": 0.5, "Copy Rotation": 1.0, "Copy Scale": 1.0},
        'lip.B.R.001': {"Copy Location": 0.25, "Copy Location.001": 0.5, "Copy Rotation": 1.0, "Copy Scale": 1.0},
        'lid.T.L.003': {"Copy Location": 0.6, "Copy Rotation": 1.0},
        'lid.T.L.002': {"Copy Location": 0.5},
        'lid.T.L.001': {"Copy Location": 0.6, "Copy Rotation": 1.0},
        'lid.B.L.001': {"Copy Rotation": 1.0, "Copy Location": 0.6},
        'lid.B.L.002': {"Copy Location": 0.5, "Copy Location.001": 0.1},
        'lid.B.L.003': {"Copy Rotation": 1.0, "Copy Location": 0.6},
        'brow.B.L.003': {"Copy Location": 0.6},
        'brow.B.L.002': {"Copy Location": 0.25},
        'brow.B.L.001': {"Copy Location": 0.6},
        'lid.T.R.003': {"Copy Location": 0.6},
        'lid.T.R.002': {"Copy Location": 0.5},
        'lid.T.R.001': {"Copy Location": 0.6},
        'lid.B.R.001': {"Copy Location": 0.6},
        'lid.B.R.002': {"Copy Location": 0.5, "Copy Location.001": 0.1},
        'lid.B.R.003': {"Copy Location": 0.6},
        'brow.B.R.003': {"Copy Location": 0.6},
        'brow.B.R.002': {"Copy Location": 0.25},
        'brow.B.R.001': {"Copy Location": 0.6},
        'nose.005': {'Copy Location': 0.5},
        'nose.003': {'Copy Location': 0.5},
        'nose.L.001': {'Copy Location': 0.2},
        'nose.R.001': {'Copy Location': 0.2},
        'cheek.T.L.001': {'Copy Location': 0.0},
        'cheek.T.R.001': {'Copy Location': 0.0},
        'nose.L': {'Copy Location': 0.25},
        'nose.R': {'Copy Location': 0.25},
        'chin.002': {'Copy Location': 0.5},
        'cheek.B.L.001': {'Copy Location': 0.5},
        'cheek.B.R.001': {'Copy Location': 0.5},
        'brow.T.L.002': {'Copy Location': 0.5, 'Copy Location.001': 0.5},
        'brow.T.R.002': {'Copy Location': 0.5, 'Copy Location.001': 0.5},
    }


def restore_constraints_to_default_values(rig: str) -> bool:
    """
    Restore all constraints to their default values.
    
    Args:
        rig: Rig object name
        
    Returns:
        True if successful
    """
    if not cmds.objExists(rig):
        return False
    
    defaults = get_constraint_defaults()
    
    for bone_name, constraints_dict in defaults.items():
        if not cmds.objExists(bone_name):
            continue
        
        for constraint_name, influence in constraints_dict.items():
            # Find constraint on bone
            constraints = cmds.listConnections(f"{bone_name}.constraints") or []
            for constr in constraints:
                if cmds.objExists(constr) and cmds.nodeType(constr) == 'constraint':
                    # Check if this is the right constraint
                    if cmds.getAttr(f"{constr}.name") == constraint_name:
                        try:
                            cmds.setAttr(f"{constr}.influence", influence)
                        except:
                            pass
    
    return True


# ============================================================
# Dimension Utilities
# ============================================================

def get_rig_dimensions(rig: str, control_bones: List[str] = None) -> List[float]:
    """
    Get the dimensions of a rig.
    
    Args:
        rig: Rig object name
        control_bones: List of control bone names (optional)
        
    Returns:
        List of [width, height, depth]
    """
    if not cmds.objExists(rig):
        return [1.0, 1.0, 1.0]
    
    if control_bones is None:
        # Use default Faceit control bones
        from ..core.faceit_data import FACEIT_CTRL_BONES
        control_bones = FACEIT_CTRL_BONES
    
    x_vals, y_vals, z_vals = [], [], []
    
    for bone in control_bones:
        if cmds.objExists(bone):
            pos = cmds.getAttr(f"{bone}.translate")[0]
            x_vals.append(pos[0])
            y_vals.append(pos[1])
            z_vals.append(pos[2])
    
    if not x_vals:
        return [1.0, 1.0, 1.0]
    
    return [
        max(x_vals) - min(x_vals),
        max(y_vals) - min(y_vals),
        max(z_vals) - min(z_vals)
    ]


def get_eye_dimensions(rig: str) -> Tuple[float, float]:
    """
    Get eye dimensions from a rig.
    
    Args:
        rig: Rig object name
        
    Returns:
        Tuple of (left eye height, right eye height)
    """
    def get_eye_height(side: str) -> float:
        top = None
        bot = None
        
        top_name = f"lid.T.{side}.002"
        bot_name = f"lid.B.{side}.002"
        
        if cmds.objExists(top_name):
            top = cmds.getAttr(f"{top_name}.translate")[0]
        if cmds.objExists(bot_name):
            bot = cmds.getAttr(f"{bot_name}.translate")[0]
        
        if top and bot:
            return abs(top[1] - bot[1])
        return 1.0
    
    return get_eye_height('L'), get_eye_height('R')


# ============================================================
# Scale Utilities
# ============================================================

def scale_action_to_rig(
    action: str,
    scale: List[float],
    filter_skip: List[str] = None,
    frames: List[int] = None
):
    """
    Scale an action to the rig's dimensions.
    
    Args:
        action: Action name
        scale: Scale factors [x, y, z]
        filter_skip: Bone names to skip
        frames: Frames to scale (if None, scale all)
    """
    if not cmds.objExists(action) or not scale:
        return
    
    # Get all animation curves
    curves = cmds.listAnimCurves(action) or []
    
    # Build skip list
    skip_data_paths = []
    if filter_skip:
        for bone in filter_skip:
            for attr in ['translate', 'rotate']:
                data_path = f"{bone}.{attr}"
                skip_data_paths.append(data_path)
    
    for curve in curves:
        data_path = cmds.getAttr(f"{curve}.attributeName") or ""
        
        # Skip if in skip list
        if any(skip in data_path for skip in skip_data_paths):
            continue
        
        # Only scale location curves
        if 'translate' not in data_path:
            continue
        
        # Get axis from attribute name
        if data_path.endswith('X'):
            idx = 0
        elif data_path.endswith('Y'):
            idx = 1
        elif data_path.endswith('Z'):
            idx = 2
        else:
            continue
        
        scale_factor = scale[idx] if idx < len(scale) else 1.0
        
        # Get keyframes
        keyframes = cmds.keyframe(curve, query=True, timeChange=True) or []
        values = cmds.keyframe(curve, query=True, valueChange=True) or []
        
        for i, (t, v) in enumerate(zip(keyframes, values)):
            if frames is not None and int(t) not in frames:
                continue
            
            # Scale the value
            new_value = v * scale_factor
            cmds.keyframe(curve, edit=True, absolute=True, valueChange=new_value, index=i, time=(t,))


def scale_poses_to_new_dimensions(
    rig: str,
    pose_bones: List[str],
    scale: List[float],
    action: str = None,
    frames: List[int] = None
):
    """
    Scale poses to new dimensions.
    
    Args:
        rig: Rig object name
        pose_bones: List of bone names
        scale: Scale factors [x, y, z]
        action: Action name
        frames: Frames to scale
    """
    if not cmds.objExists(rig) or not pose_bones or not frames:
        return
    
    # Get current pose for each bone at each frame
    for frame in frames:
        cmds.currentTime(frame)
        
        for bone in pose_bones:
            if not cmds.objExists(bone):
                continue
            
            # Get current translation
            pos = cmds.getAttr(f"{bone}.translate")[0]
            
            # Scale position
            new_pos = [
                pos[0] * scale[0],
                pos[1] * scale[1],
                pos[2] * scale[2]
            ]
            
            # Set new position
            cmds.setAttr(f"{bone}.translateX", new_pos[0])
            cmds.setAttr(f"{bone}.translateY", new_pos[1])
            cmds.setAttr(f"{bone}.translateZ", new_pos[2])
            
            # Keyframe
            cmds.setKeyframe(bone, attribute="translate", t=frame)


def scale_eye_animation(rig: str, eye_dim_L_old: float, eye_dim_R_old: float, action: str = None):
    """
    Scale eye animation to match rig dimensions.
    
    Args:
        rig: Rig object name
        eye_dim_L_old: Left eye old dimension
        eye_dim_R_old: Right eye old dimension
        action: Action name (optional)
    """
    # Get current eye dimensions
    eye_L, eye_R = get_eye_dimensions(rig)
    
    scale_L = eye_L / eye_dim_L_old if eye_dim_L_old != 0 else 1.0
    scale_R = eye_R / eye_dim_R_old if eye_dim_R_old != 0 else 1.0
    
    # Scale left eye bones
    lid_bones_L = ['lid.T.L.003', 'lid.T.L.002', 'lid.T.L.001',
                   'lid.B.L.001', 'lid.B.L.002', 'lid.B.L.003']
    
    # Scale right eye bones
    lid_bones_R = ['lid.T.R.003', 'lid.T.R.002', 'lid.T.R.001',
                   'lid.B.R.001', 'lid.B.R.002', 'lid.B.R.003']
    
    # Apply scaling
    _scale_bone_animation(action, lid_bones_L, scale_L)
    _scale_bone_animation(action, lid_bones_R, scale_R)


def scale_eye_look_animation(rig: str, scale_factor: float = 0.25, action: str = None):
    """
    Scale eye look animation for anime eyes.
    
    Args:
        rig: Rig object name
        scale_factor: Scale factor
        action: Action name (optional)
    """
    eye_bones = ["eye.R", "eye.L", "eyes", "eye_common"]
    _scale_bone_animation(action, eye_bones, scale_factor)


def _scale_bone_animation(action: str, bone_names: List[str], scale_factor: float):
    """
    Scale animation for specific bones.
    
    Args:
        action: Action name
        bone_names: List of bone names
        scale_factor: Scale factor
    """
    if not action or not cmds.objExists(action) or scale_factor == 1.0:
        return
    
    for bone_name in bone_names:
        if not cmds.objExists(bone_name):
            continue
        
        # Get animation curves for this bone
        curves = cmds.listAnimCurves(bone_name) or []
        
        for curve in curves:
            data_path = cmds.getAttr(f"{curve}.attributeName") or ""
            
            # Scale translate values
            if 'translate' in data_path:
                keyframes = cmds.keyframe(curve, query=True, timeChange=True) or []
                values = cmds.keyframe(curve, query=True, valueChange=True) or []
                
                for i, (t, v) in enumerate(zip(keyframes, values)):
                    cmds.keyframe(curve, edit=True, absolute=True, valueChange=v * scale_factor, index=i, time=(t,))


def amplify_pose(
    action: str,
    filter_pose_bone_names: List[str] = None,
    frame: int = -1,
    scale_factor: float = 1.0
):
    """
    Amplify or scale a pose in an action.
    
    Args:
        action: Action name
        filter_pose_bone_names: Filter bones
        frame: Frame to amplify (-1 for all)
        scale_factor: Scale factor
    """
    if not cmds.objExists(action) or scale_factor == 1.0:
        return
    
    curves = cmds.listAnimCurves(action) or []
    
    for curve in curves:
        data_path = cmds.getAttr(f"{curve}.attributeName") or ""
        bone_name = data_path.split('.')[0] if '.' in data_path else ""
        
        # Filter bones
        if filter_pose_bone_names and bone_name not in filter_pose_bone_names:
            continue
        
        # Skip non-transform curves
        if not any(x in data_path for x in ['translate', 'rotate', 'scale']):
            continue
        
        # Skip quaternion W component
        if 'rotation_quaternion' in data_path and data_path.endswith('W'):
            continue
        
        keyframes = cmds.keyframe(curve, query=True, timeChange=True) or []
        values = cmds.keyframe(curve, query=True, valueChange=True) or []
        
        for i, (t, v) in enumerate(zip(keyframes, values)):
            # Filter by frame
            if frame != -1 and int(t) != frame:
                continue
            
            # Calculate new value
            if 'scale' in data_path:
                # For scale, amplify from 1.0
                new_value = ((v - 1.0) * scale_factor) + 1.0
            else:
                # For translate/rotate, amplify from 0.0
                new_value = v * scale_factor
            
            cmds.keyframe(curve, edit=True, absolute=True, valueChange=new_value, index=i, time=(t,))


def reset_key_frame(
    action: str,
    filter_pose_bone_names: List[str],
    backup_action: str,
    frame: int
):
    """
    Reset a keyframe to its backup value.
    
    Args:
        action: Action name
        filter_pose_bone_names: Filter bones
        backup_action: Backup action name
        frame: Frame number
    """
    if not cmds.objExists(action) or not cmds.objExists(backup_action):
        return
    
    curves = cmds.listAnimCurves(action) or []
    
    for curve in curves:
        data_path = cmds.getAttr(f"{curve}.attributeName") or ""
        bone_name = data_path.split('.')[0] if '.' in data_path else ""
        
        # Filter bones
        if filter_pose_bone_names and bone_name not in filter_pose_bone_names:
            continue
        
        # Get value from backup action
        backup_curves = cmds.listAnimCurves(backup_action) or []
        backup_value = None
        
        for b_curve in backup_curves:
            if cmds.getAttr(f"{b_curve}.attributeName") == data_path:
                keyframes = cmds.keyframe(b_curve, query=True, timeChange=True) or []
                values = cmds.keyframe(b_curve, query=True, valueChange=True) or []
                
                for i, t in enumerate(keyframes):
                    if int(t) == frame and i < len(values):
                        backup_value = values[i]
                        break
                break
        
        if backup_value is not None:
            # Set backup value
            keyframes = cmds.keyframe(curve, query=True, timeChange=True) or []
            for i, t in enumerate(keyframes):
                if int(t) == frame:
                    cmds.keyframe(curve, edit=True, absolute=True, valueChange=backup_value, index=i, time=(t,))
                    break


def backup_expression(action: str, backup_action: str, frame: int):
    """
    Backup an expression to the backup action.
    
    Args:
        action: Action name
        backup_action: Backup action name
        frame: Frame number
    """
    if not cmds.objExists(action) or not cmds.objExists(backup_action):
        return
    
    curves = cmds.listAnimCurves(action) or []
    
    for curve in curves:
        data_path = cmds.getAttr(f"{curve}.attributeName") or ""
        
        # Get value at frame
        keyframes = cmds.keyframe(curve, query=True, timeChange=True) or []
        values = cmds.keyframe(curve, query=True, valueChange=True) or []
        
        for i, t in enumerate(keyframes):
            if int(t) == frame and i < len(values):
                # Set value in backup action
                backup_curves = cmds.listAnimCurves(backup_action) or []
                found = False
                
                for b_curve in backup_curves:
                    if cmds.getAttr(f"{b_curve}.attributeName") == data_path:
                        # Insert keyframe
                        cmds.keyframe(b_curve, edit=True, absolute=True, t=(frame,), value=values[i])
                        found = True
                        break
                
                if not found:
                    # Create new curve in backup action
                    cmds.keyframe(backup_action, edit=True, absolute=True, t=(frame,), value=values[i], attribute=data_path)


# ============================================================
# Data Path Utilities
# ============================================================

def get_bone_name_from_data_path(data_path: str) -> str:
    """
    Get bone name from a data path string.
    
    Args:
        data_path: Data path string
        
    Returns:
        Bone name
    """
    if '"' in data_path:
        # Format: pose.bones["bone_name"].attribute
        start = data_path.find('["') + 2
        end = data_path.find('"]', start)
        if start > 0 and end > start:
            return data_path[start:end]
    
    # Format: bone_name.attribute
    return data_path.split('.')[0] if '.' in data_path else data_path


def get_data_path_value(data_path: str) -> str:
    """
    Get the transform part of a data path.
    
    Args:
        data_path: Full data path
        
    Returns:
        Transform part (location, rotation_euler, etc.)
    """
    if '.' in data_path:
        return data_path.split('.')[-1]
    return data_path


# ============================================================
# Rotation Conversion Utilities
# ============================================================

def get_value_as_rotation(rot_mode: str, rotation_value: List[float]):
    """
    Convert a rotation value to a rotation object.
    
    Args:
        rot_mode: 'EULER', 'QUATERNION', or 'AXIS_ANGLE'
        rotation_value: List of rotation values
        
    Returns:
        Rotation object
    """
    if rot_mode == 'EULER':
        return MEulerRotation(*rotation_value)
    elif rot_mode == 'QUATERNION':
        return MQuaternion(*rotation_value)
    else:
        # Axis angle: [angle, x, y, z]
        angle = rotation_value[0]
        axis = [rotation_value[1], rotation_value[2], rotation_value[3]]
        return MQuaternion(angle, MVector(*axis))


def convert_rotation_values(rot, rot_mode_from: str, rot_mode_to: str):
    """
    Convert rotation values from one mode to another.
    
    Args:
        rot: Rotation object
        rot_mode_from: Source rotation mode
        rot_mode_to: Target rotation mode
        
    Returns:
        Converted rotation values as list
    """
    # Convert to quaternion first
    if rot_mode_from == 'EULER':
        quat = MQuaternion(rot)
    elif rot_mode_from == 'QUATERNION':
        quat = rot
    else:
        # Axis angle
        quat = MQuaternion(rot[0], MVector(rot[1], rot[2], rot[3]))
    
    # Convert from quaternion to target
    if rot_mode_to == 'EULER':
        euler = quat.asEulerRotation()
        return [euler.x, euler.y, euler.z]
    elif rot_mode_to == 'QUATERNION':
        return [quat.w, quat.x, quat.y, quat.z]
    else:
        # Axis angle
        vec, angle = quat.asAxisAngle()
        return [angle, vec.x, vec.y, vec.z]


# ============================================================
# Active Expression Utilities
# ============================================================

def get_active_expression() -> Optional[str]:
    """
    Get the currently active expression name.
    
    Returns:
        Expression name or None
    """
    if not cmds.objExists("faceit_animation_data"):
        return None
    
    current_idx = cmds.getAttr("faceit_animation_data.current_index") or 0
    names_str = cmds.getAttr("faceit_animation_data.expression_names") or ""
    names = names_str.split(',') if names_str else []
    
    if current_idx < len(names):
        return names[current_idx]
    
    return None


# ============================================================
# Module Exports
# ============================================================

__all__ = [
    # Rotation utilities
    'get_rotation_mode',
    'get_data_path_from_rotation_mode',
    'get_rotation_mode_from_data_path',
    'convert_rotation_values',
    'get_value_as_rotation',
    
    # Data path utilities
    'get_bone_name_from_data_path',
    'get_data_path_value',
    
    # Side utilities
    'get_side',
    'get_mirror_name',
    'poll_side_in_expression_name',
    
    # Blend shape utilities
    'get_blendshape_names',
    'get_blendshape_weight',
    'set_blendshape_weight',
    
    # Action utilities
    'create_overwrite_animation',
    'add_expression_keyframes',
    'remove_all_animation_for_frame',
    'remove_fcurve_from_action',
    
    # Keyframe utilities
    'copy_keyframe',
    'mirror_keyframe',
    'reset_key_frame',
    'backup_expression',
    'amplify_pose',
    
    # Constraint utilities
    'restore_constraints_to_default_values',
    'get_constraint_defaults',
    
    # Dimension utilities
    'get_rig_dimensions',
    'get_eye_dimensions',
    'scale_eye_animation',
    'scale_eye_look_animation',
    'scale_action_to_rig',
    'scale_poses_to_new_dimensions',
    
    # Expression data utilities
    'get_expression_data',
    'save_expression_data',
    'get_expression_frame',
    'get_expression_by_frame',
    'get_active_expression',
    
    # Module initialization
    'initialize_plugin',
    'uninitialize_plugin',
    'register_commands',
]