# -*- coding: utf-8 -*-
"""Preset I/O mixin for ARKit Mapper."""

from pathlib import Path
from typing import Union, Dict, Any, Optional

from .models import IOResult, FileFormat


class PresetIO:
    """Mixin providing I/O for presets (rig weight dictionaries)."""

    def load_preset(
        self,
        path: Union[str, Path],
        *,
        validate: bool = True,
    ) -> Dict[str, float]:
        """
        Load a preset from a file.

        Supports JSON, YAML, CSV.
        """
        path = self.normalize_path(path)
        fmt = self.detect_format(path)

        if fmt == FileFormat.JSON:
            data = self.load_json(path, validate=validate)
        elif fmt == FileFormat.YAML:
            data = self.load_yaml(path, validate=validate)
        elif fmt == FileFormat.CSV:
            rows = self.load_csv(path, validate=validate, dict_rows=True)
            data = {}
            for row in rows:
                data[row["rig_name"]] = float(row["value"])
        else:
            raise ValueError(f"Unsupported preset format: {fmt.value}")

        return {k: float(v) for k, v in data.items()}

    def save_preset(
        self,
        path: Union[str, Path],
        preset: Dict[str, float],
        *,
        format: Optional[FileFormat] = None,
    ) -> IOResult:
        """
        Save a preset to a file.
        """
        path = self.normalize_path(path)
        if format is None:
            format = self.detect_format(path)

        if format == FileFormat.JSON:
            return self.save_json(path, preset)
        elif format == FileFormat.YAML:
            return self.save_yaml(path, preset)
        elif format == FileFormat.CSV:
            rows = [{"rig_name": k, "value": v} for k, v in preset.items()]
            return self.save_csv(path, rows, dict_rows=True, fieldnames=["rig_name", "value"])
        else:
            raise ValueError(f"Unsupported preset format: {format.value}")

    def import_preset(
        self,
        source: Union[str, Path],
    ) -> Dict[str, float]:
        """Alias for load_preset."""
        return self.load_preset(source)

    def export_preset(
        self,
        preset: Dict[str, float],
        destination: Union[str, Path],
    ) -> IOResult:
        """Alias for save_preset."""
        return self.save_preset(destination, preset)

    def validate_preset(self, preset: Dict[str, float]) -> bool:
        """Validate a preset."""
        if not isinstance(preset, dict):
            raise TypeError("Preset must be a dictionary.")
        for rig, value in preset.items():
            if not isinstance(rig, str):
                raise TypeError("Rig names must be strings.")
            try:
                value = float(value)
            except Exception:
                raise ValueError(f"Invalid value for '{rig}': {value}")
            if value < 0.0 or value > 1.0:
                raise ValueError(f"Value out of range for '{rig}': {value}")
        return True

    def validate_preset_file(self, path: Union[str, Path]) -> bool:
        """Validate a preset file."""
        preset = self.load_preset(path)
        return self.validate_preset(preset)

    def merge_presets(
        self,
        *presets: Dict[str, float],
    ) -> Dict[str, float]:
        """Merge multiple presets. Later ones overwrite earlier."""
        merged = {}
        for preset in presets:
            merged.update(preset)
        return merged

    def blend_presets(
        self,
        preset_a: Dict[str, float],
        preset_b: Dict[str, float],
        weight: float = 0.5,
    ) -> Dict[str, float]:
        """Blend two presets."""
        weight = max(0.0, min(1.0, weight))
        result = {}
        keys = set(preset_a) | set(preset_b)
        for key in keys:
            a = preset_a.get(key, 0.0)
            b = preset_b.get(key, 0.0)
            result[key] = a * (1.0 - weight) + b * weight
        return result

    def preset_statistics(self, preset: Dict[str, float]) -> Dict[str, Any]:
        """Generate statistics for a preset."""
        values = list(preset.values())
        if not values:
            return {"count": 0, "minimum": 0.0, "maximum": 0.0, "average": 0.0, "active": 0}
        return {
            "count": len(values),
            "minimum": min(values),
            "maximum": max(values),
            "average": sum(values) / len(values),
            "active": sum(1 for v in values if v > 0.0),
        }