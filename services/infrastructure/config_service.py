"""
Runtime Configuration Service

This module handles runtime configuration with device detection:
- Device detection (CUDA vs CPU)
- Audio device IDs
- Model names and compute types
- Environment variables
- Methods to return structured configs

❌ NOT for static constants or enums (use global_data.py)
✅ This is for dynamic runtime configuration
"""
import os
import torch
from pathlib import Path
from typing import Dict, Optional

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    # Load .env from project root
    project_root = Path(__file__).parent.parent.parent
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"[INFO] Loaded configuration from .env file")
except ImportError:
    # python-dotenv not installed, continue without .env support
    pass
except Exception as e:
    print(f"[WARN] Could not load .env file: {e}")

# Import static defaults from global_data
# Note: global_data.py is in the project root
try:
    from global_data import (
        DEFAULT_SAMPLE_RATE,
        DEFAULT_VAD_THRESHOLD,
        DEFAULT_MAX_SILENCE,
        DEFAULT_STT_ENGINE,
        DEFAULT_TTT_ENGINE,
        DEFAULT_TTS_ENGINE,
    )
except ImportError:
    # Fallback if running from different path
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from global_data import (
        DEFAULT_SAMPLE_RATE,
        DEFAULT_VAD_THRESHOLD,
        DEFAULT_MAX_SILENCE,
        DEFAULT_STT_ENGINE,
        DEFAULT_TTT_ENGINE,
        DEFAULT_TTS_ENGINE,
    )

# ========== RUNTIME DEVICE DETECTION ==========
# These are determined at runtime based on available hardware and .env file

# Read device settings from .env file or use defaults
LLM_DEVICE_ENV = os.getenv("LLM_DEVICE", "cuda").lower()
TTS_DEVICE_ENV = os.getenv("TTS_DEVICE", "cuda").lower()
WHISPER_DEVICE_ENV = os.getenv("WHISPER_DEVICE", "cpu").lower()

# Validate device values
valid_devices = ["cuda", "cpu"]
if LLM_DEVICE_ENV not in valid_devices:
    print(f"[WARN] Invalid LLM_DEVICE={LLM_DEVICE_ENV}, defaulting to 'cuda'")
    LLM_DEVICE_ENV = "cuda"
if TTS_DEVICE_ENV not in valid_devices:
    print(f"[WARN] Invalid TTS_DEVICE={TTS_DEVICE_ENV}, defaulting to 'cuda'")
    TTS_DEVICE_ENV = "cuda"
if WHISPER_DEVICE_ENV not in valid_devices:
    print(f"[WARN] Invalid WHISPER_DEVICE={WHISPER_DEVICE_ENV}, defaulting to 'cpu'")
    WHISPER_DEVICE_ENV = "cpu"

# Check CUDA availability if any device requires it
requires_cuda = LLM_DEVICE_ENV == "cuda" or TTS_DEVICE_ENV == "cuda"
if requires_cuda and not torch.cuda.is_available():
    raise SystemExit(
        "[ERROR] CUDA is not available but required by device configuration.\n"
        f"LLM_DEVICE={LLM_DEVICE_ENV}, TTS_DEVICE={TTS_DEVICE_ENV}\n"
        "Please ensure:\n"
        "  1. NVIDIA GPU is installed and drivers are up to date\n"
        "  2. CUDA toolkit is installed\n"
        "  3. PyTorch with CUDA support is installed\n"
        "  4. Or set LLM_DEVICE=cpu and TTS_DEVICE=cpu in .env file\n"
        "  5. Restart the application"
    )

# Device assignments from .env or defaults
LLM_DEVICE = LLM_DEVICE_ENV
TTS_DEVICE = TTS_DEVICE_ENV
WHISPER_DEVICE = WHISPER_DEVICE_ENV

# Print device configuration
device_summary = f"LLM: {LLM_DEVICE}, TTS: {TTS_DEVICE}, Whisper: {WHISPER_DEVICE}"
print(f"[INFO] Device configuration: {device_summary}")
if LLM_DEVICE == "cuda" or TTS_DEVICE == "cuda":
    print(f"[INFO] CUDA available: {torch.cuda.is_available()}")

# ========== RUNTIME AUDIO CONFIGURATION ==========
# These can be changed at runtime or via environment variables

INPUT_DEVICE = int(os.getenv("INPUT_DEVICE", "1"))
OUTPUT_DEVICE = int(os.getenv("OUTPUT_DEVICE", "3"))
SAMPLE_RATE = int(os.getenv("SAMPLE_RATE", str(DEFAULT_SAMPLE_RATE)))

# Voice clone file - relative to project root, in data folder
VOICE_CLONE_WAV = os.getenv("VOICE_CLONE_WAV", "data/saved_voices/refe2.wav")

# ========== RUNTIME MODEL CONFIGURATION ==========
# Model names can be overridden via environment variables

# Default model: Use "large-v3" 
# Can be overridden via WHISPER_MODEL environment variable
# if WHISPER_DEVICE == "cuda":
#     # GPU: default to "distil-whisper/distil-large-v3" (faster inference)
#     # Will auto-fallback to "large-v3" if incompatible with faster-whisper
#     WHISPER_MODEL = os.getenv("WHISPER_MODEL", "distil-whisper/distil-large-v3")
# else:
#     # For CPU, use smaller model for better performance
#     WHISPER_MODEL = os.getenv("WHISPER_MODEL", "medium.en")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "large-v3")
LLM_MODEL = os.getenv("LLM_MODEL", "TinyLlama/TinyLlama-1.1B-Chat-v1.0")
XTTS_MODEL = os.getenv("XTTS_MODEL", "tts_models/multilingual/multi-dataset/xtts_v2")

# Whisper compute type (optimized for device)
# For CUDA (RTX 3050/3080/5080): "int8_float16" (LOWEST LATENCY - uses Tensor Cores)
# For CUDA (other GPUs): "float16" (good balance)
# For CPU: "int8" (memory efficient) - CPU does NOT support int8_float16 or float16
# Use WHISPER_DEVICE to match actual device being used
env_compute_type = os.getenv("WHISPER_COMPUTE_TYPE")
if WHISPER_DEVICE == "cuda":
    # GPU: default to "int8_float16" for RTX GPUs (best performance)
    # Can be overridden via WHISPER_COMPUTE_TYPE env var to "float16" or "int8"
    WHISPER_COMPUTE_TYPE = env_compute_type if env_compute_type else "int8_float16"
    print(f"[STT] Using GPU with compute type: {WHISPER_COMPUTE_TYPE}")
else:
    # CPU: only allow int8 (int8_float16 and float16 are not supported on CPU)
    if env_compute_type in ["int8_float16", "float16"]:
        print(f"[WARNING] WHISPER_COMPUTE_TYPE={env_compute_type} is not supported on CPU.")
        print(f"[WARNING] Falling back to 'int8' for CPU compatibility.")
        WHISPER_COMPUTE_TYPE = "int8"
    else:
        WHISPER_COMPUTE_TYPE = env_compute_type if env_compute_type else "int8"

# ========== RUNTIME VAD CONFIGURATION ==========
# Can be adjusted at runtime

VAD_THRESHOLD = float(os.getenv("VAD_THRESHOLD", str(DEFAULT_VAD_THRESHOLD)))
MAX_SILENCE = float(os.getenv("MAX_SILENCE", str(DEFAULT_MAX_SILENCE)))

# ========== ENVIRONMENT SETUP ==========
# Set environment variables for libraries

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"


class ConfigService:
    """
    Runtime Configuration Service
    
    Provides methods to get structured configuration dictionaries.
    All values are determined at runtime based on available hardware and environment.
    """
    
    @staticmethod
    def get_device_config() -> Dict[str, str]:
        """
        Get device configuration (runtime detection)
        
        Returns:
            Dictionary with device assignments for LLM, TTS, and Whisper
        """
        return {
            "llm_device": LLM_DEVICE,
            "tts_device": TTS_DEVICE,
            "whisper_device": WHISPER_DEVICE,
            "cuda_available": str(torch.cuda.is_available()),
            "cuda_device_count": str(torch.cuda.device_count()) if torch.cuda.is_available() else "0",
        }
    
    @staticmethod
    def get_audio_config() -> Dict[str, any]:
        """
        Get audio configuration
        
        Returns:
            Dictionary with audio device IDs, sample rate, and voice file path
        """
        return {
            "input_device": INPUT_DEVICE,
            "output_device": OUTPUT_DEVICE,
            "sample_rate": SAMPLE_RATE,
            "voice_clone_wav": VOICE_CLONE_WAV,
        }
    
    @staticmethod
    def get_model_config() -> Dict[str, str]:
        """
        Get model configuration
        
        Returns:
            Dictionary with model names and compute types
        """
        return {
            "whisper_model": WHISPER_MODEL,
            "whisper_device": WHISPER_DEVICE,
            "whisper_compute_type": WHISPER_COMPUTE_TYPE,
            "llm_model": LLM_MODEL,
            "tts_model": XTTS_MODEL,
            "stt_engine": DEFAULT_STT_ENGINE,
            "ttt_engine": DEFAULT_TTT_ENGINE,
            "tts_engine": DEFAULT_TTS_ENGINE,
        }
    
    @staticmethod
    def get_vad_config() -> Dict[str, float]:
        """
        Get VAD (Voice Activity Detection) configuration
        
        Returns:
            Dictionary with VAD threshold and max silence duration
        """
        return {
            "vad_threshold": VAD_THRESHOLD,
            "max_silence": MAX_SILENCE,
        }
    
    @staticmethod
    def get_all_config() -> Dict[str, any]:
        """
        Get all configuration as a single dictionary
        
        Returns:
            Complete configuration dictionary
        """
        return {
            "devices": ConfigService.get_device_config(),
            "audio": ConfigService.get_audio_config(),
            "models": ConfigService.get_model_config(),
            "vad": ConfigService.get_vad_config(),
        }

