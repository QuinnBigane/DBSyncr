"""
Dependency Injection Container
Provides a simple dependency injection container for managing application dependencies.
"""

from typing import Dict, Type, Any, TypeVar, Generic
from contextlib import contextmanager
import threading

T = TypeVar('T')


class DependencyContainer:
    """Simple dependency injection container."""

    def __init__(self):
        self._services: Dict[Type, Any] = {}
        self._factories: Dict[Type, callable] = {}
        self._singletons: Dict[Type, Any] = {}
        self._lock = threading.Lock()

    def register(self, interface: Type[T], implementation: Type[T] = None, singleton: bool = False):
        """
        Register a service implementation.

        Args:
            interface: The interface/abstract class
            implementation: The concrete implementation (if None, interface is used)
            singleton: Whether to create a singleton instance
        """
        if implementation is None:
            implementation = interface

        with self._lock:
            if singleton:
                self._singletons[interface] = None  # Will be created on first access
            else:
                self._services[interface] = implementation

        return self

    def register_factory(self, interface: Type[T], factory: callable, singleton: bool = False):
        """
        Register a factory function for creating instances.

        Args:
            interface: The interface/abstract class
            factory: Factory function that returns an instance
            singleton: Whether the factory result should be cached as singleton
        """
        with self._lock:
            self._factories[interface] = factory
            if singleton:
                self._singletons[interface] = None

        return self

    def register_instance(self, interface: Type[T], instance: T):
        """
        Register a pre-created instance.

        Args:
            interface: The interface/abstract class
            instance: The instance to register
        """
        with self._lock:
            self._services[interface] = instance

        return self

    def resolve(self, interface: Type[T]) -> T:
        """
        Resolve a service instance.

        Args:
            interface: The interface/abstract class to resolve

        Returns:
            Instance of the requested type

        Raises:
            ValueError: If the interface is not registered
        """
        with self._lock:
            # Check for singleton first
            if interface in self._singletons:
                if self._singletons[interface] is None:
                    # Create singleton instance
                    if interface in self._factories:
                        self._singletons[interface] = self._factories[interface]()
                    elif interface in self._services:
                        impl = self._services[interface]
                        if callable(impl):
                            self._singletons[interface] = impl()
                        else:
                            self._singletons[interface] = impl
                    else:
                        raise KeyError(f"No factory or implementation registered for {interface}")
                return self._singletons[interface]

            # Check for factory
            if interface in self._factories:
                return self._factories[interface]()

            # Check for direct service
            if interface in self._services:
                impl = self._services[interface]
                if callable(impl):
                    return impl()
                return impl

            raise KeyError(f"Service {interface} not registered")

    def clear(self):
        """Clear all registered services."""
        with self._lock:
            self._services.clear()
            self._factories.clear()
            self._singletons.clear()


# Global container instance
_container = DependencyContainer()


def get_container() -> DependencyContainer:
    """Get the global dependency container."""
    return _container


def register(interface: Type[T], implementation: Type[T] = None, singleton: bool = False):
    """Register a service in the global container."""
    return get_container().register(interface, implementation, singleton)


def register_factory(interface: Type[T], factory: callable, singleton: bool = False):
    """Register a factory in the global container."""
    return get_container().register_factory(interface, factory, singleton)


def register_instance(interface: Type[T], instance: T):
    """Register an instance in the global container."""
    return get_container().register_instance(interface, instance)


def resolve(interface: Type[T]) -> T:
    """Resolve a service from the global container."""
    return get_container().resolve(interface)


@contextmanager
def scoped_container():
    """Context manager for scoped dependency injection."""
    global _container
    old_container = _container
    _container = DependencyContainer()
    try:
        yield _container
    finally:
        _container = old_container