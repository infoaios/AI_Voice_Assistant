# Voice Platform - Project Structure

This document provides an overview of the optimized project structure for easy maintenance and team collaboration.

## 📁 Directory Structure

```
voice_platform/
├── 📄 SETUP_GUIDE.md          # Complete setup instructions
├── 📄 PROJECT_STRUCTURE.md    # This file
├── 📄 README.md               # Main project documentation
├── 📄 QUICK_START.md          # Quick reference
│
├── 📁 api/                    # API layer
│   ├── middleware/           # Auth, error handling, rate limiting
│   └── routes/               # API endpoints
│
├── 📁 core/                   # Core interfaces and exceptions
│   ├── interfaces.py         # Protocol definitions
│   ├── exceptions.py         # Custom exceptions
│   └── dependencies.py       # Dependency injection
│
├── 📁 llms/                   # LLM services
│   ├── STT/                  # Speech-to-Text (Whisper)
│   ├── TTT/                  # Text-to-Text (TinyLlama)
│   └── TTS/                  # Text-to-Speech (XTTS v2)
│
├── 📁 repos/                  # Data access layer
│   ├── entities/             # Domain entities
│   ├── schemas/              # Pydantic schemas
│   ├── json_repo.py          # JSON repository
│   └── mongo_repo.py         # MongoDB repository
│
├── 📁 services/               # Business logic services
│   ├── infrastructure/       # Foundational services
│   ├── business/             # Domain-specific logic
│   ├── flows/                # Flow orchestrators
│   ├── receptionist/         # Receptionist services
│   ├── platform/             # Platform services
│   └── integrations/         # External integrations
│
├── 📁 utility/                # Utility services
│   ├── helper_service.py
│   ├── memory_service.py
│   ├── rate_limiter.py
│   └── lang_detect_service.py
│
├── 📁 scripts/                # Automation scripts ⭐ NEW
│   ├── README.md             # Scripts documentation
│   ├── setup.bat             # Environment setup (Windows)
│   ├── run.bat               # Run application (Windows)
│   ├── verify.bat            # Verify installation (Windows)
│   ├── clean.bat             # Cleanup script (Windows)
│   └── setup_env.py          # Cross-platform setup
│
├── 📁 env/                    # Environment configurations ⭐ OPTIMIZED
│   ├── README.md             # Environment documentation
│   ├── cpu_env.yml           # CPU environment
│   ├── gpu3050_env.yml       # RTX 3050 environment
│   ├── gpu3080_env.yml       # RTX 3080 environment
│   ├── gpu5080_env.yml       # RTX 5080 environment
│   └── setup_env.py          # Setup script
│
├── 📄 requirements.txt       # All dependencies in one file
│
├── 📁 data/                   # Data files
│   ├── restaurant_data.json  # Restaurant menu data
│   └── saved_voices/         # Voice clone files
│
├── 📁 docs/                   # Documentation
│   ├── architecture/         # Architecture docs
│   ├── configuration/        # Configuration guides
│   ├── development/          # Development docs
│   ├── environment/          # Environment setup
│   └── flows/                # Flow documentation
│
├── 📁 tests/                  # Test suite
├── 📁 prompts/                # Prompt templates
├── 📁 logs/                   # Application logs (gitignored)
│
├── 📄 main.py                 # Application entry point
├── 📄 setup.py                # Package installation
└── 📄 .gitignore             # Git ignore rules
```

## 🎯 Key Improvements

### 1. **Consolidated Requirements** ⭐
- **`requirements.txt`**: All dependencies in one file
- Development tools are commented out (uncomment if needed)

### 2. **Professional Scripts** ⭐
- **`scripts/setup.bat`**: Automated environment setup
- **`scripts/run.bat`**: Run application with auto-detection
- **`scripts/verify.bat`**: Verify installation
- **`scripts/clean.bat`**: Cleanup temporary files

### 3. **Better Documentation** ⭐
- **`SETUP_GUIDE.md`**: Complete onboarding guide
- **`env/README.md`**: Environment-specific documentation
- **`scripts/README.md`**: Scripts documentation

### 4. **Cleaner Structure**
- Clear separation of concerns
- Hardware-aware environment setup
- Team-friendly organization

## 🚀 Quick Commands

### Setup
```batch
# Windows
scripts\setup.bat

# Linux/macOS
python env/setup_env.py
```

### Run
```batch
# Windows
scripts\run.bat

# Linux/macOS
conda activate voice_assistant_gpu3080
python -m voice_platform.main
```

### Verify
```batch
# Windows
scripts\verify.bat
```

### Clean
```batch
# Windows
scripts\clean.bat
```

## 📦 Dependency Management

### Installation Options

**Install All Dependencies:**
```bash
pip install -r requirements.txt
```

**For Development Tools:**
Uncomment the development tools section in `requirements.txt`

## 🔧 Environment Management

### Available Environments

| Environment | File | CUDA | Use Case |
|------------|------|------|----------|
| CPU | `cpu_env.yml` | N/A | Development, no GPU |
| RTX 3050 | `gpu3050_env.yml` | 11.8 | Entry-level GPU |
| RTX 3080 | `gpu3080_env.yml` | 11.8 | Most common |
| RTX 5080 | `gpu5080_env.yml` | 12.4 | Latest GPUs |

### Environment Operations

**Create:**
```bash
conda env create -f env/<env_file>.yml
```

**Update:**
```bash
conda env update -f env/<env_file>.yml --prune
```

**Remove:**
```bash
conda env remove -n voice_assistant_<type>
```

## 📝 File Organization Principles

### ✅ What to Commit
- Source code (`*.py`)
- Configuration files (`*.yml`, `*.toml`)
- Documentation (`*.md`)
- Environment files (`env/*.yml`)
- Requirements files (`requirements*.txt`)
- Scripts (`scripts/*.bat`, `scripts/*.py`)

### ❌ What NOT to Commit
- Python cache (`__pycache__/`, `*.pyc`)
- Build artifacts (`build/`, `dist/`, `*.egg-info`)
- Environment directories (`.conda/`, `venv/`)
- Log files (`logs/*.log`)
- Model cache (`.cache/`)
- Personal config (`.env.local`)

## 🎓 For New Team Members

1. **Read**: `SETUP_GUIDE.md`
2. **Run**: `scripts\setup.bat` (Windows) or `python env/setup_env.py` (Linux/macOS)
3. **Verify**: `scripts\verify.bat`
4. **Start**: `scripts\run.bat`

## 📚 Documentation Index

- **Setup**: `SETUP_GUIDE.md`
- **Quick Start**: `QUICK_START.md`
- **Architecture**: `docs/architecture/`
- **Environment**: `env/README.md`
- **Scripts**: `scripts/README.md`
- **Development**: `docs/development/`

---

**Last Updated**: 2025-01-XX
**Maintained By**: Development Team

