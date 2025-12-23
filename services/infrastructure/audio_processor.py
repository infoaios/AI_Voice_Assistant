"""
Audio Processing Service

Handles audio I/O operations:
- Audio recording from input devices
- Audio decoding and format conversion
- Resampling to target sample rates
- Audio normalization and level adjustment
- Encoding for different output formats

This service orchestrates audio operations and works with VADService
for voice activity detection during recording.
"""
import time
import numpy as np
import sounddevice as sd
from typing import Tuple

from .config_service import INPUT_DEVICE, OUTPUT_DEVICE, SAMPLE_RATE, MAX_SILENCE, VAD_THRESHOLD
from .vad_service import VADService

# Note: Audio decode/resample/normalize/encode operations would be added here
# as methods when needed for format conversion and audio processing


class AudioProcessor:
    """
    Service for audio recording, processing, and I/O operations
    
    Responsibilities:
    - Record audio from input devices
    - Decode audio from various formats
    - Resample audio to target sample rates
    - Normalize audio levels
    - Encode audio for output
    
    Works with VADService to detect speech during recording.
    """
    
    def __init__(self, vad_service: VADService):
        self.vad_service = vad_service
        self._setup_audio()
    
    def _setup_audio(self):
        """Setup audio device configuration"""
        sd.default.device = (INPUT_DEVICE, OUTPUT_DEVICE)
        sd.default.samplerate = SAMPLE_RATE
        sd.default.channels = 1
    
    def record_until_silence(
        self, 
        threshold: float = VAD_THRESHOLD, 
        max_silence: float = MAX_SILENCE
    ) -> np.ndarray:
        """
        Record audio until silence detected (optimized for low latency)
        
        Uses optimized buffer size (1024 samples) for better performance
        while maintaining low latency detection.
        """
        print("[Audio] 🎤 Listening...")
        
        audio_chunks = []
        silence_start = None
        
        # Use larger buffer (1024 samples) for better performance
        # This reduces I/O overhead while maintaining low latency
        buffer_size = 1024
        stream = sd.InputStream(
            samplerate=SAMPLE_RATE, 
            channels=1, 
            dtype="float32",
            blocksize=buffer_size
        )
        stream.start()
        
        try:
            while True:
                frame, _ = stream.read(buffer_size)
                frame = frame.flatten()
                
                if frame.size == 0:
                    continue
                
                audio_chunks.append(frame)
                
                # Check for silence using VAD (only on recent frames for speed)
                # For long recordings, check every 2nd frame to reduce VAD overhead
                if len(audio_chunks) % 2 == 0 or len(audio_chunks) < 10:
                    speech_prob = self.vad_service.detect_speech(frame, threshold)
                    
                    if speech_prob < threshold:
                        if silence_start is None:
                            silence_start = time.time()
                        elif time.time() - silence_start > max_silence:
                            print("[Audio] ✅ End of speech detected")
                            break
                    else:
                        silence_start = None
        
        except KeyboardInterrupt:
            print("\n[Audio] Recording interrupted")
        finally:
            stream.stop()
            stream.close()
        
        if not audio_chunks:
            return np.array([], dtype=np.float32)
        
        return np.concatenate(audio_chunks)

