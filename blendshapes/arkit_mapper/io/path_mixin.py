# -*- coding: utf-8 -*-
"""Path utilities for IOManager."""

import os
import shutil
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Union, Optional

from .models import FileMetadata, FileFormat


class PathMixin:
    """Mixin providing file system path utilities."""

    def normalize_path(self, path: Union[str, Path]) -> Path:
        return Path(path).expanduser().resolve()

    def exists(self, path: Union[str, Path]) -> bool:
        return self.normalize_path(path).exists()

    def is_file(self, path: Union[str, Path]) -> bool:
        return self.normalize_path(path).is_file()

    def is_directory(self, path: Union[str, Path]) -> bool:
        return self.normalize_path(path).is_dir()

    def create_directory(self, directory: Union[str, Path], *, parents: bool = True, exist_ok: bool = True) -> Path:
        directory = self.normalize_path(directory)
        directory.mkdir(parents=parents, exist_ok=exist_ok)
        return directory

    def ensure_parent_directory(self, filepath: Union[str, Path]) -> Path:
        filepath = self.normalize_path(filepath)
        if self.config.create_directories:
            filepath.parent.mkdir(parents=True, exist_ok=True)
        return filepath

    def delete(self, path: Union[str, Path], *, missing_ok: bool = True) -> bool:
        path = self.normalize_path(path)
        if not path.exists():
            return missing_ok
        path.unlink()
        return True

    def rename(self, source: Union[str, Path], destination: Union[str, Path]) -> Path:
        source = self.normalize_path(source)
        destination = self.ensure_parent_directory(destination)
        return source.rename(destination)

    def copy(self, source: Union[str, Path], destination: Union[str, Path]) -> Path:
        source = self.normalize_path(source)
        destination = self.ensure_parent_directory(destination)
        shutil.copy2(source, destination)
        return destination

    def move(self, source: Union[str, Path], destination: Union[str, Path]) -> Path:
        source = self.normalize_path(source)
        destination = self.ensure_parent_directory(destination)
        shutil.move(str(source), str(destination))
        return destination

    def temporary_file(self, *, suffix: str = ".tmp", prefix: str = "arkit_", directory: Optional[Union[str, Path]] = None) -> Path:
        if directory is not None:
            directory = self.normalize_path(directory)
        fd, filename = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=directory)
        os.close(fd)
        return Path(filename)

    def file_size(self, path: Union[str, Path]) -> int:
        return self.normalize_path(path).stat().st_size

    def modification_time(self, path: Union[str, Path]) -> datetime:
        return datetime.fromtimestamp(self.normalize_path(path).stat().st_mtime)

    def creation_time(self, path: Union[str, Path]) -> datetime:
        return datetime.fromtimestamp(self.normalize_path(path).stat().st_ctime)

    def extension(self, path: Union[str, Path]) -> str:
        return self.normalize_path(path).suffix.lower()

    def stem(self, path: Union[str, Path]) -> str:
        return self.normalize_path(path).stem

    def filename(self, path: Union[str, Path]) -> str:
        return self.normalize_path(path).name

    def parent_directory(self, path: Union[str, Path]) -> Path:
        return self.normalize_path(path).parent

    def relative_path(self, path: Union[str, Path], start: Union[str, Path]) -> Path:
        return Path(os.path.relpath(self.normalize_path(path), self.normalize_path(start)))

    def file_metadata(self, path: Union[str, Path]) -> FileMetadata:
        path = self.normalize_path(path)
        return FileMetadata(
            path=path,
            format=self.detect_format(path),
            size=path.stat().st_size,
            created=datetime.fromtimestamp(path.stat().st_ctime),
            modified=datetime.fromtimestamp(path.stat().st_mtime),
        )

    def touch(self, path: Union[str, Path]) -> Path:
        path = self.ensure_parent_directory(path)
        path.touch(exist_ok=True)
        return path

    def resolve_unique_path(self, path: Union[str, Path]) -> Path:
        path = self.normalize_path(path)
        if not path.exists():
            return path
        stem = path.stem
        suffix = path.suffix
        parent = path.parent
        counter = 1
        while True:
            candidate = parent / f"{stem}_{counter}{suffix}"
            if not candidate.exists():
                return candidate
            counter += 1