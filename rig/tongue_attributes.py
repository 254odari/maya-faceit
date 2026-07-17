"""
maya_faceit.rig.tongue_attributes

Tongue rig attribute manager.

Adds custom attributes to the tongue master control.
These attributes drive FK/IK blend, stretch, squash,
volume, thickness, taper, and other tongue-specific
behaviors.

Target
------
Maya 2026
Python 3.11
"""

from __future__ import annotations

import maya.cmds as cmds # type: ignore

from .attributes import attribute_manager


class TongueAttributeBuilder:
    """
    Adds custom attributes to the tongue master control.
    """

    def __init__(self):
        self.master_control = None

    # -----------------------------------------------------

    def build(self, master_control: str) -> None:
        """
        Build attributes on the master control.

        Args:
            master_control: Name of the master control (e.g., C_Tongue_Master_CTRL).
        """
        if not cmds.objExists(master_control):
            raise RuntimeError(f"Master control '{master_control}' does not exist.")

        self.master_control = master_control

        # Define attribute data: (name, default, min, max, type)
        attributes = [
            # FK/IK Blend
            ("fkIkBlend", 0.0, 0.0, 1.0, "float"),
            # Stretch and Squash
            ("stretch", 0.0, 0.0, 1.0, "float"),
            ("squash", 0.0, 0.0, 1.0, "float"),
            ("autoStretch", 1.0, 0.0, 1.0, "float"),
            ("autoSquash", 1.0, 0.0, 1.0, "float"),
            # Volume
            ("volume", 1.0, 0.0, 2.0, "float"),
            ("thickness", 1.0, 0.0, 2.0, "float"),
            ("taper", 0.5, 0.0, 1.0, "float"),
            # Curl and twist
            ("curlRoot", 0.0, -1.0, 1.0, "float"),
            ("curlTip", 0.0, -1.0, 1.0, "float"),
            ("roll", 0.0, -180.0, 180.0, "float"),
            ("twist", 0.0, -180.0, 180.0, "float"),
            ("side", 0.0, -1.0, 1.0, "float"),
            # IK specific
            ("ikTwist", 0.0, -180.0, 180.0, "float"),
            ("ikRoll", 0.0, -180.0, 180.0, "float"),
            ("ikFollow", 1.0, 0.0, 1.0, "float"),
            # Visibility
            ("showTongue", 1, 0, 1, "bool"),
            ("showFK", 1, 0, 1, "bool"),
            ("showIK", 1, 0, 1, "bool"),
            ("showCurve", 0, 0, 1, "bool"),
            ("showClusters", 0, 0, 1, "bool"),
            ("showHelpers", 0, 0, 1, "bool"),
            ("showDebug", 0, 0, 1, "bool"),
            ("autoVisibility", 1, 0, 1, "bool"),
        ]

        for name, default, min_val, max_val, attr_type in attributes:
            if attr_type == "float":
                attribute_manager.add_float(
                    master_control,
                    name,
                    default=default,
                    minimum=min_val,
                    maximum=max_val,
                )
            elif attr_type == "bool":
                attribute_manager.add_bool(
                    master_control,
                    name,
                    default=bool(default),
                )
            else:
                raise ValueError(f"Unknown attribute type: {attr_type}")

    # -----------------------------------------------------

    def delete(self) -> None:
        """
        Delete all custom attributes from the master control.
        """
        if not self.master_control or not cmds.objExists(self.master_control):
            return

        attrs = [
            "fkIkBlend",
            "stretch",
            "squash",
            "autoStretch",
            "autoSquash",
            "volume",
            "thickness",
            "taper",
            "curlRoot",
            "curlTip",
            "roll",
            "twist",
            "side",
            "ikTwist",
            "ikRoll",
            "ikFollow",
            "showTongue",
            "showFK",
            "showIK",
            "showCurve",
            "showClusters",
            "showHelpers",
            "showDebug",
            "autoVisibility",
        ]

        for attr in attrs:
            if cmds.attributeQuery(attr, node=self.master_control, exists=True):
                cmds.deleteAttr(self.master_control, attribute=attr)

        self.master_control = None


# ---------------------------------------------------------
# Singleton
# ---------------------------------------------------------

tongue_attributes = TongueAttributeBuilder()