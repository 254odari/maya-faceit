# -*- coding: utf-8 -*-
"""Runtime I/O mixin for ARKit Mapper."""
import pickle
from pathlib import Path
from typing import Union, Any, Dict, Optional
from datetime import datetime, timedelta
from .models import IOResult, FileFormat
from .constants import IO_VERSION, IO_SCHEMA_VERSION

class RuntimeIO:
    """Mixin providing I/O for runtime snapshots."""

    def load_runtime_snapshot(
        self,
        path: Union[str, Path],
        *,
        validate: bool = True,
    ) -> Dict[str, Any]:
        """
        Load a runtime snapshot from a file.
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
            raise ValueError(f"Unsupported runtime snapshot format: {fmt.value}")

        return data

    def save_runtime_snapshot(
        self,
        path: Union[str, Path],
        runtime: Any,
        *,
        format: Optional[FileFormat] = None,
        include_statistics: bool = True,
        include_callbacks: bool = False,
        include_metadata: bool = True,
    ) -> IOResult:
        """
        Save a runtime snapshot.

        The runtime object may be a RuntimeManager, RuntimeSession,
        or any object implementing to_dict().
        """
        path = self.normalize_path(path)
        if format is None:
            format = self.detect_format(path)

        if hasattr(runtime, "to_dict"):
            data = runtime.to_dict()
        elif isinstance(runtime, dict):
            data = dict(runtime)
        else:
            data = vars(runtime).copy()

        if not include_callbacks:
            data.pop("callbacks", None)
            data.pop("_callbacks", None)
            data.pop("frame_callbacks", None)
            data.pop("update_callbacks", None)

        if not include_statistics:
            data.pop("statistics", None)
            data.pop("_statistics", None)

        if include_metadata:
            data["_snapshot"] = {
                "created": datetime.now().isoformat(),
                "version": IO_VERSION,
                "type": "runtime",
            }

        if format == FileFormat.JSON:
            return self.save_json(path, data)
        elif format == FileFormat.YAML:
            return self.save_yaml(path, data)
        elif format == FileFormat.BINARY:
            return self.save_binary(path, data)
        else:
            raise ValueError(f"Unsupported runtime snapshot format: {format.value}")

    def export_runtime(
        self,
        runtime: Any,
        destination: Union[str, Path],
    ) -> IOResult:
        """Alias for save_runtime_snapshot."""
        return self.save_runtime_snapshot(destination, runtime)

    def import_runtime(
        self,
        source: Union[str, Path],
    ) -> Dict[str, Any]:
        """Alias for load_runtime_snapshot."""
        return self.load_runtime_snapshot(source)

    def clone_runtime_snapshot(self, runtime: Any) -> Dict[str, Any]:
        """Deep-copy a runtime snapshot."""
        if hasattr(runtime, "to_dict"):
            runtime = runtime.to_dict()
        return pickle.loads(pickle.dumps(runtime))

    def validate_runtime_snapshot(self, snapshot: Dict[str, Any]) -> bool:
        """Validate a runtime snapshot structure."""
        if not isinstance(snapshot, dict):
            raise TypeError("Runtime snapshot must be a dictionary.")
        metadata = snapshot.get("_snapshot")
        if metadata is None:
            raise ValueError("Missing runtime metadata.")
        if "version" not in metadata:
            raise ValueError("Snapshot version missing.")
        return True

    def validate_runtime_snapshot_file(self, path: Union[str, Path]) -> bool:
        """Validate a runtime snapshot file."""
        snapshot = self.load_runtime_snapshot(path)
        return self.validate_runtime_snapshot(snapshot)

    def compare_runtime_snapshots(
        self,
        snapshot_a: Dict[str, Any],
        snapshot_b: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Compare two runtime snapshots."""
        keys_a = set(snapshot_a.keys())
        keys_b = set(snapshot_b.keys())
        added = keys_b - keys_a
        removed = keys_a - keys_b
        common = keys_a & keys_b
        modified = [k for k in common if snapshot_a[k] != snapshot_b[k]]
        unchanged = [k for k in common if snapshot_a[k] == snapshot_b[k]]
        return {
            "added": sorted(added),
            "removed": sorted(removed),
            "modified": sorted(modified),
            "unchanged": sorted(unchanged),
        }