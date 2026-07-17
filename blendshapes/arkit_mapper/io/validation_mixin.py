# -*- coding: utf-8 -*-
"""Validation mixin for IOManager."""

import csv
import json
import os
from pathlib import Path
from typing import Union, Sequence

from .constants import DEFAULT_ENCODING
from .enums import FileFormat


class ValidationMixin:
    """Mixin providing file validation methods."""

    _FORMAT_EXTENSIONS = {
        FileFormat.JSON: {".json"},
        FileFormat.YAML: {".yaml", ".yml"},
        FileFormat.CSV: {".csv"},
        FileFormat.BINARY: {".bin"},
        FileFormat.PICKLE: {".pickle", ".pkl"},
        FileFormat.ZIP: {".zip", ".gz"},
    }

    def detect_format(self, path: Union[str, Path]) -> FileFormat:
        ext = self.extension(path)
        for fmt, exts in self._FORMAT_EXTENSIONS.items():
            if ext in exts:
                return fmt
        return FileFormat.UNKNOWN

    def validate_exists(self, path: Union[str, Path]) -> None:
        if not self.exists(path):
            raise FileNotFoundError(f"File does not exist: {path}")

    def validate_file(self, path: Union[str, Path]) -> None:
        self.validate_exists(path)
        if not self.is_file(path):
            raise IsADirectoryError(f"Not a file: {path}")

    def validate_directory(self, path: Union[str, Path]) -> None:
        self.validate_exists(path)
        if not self.is_directory(path):
            raise NotADirectoryError(f"Not a directory: {path}")

    def validate_extension(self, path: Union[str, Path], expected: Union[FileFormat, Sequence[FileFormat]]) -> FileFormat:
        detected = self.detect_format(path)
        if isinstance(expected, FileFormat):
            expected = [expected]
        if detected not in expected:
            names = ", ".join(f.value for f in expected)
            raise ValueError(f"Expected {names}, got {detected.value}")
        return detected

    def validate_readable(self, path: Union[str, Path]) -> None:
        self.validate_file(path)
        if not os.access(path, os.R_OK):
            raise PermissionError(f"File is not readable: {path}")

    def validate_writable(self, path: Union[str, Path]) -> None:
        path = self.normalize_path(path)
        parent = path.parent
        if not parent.exists():
            if self.config.create_directories:
                parent.mkdir(parents=True, exist_ok=True)
            else:
                raise FileNotFoundError(f"Directory does not exist: {parent}")
        if not os.access(parent, os.W_OK):
            raise PermissionError(f"Directory not writable: {parent}")

    def validate_not_empty(self, path: Union[str, Path]) -> None:
        self.validate_file(path)
        if self.file_size(path) == 0:
            raise ValueError(f"File is empty: {path}")

    def validate_json(self, path: Union[str, Path]) -> None:
        self.validate_extension(path, FileFormat.JSON)
        self.validate_readable(path)
        try:
            with open(path, "r", encoding=self.config.encoding) as fp:
                json.load(fp)
        except Exception as e:
            raise ValueError(f"Invalid JSON: {path}") from e

    def validate_yaml(self, path: Union[str, Path]) -> None:
        try:
            import yaml
        except ImportError:
            raise RuntimeError("PyYAML is not installed.")
        self.validate_extension(path, FileFormat.YAML)
        self.validate_readable(path)
        try:
            with open(path, "r", encoding=self.config.encoding) as fp:
                yaml.safe_load(fp)
        except Exception as e:
            raise ValueError(f"Invalid YAML: {path}") from e

    def validate_csv(self, path: Union[str, Path]) -> None:
        self.validate_extension(path, FileFormat.CSV)
        self.validate_readable(path)
        try:
            with open(path, newline="", encoding=self.config.encoding) as fp:
                reader = csv.reader(fp)
                for _ in reader:
                    pass
        except Exception as e:
            raise ValueError(f"Invalid CSV: {path}") from e

    def validate_binary(self, path: Union[str, Path]) -> None:
        self.validate_extension(path, (FileFormat.BINARY, FileFormat.PICKLE))
        self.validate_readable(path)

    def validate_save_path(self, path: Union[str, Path], file_format: FileFormat) -> Path:
        path = self.ensure_parent_directory(path)
        self.validate_writable(path)
        self.validate_extension(path, file_format)
        return path

    def validate(self, path: Union[str, Path]) -> bool:
        fmt = self.detect_format(path)
        if fmt == FileFormat.JSON:
            self.validate_json(path)
        elif fmt == FileFormat.YAML:
            self.validate_yaml(path)
        elif fmt == FileFormat.CSV:
            self.validate_csv(path)
        elif fmt in (FileFormat.BINARY, FileFormat.PICKLE):
            self.validate_binary(path)
        else:
            raise ValueError(f"Unsupported format: {path}")
        return True

    def is_valid(self, path: Union[str, Path]) -> bool:
        try:
            return self.validate(path)
        except Exception:
            return False