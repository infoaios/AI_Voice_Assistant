# Setup and Run Guide - Unified Environment Setup

## 🚀 Quick Start

**One Command Setup & Run:**
```batch
setup_and_run.bat
```

This single batch file will:
1. ✅ Detect your GPU/RTX model automatically
2. ✅ Select the appropriate environment YAML file
3. ✅ Create or update the conda environment
4. ✅ Activate the environment
5. ✅ Run the application

## 📋 What the Script Does

### Step 1: GPU/RTX Detection
- Uses `nvidia-smi` to detect NVIDIA GPUs
- Uses PyTorch (`torch.cuda.get_device_name(0)`) if available (more accurate)
- Detects: RTX 3050, 3060, 3070, 3080, 5080, or CPU fallback

### Step 2: Environment Selection
Based on detected hardware:
- **RTX 3050** → `gpu3050_env.yml` → `voice_assistant_gpu3050`
- **RTX 3060/3070/3080** → `gpu3080_env.yml` → `voice_assistant_gpu3080`
- **RTX 5080** → `gpu5080_env.yml` → `voice_assistant_gpu5080`
- **No GPU** → `cpu_env.yml` → `voice_assistant_cpu`
- **Unknown GPU** → Defaults to `gpu3080_env.yml` (CUDA 11.8 compatible)

### Step 3: Environment Setup
- Checks if environment already exists
- Creates new environment if needed (takes 10-20 minutes)
- Optionally updates existing environment

### Step 4: Activation & Verification
- Activates the conda environment
- Verifies PyTorch installation
- Checks for required files

### Step 5: Run Application
- Runs `python main.py`
- Handles errors with troubleshooting tips

## 🔍 Detection Methods

The script uses multiple detection methods for reliability:

1. **Primary: nvidia-smi** (works without PyTorch)
   ```batch
   nvidia-smi --query-gpu=name --format=csv
   ```

2. **Secondary: PyTorch** (more accurate if available)
   ```python
   torch.cuda.get_device_name(0)
   ```

## 📁 Environment Files

All environment files are in `env/` directory:

| Hardware | YAML File | Environment Name |
|----------|-----------|------------------|
| CPU | `cpu_env.yml` | `voice_assistant_cpu` |
| RTX 3050 | `gpu3050_env.yml` | `voice_assistant_gpu3050` |
| RTX 3080/3060/3070 | `gpu3080_env.yml` | `voice_assistant_gpu3080` |
| RTX 5080 | `gpu5080_env.yml` | `voice_assistant_gpu5080` |

## ⚙️ Environment Configuration

### RTX 3050 Environment (`gpu3050_env.yml`)
- **Python**: 3.10
- **PyTorch**: 2.3.1 with CUDA 11.8
- **Transformers**: >=4.40.0,<4.46.0 (TTS 0.22.0 compatibility)
- **TTS**: 0.22.0
- **CUDA**: 11.8

**Note**: Your old setup used `transformers==4.46.0`, but TTS 0.22.0 requires transformers 4.40.0-4.45.0. The current environment files use `<4.46.0` to ensure compatibility. If you need 4.46.0, you may need to update TTS or adjust the version constraint.

## 🛠️ Manual Setup (Alternative)

If you prefer manual setup:

### 1. Detect Hardware
```batch
nvidia-smi
```

### 2. Create Environment
```batch
conda env create -f env\gpu3050_env.yml
```

### 3. Activate
```batch
conda activate voice_assistant_gpu3050
```

### 4. Run
```batch
python main.py
```

## 🔧 Troubleshooting

### Environment Creation Fails
1. Check conda: `conda --version`
2. Try mamba (faster): `mamba env create -f env\gpu3050_env.yml`
3. Check disk space (requires ~5GB)
4. Check internet connection

### GPU Not Detected
1. Verify NVIDIA drivers: `nvidia-smi`
2. Check CUDA installation
3. Script will fallback to CPU environment

### Application Fails to Run
1. Verify environment: `conda activate voice_assistant_gpu3050`
2. Check logs: `logs\assistant.log`
3. Verify data file: `data\restaurant_data.json`
4. Run verification: `scripts\verify.bat`

### Transformers Version Issue
If you get TTS errors related to transformers:
- Current env uses: `transformers>=4.40.0,<4.46.0`
- Your old setup used: `transformers==4.46.0`
- TTS 0.22.0 requires: 4.40.0-4.45.0

**Solution**: The current restriction is correct. If you need 4.46.0, consider:
- Updating TTS to a newer version that supports 4.46.0
- Or manually installing: `pip install transformers==4.45.0`

## 📝 Environment Update

To update an existing environment:
```batch
conda env update -f env\gpu3050_env.yml --prune
```

## ✅ Verification

After setup, verify installation:
```batch
conda activate voice_assistant_gpu3050
python -c "import torch; print('PyTorch:', torch.__version__); print('CUDA:', torch.cuda.is_available())"
```

## 🎯 Summary

**Single Command Solution:**
```batch
setup_and_run.bat
```

This handles everything automatically:
- ✅ GPU detection
- ✅ Environment selection
- ✅ Environment setup
- ✅ Application execution

---

**Created**: 2024  
**File**: `setup_and_run.bat`  
**Location**: Project root

