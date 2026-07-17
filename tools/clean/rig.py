# -*- coding: utf-8 -*-
"""
tools/clean/rig.py

Rig cleanup: unused joints, orphan constraints, orphan controllers.
"""

import maya.cmds as cmds # type: ignore
from .types import RigCleanup


class RigCleaner:
    """
    Clean up rig components: joints, constraints, controllers.
    """

    def __init__(self, settings):
        self.settings = settings

    def cleanup(self) -> RigCleanup:
        """Run rig cleanup."""
        result = RigCleanup()

        # 1. Remove unused joints
        if self.settings.remove_unused_joints:
            joints = cmds.ls(type='joint', long=True)
            # Find joints used in skinClusters or constraints
            used = set()
            for skin in cmds.ls(type='skinCluster'):
                influences = cmds.skinCluster(skin, q=True, influence=True) or []
                used.update(influences)
            for constr in cmds.ls(type='constraint'):
                targets = cmds.constraint(constr, q=True, targetList=True) or []
                used.update(targets)
            for j in joints:
                if self._is_referenced(j):
                    continue
                if j not in used:
                    # Check if it has children
                    children = cmds.listRelatives(j, children=True) or []
                    if not children:
                        try:
                            cmds.delete(j)
                            result.removed_unused_joints += 1
                        except:
                            pass

        # 2. Remove orphan constraints (no connections)
        if self.settings.remove_orphan_constraints:
            constraints = cmds.ls(type='constraint')
            for c in constraints:
                if self._is_referenced(c):
                    continue
                if not cmds.listConnections(c):
                    try:
                        cmds.delete(c)
                        result.removed_orphan_constraints += 1
                    except:
                        pass

        # 3. Remove orphan controllers (no children, no connections)
        if self.settings.remove_orphan_controllers:
            all_transforms = cmds.ls(type='transform', long=True)
            controllers = []
            for t in all_transforms:
                shapes = cmds.listRelatives(t, shapes=True) or []
                if shapes and any(cmds.nodeType(s) in ['nurbsCurve', 'nurbsSurface'] for s in shapes):
                    controllers.append(t)
            for ctrl in controllers:
                if self._is_referenced(ctrl):
                    continue
                children = cmds.listRelatives(ctrl, children=True) or []
                if not children:
                    try:
                        cmds.delete(ctrl)
                        result.removed_orphan_controllers += 1
                    except:
                        pass

        return result

    def _is_referenced(self, node):
        return cmds.referenceQuery(node, isNodeReferenced=True)