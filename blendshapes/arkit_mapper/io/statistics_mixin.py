# -*- coding: utf-8 -*-
"""Statistics mixin."""

from datetime import datetime
from typing import Dict, Any, List, Union
from pathlib import Path
from .enums import IOStatus
from .models import AutosavePolicy, AutosaveEntry, AutosaveState, IOResult
class StatisticsMixin:
    """Mixin providing statistics and reporting."""

    def io_statistics(self) -> Dict[str, Any]:
        autosave = self.autosave_statistics()
        return {
            "session_id": self.session_identifier(),
            "session_duration": str(self.session_duration()),
            "autosave": autosave,
            "history": self.autosave_history_count(),
            "dirty": self.is_dirty(),
        }

    def operation_history(self) -> List[Dict[str, Any]]:
        history = []
        for entry in self.autosave_history():
            history.append({
                "id": entry.identifier,
                "filename": entry.filename,
                "created": entry.created.isoformat(),
                "size": entry.size,
                "successful": entry.successful,
                "version": entry.version,
            })
        return history

    def statistics_summary(self) -> Dict[str, Any]:
        stats = self.io_statistics()
        auto = stats["autosave"]
        return {
            "uptime": stats["session_duration"],
            "autosaves": auto["successes"],
            "failures": auto["failures"],
            "success_rate": auto["success_rate"],
            "history": stats["history"],
        }

    def report(self) -> Dict[str, Any]:
        return {
            "timestamp": datetime.now().isoformat(),
            "runtime": self.runtime_summary(),
            "session": self.session_summary(),
            "diagnostics": self.diagnostics(),
            "statistics": self.io_statistics(),
            "history": self.operation_history(),
        }

    def export_report(self, path: Union[str, Path]) -> IOResult:
        return self.save_json(path, self.report())

    def report_as_text(self) -> str:
        summary = self.statistics_summary()
        return (f"I/O Manager Report\n"
                f"==================\n"
                f"Uptime          : {summary['uptime']}\n"
                f"Autosaves       : {summary['autosaves']}\n"
                f"Failures        : {summary['failures']}\n"
                f"Success Rate    : {summary['success_rate']:.2f}%\n"
                f"History Entries : {summary['history']}")