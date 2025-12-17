# Quick Fix: Install cuDNN

## 🚨 Issue
Your environment is set up correctly, but cuDNN is missing. This is required for TTS (Text-to-Speech) to work.

## ✅ Quick Fix

**Option 1: Run the cuDNN installer script**
```batch
# Activate your environment first
conda activate voice_assistant_gpu3050

# Run the installer
env\install_cudnn.bat
```

**Option 2: Manual installation (conda-forge - Recommended)**
```batch
conda activate voice_assistant_gpu3050
conda install -c conda-forge cudnn -y
```

**Option 2b: Alternative (pip method)**
```batch
conda activate voice_assistant_gpu3050
pip install nvidia-pyindex
pip install nvidia-cudnn
```

**Option 3: Update environment (recommended)**
```batch
conda activate voice_assistant_gpu3050
conda env update -f env\gpu3050_env.yml --prune
```

## ✅ Verify Installation

After installing, verify:
```batch
python -c "import torch; print('cuDNN Available:', torch.backends.cudnn.is_available())"
```

Should output: `cuDNN Available: True`

## 🚀 Then Run Application

```batch
python main.py
```

Or use the unified script again:
```batch
env\setup_and_run.bat
```

---

**Note**: The `setup_and_run.bat` script has been updated to automatically check and install cuDNN if missing for future setups.

