# -*- coding: utf-8 -*-
"""Diagnostics mixin."""
import hashlib
import sys
import platform
from datetime import datetime
from typing import Dict, Any, Callable
from .constants import IO_SCHEMA_VERSION
from pathlib import Path
class DiagnosticsMixin:
    """Mixin providing diagnostics and health checks."""

    def validate_configuration(self) -> bool:
        policy = self.autosave_policy()
        if policy.interval_seconds <= 0:
            raise ValueError("Autosave interval must be > 0.")
        if policy.maximum_backups < 1:
            raise ValueError("maximum_backups must be >= 1.")
        if policy.autosave_directory is not None:
            d = Path(policy.autosave_directory)
            if d.exists() and not d.is_dir():
                raise ValueError("Autosave path is not a directory.")
        return True

    def validate_environment(self) -> Dict[str, bool]:
        results = {"configuration": False, "autosave_directory": False, "migration": False,
                   "compression": False, "hashing": False}
        try:
            results["configuration"] = self.validate_configuration()
        except Exception:
            pass
        try:
            d = self.autosave_directory()
            d.mkdir(parents=True, exist_ok=True)
            results["autosave_directory"] = d.exists()
        except Exception:
            pass
        try:
            self.migration_health_check()
            results["migration"] = True
        except Exception:
            pass
        try:
            self.default_compression()
            results["compression"] = True
        except Exception:
            pass
        try:
            hashlib.sha256(b"test")
            results["hashing"] = True
        except Exception:
            pass
        return results

    def self_test(self) -> Dict[str, Any]:
        report = {"timestamp": datetime.now().isoformat(), "tests": {}, "passed": True}
        tests = report["tests"]
        for name, func in [("environment", self.validate_environment),
                           ("configuration", self.validate_configuration),
                           ("migration", self.migration_health_check),
                           ("autosave", self.autosave_health)]:
            try:
                func()
                tests[name] = "PASS"
            except Exception as e:
                tests[name] = str(e)
                report["passed"] = False
        return report

    def diagnostics(self) -> Dict[str, Any]:
        return {
            "session": self.session_summary(),
            "autosave": self.autosave_health(),
            "migration": self.migration_health_check(),
            "environment": self.validate_environment(),
            "statistics": self.autosave_statistics(),
        }

    def runtime_summary(self) -> Dict[str, Any]:
        return {
            "initialized": getattr(self, "_initialized", False),
            "session_active": self.session_active(),
            "autosave_enabled": self.autosave_enabled(),
            "dirty": self.is_dirty(),
            "current_version": self.current_version(),
            "schema_version": IO_SCHEMA_VERSION,
        }

    def health_check(self) -> bool:
        try:
            return (self.validate_configuration() and
                    self.autosave_is_healthy() and
                    self.migration_health_check()["compatible"])
        except Exception:
            return False

    def diagnostics_report(self) -> str:
        runtime = self.runtime_summary()
        health = self.health_check()
        return (f"I/O Diagnostics\n"
                f"===============\n"
                f"Healthy        : {health}\n"
                f"Initialized    : {runtime['initialized']}\n"
                f"Session Active : {runtime['session_active']}\n"
                f"Autosave       : {runtime['autosave_enabled']}\n"
                f"Dirty          : {runtime['dirty']}\n"
                f"Version        : {runtime['current_version']}\n"
                f"Schema         : {runtime['schema_version']}")