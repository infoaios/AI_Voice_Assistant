"""
Global Data - Static Constants, Enums, and Default Configs

This module contains static values that don't change at runtime:
- Enums (roles, statuses, request types)
- Default configurations
- Static mappings (language codes, intent keys)
- Audio format definitions

❌ NOT for runtime device detection or dynamic configuration
✅ Use config_service.py for runtime configuration
"""

from enum import Enum
from typing import Dict, List

# ========== ENUMS ==========

class Role(str, Enum):
    """User roles in the system"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"

class CallStatus(str, Enum):
    """Call status values"""
    ACTIVE = "active"
    ENDED = "ended"
    FAILED = "failed"
    PENDING = "pending"

class RequestType(str, Enum):
    """Request type values"""
    STT = "STT"  # Speech-to-Text
    TTT = "TTT"  # Text-to-Text
    TTS = "TTS"  # Text-to-Speech

class AudioFormat(str, Enum):
    """Supported audio formats"""
    WAV = "wav"
    MP3 = "mp3"
    WEBM = "webm"
    M4A = "m4a"

# ========== DEFAULT CONFIGURATIONS ==========

# Default engine names (static defaults)
DEFAULT_STT_ENGINE = "whisper"
DEFAULT_TTT_ENGINE = "TinyLlama"
DEFAULT_TTS_ENGINE = "xtts_v2"

# Default voice settings
DEFAULT_VOICE = "female_1"
DEFAULT_LANGUAGE = "en"
DEFAULT_SAMPLE_RATE = 16000

# Default rate limits
DEFAULT_RATE_LIMIT_PER_MINUTE = 60
DEFAULT_RATE_LIMIT_PER_HOUR = 1000

# Default thresholds
DEFAULT_VAD_THRESHOLD = 0.5
DEFAULT_MAX_SILENCE = 1.0

# Restaurant business rules
RESTAURANT_OPEN_HOUR = 11
RESTAURANT_CLOSE_HOUR = 23
OUT_OF_STOCK_ITEMS = ["Ice Cream", "Special Dessert"]

# LLM blocking keywords (food-related queries should be blocked from LLM)
FOOD_KEYWORDS = [
    "make", "recipe", "ingredient", "cook", "prepare", 
    "how to", "how do", "what is", "tell me about",
    "price", "cost", "rupees", "₹", "rs",
    "menu", "dish", "food", "item", "order",
    "add", "want", "get", "give me"
]

# ========== STATIC MAPPINGS ==========

# Language code to name mapping
LANGUAGES: Dict[str, str] = {
    "en": "English",
    "hi": "Hindi",
    "gu": "Gujarati",
    "mr": "Marathi",
    "ta": "Tamil",
    "te": "Telugu",
}

# Intent keys to descriptions
INTENTS: Dict[str, str] = {
    "book": "Book a table",
    "pricing": "Menu pricing",
    "support": "Customer support",
    "handoff": "Human handoff",
    "order": "Place order",
    "menu": "View menu",
    "cancel": "Cancel order",
}

# Audio format descriptions
AUDIO_FORMAT_DESCRIPTIONS: Dict[str, str] = {
    "wav": "Uncompressed audio format",
    "mp3": "Compressed audio format",
    "webm": "Web audio format",
    "m4a": "Apple audio format",
}

# ========== LEGACY LISTS (for backward compatibility) ==========

ROLES: List[str] = [role.value for role in Role]
CALL_STATUS: List[str] = [status.value for status in CallStatus]
REQUEST_TYPES: List[str] = [req.value for req in RequestType]
AUDIO_FORMATS: List[str] = [fmt.value for fmt in AudioFormat]

# ========== DEFAULT CONFIG DICT (for backward compatibility) ==========

DEFAULT_CONFIG: Dict[str, any] = {
    "stt_engine": DEFAULT_STT_ENGINE,
    "ttt_engine": DEFAULT_TTT_ENGINE,
    "tts_engine": DEFAULT_TTS_ENGINE,
    "default_voice": DEFAULT_VOICE,
    "default_language": DEFAULT_LANGUAGE,
    "rate_limit_per_minute": DEFAULT_RATE_LIMIT_PER_MINUTE,
    "rate_limit_per_hour": DEFAULT_RATE_LIMIT_PER_HOUR,
    "vad_threshold": DEFAULT_VAD_THRESHOLD,
    "max_silence": DEFAULT_MAX_SILENCE,
    "sample_rate": DEFAULT_SAMPLE_RATE,
}
