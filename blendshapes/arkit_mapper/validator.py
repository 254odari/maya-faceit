"""
maya_faceit.blendshapes.arkit_mapper.validator

Validation system for ARKit mappings.

Performs structural validation of ARKit mapping data.

Target
------
Maya 2026
Python 3.11
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .channels import ARKitChannel
from .mapping import ARKitMapping


# ============================================================
# Data
# ============================================================

@dataclass(slots=True)
class ValidationIssue:

    severity: str

    message: str

    channel: str = ""

    target: str = ""


@dataclass(slots=True)
class ValidationReport:

    success: bool = True

    coverage: float = 0.0

    mapped_channels: int = 0

    total_channels: int = ARKitChannel.count()

    issues: list[ValidationIssue] = field(
        default_factory=list
    )

    # --------------------------------------------------------

    @property
    def errors(self) -> int:

        return sum(
            1
            for issue in self.issues
            if issue.severity == "Error"
        )

    # --------------------------------------------------------

    @property
    def warnings(self) -> int:

        return sum(
            1
            for issue in self.issues
            if issue.severity == "Warning"
        )

    # --------------------------------------------------------

    def serialize(self) -> dict:

        return {

            "success": self.success,

            "coverage": self.coverage,

            "mapped_channels": self.mapped_channels,

            "total_channels": self.total_channels,

            "errors": self.errors,

            "warnings": self.warnings,

            "issues": [

                {

                    "severity": issue.severity,

                    "message": issue.message,

                    "channel": issue.channel,

                    "target": issue.target,

                }

                for issue in self.issues

            ],

        }


# ============================================================
# Validator
# ============================================================

class ARKitValidator:
    """
    Validator for ARKit mapping data.
    """

    # --------------------------------------------------------

    def validate(
        self,
        mappings: dict[ARKitChannel, ARKitMapping],
    ) -> ValidationReport:

        report = ValidationReport()

        report.mapped_channels = len(mappings)

        report.coverage = (

            report.mapped_channels

            /

            report.total_channels

        ) * 100.0

        self._validate_missing(report, mappings)

        self._validate_duplicate_targets(report, mappings)

        self._validate_targets(report, mappings)

        self._validate_coefficients(report, mappings)

        report.success = report.errors == 0

        return report

    # --------------------------------------------------------

    def _validate_missing(

        self,

        report: ValidationReport,

        mappings,

    ):

        for channel in ARKitChannel:

            if channel not in mappings:

                report.issues.append(

                    ValidationIssue(

                        severity="Warning",

                        message="Missing ARKit mapping.",

                        channel=channel.value,

                    )

                )

    # --------------------------------------------------------

    def _validate_duplicate_targets(

        self,

        report: ValidationReport,

        mappings,

    ):

        seen = {}

        for mapping in mappings.values():

            for target in mapping.targets:

                if target.name in seen:

                    report.issues.append(

                        ValidationIssue(

                            severity="Warning",

                            message=(
                                "Target used by multiple "
                                "ARKit channels."
                            ),

                            target=target.name,

                        )

                    )

                seen[target.name] = True

    # --------------------------------------------------------

    def _validate_targets(

        self,

        report: ValidationReport,

        mappings,

    ):

        for mapping in mappings.values():

            if not mapping.targets:

                report.issues.append(

                    ValidationIssue(

                        severity="Warning",

                        message="No rig targets.",

                        channel=mapping.channel.value,

                    )

                )

                continue

            for target in mapping.targets:

                if not target.name:

                    report.issues.append(

                        ValidationIssue(

                            severity="Error",

                            message="Empty rig target name.",

                            channel=mapping.channel.value,

                        )

                    )

    # --------------------------------------------------------

    def _validate_coefficients(

        self,

        report: ValidationReport,

        mappings,

    ):

        for mapping in mappings.values():

            for target in mapping.targets:

                if target.multiplier < 0:

                    report.issues.append(

                        ValidationIssue(

                            severity="Error",

                            message="Negative multiplier.",

                            target=target.name,

                        )

                    )

                if target.minimum > target.maximum:

                    report.issues.append(

                        ValidationIssue(

                            severity="Error",

                            message="Invalid clamp range.",

                            target=target.name,

                        )

                    )

    # --------------------------------------------------------

    def coverage(

        self,

        mappings,

    ) -> float:

        return (

            len(mappings)

            /

            ARKitChannel.count()

        ) * 100.0


# ============================================================
# Singleton
# ============================================================

arkit_validator = ARKitValidator()