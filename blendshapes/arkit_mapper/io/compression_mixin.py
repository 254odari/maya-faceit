# -*- coding: utf-8 -*-
"""Compression mixin for IOManager."""

import gzip
import bz2
import lzma
import zipfile
from pathlib import Path
from typing import Union, Optional

from .enums import CompressionType


class CompressionMixin:
    """Mixin providing compression methods."""

    _COMPRESSION_EXTENSIONS = {
        CompressionType.NONE: "",
        CompressionType.GZIP: ".gz",
        CompressionType.ZIP: ".zip",
        CompressionType.BZ2: ".bz2",
        CompressionType.LZMA: ".xz",
    }

    def default_compression(self) -> CompressionType:
        return self.config.compression

    def set_default_compression(self, compression: CompressionType) -> None:
        self.config.compression = compression

    def compression_level(self) -> int:
        return getattr(self.config, "compression_level", 6)

    def set_compression_level(self, level: int) -> None:
        if not 0 <= level <= 9:
            raise ValueError("Compression level must be between 0 and 9.")
        self.config.compression_level = level

    def compression_supported(self, compression: CompressionType) -> bool:
        return compression in (CompressionType.NONE, CompressionType.GZIP, CompressionType.BZ2, CompressionType.LZMA)

    def guess_compression(self, path: Union[str, Path]) -> CompressionType:
        suffix = Path(path).suffix.lower()
        for comp, ext in self._COMPRESSION_EXTENSIONS.items():
            if ext == suffix:
                return comp
        return CompressionType.NONE

    def compress_bytes(self, data: bytes, *, compression: Optional[CompressionType] = None,
                       level: Optional[int] = None) -> bytes:
        compression = compression or self.default_compression()
        level = level if level is not None else self.compression_level()
        if compression == CompressionType.NONE:
            return data
        if compression == CompressionType.GZIP:
            return gzip.compress(data, compresslevel=level)
        if compression == CompressionType.BZ2:
            return bz2.compress(data, compresslevel=level)
        if compression == CompressionType.LZMA:
            return lzma.compress(data, preset=level)
        raise ValueError(f"Unsupported compression: {compression}")

    def decompress_bytes(self, data: bytes, compression: CompressionType) -> bytes:
        if compression == CompressionType.NONE:
            return data
        if compression == CompressionType.GZIP:
            return gzip.decompress(data)
        if compression == CompressionType.BZ2:
            return bz2.decompress(data)
        if compression == CompressionType.LZMA:
            return lzma.decompress(data)
        raise ValueError(f"Unsupported compression: {compression}")

    def compression_extension(self, compression: CompressionType) -> str:
        return self._COMPRESSION_EXTENSIONS.get(compression, "")