# Voice Platform - Quick Reference

Quick command reference for common tasks.

## 🚀 Setup & Installation

### First Time Setup

**Windows:**
```batch
scripts\setup.bat
```

**Linux/macOS:**
```bash
python env/setup_env.py
```

### Verify Installation

**Windows:**
```batch
scripts\verify.bat
```

**Linux/macOS:**
```bash
conda activate voice_assistant_gpu3080
python -c "import torch; print('CUDA:', torch.cuda.is_available())"
```

## ▶️ Running the Application

### Windows
```batch
scripts\run.bat
```

### Linux/macOS
```bash
conda activate voice_assistant_gpu3080
python -m voice_platform.main
```

### Using Entry Point
```bash
conda activate voice_assistant_gpu3080
voice-platform
```

## 🔧 Environment Management

### Activate Environment
```bash
# CPU
conda activate voice_assistant_cpu

# GPU (replace with your GPU type)
conda activate voice_assistant_gpu3080
```

### List Environments
```bash
conda env list
```

### Update Environment
```bash
conda env update -f env/<env_file>.yml --prune
```

### Remove Environment
```bash
conda env remove -n voice_assistant_<type>
```

## 📦 Dependency Management

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Update Dependencies
```bash
pip install --upgrade -r requirements.txt
```

### Development Tools
Uncomment the development tools section in `requirements.txt` if needed

## 🧹 Cleanup

### Windows
```batch
scripts\clean.bat
```

### Manual Cleanup
```bash
# Remove Python cache
find . -type d -name __pycache__ -exec rm -r {} +
find . -name "*.pyc" -delete

# Remove build artifacts
rm -rf build/ dist/ *.egg-info
```

## 🐛 Troubleshooting

### Check GPU
```bash
nvidia-smi
```

### Check CUDA in Python
```python
import torch
print('CUDA available:', torch.cuda.is_available())
print('CUDA version:', torch.version.cuda)
```

### Check Audio Devices
```python
import sounddevice as sd
print(sd.query_devices())
```

### View Logs
```bash
# Windows
type logs\assistant.log

# Linux/macOS
cat logs/assistant.log
```

## 📁 Important Files

- **Data**: `data/restaurant_data.json` (required)
- **Voice**: `data/saved_voices/refe2.wav` (optional)
- **Config**: `services/infrastructure/config_service.py`
- **Logs**: `logs/assistant.log`

## 🔗 Quick Links

- **Setup Guide**: [SETUP_GUIDE.md](SETUP_GUIDE.md)
- **Project Structure**: [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)
- **Environment Docs**: [env/README.md](env/README.md)
- **Scripts Docs**: [scripts/README.md](scripts/README.md)

---

**Tip**: Bookmark this page for quick access to common commands!

