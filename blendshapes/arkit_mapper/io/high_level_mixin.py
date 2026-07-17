# -*- coding: utf-8 -*-
"""High-level APIs mixin."""

import copy
from pathlib import Path
from typing import Any, Union, Dict, Optional
from .models import AutosavePolicy, IOConfig, IOResult
from .enums import IOStatus, FileFormat
from .enums import CompressionType

class HighLevelMixin:
    """Mixin providing high-level load/save APIs."""

    def load(self, path: Union[str, Path], *, auto_migrate: bool = True) -> Any:
        data = self.smart_load(path)
        if auto_migrate and isinstance(data, dict) and self.is_versioned_file(data) and self.requires_migration(data):
            data = self.auto_migrate(data)
        return data

    def save(self, path: Union[str, Path], data: Any, *, compression: Optional[CompressionType] = None,
             versioned: bool = True) -> IOResult:
        payload = data
        if versioned and isinstance(payload, dict):
            payload = copy.deepcopy(payload)
            self.embed_version_metadata(payload)
        return self.smart_save(path, payload, compression=compression)

    def import_file(self, path: Union[str, Path]) -> Any:
        return self.load(path)

    def export_file(self, path: Union[str, Path], data: Any) -> IOResult:
        return self.save(path, data)

    def load_project(self, path: Union[str, Path]) -> Dict[str, Any]:
        project = self.load(path)
        if not isinstance(project, dict):
            raise TypeError("Project must be a dictionary.")
        return project

    def save_project(self, path: Union[str, Path], project: Dict[str, Any]) -> IOResult:
        return self.save(path, project, versioned=True)

    def load_preset(self, path: Union[str, Path]) -> Dict[str, Any]:
        preset = self.load(path)
        if not isinstance(preset, dict):
            raise TypeError("Preset must be a dictionary.")
        return preset

    def save_preset(self, path: Union[str, Path], preset: Dict[str, Any]) -> IOResult:
        return self.save(path, preset, versioned=True)

    def load_runtime_snapshot(self, path: Union[str, Path]) -> Dict[str, Any]:
        snapshot = self.load(path)
        if not isinstance(snapshot, dict):
            raise TypeError("Invalid runtime snapshot.")
        return snapshot

    def save_runtime_snapshot(self, path: Union[str, Path], snapshot: Dict[str, Any]) -> IOResult:
        return self.save(path, snapshot, versioned=True)

    def load_mapping(self, path: Union[str, Path]) -> Dict[str, Any]:
        mapping = self.load(path)
        if not isinstance(mapping, dict):
            raise TypeError("Invalid mapping.")
        return mapping

    def save_mapping(self, path: Union[str, Path], mapping: Dict[str, Any]) -> IOResult:
        return self.save(path, mapping, versioned=True)

    def duplicate_file(self, source: Union[str, Path], destination: Union[str, Path]) -> IOResult:
        data = self.load(source)
        return self.save(destination, data)

    def convert_file(self, source: Union[str, Path], destination: Union[str, Path]) -> IOResult:
        data = self.load(source)
        return self.save(destination, data)

    def remember_recent_file(self, path: Union[str, Path]) -> None:
        self._recent_file = self.normalize_path(path)