"""
arkit/validator.py

ARKit Data Validator

This module provides the quality assurance layer for all ARKit-related data
in the maya_faceit project. It performs validation of coefficients, mapping
tables, presets, poses, calibration data, and runtime frames.

The validator never modifies data; it only inspects, verifies, and reports.
Each validation method returns a ValidationReport with errors, warnings, and
statistics. Validation can be performed at three levels of strictness:
FAST, STANDARD, or STRICT.

All other modules (mapper, remapper, calibration, pose_library, etc.) should
use this validator before processing any ARKit data to ensure consistency
and safety across the system.

Design Principles
-----------------
- Separation of concerns: each validator focuses on one data type.
- No side effects: validation never changes input data.
- Comprehensive reporting: returns structured reports with errors/warnings.
- Configurable strictness: FAST, STANDARD, STRICT levels.
- Maya-agnostic: pure Python, no Maya dependencies.
- Type safety: extensive use of dataclasses and type hints.

Architecture
------------
Foundation (constants, exceptions, enums, logger)
↓
Data Models (ValidationLevel, ValidationIssue, ValidationReport)
↓
Coefficient Validator
↓
Mapping Validator
↓
Preset Validator
↓
Pose Validator
↓
Calibration Validator
↓
Runtime Validator
↓
Diagnostics & Statistics
↓
Public API (ARKitValidator main class)

Example Usage
-------------
    validator = ARKitValidator()
    report = validator.validate_coefficients(frame, level=ValidationLevel.STANDARD)
    if not report.is_valid:
        for error in report.errors:
            print(f"Error: {error.message}")
    else:
        print("Frame is valid")
"""

from __future__ import annotations

import enum
import logging
import math
import re
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any, Union, Callable

# ---- Part 1: Foundation --------------------------------------------------

# Module metadata
__version__ = "1.0.0"
__author__ = "Maya FaceIT Team"

# Logging
logger = logging.getLogger(__name__)

# Constants
ARKIT_CHANNEL_COUNT = 52
MIN_CHANNEL_VALUE = 0.0
MAX_CHANNEL_VALUE = 1.0
MAX_TARGET_NAME_LENGTH = 128
VALID_TARGET_NAME_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_.:]*$')
# Known ARKit blendshape names (should match arkit52.py)
# We'll import from arkit52 if available, but we'll keep a local copy for self-containment.
ARKIT_BLENDSHAPES = [
    "browDownLeft", "browDownRight", "browInnerUp", "browOuterUpLeft", "browOuterUpRight",
    "cheekPuff", "cheekSquintLeft", "cheekSquintRight",
    "eyeBlinkLeft", "eyeBlinkRight", "eyeLookDownLeft", "eyeLookDownRight",
    "eyeLookInLeft", "eyeLookInRight", "eyeLookOutLeft", "eyeLookOutRight",
    "eyeLookUpLeft", "eyeLookUpRight", "eyeSquintLeft", "eyeSquintRight",
    "eyeWideLeft", "eyeWideRight",
    "jawForward", "jawLeft", "jawOpen", "jawRight",
    "mouthClose", "mouthDimpleLeft", "mouthDimpleRight",
    "mouthFrownLeft", "mouthFrownRight", "mouthFunnel",
    "mouthLeft", "mouthLowerDownLeft", "mouthLowerDownRight",
    "mouthPressLeft", "mouthPressRight", "mouthPucker",
    "mouthRight", "mouthRollLower", "mouthRollUpper",
    "mouthShrugLower", "mouthShrugUpper",
    "mouthSmileLeft", "mouthSmileRight",
    "mouthStretchLeft", "mouthStretchRight",
    "mouthUpperUpLeft", "mouthUpperUpRight",
    "noseSneerLeft", "noseSneerRight",
    "tongueOut",
]
ARKIT_SET = set(ARKIT_BLENDSHAPES)

# Exceptions
class ARKitValidationError(Exception):
    """Base exception for validation errors."""
    pass

class ValidationConfigurationError(ARKitValidationError):
    """Raised when validator configuration is invalid."""
    pass

class ValidationDataError(ARKitValidationError):
    """Raised when input data is malformed or missing."""
    pass

# ---- Part 2: Validation Models ------------------------------------------

class ValidationLevel(enum.Enum):
    """Strictness level for validation."""
    FAST = 1       # Basic value checks only
    STANDARD = 2   # All value, metadata, and structure checks
    STRICT = 3     # Full validation including duplicates, warnings, and recommendations

@dataclass
class ValidationIssue:
    """
    A single validation issue (error or warning).
    """
    message: str
    level: str  # "error" or "warning"
    path: Optional[str] = None  # e.g., "frame.jawOpen"
    suggestion: Optional[str] = None

@dataclass
class ValidationReport:
    """
    The complete report of a validation run.
    """
    is_valid: bool
    errors: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)

    def add_error(self, message: str, path: Optional[str] = None, suggestion: Optional[str] = None) -> None:
        self.errors.append(ValidationIssue(message, "error", path, suggestion))
        self.is_valid = False

    def add_warning(self, message: str, path: Optional[str] = None, suggestion: Optional[str] = None) -> None:
        self.warnings.append(ValidationIssue(message, "warning", path, suggestion))

    def merge(self, other: ValidationReport) -> None:
        """Merge another report into this one."""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.is_valid = self.is_valid and other.is_valid
        # Merge statistics (simple update)
        self.statistics.update(other.statistics)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)


# ---- Part 3: Coefficient Validation ------------------------------------

class CoefficientValidator:
    """
    Validates a dictionary of ARKit coefficients (blendshape values).
    Supports FAST, STANDARD, STRICT levels.
    """
    def __init__(self):
        self._known_channels = ARKIT_SET

    def validate(
        self,
        coeffs: Dict[str, float],
        level: ValidationLevel = ValidationLevel.STANDARD,
        allow_extra_channels: bool = False,
    ) -> ValidationReport:
        """
        Validate ARKit coefficients.

        Args:
            coeffs: dict mapping channel name to float value.
            level: strictness level.
            allow_extra_channels: if False, unknown channels are errors (STRICT) or warnings (STANDARD).

        Returns:
            ValidationReport
        """
        report = ValidationReport(is_valid=True)

        if not isinstance(coeffs, dict):
            report.add_error("Coefficients must be a dict")
            return report

        if not coeffs:
            report.add_warning("Coefficients dict is empty")

        # Stats
        stats = {
            "total_channels": len(coeffs),
            "known_channels": 0,
            "unknown_channels": 0,
            "invalid_values": 0,
            "out_of_range_values": 0,
            "duplicate_keys": 0,  # not applicable for dict, but keep
        }

        # Check for duplicate keys (dict already prevents, but we'll be safe)
        # Actually dict can't have duplicates, so skip.

        # Process each channel
        for key, value in coeffs.items():
            # Check key type
            if not isinstance(key, str):
                report.add_error(f"Channel name must be string, got {type(key).__name__}", path=str(key))
                stats["invalid_values"] += 1
                continue

            # Check if known
            is_known = key in self._known_channels
            if is_known:
                stats["known_channels"] += 1
            else:
                stats["unknown_channels"] += 1
                if not allow_extra_channels:
                    if level == ValidationLevel.STRICT:
                        report.add_error(f"Unknown ARKit channel: '{key}'", path=key)
                    elif level == ValidationLevel.STANDARD:
                        report.add_warning(f"Unknown ARKit channel: '{key}'", path=key)
                    # FAST ignores unknown channels

            # Check value type and range
            if not isinstance(value, (int, float)):
                report.add_error(f"Value for '{key}' must be numeric, got {type(value).__name__}", path=key)
                stats["invalid_values"] += 1
                continue

            if not math.isfinite(value):
                report.add_error(f"Value for '{key}' is not finite ({value})", path=key)
                stats["invalid_values"] += 1
                continue

            if value < MIN_CHANNEL_VALUE or value > MAX_CHANNEL_VALUE:
                report.add_error(
                    f"Value for '{key}' ({value}) out of range [{MIN_CHANNEL_VALUE}, {MAX_CHANNEL_VALUE}]",
                    path=key
                )
                stats["out_of_range_values"] += 1
                # In FAST, we could just warn, but we'll keep error for all levels
                # Actually, we might make it a warning in FAST? But the design says FAST only basic checks.
                # We'll keep as error to be safe, but could be configurable.

        # Extra checks for STRICT
        if level == ValidationLevel.STRICT:
            # Warn about channels that are zero? Not needed.
            # Check for unrealistic combinations? Not implemented.
            pass

        # Set statistics
        report.statistics = stats

        return report


# ---- Part 4: Mapping Validation -----------------------------------------

class MappingValidator:
    """
    Validates a mapping table that defines how ARKit channels map to rig targets.
    """
    def __init__(self):
        self._known_arkit_channels = ARKIT_SET

    def validate(
        self,
        mapping_def: Dict[str, Any],
        level: ValidationLevel = ValidationLevel.STANDARD,
        allowed_target_pattern: Optional[re.Pattern] = VALID_TARGET_NAME_PATTERN,
    ) -> ValidationReport:
        """
        Validate a mapping definition.

        Expected structure:
            {
                "jawOpen": [
                    {"target": "Jaw_Open", "multiplier": 1.0, "offset": 0.0, "invert": False, "clamp_min": 0.0, "clamp_max": 1.0},
                    ...
                ],
                ...
            }
        Or simplified:
            {
                "jawOpen": {"target": "Jaw_Open", "multiplier": 0.5}
            }
        Or even:
            {
                "jawOpen": "Jaw_Open"   # shorthand for multiplier 1.0
            }

        Returns:
            ValidationReport
        """
        report = ValidationReport(is_valid=True)

        if not isinstance(mapping_def, dict):
            report.add_error("Mapping definition must be a dict")
            return report

        if not mapping_def:
            report.add_warning("Mapping definition is empty")

        stats = {
            "source_count": len(mapping_def),
            "target_count": 0,
            "duplicate_targets": 0,
            "unknown_sources": 0,
            "known_sources": 0,
            "rules_with_zero_multiplier": 0,
            "targets_found": set(),
        }

        # First, collect all targets to detect duplicates
        all_targets = set()
        seen_targets_per_source = set()  # for duplicates within same source

        for source, rules_data in mapping_def.items():
            # Validate source name
            if not isinstance(source, str):
                report.add_error(f"Source name must be string, got {type(source).__name__}")
                stats["unknown_sources"] += 1
                continue

            if source not in self._known_arkit_channels:
                if level != ValidationLevel.FAST:
                    report.add_warning(f"Source '{source}' is not a known ARKit channel", path=source)
                stats["unknown_sources"] += 1
            else:
                stats["known_sources"] += 1

            # Normalize rules_data to a list of rule dicts
            if isinstance(rules_data, str):
                rules = [{"target": rules_data}]
            elif isinstance(rules_data, dict):
                rules = [rules_data]
            elif isinstance(rules_data, list):
                rules = rules_data
            else:
                report.add_error(f"Invalid rule definition for source '{source}': expected str, dict, or list", path=source)
                continue

            if not rules:
                report.add_warning(f"Source '{source}' has no rules", path=source)
                continue

            # Process each rule
            for idx, rule in enumerate(rules):
                if not isinstance(rule, dict):
                    report.add_error(f"Rule {idx} for source '{source}' must be a dict", path=f"{source}.rule[{idx}]")
                    continue

                # Get target name
                target = rule.get("target")
                if not target:
                    report.add_error(f"Rule {idx} for source '{source}' missing 'target' field", path=f"{source}.rule[{idx}]")
                    continue
                if not isinstance(target, str):
                    report.add_error(f"Target for rule {idx} of source '{source}' must be string", path=f"{source}.rule[{idx}].target")
                    continue
                if not target.strip():
                    report.add_error(f"Target name in rule {idx} of source '{source}' is empty", path=f"{source}.rule[{idx}].target")
                    continue
                # Validate target name format (if pattern provided)
                if allowed_target_pattern and not allowed_target_pattern.match(target):
                    report.add_warning(
                        f"Target name '{target}' does not match expected pattern",
                        path=f"{source}.rule[{idx}].target",
                        suggestion="Use only alphanumeric, underscore, dot, or colon, and start with letter/underscore"
                    )

                # Check for duplicate target within same source
                if target in seen_targets_per_source:
                    report.add_warning(
                        f"Duplicate target '{target}' within source '{source}' (duplicate rules)",
                        path=f"{source}.rule[{idx}].target"
                    )
                else:
                    seen_targets_per_source.add(target)
                    if target in all_targets:
                        stats["duplicate_targets"] += 1
                        # Only warn if STRICT or STANDARD? We'll warn always.
                        report.add_warning(
                            f"Target '{target}' appears in multiple sources (may cause accumulation)",
                            path=f"{source}.rule[{idx}].target"
                        )
                    all_targets.add(target)

                # Validate numeric fields
                for field_name in ["multiplier", "offset", "clamp_min", "clamp_max"]:
                    if field_name in rule:
                        val = rule[field_name]
                        if not isinstance(val, (int, float)):
                            report.add_error(
                                f"'{field_name}' in rule {idx} of source '{source}' must be numeric",
                                path=f"{source}.rule[{idx}].{field_name}"
                            )
                # Check multiplier
                multiplier = rule.get("multiplier", 1.0)
                if not isinstance(multiplier, (int, float)) or not math.isfinite(multiplier):
                    report.add_error(
                        f"Multiplier must be finite number, got {multiplier}",
                        path=f"{source}.rule[{idx}].multiplier"
                    )
                else:
                    if multiplier == 0.0:
                        stats["rules_with_zero_multiplier"] += 1
                        report.add_warning(
                            f"Multiplier is zero for rule {idx} of source '{source}' – rule will have no effect",
                            path=f"{source}.rule[{idx}].multiplier"
                        )
                    # If clamp_min > clamp_max
                    clamp_min = rule.get("clamp_min", 0.0)
                    clamp_max = rule.get("clamp_max", 1.0)
                    if isinstance(clamp_min, (int, float)) and isinstance(clamp_max, (int, float)):
                        if clamp_min > clamp_max:
                            report.add_error(
                                f"clamp_min ({clamp_min}) > clamp_max ({clamp_max})",
                                path=f"{source}.rule[{idx}]"
                            )

                # Check invert (boolean)
                invert = rule.get("invert", False)
                if not isinstance(invert, bool):
                    report.add_error(
                        f"'invert' must be boolean, got {type(invert).__name__}",
                        path=f"{source}.rule[{idx}].invert"
                    )

                # Add to target count
                stats["target_count"] += 1

            # Clear per-source seen targets for next source
            seen_targets_per_source.clear()

        # Additional checks for STRICT
        if level == ValidationLevel.STRICT:
            # Check for circular mapping? Not feasible in simple dict.
            # Could check for sources that are also targets? Not a problem.

            # Check if any ARKit channel is missing? Not required.

            # Warn if no mapping for some common channels? Optional.
            pass

        # Finalize statistics
        stats["unique_targets"] = len(all_targets)
        report.statistics = stats

        return report


# ---- Part 5: Preset Validation ------------------------------------------

class PresetValidator:
    """
    Validates a pose preset (a collection of mappings, settings, and metadata).
    """
    def __init__(self):
        self._mapping_validator = MappingValidator()
        self._coeff_validator = CoefficientValidator()

    def validate(
        self,
        preset: Dict[str, Any],
        level: ValidationLevel = ValidationLevel.STANDARD,
    ) -> ValidationReport:
        """
        Validate a preset definition.

        Expected structure:
            {
                "uuid": "123e4567-e89b-12d3-a456-426614174000",
                "version": "1.0.0",
                "name": "My Preset",
                "description": "Optional",
                "tags": ["facial", "happy"],
                "mapping": { ... },          # mapping definition
                "settings": { ... },         # e.g., normalize, mirror
                "metadata": { ... }          # extra info
            }
        """
        report = ValidationReport(is_valid=True)

        if not isinstance(preset, dict):
            report.add_error("Preset must be a dict")
            return report

        # Check required fields
        required = ["uuid", "version", "name", "mapping"]
        for field in required:
            if field not in preset:
                report.add_error(f"Preset missing required field: '{field}'")
            else:
                # Basic type checks
                if field == "uuid" and not isinstance(preset["uuid"], str):
                    report.add_error(f"uuid must be string, got {type(preset['uuid']).__name__}")
                elif field == "version" and not isinstance(preset["version"], str):
                    report.add_error(f"version must be string, got {type(preset['version']).__name__}")
                elif field == "name" and not isinstance(preset["name"], str):
                    report.add_error(f"name must be string, got {type(preset['name']).__name__}")
                elif field == "mapping" and not isinstance(preset["mapping"], dict):
                    report.add_error(f"mapping must be dict, got {type(preset['mapping']).__name__}")

        # Validate UUID format if present
        if "uuid" in preset and isinstance(preset["uuid"], str):
            try:
                uuid.UUID(preset["uuid"])
            except ValueError:
                report.add_error(f"Invalid UUID format: '{preset['uuid']}'")

        # Validate version format (e.g., semantic versioning)
        if "version" in preset and isinstance(preset["version"], str):
            if not re.match(r'^\d+\.\d+\.\d+$', preset["version"]):
                report.add_warning(f"Version '{preset['version']}' does not follow semantic versioning (MAJOR.MINOR.PATCH)")

        # Validate tags if present
        if "tags" in preset:
            if not isinstance(preset["tags"], list):
                report.add_error(f"tags must be list, got {type(preset['tags']).__name__}")
            else:
                for tag in preset["tags"]:
                    if not isinstance(tag, str):
                        report.add_error(f"Tag must be string, got {type(tag).__name__}")

        # Validate mapping
        if "mapping" in preset:
            mapping_report = self._mapping_validator.validate(preset["mapping"], level=level)
            report.merge(mapping_report)

        # Validate settings (optional)
        if "settings" in preset:
            if not isinstance(preset["settings"], dict):
                report.add_error("settings must be dict")
            else:
                # Check known settings keys
                allowed_settings = {"normalize", "mirror", "pre_process", "post_process"}
                for key in preset["settings"]:
                    if key not in allowed_settings:
                        report.add_warning(f"Unknown setting key: '{key}'")

        # Validate metadata (optional)
        if "metadata" in preset:
            if not isinstance(preset["metadata"], dict):
                report.add_error("metadata must be dict")
            # No further checks

        return report


# ---- Part 6: Pose Validation --------------------------------------------

class PoseValidator:
    """
    Validates a single pose (a set of ARKit coefficients with metadata).
    """
    def __init__(self):
        self._coeff_validator = CoefficientValidator()

    def validate(
        self,
        pose: Dict[str, Any],
        level: ValidationLevel = ValidationLevel.STANDARD,
    ) -> ValidationReport:
        """
        Validate a pose.

        Expected structure:
            {
                "name": "Smile",
                "coefficients": {"jawOpen": 0.5, ...},
                "timestamp": 1234567890.0,
                "metadata": {...}
            }
        """
        report = ValidationReport(is_valid=True)

        if not isinstance(pose, dict):
            report.add_error("Pose must be a dict")
            return report

        # Check required fields
        if "name" not in pose:
            report.add_error("Pose missing 'name' field")
        elif not isinstance(pose["name"], str):
            report.add_error(f"Pose name must be string, got {type(pose['name']).__name__}")

        if "coefficients" not in pose:
            report.add_error("Pose missing 'coefficients' field")
        else:
            coeffs = pose["coefficients"]
            if not isinstance(coeffs, dict):
                report.add_error(f"coefficients must be dict, got {type(coeffs).__name__}")
            else:
                # Validate coefficients using CoefficientValidator
                coeff_report = self._coeff_validator.validate(coeffs, level=level)
                report.merge(coeff_report)

        # Optional timestamp
        if "timestamp" in pose:
            ts = pose["timestamp"]
            if not isinstance(ts, (int, float)):
                report.add_error(f"timestamp must be numeric, got {type(ts).__name__}")
            elif not math.isfinite(ts):
                report.add_error(f"timestamp is not finite: {ts}")

        # Optional metadata
        if "metadata" in pose:
            if not isinstance(pose["metadata"], dict):
                report.add_error("metadata must be dict")

        # Extra strict checks
        if level == ValidationLevel.STRICT:
            # Check if pose has all zero coefficients (warn)
            if "coefficients" in pose:
                coeffs = pose["coefficients"]
                if all(v == 0.0 for v in coeffs.values()):
                    report.add_warning("Pose has all coefficients set to zero – this is a neutral pose")

        return report


# ---- Part 7: Calibration Validation ------------------------------------

class CalibrationValidator:
    """
    Validates calibration data used for remapping and normalization.
    """
    def __init__(self):
        self._coeff_validator = CoefficientValidator()

    def validate(
        self,
        calibration: Dict[str, Any],
        level: ValidationLevel = ValidationLevel.STANDARD,
    ) -> ValidationReport:
        """
        Validate calibration data.

        Expected structure:
            {
                "neutral": {"jawOpen": 0.0, ...},   # neutral pose coefficients
                "max_values": {"jawOpen": 1.0, ...}, # maximum expected values
                "offsets": {"jawOpen": 0.0, ...},    # additive offsets
                "scale_factors": {"jawOpen": 1.0, ...}, # scale factors
                "ranges": {"jawOpen": [0.0, 1.0], ...}, # min/max ranges
                "metadata": {...}
            }
        """
        report = ValidationReport(is_valid=True)

        if not isinstance(calibration, dict):
            report.add_error("Calibration must be a dict")
            return report

        # Check required fields (all optional but we validate if present)
        for field in ["neutral", "max_values", "offsets", "scale_factors", "ranges"]:
            if field in calibration:
                data = calibration[field]
                if not isinstance(data, dict):
                    report.add_error(f"'{field}' must be a dict")
                    continue
                # Validate each entry as coefficients (but we don't require known channels)
                # Use coefficient validator with allow_extra_channels=True
                coeff_report = self._coeff_validator.validate(
                    data,
                    level=level,
                    allow_extra_channels=True
                )
                # But we need to merge, but we want to allow extra channels, so we filter out unknown errors?
                # For calibration, unknown channels are likely fine.
                # We can suppress unknown channel errors by adjusting.
                # Easiest: manually check values without known channel check.
                for key, value in data.items():
                    if not isinstance(key, str):
                        report.add_error(f"Key in '{field}' must be string, got {type(key).__name__}")
                        continue
                    if not isinstance(value, (int, float)):
                        report.add_error(f"Value for '{key}' in '{field}' must be numeric, got {type(value).__name__}")
                    elif not math.isfinite(value):
                        report.add_error(f"Value for '{key}' in '{field}' is not finite")
                # Additional checks
                if field == "ranges":
                    for key, range_vals in data.items():
                        if not isinstance(range_vals, (list, tuple)) or len(range_vals) != 2:
                            report.add_error(f"Range for '{key}' must be a list/tuple of two numbers")
                        else:
                            lo, hi = range_vals
                            if not isinstance(lo, (int, float)) or not isinstance(hi, (int, float)):
                                report.add_error(f"Range for '{key}' contains non-numeric values")
                            elif lo > hi:
                                report.add_error(f"Range for '{key}' has min > max ({lo} > {hi})")

        # Additional strict checks
        if level == ValidationLevel.STRICT:
            # Check that scale_factors are positive if present
            if "scale_factors" in calibration:
                for key, val in calibration["scale_factors"].items():
                    if val <= 0:
                        report.add_warning(f"Scale factor for '{key}' is non-positive ({val})")

        return report


# ---- Part 8: Runtime Validation -----------------------------------------

class RuntimeValidator:
    """
    Validates a runtime frame (typically coming from Live Link or recorded data).
    This is similar to coefficient validation but may include additional frame-level checks.
    """
    def __init__(self):
        self._coeff_validator = CoefficientValidator()

    def validate(
        self,
        frame: Dict[str, Any],
        level: ValidationLevel = ValidationLevel.STANDARD,
        require_timestamp: bool = False,
    ) -> ValidationReport:
        """
        Validate a runtime frame.

        Frame may contain:
            - "coefficients": dict of ARKit values
            - "timestamp": float (optional)
            - "metadata": dict (optional)
        Or it may be just the coefficients dict.
        """
        report = ValidationReport(is_valid=True)

        # If frame is a dict with "coefficients", use that
        if isinstance(frame, dict) and "coefficients" in frame:
            coeffs = frame.get("coefficients")
            if not isinstance(coeffs, dict):
                report.add_error("Frame 'coefficients' must be a dict")
                return report
            # Validate coefficients
            coeff_report = self._coeff_validator.validate(coeffs, level=level)
            report.merge(coeff_report)

            # Check timestamp if required
            if require_timestamp and "timestamp" not in frame:
                report.add_error("Frame missing 'timestamp' field")
            elif "timestamp" in frame:
                ts = frame["timestamp"]
                if not isinstance(ts, (int, float)):
                    report.add_error(f"timestamp must be numeric, got {type(ts).__name__}")
                elif not math.isfinite(ts):
                    report.add_error(f"timestamp is not finite: {ts}")

            # Check metadata
            if "metadata" in frame and not isinstance(frame["metadata"], dict):
                report.add_error("metadata must be dict")
        else:
            # Assume frame is directly coefficients dict
            coeff_report = self._coeff_validator.validate(frame, level=level)
            report.merge(coeff_report)

        return report


# ---- Part 9: Diagnostics & Reports --------------------------------------

class DiagnosticsCollector:
    """
    Collects diagnostic information from validation runs for reporting.
    """
    def __init__(self):
        self.reset()

    def reset(self):
        self.total_validations = 0
        self.successful_validations = 0
        self.failed_validations = 0
        self.total_errors = 0
        self.total_warnings = 0
        self.by_type = {
            "coefficients": {"total": 0, "valid": 0, "errors": 0, "warnings": 0},
            "mapping": {"total": 0, "valid": 0, "errors": 0, "warnings": 0},
            "preset": {"total": 0, "valid": 0, "errors": 0, "warnings": 0},
            "pose": {"total": 0, "valid": 0, "errors": 0, "warnings": 0},
            "calibration": {"total": 0, "valid": 0, "errors": 0, "warnings": 0},
            "runtime": {"total": 0, "valid": 0, "errors": 0, "warnings": 0},
        }

    def record(self, validation_type: str, report: ValidationReport):
        self.total_validations += 1
        if report.is_valid:
            self.successful_validations += 1
        else:
            self.failed_validations += 1
        self.total_errors += len(report.errors)
        self.total_warnings += len(report.warnings)

        if validation_type in self.by_type:
            stats = self.by_type[validation_type]
            stats["total"] += 1
            if report.is_valid:
                stats["valid"] += 1
            stats["errors"] += len(report.errors)
            stats["warnings"] += len(report.warnings)

    def get_summary(self) -> Dict[str, Any]:
        return {
            "total_validations": self.total_validations,
            "successful": self.successful_validations,
            "failed": self.failed_validations,
            "total_errors": self.total_errors,
            "total_warnings": self.total_warnings,
            "by_type": self.by_type,
        }


# ---- Part 10: Statistics ------------------------------------------------

class StatisticsCollector:
    """
    Collects aggregate statistics about validated data (e.g., average values, ranges).
    This is separate from diagnostics; it's about the data itself.
    """
    def __init__(self):
        self.reset()

    def reset(self):
        self.coeff_stats = {
            "min": {},
            "max": {},
            "avg": {},
            "count": {},
            "sum": {},
        }

    def record_coefficients(self, coeffs: Dict[str, float]):
        for key, val in coeffs.items():
            if key not in self.coeff_stats["count"]:
                self.coeff_stats["count"][key] = 0
                self.coeff_stats["sum"][key] = 0.0
                self.coeff_stats["min"][key] = float('inf')
                self.coeff_stats["max"][key] = float('-inf')
            self.coeff_stats["count"][key] += 1
            self.coeff_stats["sum"][key] += val
            if val < self.coeff_stats["min"][key]:
                self.coeff_stats["min"][key] = val
            if val > self.coeff_stats["max"][key]:
                self.coeff_stats["max"][key] = val

    def get_stats(self) -> Dict[str, Any]:
        result = {}
        for key in self.coeff_stats["count"]:
            count = self.coeff_stats["count"][key]
            result[key] = {
                "count": count,
                "min": self.coeff_stats["min"][key] if count > 0 else None,
                "max": self.coeff_stats["max"][key] if count > 0 else None,
                "avg": self.coeff_stats["sum"][key] / count if count > 0 else None,
            }
        return result


# ---- Part 11: Public API (ARKitValidator) -------------------------------

class ARKitValidator:
    """
    The main validator class that orchestrates all validation checks.
    It combines coefficient, mapping, preset, pose, calibration, and runtime validators.
    Also provides diagnostics and statistics collection.
    """
    def __init__(self, collect_stats: bool = True):
        """
        Args:
            collect_stats: whether to accumulate statistics across validation calls.
        """
        self._coeff_validator = CoefficientValidator()
        self._mapping_validator = MappingValidator()
        self._preset_validator = PresetValidator()
        self._pose_validator = PoseValidator()
        self._calibration_validator = CalibrationValidator()
        self._runtime_validator = RuntimeValidator()
        self._diagnostics = DiagnosticsCollector()
        self._statistics = StatisticsCollector() if collect_stats else None

    def validate_coefficients(
        self,
        coeffs: Dict[str, float],
        level: ValidationLevel = ValidationLevel.STANDARD,
        allow_extra_channels: bool = False,
    ) -> ValidationReport:
        """
        Validate ARKit coefficients.
        """
        report = self._coeff_validator.validate(coeffs, level, allow_extra_channels)
        self._diagnostics.record("coefficients", report)
        if self._statistics:
            self._statistics.record_coefficients(coeffs)
        return report

    def validate_mapping(
        self,
        mapping_def: Dict[str, Any],
        level: ValidationLevel = ValidationLevel.STANDARD,
        allowed_target_pattern: Optional[re.Pattern] = VALID_TARGET_NAME_PATTERN,
    ) -> ValidationReport:
        """
        Validate a mapping definition.
        """
        report = self._mapping_validator.validate(mapping_def, level, allowed_target_pattern)
        self._diagnostics.record("mapping", report)
        return report

    def validate_preset(
        self,
        preset: Dict[str, Any],
        level: ValidationLevel = ValidationLevel.STANDARD,
    ) -> ValidationReport:
        """
        Validate a preset.
        """
        report = self._preset_validator.validate(preset, level)
        self._diagnostics.record("preset", report)
        return report

    def validate_pose(
        self,
        pose: Dict[str, Any],
        level: ValidationLevel = ValidationLevel.STANDARD,
    ) -> ValidationReport:
        """
        Validate a pose.
        """
        report = self._pose_validator.validate(pose, level)
        self._diagnostics.record("pose", report)
        # Optionally record coefficients if present
        if self._statistics and "coefficients" in pose:
            self._statistics.record_coefficients(pose["coefficients"])
        return report

    def validate_calibration(
        self,
        calibration: Dict[str, Any],
        level: ValidationLevel = ValidationLevel.STANDARD,
    ) -> ValidationReport:
        """
        Validate calibration data.
        """
        report = self._calibration_validator.validate(calibration, level)
        self._diagnostics.record("calibration", report)
        return report

    def validate_runtime(
        self,
        frame: Dict[str, Any],
        level: ValidationLevel = ValidationLevel.STANDARD,
        require_timestamp: bool = False,
    ) -> ValidationReport:
        """
        Validate a runtime frame.
        """
        report = self._runtime_validator.validate(frame, level, require_timestamp)
        self._diagnostics.record("runtime", report)
        # Record coefficients if present
        if self._statistics:
            coeffs = frame.get("coefficients") if isinstance(frame, dict) else frame
            if isinstance(coeffs, dict):
                self._statistics.record_coefficients(coeffs)
        return report

    def get_diagnostics(self) -> Dict[str, Any]:
        """Return diagnostic summary."""
        return self._diagnostics.get_summary()

    def get_statistics(self) -> Dict[str, Any]:
        """Return statistics about validated coefficients (if enabled)."""
        if self._statistics:
            return self._statistics.get_stats()
        return {}

    def reset_diagnostics(self):
        """Reset diagnostics."""
        self._diagnostics.reset()

    def reset_statistics(self):
        """Reset statistics."""
        if self._statistics:
            self._statistics.reset()

    def reset_all(self):
        """Reset both diagnostics and statistics."""
        self.reset_diagnostics()
        self.reset_statistics()

    def report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive report combining diagnostics and statistics.
        """
        return {
            "diagnostics": self.get_diagnostics(),
            "statistics": self.get_statistics(),
        }


# ---- Public API (exported names) ----------------------------------------

__all__ = [
    # Main class
    "ARKitValidator",
    # Enums and dataclasses
    "ValidationLevel",
    "ValidationIssue",
    "ValidationReport",
    # Exceptions
    "ARKitValidationError",
    "ValidationConfigurationError",
    "ValidationDataError",
    # Individual validators (if needed externally)
    "CoefficientValidator",
    "MappingValidator",
    "PresetValidator",
    "PoseValidator",
    "CalibrationValidator",
    "RuntimeValidator",
]
