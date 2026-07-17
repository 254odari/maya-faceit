"""
maya_faceit.rig.tongue_controls

Tongue controller factory.

Creates every controller required by the tongue rig.

Target
------
Maya 2026
Python 3.11
"""

from __future__ import annotations

from dataclasses import dataclass, field

import maya.cmds as cmds # type: ignore

from .controllers import controller_manager


# ----------------------------------------------------------
# Constants
# ----------------------------------------------------------

MASTER_SIZE = 1.50
FK_SIZE = 0.28
IK_SIZE = 0.45
SPLINE_SIZE = 0.40

MASTER_COLOR = "yellow"
FK_COLOR = "yellow"
IK_COLOR = "cyan"
SPLINE_COLOR = "green"


# ----------------------------------------------------------
# Data Classes
# ----------------------------------------------------------

@dataclass(slots=True)
class ControlData:

    control: str
    zero: str
    offset: str


@dataclass(slots=True)
class TongueControls:

    master: ControlData | None = None

    fk: list[ControlData] = field(default_factory=list)

    ik: list[ControlData] = field(default_factory=list)

    spline: list[ControlData] = field(default_factory=list)


# ----------------------------------------------------------
# Factory
# ----------------------------------------------------------

class TongueControlFactory:

    def __init__(self):

        self.data = TongueControls()

    # ------------------------------------------------------

    def create_master(self) -> ControlData:

        ctrl = controller_manager.create(

            name="C_Tongue_Master_CTRL",

            shape="square",

            size=MASTER_SIZE,

            color=MASTER_COLOR,

        )

        data = self._build_groups(ctrl)

        self.data.master = data

        return data

    # ------------------------------------------------------

    def create_fk(self, joints: list[str]) -> list[ControlData]:

        self.data.fk.clear()

        for i, joint in enumerate(joints, start=1):

            ctrl = controller_manager.create(

                name=f"C_Tongue_FK_{i:02d}_CTRL",

                shape="circle",

                size=FK_SIZE,

                color=FK_COLOR,

            )

            data = self._build_groups(ctrl)

            cmds.matchTransform(data.zero, joint)

            self.data.fk.append(data)

        return self.data.fk

    # ------------------------------------------------------

    def create_ik(self) -> list[ControlData]:

        self.data.ik.clear()

        for name in ("Base", "Mid", "Tip"):

            ctrl = controller_manager.create(

                name=f"C_Tongue_IK_{name}_CTRL",

                shape="cube",

                size=IK_SIZE,

                color=IK_COLOR,

            )

            self.data.ik.append(

                self._build_groups(ctrl)

            )

        return self.data.ik

    # ------------------------------------------------------

    def create_spline(self) -> list[ControlData]:

        self.data.spline.clear()

        for name in ("Start", "Middle", "End"):

            ctrl = controller_manager.create(

                name=f"C_Tongue_SPLINE_{name}_CTRL",

                shape="sphere",

                size=SPLINE_SIZE,

                color=SPLINE_COLOR,

            )

            self.data.spline.append(

                self._build_groups(ctrl)

            )

        return self.data.spline

    # ------------------------------------------------------

    def _build_groups(self, ctrl: str) -> ControlData:

        zero = cmds.group(

            empty=True,

            name=f"{ctrl}_ZERO"

        )

        offset = cmds.group(

            empty=True,

            name=f"{ctrl}_OFFSET"

        )

        cmds.matchTransform(zero, ctrl)

        cmds.parent(offset, zero)

        cmds.parent(ctrl, offset)

        return ControlData(

            control=ctrl,

            zero=zero,

            offset=offset,

        )

    # ------------------------------------------------------

    def set_fk_visibility(self, visible: bool):

        for item in self.data.fk:

            cmds.setAttr(

                item.control + ".visibility",

                visible,

            )

    # ------------------------------------------------------

    def set_ik_visibility(self, visible: bool):

        for item in self.data.ik:

            cmds.setAttr(

                item.control + ".visibility",

                visible,

            )

    # ------------------------------------------------------

    def set_spline_visibility(self, visible: bool):

        for item in self.data.spline:

            cmds.setAttr(

                item.control + ".visibility",

                visible,

            )

    # ------------------------------------------------------

    def delete(self):

        objects = []

        if self.data.master:

            objects.extend([

                self.data.master.zero,

                self.data.master.control,

            ])

        for group in (

            self.data.fk,

            self.data.ik,

            self.data.spline,

        ):

            for item in group:

                objects.append(item.zero)

        for obj in reversed(objects):

            if cmds.objExists(obj):

                cmds.delete(obj)

        self.data = TongueControls()


# ----------------------------------------------------------
# Singleton
# ----------------------------------------------------------

tongue_controls = TongueControlFactory()