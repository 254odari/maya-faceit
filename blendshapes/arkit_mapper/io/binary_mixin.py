# -*- coding: utf-8 -*-
"""Binary serialization mixin."""

import pickle
import base64
import io
import time
import shutil
from pathlib import Path
from typing import Any, Union, Optional, BinaryIO, Dict
from datetime import datetime, timedelta
from .models import IOResult, FileFormat, IOStatus
from .enums import ChecksumAlgorithm

class BinaryMixin:
    """Mixin providing binary serialization methods."""

    def serialize(self, obj: Any, *, protocol: Optional[int] = None) -> bytes:
        protocol = protocol if protocol is not None else self._get_pickle_protocol()
        try:
            return pickle.dumps(obj, protocol=protocol)
        except Exception as e:
            raise ValueError(f"Serialization failed: {e}") from e

    def deserialize(self, data: bytes) -> Any:
        try:
            return pickle.loads(data)
        except Exception as e:
            raise ValueError(f"Deserialization failed: {e}") from e

    def save_binary(self, path: Union[str, Path], obj: Any, *, protocol: Optional[int] = None,
                    create_backup: bool = False) -> IOResult:
        path = self.normalize_path(path)
        if create_backup and path.exists():
            self.create_backup(path)
        binary = self.serialize(obj, protocol=protocol)
        start = time.perf_counter()
        try:
            with path.open("wb") as fp:
                fp.write(binary)
            return self._make_result(True, path, FileFormat.BINARY, time.perf_counter() - start)
        except Exception as e:
            return self._make_result(False, path, FileFormat.BINARY, time.perf_counter() - start, str(e))

    def load_binary(self, path: Union[str, Path], *, validate: bool = True) -> Any:
        path = self.normalize_path(path)
        self.validate_file(path)
        start = time.perf_counter()
        try:
            with path.open("rb") as fp:
                data = fp.read()
            if validate and not data:
                raise ValueError("Binary file is empty.")
            obj = self.deserialize(data)
            self._record_operation(True, path, FileFormat.BINARY, time.perf_counter() - start)
            return obj
        except Exception as e:
            self._record_operation(False, path, FileFormat.BINARY, time.perf_counter() - start, str(e))
            raise

    def binary_size(self, obj: Any, *, protocol: Optional[int] = None) -> int:
        return len(self.serialize(obj, protocol=protocol))

    def is_binary_file(self, path: Union[str, Path]) -> bool:
        try:
            self.load_binary(path, validate=False)
            return True
        except Exception:
            return False

    def binary_metadata(self, path: Union[str, Path]) -> Dict[str, Any]:
        path = self.normalize_path(path)
        self.validate_file(path)
        return {
            "path": str(path),
            "size": path.stat().st_size,
            "modified": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
            "checksum": self.file_checksum(path, algorithm=ChecksumAlgorithm.SHA256),
            "format": FileFormat.BINARY.value,
        }

    def copy_binary(self, source: Union[str, Path], destination: Union[str, Path]) -> IOResult:
        source = self.normalize_path(source)
        destination = self.ensure_parent_directory(destination)
        self.validate_file(source)
        shutil.copy2(source, destination)
        return self._make_result(True, destination, FileFormat.BINARY, 0.0)

    def clone_binary_object(self, obj: Any) -> Any:
        return self.deserialize(self.serialize(obj))

    def binary_roundtrip(self, obj: Any) -> bool:
        return self.clone_binary_object(obj) == obj

    def binary_protocol(self) -> int:
        return getattr(self.config, "pickle_protocol", pickle.HIGHEST_PROTOCOL)

    def set_binary_protocol(self, protocol: int) -> None:
        if not isinstance(protocol, int) or protocol < 0:
            raise ValueError("Protocol must be a non-negative integer.")
        self.config.pickle_protocol = protocol

    def _get_pickle_protocol(self) -> int:
        return self.binary_protocol()

    def to_bytes(self, obj: Any, *, protocol: Optional[int] = None) -> bytes:
        return self.serialize(obj, protocol=protocol)

    def from_bytes(self, data: bytes) -> Any:
        return self.deserialize(data)

    def bytes_to_file(self, data: bytes, path: Union[str, Path]) -> IOResult:
        path = self.ensure_parent_directory(path)
        start = time.perf_counter()
        try:
            with path.open("wb") as fp:
                fp.write(data)
            return self._make_result(True, path, FileFormat.BINARY, time.perf_counter() - start)
        except Exception as e:
            return self._make_result(False, path, FileFormat.BINARY, time.perf_counter() - start, str(e))

    def file_to_bytes(self, path: Union[str, Path]) -> bytes:
        self.validate_file(path)
        with path.open("rb") as fp:
            return fp.read()

    def object_to_base64(self, obj: Any, *, protocol: Optional[int] = None) -> str:
        return base64.b64encode(self.serialize(obj, protocol=protocol)).decode("ascii")

    def object_from_base64(self, encoded: str) -> Any:
        return self.deserialize(base64.b64decode(encoded.encode("ascii")))

    def bytes_to_base64(self, data: bytes) -> str:
        return base64.b64encode(data).decode("ascii")

    def base64_to_bytes(self, encoded: str) -> bytes:
        return base64.b64decode(encoded.encode("ascii"))

    def file_to_base64(self, path: Union[str, Path]) -> str:
        return self.bytes_to_base64(self.file_to_bytes(path))

    def base64_to_file(self, encoded: str, destination: Union[str, Path]) -> IOResult:
        return self.bytes_to_file(self.base64_to_bytes(encoded), destination)