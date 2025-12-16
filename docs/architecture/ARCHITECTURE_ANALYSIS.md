# Architecture Analysis: Coupling & Dependency Management

## 🎯 Goal: Minimize Cross-File Impact

**Principle**: Changes to one file should not unnecessarily affect other files. This is achieved through:
- **Stable Interfaces**: Define contracts that rarely change
- **Dependency Inversion**: Depend on abstractions, not concretions
- **Clear Boundaries**: Enforce separation between layers
- **Localized Changes**: Changes to implementations don't affect dependents

## 📊 Current Dependency Analysis

### Dependency Graph

```
┌─────────────────────────────────────────────────────────────┐
│                    main.py (Entry Point)                    │
│              (Orchestrates all components)                  │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                     │
        ▼                   ▼                     ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  services/   │    │    llms/     │    │   repos/     │
│  (Business)  │    │  (AI Models) │    │  (Data)      │
└──────────────┘    └──────────────┘    └──────────────┘
        │                   │                     │
        └───────────────────┼─────────────────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │   core/      │
                    │ (Interfaces) │
                    └──────────────┘
```

### Current Dependency Issues

#### ❌ Issue 1: Direct Concrete Dependencies
**Problem**: Services depend on concrete classes instead of interfaces

**Current**:
```python
# dialog_manager.py
from repos.json_repo import JSONRepository  # Concrete class
from repos.entities.order_entity import OrderManager  # Concrete class
```

**Impact**: Changing `JSONRepository` implementation affects `DialogManager`

**Solution**: Depend on interfaces from `core/interfaces.py`

#### ❌ Issue 2: Cross-Layer Dependencies
**Problem**: `llms/` depends on `services/` and `repos/`

**Current**:
```python
# llms/ttt_service.py
from services.config_service import LLM_MODEL, LLM_DEVICE  # services/
from repos.json_repo import JSONRepository  # repos/
```

**Impact**: Changes in `services/` or `repos/` affect LLM layer

**Solution**: LLM layer should only depend on `core/` (interfaces and config)

#### ❌ Issue 3: Tight Coupling in DialogManager
**Problem**: `DialogManager` directly depends on 4 different services

**Current**:
```python
class DialogManager:
    def __init__(self, json_repo, entity_service, action_service, policy_service):
        # 4 direct dependencies
```

**Impact**: Changes to any service affect `DialogManager`

**Solution**: Use interfaces and reduce direct dependencies

#### ❌ Issue 4: Missing Abstractions
**Problem**: No protocols/interfaces for repositories and services

**Impact**: Can't swap implementations without changing dependents

**Solution**: Create interfaces in `core/interfaces.py`

## ✅ Proposed Architecture (Layered)

### Layer Hierarchy (Dependency Direction)

```
┌─────────────────────────────────────────┐
│  Layer 1: Application (main.py)        │  ← Top level
│  - Orchestrates flows                   │
│  - Depends on: Services, LLMs, Repos   │
└─────────────────────────────────────────┘
                    │
        ┌───────────┼───────────┐
        │           │           │
        ▼           ▼           ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│ Services │ │   LLMs   │ │  Repos   │  ← Layer 2: Domain
│ (Business│ │  (AI)    │ │  (Data)  │
│  Logic)  │ │          │ │          │
└──────────┘ └──────────┘ └──────────┘
        │           │           │
        └───────────┼───────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │   Core (Interfaces)   │  ← Layer 3: Abstractions
        │   - IMenuRepository   │
        │   - IEntityService    │
        │   - IOrderManager     │
        └───────────────────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │   Infrastructure     │  ← Layer 4: External
        │   - Config            │
        │   - Logging           │
        │   - Global Data       │
        └───────────────────────┘
```

### Dependency Rules

1. **Application Layer** → Can depend on Services, LLMs, Repos
2. **Services/LLMs/Repos** → Can depend on Core (interfaces) and Infrastructure
3. **Core** → No dependencies (pure interfaces)
4. **Infrastructure** → No dependencies on domain logic

### ❌ Forbidden Dependencies

- ❌ Services → LLMs (use interfaces)
- ❌ LLMs → Services (use interfaces)
- ❌ Repos → Services (use interfaces)
- ❌ Core → Anything (pure abstractions)

## 🔧 Refactoring Plan

### Step 1: Create Core Abstractions ✅
- [x] `core/interfaces.py` - Protocol definitions
- [x] `core/dependencies.py` - DI Container
- [x] `core/exceptions.py` - Exception hierarchy

### Step 2: Update Repositories
- [ ] Make `JSONRepository` implement `IMenuRepository`
- [ ] Create order persistence interface
- [ ] Update dependents to use interfaces

### Step 3: Update Services
- [ ] Make services implement interfaces
- [ ] Update `DialogManager` to depend on interfaces
- [ ] Remove direct concrete dependencies

### Step 4: Update LLM Services
- [ ] Remove dependencies on `services/` (except config)
- [ ] Use interfaces for repository access
- [ ] Inject dependencies instead of importing

### Step 5: Update Flows
- [ ] Use interfaces in flows
- [ ] Reduce coupling between flows

## 📋 Stable Interfaces (Contracts)

### IMenuRepository
```python
@runtime_checkable
class IMenuRepository(Protocol):
    def get_menu(self) -> List[Dict[str, Any]]: ...
    def get_restaurant_info(self) -> Dict[str, Any]: ...
    def all_menu_items(self) -> Generator[Tuple[Dict, Dict], None, None]: ...
```

**Stability**: High - Menu structure rarely changes
**Impact of Changes**: Low - Only affects if menu schema changes

### IEntityService
```python
@runtime_checkable
class IEntityService(Protocol):
    def find_all_dish_matches(self, text: str, ...) -> List[Tuple]: ...
    def extract_quantity(self, text: str, default: int = 1) -> int: ...
```

**Stability**: High - Entity extraction API is stable
**Impact of Changes**: Low - Implementation can change without affecting callers

### IOrderManager
```python
@runtime_checkable
class IOrderManager(Protocol):
    def add_item(self, ...) -> None: ...
    def remove_item(self, ...) -> None: ...
    def to_json(self) -> Dict[str, Any]: ...
```

**Stability**: High - Order operations are well-defined
**Impact of Changes**: Low - Can change internal structure without breaking interface

## 🎯 Benefits of This Architecture

### 1. Localized Changes
- ✅ Change `JSONRepository` implementation → Only affects repository layer
- ✅ Change `EntityService` algorithm → Only affects service implementation
- ✅ Change `OrderManager` internals → Only affects entity

### 2. Testability
- ✅ Mock interfaces for testing
- ✅ Swap implementations easily
- ✅ Isolated unit tests

### 3. Flexibility
- ✅ Swap `JSONRepository` for `MongoRepository` without changing services
- ✅ Change LLM provider without changing business logic
- ✅ Add new services without breaking existing code

### 4. Maintainability
- ✅ Clear boundaries between layers
- ✅ Stable contracts reduce breaking changes
- ✅ Easy to understand dependencies

## 📊 Coupling Metrics

### Current Coupling (Before Refactoring)
- **DialogManager**: 4 direct dependencies
- **EntityService**: 1 direct dependency
- **TTTService**: 2 direct dependencies
- **TTTFlow**: 3 direct dependencies

### Target Coupling (After Refactoring)
- **DialogManager**: 4 interface dependencies (stable)
- **EntityService**: 1 interface dependency (stable)
- **TTTService**: 1 interface dependency (stable)
- **TTTFlow**: 3 interface dependencies (stable)

### Impact Analysis

| Change Type | Current Impact | Target Impact |
|------------|----------------|---------------|
| Change JSONRepository implementation | Affects 3 files | Affects 0 files (interface stable) |
| Change EntityService algorithm | Affects 1 file | Affects 1 file (interface stable) |
| Change OrderManager internals | Affects 2 files | Affects 0 files (interface stable) |
| Change DialogManager logic | Affects 1 file | Affects 1 file (interface stable) |

## 🚀 Next Steps

1. **Implement interfaces** in existing classes
2. **Update imports** to use interfaces
3. **Add type hints** with protocols
4. **Create adapter layer** if needed
5. **Update tests** to use interfaces

## 📚 Related Documentation

- [Configuration Architecture](../configuration/CONFIG_ARCHITECTURE.md)
- [Production Review](../reference/PRODUCTION_REVIEW.md)

