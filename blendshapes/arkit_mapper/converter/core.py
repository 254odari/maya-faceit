"""
core.py

Main ARKitConverter class.
"""

from collections import defaultdict
from typing import DefaultDict, Dict, Iterable, List, Optional, Set, Tuple, Union

from .enums import MergeMode
from .models import CompiledMapping, ConverterStatistics
from ..calibration import ARKitCalibration, arkit_calibration
from ..channels import ARKitChannel
from ..mapping import ARKitMapping, MappingResult, RigTarget
from ..validator import ARKitValidator, ValidationReport, arkit_validator
from ..exceptions import ARKitMappingError, ConversionError


class ARKitConverter:
    """
    High-performance ARKit conversion engine.

    Input:  ARKit coefficients
    Output: Rig BlendShape weights
    """

    def __init__(
        self,
        calibration: Optional[ARKitCalibration] = None,
        validator: Optional[ARKitValidator] = None,
        merge_mode: MergeMode = MergeMode.MAX,
        auto_validate: bool = True,
    ) -> None:
        self._calibration = calibration or arkit_calibration
        self._validator = validator or arkit_validator
        self._merge_mode = merge_mode
        self._auto_validate = auto_validate

        # Original mapping table
        self._mappings: Dict[ARKitChannel, ARKitMapping] = {}

        # Runtime compiled cache
        self._compiled: Dict[ARKitChannel, CompiledMapping] = {}

        # Reverse lookup
        self._reverse: DefaultDict[str, List[Tuple[ARKitChannel, RigTarget]]] = defaultdict(list)

        # Statistics
        self._statistics = ConverterStatistics()

        # Compilation state
        self._compiled_valid = False

    # ------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------

    @property
    def calibration(self) -> ARKitCalibration:
        return self._calibration

    @property
    def validator(self) -> ARKitValidator:
        return self._validator

    @property
    def merge_mode(self) -> MergeMode:
        return self._merge_mode

    @merge_mode.setter
    def merge_mode(self, mode: MergeMode) -> None:
        self._merge_mode = mode

    @property
    def statistics(self) -> ConverterStatistics:
        return self._statistics

    @property
    def compiled(self) -> bool:
        return self._compiled_valid

    @property
    def mapping_count(self) -> int:
        return len(self._mappings)

    @property
    def compiled_count(self) -> int:
        return len(self._compiled)

    # ------------------------------------------------------------
    # Compilation
    # ------------------------------------------------------------

    def compile(
        self,
        mappings: Iterable[ARKitMapping],
        validate: Optional[bool] = None,
    ) -> Optional[ValidationReport]:
        """Compile ARKit mappings into optimized runtime caches."""
        self.clear_cache()

        for mapping in mappings:
            if not mapping.enabled:
                continue
            if mapping.channel in self._mappings:
                raise ARKitMappingError(f"Duplicate mapping for {mapping.channel.value}")
            self._mappings[mapping.channel] = mapping

        perform_validation = self._auto_validate if validate is None else validate
        report = None

        if perform_validation:
            report = self._validator.validate(self._mappings)
            self._statistics.validation_runs += 1
            self._statistics.errors += report.errors
            self._statistics.warnings += report.warnings
            if not report.success:
                raise ARKitMappingError("ARKit mapping validation failed.")

        self._build_compiled_cache()
        self._build_reverse_cache()
        self._compiled_valid = True

        return report

    def _build_compiled_cache(self) -> None:
        self._compiled.clear()
        for channel, mapping in self._mappings.items():
            enabled_targets = [t for t in mapping.targets if t.enabled]
            self._compiled[channel] = CompiledMapping(
                channel=channel,
                mapping=mapping,
                targets=enabled_targets,
            )

    def _build_reverse_cache(self) -> None:
        self._reverse.clear()
        for channel, compiled in self._compiled.items():
            for target in compiled.targets:
                self._reverse[target.name].append((channel, target))

    def invalidate_cache(self) -> None:
        self._compiled_valid = False

    def clear_cache(self) -> None:
        self._mappings.clear()
        self._compiled.clear()
        self._reverse.clear()
        self._compiled_valid = False

    def ensure_compiled(self) -> None:
        if not self._compiled_valid:
            raise ConversionError("Converter has not been compiled.")

    def rebuild(self, validate: bool = True) -> Optional[ValidationReport]:
        return self.compile(self._mappings.values(), validate=validate)

    # ------------------------------------------------------------
    # Channel Conversion
    # ------------------------------------------------------------

    def convert_channel(
        self,
        channel: ARKitChannel,
        coefficient: float,
        calibrate: bool = True,
    ) -> Dict[str, float]:
        self.ensure_compiled()
        compiled = self.compiled_mapping(channel)
        value = float(coefficient)

        if calibrate:
            value = self._calibration.evaluate(channel, value)
            self._statistics.calibration_calls += 1

        value = max(0.0, min(1.0, value))
        self._statistics.converted_channels += 1

        weights: Dict[str, float] = {}
        for target in compiled.targets:
            target_value = target.evaluate(value)
            target_value = max(target.minimum, min(target.maximum, target_value))
            weights[target.name] = target_value
            self._statistics.converted_targets += 1

        return weights

    def convert_channels(
        self,
        coefficients: Dict[ARKitChannel, float],
        calibrate: bool = True,
    ) -> Dict[str, float]:
        self.ensure_compiled()
        output: Dict[str, float] = {}
        for channel, value in coefficients.items():
            output.update(self.convert_channel(channel, value, calibrate=calibrate))
        return output

    def compiled_mapping(self, channel: ARKitChannel) -> CompiledMapping:
        self.ensure_compiled()
        try:
            self._statistics.cache_hits += 1
            return self._compiled[channel]
        except KeyError:
            self._statistics.cache_misses += 1
            raise ConversionError(f"No compiled mapping for {channel.value}") from None

    # ------------------------------------------------------------
    # Frame Conversion
    # ------------------------------------------------------------

    def convert_frame(
        self,
        coefficients: Dict[ARKitChannel, float],
        calibrate: bool = True,
        clamp_output: bool = True,
    ) -> MappingResult:
        self.ensure_compiled()
        result = MappingResult()
        merged: DefaultDict[str, List[float]] = defaultdict(list)
        self._statistics.converted_frames += 1

        for channel, coefficient in coefficients.items():
            if not self.has_channel(channel):
                result.missing_channels.append(channel.value)
                continue
            weights = self.convert_channel(channel, coefficient, calibrate=calibrate)
            result.mapped_channels += 1
            for target_name, value in weights.items():
                merged[target_name].append(value)

        for target_name, values in merged.items():
            final_value = self.merge_weights(values)
            if clamp_output:
                final_value = max(0.0, min(1.0, final_value))
            result.weights[target_name] = final_value
            result.mapped_targets += 1

        result.success = len(result.missing_channels) == 0
        return result

    def has_channel(self, channel: ARKitChannel) -> bool:
        return channel in self._compiled

    # ------------------------------------------------------------
    # Weight Merging
    # ------------------------------------------------------------

    def merge_weights(self, values: List[float]) -> float:
        if not values:
            return 0.0
        self._statistics.merge_operations += 1

        if self._merge_mode is MergeMode.MAX:
            return max(values)
        if self._merge_mode is MergeMode.ADD:
            return sum(values)
        if self._merge_mode is MergeMode.AVERAGE:
            return sum(values) / len(values)
        if self._merge_mode is MergeMode.OVERRIDE:
            return values[-1]

        return max(values)

    def clamp(self, value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
        return max(minimum, min(maximum, value))

    # ------------------------------------------------------------
    # Reverse Conversion
    # ------------------------------------------------------------

    def reverse_convert_channel(
        self,
        rig_target: str,
        weight: float,
        calibrated: bool = True,
    ) -> Dict[ARKitChannel, float]:
        self.ensure_compiled()
        if rig_target not in self._reverse:
            raise ConversionError(f"Unknown rig target '{rig_target}'.")

        weight = self.clamp(weight)
        output: Dict[ARKitChannel, float] = {}
        entries = self._reverse[rig_target]
        self._statistics.reverse_conversions += 1

        for channel, target in entries:
            coefficient = self._inverse_target(target, weight)
            if calibrated:
                coefficient = self._inverse_calibration(channel, coefficient)
            coefficient = self.clamp(coefficient)
            output[channel] = coefficient

        return output

    def _inverse_target(self, target: RigTarget, value: float) -> float:
        if abs(target.multiplier) < 1e-8:
            raise ConversionError(f"RigTarget '{target.name}' has zero multiplier.")
        coefficient = (value - target.offset) / target.multiplier
        return self.clamp(coefficient, target.minimum, target.maximum)

    def _inverse_calibration(self, channel: ARKitChannel, value: float) -> float:
        cal = self._calibration.get_profile().calibration(channel)
        if not cal.enabled:
            return value

        value -= cal.offset
        if abs(cal.multiplier) > 1e-8:
            value /= cal.multiplier

        curve = cal.curve
        if curve.name == "LINEAR":
            return self.clamp(value)
        if curve.name == "EASE_IN":
            value = max(value, 0.0)
            return self.clamp(value ** 0.5)
        if curve.name == "EASE_OUT":
            value = self.clamp(value)
            return self.clamp(1.0 - (1.0 - value) ** 0.5)
        if curve.name == "EASE_IN_OUT":
            # Numerical approximation
            guess = value
            for _ in range(8):
                estimate = cal.evaluate(guess)
                error = estimate - value
                guess -= error * 0.5
                guess = self.clamp(guess)
            return guess

        return self.clamp(value)

    # ------------------------------------------------------------
    # Statistics & Utilities
    # ------------------------------------------------------------

    def channel_count(self) -> int:
        return len(self._compiled)

    def target_count(self) -> int:
        self.ensure_compiled()
        targets: Set[str] = set()
        for compiled in self._compiled.values():
            for target in compiled.targets:
                targets.add(target.name)
        return len(targets)

    def reverse_target_count(self) -> int:
        return len(self._reverse)

    def coverage(self) -> float:
        return (self.mapping_count / ARKitChannel.count()) * 100.0

    def statistics_report(self) -> dict:
        report = self._statistics.serialize()
        report.update({
            "compiled": self._compiled_valid,
            "merge_mode": self._merge_mode.value,
            "mapping_count": self.mapping_count,
            "compiled_channels": self.channel_count(),
            "rig_targets": self.target_count(),
            "reverse_targets": self.reverse_target_count(),
            "coverage": self.coverage(),
        })
        return report

    # ------------------------------------------------------------
    # Dunder Methods
    # ------------------------------------------------------------

    def __len__(self) -> int:
        return len(self._compiled)

    def __contains__(self, channel: ARKitChannel) -> bool:
        return channel in self._compiled

    def __getitem__(self, channel: ARKitChannel) -> CompiledMapping:
        return self.compiled_mapping(channel)

    def __iter__(self):
        return iter(self._compiled.values())

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"compiled={self._compiled_valid}, "
            f"channels={self.channel_count()}, "
            f"targets={self.target_count()}, "
            f"coverage={self.coverage():.2f}%, "
            f"merge_mode='{self._merge_mode.value}')"
        )


# ============================================================
# Singleton
# ============================================================

arkit_converter = ARKitConverter()