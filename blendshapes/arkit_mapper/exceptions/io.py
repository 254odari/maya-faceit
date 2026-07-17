"""
io.py

Exceptions related to importing, exporting, serialization, file I/O, and data conversion.
"""

from typing import Any

from .base import ARKitMapperError, ErrorCategory


class ImportExportError(ARKitMapperError):
    def __init__(self, message: str = "Import/export error.", **kwargs: Any) -> None:
        super().__init__(message, category=ErrorCategory.IMPORT_EXPORT, **kwargs)


class ImportError(ImportExportError):
    def __init__(self, source: str = "", **kwargs: Any) -> None:
        self.source = source
        message = "Import failed." if not source else f"Failed to import '{source}'."
        super().__init__(message, **kwargs)


class UnsupportedImportFormatError(ImportExportError):
    def __init__(self, file_format: str, **kwargs: Any) -> None:
        self.file_format = file_format
        super().__init__(f"Unsupported import format '{file_format}'.", **kwargs)


class CorruptedImportFileError(ImportExportError):
    def __init__(self, filename: str = "", **kwargs: Any) -> None:
        self.filename = filename
        message = "Imported file is corrupted." if not filename else f"Imported file '{filename}' is corrupted."
        super().__init__(message, **kwargs)


class ExportError(ImportExportError):
    def __init__(self, destination: str = "", **kwargs: Any) -> None:
        self.destination = destination
        message = "Export failed." if not destination else f"Failed to export to '{destination}'."
        super().__init__(message, **kwargs)


class UnsupportedExportFormatError(ImportExportError):
    def __init__(self, file_format: str, **kwargs: Any) -> None:
        self.file_format = file_format
        super().__init__(f"Unsupported export format '{file_format}'.", **kwargs)


class SerializationError(ImportExportError):
    def __init__(self, reason: str = "Serialization failed.", **kwargs: Any) -> None:
        self.reason = reason
        super().__init__(reason, **kwargs)


class DeserializationError(ImportExportError):
    def __init__(self, reason: str = "Deserialization failed.", **kwargs: Any) -> None:
        self.reason = reason
        super().__init__(reason, **kwargs)


class JSONEncodingError(SerializationError):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__("JSON encoding failed.", **kwargs)


class JSONDecodingError(DeserializationError):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__("JSON decoding failed.", **kwargs)


class FileReadError(ImportExportError):
    def __init__(self, filename: str, **kwargs: Any) -> None:
        self.filename = filename
        super().__init__(f"Unable to read file '{filename}'.", **kwargs)


class FileWriteError(ImportExportError):
    def __init__(self, filename: str, **kwargs: Any) -> None:
        self.filename = filename
        super().__init__(f"Unable to write file '{filename}'.", **kwargs)


class FilePermissionError(ImportExportError):
    def __init__(self, path: str, **kwargs: Any) -> None:
        self.path = path
        super().__init__(f"Permission denied for '{path}'.", **kwargs)


class FileFormatError(ImportExportError):
    def __init__(self, filename: str, **kwargs: Any) -> None:
        self.filename = filename
        super().__init__(f"Invalid file format for '{filename}'.", **kwargs)


class ArchiveError(ImportExportError):
    def __init__(self, message: str = "Archive error.", **kwargs: Any) -> None:
        super().__init__(message, **kwargs)


class CompressionError(ArchiveError):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__("Compression failed.", **kwargs)


class DecompressionError(ArchiveError):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__("Decompression failed.", **kwargs)