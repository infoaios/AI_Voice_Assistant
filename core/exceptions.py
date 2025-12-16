"""
Core Exceptions

Centralized exception definitions to maintain stable error contracts.
"""


class VoicePlatformException(Exception):
    """Base exception for voice platform"""
    pass


class ConfigurationError(VoicePlatformException):
    """Configuration-related errors"""
    pass


class ServiceError(VoicePlatformException):
    """Service-related errors"""
    pass


class RepositoryError(VoicePlatformException):
    """Repository-related errors"""
    pass


class LLMServiceError(ServiceError):
    """LLM service errors"""
    pass


class AudioProcessingError(ServiceError):
    """Audio processing errors"""
    pass


class OrderError(ServiceError):
    """Order-related errors"""
    pass

