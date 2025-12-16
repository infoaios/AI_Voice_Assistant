"""
Voice Activity Detection Service

Detects speech activity in audio streams using Silero VAD model.
Built on audio_processor outputs to determine when speech starts/stops.

This service:
- Loads and manages the Silero VAD model
- Processes audio frames to detect speech probability
- Provides silence detection capabilities
- Works with AudioProcessor for real-time VAD during recording
"""
import torch
import time
import numpy as np
from typing import Tuple, Optional

from .config_service import VAD_THRESHOLD, MAX_SILENCE, SAMPLE_RATE


class VADService:
    """
    Voice Activity Detection service using Silero VAD model
    
    Detects speech in audio frames and provides speech probability scores.
    Used by AudioProcessor to determine when to start/stop recording.
    """
    
    def __init__(self):
        self.model = None
        self.utils = None
        self._load_model()
    
    def _load_model(self):
        """Load Silero VAD model"""
        self.model, self.utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            trust_repo=True,
            force_reload=False,
        )
    
    def detect_speech(
        self, 
        audio_frame: np.ndarray, 
        threshold: float = VAD_THRESHOLD
    ) -> float:
        """
        Detect speech probability in audio frame
        
        Args:
            audio_frame: Audio frame as numpy array
            threshold: Speech detection threshold
            
        Returns:
            Speech probability (0.0 to 1.0)
        """
        if audio_frame.size == 0:
            return 0.0
        
        # Prepare frame for VAD (needs 512 samples)
        if audio_frame.shape[0] > 512:
            recent = audio_frame[-512:]
        elif audio_frame.shape[0] < 512:
            pad = np.zeros(512 - audio_frame.shape[0], dtype=audio_frame.dtype)
            recent = np.concatenate([pad, audio_frame])
        else:
            recent = audio_frame
        
        # Convert to int16 format
        wav_int16 = (recent * 32768).astype(np.int16)
        torch_audio = torch.from_numpy(wav_int16).float()
        
        with torch.no_grad():
            speech_prob = self.model(torch_audio, SAMPLE_RATE).item()
        
        return speech_prob
    
    def is_silence(
        self, 
        audio_frame: np.ndarray, 
        threshold: float = VAD_THRESHOLD
    ) -> bool:
        """Check if audio frame is silence"""
        speech_prob = self.detect_speech(audio_frame, threshold)
        return speech_prob < threshold

