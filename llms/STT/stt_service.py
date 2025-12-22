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
            # Warmup model for ultra-low latency (reduces first-call overhead)
            self._warmup_model()
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
    
    def _warmup_model(self):
        """Warmup model with dummy audio to reduce first-call latency"""
        print("[STT] 🔥 Warming up model for ultra-low latency...")
        try:
            # Create dummy audio (1 second of silence at 16kHz)
            dummy_audio = np.zeros(16000, dtype=np.float32)
            # Do a quick transcription to warm up the model
            segments, _ = self.model.transcribe(
                dummy_audio,
                beam_size=1,
                language="en",
                vad_filter=False,  # Skip VAD for warmup
                condition_on_previous_text=False,
                temperature=0,
            )
            # Consume generator to complete warmup
            list(segments)
            print("[STT] ✅ Model warmed up successfully")
        except Exception as e:
            print(f"[STT] ⚠️  Warmup failed (non-critical): {e}")
    
    def _preprocess_audio(self, audio: np.ndarray) -> np.ndarray:
        """
        Preprocess audio for optimal transcription speed
        
        - Normalizes audio levels
        - Trims leading/trailing silence
        """
        if audio.size == 0:
            return audio
        
        # Normalize audio to [-1, 1] range for optimal processing
        max_val = np.abs(audio).max()
        if max_val > 0:
            audio = audio / max_val
        
        # Trim leading/trailing silence (simple threshold-based)
        # This reduces processing time by removing unnecessary audio
        threshold = 0.01  # Very low threshold to preserve speech
        mask = np.abs(audio) > threshold
        if mask.any():
            first = np.argmax(mask)
            last = len(mask) - np.argmax(mask[::-1])
            audio = audio[first:last]
        
        return audio
    
    def transcribe_with_timing(self, audio: np.ndarray) -> Tuple[str, float]:
        """
        Transcribe audio with ultra-low latency optimization
        
        Optimizations:
        - Audio preprocessing (normalize, trim silence)
        - Ultra-fast decoding parameters
        - VAD filtering for faster processing
        - Generator expression for memory efficiency
        - GPU cache management
        - Model warmup (done at initialization)
        """
        if audio.size == 0:
            return "", 0.0
        
        # Preprocess audio for optimal speed
        audio = self._preprocess_audio(audio)
        if audio.size == 0:
            return "", 0.0
        
        # Clear GPU cache before transcription for consistent latency
        if WHISPER_DEVICE == "cuda" and torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        st = time.perf_counter()
        
        # Ultra-low latency transcription parameters
        segments, info = self.model.transcribe(
            audio,
            beam_size=1,  # Greedy decoding (fastest)
            best_of=1,  # No beam search (lowest latency)
            language="en",
            vad_filter=True,  # Filter non-speech segments for speed
            condition_on_previous_text=False,  # Faster without context
            temperature=0,  # Deterministic decoding (fastest)
            no_speech_threshold=0.6,  # Detect empty audio faster
            compression_ratio_threshold=2.4,  # Filter low-quality transcriptions
            patience=1.0,  # Lower patience = faster decoding
            suppress_blank=True,  # Skip blank tokens
            suppress_tokens=[-1],  # Suppress special tokens
            without_timestamps=True,  # Skip timestamp generation (faster)
            # max_new_tokens: Leave room for prompt tokens (Whisper max_length=448)
            # Prompt typically uses ~4-8 tokens, so 440 leaves safe margin
            max_new_tokens=440,  # Limit output length for speed (448 - prompt tokens)
        )
        
        # Use generator expression directly in join for memory efficiency
        # Consume generator while timing is running
        text = "".join(s.text for s in segments).strip()
        
        elapsed = time.perf_counter() - st
        
        # Clear GPU cache after transcription to free memory
        if WHISPER_DEVICE == "cuda" and torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        return text, elapsed
