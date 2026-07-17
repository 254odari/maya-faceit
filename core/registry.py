"""
core/registry.py

Service and component registry for the application.
"""

from typing import Dict, Any, Optional


class ServiceRegistry:
    """
    Central registry for services and components.

    Allows loose coupling by registering services by name.
    """

    def __init__(self):
        self._services: Dict[str, Any] = {}

    def register(self, name: str, service: Any) -> None:
        """Register a service."""
        self._services[name] = service

    def get(self, name: str) -> Optional[Any]:
        """Get a registered service."""
        return self._services.get(name)

    def has(self, name: str) -> bool:
        """Check if a service is registered."""
        return name in self._services

    def unregister(self, name: str) -> bool:
        """Unregister a service."""
        if name in self._services:
            del self._services[name]
            return True
        return False

    def clear(self) -> None:
        """Clear all registrations."""
        self._services.clear()

    def list_services(self) -> list:
        """List all registered service names."""
        return list(self._services.keys())


class ComponentRegistry(ServiceRegistry):
    """Registry specifically for UI components (panels, tools, etc.)."""
    pass