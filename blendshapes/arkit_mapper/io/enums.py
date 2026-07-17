# -*- coding: utf-8 -*-
"""Enumerations for the ARKit Mapper I/O subsystem."""

from enum import Enum


class FileFormat(Enum):
    JSON = "json"
    YAML = "yaml"
    CSV = "csv"
    BINARY = "binary"
    PICKLE = "pickle"
    ZIP = "zip"
    UNKNOWN = "unknown"


class CompressionType(Enum):
    NONE = "none"
    ZIP = "zip"
    GZIP = "gzip"
    BZ2 = "bz2"
    LZMA = "lzma"


class BackupMode(Enum):
    NEVER = "never"
    BEFORE_SAVE = "before_save"
    ALWAYS = "always"


class MigrationStrategy(Enum):
    NONE = "none"
    SAFE = "safe"
    FORCE = "force"


class ChecksumAlgorithm(Enum):
    MD5 = "md5"
    SHA1 = "sha1"
    SHA256 = "sha256"
    SHA512 = "sha512"


class IOStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    WARNING = "warning"
    ERROR = "error"