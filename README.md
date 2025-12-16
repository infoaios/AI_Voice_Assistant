# Voice Platform - AI Voice Assistant

A professional, modular AI voice assistant platform for restaurants with Speech-to-Text, Text-to-Text, and Text-to-Speech capabilities.

## 🚀 Quick Start

### Windows (Recommended)

```batch
# First time setup (detects hardware automatically)
scripts\setup.bat

# Verify installation
scripts\verify.bat

# Run application
scripts\run.bat
```

### Linux/macOS

```bash
# First time setup
python env/setup_env.py

# Activate environment
conda activate voice_assistant_gpu3080

# Run application
python -m voice_platform.main
```


## 📋 Prerequisites

- **Anaconda or Miniconda** - [Download](https://www.anaconda.com/products/distribution)
- **Python 3.10+** (included with Conda)
- **NVIDIA GPU** (optional but recommended for best performance)
  - RTX 3050, 3080, 5080, or compatible
  - Minimum 4GB VRAM

## ⚡ Quick Commands

### Setup & Installation
```batch
# Windows
scripts\setup.bat              # Auto-detect hardware and setup
scripts\verify.bat               # Verify installation

# Linux/macOS
python env/setup_env.py         # Setup
conda activate voice_assistant_gpu3080
```

### Running
```batch
# Windows
scripts\run.bat

# Linux/macOS
conda activate voice_assistant_gpu3080
python -m voice_platform.main
```

### Environment Management
```bash
# List environments
conda env list

# Update environment
conda env update -f env/gpu3080_env.yml --prune

# Remove environment
conda env remove -n voice_assistant_gpu3080
```

### Dependencies
```bash
# Install all dependencies
pip install -r requirements.txt

# For development tools, uncomment them in requirements.txt
```

## 📁 Project Structure

```
voice_platform/
├── api/                    # API layer (FastAPI)
├── core/                   # Core interfaces & exceptions
├── llms/                   # LLM services (STT/TTT/TTS)
│   ├── STT/              # Speech-to-Text (Whisper)
│   ├── TTT/              # Text-to-Text (TinyLlama)
│   └── TTS/              # Text-to-Speech (XTTS v2)
├── repos/                  # Data access layer
├── services/              # Business logic
│   ├── infrastructure/   # Config, logging, audio
│   ├── business/         # Domain logic
│   ├── flows/            # Flow orchestrators
│   ├── receptionist/     # Dialog management
│   └── integrations/     # External APIs
├── scripts/               # Automation scripts
│   ├── setup.bat        # Environment setup
│   ├── run.bat          # Run application
│   ├── verify.bat       # Verify installation
│   └── clean.bat        # Cleanup
├── env/                   # Conda environments
│   ├── cpu_env.yml      # CPU environment
│   ├── gpu3050_env.yml  # RTX 3050
│   ├── gpu3080_env.yml  # RTX 3080 (most common)
│   └── gpu5080_env.yml  # RTX 5080
├── docs/                  # Documentation
├── data/                  # Data files
└── tests/                 # Test suite
```

## 🎯 Key Features

- **Hardware-Aware Setup**: Automatically detects CPU/GPU and configures environment
- **Modular Architecture**: Clean separation of concerns, easy to maintain
- **Multiple LLM Services**: Whisper (STT), TinyLlama (TTT), XTTS v2 (TTS)
- **Professional Scripts**: One-command setup and run
- **Team-Friendly**: Consistent setup across all machines

## 🔧 Configuration

### Environment Selection

| Hardware | Environment File | CUDA |
|----------|----------------|------|
| CPU only | `cpu_env.yml` | N/A |
| RTX 3050 | `gpu3050_env.yml` | 11.8 |
| RTX 3080 | `gpu3080_env.yml` | 11.8 |
| RTX 5080 | `gpu5080_env.yml` | 12.4 |

### Runtime Configuration

Edit `services/infrastructure/config_service.py`:
- Device settings (CPU/GPU)
- Model paths
- Audio device IDs
- Sample rates

### Required Files

- `data/restaurant_data.json` - Menu data (required)
- `data/saved_voices/refe2.wav` - Voice clone (optional)

## 📚 Documentation

### Getting Started
- **[Complete Setup Guide](docs/guides/SETUP_GUIDE.md)** - Detailed setup instructions
- **[Quick Reference](docs/guides/QUICK_REFERENCE.md)** - Command cheat sheet
- **[Project Structure](docs/guides/PROJECT_STRUCTURE.md)** - Detailed structure overview

### Scripts & Automation
- **[scripts/README.md](scripts/README.md)** - Scripts documentation
- **[env/README.md](env/README.md)** - Environment configuration

### Technical Documentation
- **[Architecture](docs/architecture/)** - System architecture
- **[Configuration](docs/configuration/)** - Configuration guides
- **[Development](docs/development/)** - Development docs
- **[Guides](docs/guides/)** - User guides

See [docs/README.md](docs/README.md) for complete documentation index.

## 🛠️ Key Components

### Infrastructure Services
- **config_service.py**: Runtime configuration
- **logger_service.py**: Logging setup
- **audio_processor.py**: Audio recording
- **vad_service.py**: Voice Activity Detection

### Business Services
- **policy_service.py**: Business rules
- **action_service.py**: Order finalization
- **entity_service.py**: Entity extraction & matching

### Receptionist Services
- **dialog_manager.py**: Main conversation handler
- **intent_service.py**: Intent detection
- **handoff_service.py**: Human handoff

## 🐛 Troubleshooting

### Common Issues

**Conda not found:**
- Install Anaconda/Miniconda
- Use "Anaconda Prompt" on Windows

**CUDA version mismatch:**
```bash
# Check CUDA version
nvidia-smi

# Reinstall PyTorch with correct CUDA
conda install pytorch torchvision torchaudio pytorch-cuda=11.8 -c pytorch -c nvidia
```

**Out of memory:**
- Use CPU environment for development
- Reduce batch size
- Close other GPU applications

**Package conflicts:**
```bash
# Create fresh environment
conda env remove -n voice_assistant_gpu3080
conda env create -f env/gpu3080_env.yml
```

**Audio device not found:**
```python
import sounddevice as sd
print(sd.query_devices())  # Check available devices
# Update device IDs in config_service.py
```

### Getting Help

1. Run verification: `scripts\verify.bat`
2. Check logs: `logs/assistant.log`
3. Review documentation: `docs/guides/`
4. See [Setup Guide](docs/guides/SETUP_GUIDE.md) troubleshooting section

## 🚀 Adding New Features

1. **Infrastructure**: `services/infrastructure/`
2. **Business Logic**: `services/business/`
3. **Flow**: `services/flows/`
4. **Receptionist**: `services/receptionist/`
5. **Integration**: `services/integrations/{category}/`
6. **API Endpoint**: `api/routes/`
7. **LLM Service**: `llms/{STT|TTT|TTS}/`

## 📦 Dependencies

### Base (Minimal)
- PyTorch, Transformers, Faster Whisper, TTS
- FastAPI, Pydantic
- Audio libraries

### Production
- Base + MongoDB, Requests, Monitoring

### Development
- Production + Testing, Code quality tools

## 🤝 Team Collaboration

### For New Team Members

1. Clone repository
2. Run `scripts\setup.bat` (Windows) or `python env/setup_env.py` (Linux/macOS)
3. Run `scripts\verify.bat` to verify
4. Start developing!

### Git Workflow

**Commit:**
- Source code, configs, docs
- Environment files (`env/*.yml`)
- Requirements files

**Don't Commit:**
- Python cache (`__pycache__/`)
- Build artifacts (`build/`, `dist/`)
- Environment directories
- Log files
- Model cache

## 📝 License

[Add your license here]

## 🙏 Acknowledgments

[Add acknowledgments if any]

---

**Need help?** Check [docs/guides/SETUP_GUIDE.md](docs/guides/SETUP_GUIDE.md) for detailed instructions.
