# -*- coding: utf-8 -*-
"""
maya_faceit.application

Application lifecycle, service registry, and core infrastructure.
"""

from .app import Application, get_application
from .registry import ServiceRegistry, ComponentRegistry
from .bootstrap import Bootstrap
from .startup import Startup
from .shutdown import Shutdown
from .session import SessionManager, Session
from .preferences import PreferenceManager
from .project import ProjectManager

__all__ = [
    "Application",
    "get_application",
    "ServiceRegistry",
    "ComponentRegistry",
    "Bootstrap",
    "Startup",
    "Shutdown",
    "SessionManager",
    "Session",
    "PreferenceManager",
    "ProjectManager",
]