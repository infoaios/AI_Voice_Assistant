"""
TTS Flow - orchestrates text-to-speech processing

Uses interfaces to reduce coupling.
"""
# Use interfaces for stable contracts
try:
    from core.interfaces import ITTSService
except ImportError:
    from llms.TTS.tts_service import TTSService as ITTSService


class TTSFlow:
    """
    Flow for Text-to-Speech processing
    
    Depends on TTS service interface, allowing implementations to change.
    """
    
    def __init__(self, tts_service: ITTSService):
        """
        Initialize TTS flow
        
        Args:
            tts_service: Text-to-speech service interface
        """
        self.tts_service = tts_service
    
    def process(self, text: str):
        """Process text and speak it"""
        tts_time = self.tts_service.speak(text)
        return tts_time

