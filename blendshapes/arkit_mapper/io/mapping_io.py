# -*- coding: utf-8 -*-
"""Mapping I/O mixin for ARKit Mapper."""

from pathlib import Path
from typing import Union, List, Optional, Dict, Any, Sequence

from .models import IOResult, FileFormat
from .enums import IOStatus, ChecksumAlgorithm
from ..mapping import ARKitMapping

class MappingIO:
    """Mixin providing I/O for ARKit mappings."""

    def load_mapping(
        self,
        path: Union[str, Path],
        *,
        validate: bool = True,
    ) -> List["ARKitMapping"]:
        """
        Load ARKit mappings from a file.

        Supports JSON, YAML, CSV.
        """
        from ..mapping import ARKitMapping

        path = self.normalize_path(path)
        fmt = self.detect_format(path)

        if fmt == FileFormat.JSON:
            raw = self.load_json(path, validate=validate)
        elif fmt == FileFormat.YAML:
            raw = self.load_yaml(path, validate=validate)
        elif fmt == FileFormat.CSV:
            raw = self.load_csv(path, validate=validate, dict_rows=True)
        else:
            raise ValueError(f"Unsupported mapping format: {fmt.value}")

        if raw is None:
            return []

        mappings = []
        for item in raw:
            if hasattr(ARKitMapping, "from_dict"):
                mappings.append(ARKitMapping.from_dict(item))
            else:
                mappings.append(ARKitMapping(**item))
        return mappings

    def save_mapping(
        self,
        path: Union[str, Path],
        mappings: Sequence["ARKitMapping"],
        *,
        format: Optional[FileFormat] = None,
    ) -> IOResult:
        """
        Save ARKit mappings to a file.
        """
        from ..mapping import ARKitMapping

        path = self.normalize_path(path)
        if format is None:
            format = self.detect_format(path)

        data = []
        for mapping in mappings:
            if hasattr(mapping, "to_dict"):
                data.append(mapping.to_dict())
            else:
                data.append(vars(mapping))

        if format == FileFormat.JSON:
            return self.save_json(path, data)
        elif format == FileFormat.YAML:
            return self.save_yaml(path, data)
        elif format == FileFormat.CSV:
            # Convert to list of dicts for CSV
            rows = []
            for item in data:
                row = {}
                for key, value in item.items():
                    row[key] = str(value) if not isinstance(value, (int, float, bool)) else value
                rows.append(row)
            return self.save_csv(path, rows, dict_rows=True, fieldnames=list(rows[0].keys()) if rows else None)
        else:
            raise ValueError(f"Unsupported mapping format: {format.value}")

    def export_mapping(
        self,
        mappings: Sequence["ARKitMapping"],
        destination: Union[str, Path],
    ) -> IOResult:
        """Alias for save_mapping."""
        return self.save_mapping(destination, mappings)

    def import_mapping(
        self,
        source: Union[str, Path],
    ) -> List["ARKitMapping"]:
        """Alias for load_mapping."""
        return self.load_mapping(source)

    def merge_mappings(
        self,
        *mapping_sets: Sequence["ARKitMapping"],
    ) -> List["ARKitMapping"]:
        """
        Merge multiple mapping collections by ARKit channel name.
        Later collections override earlier ones.
        """
        merged = {}
        for collection in mapping_sets:
            for mapping in collection:
                merged[mapping.arkit_name] = mapping
        return list(merged.values())

    def validate_mapping_file(self, path: Union[str, Path]) -> bool:
        """Validate a mapping file."""
        mappings = self.load_mapping(path)
        if not mappings:
            return False
        arkit_names = set()
        rig_names = set()
        for mapping in mappings:
            if mapping.arkit_name in arkit_names:
                raise ValueError(f"Duplicate ARKit channel: {mapping.arkit_name}")
            if mapping.rig_name in rig_names:
                raise ValueError(f"Duplicate rig target: {mapping.rig_name}")
            arkit_names.add(mapping.arkit_name)
            rig_names.add(mapping.rig_name)
        return True

    def mapping_statistics(
        self,
        mappings: Sequence["ARKitMapping"],
    ) -> Dict[str, Any]:
        """Generate statistics about a collection of mappings."""
        enabled = sum(1 for m in mappings if m.enabled)
        disabled = len(mappings) - enabled
        groups = {}
        for mapping in mappings:
            group = getattr(mapping, "category", "Default")
            groups[group] = groups.get(group, 0) + 1
        return {
            "total": len(mappings),
            "enabled": enabled,
            "disabled": disabled,
            "groups": groups,
        }