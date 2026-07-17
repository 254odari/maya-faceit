# -*- coding: utf-8 -*-
"""JSON serialization mixin."""

import json
import time
from pathlib import Path
from typing import Any, Union, Optional, Callable, Dict

from .constants import DEFAULT_ENCODING, DEFAULT_INDENT
from .models import FileMetadata, IOResult, IOStatus, FileFormat
from .enums import ChecksumAlgorithm


class JSONMixin:
    """Mixin providing JSON serialization methods."""

    def load_json(self, path: Union[str, Path], *, validate: bool = True) -> Any:
        path = self.normalize_path(path)
        start = time.perf_counter()
        if validate:
            self.validate_json(path)
        try:
            with path.open("r", encoding=self.config.encoding) as fp:
                data = json.load(fp)
            self._record_operation(True, path, FileFormat.JSON, time.perf_counter() - start)
            return data
        except Exception as e:
            self._record_operation(False, path, FileFormat.JSON, time.perf_counter() - start, str(e))
            raise

    def save_json(self, path: Union[str, Path], data: Any, *, indent: Optional[int] = None,
                  sort_keys: bool = False, ensure_ascii: bool = False) -> IOResult:
        path = self.normalize_path(path)
        indent = indent if indent is not None else self.config.indent
        start = time.perf_counter()
        try:
            self.validate_save_path(path, FileFormat.JSON)
            if self.config.atomic_writes:
                self.atomic_save_json(path, data, indent=indent, sort_keys=sort_keys, ensure_ascii=ensure_ascii)
            else:
                with path.open("w", encoding=self.config.encoding) as fp:
                    json.dump(data, fp, indent=indent, sort_keys=sort_keys, ensure_ascii=ensure_ascii)
            return self._make_result(True, path, FileFormat.JSON, time.perf_counter() - start)
        except Exception as e:
            return self._make_result(False, path, FileFormat.JSON, time.perf_counter() - start, str(e))

    def loads_json(self, text: str) -> Any:
        try:
            return json.loads(text)
        except Exception as e:
            raise ValueError("Invalid JSON string.") from e

    def dumps_json(self, data: Any, *, indent: Optional[int] = None, sort_keys: bool = False,
                   ensure_ascii: bool = False) -> str:
        indent = indent if indent is not None else self.config.indent
        try:
            return json.dumps(data, indent=indent, sort_keys=sort_keys, ensure_ascii=ensure_ascii)
        except Exception as e:
            raise ValueError("Unable to serialize JSON.") from e

    def append_json(self, path: Union[str, Path], value: Any) -> IOResult:
        if self.exists(path):
            data = self.load_json(path)
        else:
            data = []
        if not isinstance(data, list):
            raise TypeError("JSON root must be a list.")
        data.append(value)
        return self.save_json(path, data)

    def update_json(self, path: Union[str, Path], values: Dict[str, Any]) -> IOResult:
        if self.exists(path):
            data = self.load_json(path)
        else:
            data = {}
        if not isinstance(data, dict):
            raise TypeError("JSON root must be an object.")
        data.update(values)
        return self.save_json(path, data)

    def pretty_print_json(self, data: Any) -> str:
        return self.dumps_json(data, indent=4, sort_keys=True)

    def minify_json(self, data: Any) -> str:
        try:
            return json.dumps(data, separators=(",", ":"), ensure_ascii=False)
        except Exception as e:
            raise ValueError("Unable to minify JSON.") from e

    def json_size(self, data: Any) -> int:
        return len(self.minify_json(data).encode(self.config.encoding))

    def read_json_metadata(self, path: Union[str, Path]) -> FileMetadata:
        self.validate_json(path)
        metadata = self.file_metadata(path)
        metadata.checksum = self.file_checksum(path, algorithm=ChecksumAlgorithm.SHA256)
        return metadata

    def register_json_serializer(self, serializer: Callable) -> None:
        if not hasattr(self, "_json_serializers"):
            self._json_serializers = {}
        self._json_serializers["serializer"] = serializer

    def register_json_deserializer(self, deserializer: Callable) -> None:
        if not hasattr(self, "_json_deserializers"):
            self._json_deserializers = {}
        self._json_deserializers["deserializer"] = deserializer

    def _record_operation(self, success: bool, path: Path, fmt: FileFormat, elapsed: float, msg: str = ""):
        status = IOStatus.SUCCESS if success else IOStatus.FAILED
        if not hasattr(self, "_history"):
            self._history = []
        self._history.append({
            "path": str(path),
            "format": fmt.value,
            "success": success,
            "elapsed": elapsed,
            "message": msg,
        })

    def _make_result(self, success: bool, path: Path, fmt: FileFormat, elapsed: float, msg: str = "") -> IOResult:
        status = IOStatus.SUCCESS if success else IOStatus.FAILED
        return IOResult(
            status=status,
            success=success,
            path=path,
            format=fmt,
            message=msg,
            elapsed_time=elapsed,
        )