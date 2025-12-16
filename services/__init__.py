"""
Services Module

Core business logic and runtime services for the voice platform.

Structure:
- infrastructure/: Foundational runtime support (config, logger, metrics, audio, vad)
- business/: Domain-specific business logic (policy, entity, action)
- flows/: Flow orchestrators (STT, TTT, TTS)
- receptionist/: Receptionist-specific services (dialog, intent, handoff)
- platform/: Platform-level services (auth, cache, notification, validation)
- integrations/: External system integrations

Note: Utility services (helper, memory, rate_limiter, lang_detect) are in the utility/ folder at project root.
"""

# Infrastructure services
from .infrastructure import (
    ConfigService,
    setup_logging,
    log_conversation,
    MetricsService,
    AudioProcessor,
    VADService,
)

# Business services
from .business import (
    PolicyService,
    ActionService,
    EntityService,
)

# Flow orchestrators
from .flows import STTFlow, TTTFlow, TTSFlow

# Receptionist services
from .receptionist import DialogManager

# Platform services (will be exported when implemented)
# from .platform import AuthService, CacheService, NotificationService, ValidationService

# Integrations (already in subfolder)
# from .integrations import ...

__all__ = [
    # Infrastructure services
    'ConfigService',
    'setup_logging',
    'log_conversation',
    'MetricsService',
    'AudioProcessor',
    'VADService',
    
    # Business services
    'PolicyService',
    'ActionService',
    'EntityService',
    
    # Flow orchestrators
    'STTFlow',
    'TTTFlow',
    'TTSFlow',
    
    # Receptionist services
    'DialogManager',
]
