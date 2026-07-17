"""
core/logging

Logging system for Maya Faceit.
"""
from .logger import FaceitLogger, log, profile

__all__ = [
    "FaceitLogger",
    "log",
    "profile",
]