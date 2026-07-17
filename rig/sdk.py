"""
maya_faceit.rig.sdk

Set Driven Key (SDK) management for Maya Faceit.

Provides a high-level interface for creating, editing and
managing Maya Set Driven Key relationships.

Target:
    Maya 2026
    Python 3.11
"""

from __future__ import annotations

from dataclasses import dataclass, field

import maya.cmds as cmds # type: ignore


# ----------------------------------------------------------
# Data
# ----------------------------------------------------------

@dataclass(slots=True)
class SDK:

    name: str

    driver: str

    driven: str

    driver_values: list[float] = field(default_factory=list)

    driven_values: list[float] = field(default_factory=list)


# ----------------------------------------------------------
# SDK Manager
# ----------------------------------------------------------

class SDKManager:

    def __init__(self):

        self.sdks: dict[str, SDK] = {}

    # --------------------------------------------------

    def create(
        self,
        name: str,
        driver: str,
        driven: str,
        driver_values: list[float],
        driven_values: list[float],
        interpolation: str = "linear",
    ) -> SDK:

        if len(driver_values) != len(driven_values):

            raise ValueError(
                "Driver and driven value counts must match."
            )

        for dv, rv in zip(driver_values, driven_values):

            cmds.setAttr(driver, dv)

            cmds.setAttr(driven, rv)

            cmds.setDrivenKeyframe(
                driven,
                currentDriver=driver,
            )

        sdk = SDK(
            name=name,
            driver=driver,
            driven=driven,
            driver_values=list(driver_values),
            driven_values=list(driven_values),
        )

        self.sdks[name] = sdk

        self._set_tangent(interpolation)

        return sdk

    # --------------------------------------------------

    def create_linear(
        self,
        name: str,
        driver: str,
        driven: str,
        minimum: float,
        maximum: float,
    ) -> SDK:

        return self.create(

            name=name,

            driver=driver,

            driven=driven,

            driver_values=[
                minimum,
                maximum,
            ],

            driven_values=[
                minimum,
                maximum,
            ],
        )

    # --------------------------------------------------

    def create_corrective(
        self,
        name: str,
        driver: str,
        corrective: str,
    ) -> SDK:

        return self.create(

            name,

            driver,

            corrective,

            [-1, 0, 1],

            [0, 0, 1],
        )

    # --------------------------------------------------

    def delete(
        self,
        name: str,
    ):

        if name in self.sdks:

            del self.sdks[name]

    # --------------------------------------------------

    def exists(
        self,
        name: str,
    ) -> bool:

        return name in self.sdks

    # --------------------------------------------------

    def get(
        self,
        name: str,
    ) -> SDK | None:

        return self.sdks.get(name)

    # --------------------------------------------------

    def list(self):

        return sorted(self.sdks.keys())

    # --------------------------------------------------

    def clear(self):

        self.sdks.clear()

    # --------------------------------------------------

    def mirror(
        self,
        left_name: str,
        right_name: str,
    ):

        left = self.get(left_name)

        if not left:

            return

        self.create(

            right_name,

            left.driver.replace("L_", "R_"),

            left.driven.replace("L_", "R_"),

            left.driver_values,

            left.driven_values,
        )

    # --------------------------------------------------

    def rebuild(
        self,
        name: str,
    ):

        sdk = self.get(name)

        if sdk is None:
            return

        self.create(

            sdk.name,

            sdk.driver,

            sdk.driven,

            sdk.driver_values,

            sdk.driven_values,
        )

    # --------------------------------------------------

    def export(self):

        data = {}

        for sdk in self.sdks.values():

            data[sdk.name] = {

                "driver": sdk.driver,

                "driven": sdk.driven,

                "driver_values": sdk.driver_values,

                "driven_values": sdk.driven_values,
            }

        return data

    # --------------------------------------------------

    def import_data(
        self,
        data: dict,
    ):

        for name, sdk in data.items():

            self.create(

                name,

                sdk["driver"],

                sdk["driven"],

                sdk["driver_values"],

                sdk["driven_values"],
            )

    # --------------------------------------------------

    @staticmethod
    def _set_tangent(
        interpolation: str,
    ):

        curves = cmds.keyframe(
            query=True,
            name=True,
        ) or []

        for curve in curves:

            cmds.keyTangent(

                curve,

                edit=True,

                inTangentType=interpolation,

                outTangentType=interpolation,
            )


# ----------------------------------------------------------
# Singleton
# ----------------------------------------------------------

sdk_manager = SDKManager()