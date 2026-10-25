# constraint_utils.py
# Maya Faceit Plugin - Constraint Utilities
# Converted from Blender to Maya Python 3.11

"""
Constraint utilities for Faceit Maya plugin.
Handles constraint creation, management, and influence animation.
"""

import maya.cmds as cmds
import maya.api.OpenMaya as om2
from typing import List, Dict, Optional, Tuple, Any


# ============================================================
# Constraint Creation Functions
# ============================================================

def create_constraint(
    constraint_type: str,
    target: str,
    source: str,
    name: str = None,
    maintain_offset: bool = True,
    **kwargs
) -> Optional[str]:
    """
    Create a constraint between two objects.
    
    Args:
        constraint_type: Type of constraint ('parent', 'point', 'orient', 'scale', 'aim', 'poleVector')
        target: Target object name
        source: Source object name
        name: Constraint name (optional)
        maintain_offset: Whether to maintain offset
        **kwargs: Additional constraint parameters
        
    Returns:
        Created constraint name or None
    """
    if not cmds.objExists(target) or not cmds.objExists(source):
        return None
    
    # Map constraint type to Maya command
    constraint_map = {
        'parent': cmds.parentConstraint,
        'point': cmds.pointConstraint,
        'orient': cmds.orientConstraint,
        'scale': cmds.scaleConstraint,
        'aim': cmds.aimConstraint,
        'poleVector': cmds.poleVectorConstraint,
    }
    
    if constraint_type not in constraint_map:
        print(f"Unknown constraint type: {constraint_type}")
        return None
    
    # Get the constraint function
    constraint_func = constraint_map[constraint_type]
    
    # Build arguments
    args = []
    
    if constraint_type == 'aim':
        # Aim constraint needs aim vector
        args.append(target)
        args.append(source)
        if 'aim_vector' in kwargs:
            args.extend(['-aimVector', kwargs['aim_vector']])
        if 'up_vector' in kwargs:
            args.extend(['-upVector', kwargs['up_vector']])
        if 'world_up_type' in kwargs:
            args.extend(['-worldUpType', kwargs['world_up_type']])
    elif constraint_type == 'poleVector':
        args.append(source)
        args.append(target)
    else:
        args.append(target)
        args.append(source)
    
    # Add maintain offset
    if maintain_offset:
        args.append('-mo')
    
    # Add name
    if name:
        args.extend(['-n', name])
    
    # Execute constraint
    try:
        result = constraint_func(*args)
        return result[0] if result else None
    except Exception as e:
        print(f"Error creating constraint: {str(e)}")
        return None


def create_faceit_constraints(rig: str) -> bool:
    """
    Create all default Faceit constraints on a rig.
    
    Args:
        rig: Rig object name
        
    Returns:
        True if successful
    """
    if not cmds.objExists(rig):
        return False
    
    # Define bone constraints
    constraint_data = {
        'lip.T.L.001': {'Copy Location': {'target': 'lip.T', 'influence': 0.25}},
        'lip.T.R.001': {'Copy Location': {'target': 'lip.T', 'influence': 0.25}},
        'lip.B.L.001': {'Copy Location': {'target': 'lip.B', 'influence': 0.25}},
        'lip.B.R.001': {'Copy Location': {'target': 'lip.B', 'influence': 0.25}},
        'lid.T.L.003': {'Copy Location': {'target': 'lid.T.L.002', 'influence': 0.6}},
        'lid.T.R.003': {'Copy Location': {'target': 'lid.T.R.002', 'influence': 0.6}},
        'lid.B.L.001': {'Copy Location': {'target': 'lid.B.L.002', 'influence': 0.6}},
        'lid.B.R.001': {'Copy Location': {'target': 'lid.B.R.002', 'influence': 0.6}},
    }
    
    for bone_name, constraints in constraint_data.items():
        if not cmds.objExists(bone_name):
            continue
        
        for constraint_name, data in constraints.items():
            target = data.get('target')
            if not target or not cmds.objExists(target):
                continue
            
            # Create constraint
            create_constraint(
                'point',
                target,
                bone_name,
                name=f"{bone_name}_{constraint_name}",
                maintain_offset=True
            )
    
    return True


def get_constraints_on_bone(bone: str) -> List[str]:
    """
    Get all constraints on a bone.
    
    Args:
        bone: Bone name
        
    Returns:
        List of constraint names
    """
    if not cmds.objExists(bone):
        return []
    
    constraints = cmds.listConnections(f"{bone}.constraints") or []
    return constraints


def get_constraint_targets(constraint: str) -> List[str]:
    """
    Get all targets of a constraint.
    
    Args:
        constraint: Constraint name
        
    Returns:
        List of target names
    """
    if not cmds.objExists(constraint):
        return []
    
    targets = cmds.listConnections(f"{constraint}.targets") or []
    return targets


def set_constraint_influence(constraint: str, influence: float) -> bool:
    """
    Set the influence of a constraint.
    
    Args:
        constraint: Constraint name
        influence: Influence value (0.0 to 1.0)
        
    Returns:
        True if successful
    """
    if not cmds.objExists(constraint):
        return False
    
    if cmds.attributeQuery("influence", node=constraint, exists=True):
        cmds.setAttr(f"{constraint}.influence", influence)
        return True
    
    return False


def get_constraint_influence(constraint: str) -> float:
    """
    Get the influence of a constraint.
    
    Args:
        constraint: Constraint name
        
    Returns:
        Influence value
    """
    if not cmds.objExists(constraint):
        return 0.0
    
    if cmds.attributeQuery("influence", node=constraint, exists=True):
        return cmds.getAttr(f"{constraint}.influence")
    
    return 0.0


# ============================================================
# Constraint Influence Animation
# ============================================================

def animate_constraint_influence(
    constraint: str,
    frame: int,
    influence: float,
    keyframe_before: bool = True,
    keyframe_after: bool = True
) -> bool:
    """
    Animate constraint influence at a specific frame.
    
    Args:
        constraint: Constraint name
        frame: Frame number
        influence: Influence value
        keyframe_before: Whether to keyframe before the frame
        keyframe_after: Whether to keyframe after the frame
        
    Returns:
        True if successful
    """
    if not cmds.objExists(constraint):
        return False
    
    if not cmds.attributeQuery("influence", node=constraint, exists=True):
        return False
    
    # Keyframe before
    if keyframe_before:
        current_influence = cmds.getAttr(f"{constraint}.influence")
        cmds.setKeyframe(constraint, attribute="influence", t=frame - 1, v=current_influence)
    
    # Keyframe at frame
    cmds.setAttr(f"{constraint}.influence", influence)
    cmds.setKeyframe(constraint, attribute="influence", t=frame)
    
    # Keyframe after
    if keyframe_after:
        cmds.setKeyframe(constraint, attribute="influence", t=frame + 1, v=influence)
    
    return True


def animate_constraint_influence_curve(
    constraint: str,
    keyframes: Dict[int, float]
) -> bool:
    """
    Animate constraint influence with a curve.
    
    Args:
        constraint: Constraint name
        keyframes: Dictionary mapping frame to influence value
        
    Returns:
        True if successful
    """
    if not cmds.objExists(constraint):
        return False
    
    if not cmds.attributeQuery("influence", node=constraint, exists=True):
        return False
    
    for frame, influence in keyframes.items():
        cmds.setAttr(f"{constraint}.influence", influence)
        cmds.setKeyframe(constraint, attribute="influence", t=frame)
    
    return True


# ============================================================
# Constraint Management
# ============================================================

def remove_constraints_from_bone(bone: str) -> bool:
    """
    Remove all constraints from a bone.
    
    Args:
        bone: Bone name
        
    Returns:
        True if successful
    """
    if not cmds.objExists(bone):
        return False
    
    constraints = get_constraints_on_bone(bone)
    
    for constraint in constraints:
        cmds.delete(constraint)
    
    return True


def remove_constraints_by_type(bone: str, constraint_type: str) -> bool:
    """
    Remove constraints of a specific type from a bone.
    
    Args:
        bone: Bone name
        constraint_type: Constraint type ('parentConstraint', 'pointConstraint', etc.)
        
    Returns:
        True if successful
    """
    if not cmds.objExists(bone):
        return False
    
    constraints = get_constraints_on_bone(bone)
    
    for constraint in constraints:
        if cmds.nodeType(constraint) == constraint_type:
            cmds.delete(constraint)
    
    return True


def enable_constraint(constraint: str, enable: bool) -> bool:
    """
    Enable or disable a constraint.
    
    Args:
        constraint: Constraint name
        enable: Whether to enable
        
    Returns:
        True if successful
    """
    if not cmds.objExists(constraint):
        return False
    
    if cmds.attributeQuery("isEnabled", node=constraint, exists=True):
        cmds.setAttr(f"{constraint}.isEnabled", 1 if enable else 0)
        return True
    
    return False


def is_constraint_enabled(constraint: str) -> bool:
    """
    Check if a constraint is enabled.
    
    Args:
        constraint: Constraint name
        
    Returns:
        True if enabled
    """
    if not cmds.objExists(constraint):
        return False
    
    if cmds.attributeQuery("isEnabled", node=constraint, exists=True):
        return cmds.getAttr(f"{constraint}.isEnabled") == 1
    
    return True


# ============================================================
# Constraint Baking
# ============================================================

def bake_constraint(constraint: str, start_frame: int, end_frame: int) -> bool:
    """
    Bake a constraint to keyframes.
    
    Args:
        constraint: Constraint name
        start_frame: Start frame
        end_frame: End frame
        
    Returns:
        True if successful
    """
    if not cmds.objExists(constraint):
        return False
    
    # Get constrained object
    constrained_objects = cmds.listConnections(f"{constraint}.constraint") or []
    
    if not constrained_objects:
        return False
    
    obj = constrained_objects[0]
    
    # Bake the object
    cmds.bakeResults(
        obj,
        time=(start_frame, end_frame),
        simulation=True,
        sampleBy=1,
        disableImplicitControl=True,
        preserveOutsideKeys=True
    )
    
    # Disable the constraint
    enable_constraint(constraint, False)
    
    return True


def bake_all_constraints_on_object(obj: str, start_frame: int, end_frame: int) -> bool:
    """
    Bake all constraints on an object.
    
    Args:
        obj: Object name
        start_frame: Start frame
        end_frame: End frame
        
    Returns:
        True if successful
    """
    if not cmds.objExists(obj):
        return False
    
    # Get all constraints on the object
    constraints = cmds.listConnections(f"{obj}.constraints") or []
    
    for constraint in constraints:
        bake_constraint(constraint, start_frame, end_frame)
    
    return True


# ============================================================
# Constraint Utilities
# ============================================================

def get_constraint_defaults() -> Dict[str, Dict[str, float]]:
    """
    Get default constraint influence values for Faceit bones.
    
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