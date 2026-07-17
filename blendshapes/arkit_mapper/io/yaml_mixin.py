# -*- coding: utf-8 -*-
"""YAML serialization mixin."""

import time
from pathlib import Path
from typing import Any, Union, Optional, Dict, Callable

try:
    import yaml
except ImportError:
    yaml = None

from .models import IOResult, FileFormat, IOStatus
from .enums import FileFormat, FileMetadata, ChecksumAlgorithm

class YAMLMixin:
    """Mixin providing YAML serialization methods."""

    def load_yaml(self, path: Union[str, Path], *, validate: bool = True) -> Any:
        if yaml is None:
            raise RuntimeError("PyYAML is not installed.")
        path = self.normalize_path(path)
        if validate:
            self.validate_yaml(path)
        start = time.perf_counter()
        try:
            with path.open("r", encoding=self.config.encoding) as fp:
                data = yaml.safe_load(fp)
            self._record_operation(True, path, FileFormat.YAML, time.perf_counter() - start)
            return data
        except Exception as e:
            self._record_operation(False, path, FileFormat.YAML, time.perf_counter() - start, str(e))
            raise

    def save_yaml(self, path: Union[str, Path], data: Any, *,
                  default_flow_style: bool = False, sort_keys: bool = False) -> IOResult:
        if yaml is None:
            raise RuntimeError("PyYAML is not installed.")
        path = self.normalize_path(path)
        start = time.perf_counter()
        try:
            self.validate_save_path(path, FileFormat.YAML)
            if self.config.atomic_writes:
                self.atomic_save_yaml(path, data, default_flow_style=default_flow_style, sort_keys=sort_keys)
            else:
                with path.open("w", encoding=self.config.encoding) as fp:
                    yaml.safe_dump(data, fp, default_flow_style=default_flow_style,
                                   sort_keys=sort_keys, allow_unicode=True)
            return self._make_result(True, path, FileFormat.YAML, time.perf_counter() - start)
        except Exception as e:
            return self._make_result(False, path, FileFormat.YAML, time.perf_counter() - start, str(e))

    def loads_yaml(self, text: str) -> Any:
        if yaml is None:
            raise RuntimeError("PyYAML is not installed.")
        try:
            return yaml.safe_load(text)
        except Exception as e:
            raise ValueError("Invalid YAML string.") from e

    def dumps_yaml(self, data: Any, *, default_flow_style: bool = False, sort_keys: bool = False) -> str:
        if yaml is None:
            raise RuntimeError("PyYAML is not installed.")
        try:
            return yaml.safe_dump(data, default_flow_style=default_flow_style,
                                  sort_keys=sort_keys, allow_unicode=True)
        except Exception as e:
            raise ValueError("Unable to serialize YAML.") from e

    def append_yaml(self, path: Union[str, Path], value: Any) -> IOResult:
        if self.exists(path):
            data = self.load_yaml(path)
        else:
            data = []
        if not isinstance(data, list):
            raise TypeError("YAML root must be a list.")
        data.append(value)
        return self.save_yaml(path, data)

    def update_yaml(self, path: Union[str, Path], values: Dict[str, Any]) -> IOResult:
        if self.exists(path):
            data = self.load_yaml(path)
        else:
            data = {}
        if not isinstance(data, dict):
            raise TypeError("YAML root must be a dictionary.")
        data.update(values)
        return self.save_yaml(path, data)

    def yaml_size(self, data: Any) -> int:
        return len(self.dumps_yaml(data).encode(self.config.encoding))

    def read_yaml_metadata(self, path: Union[str, Path]) -> FileMetadata:
        self.validate_yaml(path)
        metadata = self.file_metadata(path)
        metadata.checksum = self.file_checksum(path, algorithm=ChecksumAlgorithm.SHA256)
        return metadata

    def register_yaml_serializer(self, serializer: Callable) -> None:
        if not hasattr(self, "_yaml_serializers"):
            self._yaml_serializers = {}
        self._yaml_serializers["serializer"] = serializer

    def register_yaml_deserializer(self, deserializer: Callable) -> None:
        if not hasattr(self, "_yaml_deserializers"):
            self._yaml_deserializers = {}
        self._yaml_deserializers["deserializer"] = deserializer

    def yaml_to_json(self, yaml_path: Union[str, Path], json_path: Union[str, Path]) -> IOResult:
        data = self.load_yaml(yaml_path)
        return self.save_json(json_path, data)

    def json_to_yaml(self, json_path: Union[str, Path], yaml_path: Union[str, Path]) -> IOResult:
        data = self.load_json(json_path)
        return self.save_yaml(yaml_path, data)