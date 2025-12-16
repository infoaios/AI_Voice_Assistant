# Voice Platform - Complete Setup Guide

Welcome to the Voice Platform! This guide will help you set up the project on any PC, whether you're working alone or as part of a team.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start (Automated)](#quick-start-automated)
3. [Manual Setup](#manual-setup)
4. [Environment Options](#environment-options)
5. [Verification](#verification)
6. [Running the Application](#running-the-application)
7. [Team Collaboration](#team-collaboration)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

1. **Anaconda or Miniconda**
   - Download: https://www.anaconda.com/products/distribution
   - Or Miniconda: https://docs.conda.io/en/latest/miniconda.html
   - Verify installation: `conda --version`

2. **Python 3.10+**
   - Included with Anaconda/Miniconda
   - Verify: `python --version`

3. **Git** (for team collaboration)
   - Download: https://git-scm.com/downloads

### Hardware Requirements

- **CPU**: Any modern CPU (Intel/AMD)
- **GPU** (Optional but recommended):
  - NVIDIA GPU with CUDA support (RTX 3050, 3080, 5080, or compatible)
  - Minimum 4GB VRAM for GPU acceleration
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: ~10GB free space (for models and dependencies)

---

## Quick Start (Automated)

### Windows

1. **Clone or download the project**
   ```batch
   git clone <repository-url>
   cd voice_platform
   ```

2. **Run automated setup**
   ```batch
   scripts\setup.bat
   ```
   This will:
   - Detect your hardware (CPU/GPU)
   - Create the appropriate conda environment
   - Install all dependencies

3. **Verify installation**
   ```batch
   scripts\verify.bat
   ```

4. **Run the application**
   ```batch
   scripts\run.bat
   ```

### Linux/macOS

1. **Clone the project**
   ```bash
   git clone <repository-url>
   cd voice_platform
   ```

2. **Run automated setup**
   ```bash
   python env/setup_env.py
   ```

3. **Activate environment and run**
   ```bash
   conda activate voice_assistant_<gpu_type>
   python -m voice_platform.main
   ```

---

## Manual Setup

If automated setup doesn't work, follow these steps:

### Step 1: Detect Your Hardware

**Check for GPU:**
```bash
# Windows
nvidia-smi

# Linux/macOS
nvidia-smi --query-gpu=name --format=csv
```

**Determine environment:**
- **No GPU or CUDA not available** → Use `cpu_env.yml`
- **RTX 3050** → Use `gpu3050_env.yml`
- **RTX 3080 or RTX 3060/3070** → Use `gpu3080_env.yml`
- **RTX 5080 or newer** → Use `gpu5080_env.yml`
- **Unknown NVIDIA GPU** → Use `gpu3080_env.yml` (most compatible)

### Step 2: Create Conda Environment

```bash
# For CPU
conda env create -f env/cpu_env.yml

# For RTX 3050
conda env create -f env/gpu3050_env.yml

# For RTX 3080
conda env create -f env/gpu3080_env.yml

# For RTX 5080
conda env create -f env/gpu5080_env.yml
```

### Step 3: Activate Environment

```bash
# CPU
conda activate voice_assistant_cpu

# GPU (replace with your GPU type)
conda activate voice_assistant_gpu3080
```

### Step 4: Install Additional Dependencies (Optional)

Install all dependencies:
```bash
pip install -r requirements.txt
```

For development tools, uncomment them in `requirements.txt`

### Step 5: Verify Installation

```bash
python -c "import torch; print('PyTorch:', torch.__version__); print('CUDA:', torch.cuda.is_available())"
python -c "import transformers; print('Transformers:', transformers.__version__)"
python -c "from faster_whisper import WhisperModel; print('Faster Whisper: OK')"
python -c "from TTS.api import TTS; print('Coqui TTS: OK')"
```

---

## Environment Options

### Available Environments

| Environment | File | CUDA Version | Use Case |
|------------|------|--------------|----------|
| CPU | `cpu_env.yml` | N/A | Development, testing, no GPU |
| RTX 3050 | `gpu3050_env.yml` | 11.8 | Entry-level GPU |
| RTX 3080 | `gpu3080_env.yml` | 11.8 | Most common, best compatibility |
| RTX 5080 | `gpu5080_env.yml` | 12.4 | Latest GPUs, best performance |

### Requirements Files

| File | Purpose |
|------|---------|
| `requirements.txt` | All dependencies (production + optional dev tools) |

---

## Verification

### Quick Verification

**Windows:**
```batch
scripts\verify.bat
```

**Linux/macOS:**
```bash
python scripts/verify.py  # If available
```

### Manual Verification

Check these packages:
- ✅ PyTorch (with CUDA if GPU available)
- ✅ Transformers
- ✅ Faster Whisper
- ✅ Coqui TTS
- ✅ FastAPI
- ✅ Audio libraries (sounddevice, soundfile)

### Required Files

Ensure these files exist:
- ✅ `data/restaurant_data.json` (required)
- ✅ `data/saved_voices/refe2.wav` (optional, for voice cloning)

---

## Running the Application

### Windows

**Option 1: Using batch script (Recommended)**
```batch
scripts\run.bat
```

**Option 2: Manual**
```batch
conda activate voice_assistant_gpu3080
cd voice_platform
python main.py
```

### Linux/macOS

```bash
conda activate voice_assistant_gpu3080
cd voice_platform
python main.py
```

### Using Entry Point (if installed)

```bash
conda activate voice_assistant_gpu3080
voice-platform
```

---

## Team Collaboration

### For New Team Members

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd voice_platform
   ```

2. **Run setup**
   ```batch
   # Windows
   scripts\setup.bat
   
   # Linux/macOS
   python env/setup_env.py
   ```

3. **Verify installation**
   ```batch
   # Windows
   scripts\verify.bat
   ```

4. **Start developing!**

### Environment Variables

Create a `.env` file (not committed to git) for local configuration:
```env
# Example .env file
API_KEY=your_api_key_here
DATABASE_URL=mongodb://localhost:27017
LOG_LEVEL=INFO
```

### Git Workflow

1. **Never commit:**
   - Conda environments (`.conda/`)
   - Python cache (`__pycache__/`, `*.pyc`)
   - Build artifacts (`build/`, `dist/`, `*.egg-info`)
   - Model cache (`.cache/`)
   - Personal config files (`.env.local`)

2. **Always commit:**
   - Environment YAML files (`env/*.yml`)
   - Requirements files (`requirements*.txt`)
   - Source code
   - Documentation

---

## Troubleshooting

### Common Issues

#### 1. Conda Not Found
**Error**: `conda: command not found`

**Solution**:
- Install Anaconda or Miniconda
- Or use "Anaconda Prompt" on Windows
- Or add conda to PATH manually

#### 2. CUDA Version Mismatch
**Error**: `CUDA runtime version mismatch`

**Solution**:
1. Check CUDA version: `nvidia-smi`
2. Ensure PyTorch CUDA version matches
3. Reinstall PyTorch with correct CUDA:
   ```bash
   conda install pytorch torchvision torchaudio pytorch-cuda=11.8 -c pytorch -c nvidia
   ```

#### 3. Out of Memory (OOM)
**Error**: `CUDA out of memory`

**Solution**:
- Use CPU environment for development
- Reduce batch size in model loading
- Use smaller models
- Close other GPU-intensive applications

#### 4. Package Conflicts
**Error**: `Solving environment: failed`

**Solution**:
1. Create fresh environment:
   ```bash
   conda env remove -n voice_assistant_gpu3080
   conda env create -f env/gpu3080_env.yml
   ```
2. Or use mamba (faster solver):
   ```bash
   mamba env create -f env/gpu3080_env.yml
   ```

#### 5. Audio Device Not Found
**Error**: `No audio device found`

**Solution**:
1. Check audio devices:
   ```python
   import sounddevice as sd
   print(sd.query_devices())
   ```
2. Update device IDs in `services/infrastructure/config_service.py`

#### 6. Missing Data Files
**Error**: `restaurant_data.json not found`

**Solution**:
1. Create `data/` folder in project root
2. Place `restaurant_data.json` in `data/` folder
3. See `data/README.md` for data structure

### Getting Help

1. **Check logs**: `logs/assistant.log`
2. **Run verification**: `scripts\verify.bat`
3. **Check documentation**: `docs/` folder
4. **Review error messages**: Most scripts provide troubleshooting tips

---

## Next Steps

After setup:

1. ✅ Read [README.md](README.md) for project overview
2. ✅ Check [docs/](docs/) for detailed documentation
3. ✅ Review [QUICK_START.md](QUICK_START.md) for quick reference
4. ✅ Explore the codebase structure
5. ✅ Run your first voice interaction!

---

## Additional Resources

- **Environment Setup**: `env/README.md`
- **Architecture**: `docs/architecture/`
- **API Documentation**: `docs/api/` (if available)
- **Development Guide**: `docs/development/`

---

**Happy Coding! 🚀**

For questions or issues, please check the troubleshooting section or refer to the project documentation.

