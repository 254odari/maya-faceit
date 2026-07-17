# -*- coding: utf-8 -*-
"""Backup mixin for IOManager."""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Union, List, Optional, Dict, Any
from .models import IOResult, FileFormat, IOStatus

class BackupMixin:
    """Mixin providing backup operations."""

    def create_backup(self, source: Union[str, Path], *, destination: Optional[Union[str, Path]] = None,
                      timestamp: bool = True) -> Path:
        source = self.normalize_path(source)
        self.validate_file(source)
        if destination is None:
            backup_dir = source.parent / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            name = source.stem
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S") if timestamp else "backup"
            filename = f"{name}_{stamp}{source.suffix}"
            destination = backup_dir / filename
        destination = self.normalize_path(destination)
        shutil.copy2(source, destination)
        return destination

    def restore_backup(self, backup_file: Union[str, Path], destination: Union[str, Path]) -> IOResult:
        backup_file = self.normalize_path(backup_file)
        destination = self.normalize_path(destination)
        self.validate_file(backup_file)
        self.ensure_parent_directory(destination)
        shutil.copy2(backup_file, destination)
        return self._make_result(True, destination, FileFormat.BINARY, 0.0)

    def list_backups(self, source: Union[str, Path]) -> List[Path]:
        source = self.normalize_path(source)
        backup_dir = source.parent / "backups"
        if not backup_dir.exists():
            return []
        pattern = f"{source.stem}*{source.suffix}"
        return sorted(backup_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)

    def latest_backup(self, source: Union[str, Path]) -> Optional[Path]:
        backups = self.list_backups(source)
        return backups[0] if backups else None

    def delete_backup(self, backup: Union[str, Path]) -> bool:
        backup = self.normalize_path(backup)
        if backup.exists():
            backup.unlink()
            return True
        return False

    def delete_all_backups(self, source: Union[str, Path]) -> int:
        count = 0
        for b in self.list_backups(source):
            b.unlink()
            count += 1
        return count

    def prune_backups(self, source: Union[str, Path], *, keep: int = 10) -> int:
        backups = self.list_backups(source)
        removed = 0
        for b in backups[keep:]:
            b.unlink()
            removed += 1
        return removed

    def backup_exists(self, source: Union[str, Path]) -> bool:
        return self.latest_backup(source) is not None

    def backup_statistics(self, source: Union[str, Path]) -> Dict[str, Any]:
        backups = self.list_backups(source)
        total_size = sum(b.stat().st_size for b in backups)
        latest = datetime.fromtimestamp(backups[0].stat().st_mtime) if backups else None
        return {"count": len(backups), "total_size": total_size, "latest_backup": latest}