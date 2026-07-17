# -*- coding: utf-8 -*-
"""
maya_faceit.utils.filesystem
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Filesystem utilities.
"""

import os
import shutil
from pathlib import Path
from typing import List, Optional, Union, Any


class FileSystemUtils:
    """Utilities for file and directory operations."""

    @staticmethod
    def ensure_dir(path: Union[str, Path]) -> Path:
        """Create directory if it doesn't exist."""
        p = Path(path)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @staticmethod
    def list_files(directory: Union[str, Path], pattern: str = "*",
                   recursive: bool = False) -> List[Path]:
        """List files in a directory matching a pattern."""
        p = Path(directory)
        if recursive:
            return list(p.rglob(pattern))
        return list(p.glob(pattern))

    @staticmethod
    def copy_file(src: Union[str, Path], dst: Union[str, Path]) -> bool:
        """Copy a file."""
        try:
            shutil.copy2(src, dst)
            return True
        except:
            return False

    @staticmethod
    def move_file(src: Union[str, Path], dst: Union[str, Path]) -> bool:
        """Move a file."""
        try:
            shutil.move(src, dst)
            return True
        except:
            return False

    @staticmethod
    def delete_file(path: Union[str, Path]) -> bool:
        """Delete a file."""
        try:
            Path(path).unlink()
            return True
        except:
            return False

    @staticmethod
    def delete_directory(path: Union[str, Path]) -> bool:
        """Delete a directory and all contents."""
        try:
            shutil.rmtree(path)
            return True
        except:
            return False

    @staticmethod
    def get_file_size(path: Union[str, Path]) -> int:
        """Get file size in bytes."""
        try:
            return Path(path).stat().st_size
        except:
            return 0

    @staticmethod
    def get_extension(path: Union[str, Path]) -> str:
        """Get file extension."""
        return Path(path).suffix.lower()

    @staticmethod
    def get_filename(path: Union[str, Path]) -> str:
        """Get filename with extension."""
        return Path(path).name

    @staticmethod
    def get_stem(path: Union[str, Path]) -> str:
        """Get filename without extension."""
        return Path(path).stem

    @staticmethod
    def get_parent(path: Union[str, Path]) -> str:
        """Get parent directory."""
        return str(Path(path).parent)

    @staticmethod
    def is_file(path: Union[str, Path]) -> bool:
        """Check if path is a file."""
        return Path(path).is_file()

    @staticmethod
    def is_dir(path: Union[str, Path]) -> bool:
        """Check if path is a directory."""
        return Path(path).is_dir()

    @staticmethod
    def exists(path: Union[str, Path]) -> bool:
        """Check if path exists."""
        return Path(path).exists()