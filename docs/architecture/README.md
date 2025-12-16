# Architecture Documentation

Architecture analysis, dependency management, and design patterns.

## Available Documents

- **[ARCHITECTURE_ANALYSIS.md](ARCHITECTURE_ANALYSIS.md)** - Complete architecture analysis with coupling review
- **[DEPENDENCY_ANALYSIS.md](DEPENDENCY_ANALYSIS.md)** - Dependency mapping and refactoring plan
- **[BOUNDARIES_AND_CONTRACTS.md](BOUNDARIES_AND_CONTRACTS.md)** - Boundaries, contracts, and change impact analysis

## Key Concepts

### Stable Interfaces
Interfaces in `core/interfaces.py` define stable contracts that rarely change. This allows implementation changes without affecting dependents.

### Dependency Inversion
High-level modules depend on abstractions (interfaces), not concrete implementations. This reduces coupling.

### Clear Boundaries
Layers are clearly separated with defined dependency rules. Changes are localized within layers.

## Quick Reference

| Need to... | See Document |
|------------|--------------|
| Understand architecture | [ARCHITECTURE_ANALYSIS.md](ARCHITECTURE_ANALYSIS.md) |
| Analyze dependencies | [DEPENDENCY_ANALYSIS.md](DEPENDENCY_ANALYSIS.md) |
| Understand boundaries | [BOUNDARIES_AND_CONTRACTS.md](BOUNDARIES_AND_CONTRACTS.md) |

