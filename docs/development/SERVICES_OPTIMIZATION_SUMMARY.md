# Services Folder Optimization Summary

## Overview

The `services/` folder has been optimized to improve modularity, maintainability, and alignment with the ER diagram and system architecture. Each service now has a clear, single responsibility with proper documentation.

## Changes Applied

### 1. Service Documentation

All service files now have comprehensive docstrings explaining:
- **Purpose**: What the service does
- **Responsibilities**: What operations it handles
- **Dependencies**: What it depends on
- **Entity Links**: How it connects to CALL, REQUEST, and other entities

**Files Updated:**
- `logger_service.py` - Added detailed docstring for logging configuration
- `audio_processor.py` - Documented audio I/O operations (decode, resample, normalize, encode)
- `vad_service.py` - Documented voice activity detection
- `action_service.py` - Documented action execution and entity linking
- `policy_service.py` - Documented business rules enforcement
- `entity_service.py` - Documented entity extraction and matching

### 2. New Service Implementations

**Previously Empty Files - Now Implemented:**

- **`lang_detect_service.py`** - Language Detection Service
  - Detects language from text input
  - Produces LANGUAGE entities
  - Supports multiple languages (en, hi, gu, mr, etc.)
  - Links to CALL and REQUEST entities

- **`memory_service.py`** - Memory Service
  - Manages conversation memory per session/call
  - Links messages to CALL and REQUEST entities
  - Provides context retrieval for dialog management
  - Handles memory persistence

- **`rate_limiter.py`** - Rate Limiter Service
  - Tracks request rates per user/session
  - Writes RateLimitRecord entities when limits exceeded
  - Applies configurable rate limiting policies
  - Uses constants from `global_data.py`

- **`helper_service.py`** - Helper Service
  - ID generation (UUIDs, timestamps)
  - Timestamp formatting and parsing
  - Error handling helpers
  - JSON serialization/deserialization utilities

### 3. Constants Management

**Moved to `global_data.py`:**
- `RESTAURANT_OPEN_HOUR` - Restaurant opening hour (11)
- `RESTAURANT_CLOSE_HOUR` - Restaurant closing hour (23)
- `OUT_OF_STOCK_ITEMS` - List of out-of-stock items
- `FOOD_KEYWORDS` - Keywords for LLM blocking rules

**Updated `policy_service.py`** to import constants from `global_data.py` instead of hardcoding them.

### 4. Import Optimization

**Within `services/` folder**: Changed to relative imports
```python
# Before
from services.config_service import ConfigService
from services.audio_processor import AudioProcessor

# After
from .config_service import ConfigService
from .audio_processor import AudioProcessor
```

**Files Updated:**
- `stt_flow.py` - Uses relative import for AudioProcessor
- `ttt_flow.py` - Uses relative imports for DialogManager and PolicyService
- `dialog_manager.py` - Uses relative imports for EntityService, ActionService, PolicyService
- `audio_processor.py` - Uses relative imports for config_service and vad_service
- `vad_service.py` - Uses relative import for config_service

**From outside `services/`**: Kept absolute imports (unchanged)
```python
from services.config_service import ConfigService
from services.logger_service import setup_logging
```

### 5. Service Exports

**Updated `services/__init__.py`** to expose only necessary exports:
- Core services: Logger, Config, Audio, VAD
- Business services: Entity, Action, Policy, Dialog
- Utility services: Helper, Memory, RateLimiter, LanguageDetection
- Flow orchestrators: STTFlow, TTTFlow, TTSFlow

### 6. Architecture Documentation

**Updated `docs/architecture/ARCHITECTURE_DIAGRAM.md`** with:
- Complete service responsibilities breakdown
- Separation of concerns explanation
- Constants management strategy
- Import optimization guidelines
- Benefits of the optimized structure

## Service Responsibilities Summary

### Core Infrastructure
- **logger_service.py**: Centralized logging configuration
- **config_service.py**: Runtime configuration (device detection, environment variables)
- **audio_processor.py**: Audio I/O operations (decode, resample, normalize, encode)
- **vad_service.py**: Voice activity detection (built on audio_processor outputs)

### Business Logic
- **entity_service.py**: Entity extraction and matching
- **action_service.py**: Action execution (links to REQUEST entities)
- **policy_service.py**: Business rules enforcement (uses global_data constants)
- **dialog_manager.py**: Conversation state management

### Utility Services
- **helper_service.py**: Utility functions (IDs, timestamps, JSON, errors)
- **memory_service.py**: Session/message orchestration (links to CALL/REQUEST entities)
- **rate_limiter.py**: Rate limit enforcement (writes RateLimitRecord entities)
- **lang_detect_service.py**: Language detection (produces LANGUAGE entities)

### Flow Orchestrators
- **stt_flow.py**: Speech-to-Text flow orchestration
- **ttt_flow.py**: Text-to-Text flow orchestration
- **tts_flow.py**: Text-to-Speech flow orchestration

## Benefits

1. **Clear Separation of Concerns**: Each service has one responsibility
2. **Reduced Duplication**: Constants centralized in `global_data.py`
3. **Better Imports**: Relative imports within services, absolute from outside
4. **Improved Documentation**: All services have comprehensive docstrings
5. **Entity Alignment**: Services properly link to CALL, REQUEST, and other entities
6. **Maintainability**: Easier to understand, test, and modify individual services

## Verification

- ✅ All service files have clear docstrings
- ✅ Constants moved to `global_data.py`
- ✅ Relative imports used within `services/` folder
- ✅ `services/__init__.py` exports only necessary items
- ✅ Architecture documentation updated
- ✅ No linter errors
- ✅ All services align with ER diagram entities

## Next Steps

When adding new services:
1. Place in appropriate category (Core, Business, Utility, Flow)
2. Add comprehensive docstring explaining purpose and entity links
3. Use relative imports for services dependencies
4. Add constants to `global_data.py` if static
5. Use `config_service.py` for runtime configuration
6. Export in `services/__init__.py` if needed externally

