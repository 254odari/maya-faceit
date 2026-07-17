# -*- coding: utf-8 -*-
"""Checksum mixin for IOManager."""

import hashlib
import hmac
import zlib
import pickle
from pathlib import Path
from typing import Union, Optional, Dict, Any
from .enums import ChecksumAlgorithm

class ChecksumMixin:
    """Mixin providing checksum methods."""

    _HASH_ALGORITHMS = {
        ChecksumAlgorithm.MD5: hashlib.md5,
        ChecksumAlgorithm.SHA1: hashlib.sha1,
        ChecksumAlgorithm.SHA256: hashlib.sha256,
        ChecksumAlgorithm.SHA512: hashlib.sha512,
    }

    def _create_hasher(self, algorithm: Optional[ChecksumAlgorithm] = None):
        alg = algorithm or self.config.checksum_algorithm
        factory = self._HASH_ALGORITHMS.get(alg)
        if factory is None:
            raise ValueError(f"Unsupported checksum algorithm: {alg}")
        return factory()

    def hash_bytes(self, data: bytes, *, algorithm: Optional[ChecksumAlgorithm] = None) -> str:
        hasher = self._create_hasher(algorithm)
        hasher.update(data)
        return hasher.hexdigest()

    def hash_string(self, text: str, *, encoding: Optional[str] = None, algorithm: Optional[ChecksumAlgorithm] = None) -> str:
        encoding = encoding or self.config.encoding
        return self.hash_bytes(text.encode(encoding), algorithm=algorithm)

    def hash_object(self, obj: Any, *, algorithm: Optional[ChecksumAlgorithm] = None) -> str:
        try:
            import json
            serialized = json.dumps(obj, sort_keys=True, default=str).encode(self.config.encoding)
        except Exception:
            serialized = pickle.dumps(obj)
        return self.hash_bytes(serialized, algorithm=algorithm)

    def file_checksum(self, path: Union[str, Path], *, algorithm: Optional[ChecksumAlgorithm] = None,
                      chunk_size: int = 8192) -> str:
        path = self.normalize_path(path)
        self.validate_file(path)
        hasher = self._create_hasher(algorithm)
        with path.open("rb") as fp:
            while True:
                block = fp.read(chunk_size)
                if not block:
                    break
                hasher.update(block)
        return hasher.hexdigest()

    def md5(self, path: Union[str, Path]) -> str:
        return self.file_checksum(path, algorithm=ChecksumAlgorithm.MD5)

    def sha1(self, path: Union[str, Path]) -> str:
        return self.file_checksum(path, algorithm=ChecksumAlgorithm.SHA1)

    def sha256(self, path: Union[str, Path]) -> str:
        return self.file_checksum(path, algorithm=ChecksumAlgorithm.SHA256)

    def sha512(self, path: Union[str, Path]) -> str:
        return self.file_checksum(path, algorithm=ChecksumAlgorithm.SHA512)

    def crc32(self, path: Union[str, Path], *, chunk_size: int = 8192) -> str:
        path = self.normalize_path(path)
        self.validate_file(path)
        checksum = 0
        with path.open("rb") as fp:
            while True:
                block = fp.read(chunk_size)
                if not block:
                    break
                checksum = zlib.crc32(block, checksum)
        checksum &= 0xFFFFFFFF
        return f"{checksum:08x}"

    def file_hashes(self, path: Union[str, Path]) -> Dict[str, str]:
        return {
            "md5": self.md5(path),
            "sha1": self.sha1(path),
            "sha256": self.sha256(path),
            "sha512": self.sha512(path),
            "crc32": self.crc32(path),
        }

    def checksum(self, source: Union[str, Path, bytes, bytearray], *, algorithm: Optional[ChecksumAlgorithm] = None) -> str:
        if isinstance(source, (bytes, bytearray)):
            return self.hash_bytes(bytes(source), algorithm=algorithm)
        candidate = Path(source)
        if candidate.exists():
            return self.file_checksum(candidate, algorithm=algorithm)
        return self.hash_string(str(source), algorithm=algorithm)

    def compare_checksums(self, left: str, right: str) -> bool:
        return hmac.compare_digest(left, right)

    def verify_file_integrity(self, path: Union[str, Path], expected: str,
                              *, algorithm: Optional[ChecksumAlgorithm] = None):
        # Placeholder – would return a VerificationResult object.
        # We'll just return a boolean for now.
        return self.compare_checksums(self.file_checksum(path, algorithm=algorithm), expected)
    def checksum_info(self, source: Any, *, algorithm: Optional[ChecksumAlgorithm] = None) -> Dict[str, Any]:
        # Placeholder implementation
        return {
            "algorithm": (algorithm or self.config.checksum_algorithm).value,
            "checksum": self.checksum(source, algorithm=algorithm),
            "type": type(source).__name__,
        }