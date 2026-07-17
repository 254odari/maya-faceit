"""
maya_faceit.rig.tongue_presets

Tongue rig preset manager.

Provides built-in and user-defined presets for
tongue rig construction and animation settings.

Target
------
Maya 2026
Python 3.11
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json


# ---------------------------------------------------------
# Data
# ---------------------------------------------------------

@dataclass(slots=True)
class TonguePreset:

    name: str

    joints: int = 7

    fk_controls: int = 7

    ik_controls: int = 3

    use_spline_ik: bool = True

    enable_stretch: bool = True

    enable_squash: bool = True

    preserve_volume: bool = True

    enable_fkik: bool = True

    thickness: float = 1.0

    taper: float = 0.5

    stretch_limit: float = 2.0

    visibility_mode: str = "Animator"


# ---------------------------------------------------------
# Manager
# ---------------------------------------------------------

class TonguePresetManager:

    BUILTIN = {

        "Default": TonguePreset(
            name="Default"
        ),

        "Realistic Human": TonguePreset(
            name="Realistic Human",
            joints=7,
            taper=0.65,
            thickness=1.0,
        ),

        "Stylized Cartoon": TonguePreset(
            name="Stylized Cartoon",
            joints=9,
            thickness=1.4,
            stretch_limit=3.0,
        ),

        "Creature": TonguePreset(
            name="Creature",
            joints=9,
            taper=0.30,
            stretch_limit=4.0,
        ),

        "Snake": TonguePreset(
            name="Snake",
            joints=9,
            thickness=0.35,
            taper=0.15,
            stretch_limit=5.0,
        ),

        "Dragon": TonguePreset(
            name="Dragon",
            joints=9,
            thickness=1.8,
            taper=0.25,
        ),

        "Game Ready": TonguePreset(
            name="Game Ready",
            joints=7,
            preserve_volume=False,
        ),

        "Film Quality": TonguePreset(
            name="Film Quality",
            joints=9,
            preserve_volume=True,
            enable_stretch=True,
            enable_squash=True,
        ),

    }

    def __init__(self):

        self.user_presets: dict[str, TonguePreset] = {}

    # -----------------------------------------------------

    def names(self) -> list[str]:

        return sorted(

            list(self.BUILTIN.keys()) +

            list(self.user_presets.keys())

        )

    # -----------------------------------------------------

    def get(

        self,

        name: str,

    ) -> TonguePreset | None:

        if name in self.user_presets:

            return self.user_presets[name]

        return self.BUILTIN.get(name)

    # -----------------------------------------------------

    def register(

        self,

        preset: TonguePreset,

    ):

        self.user_presets[preset.name] = preset

    # -----------------------------------------------------

    def remove(

        self,

        name: str,

    ):

        self.user_presets.pop(name, None)

    # -----------------------------------------------------

    def apply(

        self,

        preset_name: str,

        builder,

    ) -> bool:

        preset = self.get(preset_name)

        if preset is None:

            return False

        builder.settings.joints = preset.joints
        builder.settings.use_spline_ik = preset.use_spline_ik
        builder.settings.enable_stretch = preset.enable_stretch
        builder.settings.enable_squash = preset.enable_squash
        builder.settings.preserve_volume = preset.preserve_volume
        builder.settings.enable_fkik = preset.enable_fkik
        builder.settings.thickness = preset.thickness
        builder.settings.taper = preset.taper
        builder.settings.stretch_limit = preset.stretch_limit

        return True

    # -----------------------------------------------------

    def save(

        self,

        preset: TonguePreset,

        filepath: str,

    ):

        with open(filepath, "w", encoding="utf8") as stream:

            json.dump(

                asdict(preset),

                stream,

                indent=4,

            )

    # -----------------------------------------------------

    def load(

        self,

        filepath: str,

    ) -> TonguePreset:

        with open(filepath, encoding="utf8") as stream:

            data = json.load(stream)

        preset = TonguePreset(**data)

        self.register(preset)

        return preset

    # -----------------------------------------------------

    def export_library(

        self,

        directory: str,

    ):

        folder = Path(directory)

        folder.mkdir(

            parents=True,

            exist_ok=True,

        )

        for preset in self.BUILTIN.values():

            path = folder / f"{preset.name}.json"

            self.save(

                preset,

                str(path),

            )

    # -----------------------------------------------------

    def reset(self):

        self.user_presets.clear()


# ---------------------------------------------------------
# Singleton
# ---------------------------------------------------------

tongue_presets = TonguePresetManager()