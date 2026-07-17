# -*- coding: utf-8 -*-
"""CSV serialization mixin."""

import csv
import time
from pathlib import Path
from typing import Any, Union, Iterable, Optional, List, Dict
from .enums import IOStatus, FileFormat, ChecksumAlgorithm
from .models import IOResult, FileMetadata
class CSVMixin:
    """Mixin providing CSV serialization methods."""

    def load_csv(self, path: Union[str, Path], *, validate: bool = True, dict_rows: bool = False) -> List[Any]:
        path = self.normalize_path(path)
        if validate:
            self.validate_csv(path)
        start = time.perf_counter()
        try:
            with path.open(newline="", encoding=self.config.encoding) as fp:
                if dict_rows:
                    reader = csv.DictReader(fp)
                    rows = list(reader)
                else:
                    reader = csv.reader(fp)
                    rows = list(reader)
            self._record_operation(True, path, FileFormat.CSV, time.perf_counter() - start)
            return rows
        except Exception as e:
            self._record_operation(False, path, FileFormat.CSV, time.perf_counter() - start, str(e))
            raise

    def save_csv(self, path: Union[str, Path], rows: Iterable[Iterable[Any]], *,
                 fieldnames: Optional[List[str]] = None, dict_rows: bool = False) -> IOResult:
        path = self.normalize_path(path)
        start = time.perf_counter()
        try:
            self.validate_save_path(path, FileFormat.CSV)
            if self.config.atomic_writes:
                self.atomic_save_csv(path, rows, fieldnames=fieldnames, dict_rows=dict_rows)
            else:
                with path.open("w", newline="", encoding=self.config.encoding) as fp:
                    if dict_rows:
                        writer = csv.DictWriter(fp, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(rows)
                    else:
                        writer = csv.writer(fp)
                        writer.writerows(rows)
            return self._make_result(True, path, FileFormat.CSV, time.perf_counter() - start)
        except Exception as e:
            return self._make_result(False, path, FileFormat.CSV, time.perf_counter() - start, str(e))