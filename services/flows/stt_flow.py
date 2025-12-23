"""
STT Flow - orchestrates speech-to-text processing

Uses interfaces to reduce coupling.
"""
# Use interfaces for stable contracts
try:
    from core.interfaces import ISTTService
except ImportError:
    from llms.STT.stt_service import STTService as ISTTService

import time
from typing import Optional, Tuple

from services.infrastructure.audio_processor import AudioProcessor


class STTFlow:
    """
    Flow for Speech-to-Text processing
    
    Depends on STT service interface, allowing implementations to change.
    """
    
    def __init__(self, stt_service: ISTTService, audio_processor: AudioProcessor):
        """
        Initialize STT flow
        
        Args:
            stt_service: Speech-to-text service interface
            audio_processor: Audio processor (can be abstracted later)
        """
        self.stt_service = stt_service
        self.audio_processor = audio_processor
    
    def process(self) -> Optional[Tuple[str, float]]:
        """
        Process audio input and return transcribed text with timing
        
        Returns:
            Tuple of (transcribed_text, stt_time) if successful, None otherwise
        """
        print("\n[Recording...]")
        record_start = time.perf_counter()
        audio = self.audio_processor.record_until_silence()
        record_time = time.perf_counter() - record_start
        
        if audio.size == 0:
            print("[Info] No audio detected.\n")
            return None
        
        # STT
        text, stt_time = self.stt_service.transcribe_with_timing(audio)
        if not text.strip():
            print("[Info] No speech detected.\n")
            return None
        
        total = record_time + stt_time
        print(f"\n[User]: {text}")
        print(f"[Timing] record_time={record_time:.2f}s | transcribe_time={stt_time:.2f}s | total={total:.2f}s")
        return text, stt_time
