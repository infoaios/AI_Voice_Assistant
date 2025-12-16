# Quick Start Guide

## 🚀 Fastest Setup

### Option 1: Automatic Detection (Recommended)
```bash
python env/setup_env.py
```

This script will:
1. Detect your hardware (CPU/GPU model)
2. Select the appropriate environment
3. Create the conda environment automatically

### Option 2: Manual Selection

#### For CPU-only systems:
```bash
conda env create -f env/cpu_env.yml
conda activate voice_assistant_cpu
```

#### For RTX 3080:
```bash
conda env create -f env/gpu3080_env.yml
conda activate voice_assistant_gpu3080
```

#### For RTX 5080:
```bash
conda env create -f env/gpu5080_env.yml
conda activate voice_assistant_gpu5080
```

## ✅ Verify Installation

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

## 🎯 Environment Comparison

| Feature | CPU | RTX 3080 | RTX 5080 |
|---------|-----|----------|----------|
| PyTorch CUDA | None | 11.8 | 12.4 |
| Compute Type | int8 | int8_float16 | float16/int8_float16 |
| Latency | High | Low | Lowest |
| VRAM Usage | N/A | ~2-3GB | ~3-4GB |
| Best For | Dev/Test | Production | Production |

## 📝 Next Steps

1. **Activate environment**: `conda activate voice_assistant_gpu3080`
2. **Run application**: `python -m voice_platform.main`
3. **Check configuration**: Edit `services/config_service.py` if needed

## 🐛 Common Issues

### "CUDA not available" on GPU system
- Check CUDA driver: `nvidia-smi`
- Verify PyTorch CUDA: `python -c "import torch; print(torch.version.cuda)"`
- Reinstall PyTorch with correct CUDA version

### "Out of memory"
- Use `int8_float16` compute type (already configured)
- Reduce batch size
- Use CPU for Whisper if needed

### "Audio device not found"
- List devices: `python -c "import sounddevice as sd; print(sd.query_devices())"`
- Update `INPUT_DEVICE` and `OUTPUT_DEVICE` in `config_service.py`

For detailed information, see [README.md](README.md).

