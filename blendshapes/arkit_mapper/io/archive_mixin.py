# -*- coding: utf-8 -*-
"""Archive mixin for IOManager."""

import zipfile
import time
from pathlib import Path
from typing import Union, Iterable, List, Optional, Dict, Any
from .models import IOResult
from .enums import IOStatus, FileFormat, ChecksumAlgorithm, CompressionType



class ArchiveMixin:
    """Mixin providing archive (ZIP) methods."""

    def create_archive(self, archive_path: Union[str, Path], sources: Iterable[Union[str, Path]],
                       *, compression: int = zipfile.ZIP_DEFLATED, compresslevel: Optional[int] = None) -> IOResult:
        archive_path = self.normalize_path(archive_path)
        self.ensure_parent_directory(archive_path)
        compresslevel = compresslevel if compresslevel is not None else self.compression_level()
        file_count = 0
        with zipfile.ZipFile(archive_path, mode="w", compression=compression, compresslevel=compresslevel) as archive:
            for source in sources:
                source = self.normalize_path(source)
                self.validate_file_or_directory(source)
                if source.is_file():
                    archive.write(source, arcname=source.name)
                    file_count += 1
                else:
                    for item in source.rglob("*"):
                        if item.is_file():
                            archive.write(item, arcname=item.relative_to(source))
                            file_count += 1
        return self._make_result(True, archive_path, FileFormat.ZIP, 0.0)

    def extract_archive(self, archive_path: Union[str, Path], destination: Union[str, Path], *, overwrite: bool = True) -> IOResult:
        archive_path = self.normalize_path(archive_path)
        destination = self.normalize_path(destination)
        self.validate_file(archive_path)
        destination.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive_path, "r") as archive:
            if overwrite:
                archive.extractall(destination)
            else:
                for member in archive.infolist():
                    target = destination / member.filename
                    if not target.exists():
                        archive.extract(member, destination)
        return self._make_result(True, destination, FileFormat.ZIP, 0.0)

    def list_archive(self, archive_path: Union[str, Path]) -> List[str]:
        archive_path = self.normalize_path(archive_path)
        self.validate_file(archive_path)
        with zipfile.ZipFile(archive_path, "r") as archive:
            return archive.namelist()

    def archive_info(self, archive_path: Union[str, Path]) -> Dict[str, Any]:
        archive_path = self.normalize_path(archive_path)
        self.validate_file(archive_path)
        with zipfile.ZipFile(archive_path, "r") as archive:
            members = archive.infolist()
            compressed = sum(m.compress_size for m in members)
            uncompressed = sum(m.file_size for m in members)
        return {
            "path": str(archive_path),
            "entries": len(members),
            "compressed_size": compressed,
            "uncompressed_size": uncompressed,
            "compression_ratio": compressed / uncompressed if uncompressed else 1.0,
            "checksum": self.sha256(archive_path),
        }