# Dependency Analysis & Coupling Review

## 🔍 Current Dependency Map

### Import Dependencies (Current State)

```
main.py
├── services/config_service
├── services/logger_service
├── services/vad_service
├── services/audio_processor
├── services/entity_service
│   └── repos/json_repo
├── services/action_service
│   └── repos/entities/order_entity
├── services/policy_service
├── services/dialog_manager
│   ├── repos/json_repo
│   ├── repos/entities/order_entity
│   ├── services/entity_service
│   ├── services/action_service
│   └── services/policy_service
├── services/stt_flow
│   ├── llms/stt_service
│   └── services/audio_processor
├── services/ttt_flow
│   ├── llms/ttt_service
│   │   ├── services/config_service
│   │   └── repos/json_repo
│   ├── services/dialog_manager
│   └── services/policy_service
└── services/tts_flow
    └── llms/tts_service
        └── services/config_service
```

## ⚠️ Identified Issues

### 1. Circular Dependency Risk
**Location**: `services/` ↔ `llms/`
- `services/ttt_flow` imports `llms/ttt_service`
- `llms/ttt_service` imports `services/config_service`
- `services/stt_flow` imports `llms/stt_service`
- `llms/stt_service` imports `services/config_service`

**Impact**: Medium - Currently works but fragile
**Solution**: Move config to `core/` or use dependency injection

### 2. Tight Coupling in DialogManager
**Location**: `services/dialog_manager.py`
- Depends on 4 different services directly
- Depends on concrete repository classes

**Impact**: High - Changes to any dependency affect DialogManager
**Solution**: Use interfaces and reduce dependencies

### 3. Cross-Layer Dependencies
**Location**: `llms/` → `repos/`, `services/`
- `llms/ttt_service` imports `repos/json_repo`
- `llms/ttt_service` imports `services/config_service`

**Impact**: Medium - LLM layer shouldn't know about data layer
**Solution**: Inject dependencies, use interfaces

### 4. Missing Abstractions
**Location**: All modules
- No interfaces/protocols defined
- Direct concrete class dependencies

**Impact**: High - Can't swap implementations
**Solution**: Create interfaces in `core/interfaces.py`

## ✅ Proposed Solutions

### Solution 1: Move Config to Core
**Current**: `services/config_service.py`
**Proposed**: `core/config.py` or keep in services but make it infrastructure

**Rationale**: Config is infrastructure, not business logic

### Solution 2: Use Interfaces
**Current**: Direct concrete dependencies
**Proposed**: Depend on protocols from `core/interfaces.py`

**Example**:
```python
# Before
from repos.json_repo import JSONRepository

# After
from core.interfaces import IMenuRepository
```

### Solution 3: Dependency Injection
**Current**: Direct imports in constructors
**Proposed**: Inject dependencies via constructor

**Example**:
```python
# Before
class EntityService:
    def __init__(self, json_repo: JSONRepository):
        self.json_repo = json_repo

# After
class EntityService:
    def __init__(self, menu_repo: IMenuRepository):
        self.menu_repo = menu_repo
```

### Solution 4: Separate Infrastructure
**Current**: Config mixed with services
**Proposed**: Create `infrastructure/` layer

```
infrastructure/
├── config.py
├── logging.py
└── paths.py
```

## 📊 Dependency Direction (Target)

### Correct Dependency Flow

```
Application (main.py)
    ↓
Domain (services/, llms/, repos/)
    ↓
Core (interfaces, protocols)
    ↓
Infrastructure (config, logging, global_data)
```

### Rules

1. **Application** can depend on Domain
2. **Domain** can depend on Core and Infrastructure
3. **Core** can depend on Infrastructure (for types only)
4. **Infrastructure** has no dependencies on Domain

## 🔧 Refactoring Checklist

### Phase 1: Create Abstractions ✅
- [x] Create `core/interfaces.py`
- [x] Create `core/dependencies.py`
- [x] Create `core/exceptions.py`

### Phase 2: Update Repositories
- [ ] Make `JSONRepository` implement `IMenuRepository`
- [ ] Update `EntityService` to use `IMenuRepository`
- [ ] Update `DialogManager` to use `IMenuRepository`

### Phase 3: Update Services
- [ ] Make `EntityService` implement `IEntityService`
- [ ] Make `PolicyService` implement `IPolicyService`
- [ ] Make `ActionService` implement `IActionService`
- [ ] Update `DialogManager` to use interfaces

### Phase 4: Update LLM Services
- [ ] Remove direct `repos/` imports from `llms/`
- [ ] Inject `IMenuRepository` instead
- [ ] Move config access to infrastructure

### Phase 5: Update Flows
- [ ] Update flows to use interfaces
- [ ] Reduce coupling between flows

## 📈 Impact Assessment

### Before Refactoring
- **Files affected by JSONRepository change**: 3
- **Files affected by EntityService change**: 1
- **Files affected by OrderManager change**: 2
- **Total coupling points**: 15+

### After Refactoring
- **Files affected by JSONRepository change**: 0 (interface stable)
- **Files affected by EntityService change**: 0 (interface stable)
- **Files affected by OrderManager change**: 0 (interface stable)
- **Total coupling points**: 0 (all through interfaces)

## 🎯 Success Criteria

1. ✅ No circular dependencies
2. ✅ Clear dependency direction
3. ✅ Stable interfaces for all contracts
4. ✅ Changes to implementations don't affect dependents
5. ✅ Easy to swap implementations
6. ✅ Testable with mocks

