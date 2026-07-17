# -*- coding: utf-8 -*-
"""
tools/optimizer/rig.py

Rig optimizations (controllers, attributes, shapes).
"""

import maya.cmds as cmds # type: ignore
from .types import RigOptimization


class RigOptimizer:
    """
    Optimize rig controllers and attributes.
    """

    def __init__(self, settings):
        self.settings = settings

    def optimize(self) -> RigOptimization:
        """Run rig optimizations."""
        result = RigOptimization()

        # Find controllers (heuristic)
        all_transforms = cmds.ls(type='transform', long=True)
        controllers = []
        for t in all_transforms:
            shapes = cmds.listRelatives(t, shapes=True) or []
            if shapes and any(cmds.nodeType(s) in ['nurbsCurve', 'nurbsSurface'] for s in shapes):
                controllers.append(t)
        result.total_controllers = len(controllers)

        for ctrl in controllers:
            if cmds.referenceQuery(ctrl, isNodeReferenced=True):
                continue

            # Remove unused custom attributes
            if self.settings.remove_unused_attributes:
                attrs = cmds.listAttr(ctrl, userDefined=True) or []
                for attr in attrs:
                    full = f"{ctrl}.{attr}"
                    if not cmds.listConnections(full):
                        try:
                            cmds.deleteAttr(full)
                            result.removed_unused_attrs += 1
                        except:
                            pass

            # Optimize controller shapes (remove unnecessary display overrides)
            shapes = cmds.listRelatives(ctrl, shapes=True) or []
            for s in shapes:
                try:
                    if cmds.objExists(f"{s}.overrideEnabled"):
                        cmds.setAttr(f"{s}.overrideEnabled", 0)
                        result.optimized_shapes += 1
                except:
                    pass

            result.optimized_controllers += 1

        return result