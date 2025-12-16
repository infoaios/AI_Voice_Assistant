# Scripts Directory

This directory contains automation scripts for the Voice Platform project.

## Available Scripts

### Windows Batch Scripts

#### `setup.bat`
**Purpose**: Automatically detects hardware and sets up the appropriate conda environment.

**Usage**:
```batch
scripts\setup.bat
```

**Features**:
- Auto-detects GPU (RTX 3050, 3080, 5080, or CPU)
- Creates appropriate conda environment
- Updates existing environments if needed
- Provides clear error messages and troubleshooting tips

#### `run.bat`
**Purpose**: Runs the Voice Platform application.

**Usage**:
```batch
scripts\run.bat
```

**Features**:
- Auto-detects and activates the correct conda environment
- Verifies required files exist
- Runs the application with proper environment setup
- Provides error handling and troubleshooting

#### `verify.bat`
**Purpose**: Verifies that the environment is set up correctly.

**Usage**:
```batch
scripts\verify.bat
```

**Features**:
- Checks all critical packages are installed
- Verifies PyTorch, CUDA, and ML libraries
- Checks required data files exist
- Provides detailed status report

#### `clean.bat`
**Purpose**: Cleans up temporary files, cache, and optionally removes environments.

**Usage**:
```batch
scripts\clean.bat
```

**Features**:
- Removes Python cache files (`__pycache__`, `.pyc`)
- Cleans build artifacts (`build/`, `dist/`, `*.egg-info`)
- Optionally cleans log files
- Optionally cleans model cache
- Optionally removes conda environments

## Python Scripts

#### `setup_env.py`
**Purpose**: Cross-platform Python script for environment setup.

**Usage**:
```bash
python scripts\setup_env.py
# or
python env\setup_env.py
```

**Features**:
- Works on Windows, Linux, and macOS
- Hardware detection
- Interactive environment creation

## Quick Start

1. **First Time Setup**:
   ```batch
   scripts\setup.bat
   ```

2. **Verify Installation**:
   ```batch
   scripts\verify.bat
   ```

3. **Run Application**:
   ```batch
   scripts\run.bat
   ```

## Troubleshooting

### Scripts not working?
- Ensure you're running from the project root directory
- Check that conda is in your PATH
- Try running from "Anaconda Prompt" instead of regular command prompt

### Environment not found?
- Run `scripts\setup.bat` to create the environment
- Or manually: `conda env create -f env\<env_file>.yml`

### Permission errors?
- Run command prompt as Administrator
- Check that you have write permissions to the project directory

## Notes

- All scripts use relative paths and work from the project root
- Scripts automatically detect the correct environment based on hardware
- Error messages include troubleshooting tips
- Scripts are designed to be safe and non-destructive (except `clean.bat`)

