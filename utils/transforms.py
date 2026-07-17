# -*- coding: utf-8 -*-
"""
maya_faceit.utils.transforms
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Transform utilities.
"""

import maya.cmds as cmds # type: ignore
from typing import Tuple, Optional, List, Dict
from .math import MathUtils


class TransformUtils:
    """Utilities for transforming objects."""

    @staticmethod
    def get_translation(node: str, world_space: bool = True) -> Tuple[float, float, float]:
        """Get translation."""
        if world_space:
            t = cmds.xform(node, q=True, ws=True, t=True)
        else:
            t = cmds.xform(node, q=True, t=True)
        return (t[0], t[1], t[2])

    @staticmethod
    def get_rotation(node: str, world_space: bool = True) -> Tuple[float, float, float]:
        """Get rotation (Euler)."""
        if world_space:
            r = cmds.xform(node, q=True, ws=True, ro=True)
        else:
            r = cmds.xform(node, q=True, ro=True)
        return (r[0], r[1], r[2])

    @staticmethod
    def get_scale(node: str, world_space: bool = True) -> Tuple[float, float, float]:
        """Get scale."""
        if world_space:
            s = cmds.xform(node, q=True, ws=True, s=True)
        else:
            s = cmds.xform(node, q=True, s=True)
        return (s[0], s[1], s[2])

    @staticmethod
    def set_translation(node: str, t: Tuple[float, float, float],
                        world_space: bool = True) -> bool:
        """Set translation."""
        if not cmds.objExists(node):
            return False
        if world_space:
            cmds.xform(node, ws=True, t=(t[0], t[1], t[2]))
        else:
            cmds.xform(node, t=(t[0], t[1], t[2]))
        return True

    @staticmethod
    def set_rotation(node: str, r: Tuple[float, float, float],
                     world_space: bool = True) -> bool:
        """Set rotation."""
        if not cmds.objExists(node):
            return False
        if world_space:
            cmds.xform(node, ws=True, ro=(r[0], r[1], r[2]))
        else:
            cmds.xform(node, ro=(r[0], r[1], r[2]))
        return True

    @staticmethod
    def set_scale(node: str, s: Tuple[float, float, float],
                  world_space: bool = True) -> bool:
        """Set scale."""
        if not cmds.objExists(node):
            return False
        if world_space:
            cmds.xform(node, ws=True, s=(s[0], s[1], s[2]))
        else:
            cmds.xform(node, s=(s[0], s[1], s[2]))
        return True

    @staticmethod
    def freeze_transforms(node: str, translate: bool = True,
                          rotate: bool = True, scale: bool = True) -> bool:
        """Freeze transforms (makeIdentity)."""
        if not cmds.objExists(node):
            return False
        cmds.makeIdentity(node, apply=True,
                         t=translate, r=rotate, s=scale, n=0)
        return True

    @staticmethod
    def reset_transforms(node: str) -> bool:
        """Reset transforms to identity (position 0, rotation 0, scale 1)."""
        if not cmds.objExists(node):
            return False
        cmds.setAttr(f"{node}.tx", 0)
        cmds.setAttr(f"{node}.ty", 0)
        cmds.setAttr(f"{node}.tz", 0)
        cmds.setAttr(f"{node}.rx", 0)
        cmds.setAttr(f"{node}.ry", 0)
        cmds.setAttr(f"{node}.rz", 0)
        cmds.setAttr(f"{node}.sx", 1)
        cmds.setAttr(f"{node}.sy", 1)
        cmds.setAttr(f"{node}.sz", 1)
        return True

    @staticmethod
    def match_transforms(source: str, target: str,
                         match_translate: bool = True,
                         match_rotate: bool = True,
                         match_scale: bool = True) -> bool:
        """Match transforms from source to target."""
        if not cmds.objExists(source) or not cmds.objExists(target):
            return False
        if match_translate:
            t = TransformUtils.get_translation(source)
            TransformUtils.set_translation(target, t)
        if match_rotate:
            r = TransformUtils.get_rotation(source)
            TransformUtils.set_rotation(target, r)
        if match_scale:
            s = TransformUtils.get_scale(source)
            TransformUtils.set_scale(target, s)
        return True

    @staticmethod
    def mirror_transform(node: str, axis: str = "x", world_space: bool = True) -> bool:
        """Mirror the transform across an axis."""
        if not cmds.objExists(node):
            return False
        t = TransformUtils.get_translation(node, world_space)
        r = TransformUtils.get_rotation(node, world_space)
        if axis == "x":
            t = (-t[0], t[1], t[2])
            r = (r[0], -r[1], -r[2])
        elif axis == "y":
            t = (t[0], -t[1], t[2])
            r = (-r[0], r[1], -r[2])
        else:  # z
            t = (t[0], t[1], -t[2])
            r = (-r[0], -r[1], r[2])
        TransformUtils.set_translation(node, t, world_space)
        TransformUtils.set_rotation(node, r, world_space)
        return True