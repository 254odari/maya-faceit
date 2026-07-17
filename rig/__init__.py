"""
maya_faceit.rig

Rigging framework for Maya Faceit.

This package provides a complete facial rigging system with builders
for all facial regions: brows, cheeks, eyelids, eyes, jaw, lips, nose,
ears, forehead, neck, tongue, and more.

It includes:
- Joint and controller creation
- Matrix-based rigging (offsetParentMatrix workflow)
- Driver networks (utility nodes)
- Set Driven Key (SDK) management
- Space switching
- Visibility management
- Rig rebuilding and validation

All modules are designed to be used together through a unified API.

Author: Maya FaceIT Team
"""

from __future__ import annotations

# ------------------------------------------------------------
# Version
# ------------------------------------------------------------

__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"

# ------------------------------------------------------------
# Exports
# ------------------------------------------------------------

# Attribute management
from .attributes import attribute_manager, AttributeManager

# Controller management
from .controller_shapes import controller_shapes, ControllerShapeLibrary, SHAPES, ShapePreset
from .controllers import controller_builder, ControllerBuilder, Controller

# Joint management
from .joints import joint_builder, JointBuilder, JointData

# Constraints
from .constraints import constraint_builder, ConstraintBuilder, Constraint

# Matrix rigging
from .matrix_rig import matrix_rig, MatrixRig, MatrixConstraint

# Driver network
from .driver_network import driver_network, DriverNetworkBuilder, DriverNetwork

# SDK
from .sdk import sdk_manager, SDKManager, SDK

# Space switching
from .spaces import space_manager, SpaceManager, Space

# Deformers
from .deformers import deformer_manager, DeformerManager, Deformer

# Skeletons
from .skeleton import skeleton_builder, SkeletonBuilder, Skeleton

# Visibility
from .visibility import visibility, VisibilityManager, VisibilityGroup

# Rig rebuilding
from .rig_rebuilder import rig_rebuilder, RigRebuilder, RebuildTarget, RigInfo

# Utilities
from .utilities import (
    create_transform,
    match_transform,
    snap,
    create_offset_group,
    create_zero_group,
    lock_channels,
    unlock_channels,
    set_color,
    hide,
    show,
    freeze,
    safe_parent,
    connect,
    disconnect,
    delete_if_exists,
    exists,
)

# ------------------------------------------------------------
# Region Builders
# ------------------------------------------------------------

# Brows
from .brows import brow_builder, BrowBuilder, BrowRig

# Cheeks
from .cheeks import cheek_builder, CheekBuilder, CheekRig

# Eyelids
from .eyelids import eyelid_builder, EyelidBuilder, EyelidRig

# Eyes
from .eyes import eyes_builder, EyesBuilder, EyeRig

# Jaw
from .jaw import jaw_builder, JawBuilder, JawRig

# Lips
from .lips import lip_builder, LipBuilder, LipRig

# Nose
from .nose import nose_builder, NoseBuilder, NoseRig

# Ears
from .ears import ear_builder, EarBuilder, EarRig

# Forehead
from .forehead import forehead, ForeheadRig, ForeheadSettings, ForeheadRigState

# Neck
from .neck import neck, NeckRig, NeckSettings, NeckRigState

# Tongue
from .tongue import tongue, TongueRig, TongueSettings

# Tongue subcomponents (for advanced use)
from .tongue_chain import tongue_chain_builder, TongueChainBuilder, TongueChain
from .tongue_controls import tongue_controls, TongueControlFactory, TongueControls, ControlData
from .tongue_attributes import tongue_attributes, TongueAttributeBuilder
from .tongue_fk import tongue_fk, TongueFKBuilder, TongueFKRig
from .tongue_ik import tongue_ik, TongueIKBuilder, TongueIKRig
from .tongue_blend import tongue_blend, TongueBlendBuilder, TongueBlendRig, BlendNode
from .tongue_stretch import tongue_stretch, TongueStretchBuilder, TongueStretchRig
from .tongue_volume import tongue_volume, TongueVolumeBuilder, TongueVolumeRig
from .tongue_visibility import tongue_visibility, TongueVisibilityBuilder, TongueVisibilityRig, VisibilityGroup as TVisibilityGroup
from .tongue_presets import tongue_presets, TonguePresetManager, TonguePreset
from .tongue_solver import tongue_solver, TongueSolver, TongueSolverState

# ------------------------------------------------------------
# __all__
# ------------------------------------------------------------

__all__ = [
    # Version
    "__version__",
    "__author__",

    # Attributes
    "attribute_manager",
    "AttributeManager",

    # Controller shapes
    "controller_shapes",
    "ControllerShapeLibrary",
    "SHAPES",
    "ShapePreset",

    # Controllers
    "controller_builder",
    "ControllerBuilder",
    "Controller",

    # Joints
    "joint_builder",
    "JointBuilder",
    "JointData",

    # Constraints
    "constraint_builder",
    "ConstraintBuilder",
    "Constraint",

    # Matrix rigging
    "matrix_rig",
    "MatrixRig",
    "MatrixConstraint",

    # Driver network
    "driver_network",
    "DriverNetworkBuilder",
    "DriverNetwork",

    # SDK
    "sdk_manager",
    "SDKManager",
    "SDK",

    # Space switching
    "space_manager",
    "SpaceManager",
    "Space",

    # Deformers
    "deformer_manager",
    "DeformerManager",
    "Deformer",

    # Skeletons
    "skeleton_builder",
    "SkeletonBuilder",
    "Skeleton",

    # Visibility
    "visibility",
    "VisibilityManager",
    "VisibilityGroup",

    # Rig rebuilding
    "rig_rebuilder",
    "RigRebuilder",
    "RebuildTarget",
    "RigInfo",

    # Utilities
    "create_transform",
    "match_transform",
    "snap",
    "create_offset_group",
    "create_zero_group",
    "lock_channels",
    "unlock_channels",
    "set_color",
    "hide",
    "show",
    "freeze",
    "safe_parent",
    "connect",
    "disconnect",
    "delete_if_exists",
    "exists",

    # Region builders
    "brow_builder",
    "BrowBuilder",
    "BrowRig",

    "cheek_builder",
    "CheekBuilder",
    "CheekRig",

    "eyelid_builder",
    "EyelidBuilder",
    "EyelidRig",

    "eyes_builder",
    "EyesBuilder",
    "EyeRig",

    "jaw_builder",
    "JawBuilder",
    "JawRig",

    "lip_builder",
    "LipBuilder",
    "LipRig",

    "nose_builder",
    "NoseBuilder",
    "NoseRig",

    "ear_builder",
    "EarBuilder",
    "EarRig",

    "forehead",
    "ForeheadRig",
    "ForeheadSettings",
    "ForeheadRigState",

    "neck",
    "NeckRig",
    "NeckSettings",
    "NeckRigState",

    "tongue",
    "TongueRig",
    "TongueSettings",

    # Tongue subcomponents
    "tongue_chain_builder",
    "TongueChainBuilder",
    "TongueChain",

    "tongue_controls",
    "TongueControlFactory",
    "TongueControls",
    "ControlData",

    "tongue_attributes",
    "TongueAttributeBuilder",

    "tongue_fk",
    "TongueFKBuilder",
    "TongueFKRig",

    "tongue_ik",
    "TongueIKBuilder",
    "TongueIKRig",

    "tongue_blend",
    "TongueBlendBuilder",
    "TongueBlendRig",
    "BlendNode",

    "tongue_stretch",
    "TongueStretchBuilder",
    "TongueStretchRig",

    "tongue_volume",
    "TongueVolumeBuilder",
    "TongueVolumeRig",

    "tongue_visibility",
    "TongueVisibilityBuilder",
    "TongueVisibilityRig",

    "tongue_presets",
    "TonguePresetManager",
    "TonguePreset",

    "tongue_solver",
    "TongueSolver",
    "TongueSolverState",
]