"""
maya_faceit/services/plugins/plugin_manager.py

Plugin system for extending FaceIT with custom modules.
"""

import logging
import importlib
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Type

logger = logging.getLogger(__name__)


@dataclass
class PluginInfo:
    """Metadata about a plugin."""
    name: str
    version: str
    author: str = "Unknown"
    description: str = ""
    enabled: bool = True


class Plugin:
    """Base class for all plugins."""
    info: Optional[PluginInfo] = None

    def on_load(self) -> None:
        """Called when the plugin is loaded."""
        pass

    def on_unload(self) -> None:
        """Called when the plugin is unloaded."""
        pass

    def on_enable(self) -> None:
        """Called when the plugin is enabled."""
        pass

    def on_disable(self) -> None:
        """Called when the plugin is disabled."""
        pass


class PluginManager:
    """Manages plugin discovery, loading, and lifecycle."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self._plugins: Dict[str, Plugin] = {}
        self._plugin_dirs: List[str] = []
        logger.debug("PluginManager initialized")

    def add_plugin_directory(self, path: str) -> None:
        """Add a directory to search for plugins."""
        if os.path.exists(path) and path not in self._plugin_dirs:
            self._plugin_dirs.append(path)

    def discover_plugins(self) -> List[str]:
        """Scan plugin directories and return names of found plugins."""
        discovered = []
        for directory in self._plugin_dirs:
            if not os.path.isdir(directory):
                continue
            for entry in os.listdir(directory):
                if entry.endswith(".py") and not entry.startswith("_"):
                    name = entry[:-3]
                    discovered.append(name)
                elif os.path.isdir(os.path.join(directory, entry)):
                    # Check for __init__.py
                    init_file = os.path.join(directory, entry, "__init__.py")
                    if os.path.exists(init_file):
                        discovered.append(entry)
        return discovered

    def load_plugin(self, plugin_name: str) -> Optional[Plugin]:
        """Load a plugin by name from the discovered directories."""
        if plugin_name in self._plugins:
            logger.info(f"Plugin '{plugin_name}' already loaded.")
            return self._plugins[plugin_name]

        # Try to import the plugin module
        for directory in self._plugin_dirs:
            if directory not in sys.path:
                sys.path.insert(0, directory)

            try:
                module = importlib.import_module(plugin_name)
                # Look for a subclass of Plugin
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and
                        issubclass(attr, Plugin) and
                        attr is not Plugin):
                        plugin_instance = attr()
                        # Use info if provided, else generate from module name
                        if plugin_instance.info is None:
                            plugin_instance.info = PluginInfo(
                                name=plugin_name,
                                version="1.0.0",
                                author="Unknown"
                            )
                        self._plugins[plugin_name] = plugin_instance
                        plugin_instance.on_load()
                        logger.info(f"Plugin '{plugin_name}' loaded.")
                        return plugin_instance
            except Exception as e:
                logger.error(f"Failed to load plugin '{plugin_name}': {e}")
            finally:
                if directory in sys.path:
                    sys.path.remove(directory)

        return None

    def unload_plugin(self, plugin_name: str) -> bool:
        """Unload a plugin."""
        if plugin_name not in self._plugins:
            logger.warning(f"Plugin '{plugin_name}' not loaded.")
            return False
        plugin = self._plugins[plugin_name]
        plugin.on_unload()
        del self._plugins[plugin_name]
        logger.info(f"Plugin '{plugin_name}' unloaded.")
        return True

    def enable_plugin(self, plugin_name: str) -> bool:
        """Enable a plugin."""
        if plugin_name not in self._plugins:
            return False
        plugin = self._plugins[plugin_name]
        plugin.info.enabled = True
        plugin.on_enable()
        return True

    def disable_plugin(self, plugin_name: str) -> bool:
        """Disable a plugin."""
        if plugin_name not in self._plugins:
            return False
        plugin = self._plugins[plugin_name]
        plugin.info.enabled = False
        plugin.on_disable()
        return True

    def get_plugin(self, plugin_name: str) -> Optional[Plugin]:
        return self._plugins.get(plugin_name)

    def get_all_plugins(self) -> List[Plugin]:
        return list(self._plugins.values())

    def get_plugin_info(self, plugin_name: str) -> Optional[PluginInfo]:
        plugin = self.get_plugin(plugin_name)
        return plugin.info if plugin else None