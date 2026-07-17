# -*- coding: utf-8 -*-
"""Atomic write mixin for IOManager."""
import csv
import os
import shutil
import tempfile
import json
from contextlib import contextmanager
from pathlib import Path
from typing import Union, Any, Optional
from .models import IOResult
from .enums import FileFormat


class AtomicMixin:
    """Mixin providing atomic write operations."""

    @contextmanager
    def atomic_write(self, destination: Union[str, Path], *, mode: str = "wb", encoding: Optional[str] = None,
                     suffix: str = ".tmp"):
        destination = self.normalize_path(destination)
        self.ensure_parent_directory(destination)
        encoding = encoding or self.config.encoding
        fd, temp_name = tempfile.mkstemp(dir=str(destination.parent), suffix=suffix)
        os.close(fd)
        temp_path = Path(temp_name)
        try:
            kwargs = {}
            if "b" not in mode:
                kwargs["encoding"] = encoding
            with temp_path.open(mode, **kwargs) as stream:
                yield stream
            shutil.copystat(destination, temp_path) if destination.exists() else None
            os.replace(temp_path, destination)
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise

    def atomic_save_bytes(self, path: Union[str, Path], data: bytes) -> IOResult:
        with self.atomic_write(path, mode="wb") as fp:
            fp.write(data)
        return self._make_result(True, Path(path), FileFormat.BINARY, 0.0)

    def atomic_save_text(self, path: Union[str, Path], text: str, *, encoding: Optional[str] = None) -> IOResult:
        with self.atomic_write(path, mode="w", encoding=encoding) as fp:
            fp.write(text)
        return self._make_result(True, Path(path), FileFormat.BINARY, 0.0)

    def atomic_save_json(self, path: Union[str, Path], data: Any, *, indent: int = 4, **kwargs) -> IOResult:
        with self.atomic_write(path, mode="w") as fp:
            json.dump(data, fp, indent=indent, **kwargs)
        return self._make_result(True, Path(path), FileFormat.JSON, 0.0)

    def atomic_save_yaml(self, path: Union[str, Path], data: Any, **kwargs) -> IOResult:
        import yaml
        with self.atomic_write(path, mode="w") as fp:
            yaml.safe_dump(data, fp, allow_unicode=True, **kwargs)
        return self._make_result(True, Path(path), FileFormat.YAML, 0.0)

    def atomic_save_csv(self, path: Union[str, Path], rows, *, fieldnames=None, dict_rows=False) -> IOResult:
        with self.atomic_write(path, mode="w") as fp:
            if dict_rows:
                writer = csv.DictWriter(fp, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            else:
                writer = csv.writer(fp)
                writer.writerows(rows)
        return self._make_result(True, Path(path), FileFormat.CSV, 0.0)

    def atomic_save_binary(self, path: Union[str, Path], obj: Any, *, protocol: Optional[int] = None) -> IOResult:
        binary = self.serialize(obj, protocol=protocol)
        return self.atomic_save_bytes(path, binary)

    def atomic_replace(self, source: Union[str, Path], destination: Union[str, Path]) -> None:
        os.replace(self.normalize_path(source), self.normalize_path(destination))