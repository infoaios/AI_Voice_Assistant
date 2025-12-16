# Utility Folder Creation

## Overview

Utility services have been moved from `services/` to a new `utility/` folder at the project root level. This separation improves organization by distinguishing between core business services and shared utility functions.

## New Structure

```
voice_platform/
├── services/                    # Core business logic services
│   ├── audio_processor.py
│   ├── vad_service.py
│   ├── logger_service.py
│   ├── metrics_service.py
│   ├── config_service.py
│   ├── policy_service.py
│   ├── entity_service.py
│   ├── action_service.py
│   ├── flows/
│   ├── receptionist/
│   ├── platform/
│   └── integrations/
│
└── utility/                     # ✅ NEW: Utility services
    ├── __init__.py
    ├── helper_service.py        # Utility functions (IDs, timestamps, JSON, errors)
    ├── memory_service.py        # Session/message orchestration
    ├── rate_limiter.py          # Rate limiting enforcement
    └── lang_detect_service.py   # Language detection
```

## Rationale

### Separation of Concerns

**Services Folder** (`services/`):
- Contains core business logic and infrastructure services
- Services that are domain-specific to the voice platform
- Services that orchestrate business workflows

**Utility Folder** (`utility/`):
- Contains shared utility functions used across the application
- Services that provide generic functionality (not domain-specific)
- Services that can be reused in other projects

### Benefits

1. **Clear Separation**: Business services vs. utility functions
2. **Better Organization**: Easier to find utility functions
3. **Reusability**: Utility services can be easily extracted or reused
4. **Maintainability**: Clear distinction between domain logic and utilities
5. **Scalability**: Easy to add new utility functions without cluttering services

## Files Moved

1. `services/helper_service.py` → `utility/helper_service.py`
2. `services/memory_service.py` → `utility/memory_service.py`
3. `services/rate_limiter.py` → `utility/rate_limiter.py`
4. `services/lang_detect_service.py` → `utility/lang_detect_service.py`

## Import Patterns

### From Outside utility/ Folder

```python
# Direct imports
from utility.helper_service import HelperService
from utility.memory_service import MemoryService
from utility.rate_limiter import RateLimiter
from utility.lang_detect_service import LanguageDetectionService

# Or using package imports
from utility import HelperService, MemoryService, RateLimiter, LanguageDetectionService
```

### Within utility/ Folder

```python
# Relative imports
from .helper_service import HelperService
from .memory_service import MemoryService
```

## Updated Services Structure

The `services/` folder now contains only:
- **Core Infrastructure**: config, logger, metrics, audio, vad
- **Business Logic**: policy, entity, action
- **Flow Orchestrators**: flows/ subfolder
- **Receptionist Services**: receptionist/ subfolder
- **Platform Services**: platform/ subfolder
- **Integrations**: integrations/ subfolder

## No Breaking Changes

The utility services maintain the same API and functionality. Only their location has changed. If you were importing from `services.helper_service`, you'll need to update to `utility.helper_service`.

## Next Steps

When adding new utilities:
- **Generic utility function?** → Add to `utility/`
- **Domain-specific service?** → Add to `services/`
- **Flow orchestrator?** → Add to `services/flows/`
- **Receptionist feature?** → Add to `services/receptionist/`
- **Platform infrastructure?** → Add to `services/platform/`

This structure ensures utilities are clearly separated from business logic.

