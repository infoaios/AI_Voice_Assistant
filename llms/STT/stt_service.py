"""Speech-to-Text service using Whisper"""
import time
import numpy as np
from faster_whisper import WhisperModel
from typing import Tuple, Optional
import torch

from services.infrastructure.config_service import WHISPER_MODEL, WHISPER_DEVICE, WHISPER_COMPUTE_TYPE


class STTService:
    """Speech-to-Text service using Whisper"""
    
    def _clear_corrupted_cache(self):
        """Pre-emptively clear any corrupted cache before loading model"""
        import shutil
        from pathlib import Path
        
        cache_base = Path.home() / ".cache"
        hf_cache = cache_base / "huggingface" / "hub"
        model_name = WHISPER_MODEL.replace('/', '--')
        model_cache = hf_cache / f"models--{model_name}"
        
        # Check if cache exists and has corrupted snapshots
        if model_cache.exists():
            snapshots_dir = model_cache / "snapshots"
            if snapshots_dir.exists():
                for snapshot in snapshots_dir.iterdir():
                    if snapshot.is_dir():
                        model_bin = snapshot / "model.bin"
                        # Check if snapshot exists but model.bin is missing (corrupted)
                        if not model_bin.exists():
                            try:
                                print(f"[STT] ⚠️  Found corrupted snapshot: {snapshot.name}. Clearing...")
                                shutil.rmtree(snapshot)
                                print(f"[STT] ✅ Cleared corrupted snapshot")
                            except:
                                pass
    
    def __init__(self):
        print(f"[STT] Loading Whisper model: {WHISPER_MODEL} on {WHISPER_DEVICE} with compute type {WHISPER_COMPUTE_TYPE}...")
        
        # Pre-clear any corrupted cache before attempting to load
        self._clear_corrupted_cache()
        
        try:
            self.model = WhisperModel(
                WHISPER_MODEL,
                device=WHISPER_DEVICE,
                compute_type=WHISPER_COMPUTE_TYPE,
            )
        except RuntimeError as e:
            if "model.bin" in str(e) or "Unable to open file" in str(e):
                print(f"[STT] ⚠️  Model cache corrupted. Performing complete cache cleanup...")
                import shutil
                from pathlib import Path
                
                cache_base = Path.home() / ".cache"
                hf_cache = cache_base / "huggingface" / "hub"
                model_name = WHISPER_MODEL.replace('/', '--')
                model_cache = hf_cache / f"models--{model_name}"
                
                # Clear ALL related caches completely
                cleared_any = False
                
                # 1. Clear entire model cache directory (includes snapshots)
                if model_cache.exists():
                    try:
                        shutil.rmtree(model_cache)
                        print(f"[STT] ✅ Cleared model cache: {model_cache}")
                        cleared_any = True
                    except Exception as clear_err:
                        print(f"[STT] ⚠️  Could not clear model cache: {clear_err}")
                
                # 2. Clear ctranslate2 cache (faster-whisper internal conversion cache)
                ctranslate_cache = cache_base / "ctranslate2"
                if ctranslate_cache.exists():
                    try:
                        for item in list(ctranslate_cache.iterdir()):
                            if model_name.lower() in item.name.lower() or "whisper" in item.name.lower() or "distil" in item.name.lower():
                                try:
                                    shutil.rmtree(item)
                                    print(f"[STT] ✅ Cleared ctranslate2 cache: {item.name}")
                                    cleared_any = True
                                except:
                                    pass
                    except Exception:
                        pass
                
                # 3. Clear any remaining snapshot references in HF cache
                if hf_cache.exists():
                    for item in list(hf_cache.iterdir()):
                        if model_name in item.name and item.is_dir():
                            try:
                                shutil.rmtree(item)
                                print(f"[STT] ✅ Cleared remaining cache: {item.name}")
                                cleared_any = True
                            except:
                                pass
                
                if not cleared_any:
                    print(f"[STT] ⚠️  No cache found to clear, but error persists.")
                
                # Wait longer for filesystem to fully sync
                print(f"[STT] ⏳ Waiting for filesystem sync...")
                time.sleep(3)
                
                # Try loading again - this will trigger fresh download and conversion
                print(f"[STT] 🔄 Re-downloading and converting model (this may take several minutes)...")
                print(f"[STT]    Note: faster-whisper needs to convert the model to ctranslate2 format.")
                print(f"[STT]    This is a one-time process and may take 5-10 minutes.")
                
                try:
                    self.model = WhisperModel(
                        WHISPER_MODEL,
                        device=WHISPER_DEVICE,
                        compute_type=WHISPER_COMPUTE_TYPE,
                    )
                    print(f"[STT] ✅ Model loaded successfully after cache clear!")
                except RuntimeError as retry_err:
                    # If still failing, try fallback model
                    if "model.bin" in str(retry_err) or "Unable to open file" in str(retry_err):
                        print(f"[STT] ❌ Model '{WHISPER_MODEL}' still failing after cache clear.")
                        print(f"[STT] 💡 This model may be incompatible with faster-whisper.")
                        print(f"[STT] 🔄 Trying fallback model: 'large-v3' (more compatible)...")
                        
                        # Try with a more compatible model
                        fallback_model = "large-v3"
                        try:
                            # Clear cache for fallback model too
                            fallback_cache = hf_cache / f"models--{fallback_model.replace('/', '--')}"
                            if fallback_cache.exists():
                                try:
                                    shutil.rmtree(fallback_cache)
                                except:
                                    pass
                            
                            time.sleep(2)
                            print(f"[STT] 🔄 Loading fallback model: {fallback_model}...")
                            self.model = WhisperModel(
                                fallback_model,
                                device=WHISPER_DEVICE,
                                compute_type=WHISPER_COMPUTE_TYPE,
                            )
                            print(f"[STT] ✅ Fallback model '{fallback_model}' loaded successfully!")
                            print(f"[STT] ⚠️  Note: Using '{fallback_model}' instead of '{WHISPER_MODEL}'")
                            print(f"[STT] 💡 To use '{WHISPER_MODEL}', you may need to use the standard 'whisper' library instead of 'faster-whisper'")
                        except Exception as fallback_err:
                            print(f"[STT] ❌ Fallback model also failed: {fallback_err}")
                            raise RuntimeError(
                                f"Failed to load Whisper model '{WHISPER_MODEL}' and fallback '{fallback_model}'. "
                                f"This might be a compatibility issue with faster-whisper. "
                                f"Try using a different model like 'medium.en' or 'small.en'"
                            ) from fallback_err
                    else:
                        raise
            else:
                raise
    
    def transcribe_with_timing(self, audio: np.ndarray) -> Tuple[str, float]:
        """
        Transcribe audio with timing
        
        Optimized with:
        - VAD filtering for faster processing
        - Generator expression for memory efficiency
        - Optimized faster-whisper parameters
        """
        if audio.size == 0:
            return "", 0.0
        
        st = time.perf_counter()
        segments, info = self.model.transcribe(
            audio,
            beam_size=1,
            language="en",
            vad_filter=True,  # Filter non-speech segments for speed
            condition_on_previous_text=False,  # Faster without context
            temperature=0,  # Deterministic decoding
            no_speech_threshold=0.6,  # Detect empty audio faster
            compression_ratio_threshold=2.4  # Filter low-quality transcriptions
        )
        
        # Use generator expression directly in join for memory efficiency
        # Consume generator while timing is running
        text = "".join(s.text for s in segments).strip()
        
        elapsed = time.perf_counter() - st
        return text, elapsed
