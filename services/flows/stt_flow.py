"""
STT Flow - orchestrates speech-to-text processing

Uses interfaces to reduce coupling.
"""
# Use interfaces for stable contracts
try:
    from core.interfaces import ISTTService
except ImportError:
    from llms.STT.stt_service import STTService as ISTTService

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
    
    def process(self):
        """Process audio input and return transcribed text"""
        print("\n[Recording...]")
        audio = self.audio_processor.record_until_silence()
        
        if audio.size == 0:
            print("[Info] No audio detected.\n")
            return None
        
        # STT
        text, stt_time = self.stt_service.transcribe_with_timing(audio)
        if not text.strip():
            print("[Info] No speech detected.\n")
            return None
        
        print(f"\n[User]: {text}")
        return text, stt_time

