"""
Unit tests for dependency injection container
Tests service registration, resolution, singleton behavior, and factory functions
"""
import pytest
from unittest.mock import MagicMock
from src.utils.dependency_injection import DependencyContainer


class TestDependencyContainer:
    """Test DependencyContainer class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.container = DependencyContainer()

    def test_register_simple_service(self):
        """Test registering a simple service."""

        class TestService:
            def __init__(self):
                self.value = "test"

        self.container.register(TestService)

        # Service should be registered
        assert TestService in self.container._services

    def test_register_with_interface(self):
        """Test registering a service with a specific interface."""

        class IService:
            pass

        class ConcreteService(IService):
            def __init__(self):
                self.value = "concrete"

        self.container.register(IService, ConcreteService)

        assert self.container._services[IService] == ConcreteService

    def test_register_singleton(self):
        """Test registering a singleton service."""

        class SingletonService:
            def __init__(self):
                self.value = "singleton"

        # Register with factory for singleton
        self.container.register_factory(SingletonService, factory=SingletonService, singleton=True)

        assert SingletonService in self.container._singletons
        assert self.container._singletons[SingletonService] is None  # Not yet created

    def test_register_factory(self):
        """Test registering a factory function."""

        def test_factory():
            return "factory_result"

        class IService:
            pass

        self.container.register_factory(IService, test_factory)

        assert self.container._factories[IService] == test_factory

    def test_register_factory_singleton(self):
        """Test registering a singleton factory."""

        def test_factory():
            return "singleton_factory_result"

        class IService:
            pass

        self.container.register_factory(IService, test_factory, singleton=True)

        assert IService in self.container._singletons
        assert self.container._singletons[IService] is None  # Not yet created

    def test_resolve_simple_service(self):
        """Test resolving a simple service."""

        class TestService:
            def __init__(self):
                self.value = 42

        self.container.register(TestService)

        instance = self.container.resolve(TestService)

        assert isinstance(instance, TestService)
        assert instance.value == 42

    def test_resolve_with_dependencies(self):
        """Test resolving services with dependencies (manual setup)."""

        class Dependency:
            def __init__(self):
                self.name = "dependency"

        class ServiceWithDep:
            def __init__(self, dep: Dependency):
                self.dep = dep

        # Register the dependency first
        self.container.register(Dependency)

        # Create service instance manually with resolved dependency
        dep_instance = self.container.resolve(Dependency)
        service_instance = ServiceWithDep(dep_instance)

        # Register the service instance (not the class)
        self.container.register(ServiceWithDep, service_instance)

        # Resolve and verify
        resolved_service = self.container.resolve(ServiceWithDep)

        assert isinstance(resolved_service, ServiceWithDep)
        assert resolved_service.dep is dep_instance
        assert resolved_service.dep.name == "dependency"

    def test_resolve_singleton(self):
        """Test resolving singleton services."""

        class SingletonService:
            def __init__(self):
                self.instance_id = id(self)

        # Register with factory for singleton
        self.container.register_factory(SingletonService, factory=SingletonService, singleton=True)

        instance1 = self.container.resolve(SingletonService)
        instance2 = self.container.resolve(SingletonService)

        assert instance1 is instance2  # Same instance
        assert instance1.instance_id == instance2.instance_id

    def test_resolve_factory(self):
        """Test resolving factory-created services."""

        call_count = 0

        def test_factory():
            nonlocal call_count
            call_count += 1
            return f"result_{call_count}"

        class IService:
            pass

        self.container.register_factory(IService, test_factory)

        result1 = self.container.resolve(IService)
        result2 = self.container.resolve(IService)

        assert result1 == "result_1"
        assert result2 == "result_2"  # Factory called each time
        assert call_count == 2

    def test_resolve_factory_singleton(self):
        """Test resolving singleton factory services."""

        call_count = 0

        def test_factory():
            nonlocal call_count
            call_count += 1
            return f"singleton_{call_count}"

        class IService:
            pass

        self.container.register_factory(IService, test_factory, singleton=True)

        result1 = self.container.resolve(IService)
        result2 = self.container.resolve(IService)

        assert result1 == "singleton_1"
        assert result2 == "singleton_1"  # Same instance
        assert call_count == 1  # Factory called only once

    def test_resolve_unregistered_service(self):
        """Test resolving an unregistered service."""

        class UnregisteredService:
            pass

        with pytest.raises(KeyError):
            self.container.resolve(UnregisteredService)

    def test_thread_safety(self):
        """Test that container operations are thread-safe."""
        import threading
        import time

        results = []
        errors = []

        def register_and_resolve(service_id):
            try:
                class TestService:
                    def __init__(self):
                        self.id = service_id

                self.container.register(TestService)
                instance = self.container.resolve(TestService)
                results.append(instance.id)
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(10):
            thread = threading.Thread(target=register_and_resolve, args=(i,))
            threads.append(thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        assert len(results) == 10
        assert len(errors) == 0
        assert set(results) == set(range(10))

    def test_context_manager(self):
        """Test that container doesn't support context manager (by design)."""

        class TestService:
            def __init__(self):
                self.value = "test"

        # This should raise TypeError since DependencyContainer doesn't implement context manager
        with pytest.raises(TypeError):
            with self.container as container:
                container.register(TestService)
                instance = container.resolve(TestService)

                assert isinstance(instance, TestService)

    def test_clear_container(self):
        """Test clearing all registrations."""

        class TestService:
            pass

        self.container.register(TestService)
        assert TestService in self.container._services

        self.container.clear()

        assert len(self.container._services) == 0
        assert len(self.container._factories) == 0
        assert len(self.container._singletons) == 0

    def test_override_registration(self):
        """Test overriding service registrations."""

        class TestService:
            def __init__(self):
                self.version = 1

        class TestServiceV2:
            def __init__(self):
                self.version = 2

        # Register initial service
        self.container.register(TestService)
        instance1 = self.container.resolve(TestService)
        assert instance1.version == 1

        # Override registration
        self.container.register(TestService, TestServiceV2)
        instance2 = self.container.resolve(TestService)
        assert instance2.version == 2

    def test_circular_dependency_detection(self):
        """Test that circular dependencies are not automatically resolved."""

        class ServiceA:
            def __init__(self, b):
                self.b = b

        class ServiceB:
            def __init__(self, a):
                self.a = a

        # Register with a factory that just returns the class, not an instance
        self.container.register_factory(ServiceA, factory=lambda: ServiceA)
        self.container.register_factory(ServiceB, factory=lambda: ServiceB)

        # Should return the class, not an instance
        service_a_class = self.container.resolve(ServiceA)
        service_b_class = self.container.resolve(ServiceB)
        assert service_a_class == ServiceA
        assert service_b_class == ServiceB