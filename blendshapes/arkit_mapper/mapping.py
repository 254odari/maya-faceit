"""
maya_faceit.blendshapes.arkit_mapper.mapping

Data models for the ARKit mapping system.

This module contains the core data structures used
throughout the ARKit mapper.

Target
------
Maya 2026
Python 3.11
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .channels import ARKitChannel


# ============================================================
# Rig Target
# ============================================================

@dataclass(slots=True)
class RigTarget:
    """
    A BlendShape driven by an ARKit channel.
    """

    name: str

    multiplier: float = 1.0

    offset: float = 0.0

    enabled: bool = True

    minimum: float = 0.0

    maximum: float = 1.0

    metadata: dict[str, Any] = field(default_factory=dict)

    # --------------------------------------------------------

    def evaluate(
        self,
        coefficient: float,
    ) -> float:
        """
        Convert an ARKit coefficient into
        a BlendShape value.
        """

        value = coefficient * self.multiplier

        value += self.offset

        return max(
            self.minimum,
            min(self.maximum, value),
        )

    # --------------------------------------------------------

    def serialize(self) -> dict:

        return {

            "name": self.name,

            "multiplier": self.multiplier,

            "offset": self.offset,

            "enabled": self.enabled,

            "minimum": self.minimum,

            "maximum": self.maximum,

            "metadata": self.metadata,

        }


# ============================================================
# Mapping
# ============================================================

@dataclass(slots=True)
class ARKitMapping:
    """
    Maps one ARKit channel to one or more rig targets.
    """

    channel: ARKitChannel

    targets: list[RigTarget] = field(default_factory=list)

    enabled: bool = True

    metadata: dict[str, Any] = field(default_factory=dict)

    # --------------------------------------------------------

    def add_target(
        self,
        target: RigTarget,
    ) -> None:

        self.targets.append(target)

    # --------------------------------------------------------

    def remove_target(
        self,
        name: str,
    ) -> bool:

        for target in self.targets:

            if target.name == name:

                self.targets.remove(target)

                return True

        return False

    # --------------------------------------------------------

    def target(
        self,
        name: str,
    ) -> RigTarget | None:

        for target in self.targets:

            if target.name == name:

                return target

        return None

    # --------------------------------------------------------

    def evaluate(
        self,
        coefficient: float,
    ) -> dict[str, float]:
        """
        Evaluate all rig targets.
        """

        if not self.enabled:

            return {}

        values = {}

        for target in self.targets:

            if not target.enabled:

                continue

            values[target.name] = target.evaluate(
                coefficient
            )

        return values

    # --------------------------------------------------------

    @property
    def target_count(self) -> int:

        return len(self.targets)

    # --------------------------------------------------------

    def serialize(self) -> dict:

        return {

            "channel": self.channel.value,

            "enabled": self.enabled,

            "metadata": self.metadata,

            "targets": [

                target.serialize()

                for target in self.targets

            ],

        }


# ============================================================
# Mapping Result
# ============================================================

@dataclass(slots=True)
class MappingResult:
    """
    Result of an ARKit mapping operation.
    """

    success: bool = True

    mapped_channels: int = 0

    mapped_targets: int = 0

    missing_channels: list[str] = field(
        default_factory=list
    )

    warnings: list[str] = field(
        default_factory=list
    )

    errors: list[str] = field(
        default_factory=list
    )

    weights: dict[str, float] = field(
        default_factory=dict
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    # --------------------------------------------------------

    @property
    def has_errors(self) -> bool:

        return len(self.errors) > 0

    # --------------------------------------------------------

    @property
    def has_warnings(self) -> bool:

        return len(self.warnings) > 0

    # --------------------------------------------------------

    def add_warning(
        self,
        message: str,
    ) -> None:

        self.warnings.append(message)

    # --------------------------------------------------------

    def add_error(
        self,
        message: str,
    ) -> None:

        self.errors.append(message)

        self.success = False

    # --------------------------------------------------------

    def serialize(self) -> dict:

        return {

            "success": self.success,

            "mapped_channels": self.mapped_channels,

            "mapped_targets": self.mapped_targets,

            "missing_channels": self.missing_channels,

            "warnings": self.warnings,

            "errors": self.errors,

            "weights": self.weights,

            "metadata": self.metadata,

        }