# Services Business/Infrastructure Refactoring

## Overview

The `services/` folder has been further refactored to separate domain-specific business logic from foundational infrastructure services. This creates a clearer distinction between what the application does (business logic) and how it runs (infrastructure).

## New Structure

```
services/
├── __init__.py
│
├── infrastructure/           # ✅ NEW: Foundational runtime support
│   ├── __init__.py
│   ├── config_service.py    # Runtime configuration
│   ├── logger_service.py     # Logging configuration
│   ├── metrics_service.py    # Metrics collection
│   ├── audio_processor.py    # Audio I/O operations
│   └── vad_service.py        # Voice activity detection
│
├── business/                 # ✅ NEW: Domain-specific business logic
│   ├── __init__.py
│   ├── policy_service.py     # Business policies and rules
│   ├── action_service.py     # Action execution
│   └── entity_service.py     # Entity extraction and matching
│
├── flows/                    # Flow orchestrators
│   ├── stt_flow.py
│   ├── ttt_flow.py
│   └── tts_flow.py
│
├── receptionist/            # Receptionist services
│   ├── dialog_manager.py
│   ├── intent_service.py
│   └── handoff_service.py
│
├── platform/                # Platform services
│   ├── auth_service.py
│   ├── cache_service.py
│   ├── notification_service.py
│   └── validation_service.py
│
└── integrations/            # External integrations
    └── ...
```

## Rationale

### Infrastructure Services (`infrastructure/`)

**Purpose**: Foundational runtime support that enables the application to function.

**Characteristics**:
- Low-level, technical concerns
- Not domain-specific (could be used in any application)
- Provide the "how" - how the application runs
- Typically initialized early in application startup

**Services**:
- **config_service.py**: Device detection, environment variables, runtime configuration
- **logger_service.py**: Logging handlers, formatters, rotation
- **metrics_service.py**: Metrics collection and reporting
- **audio_processor.py**: Audio I/O operations (recording, decoding, encoding)
- **vad_service.py**: Voice activity detection (speech detection)

### Business Services (`business/`)

**Purpose**: Domain-specific business logic for the restaurant voice assistant.

**Characteristics**:
- High-level, domain-specific concerns
- Encapsulate business rules and operations
- Provide the "what" - what the application does
- Restaurant/voice assistant specific

**Services**:
- **policy_service.py**: Business rules (restaurant hours, availability, LLM blocking)
- **action_service.py**: Business actions (order finalization, customer info extraction)
- **entity_service.py**: Domain entity extraction (dish names, quantities, phonetic corrections)

## Benefits

1. **Clear Separation**: Infrastructure vs. Business logic is now explicit
2. **Better Organization**: Related services are grouped by their purpose
3. **Easier Testing**: Infrastructure can be mocked separately from business logic
4. **Improved Maintainability**: Changes to infrastructure don't affect business logic
5. **Domain Clarity**: Business services clearly represent restaurant domain concepts

## Import Patterns

### From Outside services/ Folder

```python
# Infrastructure services
from services.infrastructure.config_service import ConfigService
from services.infrastructure.logger_service import setup_logging
from services.infrastructure.audio_processor import AudioProcessor
from services.infrastructure.vad_service import VADService

# Business services
from services.business.policy_service import PolicyService
from services.business.action_service import ActionService
from services.business.entity_service import EntityService
```

### Within services/ Folder (Relative Imports)

```python
# Within infrastructure/
from .config_service import ConfigService
from .vad_service import VADService

# Within business/
from .policy_service import PolicyService
from .entity_service import EntityService

# From flows/ to infrastructure/
from services.infrastructure.audio_processor import AudioProcessor

# From receptionist/ to business/
from services.business.entity_service import EntityService
from services.business.action_service import ActionService
```

### Using Package Exports

```python
# Can use direct imports from services package
from services import ConfigService, AudioProcessor, VADService
from services import PolicyService, ActionService, EntityService
```

## Files Moved

### Infrastructure Services
1. `services/config_service.py` → `services/infrastructure/config_service.py`
2. `services/logger_service.py` → `services/infrastructure/logger_service.py`
3. `services/metrics_service.py` → `services/infrastructure/metrics_service.py`
4. `services/audio_processor.py` → `services/infrastructure/audio_processor.py`
5. `services/vad_service.py` → `services/infrastructure/vad_service.py`

### Business Services
1. `services/policy_service.py` → `services/business/policy_service.py`
2. `services/action_service.py` → `services/business/action_service.py`
3. `services/entity_service.py` → `services/business/entity_service.py`

## Imports Updated

- ✅ `main.py` - Updated to use new paths
- ✅ `services/flows/stt_flow.py` - Updated AudioProcessor import
- ✅ `services/flows/ttt_flow.py` - Updated PolicyService import
- ✅ `services/receptionist/dialog_manager.py` - Updated business service imports
- ✅ `services/infrastructure/*.py` - Updated relative imports
- ✅ `llms/STT/stt_service.py` - Updated config_service import
- ✅ `llms/TTT/ttt_service.py` - Updated config_service import
- ✅ `llms/TTS/tts_service.py` - Updated config_service import
- ✅ `services/__init__.py` - Updated exports

## Next Steps

When adding new services:
- **Infrastructure concern?** (config, logging, metrics, audio, etc.) → Add to `services/infrastructure/`
- **Business logic?** (restaurant rules, actions, entities) → Add to `services/business/`
- **Flow orchestrator?** → Add to `services/flows/`
- **Receptionist feature?** → Add to `services/receptionist/`
- **Platform infrastructure?** → Add to `services/platform/`

This structure ensures every service has a clear, logical home based on its purpose and domain.

