"""Text-to-Speech service using XTTS"""
import re
import time
import sounddevice as sd
import soundfile as sf
from pathlib import Path
import torch

# Fix for PyTorch 2.6+ weights_only issue with TTS models
# Monkey-patch torch.load to use weights_only=False for TTS compatibility
_original_torch_load = torch.load
def _patched_torch_load(*args, **kwargs):
    """Patched torch.load that defaults weights_only=False for TTS compatibility"""
    if 'weights_only' not in kwargs:
        kwargs['weights_only'] = False
    return _original_torch_load(*args, **kwargs)
torch.load = _patched_torch_load

from TTS.api import TTS

from services.infrastructure.config_service import TTS_DEVICE, XTTS_MODEL, VOICE_CLONE_WAV


class TTSService:
    """Text-to-Speech service using XTTS v2"""
    
    def __init__(self):
        self.device = TTS_DEVICE
        # Resolve path relative to project root
        # This file is in llms/TTS/, so project root is 3 levels up
        project_root = Path(__file__).parent.parent.parent  # project root
        ref_path = project_root / VOICE_CLONE_WAV

        if not ref_path.is_file():
            raise SystemExit(f"[TTS] Voice file not found: {ref_path}")

        print("[TTS] Loading XTTS v2...")
        
        # Pre-check transformers version before loading TTS
        try:
            import transformers
            transformers_version = transformers.__version__
            print(f"[TTS] Detected transformers version: {transformers_version}")
            
            # Check if version is compatible (TTS 0.22.0 needs 4.40.0-4.45.0)
            try:
                from packaging import version
                if version.parse(transformers_version) >= version.parse("4.46.0"):
                    print(f"[TTS] ⚠️  Incompatible transformers version: {transformers_version}")
                    print(f"[TTS] 💡 TTS 0.22.0 requires transformers 4.40.0-4.45.0")
                    print(f"[TTS] 🔄 Attempting to fix by installing compatible version...")
                    import subprocess
                    import sys
                    try:
                        # Install compatible version
                        subprocess.check_call([
                            sys.executable, "-m", "pip", "install", 
                            "transformers==4.45.0", "--force-reinstall"
                        ])
                        print(f"[TTS] ✅ Installed transformers 4.45.0")
                        print(f"[TTS] ⚠️  Python must be restarted to use the new version.")
                        print(f"[TTS] 💡 Please restart the application now.")
                        raise SystemExit(
                            "Transformers version updated. Please restart the application:\n"
                            "  1. Stop this application (Ctrl+C)\n"
                            "  2. Run: python main.py\n"
                            "  Or: scripts\\run.bat"
                        )
                    except Exception as install_err:
                        print(f"[TTS] ❌ Failed to install compatible version: {install_err}")
                        print(f"[TTS] 💡 Manual fix required:")
                        print(f"[TTS]   1. Stop this application")
                        print(f"[TTS]   2. Activate conda environment: conda activate voice_assistant_gpu3050")
                        print(f"[TTS]   3. Run: pip install transformers==4.45.0")
                        print(f"[TTS]   4. Restart the application")
                        raise SystemExit(
                            f"TTS requires transformers 4.40.0-4.45.0, but found {transformers_version}. "
                            f"Please install compatible version and restart."
                        )
            except ImportError:
                # packaging not available, try string comparison
                if transformers_version >= "4.46.0":
                    print(f"[TTS] ⚠️  Incompatible transformers version: {transformers_version}")
                    print(f"[TTS] 💡 Please install: pip install transformers==4.45.0")
                    print(f"[TTS] 💡 Then restart the application")
                    raise SystemExit(
                        f"TTS requires transformers 4.40.0-4.45.0, but found {transformers_version}. "
                        f"Please install compatible version and restart."
                    )
        except ImportError:
            # transformers not installed - will be caught by TTS import
            pass
        
        # GPU ONLY - no CPU fallback
        if self.device != "cuda":
            raise SystemExit(
                "[TTS] ERROR: GPU is required. This application does not support CPU mode.\n"
                "Please ensure GPU and cuDNN are properly installed."
            )
        
        try:
            print("[TTS] Loading TTS model on GPU...")
            self.tts = TTS(model_name=XTTS_MODEL, gpu=True)
            
            # Test GPU functionality with a small generation to catch cuDNN errors early
            try:
                print("[TTS] Testing GPU functionality...")
                # Create a temporary test file
                test_path = project_root / "tts_test_temp.wav"
                self.tts.tts_to_file(
                    text="test",
                    file_path=test_path,
                    speaker_wav=str(ref_path),
                    language="en",
                )
                # Clean up test file
                if test_path.exists():
                    test_path.unlink()
                print("[TTS] ✅ GPU test successful")
            except Exception as gpu_test_err:
                error_str = str(gpu_test_err).lower()
                is_cudnn_error = (
                    "cudnn" in error_str or 
                    ("cuda" in error_str and "dll" in error_str) or
                    "cudnncreate" in error_str or
                    "cudnn_ops" in error_str or
                    "invalid handle" in error_str
                )
                if is_cudnn_error:
                    raise SystemExit(
                        f"[TTS] ERROR: GPU cuDNN error detected: {gpu_test_err}\n"
                        "This application requires GPU with cuDNN support.\n\n"
                        "To fix:\n"
                        "  1. Install cuDNN: conda install -c conda-forge cudnn\n"
                        "  2. Or download from: https://developer.nvidia.com/cudnn\n"
                        "  3. Restart the application\n\n"
                        "Application will not run without GPU + cuDNN."
                    ) from gpu_test_err
                else:
                    # Other GPU error - still fail (GPU only mode)
                    raise SystemExit(
                        f"[TTS] ERROR: GPU test failed: {gpu_test_err}\n"
                        "This application requires GPU. Please check your GPU setup."
                    ) from gpu_test_err
                    
        except (ImportError, RuntimeError, OSError) as e:
            error_str = str(e).lower()
            is_cudnn_error = (
                "cudnn" in error_str or 
                ("cuda" in error_str and "dll" in error_str) or
                "cudnncreate" in error_str or
                "cudnn_ops" in error_str or
                "invalid handle" in error_str
            )
            
            if is_cudnn_error:
                raise SystemExit(
                    f"[TTS] ERROR: CUDA/cuDNN error detected: {e}\n"
                    "This application requires GPU with cuDNN support.\n\n"
                    "To fix:\n"
                    "  1. Install cuDNN: conda install -c conda-forge cudnn\n"
                    "  2. Or download from: https://developer.nvidia.com/cudnn\n"
                    "  3. Restart the application\n\n"
                    "Application will not run without GPU + cuDNN."
                ) from e
            elif "BeamSearchScorer" in str(e):
                print(f"[TTS] ❌ Import error: {e}")
                print(f"[TTS] 💡 This indicates transformers version incompatibility.")
                print(f"[TTS] 💡 Manual fix required:")
                print(f"[TTS]   1. Stop this application")
                print(f"[TTS]   2. Activate conda environment: conda activate voice_assistant_gpu3050")
                print(f"[TTS]   3. Run: pip install transformers==4.45.0")
                print(f"[TTS]   4. Restart the application")
                raise SystemExit(
                    f"TTS library requires transformers 4.40.0-4.45.0. "
                    f"Please install compatible version and restart the application."
                ) from e
            else:
                raise SystemExit(
                    f"[TTS] ERROR: Failed to load TTS model on GPU: {e}\n"
                    "This application requires GPU. Please check your GPU setup."
                ) from e
        
        self.clone = str(ref_path)

    def speak(self, text: str) -> float:
        """Split text by sentence boundaries and length for smooth speech."""
        text = text.strip()
        if not text:
            return 0.0

        # STEP 1 — First split using punctuation
        raw_sentences = re.split(r'[.!?]', text)
        sentences = [s.strip() for s in raw_sentences if s.strip()]

        # STEP 2 — But if no punctuation exists, fall back to splitting by "|"
        if len(sentences) <= 1 and "|" in text:
            sentences = [x.strip() for x in text.split("|") if x.strip()]

        # STEP 3 — Now enforce max length per sentence (for XTTS safety)
        final_chunks = []
        max_len = 180  # safe under XTTS 250 char limit

        for s in sentences:
            words = s.split()
            chunk = ""

            for w in words:
                candidate = (chunk + " " + w).strip()
                if len(candidate) > max_len:
                    final_chunks.append(chunk + ".")
                    chunk = w
                else:
                    chunk = candidate

            if chunk:
                final_chunks.append(chunk + ".")

        total_gen = 0.0
        for chunk in final_chunks:
            total_gen += self._speak_single(chunk)

        return total_gen

    def _speak_single(self, text: str) -> float:
        """Generate and play single chunk"""
        # Save TTS output to project root
        project_root = Path(__file__).parent.parent.parent  # project root
        out_path = project_root / "tts_output.wav"
        tts_start = time.time()

        try:
            self.tts.tts_to_file(
                text=text,
                file_path=out_path,
                speaker_wav=self.clone,
                language="en",
            )
        except Exception as e:
            error_str = str(e).lower()
            # GPU ONLY - no CPU fallback
            # Check for various cuDNN error patterns
            is_cudnn_error = (
                "cudnn" in error_str or 
                ("cuda" in error_str and "dll" in error_str) or
                "cudnncreate" in error_str or
                "cudnn_ops" in error_str or
                "invalid handle" in error_str
            )
            
            if is_cudnn_error:
                raise SystemExit(
                    f"[TTS] ERROR: cuDNN error during generation: {e}\n"
                    "This application requires GPU with cuDNN support.\n\n"
                    "To fix:\n"
                    "  1. Install cuDNN: conda install -c conda-forge cudnn\n"
                    "  2. Or download from: https://developer.nvidia.com/cudnn\n"
                    "  3. Restart the application\n\n"
                    "Application will not run without GPU + cuDNN."
                ) from e
            else:
                raise SystemExit(
                    f"[TTS] ERROR: Failed to generate on GPU: {e}\n"
                    "This application requires GPU. Please check your GPU setup."
                ) from e

        gen_time = time.time() - tts_start
        print(f"[Timing] TTS: {gen_time:.2f}s")

        audio, sr = sf.read(out_path)
        sd.play(audio, sr)
        sd.wait()

        return gen_time

