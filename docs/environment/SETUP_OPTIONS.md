# Environment Setup Options

You have **two ways** to set up the conda environment:

## Option 1: Standalone Script (Before Package Install) ⭐ Recommended

**Use this if**: You haven't installed the package yet, or want to set up the environment first.

```bash
# From project root
python env/setup_env.py
```

**Advantages**:
- ✅ Works before package installation
- ✅ No dependencies required
- ✅ Can be run from anywhere
- ✅ Standalone script

**Location**: `env/setup_env.py`

---

## Option 2: Console Script (After Package Install)

**Use this if**: You've already installed the package via `pip install -e .`

```bash
# After installing the package
voice-platform-setup-env
```

**Advantages**:
- ✅ Integrated into package
- ✅ Available as command-line tool
- ✅ Consistent with other package commands

**Location**: `voice_platform/scripts/setup_env.py` (installed as `voice-platform-setup-env`)

---

## Which One Should I Use?

### For First-Time Setup (Recommended):
```bash
# 1. Clone/download project
cd AI_voice_assistent_final

# 2. Run standalone setup script
python env/setup_env.py

# 3. Activate environment
conda activate voice_assistant_gpu3080  # or your detected environment

# 4. (Optional) Install package in development mode
pip install -e .
```

### For Development:
```bash
# If package is already installed
voice-platform-setup-env

# Or use standalone
python env/setup_env.py
```

---

## Technical Details

### Standalone Script (`env/setup_env.py`)
- **Purpose**: Initial environment setup
- **Dependencies**: None (uses subprocess for conda)
- **Location**: `env/setup_env.py`
- **Usage**: `python env/setup_env.py`

### Installable Script (`scripts/setup_env.py`)
- **Purpose**: Same functionality, but installable
- **Dependencies**: Package must be installed
- **Location**: `voice_platform/scripts/setup_env.py`
- **Usage**: `voice-platform-setup-env` (after `pip install -e .`)

Both scripts:
- ✅ Detect hardware automatically
- ✅ Select appropriate environment
- ✅ Create conda environment
- ✅ Provide same functionality

---

## Recommendation

**Use Option 1 (standalone)** for initial setup, as it:
1. Works immediately without installation
2. Sets up the environment first
3. Then you can install the package in the environment

**Use Option 2 (console script)** if you've already installed the package and want a convenient command.

