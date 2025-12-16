# Quick Start Guide

## 🚀 Run Your Application - Easiest Way

### ⭐ Quick Start (Recommended)

**Windows:**
```batch
# First time: Setup environment
scripts\setup.bat

# Then: Run application
scripts\run.bat
```

**Linux/macOS:**
```bash
# First time: Setup environment
python env/setup_env.py

# Then: Activate and run
conda activate voice_assistant_gpu3080
python -m voice_platform.main
```

This will:
1. ✅ Detect your hardware
2. ✅ Create environment if needed
3. ✅ Run the application

---

## 📋 Manual Steps (Alternative)

### Step 1: Set Up Environment

```bash
# Automatic setup (detects your hardware)
python env/setup_env.py
```

### Step 2: Activate Environment

```bash
# Based on your hardware (example for RTX 3080)
conda activate voice_assistant_gpu3080
```

### Step 3: Run Application

```bash
# Option 1: Using entry point (after pip install -e .)
voice-platform

# Option 2: Using Python module
python -m voice_platform.main

# Option 3: Direct execution
cd voice_platform
python main.py
```

## 📋 Complete Example

```bash
# 1. Setup (one-time)
python env/setup_env.py

# 2. Activate environment
conda activate voice_assistant_gpu3080

# 3. (Optional) Install package
pip install -e .

# 4. Run
voice-platform
```

## ✅ Before Running

Make sure these files exist:
- `data/restaurant_data.json` - Menu data
- `data/saved_voices/refe2.wav` - Voice clone file

## 📚 Full Documentation

- [Complete Running Guide](docs/guides/RUNNING_THE_APPLICATION.md)
- [Environment Setup](env/README.md)
- [File Structure](docs/guides/FILE_STRUCTURE.md)

