# -*- coding: utf-8 -*-
"""Project I/O mixin for ARKit Mapper."""
import pickle
from pathlib import Path
from datetime import datetime
from typing import Union, Dict, Any, Optional

from .models import ProjectSnapshot, IOResult, FileFormat
from .constants import IO_VERSION


class ProjectIO:
    """Mixin providing I/O for complete ARKit Mapper projects."""

    def save_project(
        self,
        path: Union[str, Path],
        project: Union[ProjectSnapshot, Dict[str, Any]],
        *,
        format: Optional[FileFormat] = None,
    ) -> IOResult:
        """
        Save a complete project.
        """
        path = self.normalize_path(path)
        if format is None:
            format = self.detect_format(path)

        if isinstance(project, ProjectSnapshot):
            data = {
                "version": project.version,
                "created": project.created.isoformat(),
                "mappings": project.mappings,
                "presets": project.presets,
                "statistics": project.statistics,
                "runtime": project.runtime,
                "metadata": project.metadata,
            }
        else:
            data = dict(project)

        data.setdefault("version", IO_VERSION)
        data.setdefault("created", datetime.now().isoformat())
        data.setdefault("mappings", {})
        data.setdefault("presets", {})
        data.setdefault("statistics", {})
        data.setdefault("runtime", {})
        data.setdefault("metadata", {})

        if format == FileFormat.JSON:
            return self.save_json(path, data)
        elif format == FileFormat.YAML:
            return self.save_yaml(path, data)
        elif format == FileFormat.BINARY:
            return self.save_binary(path, data)
        else:
            raise ValueError(f"Unsupported project format: {format.value}")

    def load_project(
        self,
        path: Union[str, Path],
        *,
        validate: bool = True,
    ) -> ProjectSnapshot:
        """
        Load a complete project.
        """
        path = self.normalize_path(path)
        fmt = self.detect_format(path)

        if fmt == FileFormat.JSON:
            data = self.load_json(path, validate=validate)
        elif fmt == FileFormat.YAML:
            data = self.load_yaml(path, validate=validate)
        elif fmt == FileFormat.BINARY:
            data = self.load_binary(path)
        else:
            raise ValueError(f"Unsupported project format: {fmt.value}")

        if validate:
            self.validate_project(data)

        return ProjectSnapshot(
            version=data.get("version", IO_VERSION),
            created=datetime.fromisoformat(data.get("created", datetime.now().isoformat())),
            mappings=data.get("mappings", {}),
            presets=data.get("presets", {}),
            statistics=data.get("statistics", {}),
            runtime=data.get("runtime", {}),
            metadata=data.get("metadata", {}),
        )

    def export_project(
        self,
        project: Union[ProjectSnapshot, Dict[str, Any]],
        destination: Union[str, Path],
    ) -> IOResult:
        """Alias for save_project."""
        return self.save_project(destination, project)

    def import_project(
        self,
        source: Union[str, Path],
    ) -> ProjectSnapshot:
        """Alias for load_project."""
        return self.load_project(source)

    def validate_project(
        self,
        project: Union[ProjectSnapshot, Dict[str, Any]],
    ) -> bool:
        """Validate a project structure."""
        if isinstance(project, ProjectSnapshot):
            project = {
                "version": project.version,
                "created": project.created,
                "mappings": project.mappings,
                "presets": project.presets,
                "statistics": project.statistics,
                "runtime": project.runtime,
                "metadata": project.metadata,
            }
        required = ("version", "created", "mappings", "presets", "statistics", "runtime", "metadata")
        for key in required:
            if key not in project:
                raise ValueError(f"Project missing '{key}'.")
        return True

    def validate_project_file(self, path: Union[str, Path]) -> bool:
        """Validate a project file."""
        project = self.load_project(path)
        return self.validate_project(project)

    def clone_project(self, project: ProjectSnapshot) -> ProjectSnapshot:
        """Deep-copy a project."""
        return pickle.loads(pickle.dumps(project))

    def project_statistics(self, project: Union[ProjectSnapshot, Dict[str, Any]]) -> Dict[str, Any]:
        """Generate statistics about a project."""
        if isinstance(project, ProjectSnapshot):
            mappings = project.mappings
            presets = project.presets
            runtime = project.runtime
            statistics = project.statistics
            metadata = project.metadata
        else:
            mappings = project.get("mappings", {})
            presets = project.get("presets", {})
            runtime = project.get("runtime", {})
            statistics = project.get("statistics", {})
            metadata = project.get("metadata", {})

        return {
            "mapping_count": len(mappings),
            "preset_count": len(presets),
            "runtime_entries": len(runtime),
            "statistics_entries": len(statistics),
            "metadata_entries": len(metadata),
        }

    def merge_projects(self, *projects: ProjectSnapshot) -> ProjectSnapshot:
        """Merge multiple projects. Later projects overwrite earlier values."""
        merged = ProjectSnapshot()
        for project in projects:
            merged.mappings.update(project.mappings)
            merged.presets.update(project.presets)
            merged.statistics.update(project.statistics)
            merged.runtime.update(project.runtime)
            merged.metadata.update(project.metadata)
            merged.version = project.version
            merged.created = project.created
        return merged

    def compare_projects(
        self,
        project_a: ProjectSnapshot,
        project_b: ProjectSnapshot,
    ) -> Dict[str, Any]:
        """Compare two projects."""
        differences = {}
        for field in ("mappings", "presets", "statistics", "runtime", "metadata"):
            left = getattr(project_a, field, {})
            right = getattr(project_b, field, {})
            if left != right:
                differences[field] = {"left": left, "right": right}
        return differences