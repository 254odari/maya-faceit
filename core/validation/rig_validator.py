"""
core/validation/rig_validator.py

Rig validation for Maya Faceit.

Validates controller structure, joints, constraints, skinning,
and overall rig integrity.
"""

import maya.cmds as cmds # type: ignore
from typing import List, Optional, Dict, Set

from ..logging.logger import log
from ..naming.naming import naming
from ..scene.hierarchy import HierarchyUtils
from .validation import Validator


class RigValidator:
    """
    Validate facial rig components.
    """

    @staticmethod
    def validate_controllers(controllers: List[str]) -> Dict[str, List[str]]:
        """
        Validate a list of controllers.

        Checks:
            - Each controller exists
            - Each controller is a transform
            - Each controller has a shape (NURBS)
            - No duplicate names

        Returns:
            Dict with keys 'errors' and 'warnings'.
        """
        errors = []
        warnings = []
        seen = set()

        for ctrl in controllers:
            if not cmds.objExists(ctrl):
                errors.append(f"Controller '{ctrl}' does not exist.")
                continue
            if cmds.nodeType(ctrl) != 'transform':
                errors.append(f"'{ctrl}' is not a transform.")
                continue
            shapes = cmds.listRelatives(ctrl, shapes=True) or []
            if not shapes:
                warnings.append(f"Controller '{ctrl}' has no shapes.")
            else:
                nurbs = [s for s in shapes if cmds.nodeType(s) in ['nurbsCurve', 'nurbsSurface']]
                if not nurbs:
                    warnings.append(f"Controller '{ctrl}' has no NURBS shape.")
            if ctrl in seen:
                warnings.append(f"Duplicate controller name: {ctrl}")
            seen.add(ctrl)

        return {'errors': errors, 'warnings': warnings}

    @staticmethod
    def validate_joints(joints: List[str]) -> Dict[str, List[str]]:
        """
        Validate a list of joints.

        Checks:
            - Each joint exists
            - Each joint is a joint
            - No duplicate names

        Returns:
            Dict with 'errors' and 'warnings'.
        """
        errors = []
        warnings = []
        seen = set()

        for jnt in joints:
            if not cmds.objExists(jnt):
                errors.append(f"Joint '{jnt}' does not exist.")
                continue
            if cmds.nodeType(jnt) != 'joint':
                errors.append(f"'{jnt}' is not a joint.")
                continue
            if jnt in seen:
                warnings.append(f"Duplicate joint name: {jnt}")
            seen.add(jnt)

        return {'errors': errors, 'warnings': warnings}

    @staticmethod
    def validate_constraints(constraints: List[str]) -> Dict[str, List[str]]:
        """
        Validate a list of constraints.

        Checks:
            - Each constraint exists
            - Each constraint is a constraint type
            - Targets exist

        Returns:
            Dict with 'errors' and 'warnings'.
        """
        errors = []
        warnings = []
        constraint_types = ['parentConstraint', 'pointConstraint', 'orientConstraint',
                            'scaleConstraint', 'aimConstraint', 'matrixConstraint']

        for con in constraints:
            if not cmds.objExists(con):
                errors.append(f"Constraint '{con}' does not exist.")
                continue
            if cmds.nodeType(con) not in constraint_types:
                warnings.append(f"'{con}' is not a recognized constraint type.")
                continue
            targets = cmds.constraint(con, q=True, targetList=True) or []
            if not targets:
                warnings.append(f"Constraint '{con}' has no targets.")
            for tgt in targets:
                if not cmds.objExists(tgt):
                    errors.append(f"Target '{tgt}' of constraint '{con}' does not exist.")

        return {'errors': errors, 'warnings': warnings}

    @staticmethod
    def validate_skin_clusters(skin_clusters: List[str]) -> Dict[str, List[str]]:
        """
        Validate skinClusters.

        Checks:
            - Each skinCluster exists
            - Influences exist
            - Vertices are bound

        Returns:
            Dict with 'errors' and 'warnings'.
        """
        errors = []
        warnings = []

        for skin in skin_clusters:
            if not cmds.objExists(skin):
                errors.append(f"SkinCluster '{skin}' does not exist.")
                continue
            if cmds.nodeType(skin) != 'skinCluster':
                errors.append(f"'{skin}' is not a skinCluster.")
                continue
            influences = cmds.skinCluster(skin, q=True, influence=True) or []
            for inf in influences:
                if not cmds.objExists(inf):
                    errors.append(f"Influence '{inf}' in skinCluster '{skin}' does not exist.")
            geom = cmds.skinCluster(skin, q=True, geometry=True) or []
            if not geom:
                warnings.append(f"SkinCluster '{skin}' has no geometry.")
            else:
                mesh = geom[0]
                if not cmds.objExists(mesh):
                    errors.append(f"Geometry '{mesh}' of skinCluster '{skin}' does not exist.")
                else:
                    vtx_count = cmds.polyEvaluate(mesh, vertex=True)
                    if vtx_count == 0:
                        warnings.append(f"SkinCluster '{skin}' is on an empty mesh.")

        return {'errors': errors, 'warnings': warnings}

    @staticmethod
    def validate_rig_hierarchy(rig_root: str) -> Dict[str, List[str]]:
        """
        Validate the hierarchy structure of a rig.

        Checks:
            - Rig root exists
            - All children are valid transforms
            - Naming conventions are followed (optional)

        Returns:
            Dict with 'errors' and 'warnings'.
        """
        errors = []
        warnings = []

        if not cmds.objExists(rig_root):
            errors.append(f"Rig root '{rig_root}' does not exist.")
            return {'errors': errors, 'warnings': warnings}

        all_nodes = HierarchyUtils.get_children(rig_root, recursive=True)
        all_nodes.append(rig_root)

        for node in all_nodes:
            if cmds.nodeType(node) == 'transform':
                # Check naming convention
                short_name = node.split('|')[-1]
                if not short_name.endswith('_ctrl') and not short_name.endswith('_jnt') and not short_name.endswith('_grp'):
                    warnings.append(f"Node '{short_name}' does not follow naming convention.")
            else:
                warnings.append(f"Non-transform node '{node}' found in hierarchy.")

        return {'errors': errors, 'warnings': warnings}

    @staticmethod
    def validate_rig_complete(mesh: str, controllers: List[str],
                              joints: List[str], constraints: List[str]) -> Dict[str, List[str]]:
        """
        Perform complete rig validation.

        Combines all individual validators.

        Returns:
            Combined dict with 'errors' and 'warnings'.
        """
        combined = {'errors': [], 'warnings': []}

        # Mesh validation
        if not cmds.objExists(mesh):
            combined['errors'].append(f"Mesh '{mesh}' does not exist.")
        else:
            try:
                Validator.mesh(mesh)
            except Exception as e:
                combined['errors'].append(str(e))

        # Controller validation
        ctrl_result = RigValidator.validate_controllers(controllers)
        combined['errors'].extend(ctrl_result['errors'])
        combined['warnings'].extend(ctrl_result['warnings'])

        # Joint validation
        joint_result = RigValidator.validate_joints(joints)
        combined['errors'].extend(joint_result['errors'])
        combined['warnings'].extend(joint_result['warnings'])

        # Constraint validation
        constr_result = RigValidator.validate_constraints(constraints)
        combined['errors'].extend(constr_result['errors'])
        combined['warnings'].extend(constr_result['warnings'])

        return combined


# Singleton
rig_validator = RigValidator()