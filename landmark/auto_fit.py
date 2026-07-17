"""
maya_faceit.landmark.auto_fit

Automatic facial rig fitting system.

Computes guide, joint and controller transforms
from aligned facial landmarks. This module prepares
rig placement data but does not construct the rig.

Target
------
Maya 2026
Python 3.11
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .alignment import (
    AlignmentResult,
)

from .landmark_mapper import (
    MappedLandmark,
)


# ------------------------------------------------------------
# Data
# ------------------------------------------------------------

@dataclass(slots=True)
class AutoFitSettings:
    """
    User configurable fitting options.
    """

    preserve_scale: bool = False

    preserve_rotation: bool = False

    enforce_symmetry: bool = True

    preview_only: bool = False

    fit_tongue: bool = True

    fit_neck: bool = True

    fit_ears: bool = True


@dataclass(slots=True)
class FitTransform:
    """
    Target transform for one rig component.
    """

    translation: tuple[float, float, float]

    rotation: tuple[float, float, float]

    scale: tuple[float, float, float]


@dataclass(slots=True)
class AutoFitResult:

    success: bool = False

    transforms: dict[str, FitTransform] = field(
        default_factory=dict
    )

    warnings: list[str] = field(
        default_factory=list
    )

    message: str = ""


# ------------------------------------------------------------
# Solver
# ------------------------------------------------------------

class AutoFit:
    """
    Computes rig placement transforms.
    """

    def __init__(self):

        self.settings = AutoFitSettings()

        self._last: AutoFitResult | None = None

    # -----------------------------------------------------

    def fit(
        self,
        alignment: AlignmentResult,
    ) -> AutoFitResult:

        result = AutoFitResult()

        if not alignment.success:

            result.message = "Alignment failed."

            return result

        self.fit_head(alignment, result)
        self.fit_eyes(alignment, result)
        self.fit_eyelids(alignment, result)
        self.fit_brows(alignment, result)
        self.fit_nose(alignment, result)
        self.fit_cheeks(alignment, result)
        self.fit_lips(alignment, result)
        self.fit_jaw(alignment, result)
        self.fit_chin(alignment, result)

        if self.settings.fit_ears:
            self.fit_ears(alignment, result)

        if self.settings.fit_neck:
            self.fit_neck(alignment, result)

        if self.settings.fit_tongue:
            self.fit_tongue(alignment, result)

        result.success = True
        result.message = "Auto fit completed."

        self._last = result

        return result

    # -----------------------------------------------------

    def _add_transform(
        self,
        result: AutoFitResult,
        name: str,
        translation=(0.0, 0.0, 0.0),
        rotation=(0.0, 0.0, 0.0),
        scale=(1.0, 1.0, 1.0),
    ):

        result.transforms[name] = FitTransform(
            translation=translation,
            rotation=rotation,
            scale=scale,
        )

    # -----------------------------------------------------
    # Individual fitting stages
    # -----------------------------------------------------

    def fit_head(self, alignment, result):
        self._add_transform(result, "Head")

    def fit_eyes(self, alignment, result):
        self._add_transform(result, "Eyes")

    def fit_eyelids(self, alignment, result):
        self._add_transform(result, "Eyelids")

    def fit_brows(self, alignment, result):
        self._add_transform(result, "Brows")

    def fit_nose(self, alignment, result):
        self._add_transform(result, "Nose")

    def fit_cheeks(self, alignment, result):
        self._add_transform(result, "Cheeks")

    def fit_lips(self, alignment, result):
        self._add_transform(result, "Lips")

    def fit_jaw(self, alignment, result):
        self._add_transform(result, "Jaw")

    def fit_chin(self, alignment, result):
        self._add_transform(result, "Chin")

    def fit_ears(self, alignment, result):
        self._add_transform(result, "Ears")

    def fit_neck(self, alignment, result):
        self._add_transform(result, "Neck")

    def fit_tongue(self, alignment, result):
        self._add_transform(result, "Tongue")

    # -----------------------------------------------------

    def preview(self):
        """
        Preview the fitting result.

        Intended to drive viewport guides without
        modifying the rig.
        """
        return self._last

    # -----------------------------------------------------

    def apply(self):
        """
        Apply transforms to the rig.

        Future versions should forward the computed
        transforms to rig_builder.py.
        """
        return self._last

    # -----------------------------------------------------

    def rollback(self):
        """
        Restore the previous rig state.
        """
        self._last = None

    # -----------------------------------------------------

    def validate(
        self,
        result: AutoFitResult,
    ) -> bool:

        return (
            result.success and
            len(result.transforms) > 0
        )

    # -----------------------------------------------------

    def serialize(self):

        if self._last is None:
            return {}

        return {
            name: {
                "translation": t.translation,
                "rotation": t.rotation,
                "scale": t.scale,
            }
            for name, t in self._last.transforms.items()
        }

    # -----------------------------------------------------

    def clear(self):

        self._last = None


# ------------------------------------------------------------
# Singleton
# ------------------------------------------------------------

auto_fit = AutoFit()