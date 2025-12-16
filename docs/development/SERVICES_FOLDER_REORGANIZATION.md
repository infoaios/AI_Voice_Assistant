# Services Folder Reorganization

## Overview

The `services/` folder has been reorganized into a hierarchical structure that groups related services by their domain and purpose, improving discoverability and maintainability.

## New Structure

```
services/
├── __init__.py                    # Main exports
├── config_service.py              # Runtime configuration
├── logger_service.py              # Logging configuration
├── metrics_service.py             # Metrics collection
├── rate_limiter.py                # Rate limiting
├── policy_service.py              # Business policies
├── helper_service.py              # Utility functions
├── audio_processor.py             # Audio I/O operations
├── vad_service.py                 # Voice activity detection
├── lang_detect_service.py         # Language detection
├── memory_service.py              # Session/message memory
├── entity_service.py              # Entity extraction
├── action_service.py              # Action execution
│
├── flows/                         # Flow Orchestrators
│   ├── __init__.py
│   ├── stt_flow.py               # Speech-to-Text flow
│   ├── ttt_flow.py               # Text-to-Text flow
│   └── tts_flow.py               # Text-to-Speech flow
│
├── receptionist/                  # Receptionist Services
│   ├── __init__.py
│   ├── dialog_manager.py         # Conversation management
│   ├── intent_service.py         # Intent detection
│   └── handoff_service.py        # Human handoff
│
├── platform/                     # Platform Services
│   ├── __init__.py
│   ├── auth_service.py           # Authentication
│   ├── cache_service.py          # Caching
│   ├── notification_service.py   # Notifications
│   └── validation_service.py     # Data validation
│
└── integrations/                  # External Integrations
    ├── telephony/
    ├── calendar/
    ├── crm/
    ├── ticketing/
    └── messaging/
```

## Organization Rationale

### Root Level Services
Core infrastructure and business logic services that are used across the application:
- **Infrastructure**: `config_service`, `logger_service`, `metrics_service`, `rate_limiter`
- **Business Logic**: `policy_service`, `entity_service`, `action_service`
- **Utilities**: `helper_service`, `audio_processor`, `vad_service`, `lang_detect_service`, `memory_service`

### flows/ Subfolder
Flow orchestrators that coordinate multiple services to complete a transformation pipeline:
- **STTFlow**: Orchestrates speech-to-text processing
- **TTTFlow**: Orchestrates text-to-text (LLM) processing
- **TTSFlow**: Orchestrates text-to-speech processing

### receptionist/ Subfolder
Services specific to the restaurant receptionist functionality:
- **DialogManager**: Manages conversation state and dialog flow
- **IntentService**: Detects and classifies user intents
- **HandoffService**: Coordinates human handoff when needed

### platform/ Subfolder
Platform-level infrastructure services:
- **AuthService**: Authentication and authorization
- **CacheService**: Caching for performance optimization
- **NotificationService**: Notifications and messaging
- **ValidationService**: Data validation and sanitization

### integrations/ Subfolder
External system integrations (already existed):
- **telephony/**: Twilio adapter, webhook verifier
- **calendar/**: Google Calendar integration
- **crm/**: HubSpot, Zoho integrations
- **ticketing/**: Zendesk, Freshdesk integrations
- **messaging/**: WhatsApp, Telegram integrations

## Import Paths

### Updated Import Patterns

**From outside services/ folder:**
```python
# Core services (unchanged)
from services.config_service import ConfigService
from services.logger_service import setup_logging

# Flows (new path)
from services.flows.stt_flow import STTFlow
from services.flows.ttt_flow import TTTFlow
from services.flows.tts_flow import TTSFlow

# Receptionist services (new path)
from services.receptionist.dialog_manager import DialogManager

# Platform services (new path, when implemented)
from services.platform.auth_service import AuthService
```

**Within services/ folder (relative imports):**
```python
# From flows/
from ..audio_processor import AudioProcessor
from ..policy_service import PolicyService

# From receptionist/
from ..entity_service import EntityService
from ..action_service import ActionService
```

**Using services/__init__.py:**
```python
# Can use direct imports from services package
from services import STTFlow, TTTFlow, TTSFlow, DialogManager
```

## Migration Summary

### Files Moved
1. `services/stt_flow.py` → `services/flows/stt_flow.py`
2. `services/ttt_flow.py` → `services/flows/ttt_flow.py`
3. `services/tts_flow.py` → `services/flows/tts_flow.py`
4. `services/dialog_manager.py` → `services/receptionist/dialog_manager.py`
5. `services/intent_service.py` → `services/receptionist/intent_service.py`
6. `services/handoff_service.py` → `services/receptionist/handoff_service.py`
7. `services/auth_service.py` → `services/platform/auth_service.py`
8. `services/cache_service.py` → `services/platform/cache_service.py`
9. `services/notification_service.py` → `services/platform/notification_service.py`
10. `services/validation_service.py` → `services/platform/validation_service.py`

### Imports Updated
- ✅ `main.py` - Updated to use new paths for flows and receptionist services
- ✅ `services/flows/*.py` - Updated relative imports
- ✅ `services/receptionist/dialog_manager.py` - Updated relative imports
- ✅ `services/__init__.py` - Updated exports to reflect new structure

## Benefits

1. **Better Organization**: Related services are grouped together
2. **Clearer Structure**: Easy to understand what each subfolder contains
3. **Improved Discoverability**: Developers can quickly find services by domain
4. **Scalability**: Easy to add new services to appropriate subfolders
5. **Separation of Concerns**: Platform services separated from business logic
6. **Domain Clarity**: Receptionist-specific services are clearly grouped

## Next Steps

When adding new services:
- **Flow orchestrator?** → Add to `services/flows/`
- **Receptionist feature?** → Add to `services/receptionist/`
- **Platform infrastructure?** → Add to `services/platform/`
- **External integration?** → Add to `services/integrations/{category}/`
- **Core business logic?** → Add to `services/` root level

This structure ensures every service has a logical, discoverable location.

