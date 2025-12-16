"""
Dependency Injection Container

This module provides a simple dependency injection container to manage dependencies
and reduce coupling between modules.
"""
from typing import Dict, Any, Optional, TypeVar, Callable
from dataclasses import dataclass

T = TypeVar('T')


@dataclass
class ServiceDescriptor:
    """Descriptor for a service dependency"""
    factory: Callable[[], Any]
    singleton: bool = False
    instance: Optional[Any] = None


class DIContainer:
    """
    Simple Dependency Injection Container
    
    Provides centralized dependency management to reduce coupling.
    """
    
    def __init__(self):
        self._services: Dict[str, ServiceDescriptor] = {}
    
    def register(self, name: str, factory: Callable[[], Any], singleton: bool = False):
        """Register a service factory"""
        self._services[name] = ServiceDescriptor(factory=factory, singleton=singleton)
    
    def get(self, name: str) -> Any:
        """Get a service instance"""
        if name not in self._services:
            raise ValueError(f"Service '{name}' not registered")
        
        descriptor = self._services[name]
        
        if descriptor.singleton:
            if descriptor.instance is None:
                descriptor.instance = descriptor.factory()
            return descriptor.instance
        
        return descriptor.factory()
    
    def has(self, name: str) -> bool:
        """Check if service is registered"""
        return name in self._services

