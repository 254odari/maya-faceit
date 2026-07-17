"""
core/validation/scene_validator.py

Scene-wide validation for Maya Faceit.
"""

import maya.cmds as cmds # type: ignore
from typing import Dict, List, Tuple

from ..logging.logger import log
from .validation import Validator
from .topology_validator import TopologyValidator
from ..scene.references import ReferenceUtils


class SceneValidator:
    """
    Validate the entire Maya scene for rigging readiness.
    """

    @staticmethod
    def validate_scene() -> Dict[str, List[str]]:
        """
        Perform complete scene validation.

        Checks:
            - No unknown nodes
            - No missing references
            - No empty groups
            - No locked nodes with animation
            - Meshes are valid for rigging (call mesh_validator)

        Returns:
            Dict with 'errors' and 'warnings'.
        """
        errors = []
        warnings = []

        # 1. Unknown nodes
        unknown = cmds.ls(type='unknown')
        if unknown:
            warnings.append(f"Unknown nodes found: {len(unknown)}")

        # 2. Missing references
        missing_refs = ReferenceUtils.find_missing_references()
        if missing_refs:
            errors.append(f"Missing references: {', '.join(missing_refs)}")

        # 3. Empty groups
        groups = cmds.ls(type='group')
        empty_groups = []
        for g in groups:
            if not cmds.listRelatives(g, children=True):
                empty_groups.append(g)
        if empty_groups:
            warnings.append(f"Empty groups found: {len(empty_groups)}")

        # 4. Locked nodes with animation
        transforms = cmds.ls(type='transform', long=True)
        locked_animated = []
        for t in transforms:
            if cmds.lockNode(t, q=True, lock=True)[0]:
                attrs = cmds.listAttr(t, keyable=True) or []
                for attr in attrs:
                    if cmds.keyframe(f"{t}.{attr}", q=True, keyframeCount=True):
                        locked_animated.append(t)
                        break
        if locked_animated:
            warnings.append(f"Locked nodes with animation: {len(locked_animated)}")

        # 5. Mesh validation for all meshes
        meshes = cmds.ls(type='mesh', long=True)
        if meshes:
            from .mesh_validator import MeshValidator
            for m in meshes:
                # Get transform
                parents = cmds.listRelatives(m, parent=True, fullPath=True)
                if parents:
                    mesh_transform = parents[0]
                    result = MeshValidator.validate_for_rigging(mesh_transform)
                    if result['errors']:
                        errors.extend([f"{mesh_transform}: {e}" for e in result['errors']])
                    if result['warnings']:
                        warnings.extend([f"{mesh_transform}: {w}" for w in result['warnings']])
        else:
            warnings.append("No polygon meshes found in scene.")

        # 6. Check for references (info)
        refs = ReferenceUtils.get_all_references()
        if refs:
            warnings.append(f"Scene contains {len(refs)} references. Ensure they are valid.")

        return {'errors': errors, 'warnings': warnings}

    @staticmethod
    def print_scene_report() -> None:
        """Print a formatted scene validation report."""
        result = SceneValidator.validate_scene()
        print("\n" + "=" * 60)
        print("SCENE VALIDATION REPORT")
        print("=" * 60)
        if result['errors']:
            print("ERRORS:")
            for e in result['errors']:
                print(f"  - {e}")
        if result['warnings']:
            print("WARNINGS:")
            for w in result['warnings']:
                print(f"  - {w}")
        if not result['errors'] and not result['warnings']:
            print("Scene is clean. No issues found.")
        print("=" * 60)


# Singleton
scene_validator = SceneValidator()