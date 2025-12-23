"""Speech-to-Text service using Whisper"""
import time
import numpy as np
from faster_whisper import WhisperModel
from typing import Tuple, Optional
import torch

from services.infrastructure.config_service import WHISPER_MODEL, WHISPER_DEVICE, WHISPER_COMPUTE_TYPE, WHISPER_LANGUAGE

# Allowed languages for auto-detection (only these 3 languages will be detected)
ALLOWED_LANGUAGES = ["en", "hi", "gu"]  # English, Hindi, Gujarati
DEFAULT_LANGUAGE = "en"  # Default to English if detection fails or returns other language


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
            # Use configured language or None for auto-detect
            warmup_language = WHISPER_LANGUAGE if WHISPER_LANGUAGE else None
            segments, _ = self.model.transcribe(
                dummy_audio,
                beam_size=1,
                language=warmup_language,
                vad_filter=False,  # Skip VAD for warmup
                condition_on_previous_text=False,
                temperature=0,
            )
            # Consume generator to complete warmup
            list(segments)
            print(f"[STT] ✅ Model warmed up successfully (language: {warmup_language or 'auto-detect'})")
        except Exception as e:
            print(f"[STT] ⚠️  Warmup failed (non-critical): {e}")
    
    def _preprocess_audio(self, audio: np.ndarray) -> np.ndarray:
        """
        Minimal preprocessing for ultra-low latency
        
        - Only normalize if necessary (skip if already normalized)
        - Skip silence trimming (let Whisper handle it for speed)
        """
        if audio.size == 0:
            return audio
        
        # Quick normalization check - only normalize if audio is clipped or too quiet
        max_val = np.abs(audio).max()
        if max_val > 1.0:
            # Audio is clipped, normalize
            audio = audio / max_val
        elif max_val < 0.01:
            # Audio is too quiet, skip processing
            return np.array([], dtype=np.float32)
        
        # Skip silence trimming - Whisper's VAD is faster and more accurate
        # This reduces preprocessing overhead for ultra-low latency
        
        return audio
    
    def transcribe_with_timing(self, audio: np.ndarray) -> Tuple[str, float]:
        """
        Transcribe audio with ultra-low latency optimization (target: 2.0-2.5s for 45s audio)
        
        Optimizations:
        - Minimal preprocessing (skip expensive operations)
        - Chunked processing for long audio (45s+)
        - Ultra-fast decoding parameters
        - VAD filtering for faster processing
        - Generator expression for memory efficiency
        - Optimized GPU cache management
        - Model warmup (done at initialization)
        """
        if audio.size == 0:
            return "", 0.0
        
        # Minimal preprocessing for speed
        audio = self._preprocess_audio(audio)
        if audio.size == 0:
            return "", 0.0
        
        # Clear GPU cache before transcription for consistent latency
        if WHISPER_DEVICE == "cuda" and torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        st = time.perf_counter()
        
        # Use configured language or auto-detect (limited to en, hi, gu only)
        # If auto-detection returns other language, default to English
        transcription_language = WHISPER_LANGUAGE if WHISPER_LANGUAGE else None
        
        if transcription_language:
            print(f"[STT] 🔒 Using FORCED language: {transcription_language}")
        else:
            print(f"[STT] 🌐 Auto-detecting language (en/hi/gu only, default: en)...")
        
        # For long audio (>30s), use chunked processing to reduce memory and improve speed
        # This is critical for achieving 2.0-2.5s latency on 45s audio
        audio_duration = len(audio) / 16000  # Assuming 16kHz sample rate
        use_chunked = audio_duration > 30.0
        
        # Helper function to validate and correct detected language
        def validate_language(detected_lang: Optional[str]) -> str:
            """Validate detected language - must be in allowed list, else default to English"""
            if detected_lang and detected_lang in ALLOWED_LANGUAGES:
                return detected_lang
            else:
                if detected_lang:
                    print(f"[STT] ⚠️  Detected '{detected_lang}' not in allowed list {ALLOWED_LANGUAGES}, defaulting to '{DEFAULT_LANGUAGE}'")
                else:
                    print(f"[STT] ⚠️  Language detection failed, defaulting to '{DEFAULT_LANGUAGE}'")
                return DEFAULT_LANGUAGE
        
        if use_chunked:
            # Chunked processing for long audio (45s+)
            # Process in overlapping chunks to maintain context
            chunk_size = 30 * 16000  # 30 second chunks
            overlap = 2 * 16000  # 2 second overlap
            text_parts = []
            
            # For chunked processing, use the validated language for all chunks
            # First chunk: auto-detect and validate, subsequent chunks: use validated language
            validated_lang = None
            
            for i in range(0, len(audio), chunk_size - overlap):
                chunk = audio[i:i + chunk_size]
                if len(chunk) < 1000:  # Skip tiny chunks
                    break
                
                # For first chunk, auto-detect and validate language
                # For subsequent chunks, use the validated language
                chunk_language = validated_lang if validated_lang else transcription_language
                
                # Process chunk with ultra-low latency parameters
                segments, info = self.model.transcribe(
                    chunk,
                    beam_size=1,  # Greedy decoding (fastest)
                    best_of=1,  # No beam search
                    language=chunk_language,  # None = auto-detect, or explicit code
                    vad_filter=True,  # Filter non-speech segments
                    condition_on_previous_text=False,  # Faster without context
                    temperature=0,  # Deterministic decoding
                    no_speech_threshold=0.6,
                    compression_ratio_threshold=2.4,
                    patience=0.5,  # Lower patience for chunked processing
                    suppress_blank=True,
                    suppress_tokens=[-1],
                    without_timestamps=True,  # Skip timestamps for speed
                    max_new_tokens=440,
                )
                
                # Validate language on first chunk only
                if validated_lang is None and chunk_language is None and hasattr(info, 'language'):
                    detected_lang = info.language
                    validated_lang = validate_language(detected_lang)
                    # Re-transcribe first chunk with validated language for consistency
                    if validated_lang != detected_lang:
                        segments, _ = self.model.transcribe(
                            chunk,
                            beam_size=1,
                            best_of=1,
                            language=validated_lang,
                            vad_filter=True,
                            condition_on_previous_text=False,
                            temperature=0,
                            no_speech_threshold=0.6,
                            compression_ratio_threshold=2.4,
                            patience=0.5,
                            suppress_blank=True,
                            suppress_tokens=[-1],
                            without_timestamps=True,
                            max_new_tokens=440,
                        )
                
                chunk_text = "".join(s.text for s in segments).strip()
                if chunk_text:
                    text_parts.append(chunk_text)
        else:
            # Single-pass processing for shorter audio
            # Ultra-low latency transcription parameters
            segments, info = self.model.transcribe(
                audio,
                beam_size=1,  # Greedy decoding (fastest)
                best_of=1,  # No beam search (lowest latency)
                language=transcription_language,  # None = auto-detect, or explicit code
                vad_filter=True,  # Filter non-speech segments for speed
                condition_on_previous_text=False,  # Faster without context
                temperature=0,  # Deterministic decoding (fastest)
                no_speech_threshold=0.6,  # Detect empty audio faster
                compression_ratio_threshold=2.4,  # Filter low-quality transcriptions
                patience=0.5,  # Lower patience = faster decoding (optimized for speed)
                suppress_blank=True,  # Skip blank tokens
                suppress_tokens=[-1],  # Suppress special tokens
                without_timestamps=True,  # Skip timestamp generation (faster)
                max_new_tokens=440,  # Limit output length for speed
            )
            
            # Validate and correct detected language if auto-detection was used
            if transcription_language is None and hasattr(info, 'language'):
                detected_lang = info.language
                lang_prob = getattr(info, 'language_probability', None)
                
                # Validate detected language - must be in allowed list
                validated_lang = validate_language(detected_lang)
                
                # If detected language is not in allowed list, re-transcribe with validated language
                if validated_lang != detected_lang:
                    print(f"[STT] 🔄 Re-transcribing with validated language: {validated_lang}")
                    segments, info = self.model.transcribe(
                        audio,
                        beam_size=1,
                        best_of=1,
                        language=validated_lang,
                        vad_filter=True,
                        condition_on_previous_text=False,
                        temperature=0,
                        no_speech_threshold=0.6,
                        compression_ratio_threshold=2.4,
                        patience=0.5,
                        suppress_blank=True,
                        suppress_tokens=[-1],
                        without_timestamps=True,
                        max_new_tokens=440,
                    )
                    print(f"[STT] ✅ Using language: {validated_lang}")
                else:
                    # Log detected language with confidence
                    if lang_prob is not None:
                        if lang_prob < 0.5:
                            print(f"[STT] ⚠️  Auto-detected language: {detected_lang} (LOW confidence: {lang_prob:.3f})")
                        else:
                            print(f"[STT] ✅ Auto-detected language: {detected_lang} (confidence: {lang_prob:.3f})")
                    else:
                        print(f"[STT] ✅ Auto-detected language: {detected_lang}")
            
            # Use generator expression directly in join for memory efficiency
            text_parts = ["".join(s.text for s in segments).strip()]
        
        # Join all text parts
        text = " ".join(text_parts).strip()
        
        elapsed = time.perf_counter() - st
        
        # Clear GPU cache after transcription to free memory
        if WHISPER_DEVICE == "cuda" and torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        return text, elapsed