# Running the Application

Complete guide on how to set up the environment and run the voice assistant application.

## ⭐ Easiest Way: Setup & Run

### Windows (Recommended)

```batch
# First time: Setup environment
scripts\setup.bat

# Then: Run application
scripts\run.bat
```

### Linux/macOS

```bash
# First time: Setup environment
python env/setup_env.py

# Then: Activate and run
conda activate voice_assistant_gpu3080
python -m voice_platform.main
```

This will:
1. ✅ Detect your hardware (CPU/RTX 3080/RTX 5080)
2. ✅ Check if environment exists
3. ✅ Create environment if needed
4. ✅ Run the application

---

## 📋 Manual Steps (Alternative)

### Step 1: Set Up Environment

#### Option A: Automatic Setup (Recommended)
```bash
# From project root
python env/setup_env.py
```

This will:
1. Detect your hardware (CPU/RTX 3080/RTX 5080)
2. Create the appropriate conda environment
3. Install all dependencies

#### Option B: Windows Batch Script
```batch
# From voice_platform/env/ folder
install_windows_voice_assistant.bat
```

#### Option C: Manual Setup
```bash
# For RTX 3080 (most common)
conda env create -f env/gpu3080_env.yml
conda activate voice_assistant_gpu3080

# For RTX 5080
conda env create -f env/gpu5080_env.yml
conda activate voice_assistant_gpu5080

# For CPU-only
conda env create -f env/cpu_env.yml
conda activate voice_assistant_cpu
```

### Step 2: Activate Environment

```bash
# Activate the environment (choose based on your hardware)
conda activate voice_assistant_gpu3080
# OR
conda activate voice_assistant_gpu5080
# OR
conda activate voice_assistant_cpu
```

### Step 3: Verify Installation

```bash
# Check PyTorch and CUDA
python -c "import torch; print('PyTorch:', torch.__version__); print('CUDA:', torch.cuda.is_available())"

# Check all dependencies
python -c "
import torch
import transformers
from faster_whisper import WhisperModel
from TTS.api import TTS
import sounddevice as sd
import fastapi
import pymongo
print('✅ All dependencies OK!')
"
```

### Step 4: Install Package (Optional but Recommended)

```bash
# Install package in development mode
pip install -e .
```

This allows you to use the entry point command: `voice-platform`

### Step 5: Ensure Required Files

Make sure these files exist:
- `data/restaurant_data.json` - Restaurant menu data
- `data/saved_voices/refe2.wav` - Voice clone file

See [File Structure Guide](FILE_STRUCTURE.md) for details.

## 🎯 Running the Application

### Method 1: Using Entry Point (After `pip install -e .`)

```bash
# Activate environment
conda activate voice_assistant_gpu3080

# Run using entry point
voice-platform
```

### Method 2: Using Python Module

```bash
# Activate environment
conda activate voice_assistant_gpu3080

# Run as module
python -m voice_platform.main
```

### Method 3: Direct Python Execution

```bash
# Activate environment
conda activate voice_assistant_gpu3080

# Navigate to voice_platform directory
cd voice_platform

# Run directly
python main.py
```

### Method 4: From Project Root

```bash
# Activate environment
conda activate voice_assistant_gpu3080

# From project root (AI_voice_assistent_final/)
python -m voice_platform.main
```

## 📋 Complete Workflow Example

### First-Time Setup:

```bash
# 1. Navigate to project root
cd D:\kinjal\AI_voice_assistent_final

# 2. Set up environment automatically
python voice_platform/env/setup_env.py

# 3. Activate environment (based on detected hardware)
conda activate voice_assistant_gpu3080

# 4. Verify installation
python -c "import torch; print('CUDA:', torch.cuda.is_available())"

# 5. Install package (optional)
pip install -e .

# 6. Run application
voice-platform
# OR
python -m voice_platform.main
```

### Daily Usage:

```bash
# 1. Activate environment
conda activate voice_assistant_gpu3080

# 2. Run application
voice-platform
```

## 🔧 Troubleshooting

### Error: "ModuleNotFoundError"
**Solution**: Make sure you've activated the conda environment:
```bash
conda activate voice_assistant_gpu3080
```

### Error: "CUDA not available" (on GPU system)
**Solution**: 
1. Check CUDA driver: `nvidia-smi`
2. Verify PyTorch CUDA: `python -c "import torch; print(torch.version.cuda)"`
3. Reinstall PyTorch with correct CUDA version

### Error: "Voice file not found"
**Solution**: 
1. Ensure `data/saved_voices/refe2.wav` exists
2. Or update `VOICE_CLONE_WAV` in `services/config_service.py`

### Error: "restaurant_data.json not found"
**Solution**: 
1. Create `data/restaurant_data.json` in project root
2. See [File Structure Guide](FILE_STRUCTURE.md) for format

### Error: "Audio device not found"
**Solution**:
1. List devices: `python -c "import sounddevice as sd; print(sd.query_devices())"`
2. Update `INPUT_DEVICE` and `OUTPUT_DEVICE` in `services/config_service.py`

## 📝 Environment Variables

You can override configuration using environment variables:

```bash
# Set environment variables before running
set WHISPER_MODEL=distil-whisper/distil-large-v3
set WHISPER_COMPUTE_TYPE=int8_float16
set LLM_MODEL=TinyLlama/TinyLlama-1.1B-Chat-v1.0

# Then run
voice-platform
```

## 🎯 Quick Reference

| Task | Command |
|------|---------|
| Setup environment | `python env/setup_env.py` |
| Activate environment | `conda activate voice_assistant_gpu3080` |
| Verify installation | `python -c "import torch; print(torch.cuda.is_available())"` |
| Install package | `pip install -e .` |
| Run application | `voice-platform` or `python -m voice_platform.main` |

## 📚 Related Documentation

- [Environment Setup Guide](../env/README.md)
- [File Structure Guide](FILE_STRUCTURE.md)
- [Configuration Guide](../configuration/WHISPER_CONFIG_NOTES.md)
- [Quick Start](../environment/QUICK_START.md)

