# Architecture Diagram & Refactoring Rationale

## Project Structure Overview

```
voice_platform/
├── llms/                    # Language Model Services
│   ├── STT/                 # Speech-to-Text submodule
│   │   ├── __init__.py
│   │   └── stt_service.py
│   ├── TTT/                 # Text-to-Text submodule
│   │   ├── __init__.py
│   │   ├── ttt_service.py
│   │   └── prompt_service.py  # Prompt management (TTT-specific)
│   ├── TTS/                 # Text-to-Speech submodule
│   │   ├── __init__.py
│   │   └── tts_service.py
│   └── __init__.py
│
├── repos/                   # Data Access Layer
│   ├── schemas/             # Pydantic data contracts (moved from schemas/pydantic)
│   │   ├── __init__.py
│   │   ├── call_schema.py
│   │   ├── transcript_schema.py
│   │   ├── action_schema.py
│   │   └── appointment_schema.py
│   ├── entities/
│   ├── json_repo.py
│   ├── mongo_repo.py
│   └── global_data_repo.py
│
├── services/                # Business Logic & Runtime Services
│   ├── __init__.py
│   │
│   ├── infrastructure/      # ✅ Foundational runtime support
│   │   ├── __init__.py
│   │   ├── config_service.py    # Runtime configuration
│   │   ├── logger_service.py     # Logging configuration
│   │   ├── metrics_service.py    # Metrics collection
│   │   ├── audio_processor.py    # Audio I/O operations
│   │   └── vad_service.py        # Voice activity detection
│   │
│   ├── business/            # ✅ Domain-specific business logic
│   │   ├── __init__.py
│   │   ├── policy_service.py     # Business policies
│   │   ├── action_service.py     # Action execution
│   │   └── entity_service.py     # Entity extraction
│   │
│   ├── flows/               # Flow Orchestrators
│   │   ├── __init__.py
│   │   ├── stt_flow.py      # Speech-to-Text flow
│   │   ├── ttt_flow.py      # Text-to-Text flow
│   │   └── tts_flow.py      # Text-to-Speech flow
│   │
│   ├── receptionist/        # Receptionist Services
│   │   ├── __init__.py
│   │   ├── dialog_manager.py    # Conversation management
│   │   ├── intent_service.py     # Intent detection
│   │   └── handoff_service.py   # Human handoff
│   │
│   ├── platform/            # Platform Services
│   │   ├── __init__.py
│   │   ├── auth_service.py      # Authentication
│   │   ├── cache_service.py     # Caching
│   │   ├── notification_service.py  # Notifications
│   │   └── validation_service.py    # Data validation
│   │
│   └── integrations/        # External system integrations
│       ├── telephony/
│       │   ├── twilio_adapter.py
│       │   └── webhook_verifier.py
│       ├── calendar/
│       │   └── google_calendar.py
│       ├── crm/
│       │   ├── hubspot.py
│       │   └── zoho.py
│       ├── ticketing/
│       │   ├── zendesk.py
│       │   └── freshdesk.py
│       └── messaging/
│           ├── whatsapp_cloud.py
│           └── telegram.py
│
├── utility/                 # ✅ Utility Services (shared utilities)
│   ├── __init__.py
│   ├── helper_service.py    # Utility functions (IDs, timestamps, JSON, errors)
│   ├── memory_service.py    # Session/message orchestration
│   ├── rate_limiter.py      # Rate limiting enforcement
│   └── lang_detect_service.py  # Language detection
│
├── api/                     # API Layer
├── core/                    # Core Interfaces & Dependencies
├── tests/                   # Test Suite
└── main.py                  # Application Entry Point
```

## Refactoring Rationale

### 1. LLM Services Modularization (`llms/STT/`, `llms/TTT/`, `llms/TTS/`)

**Rationale:**
- **Separation of Concerns**: Each LLM service (STT, TTT, TTS) represents a distinct AI capability with different models, dependencies, and responsibilities.
- **Scalability**: As the project grows, each submodule can evolve independently (e.g., adding alternative STT providers, different LLM models, or TTS engines).
- **Clear Boundaries**: The subfolder structure makes it immediately clear which service handles which transformation pipeline stage.
- **Maintainability**: Changes to one service (e.g., upgrading Whisper for STT) don't affect the structure or imports of other services.

**Import Pattern:**
```python
from llms.STT.stt_service import STTService
from llms.TTT.ttt_service import TTTService
from llms.TTT.prompt_service import PromptService  # TTT-specific
from llms.TTS.tts_service import TTSService
```

**Why `prompt_service.py` is in `TTT/` submodule:**
- **Cohesion**: Prompts are exclusively used by the Text-to-Text (LLM) service. STT (transcription) and TTS (synthesis) don't require prompts.
- **Encapsulation**: TTT module owns all aspects of text generation, including prompt management, templates, and tools.
- **Single Responsibility**: Prompt strategies, A/B testing, and prompt variations are TTT-specific concerns.
- **Future-proofing**: If different LLM providers or prompt strategies are added, they belong within the TTT module.
- **Professional Practice**: Code should be placed close to where it's used, following the principle of high cohesion.

---

### 2. Schemas in Repository Layer (`repos/schemas/`)

**Rationale:**
- **Data Contracts = Persistence Contracts**: Pydantic schemas define the structure of data that flows through the persistence layer (repositories).
- **Cohesion**: Schemas are tightly coupled with entities and repositories - they define what data can be stored, retrieved, and validated.
- **Domain Alignment**: The repository pattern encapsulates data access logic, and schemas are part of that encapsulation.
- **Single Source of Truth**: Placing schemas in `repos/` ensures that data contracts are defined alongside the code that uses them, reducing the risk of schema-drift.

**Import Pattern:**
```python
from repos.schemas.call_schema import CallSchema
from repos.schemas.transcript_schema import TranscriptSchema
from repos.schemas.action_schema import ActionSchema
from repos.schemas.appointment_schema import AppointmentSchema
```

**Why not in a separate `schemas/` folder:**
- A standalone `schemas/` folder suggests schemas are independent of persistence logic, but in practice, they define the contracts for repository operations.
- Moving them to `repos/schemas/` makes the dependency explicit and groups related concerns together.

---

### 3. Integrations as Runtime Services (`services/integrations/`)

**Rationale:**
- **Runtime Behavior**: Integrations are active services that connect to external systems at runtime (Twilio, Google Calendar, HubSpot, etc.).
- **Service Layer Alignment**: They perform business operations (sending messages, creating calendar events, syncing CRM data) rather than just data access.
- **Consistency**: Other runtime services (like `dialog_manager`, `action_service`) live in `services/`, so integrations belong there too.
- **Dependency Management**: Integrations often require configuration, authentication, and error handling - concerns that align with the service layer.

**Import Pattern:**
```python
from services.integrations.telephony.twilio_adapter import TwilioAdapter
from services.integrations.calendar.google_calendar import GoogleCalendarService
from services.integrations.crm.hubspot import HubSpotAdapter
from services.integrations.ticketing.zendesk import ZendeskAdapter
from services.integrations.messaging.whatsapp_cloud import WhatsAppCloudAdapter
```

**Why not a top-level `integrations/` folder:**
- Integrations are not infrastructure components (like databases or message queues) - they're business services that execute operations.
- Placing them in `services/integrations/` makes it clear they're part of the application's runtime service layer.
- This structure allows for better dependency injection and testing, as integrations can be treated as service dependencies.

---

## Architecture Principles Applied

### 1. **Layered Architecture**
- **Presentation Layer**: `api/` (routes, middleware)
- **Business Logic Layer**: `services/` (flows, managers, integrations)
- **Data Access Layer**: `repos/` (repositories, schemas, entities)
- **AI/ML Layer**: `llms/` (STT, TTT, TTS services)

### 2. **Separation of Concerns**
- Each module has a single, well-defined responsibility
- LLM services are separated by transformation type
- Data contracts live with data access code
- Runtime services (including integrations) are grouped together

### 3. **Dependency Direction**
- Higher layers depend on lower layers
- Services depend on repositories (not vice versa)
- Flows depend on services (not vice versa)
- Clear import paths prevent circular dependencies

### 4. **Modularity & Scalability**
- Submodules can evolve independently
- New integrations can be added without restructuring
- Alternative LLM providers can be swapped per submodule
- Schema changes are localized to the repository layer

---

## Migration Summary

### Files Moved:
1. `llms/stt_service.py` → `llms/STT/stt_service.py`
2. `llms/ttt_service.py` → `llms/TTT/ttt_service.py`
3. `llms/tts_service.py` → `llms/TTS/tts_service.py`
4. `llms/prompt_service.py` → `llms/TTT/prompt_service.py` (TTT-specific)
5. `schemas/pydantic/*.py` → `repos/schemas/*.py`
6. `integrations/` → `services/integrations/`

### Imports Updated:
- ✅ `main.py` - Updated LLM service imports
- ✅ `services/stt_flow.py` - Updated STT import
- ✅ `services/ttt_flow.py` - Updated TTT import
- ✅ `services/tts_flow.py` - Updated TTS import
- ✅ `llms/__init__.py` - Re-exports for backward compatibility

### Backward Compatibility:
- `llms/__init__.py` provides re-exports, so old imports (`from llms import STTService`) still work
- However, new code should use explicit submodule imports for clarity

---

## Benefits of This Structure

1. **Improved Discoverability**: Developers can quickly find services by their function (STT/TTT/TTS) or by their layer (repos/services).
2. **Reduced Coupling**: Clear boundaries prevent accidental dependencies between unrelated modules.
3. **Easier Testing**: Each module can be tested in isolation with clear mock boundaries.
4. **Better Onboarding**: New developers can understand the architecture by following the folder structure.
5. **Future-Proof**: The structure supports adding new services, integrations, or LLM providers without major restructuring.

---

## Next Steps

When adding new components:
- **New LLM Service?** → Add to appropriate `llms/{STT|TTT|TTS}/` submodule
- **New Prompt/Template for LLM?** → Add to `llms/TTT/` (prompts are TTT-specific)
- **New Data Schema?** → Add to `repos/schemas/`
- **New Flow Orchestrator?** → Add to `services/flows/`
- **New Receptionist Feature?** → Add to `services/receptionist/`
- **New Platform Service?** → Add to `services/platform/`
- **New External Integration?** → Add to `services/integrations/{category}/`
- **New Core Business Service?** → Add to `services/` root

This structure ensures that every component has a clear, logical home.

---

## Services Folder Optimization

### Service Responsibilities

The `services/` folder contains runtime business logic and infrastructure services, each with a single, well-defined responsibility:

#### Core Infrastructure Services

**`logger_service.py`** - Centralized Logging Configuration
- Configures handlers (file and console)
- Sets up formatters with timestamps and log levels
- Manages log rotation and file paths
- Provides conversation logging utilities
- Links to CALL and REQUEST entities

**`config_service.py`** - Runtime Configuration
- Device detection (CUDA vs CPU, cuDNN availability)
- Audio device IDs and sample rates
- Model names and compute types
- Environment variable management
- Runtime detection logic (NOT static constants)

**`audio_processor.py`** - Audio I/O Operations
- Audio recording from input devices
- Audio decoding and format conversion
- Resampling to target sample rates
- Audio normalization and level adjustment
- Encoding for different output formats
- Works with VADService for voice activity detection

**`vad_service.py`** - Voice Activity Detection
- Loads and manages Silero VAD model
- Processes audio frames to detect speech probability
- Provides silence detection capabilities
- Built on audio_processor outputs

#### Business Logic Services

**`entity_service.py`** - Entity Extraction and Matching
- Dish name matching with fuzzy search
- Quantity extraction from text
- Multiple dish detection
- Phonetic corrections for Indian food terms
- Depends on IMenuRepository interface

**`action_service.py`** - Action Execution
- Executes order finalization with customer details
- Extracts customer information (name, phone)
- Saves order data to persistence layer
- Links actions to REQUEST entities

**`policy_service.py`** - Business Rules and Policies
- Restaurant hours and availability checks
- Item availability validation
- LLM query blocking rules
- Uses constants from `global_data.py` (RESTAURANT_OPEN_HOUR, OUT_OF_STOCK_ITEMS, FOOD_KEYWORDS)

**`dialog_manager.py`** - Conversation State Management
- Manages conversation state and dialog flow
- Coordinates entity extraction, actions, and policies
- Depends on service interfaces (not concrete implementations)

#### Utility Services

**`helper_service.py`** - Utility Functions
- ID generation (UUIDs, timestamps)
- Timestamp formatting and parsing
- Error handling helpers
- JSON serialization/deserialization utilities
- Centralizes common helper functions

**`memory_service.py`** - Session/Message Orchestration
- Manages conversation memory per session/call
- Links messages to CALL and REQUEST entities
- Provides context retrieval for dialog management
- Handles memory persistence and retrieval

**`rate_limiter.py`** - Rate Limit Enforcement
- Tracks request rates per user/session
- Writes RateLimitRecord entities when limits are exceeded
- Applies configurable rate limiting policies
- Uses constants from `global_data.py` (DEFAULT_RATE_LIMIT_PER_MINUTE, DEFAULT_RATE_LIMIT_PER_HOUR)

**`lang_detect_service.py`** - Language Detection
- Detects language from text input
- Produces LANGUAGE entities for persistence
- Supports multiple language detection strategies
- Links to CALL and REQUEST entities

#### Flow Orchestrators

**`stt_flow.py`** - Speech-to-Text Flow
- Orchestrates STT processing pipeline
- Coordinates audio recording and transcription

**`ttt_flow.py`** - Text-to-Text Flow
- Orchestrates LLM processing pipeline
- Coordinates dialog management and LLM generation

**`tts_flow.py`** - Text-to-Speech Flow
- Orchestrates TTS processing pipeline
- Coordinates text-to-speech conversion

### Separation of Concerns

Each service has a **single responsibility**:

- **Logger**: Only logging configuration and utilities
- **Config**: Only runtime configuration (device detection, environment variables)
- **Audio**: Only audio I/O operations (decode, resample, normalize, encode)
- **VAD**: Only voice activity detection (built on audio_processor outputs)
- **Entity**: Only entity extraction and matching
- **Action**: Only action execution
- **Policy**: Only business rules enforcement
- **Dialog**: Only conversation state management
- **Helper**: Only utility functions
- **Memory**: Only session/message orchestration
- **RateLimiter**: Only rate limit enforcement
- **LanguageDetection**: Only language detection logic

### Constants Management

**Static constants** are in `global_data.py`:
- Enums (Role, CallStatus, RequestType, AudioFormat)
- Default configurations (DEFAULT_SAMPLE_RATE, DEFAULT_VAD_THRESHOLD)
- Static mappings (LANGUAGES, INTENTS)
- Business rules constants (RESTAURANT_OPEN_HOUR, OUT_OF_STOCK_ITEMS, FOOD_KEYWORDS)

**Runtime configuration** is in `config_service.py`:
- Device detection (CUDA availability, cuDNN checks)
- Environment variable overrides
- Dynamic model selection
- Runtime audio device configuration

### Import Optimization

**Within `services/` folder**: Use relative imports
```python
from .config_service import ConfigService
from .audio_processor import AudioProcessor
from .vad_service import VADService
```

**From outside `services/`**: Use absolute imports
```python
from services.config_service import ConfigService
from services.logger_service import setup_logging
```

**Service exports**: Only necessary functions/classes exposed in `services/__init__.py`

### Benefits

1. **Clear Responsibilities**: Each service has one job, making code easier to understand and maintain
2. **Reduced Coupling**: Services depend on interfaces, not concrete implementations
3. **Easy Testing**: Each service can be tested in isolation
4. **Better Organization**: Related functionality is grouped together
5. **Constants Centralization**: Static values in `global_data.py`, runtime config in `config_service.py`
6. **Import Clarity**: Relative imports within services, absolute imports from outside

