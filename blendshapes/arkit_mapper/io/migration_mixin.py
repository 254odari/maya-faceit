# -*- coding: utf-8 -*-
"""Migration mixin for IOManager."""

import copy
from collections import deque
from datetime import datetime
from typing import Any, Dict, List, Tuple, Callable, Optional, Union

from .constants import IO_VERSION, IO_SCHEMA_VERSION


class MigrationMixin:
    """Mixin providing version migration methods."""

    def _init_migration_registry(self):
        self._migrations: Dict[Tuple[str, str], Callable] = {}

    def parse_version(self, version: Union[str, Tuple[int, int, int]]) -> Tuple[int, int, int]:
        if isinstance(version, tuple):
            if len(version) != 3:
                raise ValueError("Version tuple must have three values.")
            return tuple(int(v) for v in version)
        parts = str(version).strip().split(".")
        if len(parts) != 3:
            raise ValueError(f"Invalid semantic version: {version}")
        return tuple(int(part) for part in parts)

    def version_string(self, version: Tuple[int, int, int]) -> str:
        return ".".join(str(v) for v in version)

    def current_version(self) -> str:
        return IO_VERSION

    def current_version_tuple(self) -> Tuple[int, int, int]:
        return (1, 0, 0)

    def compare_versions(self, left: Union[str, Tuple[int, int, int]], right: Union[str, Tuple[int, int, int]]) -> int:
        a = self.parse_version(left)
        b = self.parse_version(right)
        return (a > b) - (a < b)

    def version_equal(self, left, right) -> bool:
        return self.compare_versions(left, right) == 0

    def version_newer(self, left, right) -> bool:
        return self.compare_versions(left, right) > 0

    def version_older(self, left, right) -> bool:
        return self.compare_versions(left, right) < 0

    def compatible_version(self, version) -> bool:
        return self.parse_version(version)[0] == self.current_version_tuple()[0]

    def register_migration(self, source: str, target: str, migration: Callable) -> None:
        self.validate_version(source)
        self.validate_version(target)
        key = (source, target)
        if key in self._migrations:
            raise ValueError(f"Migration {key} already exists.")
        self._migrations[key] = migration

    def has_migration(self, source: str, target: str) -> bool:
        return (source, target) in self._migrations

    def get_migration(self, source: str, target: str) -> Callable:
        key = (source, target)
        if key not in self._migrations:
            raise ValueError(f"No migration {source} -> {target}")
        return self._migrations[key]

    def find_migration_path(self, source: str, target: str) -> List[Tuple[str, str]]:
        if source == target:
            return []
        graph = {}
        for src, dst in self._migrations:
            graph.setdefault(src, []).append(dst)
        queue = deque([(source, [])])
        visited = {source}
        while queue:
            current, path = queue.popleft()
            for neighbor in graph.get(current, []):
                if neighbor in visited:
                    continue
                new_path = path + [(current, neighbor)]
                if neighbor == target:
                    return new_path
                visited.add(neighbor)
                queue.append((neighbor, new_path))
        raise ValueError(f"No migration path from {source} to {target}")

    def migrate_step(self, data: Any, source: str, target: str) -> Any:
        migration = self.get_migration(source, target)
        return migration(data)

    def migrate(self, data: Any, source: str, target: str, *, validate: bool = True) -> Any:
        if source == target:
            return data
        path = self.find_migration_path(source, target)
        migrated = data
        for src, dst in path:
            migrated = self.migrate_step(migrated, src, dst)
        return migrated

    def auto_migrate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        version = data.get("version", "1.0.0")
        if version == self.current_version():
            return data
        return self.migrate(data, version, self.current_version())

    def validate_version(self, version: str) -> None:
        self.parse_version(version)