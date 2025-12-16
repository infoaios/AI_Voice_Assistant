# Boundaries & Contracts: Minimizing Cross-File Impact

## 🎯 Core Principle

**"If I change one file, it should not reflect in another file"**

This is achieved through:
1. **Stable Interfaces** - Define contracts that rarely change
2. **Dependency Inversion** - Depend on abstractions, not concretions
3. **Clear Boundaries** - Enforce separation between layers
4. **Localized Changes** - Implementation changes don't affect dependents

## 📐 Architecture Layers

### Layer 1: Application (Entry Point)
**Location**: `main.py`

**Responsibilities**:
- Orchestrates all components
- Dependency injection
- Application lifecycle

**Dependencies**: Can depend on all layers below

**Stability**: Changes frequently (orchestration logic)

---

### Layer 2: Domain (Business Logic)
**Locations**: `services/`, `llms/`, `repos/`

**Responsibilities**:
- Business logic
- AI model services
- Data access

**Dependencies**: Can depend on Core (interfaces) and Infrastructure

**Stability**: Changes moderately (business rules evolve)

**Key Rule**: Domain modules should NOT depend on each other directly

---

### Layer 3: Core (Abstractions)
**Location**: `core/`

**Responsibilities**:
- Define stable interfaces/protocols
- Exception hierarchy
- Dependency injection container

**Dependencies**: None (pure abstractions)

**Stability**: Changes rarely (only when contracts change)

**Key Rule**: This is the most stable layer - changes here affect all dependents

---

### Layer 4: Infrastructure
**Locations**: `services/config_service.py`, `services/logger_service.py`, `global_data.py`

**Responsibilities**:
- Configuration
- Logging
- Static constants

**Dependencies**: None on domain logic

**Stability**: Changes infrequently

---

## 🔒 Stable Contracts (Interfaces)

### IMenuRepository
**Purpose**: Abstract menu data access

**Stability**: ⭐⭐⭐⭐⭐ (Very High)
- Menu structure rarely changes
- Implementation can change without affecting callers

**Impact of Changes**:
- ✅ Change `JSONRepository` → MongoDB → **0 files affected** (interface stable)
- ❌ Change `IMenuRepository` interface → **3 files affected** (contract change)

### IEntityService
**Purpose**: Abstract entity extraction

**Stability**: ⭐⭐⭐⭐⭐ (Very High)
- Entity extraction API is stable
- Algorithm can change without affecting callers

**Impact of Changes**:
- ✅ Change matching algorithm → **0 files affected** (interface stable)
- ❌ Change `IEntityService` interface → **1 file affected** (contract change)

### IOrderManager
**Purpose**: Abstract order management

**Stability**: ⭐⭐⭐⭐⭐ (Very High)
- Order operations are well-defined
- Internal structure can change

**Impact of Changes**:
- ✅ Change order storage format → **0 files affected** (interface stable)
- ❌ Change `IOrderManager` interface → **2 files affected** (contract change)

## 📊 Change Impact Analysis

### Scenario 1: Change JSONRepository Implementation

**Before (Direct Dependency)**:
```
JSONRepository (implementation change)
    ↓ affects
EntityService
    ↓ affects
DialogManager
    ↓ affects
TTTFlow
    ↓ affects
main.py

Total: 4 files affected
```

**After (Interface Dependency)**:
```
JSONRepository (implementation change)
    ↓ (implements IMenuRepository)
    ↓ (interface unchanged)
    ↓ (no impact)

Total: 0 files affected ✅
```

### Scenario 2: Change EntityService Algorithm

**Before (Direct Dependency)**:
```
EntityService (algorithm change)
    ↓ affects
DialogManager

Total: 1 file affected
```

**After (Interface Dependency)**:
```
EntityService (algorithm change)
    ↓ (implements IEntityService)
    ↓ (interface unchanged)
    ↓ (no impact)

Total: 0 files affected ✅
```

### Scenario 3: Change OrderManager Internals

**Before (Direct Dependency)**:
```
OrderManager (internal change)
    ↓ affects
ActionService
    ↓ affects
DialogManager

Total: 2 files affected
```

**After (Interface Dependency)**:
```
OrderManager (internal change)
    ↓ (implements IOrderManager)
    ↓ (interface unchanged)
    ↓ (no impact)

Total: 0 files affected ✅
```

## 🛡️ Boundary Enforcement

### Rule 1: Services Don't Import from LLMs
**Current**: ❌ `services/stt_flow.py` imports `llms/stt_service.py`
**Solution**: ✅ Use `ISTTService` interface

### Rule 2: LLMs Don't Import from Services (except infrastructure)
**Current**: ❌ `llms/ttt_service.py` imports `services/config_service.py`
**Solution**: ✅ Move config to `infrastructure/` or use dependency injection

### Rule 3: Repos Don't Import from Services
**Current**: ✅ Already correct
**Solution**: ✅ Maintain this

### Rule 4: Core Has No Dependencies
**Current**: ✅ Already correct
**Solution**: ✅ Maintain this

## 🔄 Dependency Injection Pattern

### Before (Tight Coupling)
```python
# dialog_manager.py
from repos.json_repo import JSONRepository  # Concrete class
from services.entity_service import EntityService  # Concrete class

class DialogManager:
    def __init__(self):
        self.repo = JSONRepository()  # Hard dependency
        self.entity = EntityService(JSONRepository())  # Hard dependency
```

**Problem**: Can't swap implementations, tight coupling

### After (Loose Coupling)
```python
# dialog_manager.py
from core.interfaces import IMenuRepository, IEntityService

class DialogManager:
    def __init__(self, menu_repo: IMenuRepository, entity_service: IEntityService):
        self.menu_repo = menu_repo  # Interface dependency
        self.entity_service = entity_service  # Interface dependency
```

**Benefit**: Can swap implementations, loose coupling

## 📋 Implementation Status

### ✅ Completed
- [x] Created `core/interfaces.py` with protocol definitions
- [x] Created `core/dependencies.py` for DI container
- [x] Created `core/exceptions.py` for exception hierarchy
- [x] Updated `EntityService` to use `IMenuRepository`
- [x] Updated `DialogManager` to use interfaces
- [x] Updated flows to use interfaces

### 🔄 In Progress
- [ ] Make all repositories implement interfaces
- [ ] Make all services implement interfaces
- [ ] Update all dependents to use interfaces
- [ ] Move config to infrastructure layer

### 📝 Documentation
- [x] Architecture analysis document
- [x] Dependency analysis document
- [x] Boundaries and contracts document

## 🎯 Success Metrics

### Coupling Reduction
- **Before**: 15+ direct dependencies
- **After**: 0 direct dependencies (all through interfaces)

### Change Impact
- **Before**: Average 2-3 files affected per change
- **After**: 0 files affected (implementation changes)

### Testability
- **Before**: Hard to mock dependencies
- **After**: Easy to mock (use interfaces)

## 📚 Related Documentation

- [Architecture Analysis](ARCHITECTURE_ANALYSIS.md)
- [Dependency Analysis](DEPENDENCY_ANALYSIS.md)
- [Configuration Architecture](../configuration/CONFIG_ARCHITECTURE.md)

