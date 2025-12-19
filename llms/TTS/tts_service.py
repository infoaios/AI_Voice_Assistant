"""Text-to-Speech service using XTTS - Optimized for low latency"""
import re
import time
import sounddevice as sd
import soundfile as sf
from pathlib import Path
import torch
import numpy as np

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
            # Load model with GPU optimization
            self.tts = TTS(model_name=XTTS_MODEL, gpu=True, progress_bar=False)
            
            # Ensure model is on GPU and set to eval mode for faster inference
            if hasattr(self.tts, 'synthesizer') and hasattr(self.tts.synthesizer, 'model'):
                self.tts.synthesizer.model.eval()
                # Enable optimizations for inference
                if hasattr(self.tts.synthesizer.model, 'half'):
                    try:
                        self.tts.synthesizer.model = self.tts.synthesizer.model.half()  # FP16 for faster inference
                        print("[TTS] Using FP16 precision for faster inference")
                    except Exception:
                        print("[TTS] FP16 not available, using FP32")
            
            # Test GPU functionality with in-memory generation (faster than file I/O)
            try:
                print("[TTS] Testing GPU functionality...")
                test_wav = self.tts.tts(
                    text="test",
                    speaker_wav=str(ref_path),
                    language="en",
                )
                print(f"[TTS] ✅ GPU test successful (generated {len(test_wav) if isinstance(test_wav, (list, np.ndarray)) else 'audio'} samples)")
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

    def speak(self, text: str, language: str = "en") -> float:
        """
        Low-latency TTS with streaming playback.
        Splits text into smaller chunks and streams them for faster first audio.
        """
        text = text.strip()
        if not text:
            return 0.0

        # Optimized chunking for low latency - smaller chunks for faster first audio
        final_chunks = self._chunk_text_optimized(text, max_len=80)  # Reduced from 180 for faster generation
        
        if not final_chunks:
            return 0.0

        # Get sample rate from TTS model
        sample_rate = self.tts.synthesizer.output_sample_rate
        
        # Use streaming playback for lowest latency
        total_gen = self._speak_streaming(final_chunks, language, sample_rate)
        
        return total_gen

    def _chunk_text_optimized(self, text: str, max_len: int = 80) -> list[str]:
        """
        Optimized text chunking for low latency.
        Creates smaller chunks to reduce time-to-first-audio.
        """
        # STEP 1 — Split by punctuation first
        raw_sentences = re.split(r'[.!?।]', text)
        sentences = [s.strip() for s in raw_sentences if s.strip()]

        # STEP 2 — Fall back to "|" if no punctuation
        if len(sentences) <= 1 and "|" in text:
            sentences = [x.strip() for x in text.split("|") if x.strip()]

        # STEP 3 — Split into smaller chunks for faster generation
        final_chunks = []
        
        for s in sentences:
            words = s.split()
            chunk = ""

            for w in words:
                candidate = (chunk + " " + w).strip() if chunk else w
                if len(candidate) > max_len:
                    if chunk:
                        final_chunks.append(chunk + ".")
                    # If single word is too long, split it
                    if len(w) > max_len:
                        for i in range(0, len(w), max_len):
                            final_chunks.append(w[i:i+max_len] + ".")
                        chunk = ""
                    else:
                        chunk = w
                else:
                    chunk = candidate

            if chunk:
                final_chunks.append(chunk + ".")

        return final_chunks

    def _speak_streaming(self, chunks: list[str], language: str, sample_rate: int) -> float:
        """
        Stream TTS generation and playback for lowest latency.
        Generates chunks in sequence and plays them immediately.
        Uses torch.inference_mode() for faster inference.
        """
        total_gen = 0.0
        first_audio_time = None
        
        # Use inference mode for faster generation (disables gradient computation)
        with torch.inference_mode():
            for i, chunk in enumerate(chunks):
                tts_start = time.time()
                
                try:
                    # Use in-memory generation (no disk I/O) for lower latency
                    wav = self.tts.tts(
                        text=chunk,
                        speaker_wav=self.clone,
                        language=language,
                    )
                    
                    # Convert to numpy array if not already
                    if not isinstance(wav, np.ndarray):
                        wav = np.array(wav, dtype=np.float32)
                    else:
                        wav = wav.astype(np.float32)
                    
                    gen_time = time.time() - tts_start
                    total_gen += gen_time
                    
                    # Track time to first audio
                    if first_audio_time is None:
                        first_audio_time = gen_time
                        print(f"[TTS] First audio latency: {first_audio_time:.2f}s")
                    
                    # Play immediately (streaming)
                    sd.play(wav, sample_rate)
                    
                    # For last chunk, wait for completion
                    if i == len(chunks) - 1:
                        sd.wait()
                    else:
                        # For intermediate chunks, start playing and continue generating next
                        # This allows overlap of generation and playback
                        # Optionally clear GPU cache periodically for long sequences
                        if (i + 1) % 5 == 0 and torch.cuda.is_available():
                            torch.cuda.empty_cache()
                        
                except Exception as e:
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
        
        print(f"[TTS] Total generation time: {total_gen:.2f}s for {len(chunks)} chunks")
        return total_gen

    def _speak_single(self, text: str, language: str = "en") -> float:
        """
        Legacy method for single chunk generation (kept for compatibility).
        Use speak() for optimized streaming.
        """
        sample_rate = self.tts.synthesizer.output_sample_rate
        tts_start = time.time()

        try:
            # Use in-memory generation for lower latency
            wav = self.tts.tts(
                text=text,
                speaker_wav=self.clone,
                language=language,
            )
            
            if not isinstance(wav, np.ndarray):
                wav = np.array(wav, dtype=np.float32)
            else:
                wav = wav.astype(np.float32)
                
        except Exception as e:
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

        sd.play(wav, sample_rate)
        sd.wait()

        return gen_time



