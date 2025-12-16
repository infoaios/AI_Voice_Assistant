# Configuration Architecture

This document explains the clear separation of concerns between `setup.py`, `global_data.py`, and `config_service.py`.

## 📋 Overview

| File | Purpose | What Goes Here | What NOT to Put Here |
|------|---------|----------------|---------------------|
| **setup.py** | Packaging & Installation | Project metadata, dependencies, entry points | Runtime configs, device detection |
| **global_data.py** | Static Constants | Enums, default values, static mappings | Dynamic device detection, runtime values |
| **config_service.py** | Runtime Configuration | Device detection, model paths, environment vars | Static enums, packaging info |

## ⚙️ setup.py

**Purpose**: Packaging & installation metadata for pip/pdm

### ✅ What Goes Here:
- Project name, version, author, license
- Dependencies (`install_requires`)
- Entry points (console scripts)
- Package discovery (`find_packages()`)
- Optional dependencies (`extras_require`)
- Classifiers

### ❌ NOT for:
- Runtime configuration
- Device detection (like `torch.cuda.is_available()`)
- Model names or paths
- Audio device IDs
- Environment variables

### Example:
```python
setup(
    name="voice_platform",
    version="0.1.0",
    install_requires=["torch", "transformers", ...],
    entry_points={"console_scripts": [...]},
)
```

## 🌍 global_data.py

**Purpose**: Shared constants, enums, and default configs (static values)

### ✅ What Goes Here:
- **Enums**: Roles, statuses, request types, audio formats
- **Default configs**: Default STT/TTT/TTS engine names, default voice, default rate limits
- **Static mappings**: Language codes → names, intent keys → descriptions
- **Constants**: Default thresholds, sample rates (as static values)

### ❌ NOT for:
- Dynamic device detection (like `torch.cuda.is_available()`)
- Runtime configuration
- Environment variable reading
- Model paths that change

### Example:
```python
class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"

DEFAULT_STT_ENGINE = "whisper"
LANGUAGES = {"en": "English", "hi": "Hindi"}
```

## 🛠️ config_service.py

**Purpose**: Runtime configuration service (dynamic values)

### ✅ What Goes Here:
- **Device detection**: `torch.cuda.is_available()` → CUDA vs CPU
- **Audio device IDs**: Input/output device numbers
- **Model names and paths**: Whisper model, LLM model, TTS model
- **Compute types**: Optimized for device (int8_float16 for CUDA, int8 for CPU)
- **Environment variables**: Reading from `os.getenv()`
- **Methods**: `get_device_config()`, `get_audio_config()`, `get_model_config()`

### ❌ NOT for:
- Static enums (use `global_data.py`)
- Packaging metadata (use `setup.py`)
- Default values that never change (use `global_data.py`)

### Example:
```python
WHISPER_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "distil-whisper/distil-large-v3")
INPUT_DEVICE = int(os.getenv("INPUT_DEVICE", "1"))
```

## 🔄 How They Work Together

```
┌─────────────────┐
│   setup.py      │  ← Installation metadata
│   (packaging)   │     Dependencies, entry points
└─────────────────┘
         │
         │ imports
         ▼
┌─────────────────┐
│ global_data.py  │  ← Static constants
│   (constants)   │     Enums, defaults, mappings
└─────────────────┘
         │
         │ imports
         ▼
┌─────────────────┐
│config_service.py│  ← Runtime configuration
│  (runtime cfg)  │     Device detection, env vars
└─────────────────┘
         │
         │ used by
         ▼
┌─────────────────┐
│  main.py        │  ← Application entry point
│  services/      │     Uses config_service
└─────────────────┘
```

## 📝 Best Practices

### ✅ DO:
- Put static enums in `global_data.py`
- Put device detection in `config_service.py`
- Put dependencies in `setup.py`
- Import defaults from `global_data.py` in `config_service.py`

### ❌ DON'T:
- Put `torch.cuda.is_available()` in `global_data.py`
- Put enums in `config_service.py`
- Put runtime config in `setup.py`
- Hardcode device values in `global_data.py`

## 🔍 Quick Reference

| Need to... | Use File |
|------------|----------|
| Add a new dependency | `setup.py` |
| Add a new enum/constant | `global_data.py` |
| Detect GPU availability | `config_service.py` |
| Set default engine name | `global_data.py` |
| Read environment variable | `config_service.py` |
| Add console script | `setup.py` |
| Set default rate limit | `global_data.py` |
| Configure audio device | `config_service.py` |

## 📚 Related Documentation

- [Whisper Configuration](WHISPER_CONFIG_NOTES.md)
- [File Structure](../guides/FILE_STRUCTURE.md)
- [Production Review](../reference/PRODUCTION_REVIEW.md)

